import sys
from pdf_extractor import extract_text
from markdown_writer import write_markdown

def main():
    if len(sys.argv) != 3:
        print("Usage: python main.py <input_pdf_path> <output_md_path>")
        sys.exit(1)
    input_pdf = sys.argv[1]
    output_md = sys.argv[2]
    pages = extract_text(input_pdf)
    write_markdown(output_md, pages)
    print(f"Markdown file created: {output_md}")

if __name__ == "__main__":
    main()