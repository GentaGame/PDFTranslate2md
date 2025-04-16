import sys
from tqdm import tqdm
from pdf_extractor import extract_text
from markdown_writer import write_markdown
from translator import translate_text

def main():
    if len(sys.argv) != 3:
        print("Usage: python main.py <input_pdf_path> <output_md_path>")
        sys.exit(1)
    input_pdf = sys.argv[1]
    output_md = sys.argv[2]
    
    print(f"PDFファイル '{input_pdf}' からテキストを抽出中...")
    pages = extract_text(input_pdf)
    total_pages = len(pages)
    print(f"合計 {total_pages} ページが抽出されました。翻訳を開始します...")
    
    # Translate each page's text using Gemini API with progress bar
    translated_pages = []
    for i, page in enumerate(tqdm(pages, desc="翻訳処理中", unit="ページ")):
        page_info = {'current': i+1, 'total': total_pages}
        translated_pages.append(translate_text(page, page_info=page_info))
    
    print("\n翻訳完了。Markdownファイルに書き出しています...")
    write_markdown(output_md, translated_pages)
    print(f"処理完了: Markdownファイルが作成されました: {output_md}")

if __name__ == "__main__":
    main()