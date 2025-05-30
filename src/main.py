import sys
import os
import argparse
import glob
import time  # time.sleepを使用するために追加
from tqdm import tqdm
from pdf_extractor import extract_text, extract_images
from markdown_writer import write_markdown
from translator import translate_text

def process_pdf(input_pdf, output_dir, image_dir, llm_provider, model_name, force_overwrite=False):
    """単一のPDFファイルを処理する関数"""
    print(f"PDFファイル '{input_pdf}' の処理を開始します...")
    
    # 出力ファイル名を入力PDFの名前に基づいて自動生成
    pdf_base = os.path.splitext(os.path.basename(input_pdf))[0]
    output_md = os.path.join(output_dir, f"{pdf_base}.md")
    
    # 既存の.mdファイルがあるかチェック
    if os.path.exists(output_md) and not force_overwrite:
        print(f"スキップ: 出力先に既に '{pdf_base}.md' が存在します。上書きするには --force オプションを使用してください。")
        return output_md
    
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
    all_headers = []  # すべてのヘッダーを保持するリスト
    
    for i, page in enumerate(tqdm(pages, desc="翻訳処理中", unit="ページ")):
        page_info = {'current': i+1, 'total': total_pages}
            
        # 前のページのヘッダー情報を使用して翻訳
        try:
            translated_text, headers = translate_text(
                page, 
                page_info=page_info, 
                llm_provider=llm_provider, 
                model_name=model_name,
                previous_headers=all_headers
            )
            translated_pages.append(translated_text)
            # 新しいヘッダーを追加
            all_headers.extend(headers)
        except Exception as e:
            error_msg = f"ページ {page_info['current']}/{page_info['total']} の翻訳に失敗しました: {str(e)}"
            tqdm.write(f"\n❌ {error_msg}")
            # エラーメッセージを翻訳結果として追加
            translated_pages.append(f"## 翻訳エラー\n\n{error_msg}\n\n---\n\n**原文:**\n\n{page}")
            continue
    
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
    parser.add_argument('-f', '--force', help='既存のMarkdownファイルが存在する場合も強制的に上書きする', action='store_true')

    args = parser.parse_args()
    
    # 起動メッセージ表示
    print("PDFTranslate2md を起動中...")
    print(f"使用するAIプロバイダー: {args.provider}")
    
    # モデル名の表示
    if args.model_name:
        print(f"モデル: {args.model_name}")
    
    # 使用するAIプロバイダーが正しいかどうかを検証
    valid_providers = ["gemini", "openai", "claude", "anthropic"]
    if args.provider not in valid_providers:
        print(f"エラー: 無効なAIプロバイダーです: {args.provider}")
        print(f"有効なプロバイダー: {', '.join(valid_providers)}")
        return

    # 入力パスを取得
    input_path = args.input
    # LLM設定
    llm_provider = args.provider
    model_name = args.model_name
    # 強制上書きオプション
    force_overwrite = args.force

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
    skipped_files = []
    
    # 入力パスがディレクトリかファイルかを判断
    if os.path.isdir(input_path):
        # ディレクトリ内のすべてのPDFファイルを処理
        pdf_files = glob.glob(os.path.join(input_path, "*.pdf"))
        if not pdf_files:
            print(f"エラー: ディレクトリ '{input_path}' にPDFファイルが見つかりませんでした。")
            return
        
        print(f"ディレクトリ '{input_path}' 内の {len(pdf_files)} 個のPDFファイルを処理します...")
        
        for pdf_file in pdf_files:
            pdf_base = os.path.splitext(os.path.basename(pdf_file))[0]
            output_md = os.path.join(output_dir, f"{pdf_base}.md")
            
            # 既存の.mdファイルがあるかチェック
            if os.path.exists(output_md) and not force_overwrite:
                print(f"スキップ: 出力先に既に '{pdf_base}.md' が存在します。")
                skipped_files.append(output_md)
                continue
                
            output_md = process_pdf(pdf_file, output_dir, image_dir, llm_provider, model_name, force_overwrite)
            processed_files.append(output_md)
            
        if processed_files:
            print(f"\n処理完了: {len(processed_files)}個のファイルが作成されました:")
            for file in processed_files:
                print(f"- {file}")
        
        if skipped_files:
            print(f"\nスキップされたファイル: {len(skipped_files)}個")
            print("スキップされたファイルを処理するには --force オプションを使用してください。")
    else:
        # 単一のPDFファイルを処理
        if not input_path.lower().endswith('.pdf'):
            print(f"エラー: 入力ファイル '{input_path}' はPDFファイルではありません。")
            return
        
        pdf_base = os.path.splitext(os.path.basename(input_path))[0]
        output_md = os.path.join(output_dir, f"{pdf_base}.md")
        
        # 既存の.mdファイルがあるかチェック
        if os.path.exists(output_md) and not force_overwrite:
            print(f"スキップ: 出力先に既に '{pdf_base}.md' が存在します。上書きするには --force オプションを使用してください。")
            return
            
        output_md = process_pdf(input_path, output_dir, image_dir, llm_provider, model_name, force_overwrite)
        processed_files.append(output_md)
    
    print(f"\n出力ディレクトリ: {output_dir}")
    print(f"画像ディレクトリ: {image_dir}")

if __name__ == "__main__":
    main()