"""DOM AST pruner for stripping noise and extracting structured tables, forms, and record nodes."""

import re
from html.parser import HTMLParser
from typing import Any


class CleanHTMLParser(HTMLParser):
    """HTML Parser that strips scripts, styles, SVGs, navs, footers, and extracts key data nodes."""

    BLOCKED_TAGS = {
        "script",
        "style",
        "svg",
        "noscript",
        "iframe",
        "nav",
        "footer",
        "header",
        "head",
    }

    def __init__(self) -> None:
        super().__init__()
        self.tags_stack: list[str] = []
        self.clean_text: list[str] = []
        self.tables: list[list[list[str]]] = []
        self.current_table: list[list[str]] | None = None
        self.current_row: list[str] | None = None
        self.current_cell: list[str] = []
        self.forms: list[dict[str, Any]] = []
        self.current_form: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()
        self.tags_stack.append(tag_lower)
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        if any(t in self.BLOCKED_TAGS for t in self.tags_stack):
            return

        if tag_lower == "form":
            self.current_form = {
                "action": attr_dict.get("action", ""),
                "method": attr_dict.get("method", "get").upper(),
                "inputs": [],
            }
        elif tag_lower in {"input", "select", "textarea"} and self.current_form is not None:
            self.current_form["inputs"].append({
                "tag": tag_lower,
                "name": attr_dict.get("name", ""),
                "type": attr_dict.get("type", "text"),
                "id": attr_dict.get("id", ""),
                "placeholder": attr_dict.get("placeholder", ""),
            })

        if tag_lower == "table":
            self.current_table = []
        elif tag_lower == "tr" and self.current_table is not None:
            self.current_row = []
        elif tag_lower in {"th", "td"} and self.current_row is not None:
            self.current_cell = []

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if self.tags_stack and self.tags_stack[-1] == tag_lower:
            self.tags_stack.pop()

        if any(t in self.BLOCKED_TAGS for t in self.tags_stack):
            return

        if tag_lower == "form" and self.current_form is not None:
            self.forms.append(self.current_form)
            self.current_form = None
        elif tag_lower in {"th", "td"} and self.current_row is not None:
            cell_text = " ".join(self.current_cell).strip()
            self.current_row.append(cell_text)
            self.current_cell = []
        elif tag_lower == "tr" and self.current_table is not None:
            if self.current_row is not None:
                self.current_table.append(self.current_row)
                self.current_row = None
        elif tag_lower == "table" and self.current_table is not None:
            if self.current_table:
                self.tables.append(self.current_table)
            self.current_table = None

    def handle_data(self, data: str) -> None:
        if any(t in self.BLOCKED_TAGS for t in self.tags_stack):
            return
        cleaned = re.sub(r"\s+", " ", data).strip()
        if not cleaned:
            return
        if self.current_row is not None and self.tags_stack and self.tags_stack[-1] in {"th", "td"}:
            self.current_cell.append(cleaned)
        self.clean_text.append(cleaned)


def prune_dom(html: str) -> dict[str, Any]:
    """Prune raw HTML into structured text, extracted tables, and form field maps."""
    if not html:
        return {"clean_text": "", "tables": [], "forms": [], "summary_stats": {"tables_found": 0, "forms_found": 0}}

    parser = CleanHTMLParser()
    parser.feed(html)

    # Convert tables into list of dicts where first row is header if valid
    parsed_tables = []
    for raw_table in parser.tables:
        if not raw_table:
            continue
        if len(raw_table) > 1:
            headers = [h if h else f"col_{idx}" for idx, h in enumerate(raw_table[0])]
            rows = []
            for row in raw_table[1:]:
                row_dict = {}
                for idx, val in enumerate(row):
                    header = headers[idx] if idx < len(headers) else f"col_{idx}"
                    row_dict[header] = val
                if row_dict:
                    rows.append(row_dict)
            parsed_tables.append({"headers": headers, "rows": rows, "raw_rows": raw_table})
        else:
            parsed_tables.append({"headers": raw_table[0], "rows": [], "raw_rows": raw_table})

    clean_text = " ".join(parser.clean_text)
    return {
        "clean_text": clean_text[:10000],  # bounded text for LLM ingestion
        "tables": parsed_tables,
        "forms": parser.forms,
        "summary_stats": {
            "tables_found": len(parsed_tables),
            "forms_found": len(parser.forms),
            "text_length": len(clean_text),
        },
    }
