import PyPDF2
import os
import fitz  # PyMuPDF
import argparse
import logging
from src.unicode_handler import normalize_unicode_text, detect_surrogate_pairs

def extract_text(pdf_path: str) -> list:
    """
    Extract text from each page in the PDF file and
    return a list of text where each element corresponds to a page.
    Unicode文字の正規化処理も含む。
    """
    pages_text = []
    logger = logging.getLogger(__name__)
    
    with open(pdf_path, "rb") as pdf_file:
        reader = PyPDF2.PdfReader(pdf_file)
        total_pages = len(reader.pages)
        logger.info(f"PDFから {total_pages} ページのテキストを抽出開始")
        
        for page_num, page in enumerate(reader.pages, 1):
            text = page.extract_text()
            
            if text:
                # サロゲートペア文字の検出
                if detect_surrogate_pairs(text):
                    logger.warning(f"ページ {page_num}: サロゲートペア文字が検出されました")
                    
                    # Unicode正規化処理
                    normalized_text, was_modified = normalize_unicode_text(text)
                    
                    if was_modified:
                        logger.info(f"ページ {page_num}: Unicode正規化が適用されました")
                        char_count_before = len(text)
                        char_count_after = len(normalized_text)
                        logger.debug(f"文字数: {char_count_before} → {char_count_after}")
                    
                    pages_text.append(normalized_text)
                else:
                    pages_text.append(text)
            else:
                pages_text.append("")
                
    logger.info(f"テキスト抽出完了: {len(pages_text)} ページ")
    return pages_text

def extract_images(pdf_path: str, output_dir: str) -> list:
    """
    Extract each page of the PDF as an image and save them to the output directory.
    Returns a list of image file paths.
    """
    # 保存先ディレクトリが存在しない場合は作成
    os.makedirs(output_dir, exist_ok=True)
    
    # PDFベースファイル名を取得（拡張子なし）
    pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]
    
    # PDFをMuPDFで開く
    pdf_document = fitz.open(pdf_path)
    image_paths = []
    
    # 各ページを画像に変換
    for page_num in range(len(pdf_document)):
        # ページを取得
        page = pdf_document.load_page(page_num)
        
        # 画像ファイル名を生成（例：pdf名_page_1.png）
        image_filename = f"{pdf_basename}_page_{page_num+1}.png"
        image_path = os.path.join(output_dir, image_filename)
        
        # 高品質なレンダリングのためのマトリックス（ズーム値）
        zoom_factor = 2.0  # 解像度を2倍に
        matrix = fitz.Matrix(zoom_factor, zoom_factor)
        
        # ページをピクセルマップとしてレンダリング
        pixmap = page.get_pixmap(matrix=matrix)
        
        # 画像を保存
        pixmap.save(image_path)
        image_paths.append(image_path)
    
    # PDFを閉じる
    pdf_document.close()
    return image_paths

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PDFからテキストと画像を抽出するツール')
    parser.add_argument('pdf_path', help='PDFファイルのパス')
    parser.add_argument('-o', '--output_dir', default='images', help='抽出した画像の保存先ディレクトリ（デフォルト: images）')
    parser.add_argument('-t', '--text_only', action='store_true', help='テキストのみを抽出する場合に指定')
    parser.add_argument('-i', '--images_only', action='store_true', help='画像のみを抽出する場合に指定')
    
    args = parser.parse_args()
    
    # デフォルトでは両方抽出
    extract_text_flag = not args.images_only or args.text_only
    extract_images_flag = not args.text_only or args.images_only
    
    if extract_text_flag:
        print("テキストを抽出中...")
        pages = extract_text(args.pdf_path)
        for i, page_text in enumerate(pages, start=1):
            print(f"--- Page {i} ---")
            print(page_text)
    
    if extract_images_flag:
        print(f"画像を抽出中... 保存先: {args.output_dir}")
        image_paths = extract_images(args.pdf_path, args.output_dir)
        print(f"{len(image_paths)}ページの画像を保存しました。")