import os
import time
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini APIの設定
genai.configure(api_key=GEMINI_API_KEY)

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
        
        # APIリクエスト
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        # 翻訳リクエスト用のプロンプト
        prompt = f"次の文章を{target_lang}語に翻訳してください。翻訳のみを返してください。\n#制約\nMarkdownとして体裁を整えてください。ヘッダーは##の階層から始めてください。(すでに#があるところに入れるため)。あなたに渡すのは論文pdfの1ページを出力したものなので、それを前提にヘッダーを組むようにしてください。オリジナルなヘッダーを付け足したらはしなくて良いです。：\n\n{text}"
        
        # 内容の生成リクエスト
        start_time = time.time()
        response = model.generate_content(prompt)
        elapsed_time = time.time() - start_time
        
        # 応答から翻訳テキストを取得
        result = response.text
        
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