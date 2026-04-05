import pdfplumber
from collections import defaultdict
from contextlib import nullcontext

def extract_lines_with_fontsize(pdf_path, output_path=None, y_tolerance=3):
    results = [] if output_path is None else None

    with pdfplumber.open(pdf_path) as pdf, (
        open(output_path, "w", encoding="utf-8") if output_path else nullcontext()
    ) as output_file:
        x = 0
        for page in pdf.pages:
            chars = page.chars

            # Group characters into lines by their 'top' coordinate
            lines = defaultdict(list)
            for ch in chars:
                # Round the vertical position to group nearby chars
                key = round(ch["top"] / y_tolerance) * y_tolerance
                lines[key].append(ch)

            # Sort lines top-to-bottom
            for _, line_chars in sorted(lines.items(), key=lambda x: x[0]):
                # Sort characters left-to-right
                line_chars.sort(key=lambda c: c["x0"])

                # Reconstruct text
                text = "".join(ch["text"] for ch in line_chars).strip()
                if not text:
                    continue

                # Font size of first visible character
                first_char = next((ch for ch in line_chars if ch["text"].strip()), None)
                font_size = first_char["size"] if first_char else None

                line_result = (text, int(font_size))
                if output_path:
                    output_file.write(f"{line_result!r}\n")
                else:
                    results.append(line_result)
            print("Wrote page: ", x)
            x += 1

    return results


if __name__ == "__main__":
    pdf_file = "/Users/brendanwilhelmsen/Downloads/Riftbound Core Rules RUP3 Staging (1).pdf"
    output_file = "/Users/brendanwilhelmsen/Desktop/rules_output.txt"
    extract_lines_with_fontsize(pdf_file, output_path=output_file)
    print(f"Line data written to: {output_file}")
