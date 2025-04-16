import PyPDF2

def extract_text(pdf_path: str) -> list:
    """
    Extract text from each page in the PDF file and
    return a list of text where each element corresponds to a page.
    """
    pages_text = []
    with open(pdf_path, "rb") as pdf_file:
        reader = PyPDF2.PdfReader(pdf_file)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)
            else:
                pages_text.append("")
    return pages_text

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pdf_extractor.py <pdf_path>")
    else:
        pdf_path = sys.argv[1]
        pages = extract_text(pdf_path)
        for i, page_text in enumerate(pages, start=1):
            print(f"--- Page {i} ---")
            print(page_text)