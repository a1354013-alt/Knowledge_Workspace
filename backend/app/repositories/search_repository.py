# ruff: noqa: E501
from __future__ import annotations

from typing import Any


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
        keyword = str(keyword or "").strip().lower()
        status = str(status or "").strip()
        tag = str(tag or "").strip()
        date_from = str(date_from or "").strip()
        date_to = str(date_to or "").strip()
        limit = max(1, min(int(limit), 500))

        supported = {"knowledge", "logbook", "document", "photo", "prompt", "autotest_run"}
        selected = [t for t in (item_types or []) if t in supported]
        if not selected:
            selected = sorted(supported)

        clauses_common: list[str] = []
        params_common: list[Any] = []

        if keyword:
            clauses_common.append("haystack LIKE ?")
            params_common.append(f"%{keyword}%")
        if status:
            clauses_common.append("status = ?")
            params_common.append(status)
        if tag:
            clauses_common.append("tags LIKE ?")
            params_common.append(f"%{tag}%")
        if date_from:
            clauses_common.append("updated_at >= ?")
            params_common.append(date_from)
        if date_to:
            clauses_common.append("updated_at <= ?")
            params_common.append(date_to)

        def build_query(table: str, id_col: str, title_col: str, status_col: str, tags_expr: str, haystack_expr: str, created_col: str, updated_col: str, extra_where: str, extra_params: list[Any], item_type: str, source_type_expr: str, source_ref_expr: str) -> tuple[str, list[Any]]:
            where_parts = [extra_where] if extra_where else []
            if clauses_common:
                where_parts.append(" AND ".join(clauses_common))
            where_sql = " AND ".join([part for part in where_parts if part])
            if where_sql:
                where_sql = "WHERE " + where_sql
            sql = f"""
            SELECT
              '{item_type}' AS item_type,
              {id_col} AS item_id,
              {title_col} AS title,
              {status_col} AS status,
              {created_col} AS created_at,
              {updated_col} AS updated_at,
              {source_type_expr} AS source_type,
              {source_ref_expr} AS source_ref,
              {tags_expr} AS tags,
              {haystack_expr} AS haystack
            FROM {table}
            {where_sql}
            """
            return sql, [*extra_params, *params_common]

        queries: list[tuple[str, list[Any]]] = []

        if "knowledge" in selected:
            sql, params = build_query(
                "knowledge_entries",
                "entry_id",
                "COALESCE(NULLIF(title,''), substr(problem,1,80))",
                "status",
                "tags",
                "lower(title || ' ' || problem || ' ' || solution || ' ' || tags || ' ' || source_type || ' ' || source_ref)",
                "created_at",
                "updated_at",
                "created_by = ? AND is_active = 1",
                [user_id],
                "knowledge",
                "source_type",
                "source_ref",
            )
            queries.append((sql, params))

        if "logbook" in selected:
            sql, params = build_query(
                "logbook_entries",
                "entry_id",
                "COALESCE(NULLIF(title,''), substr(problem,1,80))",
                "status",
                "tags",
                "lower(title || ' ' || problem || ' ' || solution || ' ' || tags || ' ' || source_type || ' ' || source_ref)",
                "created_at",
                "updated_at",
                "created_by = ? AND is_active = 1",
                [user_id],
                "logbook",
                "source_type",
                "source_ref",
            )
            queries.append((sql, params))

        if "document" in selected:
            sql, params = build_query(
                "documents",
                "doc_id",
                "filename",
                "status",
                "tags",
                "lower(filename || ' ' || category || ' ' || tags)",
                "uploaded_at",
                "updated_at",
                "uploaded_by = ? AND is_active = 1",
                [user_id],
                "document",
                "''",
                "''",
            )
            queries.append((sql, params))

        if "photo" in selected:
            sql, params = build_query(
                "photos",
                "photo_id",
                "filename",
                "status",
                "tags",
                "lower(filename || ' ' || tags || ' ' || description || ' ' || ocr_text)",
                "created_at",
                "updated_at",
                "uploaded_by = ? AND is_active = 1",
                [user_id],
                "photo",
                "''",
                "''",
            )
            queries.append((sql, params))

        if "prompt" in selected:
            sql, params = build_query(
                "saved_prompts",
                "prompt_id",
                "title",
                "CASE WHEN is_active = 1 THEN 'active' ELSE 'archived' END",
                "tags",
                "lower(title || ' ' || tags || ' ' || content)",
                "created_at",
                "updated_at",
                "created_by = ? AND is_active = 1",
                [user_id],
                "prompt",
                "''",
                "''",
            )
            queries.append((sql, params))

        if "autotest_run" in selected:
            sql, params = build_query(
                "autotest_runs",
                "run_id",
                "COALESCE(NULLIF(project_name,''), source_ref)",
                "status",
                "''",
                "lower(project_name || ' ' || source_ref || ' ' || summary || ' ' || suggestion)",
                "created_at",
                "created_at",
                "created_by = ?",
                [user_id],
                "autotest_run",
                "source_type",
                "source_ref",
            )
            queries.append((sql, params))

        union_sql = " UNION ALL ".join([q[0] for q in queries])
        sql = f"""
        SELECT item_type, item_id, title, status, created_at, updated_at, source_type, source_ref
        FROM (
          {union_sql}
        )
        ORDER BY updated_at DESC
        LIMIT ?
        """
        all_params: list[Any] = []
        for _q, params in queries:
            all_params.extend(params)
        all_params.append(limit)

        with self._connection() as conn:
            rows = conn.execute(sql, all_params).fetchall()
        return [dict(row) for row in rows]
