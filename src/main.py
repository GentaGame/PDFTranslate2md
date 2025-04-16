import sys
import os
from tqdm import tqdm
from pdf_extractor import extract_text, extract_images
from markdown_writer import write_markdown
from translator import translate_text

def main():
    # コマンドライン引数の処理
    if len(sys.argv) < 2:
        print("Usage: python main.py <input_pdf_path> [output_md_path]")
        sys.exit(1)
    
    input_pdf = sys.argv[1]
    
    # 出力ファイル名を入力PDFの名前に基づいて自動生成
    if len(sys.argv) >= 3:
        output_md = sys.argv[2]
    else:
        # 入力PDFのベース名を取得し、拡張子を.mdに変更
        pdf_base = os.path.splitext(os.path.basename(input_pdf))[0]
        output_md = f"{pdf_base}.md"
    
    print(f"PDFファイル '{input_pdf}' からテキストを抽出中...")
    pages = extract_text(input_pdf)
    total_pages = len(pages)
    print(f"合計 {total_pages} ページが抽出されました。")
    
    # PDFの各ページを画像として保存
    print("PDFから画像を抽出しています...")
    output_dir = os.path.join(os.path.dirname(output_md), "images")
    image_paths = extract_images(input_pdf, output_dir)
    print(f"{len(image_paths)}枚の画像が保存されました: {output_dir}")
    
    print("翻訳を開始します...")
    # Translate each page's text using Gemini API with progress bar
    translated_pages = []
    for i, page in enumerate(tqdm(pages, desc="翻訳処理中", unit="ページ")):
        page_info = {'current': i+1, 'total': total_pages}
        translated_pages.append(translate_text(page, page_info=page_info))
    
    print("\n翻訳完了。Markdownファイルに書き出しています...")
    write_markdown(output_md, translated_pages, image_paths)
    print(f"処理完了: Markdownファイルが作成されました: {output_md}")

if __name__ == "__main__":
    main()