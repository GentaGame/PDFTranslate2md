import PyPDF2
import os
import fitz  # PyMuPDF

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
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pdf_extractor.py <pdf_path>")
    else:
        pdf_path = sys.argv[1]
        pages = extract_text(pdf_path)
        for i, page_text in enumerate(pages, start=1):
            print(f"--- Page {i} ---")
            print(page_text)