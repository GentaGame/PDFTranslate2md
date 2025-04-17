import sys
import os
import argparse
from tqdm import tqdm
from pdf_extractor import extract_text, extract_images
from markdown_writer import write_markdown
from translator import translate_text

def main():
    # コマンドライン引数の処理
    parser = argparse.ArgumentParser(description='PDFから翻訳されたMarkdownファイルを生成するツール')
    parser.add_argument('input_pdf', help='入力PDFファイルのパス')
    parser.add_argument('-o', '--output', help='出力Markdownファイルのパス（指定しない場合、入力PDFと同名の.mdファイルが生成されます）')
    parser.add_argument('-i', '--image_dir', help='画像出力ディレクトリ（指定しない場合、出力Markdownと同じディレクトリの"images"フォルダが使用されます）')
    parser.add_argument('-p', '--provider', help='使用するLLMプロバイダー（gemini, openai, claude, anthropic）', default='gemini')
    parser.add_argument('-m', '--model-name', help='LLMモデル名（指定しない場合はプロバイダーのデフォルト）')

    args = parser.parse_args()

    input_pdf = args.input_pdf
    # LLM設定
    llm_provider = args.provider
    model_name = args.model_name

    # 出力ファイル名を入力PDFの名前に基づいて自動生成
    if args.output:
        output_md = args.output
    else:
        # 入力PDFのベース名を取得し、拡張子を.mdに変更
        pdf_base = os.path.splitext(os.path.basename(input_pdf))[0]
        output_md = f"{pdf_base}.md"
    
    # 画像出力ディレクトリの設定
    if args.image_dir:
        output_dir = args.image_dir
    else:
        output_dir = os.path.join(os.path.dirname(output_md), "images")
    
    print(f"PDFファイル '{input_pdf}' からテキストを抽出中...")
    pages = extract_text(input_pdf)
    total_pages = len(pages)
    print(f"合計 {total_pages} ページが抽出されました。")
    
    # PDFの各ページを画像として保存
    print(f"PDFから画像を抽出しています... 保存先: {output_dir}")
    image_paths = extract_images(input_pdf, output_dir)
    print(f"{len(image_paths)}枚の画像が保存されました: {output_dir}")
    
    print("翻訳を開始します...")
    # Translate each page's text using Gemini API with progress bar
    translated_pages = []
    for i, page in enumerate(tqdm(pages, desc="翻訳処理中", unit="ページ")):
        page_info = {'current': i+1, 'total': total_pages}
        translated_pages.append(
            translate_text(page, page_info=page_info, llm_provider=llm_provider, model_name=model_name)
        )
    
    print("\n翻訳完了。Markdownファイルに書き出しています...")
    write_markdown(output_md, translated_pages, image_paths)
    print(f"処理完了: Markdownファイルが作成されました: {output_md}")

if __name__ == "__main__":
    main()