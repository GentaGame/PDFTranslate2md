import os
import time
import re
from dotenv import load_dotenv
import google.generativeai as genai
import openai
import anthropic
import backoff
import tenacity
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# タイムアウトとリトライの設定
DEFAULT_TIMEOUT = 300  # デフォルトタイムアウト (秒)
MAX_RETRIES = 2        # 最大リトライ回数

# Gemini APIの設定
genai.configure(api_key=GEMINI_API_KEY)

# OpenAIとAnthropicクライアント設定
# OpenAI APIクライアントを初期化（新しい形式）
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY, timeout=DEFAULT_TIMEOUT)
anthropic_client = anthropic.Client(api_key=ANTHROPIC_API_KEY, timeout=DEFAULT_TIMEOUT)

def clean_markdown_headers(text: str) -> str:
    """
    既存のMarkdownヘッダーのレベルを数字パターンに合わせて修正する関数
    既にヘッダー記号(#)がついている行のみを対象とします
    
    例: '# 3.1 手法' → '## 3.1 手法' (ドットが1つなので##に修正)
    例: '### 2 方法' → '# 2 方法' (ドットがないので#に修正)
    
    Args:
        text: 整形する翻訳済みテキスト
    Returns:
        整形後のテキスト
    """
    lines = text.split('\n')
    processed_lines = []
    
    # 数字とドットのパターンを検出する正規表現
    # 例: "1", "1.2", "1.2.3" などにマッチ
    section_pattern = r'^(\d+(\.\d+)*)\s'
    
    for line in lines:
        trimmed_line = line.lstrip()
        
        # 既存のヘッダー行のみを処理
        if trimmed_line.startswith('#'):
            # ヘッダー記号を削除してテキスト部分を取得
            header_text = re.sub(r'^#+\s*', '', trimmed_line)
            
            # ヘッダーテキストの先頭に数字パターンがあるかチェック
            match = re.match(section_pattern, header_text)
            
            if match:
                # 数字パターンが見つかった場合
                section_num = match.group(1)
                # ドットの数をカウントしてヘッダーレベルを決定 (ドット数+1)
                header_level = section_num.count('.') + 1
                # ヘッダーマーカーの作成（例: ###）
                header_marker = '#' * header_level
                # 新しいヘッダー記号を追加
                formatted_line = f"{header_marker} {header_text}"
                processed_lines.append(formatted_line)
            else:
                # 数字パターンがない場合はそのまま
                processed_lines.append(line)
        else:
            # ヘッダー行でない場合はそのまま
            processed_lines.append(line)
    
    return '\n'.join(processed_lines)

@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type((openai.APIError, openai.APITimeoutError, anthropic.APIError, ConnectionError, TimeoutError)),
    reraise=True
)
def call_llm_with_retry(llm_provider, model_name, prompt):
    """
    リトライ機能を持つLLM呼び出し関数
    
    Args:
        llm_provider: 使用するLLMプロバイダー
        model_name: 使用するモデル名
        prompt: 送信するプロンプト
        
    Returns:
        LLMからの応答テキスト
    """
    try:
        if llm_provider == "gemini":
            model = genai.GenerativeModel(model_name, generation_config={"temperature": 0.0})
            response = model.generate_content(prompt)
            return response.text
        elif llm_provider == "openai":
            response = openai_client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            return response.choices[0].message.content
        elif llm_provider in ("claude", "anthropic"):
            response = anthropic_client.completions.create(
                model=model_name,
                prompt=anthropic.HUMAN_PROMPT + prompt + anthropic.AI_PROMPT,
                max_tokens_to_sample=10000,
                temperature=0.0
            )
            return response.completion
        else:
            raise ValueError(f"Unknown llm_provider: {llm_provider}")
    except Exception as e:
        print(f"  ! API呼び出しエラー (リトライします): {str(e)}")
        raise e

def translate_text(text: str, target_lang: str = "ja", page_info=None, llm_provider: str = "gemini", model_name: str = None) -> str:
    """
    Translate the given text to the target language using the specified LLM provider.
    APIキーは.envから読み込み、google-generativeai、OpenAI、Anthropicライブラリを使用して翻訳を実行する。
    
    Args:
        text: 翻訳するテキスト
        target_lang: 翻訳先の言語
        page_info: {'current': 現在のページ番号, 'total': 合計ページ数} の形式の辞書
        llm_provider: 使用するLLMプロバイダー ("gemini", "openai", "claude", "anthropic")
        model_name: 使用するモデル名（省略時はデフォルト値を使用）
    """
    try:
        # テキストの文字数を取得
        char_count = len(text)
        
        # モデルとプロンプト準備
        # デフォルトモデル名決定
        if model_name is None:
            if llm_provider == "gemini":
                model_name = "gemini-2.0-flash"
            elif llm_provider == "openai":
                model_name = "gpt-4o"
            elif llm_provider in ("claude", "anthropic"):
                model_name = "claude-3.5-sonnet"

        # 翻訳リクエスト用のプロンプト
        prompt = f"""あなたに渡すのは論文pdfの1ページを抽出したものです。次の文章を{target_lang}語に翻訳してください。
翻訳した文章のみを返してください。原文に忠実に翻訳し、自分で文章を足したりスキップしたりはしないでください。専門用語は無理に日本語にせず英単語、カタカナのままでもOKです。

Markdownとして体裁を整えてください。特にヘッダーは以下のルールで変換してください：
- 見出しレベルはMarkdownで表現してください
- '1 はじめに'→'# 1 はじめに' (数字を含めて変換)
- '2.1 関連研究'→'## 2.1 関連研究' (数字を含めて変換)
- '3.1.2 実験方法'→'### 3.1.2 実験方法' (数字を含めて変換)
- Markdownはコードブロックに入れないで、そのまま返してください

つまり、見出しの階層は以下のルールで決定します：
- 1段階(section)なら'#'（例：1、2、3→# 1、# 2、# 3）
- 2段階(subsection)なら'##'（例：1.1、2.1、3.1→## 1.1、## 2.1、## 3.1）
- 3段階（subsubsection）なら'###'（例：1.1.1、2.1.1、3.1.1→### 1.1.1、### 2.1.1、### 3.1.1）

翻訳対象：
{text}"""
        # LLMプロバイダーを使用してリクエスト（リトライ機能付き）
        start_time = time.time()
        
        # リトライ機能付き呼び出し
        result = call_llm_with_retry(llm_provider, model_name, prompt)
        
        # ヘッダーの整形処理を適用
        result = clean_markdown_headers(result)
        
        elapsed_time = time.time() - start_time
        
        # ページ情報があれば、ログに残す（tqdmと競合しないように）
        if page_info:
            print(f"  ✓ ページ {page_info['current']}/{page_info['total']} ({char_count}文字) - {elapsed_time:.1f}秒で翻訳完了")
        
        return result
    except Exception as e:
        error_msg = f"翻訳エラー: {str(e)}"
        print(error_msg)
        return f"翻訳エラーが発生しました: {error_msg}"

if __name__ == "__main__":
    sample_text = "Hello, world!"
    translated = translate_text(sample_text, "ja", llm_provider="openai")
    print("Translated text:", translated)