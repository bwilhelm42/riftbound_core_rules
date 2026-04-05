import ast
import re
from html import escape
from pathlib import Path

# ---------- INPUT ----------
DATA_FILE = Path(__file__).with_name("rules_output.txt")


def load_data(input_path=DATA_FILE):
    with open(input_path, "r", encoding="utf-8") as f:
        return [
            ast.literal_eval(line.strip())
            for line in f
            if line.strip()
        ]


data = load_data()

# ---------- PRE PROCESS -------
def merge_continuation_lines(data):
    merged = []

    for text, font_size in data:
        rule_id, parsed_text = parse_line(text)

        if rule_id is None and merged:
            # Append to previous entry
            prev_text, prev_size = merged[-1]
            merged[-1] = (prev_text + " " + text.strip(), prev_size)
        else:
            merged.append((text, font_size))

    return merged

# ---------- PARSING ----------

rule_pattern = re.compile(r'^(\d+(?:\.\d+)*(?:\.[a-z])?)\.?\s+(.*)$', re.IGNORECASE)

def parse_line(text):
    match = rule_pattern.match(text)
    if match:
        return match.group(1), match.group(2)
    return None, text


def rule_depth(rule_id):
    if not rule_id:
        return -1
    return rule_id.count(".")


# ---------- TREE NODE ----------

class Node:
    def __init__(self, rule_id, text, font_size):
        self.rule_id = rule_id
        self.text = text
        self.font_size = font_size
        self.children = []

    def label(self):
        if self.rule_id:
            return f"{self.rule_id} {self.text}"
        return self.text

    def html_label(self):
        if self.rule_id:
            return (
                f"<span class='rule-id'>{escape(self.rule_id)}</span>"
                f"<span class='delimiter'>&#124;</span>"
                f"<span class='rule-text'>{escape(self.text)}</span>"
            )
        return f"<span class='rule-text'>{escape(self.text)}</span>"

    def copy_text(self):
        if self.rule_id:
            return f"{self.rule_id} {self.text}"
        return self.text

    def anchor_id(self):
        if self.rule_id:
            return f"rule-{self.rule_id.lower().replace('.', '-')}"
        slug = re.sub(r"[^a-z0-9]+", "-", self.text.lower()).strip("-")
        return f"section-{slug or 'root'}"

    def copy_button_html(self):
        return (
            f"<button class='copy-button' type='button' "
            f"data-copy-text='{escape(self.copy_text())}' "
            f"aria-label='Copy rule text' title='Copy rule text'>"
            f"<span class='copy-icon' aria-hidden='true'></span>"
            f"</button>"
        )


# ---------- TREE BUILDING ----------

def build_tree(data):
    root = Node(None, "ROOT", float("inf"))
    stack = [root]

    for raw_text, font_size in data:
        rule_id, text = parse_line(raw_text)
        new_node = Node(rule_id, text, font_size)

        # --- Step 1: FONT hierarchy ---
        while stack and stack[-1].font_size < font_size:
            stack.pop()

        parent = stack[-1]

        # --- Step 2: RULE hierarchy (same font only) ---
        if rule_id:
            while (
                parent.rule_id
                and parent.font_size == font_size
                and not is_child_rule(parent.rule_id, rule_id)
            ):
                stack.pop()
                parent = stack[-1]

        parent.children.append(new_node)
        stack.append(new_node)

    return root

# ---------- HTML GENERATION ----------

def node_to_html(node):
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
    html += "</div>"
    html += "</details>"
    return html


def build_toc(nodes, max_depth=1):
    items = []

    def walk(node, depth):
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

def is_child_rule(parent_id, child_id):
    if not parent_id or not child_id:
        return False
    return child_id.startswith(parent_id + ".")

def build_html(tree):
    html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Riftbound Rules</title>
<style>
:root {
    --page-bg: #f4efe6;
    --surface: rgba(255, 252, 245, 0.94);
    --surface-strong: #fffdf8;
    --border: #d8cfbf;
    --border-strong: #b8ab95;
    --text: #2d261e;
    --muted: #6c6154;
    --accent: #9b5c2e;
    --accent-soft: rgba(155, 92, 46, 0.12);
    --match: #fff1bf;
    --shadow: 0 18px 50px rgba(68, 46, 24, 0.10);
}
* {
    box-sizing: border-box;
}
body {
    font-family: "Charter", "Baskerville", "Palatino Linotype", "Book Antiqua", serif;
    margin: 0;
    padding: 32px 20px 56px;
    color: var(--text);
    background:
        radial-gradient(circle at top, rgba(255, 255, 255, 0.5), transparent 38%),
        linear-gradient(180deg, #f7f2ea 0%, var(--page-bg) 100%);
    line-height: 1.55;
}
.page {
    max-width: 1380px;
    margin: 0 auto;
}
.layout {
    display: grid;
    grid-template-columns: 280px minmax(0, 1fr);
    gap: 24px;
    align-items: start;
}
.mobile-toolbar {
    display: none;
}
.toc-sidebar {
    position: sticky;
    top: 14px;
    max-height: calc(100vh - 28px);
    overflow: auto;
    padding: 18px 16px;
    background: var(--surface);
    border: 1px solid rgba(184, 171, 149, 0.5);
    border-radius: 20px;
    box-shadow: var(--shadow);
}
.toc-title {
    margin: 0 0 12px;
    color: var(--accent);
    font-family: "Trebuchet MS", "Avenir Next", sans-serif;
    font-size: 0.9rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.toc-links {
    display: flex;
    flex-direction: column;
    gap: 6px;
}
.toc-link {
    color: var(--muted);
    text-decoration: none;
    line-height: 1.3;
    padding: 7px 10px;
    border-radius: 10px;
    transition: background-color 140ms ease, color 140ms ease;
}
.toc-link:hover,
.toc-link-active {
    color: var(--text);
    background: rgba(155, 92, 46, 0.08);
}
.toc-depth-1 {
    padding-left: 20px;
    font-size: 0.95rem;
}
.page-header {
    margin-bottom: 18px;
}
.eyebrow {
    margin: 0 0 10px;
    color: var(--accent);
    font-family: "Trebuchet MS", "Avenir Next", sans-serif;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
}
.page-title {
    margin: 0;
    font-family: "Avenir Next Condensed", "Trebuchet MS", "Segoe UI", sans-serif;
    font-size: clamp(2rem, 4vw, 3rem);
    line-height: 1.05;
}
.page-subtitle {
    max-width: 70ch;
    margin: 10px 0 0;
    color: var(--muted);
    font-size: 1rem;
}
.search-bar {
    position: sticky;
    top: 0;
    z-index: 10;
    display: flex;
    gap: 12px;
    align-items: center;
    margin-bottom: 24px;
    padding: 14px 16px;
    background: rgba(255, 251, 244, 0.88);
    border: 1px solid rgba(184, 171, 149, 0.65);
    border-radius: 16px;
    box-shadow: var(--shadow);
    backdrop-filter: blur(10px);
    transition: transform 180ms ease, opacity 180ms ease;
}
.sticky-search.search-hidden-bar {
    opacity: 0;
    transform: translateY(-120%);
    pointer-events: none;
}
.search-bar label {
    font-family: "Trebuchet MS", "Avenir Next", sans-serif;
    font-size: 0.95rem;
    font-weight: 700;
    white-space: nowrap;
}
.search-bar input {
    flex: 1;
    min-width: 220px;
    padding: 10px 12px;
    font-size: 16px;
    color: var(--text);
    background: rgba(255, 255, 255, 0.85);
    border: 1px solid var(--border);
    border-radius: 10px;
    outline: none;
}
.search-bar input:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 4px var(--accent-soft);
}
.search-status {
    color: var(--muted);
    font-size: 14px;
    white-space: nowrap;
}
.rules-tree {
    padding: 22px;
    background: var(--surface);
    border: 1px solid rgba(184, 171, 149, 0.5);
    border-radius: 24px;
    box-shadow: var(--shadow);
}
details {
    margin-left: 0;
}
.children {
    margin-left: 1.6em;
    padding-left: 14px;
    border-left: 1px solid rgba(184, 171, 149, 0.35);
}
summary, .leaf {
    display: grid;
    grid-template-columns: 1.5em minmax(0, 1fr) auto;
    align-items: start;
    column-gap: 10px;
    margin-left: 0;
    padding: 7px 10px;
    border-radius: 10px;
}
summary {
    cursor: pointer;
    margin-bottom: 4px;
    font-weight: 700;
    list-style: none;
    transition: background-color 140ms ease, transform 140ms ease;
}
summary:hover,
.leaf:hover {
    background: rgba(155, 92, 46, 0.06);
}
.label {
    display: block;
    min-width: 0;
    overflow-wrap: anywhere;
}
.copy-button {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    margin-left: auto;
    padding: 0;
    border: 1px solid rgba(184, 171, 149, 0.75);
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.72);
    color: var(--muted);
    cursor: pointer;
    transition: background-color 140ms ease, border-color 140ms ease, color 140ms ease;
}
.copy-button:hover,
.copy-button:focus-visible {
    background: rgba(155, 92, 46, 0.1);
    border-color: rgba(155, 92, 46, 0.5);
    color: var(--accent);
    outline: none;
}
.copy-button[data-copied="true"] {
    background: rgba(155, 92, 46, 0.16);
    border-color: rgba(155, 92, 46, 0.55);
    color: var(--accent);
}
.copy-icon {
    position: relative;
    width: 13px;
    height: 13px;
}
.copy-icon::before,
.copy-icon::after {
    content: "";
    position: absolute;
    border: 1.5px solid currentColor;
    border-radius: 2px;
    background: var(--surface-strong);
}
.copy-icon::before {
    width: 9px;
    height: 9px;
    top: 0;
    left: 3px;
}
.copy-icon::after {
    width: 9px;
    height: 9px;
    top: 3px;
    left: 0;
}
.rule-id {
    color: var(--accent);
    font-family: "Avenir Next", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    letter-spacing: 0.01em;
    font-variant-numeric: tabular-nums;
    font-weight: 700;
}
.delimiter {
    margin: 0 0.45em;
    color: var(--border-strong);
    opacity: 1;
}
.rule-text {
    color: var(--text);
    font-family: "Charter", "Baskerville", "Palatino Linotype", "Book Antiqua", serif;
}
.search-hit {
    background: var(--match);
    box-shadow: inset 0 -1px 0 rgba(181, 140, 47, 0.4);
    border-radius: 0.22em;
    padding: 0 0.08em;
}
.search-hit-active {
    background: #f3b83d;
    box-shadow: 0 0 0 2px rgba(155, 92, 46, 0.18);
}
.search-hidden {
    display: none !important;
}
.rules-tree summary::-webkit-details-marker { display: none; }
.rules-tree summary::before, .leaf::before {
    display: block;
    width: 1.25em;
    color: var(--accent);
    font-family: "Trebuchet MS", "Avenir Next", sans-serif;
    font-size: 0.9rem;
    line-height: 1.6;
}
.rules-tree summary::before { content: "▾"; }
.rules-tree details:not([open]) > summary::before { content: "▸"; }
.leaf::before { content: ""; }
@media (max-width: 980px) {
    body {
        padding: 14px 10px 28px;
    }
    .content > .search-bar.sticky-search {
        display: none;
    }
    .layout {
        grid-template-columns: 1fr;
        gap: 14px;
    }
    .toc-sidebar {
        display: none;
    }
    .mobile-toolbar {
        display: block;
        position: sticky;
        top: 0;
        z-index: 15;
        margin-bottom: 14px;
        transition: transform 180ms ease, opacity 180ms ease;
    }
    .toc-mobile {
        position: relative;
        grid-row: 1;
        grid-column: 1;
    }
    .toc-mobile-summary {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 50px;
        height: 50px;
        padding: 0;
        border: 1px solid rgba(184, 171, 149, 0.65);
        border-radius: 14px;
        background: rgba(255, 251, 244, 0.88);
        box-shadow: var(--shadow);
        backdrop-filter: blur(10px);
        cursor: pointer;
        list-style: none;
    }
    .toc-mobile-summary::-webkit-details-marker {
        display: none;
    }
    .toc-mobile-summary::marker {
        content: "";
    }
    .toc-mobile-summary::before,
    .toc-mobile-summary::after {
        content: "";
    }
    .hamburger-icon,
    .hamburger-icon::before,
    .hamburger-icon::after {
        display: block;
        width: 18px;
        height: 2px;
        border-radius: 999px;
        background: var(--accent);
        transition: transform 140ms ease, opacity 140ms ease;
    }
    .hamburger-icon {
        position: relative;
    }
    .hamburger-icon::before,
    .hamburger-icon::after {
        content: "";
        position: absolute;
        left: 0;
    }
    .hamburger-icon::before {
        top: -6px;
    }
    .hamburger-icon::after {
        top: 6px;
    }
    .toc-mobile-panel {
        position: absolute;
        top: calc(100% + 8px);
        left: 0;
        width: min(92vw, 360px);
        max-height: min(70vh, 560px);
        overflow: auto;
        padding: 10px;
        background: var(--surface);
        border: 1px solid rgba(184, 171, 149, 0.6);
        border-radius: 16px;
        box-shadow: var(--shadow);
    }
    .toc-mobile-title {
        margin: 0 0 8px;
        padding: 4px 6px 0;
        color: var(--accent);
        font-family: "Trebuchet MS", "Avenir Next", sans-serif;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    .toc-mobile-links {
        gap: 4px;
    }
    .toc-mobile-link {
        padding: 10px 12px;
        font-size: 0.96rem;
    }
    .toc-mobile-link.toc-depth-1 {
        padding-left: 18px;
    }
    .search-bar {
        flex: 1 1 auto;
        min-width: 0;
        display: grid;
        grid-template-columns: minmax(0, 1fr);
        gap: 8px;
        margin-bottom: 0;
        padding: 8px;
        border-radius: 14px;
    }
    .search-bar label {
        display: none;
    }
    .search-bar input {
        min-width: 0;
        width: 100%;
        min-height: 50px;
        padding: 0 14px;
        font-size: 16px;
        line-height: 1.2;
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.96);
    }
    .search-status {
        width: 100%;
        font-size: 13px;
        white-space: normal;
    }
    .mobile-toolbar .search-bar {
        position: relative;
        grid-template-columns: auto minmax(0, 1fr);
        align-items: center;
        column-gap: 10px;
    }
    .mobile-toolbar .search-bar input {
        grid-column: 2;
        grid-row: 1;
    }
    .mobile-toolbar .search-status {
        grid-column: 1 / -1;
        grid-row: 2;
    }
    .rules-tree {
        padding: 10px;
        border-radius: 18px;
    }
    summary, .leaf {
        grid-template-columns: 1.25em minmax(0, 1fr) 32px;
        column-gap: 8px;
        padding: 10px 8px;
        align-items: start;
    }
    .rules-tree summary::before,
    .leaf::before {
        width: 1em;
        font-size: 0.82rem;
        line-height: 1.7;
    }
    .copy-button {
        width: 32px;
        height: 32px;
        border-radius: 9px;
    }
    .children {
        margin-left: 0.7em;
        padding-left: 8px;
    }
    .page-header {
        margin-bottom: 12px;
    }
    .eyebrow {
        margin-bottom: 8px;
        font-size: 11px;
        letter-spacing: 0.14em;
    }
    .page-title {
        font-size: clamp(1.55rem, 8vw, 2.15rem);
        line-height: 1.02;
    }
    .page-subtitle {
        margin-top: 8px;
        font-size: 0.96rem;
    }
}
@media (max-width: 560px) {
    body {
        padding: 10px 8px 22px;
    }
    .rules-tree {
        padding: 8px;
        border-radius: 16px;
    }
    .mobile-toolbar {
        top: 0;
        margin-bottom: 12px;
    }
    .toc-mobile-summary {
        width: 46px;
        height: 46px;
        border-radius: 12px;
    }
    .mobile-toolbar .search-bar {
        padding: 7px;
        column-gap: 8px;
    }
    .mobile-toolbar .search-bar input {
        min-height: 46px;
        padding: 0 12px;
    }
    .toc-mobile-panel {
        width: min(94vw, 340px);
        left: 0;
        padding: 8px;
    }
    summary, .leaf {
        grid-template-columns: 1em minmax(0, 1fr) 30px;
        padding: 9px 6px;
    }
    .children {
        margin-left: 0.45em;
        padding-left: 7px;
    }
}
</style>
</head>
<body>
<div class="page">
<header class="page-header">
    <p class="eyebrow">Reference Document</p>
    <h1 class="page-title">Riftbound Core Rules</h1>
    <p class="page-subtitle">Structured rules reference with expandable sections and in-page search for quick lookups.</p>
</header>
<div class="mobile-toolbar sticky-search">
    <div class="search-bar">
        <details class="toc-mobile">
            <summary class="toc-mobile-summary" aria-label="Toggle contents menu">
                <span class="hamburger-icon" aria-hidden="true"></span>
            </summary>
            <div class="toc-mobile-panel">
                <h2 class="toc-mobile-title">Contents</h2>
                <nav class="toc-links toc-mobile-links">
"""
    html += build_toc(tree.children)
    html += """
                </nav>
            </div>
        </details>
        <label for="rule-search-mobile">Search rules</label>
        <input id="rule-search-mobile" class="rule-search-input" type="search" placeholder="Try: conquer, chosen champion, discard..." />
    </div>
</div>
<div class="layout">
<aside class="toc-sidebar">
    <h2 class="toc-title">Contents</h2>
    <nav class="toc-links">
"""
    html += build_toc(tree.children)
    html += """
    </nav>
</aside>
<section class="content">
<div class="search-bar sticky-search">
    <label for="rule-search-desktop">Search rules</label>
    <input id="rule-search-desktop" class="rule-search-input" type="search" placeholder="Try: conquer, chosen champion, discard..." />
    <div class="search-status">Showing all rules</div>
</div>
<main class="rules-tree">
"""
    for child in tree.children:
        html += node_to_html(child)

    html += """
</main>
</section>
</div>
</div>
<script>
const searchInputs = Array.from(document.querySelectorAll(".rule-search-input"));
const searchStatuses = Array.from(document.querySelectorAll(".search-status"));
const nodes = Array.from(document.querySelectorAll(".rules-tree details, .rules-tree .leaf"));
const detailNodes = Array.from(document.querySelectorAll(".rules-tree details"));
const textNodes = Array.from(document.querySelectorAll(".rule-text"));
const tocLinks = Array.from(document.querySelectorAll(".toc-link"));
const tocMobile = document.querySelector(".toc-mobile");
const stickySearchBars = Array.from(document.querySelectorAll(".sticky-search"));
const copyButtons = Array.from(document.querySelectorAll(".copy-button"));
let activeMatchIndex = -1;
let currentMatches = [];
let lastScrollY = window.scrollY;
let copiedButtonTimeout = null;
let isSyncingSearchInputs = false;

function normalizeText(value) {
    return value
        .toLowerCase()
        .normalize("NFKD")
        .replace(/[\\u0300-\\u036f]/g, "")
        .replace(/[^a-z0-9]+/g, " ")
        .trim();
}

function matchesQuery(text, queryTerms) {
    if (!queryTerms.length) {
        return true;
    }

    const normalizedText = normalizeText(text);
    const normalizedQuery = queryTerms.join(" ");
    return normalizedText.includes(normalizedQuery);
}

function clearHighlights() {
    textNodes.forEach((node) => {
        node.innerHTML = node.dataset.originalText;
    });
    currentMatches = [];
    activeMatchIndex = -1;
}

function applyHighlights(query) {
    if (!query) {
        return;
    }

    textNodes.forEach((node) => {
        const originalText = node.dataset.originalText;
        const plainText = node.textContent || "";
        const lowerText = plainText.toLowerCase();
        const lowerQuery = query.toLowerCase();
        let highlighted = "";
        let cursor = 0;
        let matchIndex = lowerText.indexOf(lowerQuery);

        while (matchIndex !== -1) {
            const matchEnd = matchIndex + query.length;
            highlighted += originalText.slice(cursor, matchIndex);
            highlighted += `<mark class='search-hit'>${originalText.slice(matchIndex, matchEnd)}</mark>`;
            cursor = matchEnd;
            matchIndex = lowerText.indexOf(lowerQuery, cursor);
        }

        highlighted += originalText.slice(cursor);
        node.innerHTML = highlighted;
    });

    currentMatches = Array.from(document.querySelectorAll(".search-hit"));
}

function setActiveMatch(index) {
    currentMatches.forEach((match) => {
        match.classList.remove("search-hit-active");
    });

    if (!currentMatches.length) {
        activeMatchIndex = -1;
        return;
    }

    activeMatchIndex = ((index % currentMatches.length) + currentMatches.length) % currentMatches.length;
    const activeMatch = currentMatches[activeMatchIndex];
    activeMatch.classList.add("search-hit-active");
    activeMatch.scrollIntoView({ behavior: "smooth", block: "center" });
}

function stepActiveMatch(direction = 1) {
    if (!currentMatches.length) {
        return;
    }

    if (activeMatchIndex === -1) {
        setActiveMatch(0);
        return;
    }

    setActiveMatch(activeMatchIndex + direction);
}

function updateActiveTocLink() {
    const scrollPosition = window.scrollY + 140;
    let activeId = "";

    nodes.forEach((node) => {
        if (node.offsetTop <= scrollPosition) {
            activeId = node.id || activeId;
        }
    });

    tocLinks.forEach((link) => {
        const isActive = link.getAttribute("href") === `#${activeId}`;
        link.classList.toggle("toc-link-active", isActive);
    });
}

function updateSearchBarVisibility() {
    const currentScrollY = window.scrollY;
    const barHeight = stickySearchBars[0] ? stickySearchBars[0].offsetHeight + 28 : 28;
    const nearTop = currentScrollY < barHeight;
    const scrollingUp = currentScrollY <= lastScrollY;

    stickySearchBars.forEach((bar) => {
        const isMobileToolbar = bar.classList.contains("mobile-toolbar");
        const isVisibleAtWidth = isMobileToolbar ? window.innerWidth <= 980 : window.innerWidth > 980;
        if (!isVisibleAtWidth) {
            bar.classList.remove("search-hidden-bar");
            return;
        }

        bar.classList.toggle("search-hidden-bar", !nearTop && !scrollingUp);
    });

    lastScrollY = currentScrollY;
}

function updateSearch() {
    const activeInput = document.activeElement && document.activeElement.classList.contains("rule-search-input")
        ? document.activeElement
        : searchInputs[0];
    const rawQuery = (activeInput ? activeInput.value : "").trim();
    const queryTerms = normalizeText(rawQuery).split(" ").filter(Boolean);
    let matchCount = 0;

    clearHighlights();

    nodes.forEach((node) => {
        node.classList.remove("search-match", "search-hidden");
    });

    detailNodes.forEach((detail) => {
        if (detail.dataset.userOpen === undefined) {
            detail.dataset.userOpen = detail.open ? "true" : "false";
        }
    });

    if (!queryTerms.length) {
        detailNodes.forEach((detail) => {
            detail.open = detail.dataset.userOpen === "true";
        });
        searchStatuses.forEach((status) => {
            status.textContent = "Showing all rules";
        });
        return;
    }

    applyHighlights(rawQuery);

    nodes.forEach((node) => {
        const label = node.querySelector(".label");
        const isMatch = label && matchesQuery(label.textContent || "", queryTerms);
        if (isMatch) {
            node.classList.add("search-match");
            matchCount += 1;
        }
    });

    nodes.forEach((node) => {
        const hasMatch = node.classList.contains("search-match") || node.querySelector(".search-match");
        if (!hasMatch) {
            node.classList.add("search-hidden");
            if (node.tagName === "DETAILS") {
                node.open = false;
            }
            return;
        }

        if (node.tagName === "DETAILS") {
            node.open = true;
        }
    });

    searchStatuses.forEach((status) => {
        status.textContent = matchCount
            ? `${matchCount} matching rule${matchCount === 1 ? "" : "s"}`
            : "No matching rules";
    });

    setActiveMatch(0);
}

async function copyTextToClipboard(value) {
    if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(value);
        return;
    }

    const helper = document.createElement("textarea");
    helper.value = value;
    helper.setAttribute("readonly", "");
    helper.style.position = "absolute";
    helper.style.left = "-9999px";
    document.body.appendChild(helper);
    helper.select();
    document.execCommand("copy");
    helper.remove();
}

function showCopiedState(button) {
    if (copiedButtonTimeout) {
        window.clearTimeout(copiedButtonTimeout);
    }

    copyButtons.forEach((item) => {
        item.dataset.copied = "false";
        item.setAttribute("title", "Copy rule text");
    });

    button.dataset.copied = "true";
    button.setAttribute("title", "Copied");
    copiedButtonTimeout = window.setTimeout(() => {
        button.dataset.copied = "false";
        button.setAttribute("title", "Copy rule text");
    }, 1200);
}

searchInputs.forEach((input) => {
    input.addEventListener("input", () => {
        if (isSyncingSearchInputs) {
            return;
        }

        isSyncingSearchInputs = true;
        searchInputs.forEach((otherInput) => {
            if (otherInput !== input) {
                otherInput.value = input.value;
            }
        });
        isSyncingSearchInputs = false;
        updateSearch();
    });

    input.addEventListener("keydown", (event) => {
        if (event.key !== "Enter") {
            return;
        }

        event.preventDefault();
        stepActiveMatch(event.shiftKey ? -1 : 1);
    });
});
textNodes.forEach((node) => {
    node.dataset.originalText = node.innerHTML;
});
tocLinks.forEach((link) => {
    link.addEventListener("click", () => {
        tocLinks.forEach((item) => item.classList.remove("toc-link-active"));
        link.classList.add("toc-link-active");
        if (window.innerWidth <= 980 && tocMobile) {
            tocMobile.open = false;
        }
    });
});
copyButtons.forEach((button) => {
    button.dataset.copied = "false";
    button.addEventListener("click", async (event) => {
        event.preventDefault();
        event.stopPropagation();

        try {
            await copyTextToClipboard(button.dataset.copyText || "");
            showCopiedState(button);
        } catch (error) {
            button.setAttribute("title", "Copy failed");
        }
    });
});
detailNodes.forEach((detail) => {
    detail.addEventListener("toggle", () => {
        if (!detail.open) {
            detail.querySelectorAll("details").forEach((childDetail) => {
                childDetail.open = false;
                childDetail.dataset.userOpen = "false";
            });
        }
        if (!searchInputs.some((input) => input.value.trim())) {
            detail.dataset.userOpen = detail.open ? "true" : "false";
        }
    });
});
window.addEventListener("scroll", updateActiveTocLink, { passive: true });
window.addEventListener("scroll", updateSearchBarVisibility, { passive: true });
window.addEventListener("resize", updateSearchBarVisibility, { passive: true });
updateActiveTocLink();
updateSearchBarVisibility();
</script>
</body>
</html>"""
    return html


# ---------- RUN ----------
if __name__ == "__main__":
    cleaned_data = merge_continuation_lines(data)
    tree = build_tree(cleaned_data)
    html_output = build_html(tree)


    with open("output.html", "w", encoding="utf-8") as f:
        f.write(html_output)

    print("HTML file generated: output.html")
