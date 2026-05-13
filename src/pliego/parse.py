"""Markdown source → IR. Built on markdown-it-py token streams."""
from __future__ import annotations

import yaml
from markdown_it import MarkdownIt
from mdit_py_plugins.front_matter import front_matter_plugin

from .config import DocConfig
from .doc import (
    BlockQuote,
    BulletList,
    CodeBlock,
    Document,
    Emphasis,
    Figure,
    HorizontalRule,
    Image,
    InlineCode,
    Link,
    ListItem,
    OrderedList,
    Paragraph,
    Section,
    Strong,
    Table,
    TableCell,
    TableRow,
    Text,
)


def _make_parser() -> MarkdownIt:
    md = MarkdownIt("commonmark", {"breaks": False, "html": False})
    md.use(front_matter_plugin)
    md.enable("table")
    return md


def parse(source: str) -> Document:
    """Parse Markdown source (with required frontmatter) into a Document IR.

    v0.1 supports only: frontmatter, h1 sections, paragraphs of plain text.
    Anything else raises a ``NotImplementedError`` pointing at the roadmap.
    """
    md = _make_parser()
    tokens = md.parse(source)

    if not tokens or tokens[0].type != "front_matter":
        raise ValueError("pliego requires YAML frontmatter (title + date).")

    frontmatter_raw = tokens[0].content
    frontmatter = yaml.safe_load(frontmatter_raw) or {}
    config = DocConfig.from_frontmatter(frontmatter)

    body_tokens = tokens[1:]
    children = _parse_blocks(body_tokens)
    return Document(config=config, children=children)


def _parse_blocks(tokens: list) -> list:
    """Walk top-level tokens into a nested Section tree.

    Each heading opens a new Section. Headings at level <= the deepest
    open section's level close opened sections back to the heading's
    parent level before opening the new one. Paragraphs attach to the
    deepest open section; a paragraph before any heading raises
    NotImplementedError.
    """
    blocks: list = []
    section_stack: list[Section] = []

    def container() -> list:
        return section_stack[-1].children if section_stack else blocks

    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t.type == "heading_open":
            level = int(t.tag[1])
            inline_token = tokens[i + 1]
            title_inlines = _parse_inline(inline_token)
            i += 3
            while section_stack and section_stack[-1].level >= level:
                section_stack.pop()
            new_section = Section(level=level, title=title_inlines, children=[])
            container().append(new_section)
            section_stack.append(new_section)
            continue
        if t.type == "paragraph_open":
            inline_token = tokens[i + 1]
            children = _parse_inline(inline_token)
            # Promote a paragraph that is just one Image to a Figure
            if len(children) == 1 and isinstance(children[0], Image):
                img = children[0]
                if not section_stack:
                    raise NotImplementedError(
                        "Figures outside a heading are not supported in pliego v0.3."
                    )
                section_stack[-1].children.append(
                    Figure(src=img.src, alt=img.alt)
                )
                i += 3
                continue
            para = Paragraph(children=children)
            if not section_stack:
                raise NotImplementedError(
                    "Paragraphs outside a heading are not supported in pliego v0.2."
                )
            section_stack[-1].children.append(para)
            i += 3
            continue
        if t.type == "bullet_list_open":
            end_i, items = _parse_list_items(tokens, i + 1)
            bl = BulletList(items=items)
            if not section_stack:
                raise NotImplementedError(
                    "Lists outside a heading are not supported in pliego v0.2."
                )
            section_stack[-1].children.append(bl)
            i = end_i + 1
            continue
        if t.type == "ordered_list_open":
            start = 1
            for k, v in (t.attrs or {}).items():
                if k == "start":
                    start = int(v)
            end_i, items = _parse_list_items(tokens, i + 1)
            ol = OrderedList(items=items, start=start)
            if not section_stack:
                raise NotImplementedError(
                    "Lists outside a heading are not supported in pliego v0.2."
                )
            section_stack[-1].children.append(ol)
            i = end_i + 1
            continue
        if t.type == "blockquote_open":
            end_i = _find_close(tokens, i, "blockquote_open", "blockquote_close")
            inner = tokens[i + 1:end_i]
            bq = BlockQuote(children=_parse_item_blocks(inner))
            if not section_stack:
                raise NotImplementedError(
                    "BlockQuote outside a heading is not supported in pliego v0.2."
                )
            section_stack[-1].children.append(bq)
            i = end_i + 1
            continue
        if t.type == "hr":
            if not section_stack:
                raise NotImplementedError("HR outside a heading.")
            section_stack[-1].children.append(HorizontalRule())
            i += 1
            continue
        if t.type == "fence":
            if not section_stack:
                raise NotImplementedError("Code block outside a heading.")
            section_stack[-1].children.append(
                CodeBlock(text=t.content, language=(t.info or "").strip())
            )
            i += 1
            continue
        if t.type == "code_block":
            if not section_stack:
                raise NotImplementedError("Code block outside a heading.")
            section_stack[-1].children.append(
                CodeBlock(text=t.content, language="")
            )
            i += 1
            continue
        if t.type == "table_open":
            end_i = _find_close(tokens, i, "table_open", "table_close")
            inner = tokens[i + 1:end_i]
            table = _parse_table(inner)
            if not section_stack:
                raise NotImplementedError(
                    "Tables outside a heading are not supported in pliego v0.3."
                )
            section_stack[-1].children.append(table)
            i = end_i + 1
            continue
        raise NotImplementedError(
            f"Markdown construct '{t.type}' is not supported in pliego v0.2. "
            "See the roadmap in the design doc."
        )
    return blocks


def _parse_table(tokens: list) -> Table:
    """Walk the inner tokens of table_open/table_close into a Table IR."""
    header: TableRow | None = None
    body: list[TableRow] = []
    in_head = False
    in_body = False
    current_row_cells: list[TableCell] = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t.type == "thead_open":
            in_head, in_body = True, False
        elif t.type == "thead_close":
            in_head = False
        elif t.type == "tbody_open":
            in_head, in_body = False, True
        elif t.type == "tbody_close":
            in_body = False
        elif t.type == "tr_open":
            current_row_cells = []
        elif t.type == "tr_close":
            row = TableRow(cells=current_row_cells)
            if in_head:
                header = row
            else:
                body.append(row)
            current_row_cells = []
        elif t.type in ("th_open", "td_open"):
            if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                inlines = _parse_inline(tokens[i + 1])
            else:
                inlines = []
            current_row_cells.append(TableCell(children=inlines))
        i += 1
    if header is None:
        header = TableRow(cells=[])
    return Table(header=header, body=body)


def _find_close(tokens: list, open_i: int, open_type: str, close_type: str) -> int:
    """Find the matching close-token index for the open at ``tokens[open_i]``,
    handling nesting."""
    depth = 1
    j = open_i + 1
    while j < len(tokens):
        if tokens[j].type == open_type:
            depth += 1
        elif tokens[j].type == close_type:
            depth -= 1
            if depth == 0:
                return j
        j += 1
    raise ValueError(f"unclosed {open_type}")


def _parse_list_items(tokens: list, start: int) -> tuple[int, list]:
    """Parse tokens between bullet_list_open/ordered_list_open and the
    matching close (exclusive). Returns ``(close_index, [ListItem, ...])``.
    """
    items: list = []
    i = start
    while i < len(tokens):
        t = tokens[i]
        if t.type in ("bullet_list_close", "ordered_list_close"):
            return i, items
        if t.type == "list_item_open":
            depth = 1
            inner: list = []
            j = i + 1
            while j < len(tokens) and depth > 0:
                tj = tokens[j]
                if tj.type == "list_item_open":
                    depth += 1
                elif tj.type == "list_item_close":
                    depth -= 1
                    if depth == 0:
                        break
                inner.append(tj)
                j += 1
            items.append(ListItem(children=_parse_item_blocks(inner)))
            i = j + 1
            continue
        i += 1
    return i, items


def _parse_item_blocks(tokens: list) -> list:
    """Parse a list item's inner tokens into Block nodes (Paragraph,
    nested BulletList/OrderedList, etc.). Tokens are the slice between
    list_item_open and list_item_close (exclusive)."""
    out: list = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t.type == "paragraph_open":
            inline_token = tokens[i + 1]
            children = _parse_inline(inline_token)
            out.append(Paragraph(children=children))
            i += 3
            continue
        if t.type == "bullet_list_open":
            end_i, items = _parse_list_items(tokens, i + 1)
            out.append(BulletList(items=items))
            i = end_i + 1
            continue
        if t.type == "ordered_list_open":
            end_i, items = _parse_list_items(tokens, i + 1)
            out.append(OrderedList(items=items))
            i = end_i + 1
            continue
        if t.type == "blockquote_open":
            end_i = _find_close(tokens, i, "blockquote_open", "blockquote_close")
            inner = tokens[i + 1:end_i]
            out.append(BlockQuote(children=_parse_item_blocks(inner)))
            i = end_i + 1
            continue
        i += 1
    return out


def _parse_inline(inline_token) -> list:
    """Walk markdown-it-py inline children into IR Inline nodes.

    Supports text, strong, emphasis, link, inline code, and soft breaks
    (rendered as spaces).
    """
    out: list = []
    # stack[i] = (kind, parent_list_we_were_appending_to, attrs)
    stack: list[tuple[str, list, dict]] = []
    current = out
    for child in inline_token.children or []:
        t = child.type
        if t == "text":
            current.append(Text(text=child.content))
        elif t == "strong_open":
            new_children: list = []
            stack.append(("strong", current, {}))
            current = new_children
        elif t == "strong_close":
            kind, parent, _ = stack.pop()
            assert kind == "strong"
            parent.append(Strong(children=current))
            current = parent
        elif t == "em_open":
            new_children = []
            stack.append(("em", current, {}))
            current = new_children
        elif t == "em_close":
            kind, parent, _ = stack.pop()
            assert kind == "em"
            parent.append(Emphasis(children=current))
            current = parent
        elif t == "link_open":
            href = ""
            attrs = child.attrs or {}
            for k, v in attrs.items():
                if k == "href":
                    href = v
            new_children = []
            stack.append(("link", current, {"href": href}))
            current = new_children
        elif t == "link_close":
            kind, parent, attrs = stack.pop()
            assert kind == "link"
            parent.append(Link(href=attrs["href"], children=current))
            current = parent
        elif t == "code_inline":
            current.append(InlineCode(text=child.content))
        elif t == "image":
            src = ""
            for k, v in (child.attrs or {}).items():
                if k == "src":
                    src = v
            # markdown-it-py flattens the alt-text content into child.content
            alt = child.content or ""
            current.append(Image(src=src, alt=alt))
        elif t == "softbreak":
            current.append(Text(text=" "))
        else:
            raise NotImplementedError(
                f"Inline construct '{t}' is not supported in pliego v0.2."
            )
    return out
