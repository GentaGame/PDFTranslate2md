def write_markdown(md_path: str, pages: list) -> None:
    """
    Write the list of page texts to a Markdown file.
    Each page is separated by a header indicating the page number.
    """
    with open(md_path, "w", encoding="utf-8") as md_file:
        for i, page in enumerate(pages, start=1):
            md_file.write(f"(Page {i})\n")
            md_file.write(page)
            md_file.write("\n\n---\n\n")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python markdown_writer.py <output_md_path> <input_pdf_path>")
    else:
        output_md = sys.argv[1]
        pdf_path = sys.argv[2]
        from pdf_extractor import extract_text
        pages = extract_text(pdf_path)
        write_markdown(output_md, pages)
        print(f"Markdown file has been created: {output_md}")