import os
import re

def process_references(text: str) -> tuple:
    """
    参考文献セクションを処理し、参考文献の引用番号とそのアンカーを特定します
    
    Args:
        text: マークダウン形式の全テキスト
        
    Returns:
        tuple: (参考文献セクションがあるか, リファレンス番号のリスト, アンカー付き参考文献テキスト)
    """
    # 参考文献セクションを検出するパターン
    # "References", "参考文献", "引用文献" などの見出しを検索
    ref_section_pattern = r'(?i)^#+\s+(References|参考文献|引用文献|Bibliography|文献|引用|References cited).*?$'
    
    # 参考文献の引用パターン [数字] または [数字, 数字, ...]
    ref_pattern = r'\[(\d+(?:,\s*\d+)*)\]'
    
    lines = text.split('\n')
    ref_section_found = False
    ref_section_start = -1
    refs_found = set()
    
    # 参考文献セクションの検出
    for i, line in enumerate(lines):
        if re.search(ref_section_pattern, line):
            ref_section_found = True
            ref_section_start = i
            break
    
    # 参考文献セクションが見つからない場合
    if not ref_section_found:
        return False, [], text
        
    # 参考文献セクションのテキストを取得
    if ref_section_found:
        for i in range(ref_section_start, len(lines)):
            # 参考文献エントリから引用番号を抽出
            ref_match = re.search(r'^\s*\[(\d+)\]', lines[i])
            if ref_match:
                refs_found.add(ref_match.group(1))
    
    if refs_found:
        print(f"検出された参考文献番号: {sorted([int(r) for r in refs_found])}")
    
    # 参考文献セクションにアンカーを追加
    processed_lines = []
    in_ref_section = False
    
    for i, line in enumerate(lines):
        # 参考文献セクションの検出
        if i == ref_section_start:
            in_ref_section = True
            processed_lines.append(line)
            continue
            
        # 参考文献セクション内の処理
        if in_ref_section:
            ref_match = re.search(r'^\s*\[(\d+)\]', line)
            if ref_match:
                ref_num = ref_match.group(1)
                # マークダウン形式のアンカーを設定 (Obsidianで動作)
                processed_line = f'<div id="ref{ref_num}"></div>\n\n{line}'
                processed_lines.append(processed_line)
            else:
                processed_lines.append(line)
        else:
            # 参考文献セクション外はそのまま
            processed_lines.append(line)
            
    return ref_section_found, list(refs_found), '\n'.join(processed_lines)

def add_reference_links(text: str, refs_found: list) -> str:
    """
    本文中の参考文献引用をリンクに変換します
    
    Args:
        text: 元のテキスト
        refs_found: 参考文献セクションで見つかった引用番号のリスト
        
    Returns:
        str: リンクを追加したテキスト
    """
    def replace_ref(match):
        # マッチした部分の全体
        full_match = match.group(0)
        # 括弧内の数字部分
        ref_nums = match.group(1)
        
        # カンマで区切られた複数の引用がある場合（[1, 2, 3]のような形式）
        if ',' in ref_nums:
            nums = [num.strip() for num in ref_nums.split(',')]
            result = '['
            for i, num in enumerate(nums):
                if i > 0:
                    result += ', '
                if num in refs_found:
                    # Obsidianでより確実に動作するリンク形式
                    result += f'[{num}](#ref{num})'
                else:
                    result += num
            result += ']'
            print(f"複数引用変換: {full_match} → {result}")
            return result
        else:
            # 単一の引用の場合
            if ref_nums in refs_found:
                # Obsidianでより確実に動作するリンク形式
                result = f'[[#{ref_nums}|{full_match}]]'
                print(f"単一引用変換: {full_match} → {result}")
                return result
            else:
                return full_match
    
    # 参考文献セクションの前にあるテキストのみを処理（参考文献自体は処理しない）
    ref_section_pattern = r'(?i)^#+\s+(References|参考文献|引用文献|Bibliography|文献|引用|References cited).*?$'
    
    lines = text.split('\n')
    processed_lines = []
    ref_section_reached = False
    
    # 参考文献がある場合、最初にマークダウンの先頭にアンカーリンクを定義
    if refs_found:
        processed_lines.append("<!-- 参考文献アンカーリンク定義 -->")
        for ref in sorted([int(r) for r in refs_found]):
            processed_lines.append(f'<a id="ref{ref}"></a>')
        processed_lines.append("\n")
    
    for line in lines:
        if re.search(ref_section_pattern, line):
            ref_section_reached = True
            processed_lines.append(line)
        elif not ref_section_reached:
            # 参考文献部分に達していなければ、引用をリンクに置き換える
            processed_line = re.sub(r'\[(\d+(?:,\s*\d+)*)\]', replace_ref, line)
            processed_lines.append(processed_line)
        else:
            # 参考文献部分はそのまま（すでにアンカーが追加済み）
            processed_lines.append(line)
    
    return '\n'.join(processed_lines)

def write_markdown(md_path: str, pages: list, image_paths: list = None) -> None:
    """
    Write the list of page texts to a Markdown file.
    Each page is separated by a header indicating the page number.
    
    Args:
        md_path: マークダウンファイルの出力先パス
        pages: ページごとの翻訳済みテキストのリスト
        image_paths: ページごとの画像ファイルパスのリスト（指定された場合）
    """
    # まずは通常通りのマークダウンファイルを作成
    combined_text = ""
    
    with open(md_path, "w", encoding="utf-8") as md_file:
        for i, page in enumerate(pages, start=1):
            # ページ番号のヘッダーを書き込み
            page_header = f"(Page {i})\n\n"
            md_file.write(page_header)
            combined_text += page_header
            
            # 画像がある場合は、マークダウン形式で画像を埋め込む
            if image_paths and i <= len(image_paths):
                # 相対パスに変換
                rel_path = os.path.relpath(image_paths[i-1], os.path.dirname(md_path))
                # 画像タグを書き込み
                img_tag = f"<img src=\"{rel_path}\" width=\"20%\">\n\n"
                md_file.write(img_tag)
                combined_text += img_tag
            
            # 翻訳テキストを書き込み
            md_file.write(page)
            md_file.write("\n\n---\n\n")
            combined_text += page + "\n\n---\n\n"
    
    # 参考文献セクションを処理し、リンクを追加
    has_refs, refs_found, text_with_anchors = process_references(combined_text)
    
    if has_refs and refs_found:
        print(f"参考文献セクションを検出しました。{len(refs_found)}件の引用を処理します。")
        # 参考文献へのリンクを追加
        final_text = add_reference_links(text_with_anchors, refs_found)
        
        # 修正したテキストでファイルを上書き
        with open(md_path, "w", encoding="utf-8") as md_file:
            md_file.write(final_text)
        
        print(f"参考文献のクロスリファレンスを設定しました：{', '.join(refs_found)}")
    else:
        print("参考文献セクションが見つからなかったか、引用が検出されませんでした。")

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