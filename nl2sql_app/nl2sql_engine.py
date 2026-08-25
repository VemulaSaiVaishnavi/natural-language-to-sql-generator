"""
nl2sql_engine.py
-----------------
Converts a natural-language request into a SQL query.

Two modes:
    1. Rule-based engine (always available, no API key required). Uses
       keyword/regex pattern matching to cover SELECT, WHERE, JOIN,
       GROUP BY, ORDER BY, HAVING, aggregate functions, INSERT, UPDATE,
       DELETE and simple subqueries.
    2. AI-assisted mode (optional). If the user supplies an Anthropic API
       key in the sidebar, the request is sent to Claude for a more
       flexible/accurate translation. Falls back to the rule-based engine
       automatically if the call fails for any reason (no key, no network,
       bad response, etc.) so the app never crashes.
"""

import re
from dataclasses import dataclass, field


@dataclass
class SQLResult:
    sql: str
    explanation: str
    engine_used: str = "rule-based"
    warning: str = ""


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
_AGG_WORDS = {
    "count": "COUNT",
    "number of": "COUNT",
    "total number of": "COUNT",
    "sum": "SUM",
    "total": "SUM",
    "average": "AVG",
    "avg": "AVG",
    "maximum": "MAX",
    "highest": "MAX",
    "max": "MAX",
    "minimum": "MIN",
    "lowest": "MIN",
    "min": "MIN",
}

_OP_WORDS = [
    (r"greater than or equal to|at least|>=", ">="),
    (r"less than or equal to|at most|<=", "<="),
    (r"not equal to|is not|!=|<>", "!="),
    (r"greater than|more than|above|over", ">"),
    (r"less than|below|under", "<"),
    (r"starts with|begins with", "LIKE_PREFIX"),
    (r"ends with", "LIKE_SUFFIX"),
    (r"contains|containing|like", "LIKE"),
    (r"equal to|equals|is|=", "="),
]

_STOPWORDS_TABLE_PREFIX = (
    "the ", "a ", "an ", "all ", "every "
)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _sql_literal(value: str) -> str:
    """Render a raw extracted value as a numeric literal or a quoted string literal."""
    if re.match(r"^-?\d+(\.\d+)?$", value):
        return value
    return "'" + value.replace("'", "''") + "'"


_STOPWORD_GROUP = r"(?:the|a|an|all|every)\s+"

_COLUMN_FILLER_WORDS = {
    "the", "a", "an", "column", "columns", "field", "fields",
    "is", "was", "are", "were", "has", "have",
}


def _clean_column_token(token: str) -> str:
    words = [w for w in token.strip().split() if w.lower() not in _COLUMN_FILLER_WORDS]
    return "_".join(words) if words else token.strip().replace(" ", "_")

# Adjectives that imply an unstated status-style condition, e.g.
# "who passed the exam" -> WHERE exam_status = 'Pass'
_STATUS_ADJECTIVES = {
    "passed": "Pass",
    "pass": "Pass",
    "failed": "Fail",
    "fail": "Fail",
    "active": "Active",
    "inactive": "Inactive",
    "completed": "Completed",
    "pending": "Pending",
    "cancelled": "Cancelled",
    "canceled": "Cancelled",
}

# Domain words where we know a friendlier table/column convention,
# e.g. "exam" -> table 'exam_results', name column 'student_name'.
_DOMAIN_TABLE_MAP = {
    "exam": "exam_results",
    "exams": "exam_results",
    "test": "exam_results",
    "tests": "exam_results",
}

_DOMAIN_NAME_COLUMN = {
    "exam": "student_name",
    "exams": "student_name",
    "test": "student_name",
    "tests": "student_name",
    "student": "student_name",
    "students": "student_name",
}


def _extract_domain_noun(text: str):
    """Look for 'from <x>' / 'in <x>' / 'into <x>' and return the raw noun, or None."""
    match = re.search(
        rf"\b(?:from|into|in)\s+(?:{_STOPWORD_GROUP})?([a-zA-Z_][a-zA-Z0-9_]*)",
        text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1)

    agg_of = re.search(r"(?:number|total|count|sum|average|avg)\s+of\s+([a-zA-Z_][a-zA-Z0-9_]*)", text, re.IGNORECASE)
    if agg_of:
        return agg_of.group(1)

    # fallback for phrasing with no preposition at all, e.g. "show all employees who ..."
    implicit = re.search(
        r"\b(?:show|get|find|list|select|display|give(?:\s+me)?)\b\s+(?:all|every)\s+([a-zA-Z_][a-zA-Z0-9_]*)",
        text,
        re.IGNORECASE,
    )
    if implicit:
        return implicit.group(1)

    return None


def _extract_status_adjective(lower_text: str):
    """Return (word, value) for the first status-style adjective found as a whole word."""
    for word, value in _STATUS_ADJECTIVES.items():
        if re.search(rf"\b{word}\b", lower_text):
            return word, value
    return None


def _domain_status_column(domain_noun: str) -> str:
    if not domain_noun:
        return "status"
    return f"{domain_noun.lower().rstrip('s')}_status"


def _domain_table_name(domain_noun: str):
    if not domain_noun:
        return None
    return _DOMAIN_TABLE_MAP.get(domain_noun.lower())


def _domain_name_column(domain_noun: str) -> str:
    if not domain_noun:
        return "name"
    return _DOMAIN_NAME_COLUMN.get(domain_noun.lower(), "name")


def _extract_table(text: str) -> str:
    """Look for 'from <table>' / 'in <table>' / 'into <table>' patterns, skipping filler words."""
    noun = _extract_domain_noun(text)
    return noun if noun else "table_name"  # honest placeholder rather than guessing a wrong word


def _extract_update_table(text: str) -> str:
    match = re.search(r"\bupdate\s+(?:{0})?([a-zA-Z_][a-zA-Z0-9_]*)".format(_STOPWORD_GROUP), text, re.IGNORECASE)
    if match:
        return match.group(1)
    return _extract_table(text)


def _extract_insert_table(text: str) -> str:
    match = re.search(
        rf"\b(?:insert|add).*?\b(?:into|to)\s+(?:{_STOPWORD_GROUP})?([a-zA-Z_][a-zA-Z0-9_]*)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        return match.group(1)
    return _extract_table(text)


def _extract_where(text: str):
    """Extract a single simple condition after 'where', or natural 'who'/'whose' phrasing."""
    m = re.search(r"\b(where|whose|who)\b(.+)", text, re.IGNORECASE)
    if not m:
        return None
    trigger_word = m.group(1).lower()
    clause = m.group(2).strip()
    # remove trailing order-by / group-by portions if present
    clause = re.split(r"\border by\b|\bgroup by\b|\bhaving\b", clause, flags=re.IGNORECASE)[0].strip()

    for pattern, op in _OP_WORDS:
        cm = re.search(rf"([a-zA-Z_][a-zA-Z0-9_ ]*?)\s*(?:{pattern})\s*([\w'.\-@]+)", clause, re.IGNORECASE)
        if cm:
            col = _clean_column_token(cm.group(1))
            val = cm.group(2).strip().strip("'\"")
            if op == "LIKE":
                return f"{col} LIKE '%{val}%'"
            if op == "LIKE_PREFIX":
                return f"{col} LIKE '{val}%'"
            if op == "LIKE_SUFFIX":
                return f"{col} LIKE '%{val}'"
            return f"{col} {op} {_sql_literal(val)}"

    # Explicit "where ..." with formatting we couldn't parse cleanly: pass it through
    # as a last resort. For natural "who"/"whose" phrasing we didn't manage to parse,
    # it's safer to omit the condition than to guess and emit invalid SQL.
    if trigger_word == "where" and clause:
        return clause
    return None


def _extract_order_by(text: str):
    m = re.search(r"order by\s+([a-zA-Z_][a-zA-Z0-9_]*)(\s+desc|\s+descending|\s+asc|\s+ascending)?", text, re.IGNORECASE)
    if not m:
        # natural phrasing: "sorted by X descending"
        m = re.search(r"sort(?:ed)? by\s+([a-zA-Z_][a-zA-Z0-9_]*)(\s+desc|\s+descending|\s+asc|\s+ascending)?", text, re.IGNORECASE)
        if not m:
            return None
    col = m.group(1)
    direction = "DESC" if m.group(2) and "desc" in m.group(2).lower() else "ASC"
    return f"{col} {direction}"


def _extract_group_by(text: str):
    m = re.search(r"group(?:ed)? by\s+([a-zA-Z_][a-zA-Z0-9_]*)", text, re.IGNORECASE)
    return m.group(1) if m else None


def _extract_join(text: str):
    """Detect 'join <table2> on <col>' phrasing."""
    m = re.search(
        r"join\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:on\s+([a-zA-Z0-9_.]+)\s*=\s*([a-zA-Z0-9_.]+))?",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    table2, left, right = m.group(1), m.group(2), m.group(3)
    return table2, left, right


def _extract_limit(text: str):
    m = re.search(r"\btop\s+(\d+)\b", text, re.IGNORECASE) or re.search(r"\bfirst\s+(\d+)\b", text, re.IGNORECASE) or re.search(r"\blimit\s+(\d+)\b", text, re.IGNORECASE)
    return m.group(1) if m else None


# --------------------------------------------------------------------------- #
# Rule-based generator
# --------------------------------------------------------------------------- #
def rule_based_generate(text: str) -> SQLResult:
    original = text
    text = _clean(text)
    lower = text.lower()

    # ---------------- INSERT ----------------
    if re.search(r"\b(insert|add)\b", lower) and re.search(r"\b(into|to)\b", lower):
        table = _extract_insert_table(text)
        cols_vals = re.findall(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:=|as|is)\s*([\w'.\-@]+)", text)
        if cols_vals:
            cols = ", ".join(c for c, _ in cols_vals)
            vals = ", ".join(_sql_literal(v) for _, v in cols_vals)
            sql = f"INSERT INTO {table} ({cols})\nVALUES ({vals});"
        else:
            sql = f"INSERT INTO {table} (column1, column2)\nVALUES (value1, value2);"
        return SQLResult(
            sql=sql,
            explanation=f"Adds a new row into the '{table}' table with the specified column values.",
        )

    # ---------------- DELETE ----------------
    if re.search(r"\bdelete\b", lower) or re.search(r"\bremove\b", lower):
        table = _extract_table(text)
        where = _extract_where(text)
        sql = f"DELETE FROM {table}"
        if where:
            sql += f"\nWHERE {where}"
        sql += ";"
        expl = f"Deletes rows from '{table}'"
        expl += f" that match the condition ({where})." if where else " (all rows — use WHERE to restrict!)."
        return SQLResult(sql=sql, explanation=expl)

    # ---------------- UPDATE ----------------
    if re.search(r"\bupdate\b|\bchange\b|\bset\b.*\bto\b", lower):
        table = _extract_update_table(text)
        set_clause = None
        m = re.search(r"set\s+(.+?)(?:\bwhere\b|$)", text, re.IGNORECASE)
        if m:
            assignments = re.findall(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:=|to)\s*([\w'.\-@]+)", m.group(1))
            if assignments:
                set_clause = ", ".join(f"{c} = {_sql_literal(v)}" for c, v in assignments)
        if not set_clause:
            set_clause = "column1 = value1"
        where = _extract_where(text)
        sql = f"UPDATE {table}\nSET {set_clause}"
        if where:
            sql += f"\nWHERE {where}"
        sql += ";"
        expl = f"Updates '{table}', setting {set_clause}"
        expl += f" for rows matching ({where})." if where else " for ALL rows (add a WHERE clause to be safer)."
        return SQLResult(sql=sql, explanation=expl)

    # ---------------- SELECT (default) ----------------
    domain_noun = _extract_domain_noun(text)
    table = _extract_table(text)

    # Aggregate detection
    agg_func, agg_col = None, None
    for phrase, func in sorted(_AGG_WORDS.items(), key=lambda kv: -len(kv[0])):
        if phrase in lower:
            agg_func = func
            m = re.search(rf"{phrase}\s+(?:of\s+)?([a-zA-Z_][a-zA-Z0-9_]*)", lower)
            agg_col = m.group(1) if m else "*"
            break

    group_col = _extract_group_by(text)
    order_clause = _extract_order_by(text)
    where_clause = _extract_where(text)
    join_info = _extract_join(text)
    limit_val = _extract_limit(text)

    # Implicit status-style condition from an adjective, e.g. "who passed the exam",
    # when there was no explicit "where ..." clause to begin with.
    if not where_clause:
        status_match = _extract_status_adjective(lower)
        if status_match:
            _, status_value = status_match
            status_col = _domain_status_column(domain_noun)
            where_clause = f"{status_col} = '{status_value}'"
            mapped_table = _domain_table_name(domain_noun)
            if mapped_table:
                table = mapped_table

    if agg_func:
        select_expr = f"{agg_func}({agg_col if agg_col != '*' or agg_func == 'COUNT' else '*'})"
        if group_col:
            select_clause = f"{group_col}, {select_expr}"
        else:
            select_clause = select_expr
    else:
        # try to find explicit column list, e.g. "show name and salary from employees"
        # (also covers "give me ..." phrasing, and stops before who/that/in/where even
        # without an explicit "from" — e.g. "give me names who passed in exam")
        col_match = re.search(
            r"\b(?:show|get|find|list|select|display|give(?:\s+me)?)\b\s+(.+?)"
            r"(?=\s+(?:from|who|that|which|in|where)\b)",
            lower,
        )
        is_limit_phrase = col_match and re.match(r"^(top|first)\s+\d+\b", col_match.group(1).strip())
        if col_match and not is_limit_phrase and "all" not in col_match.group(1) and "*" not in col_match.group(1):
            raw_cols = re.split(r",|\band\b", col_match.group(1))
            cols = []
            for c in raw_cols:
                c = _clean_column_token(c)
                if not c:
                    continue
                if c in ("name", "names"):
                    c = _domain_name_column(domain_noun)
                cols.append(c)
            select_clause = ", ".join(cols) if cols else "*"
        else:
            select_clause = "*"

    sql_lines = [f"SELECT {select_clause}"]
    from_line = f"FROM {table}"
    if join_info:
        table2, left, right = join_info
        from_line += f"\nJOIN {table2}"
        if left and right:
            from_line += f" ON {left} = {right}"
        else:
            from_line += f" ON {table}.id = {table2}.{table}_id"
    sql_lines.append(from_line)

    if where_clause:
        sql_lines.append(f"WHERE {where_clause}")
    if group_col:
        sql_lines.append(f"GROUP BY {group_col}")
    having_match = re.search(r"having\s+(.+)", lower)
    if having_match:
        having_clause = having_match.group(1).strip()
        # turn a bare "count > 5" into proper "COUNT(*) > 5" style syntax
        having_clause = re.sub(r"\bcount\b(?!\()", "COUNT(*)", having_clause, flags=re.IGNORECASE)
        for word, func in (("sum", "SUM"), ("average", "AVG"), ("avg", "AVG"), ("max", "MAX"), ("min", "MIN")):
            having_clause = re.sub(rf"\b{word}\s+([a-zA-Z_][a-zA-Z0-9_]*)", rf"{func}(\1)", having_clause, flags=re.IGNORECASE)
        sql_lines.append(f"HAVING {having_clause}")
    if order_clause:
        sql_lines.append(f"ORDER BY {order_clause}")
    if limit_val:
        sql_lines.append(f"LIMIT {limit_val}")

    sql = "\n".join(sql_lines) + ";"

    expl_parts = [f"Retrieves {'the ' + agg_func.lower() + ' of ' + agg_col if agg_func else select_clause} from '{table}'"]
    if join_info:
        expl_parts.append(f"joined with '{join_info[0]}'")
    if where_clause:
        expl_parts.append(f"filtered where {where_clause}")
    if group_col:
        expl_parts.append(f"grouped by {group_col}")
    if order_clause:
        expl_parts.append(f"sorted by {order_clause}")
    if limit_val:
        expl_parts.append(f"limited to {limit_val} row(s)")
    explanation = ", ".join(expl_parts) + "."

    return SQLResult(sql=sql, explanation=explanation)


# --------------------------------------------------------------------------- #
# Optional AI-assisted generator (Anthropic Claude)
# --------------------------------------------------------------------------- #
def ai_generate(text: str, api_key: str) -> SQLResult:
    """
    Attempts to use the Anthropic API for a higher-quality translation.
    Raises an exception on any failure; caller is expected to catch it
    and fall back to rule_based_generate().
    """
    import anthropic  # imported lazily so the app runs fine without the package

    client = anthropic.Anthropic(api_key=api_key)
    system_prompt = (
        "You are an expert SQL generator. Given a natural language request, respond with "
        "STRICT JSON only (no markdown fences, no prose) in this exact shape: "
        '{"sql": "<the SQL query, properly formatted>", "explanation": "<one or two plain-English sentences>"}. '
        "Assume standard ANSI SQL and reasonable table/column names when not specified."
    )
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=system_prompt,
        messages=[{"role": "user", "content": text}],
    )
    raw = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
    raw = raw.strip().strip("`")
    if raw.lower().startswith("json"):
        raw = raw[4:].strip()

    import json
    data = json.loads(raw)
    return SQLResult(sql=data["sql"], explanation=data.get("explanation", ""), engine_used="ai")


def generate_sql(text: str, api_key: str = "") -> SQLResult:
    """Main entry point used by the Streamlit app."""
    text = (text or "").strip()
    if not text:
        return SQLResult(sql="", explanation="Please enter a request first.")

    if api_key:
        try:
            return ai_generate(text, api_key)
        except Exception as exc:  # noqa: BLE001 - deliberate broad catch, always fall back safely
            result = rule_based_generate(text)
            result.warning = f"AI mode unavailable ({exc.__class__.__name__}); used the built-in rule-based engine instead."
            return result

    return rule_based_generate(text)
