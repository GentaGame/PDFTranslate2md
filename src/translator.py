import os
import time
import re
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini APIの設定
genai.configure(api_key=GEMINI_API_KEY)

def clean_markdown_headers(text: str) -> str:
    """
    Markdownのヘッダー形式を整形する関数
    ※数字部分は保持します
    例: '### 3.1 設計' → '### 3.1 設計' (数字はそのまま)
    
    Args:
        text: 整形する翻訳済みテキスト
    Returns:
        整形後のテキスト
    """
    # 見出しを適切に検出するための正規表現を修正
    # パターン: 数字から始まる行を見出しに変換 (例: '3.1 設計' → '### 3.1 設計')
    # ただし、既に '#' で始まる行はそのまま
    
    lines = text.split('\n')
    processed_lines = []
    
    for line in lines:
        processed_lines.append(line)
    
    return '\n'.join(processed_lines)

def translate_text(text: str, target_lang: str = "ja", page_info=None) -> str:
    """
    Translate the given text to the target language using the Gemini API.
    APIキーは.envから読み込み、google-generativeaiライブラリを使用して翻訳を実行する。
    
    Args:
        text: 翻訳するテキスト
        target_lang: 翻訳先の言語
        page_info: {'current': 現在のページ番号, 'total': 合計ページ数} の形式の辞書
    """
    try:
        # テキストの文字数を取得
        char_count = len(text)
        
        # APIリクエスト - temperatureを0に設定
        model = genai.GenerativeModel("gemini-2.0-flash", generation_config={"temperature": 0.0})
        
        # 翻訳リクエスト用のプロンプト
        prompt = f"""あなたに渡すのは論文pdfの1ページを抽出したものです。次の文章を{target_lang}語に翻訳してください。
翻訳した文章のみを返してください。原文に忠実に翻訳し、自分で文章を足したりスキップしたりはしないでください。専門用語は無理に日本語にせず英単語のままでもOKです。

Markdownとして体裁を整えてください。特にヘッダーは以下のルールで変換してください：
- 見出しレベルはMarkdownで表現してください
- '1 はじめに'→'# 1 はじめに' (数字を含めて変換)
- '2.1 関連研究'→'## 2.1 関連研究' (数字を含めて変換)
- '3.1.2 実験方法'→'### 3.1.2 実験方法' (数字を含めて変換)

つまり、見出しの階層は以下のルールで決定します：
- 1段階(section)なら'#'（例：1、2、3→# 1、# 2、# 3）
- 2段階(subsection)なら'##'（例：1.1、2.1、3.1→## 1.1、## 2.1、## 3.1）
- 3段階（subsubsection）なら'###'（例：1.1.1、2.1.1、3.1.1→### 1.1.1、### 2.1.1、### 3.1.1）

翻訳対象：
{text}"""
        # 内容の生成リクエスト
        start_time = time.time()
        response = model.generate_content(prompt)
        elapsed_time = time.time() - start_time
        
        # 応答から翻訳テキストを取得
        result = response.text
        
        # 後処理：見出しの整形（必要に応じて）
        # result = clean_markdown_headers(result)
        
        # ページ情報があれば、ログに残す（tqdmと競合しないように）
        if page_info:
            print(f"  ✓ ページ {page_info['current']}/{page_info['total']} ({char_count}文字) - {elapsed_time:.1f}秒で翻訳完了")
        
        return result
    except Exception as e:
        error_msg = f"翻訳エラー: {str(e)}"
        print(error_msg)
        return "翻訳エラーが発生しました"

if __name__ == "__main__":
    sample_text = "Hello, world!"
    translated = translate_text(sample_text, "ja")
    print("Translated text:", translated)