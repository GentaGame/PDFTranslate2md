import sys
import os
from pdf_extractor import extract_text
from markdown_writer import write_markdown

def main():
    if len(sys.argv) != 3:
        print("Usage: python main.py <input_pdf_path> <output_md_path>")
        sys.exit(1)
    
    # 入力ファイルパスを絶対パスに変換
    input_pdf = sys.argv[1]
    if not os.path.isabs(input_pdf):
        input_pdf = os.path.abspath(input_pdf)
    
    # 出力ファイルパスを絶対パスに変換
    output_md = sys.argv[2]
    if not os.path.isabs(output_md):
        output_md = os.path.abspath(output_md)
    
    # 入力ファイルが存在するか確認
    if not os.path.exists(input_pdf):
        print(f"Error: Input PDF file '{input_pdf}' does not exist")
        sys.exit(1)
        
    pages = extract_text(input_pdf)
    write_markdown(output_md, pages)
    print(f"Markdown file created: {output_md}")

if __name__ == "__main__":
    main()