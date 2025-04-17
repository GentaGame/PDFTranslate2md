import os

def write_markdown(md_path: str, pages: list, image_paths: list = None) -> None:
    """
    Write the list of page texts to a Markdown file.
    Each page is separated by a header indicating the page number.
    
    Args:
        md_path: マークダウンファイルの出力先パス
        pages: ページごとの翻訳済みテキストのリスト
        image_paths: ページごとの画像ファイルパスのリスト（指定された場合）
    """
    with open(md_path, "w", encoding="utf-8") as md_file:
        for i, page in enumerate(pages, start=1):
            # ページ番号のヘッダーを書き込み
            md_file.write(f"(Page {i})\n\n")
            
            # 画像がある場合は、マークダウン形式で画像を埋め込む
            if image_paths and i <= len(image_paths):
                # 相対パスに変換
                rel_path = os.path.relpath(image_paths[i-1], os.path.dirname(md_path))
                # 画像タグを書き込み（幅を20%に設定）
                md_file.write(f"<img src=\"{rel_path}\" width=\"20%\">\n\n")
            
            # 翻訳テキストを書き込み
            md_file.write(page)
            md_file.write("\n\n---\n\n")

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