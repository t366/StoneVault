from sanic import Blueprint
from sanic.response import json

from ..database import Database
from ..query_service import FileQueryService


def _int_param(value: str | None, name: str) -> tuple[int | None, str | None]:
    if value is None or value == "":
        return None, None
    try:
        return int(value), None
    except ValueError:
        return None, f"{name} 必须为整数"


def create_files_bp(db: Database) -> Blueprint:
    bp = Blueprint("files", url_prefix="/api/files")
    service = FileQueryService(db)

    @bp.get("/search")
    async def search_files(request):
        q = (request.args.get("q") or "").strip()
        page, err_page = _int_param(request.args.get("page"), "page")
        if err_page:
            return json({"error": err_page}, status=400)
        page_size, err_ps = _int_param(request.args.get("page_size"), "page_size")
        if err_ps:
            return json({"error": err_ps}, status=400)
        if not q:
            return json({"error": "查询词不能为空"}, status=400)
        result = service.fts_query(q=q, page=page or 1, page_size=page_size or 20)
        return json(result)

    @bp.get("/")
    async def list_files(request):
        args = request.args
        size_min, err_min = _int_param(args.get("size_min"), "size_min")
        if err_min:
            return json({"error": err_min}, status=400)
        size_max, err_max = _int_param(args.get("size_max"), "size_max")
        if err_max:
            return json({"error": err_max}, status=400)
        page, err_page = _int_param(args.get("page"), "page")
        if err_page:
            return json({"error": err_page}, status=400)
        page_size, err_ps = _int_param(args.get("page_size"), "page_size")
        if err_ps:
            return json({"error": err_ps}, status=400)

        result = service.query(
            q=args.get("q"),
            ext=args.get("ext"),
            from_time=args.get("from"),
            to_time=args.get("to"),
            size_min=size_min,
            size_max=size_max,
            page=page or 1,
            page_size=page_size or 50,
            sort_by=args.get("sort_by") or "id",
            order=args.get("order") or "desc",
        )
        return json(result)

    return bp
