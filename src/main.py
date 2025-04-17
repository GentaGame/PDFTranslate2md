import sys
import os
import argparse
import glob
from tqdm import tqdm
from pdf_extractor import extract_text, extract_images
from markdown_writer import write_markdown
from translator import translate_text

def process_pdf(input_pdf, output_dir, image_dir, llm_provider, model_name):
    """単一のPDFファイルを処理する関数"""
    print(f"PDFファイル '{input_pdf}' の処理を開始します...")
    
    # 出力ファイル名を入力PDFの名前に基づいて自動生成
    pdf_base = os.path.splitext(os.path.basename(input_pdf))[0]
    output_md = os.path.join(output_dir, f"{pdf_base}.md")
    
    # 画像出力ディレクトリの設定
    pdf_image_dir = os.path.join(image_dir, pdf_base)
    os.makedirs(pdf_image_dir, exist_ok=True)
    
    print(f"PDFファイル '{input_pdf}' からテキストを抽出中...")
    pages = extract_text(input_pdf)
    total_pages = len(pages)
    print(f"合計 {total_pages} ページが抽出されました。")
    
    # PDFの各ページを画像として保存
    print(f"PDFから画像を抽出しています... 保存先: {pdf_image_dir}")
    image_paths = extract_images(input_pdf, pdf_image_dir)
    print(f"{len(image_paths)}枚の画像が保存されました: {pdf_image_dir}")
    
    print("翻訳を開始します...")
    # Translate each page's text using LLM API with progress bar
    translated_pages = []
    for i, page in enumerate(tqdm(pages, desc="翻訳処理中", unit="ページ")):
        page_info = {'current': i+1, 'total': total_pages}
        translated_pages.append(
            translate_text(page, page_info=page_info, llm_provider=llm_provider, model_name=model_name)
        )
    
    print("\n翻訳完了。Markdownファイルに書き出しています...")
    write_markdown(output_md, translated_pages, image_paths)
    print(f"処理完了: Markdownファイルが作成されました: {output_md}")
    
    return output_md

def main():
    # コマンドライン引数の処理
    parser = argparse.ArgumentParser(description='PDFから翻訳されたMarkdownファイルを生成するツール')
    parser.add_argument('input', help='入力PDFファイルまたはPDFファイルを含むディレクトリのパス')
    parser.add_argument('-o', '--output-dir', help='出力ディレクトリのパス（指定しない場合、現在のディレクトリが使用されます）')
    parser.add_argument('-i', '--image-dir', help='画像出力ディレクトリ（指定しない場合、出力ディレクトリ内の"images"フォルダが使用されます）')
    parser.add_argument('-p', '--provider', help='使用するLLMプロバイダー（gemini, openai, claude, anthropic）', default='gemini')
    parser.add_argument('-m', '--model-name', help='LLMモデル名（指定しない場合はプロバイダーのデフォルト）')

    args = parser.parse_args()

    # 入力パスを取得
    input_path = args.input
    # LLM設定
    llm_provider = args.provider
    model_name = args.model_name

    # 出力ディレクトリの設定（デフォルトは現在のディレクトリ）
    output_dir = args.output_dir if args.output_dir else os.getcwd()
    os.makedirs(output_dir, exist_ok=True)
    
    # 画像出力ディレクトリの設定
    if args.image_dir:
        image_dir = args.image_dir
    else:
        image_dir = os.path.join(output_dir, "images")
    os.makedirs(image_dir, exist_ok=True)
    
    processed_files = []
    
    # 入力パスがディレクトリかファイルかを判断
    if os.path.isdir(input_path):
        # ディレクトリ内のすべてのPDFファイルを処理
        pdf_files = glob.glob(os.path.join(input_path, "*.pdf"))
        if not pdf_files:
            print(f"エラー: ディレクトリ '{input_path}' にPDFファイルが見つかりませんでした。")
            return
        
        print(f"ディレクトリ '{input_path}' 内の {len(pdf_files)} 個のPDFファイルを処理します...")
        
        for pdf_file in pdf_files:
            output_md = process_pdf(pdf_file, output_dir, image_dir, llm_provider, model_name)
            processed_files.append(output_md)
            
        print(f"\nすべての処理が完了しました。{len(processed_files)}個のファイルが作成されました:")
        for file in processed_files:
            print(f"- {file}")
    else:
        # 単一のPDFファイルを処理
        if not input_path.lower().endswith('.pdf'):
            print(f"エラー: 入力ファイル '{input_path}' はPDFファイルではありません。")
            return
        
        output_md = process_pdf(input_path, output_dir, image_dir, llm_provider, model_name)
        processed_files.append(output_md)
    
    print(f"\n出力ディレクトリ: {output_dir}")
    print(f"画像ディレクトリ: {image_dir}")

if __name__ == "__main__":
    main()