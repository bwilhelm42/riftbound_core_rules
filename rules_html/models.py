import re
from dataclasses import dataclass, field
from html import escape


@dataclass
class Node:
    rule_id: str | None
    text: str
    font_size: float
    children: list["Node"] = field(default_factory=list)

    def label(self) -> str:
        if self.rule_id:
            return f"{self.rule_id} {self.text}"
        return self.text

    def html_label(self) -> str:
        if self.rule_id:
            return (
                f"<span class='rule-id'>{escape(self.rule_id)}</span>"
                f"<span class='delimiter'>&#124;</span>"
                f"<span class='rule-text'>{escape(self.text)}</span>"
            )
        return f"<span class='rule-text'>{escape(self.text)}</span>"

    def copy_text(self) -> str:
        if self.rule_id:
            return f"{self.rule_id} {self.text}"
        return self.text

    def anchor_id(self) -> str:
        if self.rule_id:
            return f"rule-{self.rule_id.lower().replace('.', '-')}"
        slug = re.sub(r"[^a-z0-9]+", "-", self.text.lower()).strip("-")
        return f"section-{slug or 'root'}"

    def copy_button_html(self) -> str:
        return (
            f"<button class='copy-button' type='button' "
            f"data-copy-text='{escape(self.copy_text())}' "
            f"aria-label='Copy rule text' title='Copy rule text'>"
            f"<span class='copy-icon' aria-hidden='true'></span>"
            f"</button>"
        )
