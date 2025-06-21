import os
import logging
from src.unicode_handler import normalize_unicode_text, validate_text_for_api

def write_markdown(md_path: str, pages: list, image_paths: list = None) -> None:
    """
    Write the list of page texts to a Markdown file.
    Each page is separated by a header indicating the page number.
    Unicode検証とエラーハンドリングを含む。
    
    Args:
        md_path: マークダウンファイルの出力先パス
        pages: ページごとの翻訳済みテキストのリスト
        image_paths: ページごとの画像ファイルパスのリスト（指定された場合）
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Markdownファイル出力開始: {md_path}")
    
    unicode_issues_count = 0
    
    try:
        with open(md_path, "w", encoding="utf-8") as md_file:
            for i, page in enumerate(pages, start=1):
                # ページテキストのUnicode検証
                is_safe, error_msg = validate_text_for_api(page)
                if not is_safe:
                    logger.warning(f"ページ {i}: Unicode問題が検出されました - {error_msg}")
                    unicode_issues_count += 1
                    
                    # 正規化を適用
                    normalized_page, was_modified = normalize_unicode_text(page, aggressive=True)
                    if was_modified:
                        logger.info(f"ページ {i}: Unicode正規化が適用されました")
                        page = normalized_page
                    
                # ページ番号のヘッダーを書き込み
                try:
                    md_file.write(f"(Page {i})\n\n")
                except UnicodeEncodeError as e:
                    logger.error(f"ページ {i} ヘッダー書き込みエラー: {e}")
                    md_file.write(f"(Page {i} - Unicode Error)\n\n")
                
                # 画像がある場合は、マークダウン形式で画像を埋め込む
                if image_paths and i <= len(image_paths) and (i-1) < len(image_paths):
                    try:
                        # 相対パスに変換
                        rel_path = os.path.relpath(image_paths[i-1], os.path.dirname(md_path))
                        # 画像タグを書き込み（幅を20%に設定）
                        md_file.write(f"<img src=\"{rel_path}\" width=\"20%\">\n\n")
                    except (UnicodeEncodeError, OSError) as e:
                        logger.error(f"ページ {i} 画像パス書き込みエラー: {e}")
                        md_file.write(f"[Image Error: {rel_path}]\n\n")
                
                # 翻訳テキストを書き込み
                try:
                    md_file.write(page)
                    md_file.write("\n\n---\n\n")
                except UnicodeEncodeError as e:
                    logger.error(f"ページ {i} テキスト書き込みエラー: {e}")
                    # 強制的にUTF-8安全な文字列に変換して書き込み
                    safe_page = page.encode('utf-8', errors='replace').decode('utf-8')
                    md_file.write(safe_page)
                    md_file.write("\n\n---\n\n")
                    
        logger.info(f"Markdownファイル出力完了: {md_path}")
        if unicode_issues_count > 0:
            logger.warning(f"Unicode問題が検出されたページ数: {unicode_issues_count}")
            
    except Exception as e:
        logger.error(f"Markdownファイル書き込み中にエラーが発生しました: {e}")
        raise

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