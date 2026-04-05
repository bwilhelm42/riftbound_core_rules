from html import escape

from .assets import CSS, JS
from .models import Node


def node_to_html(node: Node) -> str:
    if not node.children:
        return (
            f"<div class='leaf' id='{escape(node.anchor_id())}'>"
            f"<span class='label'>{node.html_label()}</span>"
            f"{node.copy_button_html()}"
            f"</div>"
        )

    html = f"<details open id='{escape(node.anchor_id())}'>"
    html += (
        f"<summary><span class='label'>{node.html_label()}</span>"
        f"{node.copy_button_html()}</summary>"
    )
    html += "<div class='children'>"
    for child in node.children:
        html += node_to_html(child)
    html += "</div></details>"
    return html


def build_toc(nodes: list[Node], max_depth: int = 1) -> str:
    items: list[str] = []

    def walk(node: Node, depth: int) -> None:
        if node.rule_id and depth <= max_depth:
            items.append(
                f"<a class='toc-link toc-depth-{depth}' href='#{escape(node.anchor_id())}'>"
                f"{escape(node.rule_id)} {escape(node.text)}"
                f"</a>"
            )
        for child in node.children:
            walk(child, depth + 1)

    for node in nodes:
        walk(node, 0)

    return "".join(items)


def build_html(tree: Node) -> str:
    toc_html = build_toc(tree.children)
    rules_html = "".join(node_to_html(child) for child in tree.children)

    return (
        "<!DOCTYPE html>\n"
        "<html>\n"
        "<head>\n"
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        "<title>Riftbound Rules</title>\n"
        "<style>\n"
        f"{CSS}\n"
        "</style>\n"
        "</head>\n"
        "<body>\n"
        "<div class=\"page\">\n"
        "<header class=\"page-header\">\n"
        "    <h1 class=\"page-title\">Riftbound Core Rules</h1>\n"
        "</header>\n"
        "<div class=\"mobile-toolbar sticky-search\">\n"
        "    <div class=\"search-bar\">\n"
        "        <details class=\"toc-mobile\">\n"
        "            <summary class=\"toc-mobile-summary\" aria-label=\"Toggle contents menu\">\n"
        "                <span class=\"hamburger-icon\" aria-hidden=\"true\"></span>\n"
        "            </summary>\n"
        "            <div class=\"toc-mobile-panel\">\n"
        "                <nav class=\"toc-links toc-mobile-links\">\n"
        f"{toc_html}\n"
        "                </nav>\n"
        "            </div>\n"
        "        </details>\n"
        "        <label for=\"rule-search-mobile\">Search rules</label>\n"
        "        <div class=\"search-input-shell\">\n"
        "            <input id=\"rule-search-mobile\" class=\"rule-search-input\" type=\"search\" placeholder=\"Try: conquer, chosen champion, discard...\" />\n"
        "            <span class=\"search-shortcut\"></span>\n"
        "        </div>\n"
        "        <div class=\"search-nav\">\n"
        "            <button class=\"search-nav-button search-prev\" type=\"button\" aria-label=\"Previous match\" title=\"Previous match\">&#8593;</button>\n"
        "            <button class=\"search-nav-button search-next\" type=\"button\" aria-label=\"Next match\" title=\"Next match\">&#8595;</button>\n"
        "        </div>\n"
        "    </div>\n"
        "</div>\n"
        "<div class=\"layout\">\n"
        "<aside class=\"toc-sidebar\">\n"
        "    <nav class=\"toc-links\">\n"
        f"{toc_html}\n"
        "    </nav>\n"
        "</aside>\n"
        "<section class=\"content\">\n"
        "<div class=\"search-bar sticky-search\">\n"
        "    <label for=\"rule-search-desktop\">Search rules</label>\n"
        "    <div class=\"search-input-shell\">\n"
        "        <input id=\"rule-search-desktop\" class=\"rule-search-input\" type=\"search\" placeholder=\"Try: conquer, chosen champion, discard...\" />\n"
        "        <span class=\"search-shortcut\"></span>\n"
        "    </div>\n"
        "    <div class=\"search-nav\">\n"
        "        <button class=\"search-nav-button search-prev\" type=\"button\" aria-label=\"Previous match\" title=\"Previous match\">&#8593;</button>\n"
        "        <button class=\"search-nav-button search-next\" type=\"button\" aria-label=\"Next match\" title=\"Next match\">&#8595;</button>\n"
        "    </div>\n"
        "    <div class=\"search-status\">Showing all rules</div>\n"
        "</div>\n"
        "<main class=\"rules-tree\">\n"
        f"{rules_html}\n"
        "</main>\n"
        "</section>\n"
        "</div>\n"
        "</div>\n"
        "<script>\n"
        f"{JS}\n"
        "</script>\n"
        "</body>\n"
        "</html>"
    )
