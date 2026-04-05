import ast
import re
from pathlib import Path

from .models import Node

DATA_FILE = Path(__file__).resolve().parent.parent / "rules_output.txt"
RULE_PATTERN = re.compile(r"^(\d+(?:\.\d+)*(?:\.[a-z])?)\.?\s+(.*)$", re.IGNORECASE)


def load_data(input_path: Path = DATA_FILE) -> list[tuple[str, int]]:
    with open(input_path, "r", encoding="utf-8") as handle:
        return [
            ast.literal_eval(line.strip())
            for line in handle
            if line.strip()
        ]


def merge_continuation_lines(data: list[tuple[str, int]]) -> list[tuple[str, int]]:
    merged: list[tuple[str, int]] = []

    for text, font_size in data:
        rule_id, _ = parse_line(text)

        if rule_id is None and merged:
            prev_text, prev_size = merged[-1]
            merged[-1] = (prev_text + " " + text.strip(), prev_size)
        else:
            merged.append((text, font_size))

    return merged


def parse_line(text: str) -> tuple[str | None, str]:
    match = RULE_PATTERN.match(text)
    if match:
        return match.group(1), match.group(2)
    return None, text


def rule_depth(rule_id: str | None) -> int:
    if not rule_id:
        return -1
    return rule_id.count(".")


def is_child_rule(parent_id: str | None, child_id: str | None) -> bool:
    if not parent_id or not child_id:
        return False
    return child_id.startswith(parent_id + ".")


def build_tree(data: list[tuple[str, int]]) -> Node:
    root = Node(None, "ROOT", float("inf"))
    stack = [root]

    for raw_text, font_size in data:
        rule_id, text = parse_line(raw_text)
        new_node = Node(rule_id, text, font_size)

        while stack and stack[-1].font_size < font_size:
            stack.pop()

        parent = stack[-1]

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
