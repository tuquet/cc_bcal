from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Tuple


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def paginate_query(
    query,
    model,
    request_args: Mapping[str, str],
    serialize: Optional[Callable[[Any], Dict]] = None,
    *,
    page_param: str = "page",
    page_size_param: str = "pageSize",
    legacy_page_size_param: str = "per_page",
    default_page: int = 1,
    default_page_size: int = 25,
    max_page_size: int = 100,
    sort_by_param: str = "sortBy",
    sort_order_param: str = "sortOrder",
    default_sort: str = "updated_at",
    allowed_sort_fields: Optional[Iterable[str]] = None,
):
    """
    Generic pagination helper for SQLAlchemy queries.

    Parameters:
      - query: base SQLAlchemy query (no ordering applied)
      - model: SQLAlchemy model class used to resolve sort columns
      - request_args: typically `request.args`
      - serialize: callable(item) -> dict, if None uses item.to_dict()
    Returns: dict with keys 'meta' and 'data'
    """

    page = _to_int(request_args.get(page_param), default_page) if request_args else default_page

    # prefer new param pageSize, but fall back to legacy per_page
    page_size_raw = request_args.get(page_size_param) if request_args else None
    if page_size_raw is None:
        page_size_raw = request_args.get(legacy_page_size_param) if request_args else None
    page_size = _to_int(page_size_raw, default_page_size)

    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > max_page_size:
        page_size = max_page_size

    sort_by = (request_args.get(sort_by_param) if request_args else None) or default_sort
    sort_order = (request_args.get(sort_order_param) if request_args else None) or "desc"
    sort_order = str(sort_order).lower()

    if allowed_sort_fields is not None and sort_by not in allowed_sort_fields:
        sort_by = default_sort

    # Resolve column and apply ordering
    try:
        sort_column = getattr(model, sort_by)
    except Exception:
        sort_column = getattr(model, default_sort)

    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    total = query.count()
    total_pages = (total + page_size - 1) // page_size if page_size else 1
    offset = (page - 1) * page_size
    items_q = query.offset(offset).limit(page_size).all()

    data = []
    for item in items_q:
        if serialize:
            data.append(serialize(item))
        else:
            if hasattr(item, "to_dict"):
                data.append(item.to_dict())
            else:
                # fallback: try to convert mapping
                try:
                    data.append(dict(item))
                except Exception:
                    data.append({})

    return {
        "meta": {
            "total": total,
            "page": page,
            "pageSize": page_size,
            "total_pages": total_pages,
            "sortBy": sort_by,
            "sortOrder": sort_order,
        },
        "data": data,
    }


def has_pagination_args(request_args: Mapping[str, str], keys: Optional[Iterable[str]] = None) -> bool:
    """Return True if any of the provided keys exist in request_args.

    Default keys checked are: page, pageSize, per_page, sortBy, sortOrder.
    """
    if not request_args:
        return False
    default_keys = ("page", "pageSize", "per_page", "sortBy", "sortOrder")
    check_keys = keys if keys is not None else default_keys
    return any(k in request_args for k in check_keys)


__all__ = ["paginate_query", "has_pagination_args"]
