"""
sql_visualizer.py
------------------
Builds an illustrative, step-by-step visual explanation of a generated SQL
SELECT statement: Original Table -> After WHERE -> After SELECT -> Final
Result, plus a plain-English bullet breakdown of each clause.

The sample data shown is fabricated for illustration only (the app has no
live database connection to draw real rows from) -- it exists purely to
make the effect of WHERE / SELECT mechanically obvious, the same way a
teacher would sketch it on a whiteboard.

All HTML returned by this module is built as flat, single-line strings
(no leading indentation, no embedded blank lines) on purpose: Streamlit's
markdown renderer treats indented block-level HTML (<div>, <table>, ...)
as a literal code block instead of parsing it, which is exactly the bug
this module previously had.
"""

import re


# --------------------------------------------------------------------------- #
# Best-effort SQL parsing (for explanation purposes only)
# --------------------------------------------------------------------------- #
def _parse_select(sql: str):
    """
    Very small parser for simple SELECT statements. Returns a dict with
    keys: select ('*' or list[str]), table, where (col, op, val) | None,
    group_by, order_by (col, dir) | None, limit -- or None if this isn't a
    simple SELECT we know how to visualize this way.
    """
    s = sql.strip().rstrip(";")

    m = re.match(r"select\s+(.+?)\s+from\s+([a-zA-Z_][a-zA-Z0-9_]*)", s, re.IGNORECASE | re.DOTALL)
    if not m:
        return None

    select_raw = m.group(1).strip()
    table = m.group(2).strip()

    if select_raw == "*":
        select_cols = "*"
    else:
        select_cols = [c.strip() for c in select_raw.split(",") if c.strip()]

    where = None
    wm = re.search(r"\bwhere\s+(.+?)(?:\bgroup by\b|\border by\b|\blimit\b|$)", s, re.IGNORECASE | re.DOTALL)
    if wm:
        cond = wm.group(1).strip()
        cm = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*(=|!=|<>|>=|<=|>|<|LIKE)\s*(.+)", cond, re.IGNORECASE)
        if cm:
            where = (cm.group(1), cm.group(2).upper(), cm.group(3).strip())

    order_by = None
    om = re.search(r"\border by\s+([a-zA-Z_][a-zA-Z0-9_]*)(\s+desc|\s+asc)?", s, re.IGNORECASE)
    if om:
        order_by = (om.group(1), (om.group(2) or "").strip().upper() or "ASC")

    limit = None
    lm = re.search(r"\blimit\s+(\d+)", s, re.IGNORECASE)
    if lm:
        limit = lm.group(1)

    group_by = None
    gm = re.search(r"\bgroup by\s+([a-zA-Z_][a-zA-Z0-9_]*)", s, re.IGNORECASE)
    if gm:
        group_by = gm.group(1)

    return {
        "select": select_cols,
        "table": table,
        "where": where,
        "order_by": order_by,
        "limit": limit,
        "group_by": group_by,
    }


# --------------------------------------------------------------------------- #
# Illustrative sample-data generation
# --------------------------------------------------------------------------- #
_SAMPLE_NAMES = ["Rahul", "Priya", "Arjun", "Sneha", "Kiran"]

_CONTRAST_VALUES = {
    "pass": "Fail", "fail": "Pass",
    "active": "Inactive", "inactive": "Active",
    "completed": "Pending", "pending": "Completed",
    "cancelled": "Active", "canceled": "Active",
    "yes": "No", "no": "Yes",
}


def _contrasting_value(value: str) -> str:
    return _CONTRAST_VALUES.get(value.lower(), "Other")


def _build_columns(select_cols, where):
    cols = ["id"]

    if select_cols == "*":
        cols.extend(["name", "status"])
    else:
        for c in select_cols:
            base = c.split("(")[-1].rstrip(")").strip()
            if base and base.lower() not in [x.lower() for x in cols]:
                cols.append(base)

    if where:
        wcol = where[0]
        if wcol.lower() not in [x.lower() for x in cols]:
            cols.append(wcol)

    return cols


def _sample_where_cell(where, i):
    """Deterministically fabricate a WHERE-column value for sample row i, and
    whether that value satisfies the condition -- returns (value, satisfies)."""
    _col, op, val = where
    raw_val = val.strip().strip("'\"")
    is_numeric = re.match(r"^-?\d+(\.\d+)?$", raw_val) is not None

    if is_numeric and op in (">", ">=", "<", "<="):
        base = float(raw_val)
        step = max(abs(base) * 0.15, 5)
        above = i < 3
        value = base + step if above else base - step
        satisfies = above if op in (">", ">=") else not above
        return str(int(value)), satisfies

    want_equal_cell = i % 2 == 0
    value = raw_val if want_equal_cell else _contrasting_value(raw_val)
    if op in ("!=", "<>"):
        satisfies = not want_equal_cell
    else:  # '=' or 'LIKE'
        satisfies = want_equal_cell
    return value, satisfies


def _build_sample_rows(columns, where):
    """Returns a list of (row_dict, satisfies_where_bool) for 5 illustrative rows."""
    where_col = where[0] if where else None
    rows = []

    for i in range(5):
        row = {}
        satisfies = True
        for col in columns:
            cl = col.lower()
            if where_col and cl == where_col.lower():
                value, satisfies = _sample_where_cell(where, i)
                row[col] = value
            elif cl == "id" or cl.endswith("_id"):
                row[col] = str(i + 1)
            elif "name" in cl:
                row[col] = _SAMPLE_NAMES[i % len(_SAMPLE_NAMES)]
            elif any(k in cl for k in ("price", "salary", "amount", "marks", "score", "total")):
                row[col] = str(100 * (i + 1))
            elif "status" in cl:
                row[col] = "Active" if i % 2 == 0 else "Inactive"
            else:
                row[col] = f"value{i + 1}"
        rows.append((row, satisfies))

    return rows


# --------------------------------------------------------------------------- #
# HTML rendering helpers (flat, single-line strings only -- see module docstring)
# --------------------------------------------------------------------------- #
def _render_table_html(columns, rows, highlight_col=None):
    if not rows:
        return '<div style="padding:14px;color:#94A3B8;font-size:0.85rem;">No rows match.</div>'

    header_cells = "".join(
        f'<th style="padding:7px 12px;text-align:left;font-size:0.78rem;'
        f'color:#475569;background:#F1F5F9;border-bottom:1px solid #E2E8F0;">{c}</th>'
        for c in columns
    )

    body_rows = []
    for row in rows:
        cells = []
        for c in columns:
            val = row.get(c, "")
            style = "padding:7px 12px;font-size:0.82rem;color:#1E293B;border-bottom:1px solid #F1F5F9;"
            if highlight_col and c.lower() == highlight_col.lower():
                style += "font-weight:700;color:#0F4C5C;background:#F0FDF4;"
            cells.append(f'<td style="{style}">{val}</td>')
        body_rows.append("<tr>" + "".join(cells) + "</tr>")

    return (
        '<div style="overflow-x:auto;">'
        '<table style="width:100%;border-collapse:collapse;background:#FFFFFF;border-radius:8px;overflow:hidden;">'
        f'<thead><tr>{header_cells}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody>'
        '</table>'
        '</div>'
    )


def _step_panel(number, color, title, subtitle, table_html, caption):
    return (
        '<div style="flex:1;min-width:230px;background:#FFFFFF;border:1px solid #E2E8F0;'
        'border-radius:14px;padding:16px;">'
        '<div style="display:flex;align-items:center;gap:10px;margin-bottom:2px;">'
        f'<div style="width:26px;height:26px;border-radius:50%;background:{color};color:#FFFFFF;'
        f'display:flex;align-items:center;justify-content:center;font-weight:700;font-size:0.82rem;'
        f'flex-shrink:0;">{number}</div>'
        f'<div style="font-weight:700;color:#1E293B;font-size:0.92rem;">{title}</div>'
        '</div>'
        f'<div style="font-size:0.78rem;color:#64748B;margin:0 0 10px 36px;word-break:break-word;">{subtitle}</div>'
        f'{table_html}'
        f'<div style="font-size:0.78rem;color:#64748B;margin-top:10px;">{caption}</div>'
        '</div>'
    )


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
def build_query_steps_html(sql: str) -> str:
    """
    Returns a flat HTML string with the step-by-step visual explanation for
    a simple SELECT statement, or "" if the statement isn't one this module
    knows how to visualize this way (INSERT/UPDATE/DELETE, complex joins,
    subqueries, etc.) -- callers should skip rendering the section in that case.
    """
    parsed = _parse_select(sql)
    if not parsed:
        return ""

    table = parsed["table"]
    select_cols = parsed["select"]
    where = parsed["where"]

    columns = _build_columns(select_cols, where)
    raw_rows = _build_sample_rows(columns, where)
    all_rows = [r for r, _ in raw_rows]
    filtered_rows = [r for r, satisfies in raw_rows if satisfies] if where else all_rows

    if select_cols == "*":
        final_cols = columns
    else:
        normalized = [c.split("(")[-1].rstrip(")").strip() for c in select_cols]
        final_cols = [c for c in columns if c in normalized] or columns

    panels = [
        _step_panel(
            1, "#2563EB", "Original Table", table,
            _render_table_html(columns, all_rows),
            "This is illustrative sample data, showing all rows and columns.",
        )
    ]

    step_num = 2
    if where:
        col, op, val = where
        panels.append(_step_panel(
            step_num, "#16A34A", "After WHERE Condition", f"{col} {op} {val}",
            _render_table_html(columns, filtered_rows, highlight_col=col),
            f"Only rows where {col} {op} {val} are kept.",
        ))
        step_num += 1

    select_label = "Select " + (", ".join(final_cols) if select_cols != "*" else "*")
    panels.append(_step_panel(
        step_num, "#D97706", "After SELECT", select_label,
        _render_table_html(final_cols, filtered_rows),
        f"Only the {', '.join(final_cols)} column(s) {'is' if len(final_cols) == 1 else 'are'} returned.",
    ))

    steps_row_html = (
        '<div style="display:flex;flex-wrap:wrap;gap:14px;margin-bottom:14px;">'
        + "".join(panels) + '</div>'
    )

    explanation_items = [f'<li><strong>FROM</strong> &rarr; Choose table (<code>{table}</code>)</li>']
    if where:
        col, op, val = where
        explanation_items.append(
            f'<li><strong>WHERE</strong> &rarr; Filter rows (<code>{col} {op} {val}</code>)</li>'
        )
    if parsed["group_by"]:
        explanation_items.append(
            f'<li><strong>GROUP BY</strong> &rarr; Group rows by <code>{parsed["group_by"]}</code></li>'
        )
    select_desc = ", ".join(final_cols) if select_cols != "*" else "*"
    explanation_items.append(f'<li><strong>SELECT</strong> &rarr; Choose column(s) (<code>{select_desc}</code>)</li>')
    if parsed["order_by"]:
        ocol, odir = parsed["order_by"]
        explanation_items.append(
            f'<li><strong>ORDER BY</strong> &rarr; Sort by <code>{ocol} {odir}</code></li>'
        )
    if parsed["limit"]:
        explanation_items.append(
            f'<li><strong>LIMIT</strong> &rarr; Restrict to <code>{parsed["limit"]}</code> row(s)</li>'
        )

    final_result_html = _render_table_html(final_cols, filtered_rows)

    bottom_row_html = (
        '<div style="display:flex;flex-wrap:wrap;gap:14px;">'
        '<div style="flex:1;min-width:230px;background:#FFFFFF;border:1px solid #E2E8F0;'
        'border-radius:14px;padding:16px;">'
        '<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">'
        '<div style="width:26px;height:26px;border-radius:50%;background:#7C3AED;color:#FFFFFF;'
        'display:flex;align-items:center;justify-content:center;font-weight:700;font-size:0.9rem;'
        'flex-shrink:0;">&#10003;</div>'
        '<div style="font-weight:700;color:#1E293B;font-size:0.92rem;">Final Result</div>'
        '</div>'
        f'{final_result_html}'
        '</div>'
        '<div style="flex:1;min-width:230px;background:#FFFFFF;border:1px solid #E2E8F0;'
        'border-radius:14px;padding:16px;">'
        '<div style="font-weight:700;color:#1E293B;font-size:0.92rem;margin-bottom:10px;">'
        '&#128161; Explanation</div>'
        f'<ul style="margin:0;padding-left:18px;color:#334155;font-size:0.82rem;line-height:1.85;">'
        f'{"".join(explanation_items)}</ul>'
        '</div>'
        '</div>'
    )

    return (
        '<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:16px;padding:18px;">'
        f'{steps_row_html}{bottom_row_html}'
        '</div>'
    )
