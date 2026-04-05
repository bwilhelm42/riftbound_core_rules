from rules_html import DATA_FILE, build_html, build_tree, load_data, merge_continuation_lines


def main() -> None:
    raw_data = load_data(DATA_FILE)
    cleaned_data = merge_continuation_lines(raw_data)
    tree = build_tree(cleaned_data)
    html_output = build_html(tree)

    with open("output.html", "w", encoding="utf-8") as handle:
        handle.write(html_output)

    print("HTML file generated: output.html")


if __name__ == "__main__":
    main()
