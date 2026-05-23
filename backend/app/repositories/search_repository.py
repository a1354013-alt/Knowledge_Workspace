# ruff: noqa: E501
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SUPPORTED_SEARCH_ITEM_TYPES = ("knowledge", "logbook", "document", "photo", "prompt", "autotest_run")


@dataclass(frozen=True)
class SearchFilters:
    keyword: str
    status: str
    tag: str
    date_from: str
    date_to: str
    limit: int
    selected_types: tuple[str, ...]


@dataclass(frozen=True)
class SearchQuerySpec:
    table: str
    id_col: str
    title_col: str
    status_col: str
    tags_expr: str
    haystack_expr: str
    created_col: str
    updated_col: str
    extra_where: str
    extra_params: tuple[Any, ...]
    item_type: str
    source_type_expr: str
    source_ref_expr: str


class SearchRepositoryMixin:
    def search_items(
        self,
        *,
        user_id: str,
        keyword: str = "",
        item_types: list[str] | None = None,
        status: str = "",
        tag: str = "",
        date_from: str = "",
        date_to: str = "",
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        filters = _normalize_filters(
            keyword=keyword,
            item_types=item_types,
            status=status,
            tag=tag,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
        )
        queries = _build_queries(user_id=user_id, selected_types=filters.selected_types)
        sql, params = _build_union_sql(queries=queries, filters=filters)

        with self._connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_map_search_row(row) for row in rows]


def _normalize_filters(
    *,
    keyword: str,
    item_types: list[str] | None,
    status: str,
    tag: str,
    date_from: str,
    date_to: str,
    limit: int,
) -> SearchFilters:
    selected = tuple(item_type for item_type in (item_types or []) if item_type in SUPPORTED_SEARCH_ITEM_TYPES)
    if not selected:
        selected = tuple(sorted(SUPPORTED_SEARCH_ITEM_TYPES))
    return SearchFilters(
        keyword=str(keyword or "").strip().lower(),
        status=str(status or "").strip(),
        tag=str(tag or "").strip(),
        date_from=str(date_from or "").strip(),
        date_to=str(date_to or "").strip(),
        limit=max(1, min(int(limit), 500)),
        selected_types=selected,
    )


def _common_where(filters: SearchFilters) -> tuple[list[str], list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if filters.keyword:
        clauses.append("haystack LIKE ?")
        params.append(f"%{filters.keyword}%")
    if filters.status:
        clauses.append("status = ?")
        params.append(filters.status)
    if filters.tag:
        clauses.append("tags LIKE ?")
        params.append(f"%{filters.tag}%")
    if filters.date_from:
        clauses.append("updated_at >= ?")
        params.append(filters.date_from)
    if filters.date_to:
        clauses.append("updated_at <= ?")
        params.append(filters.date_to)
    return clauses, params


def _build_query_sql(spec: SearchQuerySpec, filters: SearchFilters) -> tuple[str, list[Any]]:
    clauses_common, params_common = _common_where(filters)
    where_parts = [spec.extra_where] if spec.extra_where else []
    if clauses_common:
        where_parts.append(" AND ".join(clauses_common))
    where_sql = " AND ".join(part for part in where_parts if part)
    if where_sql:
        where_sql = "WHERE " + where_sql
    sql = f"""
            SELECT
              '{spec.item_type}' AS item_type,
              {spec.id_col} AS item_id,
              {spec.title_col} AS title,
              {spec.status_col} AS status,
              {spec.created_col} AS created_at,
              {spec.updated_col} AS updated_at,
              {spec.source_type_expr} AS source_type,
              {spec.source_ref_expr} AS source_ref,
              {spec.tags_expr} AS tags,
              {spec.haystack_expr} AS haystack
            FROM {spec.table}
            {where_sql}
            """
    return sql, [*spec.extra_params, *params_common]


def _build_queries(*, user_id: str, selected_types: tuple[str, ...]) -> list[SearchQuerySpec]:
    by_type = {
        "knowledge": SearchQuerySpec(
            "knowledge_entries",
            "entry_id",
            "COALESCE(NULLIF(title,''), substr(problem,1,80))",
            "status",
            "tags",
            "lower(title || ' ' || problem || ' ' || solution || ' ' || tags || ' ' || source_type || ' ' || source_ref)",
            "created_at",
            "updated_at",
            "created_by = ? AND is_active = 1",
            (user_id,),
            "knowledge",
            "source_type",
            "source_ref",
        ),
        "logbook": SearchQuerySpec(
            "logbook_entries",
            "entry_id",
            "COALESCE(NULLIF(title,''), substr(problem,1,80))",
            "status",
            "tags",
            "lower(title || ' ' || problem || ' ' || solution || ' ' || tags || ' ' || source_type || ' ' || source_ref)",
            "created_at",
            "updated_at",
            "created_by = ? AND is_active = 1",
            (user_id,),
            "logbook",
            "source_type",
            "source_ref",
        ),
        "document": SearchQuerySpec(
            "documents",
            "doc_id",
            "filename",
            "status",
            "tags",
            "lower(filename || ' ' || category || ' ' || tags)",
            "uploaded_at",
            "updated_at",
            "uploaded_by = ? AND is_active = 1",
            (user_id,),
            "document",
            "''",
            "''",
        ),
        "photo": SearchQuerySpec(
            "photos",
            "photo_id",
            "filename",
            "status",
            "tags",
            "lower(filename || ' ' || tags || ' ' || description || ' ' || ocr_text)",
            "created_at",
            "updated_at",
            "uploaded_by = ? AND is_active = 1",
            (user_id,),
            "photo",
            "''",
            "''",
        ),
        "prompt": SearchQuerySpec(
            "saved_prompts",
            "prompt_id",
            "title",
            "CASE WHEN is_active = 1 THEN 'active' ELSE 'archived' END",
            "tags",
            "lower(title || ' ' || tags || ' ' || content)",
            "created_at",
            "updated_at",
            "created_by = ? AND is_active = 1",
            (user_id,),
            "prompt",
            "''",
            "''",
        ),
        "autotest_run": SearchQuerySpec(
            "autotest_runs",
            "run_id",
            "COALESCE(NULLIF(project_name,''), source_ref)",
            "status",
            "''",
            "lower(project_name || ' ' || source_ref || ' ' || summary || ' ' || suggestion)",
            "created_at",
            "COALESCE(NULLIF(updated_at,''), created_at)",
            "created_by = ?",
            (user_id,),
            "autotest_run",
            "source_type",
            "source_ref",
        ),
    }
    return [by_type[item_type] for item_type in selected_types if item_type in by_type]


def _build_union_sql(*, queries: list[SearchQuerySpec], filters: SearchFilters) -> tuple[str, list[Any]]:
    sql_parts: list[str] = []
    all_params: list[Any] = []
    for query in queries:
        sql, params = _build_query_sql(query, filters)
        sql_parts.append(sql)
        all_params.extend(params)
    union_sql = " UNION ALL ".join(sql_parts)
    sql = f"""
        SELECT item_type, item_id, title, status, created_at, updated_at, source_type, source_ref
        FROM (
          {union_sql}
        )
        ORDER BY updated_at DESC
        LIMIT ?
        """
    all_params.append(filters.limit)
    return sql, all_params


def _map_search_row(row: Any) -> dict[str, Any]:
    return dict(row)
