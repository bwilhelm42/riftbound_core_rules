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

    def anchor_id(self):
        if self.rule_id:
            return f"rule-{self.rule_id.lower().replace('.', '-')}"
        slug = re.sub(r"[^a-z0-9]+", "-", self.text.lower()).strip("-")
        return f"section-{slug or 'root'}"


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
            f"</div>"
        )

    html = f"<details open id='{escape(node.anchor_id())}'>"
    html += f"<summary><span class='label'>{node.html_label()}</span></summary>"
    for child in node.children:
        html += node_to_html(child)
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
    font-family: Georgia, "Iowan Old Style", "Palatino Linotype", serif;
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
.toc {
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
    top: 14px;
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
.search-bar.search-hidden-bar {
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
    border-left: 1px solid rgba(184, 171, 149, 0.35);
    padding-left: 14px;
}
details > details,
details > .leaf { margin-left: 1.6em; }
summary, .leaf {
    display: grid;
    grid-template-columns: 1.5em minmax(0, 1fr);
    align-items: start;
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
}
.rule-id {
    color: var(--accent);
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
summary::-webkit-details-marker { display: none; }
summary::before, .leaf::before {
    display: block;
    width: 1.25em;
    color: var(--accent);
    font-family: "Trebuchet MS", "Avenir Next", sans-serif;
    font-size: 0.9rem;
    line-height: 1.6;
}
summary::before { content: "▾"; }
details:not([open]) > summary::before { content: "▸"; }
.leaf::before { content: ""; }
@media (max-width: 760px) {
    body {
        padding: 18px 12px 32px;
    }
    .layout {
        grid-template-columns: 1fr;
    }
    .toc {
        position: static;
        max-height: none;
        order: 2;
    }
    .search-bar {
        top: 8px;
        flex-wrap: wrap;
    }
    .search-status {
        width: 100%;
    }
    .rules-tree {
        padding: 14px;
        border-radius: 18px;
    }
    details {
        padding-left: 10px;
    }
    details > details,
    details > .leaf {
        margin-left: 1em;
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
<div class="layout">
<aside class="toc">
    <h2 class="toc-title">Contents</h2>
    <nav class="toc-links">
"""
    html += build_toc(tree.children)
    html += """
    </nav>
</aside>
<section class="content">
<div class="search-bar">
    <label for="rule-search">Search rules</label>
    <input id="rule-search" type="search" placeholder="Try: conquer, chosen champion, discard..." />
    <div id="search-status" class="search-status">Showing all rules</div>
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
const searchInput = document.getElementById("rule-search");
const searchStatus = document.getElementById("search-status");
const nodes = Array.from(document.querySelectorAll("details, .leaf"));
const detailNodes = Array.from(document.querySelectorAll("details"));
const textNodes = Array.from(document.querySelectorAll(".rule-text"));
const tocLinks = Array.from(document.querySelectorAll(".toc-link"));
const searchBar = document.querySelector(".search-bar");
let activeMatchIndex = -1;
let currentMatches = [];
let lastScrollY = window.scrollY;

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
    const barHeight = searchBar.offsetHeight + 28;
    const nearTop = currentScrollY < barHeight;
    const scrollingUp = currentScrollY <= lastScrollY;

    searchBar.classList.toggle(
        "search-hidden-bar",
        !nearTop && !scrollingUp
    );

    lastScrollY = currentScrollY;
}

function updateSearch() {
    const rawQuery = searchInput.value.trim();
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
        searchStatus.textContent = "Showing all rules";
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

    searchStatus.textContent = matchCount
        ? `${matchCount} matching rule${matchCount === 1 ? "" : "s"}`
        : "No matching rules";

    setActiveMatch(0);
}

searchInput.addEventListener("input", updateSearch);
searchInput.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") {
        return;
    }

    event.preventDefault();
    stepActiveMatch(event.shiftKey ? -1 : 1);
});
textNodes.forEach((node) => {
    node.dataset.originalText = node.innerHTML;
});
tocLinks.forEach((link) => {
    link.addEventListener("click", () => {
        tocLinks.forEach((item) => item.classList.remove("toc-link-active"));
        link.classList.add("toc-link-active");
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
        if (!searchInput.value.trim()) {
            detail.dataset.userOpen = detail.open ? "true" : "false";
        }
    });
});
window.addEventListener("scroll", updateActiveTocLink, { passive: true });
window.addEventListener("scroll", updateSearchBarVisibility, { passive: true });
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
