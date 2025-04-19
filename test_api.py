import os
from dotenv import load_dotenv
from google import generativeai as genai

load_dotenv()

# APIキーを取得
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
print(f"APIキーの先頭10文字: {GEMINI_API_KEY[:10]}...")

# Gemini APIの設定
genai.configure(api_key=GEMINI_API_KEY)

try:
    # 利用可能なモデルを表示
    print("利用可能なモデルを取得しています...")
    models = genai.list_models()
    for model in models:
        print(f"モデル名: {model.name}")
    
    # 簡単な翻訳テスト
    print("\n翻訳テスト実行中...")
    # 最新のモデル名を使用
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content("Translate this text to Japanese: Hello, world!")
    print(f"テスト結果: {response.text}")
    
except Exception as e:
    print(f"エラーが発生しました: {str(e)}")