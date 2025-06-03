import os
import time
import re
from dotenv import load_dotenv
# 遅延インポートのためにAPIクライアントのインポートを移動
import tenacity
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests.exceptions
import http.client
import urllib.error
from tqdm.auto import tqdm  # 進捗バーと衝突しない出力用（tqdm.write使用）
from unicode_handler import normalize_unicode_text, validate_text_for_api, detect_surrogate_pairs

# レート制限ステータスを管理するグローバル変数
rate_limit_status = {
    "gemini": {"hit": False, "last_hit_time": 0, "waiting_period": 0},
    "openai": {"hit": False, "last_hit_time": 0, "waiting_period": 0},
    "anthropic": {"hit": False, "last_hit_time": 0, "waiting_period": 0},
    "claude": {"hit": False, "last_hit_time": 0, "waiting_period": 0},
}

# .envファイルの存在確認
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if not os.path.exists(dotenv_path):
    print(f"\n警告: .envファイルが見つかりません。{dotenv_path} に.envファイルを作成してください。")
    print("必要なAPIキーの設定例:")
    print("GEMINI_API_KEY=your_gemini_api_key")
    print("OPENAI_API_KEY=your_openai_api_key")
    print("ANTHROPIC_API_KEY=your_anthropic_api_key\n")

# 環境変数の読み込み
load_dotenv(dotenv_path)

# 環境変数の読み込み
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# タイムアウトとリトライの設定
DEFAULT_TIMEOUT = 500  # デフォルトタイムアウト (秒)
MAX_RETRIES = 5        # 最大リトライ回数（単一のリトライシステムに統合）

# APIクライアントとモデル（遅延インポート用）
genai = None
openai_client = None
anthropic_client = None

# 例外をまとめたクラス定義（HTTPエラーを含む）
class APIError(Exception):
    """APIエラーの基底クラス"""
    pass

class HTTPStatusError(APIError):
    """HTTPステータスエラー"""
    def __init__(self, status_code, message=None):
        self.status_code = status_code
        self.message = message or f"HTTPステータスエラー: {status_code}"
        super().__init__(self.message)

# リトライ対象のエラー種類を定義
RETRY_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    requests.exceptions.RequestException,
    requests.exceptions.HTTPError,
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    http.client.HTTPException,
    urllib.error.HTTPError,
    urllib.error.URLError,
    HTTPStatusError,
    APIError,
    UnicodeEncodeError,  # Unicode処理エラーを追加
    # Google APIの特定エラーを追加
    Exception  # DeadlineExceededを含むすべての例外をキャッチ
)

def extract_gemini_response_text(response) -> str:
    """
    Gemini APIレスポンスからテキストを安全に抽出するヘルパー関数
    
    Args:
        response: Gemini APIのレスポンスオブジェクト
        
    Returns:
        抽出されたテキスト
        
    Raises:
        APIError: テキストの抽出に失敗した場合
    """
    try:
        # 🔍 DEBUG: Gemini APIレスポンスの詳細ログ
        tqdm.write(f"  🔍 DEBUG - Gemini APIレスポンス調査:")
        tqdm.write(f"    - response type: {type(response)}")
        tqdm.write(f"    - hasattr candidates: {hasattr(response, 'candidates')}")
        
        if hasattr(response, 'candidates'):
            tqdm.write(f"    - candidates type: {type(response.candidates)}")
            tqdm.write(f"    - candidates length: {len(response.candidates) if response.candidates else 'None'}")
            if response.candidates and len(response.candidates) > 0:
                tqdm.write(f"    - candidate[0] type: {type(response.candidates[0])}")
        
        # 1. candidates構造をまず確認（最も一般的）
        if hasattr(response, 'candidates') and response.candidates and len(response.candidates) > 0:
            tqdm.write(f"  🔍 DEBUG - candidates配列にアクセス中... 長さ: {len(response.candidates)}")
            
            try:
                candidate = response.candidates[0]
                tqdm.write(f"  🔍 DEBUG - candidate[0]取得成功, type: {type(candidate)}")
            except IndexError as idx_err:
                tqdm.write(f"  ❌ DEBUG - candidates[0]でIndexError: {str(idx_err)}")
                raise APIError(f"Gemini APIのcandidates配列が空です - IndexError: {str(idx_err)}")
            
            if hasattr(candidate, 'content') and candidate.content:
                tqdm.write(f"  🔍 DEBUG - content存在確認, type: {type(candidate.content)}")
                if hasattr(candidate.content, 'parts') and candidate.content.parts and len(candidate.content.parts) > 0:
                    tqdm.write(f"  🔍 DEBUG - parts配列にアクセス中... 長さ: {len(candidate.content.parts)}")
                    
                    try:
                        part = candidate.content.parts[0]
                        tqdm.write(f"  🔍 DEBUG - parts[0]取得成功, type: {type(part)}")
                    except IndexError as idx_err:
                        tqdm.write(f"  ❌ DEBUG - parts[0]でIndexError: {str(idx_err)}")
                        raise APIError(f"Gemini APIのparts配列が空です - IndexError: {str(idx_err)}")
                    
                    if hasattr(part, 'text') and part.text:
                        tqdm.write(f"  ✅ DEBUG - テキスト取得成功, 長さ: {len(part.text)}")
                        return part.text
                    else:
                        tqdm.write(f"  ⚠️ DEBUG - parts[0].textが空またはなし")
                else:
                    tqdm.write(f"  ⚠️ DEBUG - partsが空またはなし")
            else:
                tqdm.write(f"  ⚠️ DEBUG - contentが空またはなし")
        else:
            tqdm.write(f"  ⚠️ DEBUG - candidatesが空またはなし")
        
        # 2. 直接text属性をチェック
        if hasattr(response, 'text') and response.text:
            return response.text
        
        # 3. parts属性を直接チェック（fallback）
        if hasattr(response, 'parts') and response.parts and len(response.parts) > 0:
            if hasattr(response.parts[0], 'text') and response.parts[0].text:
                return response.parts[0].text
        
        # 4. レスポンスをより詳細に調査
        tqdm.write("  ! Gemini APIレスポンスの構造を詳細調査中...")
        
        # responseの属性をデバッグ出力
        response_attrs = [attr for attr in dir(response) if not attr.startswith('_')]
        tqdm.write(f"  Debug - 利用可能な属性: {response_attrs}")
        
        # 各属性の値を確認
        for attr in ['candidates', 'parts', 'text']:
            if hasattr(response, attr):
                attr_value = getattr(response, attr)
                tqdm.write(f"  Debug - {attr}: {type(attr_value)} - {str(attr_value)[:100]}...")
        
        # 最後の手段として空でないテキストを探す
        if hasattr(response, 'candidates') and response.candidates:
            for i, candidate in enumerate(response.candidates):
                try:
                    if hasattr(candidate, 'content') and candidate.content:
                        if hasattr(candidate.content, 'parts') and candidate.content.parts:
                            for j, part in enumerate(candidate.content.parts):
                                if hasattr(part, 'text') and part.text and part.text.strip():
                                    tqdm.write(f"  ✓ 候補{i}のパート{j}からテキストを取得")
                                    return part.text
                except (IndexError, AttributeError) as inner_error:
                    tqdm.write(f"  Debug - 候補{i}処理エラー: {str(inner_error)}")
                    continue
        
        # まだ見つからない場合は他の属性を確認
        for attr_name in ['text', '_result', 'result']:
            if hasattr(response, attr_name):
                attr_value = getattr(response, attr_name)
                if attr_value and str(attr_value).strip():
                    tqdm.write(f"  ✓ {attr_name}属性からテキストを取得")
                    return str(attr_value)
        
        # どの方法でも取得できない場合はエラー
        raise APIError("Gemini APIからの応答に有効なコンテンツが含まれていません")
        
    except IndexError as idx_error:
        # 🔍 IndexErrorの詳細な診断情報を追加
        import traceback
        tqdm.write(f"  ❌ CRITICAL - Gemini APIレスポンス処理でIndexError発生:")
        tqdm.write(f"    - エラー詳細: {str(idx_error)}")
        tqdm.write(f"    - スタックトレース:")
        for line in traceback.format_exc().split('\n'):
            if line.strip():
                tqdm.write(f"      {line}")
        
        # レスポンスオブジェクトの詳細情報を出力
        tqdm.write(f"  🔍 レスポンスオブジェクトの緊急診断:")
        try:
            tqdm.write(f"    - response.__dict__: {response.__dict__ if hasattr(response, '__dict__') else 'なし'}")
        except:
            tqdm.write(f"    - response.__dict__取得失敗")
        
        raise APIError(f"Gemini APIからの応答の処理中にIndexErrorが発生しました: {str(idx_error)}")
    except Exception as other_error:
        tqdm.write(f"  ! レスポンス処理で予期しないエラー: {str(other_error)}")
        raise APIError(f"Gemini APIレスポンス処理エラー: {str(other_error)}")

def extract_headers(text: str) -> list:
    """
    Markdownテキストからヘッダー（# で始まる行）を抽出する関数
    
    Args:
        text: ヘッダーを抽出するMarkdownテキスト
        
    Returns:
        抽出されたヘッダーのリスト
    """
    headers = []
    for line in text.split('\n'):
        stripped_line = line.strip()
        if stripped_line.startswith('#'):
            headers.append(stripped_line)
    return headers

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
    wait=wait_exponential(multiplier=3, min=10, max=180),  # さらに長いバックオフを設定
    retry=retry_if_exception_type(RETRY_EXCEPTIONS),
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
    # リトライカウントを取得
    retry_count = 1
    if hasattr(call_llm_with_retry, 'retry'):
        retry_obj = getattr(call_llm_with_retry, 'retry')
        if hasattr(retry_obj, 'statistics') and retry_obj.statistics.get('attempt_number') is not None:
            retry_count = retry_obj.statistics.get('attempt_number')
    
    try:
        if llm_provider == "gemini":
            # 必要なときにだけGemini APIをインポート
            global genai
            if genai is None:
                from google import generativeai as genai
                genai.configure(api_key=GEMINI_API_KEY)
                # バージョン情報を取得
                try:
                    import google.generativeai
                    version_info = getattr(google.generativeai, '__version__', 'unknown')
                    tqdm.write(f"Gemini API ({version_info}) を初期化しました")
                except:
                    tqdm.write("Gemini APIを初期化しました")
            
            # 新しいGenerativeModelインターフェースを使用
            # 🔍 DEBUG: API呼び出し前の情報
            tqdm.write(f"  🔍 DEBUG - Gemini API呼び出し:")
            tqdm.write(f"    - model_name: {model_name}")
            tqdm.write(f"    - prompt length: {len(prompt)} 文字")
            
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt, generation_config={"temperature": 0.0, "max_output_tokens": 10000})
            
            # 🔍 DEBUG: API応答後の情報
            tqdm.write(f"  🔍 DEBUG - Gemini API応答受信:")
            tqdm.write(f"    - response received: {response is not None}")
            
            # ヘルパー関数を使用してレスポンスからテキストを安全に抽出
            return extract_gemini_response_text(response)
        elif llm_provider == "openai":
            # 必要なときにだけOpenAI APIをインポート
            global openai_client
            if openai_client is None:
                import openai
                openai_client = openai.OpenAI(api_key=OPENAI_API_KEY, timeout=DEFAULT_TIMEOUT)
                tqdm.write("OpenAI APIを初期化しました")
                
            response = openai_client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            
            # レスポンスの検証
            if not response.choices or len(response.choices) == 0:
                raise APIError("OpenAI APIからの応答にchoicesが含まれていません")
            
            if not hasattr(response.choices[0], 'message') or not hasattr(response.choices[0].message, 'content'):
                raise APIError("OpenAI APIからの応答の形式が不正です")
            
            return response.choices[0].message.content
        elif llm_provider in ("claude", "anthropic"):
            # 必要なときにだけAnthropic APIをインポート
            global anthropic_client
            if anthropic_client is None:
                import anthropic
                anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, timeout=DEFAULT_TIMEOUT)
                tqdm.write("Anthropic APIを初期化しました")
                
            response = anthropic_client.messages.create(
                model=model_name,
                max_tokens=10000,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # レスポンスの検証
            if not hasattr(response, 'content') or not response.content or len(response.content) == 0:
                raise APIError("Anthropic APIからの応答にcontentが含まれていません")
            
            # content[0]が存在するかチェック
            if not hasattr(response.content[0], 'text'):
                raise APIError("Anthropic APIからの応答の形式が不正です")
            
            return response.content[0].text
        else:
            raise ValueError(f"Unknown llm_provider: {llm_provider}")
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if hasattr(e, 'response') and hasattr(e.response, 'status_code') else 0
        
        # 504エラーや503エラーの場合は特別なエラーとして再発生
        if status_code in [503, 504]:
            error_msg = f"サーバータイムアウトエラー ({status_code}): {str(e)}"
            # リトライカウントを表示
            if retry_count > 1:
                tqdm.write(f"  ! {status_code} タイムアウトエラー (リトライ {retry_count}/{MAX_RETRIES}): {error_msg}")
            else:
                tqdm.write(f"  ! {status_code} タイムアウトエラー: {error_msg}")
            raise HTTPStatusError(status_code, error_msg)
        
        # レート制限エラー (429) の処理
        elif status_code == 429:
            error_msg = f"レート制限エラー (429): {str(e)}"
            
            # グローバルレート制限状態を更新
            rate_limit_status[llm_provider]["hit"] = True
            rate_limit_status[llm_provider]["last_hit_time"] = time.time()
            
            # レスポンスから遅延時間情報を取得（あれば）
            retry_delay = None
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                try:
                    error_json = e.response.json()
                    if 'retry_delay' in error_json:
                        retry_seconds = error_json['retry_delay'].get('seconds', 0)
                        if retry_seconds > 0:
                            retry_delay = retry_seconds
                except:
                    pass
            
            # APIが推奨する待機時間があればそれを使用、なければ独自の計算式
            if retry_delay:
                wait_time = retry_delay + 10  # APIの推奨+余裕
            else:
                # より長い待機時間を設定（リトライ回数に応じて指数的に増加）
                wait_time = 60 + (retry_count * retry_count * 10)
            
            # 待機時間を記録
            rate_limit_status[llm_provider]["waiting_period"] = wait_time
            
            tqdm.write(f"  ! レート制限に達しました (リトライ {retry_count}/{MAX_RETRIES}): {wait_time}秒待機します")
            time.sleep(wait_time)  # 明示的な待機
            raise HTTPStatusError(429, error_msg)
        
        # その他のHTTPエラー
        error_msg = f"HTTP エラー ({status_code}): {str(e)}"
        if retry_count > 1:
            tqdm.write(f"  ! HTTP エラー (リトライ {retry_count}/{MAX_RETRIES}): {error_msg}")
        else:
            tqdm.write(f"  ! HTTP エラー: {error_msg}")
        raise e
    except UnicodeEncodeError as e:
        # UnicodeEncodeError専用の処理
        error_msg = f"UnicodeEncodeError: {str(e)}"
        tqdm.write(f"  ! Unicode処理エラーが発生しました: {error_msg}")
        
        # プロンプトの再処理を試行
        try:
            tqdm.write(f"  🔧 プロンプトのUnicode正規化を実行中...")
            normalized_prompt, was_modified = normalize_unicode_text(prompt, aggressive=True)
            
            if was_modified:
                tqdm.write(f"  ↻ 正規化されたプロンプトで再試行中...")
                # 正規化されたプロンプトで再度API呼び出し
                if llm_provider == "gemini":
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(normalized_prompt, generation_config={"temperature": 0.0, "max_output_tokens": 10000})
                    
                    # ヘルパー関数を使用してレスポンスからテキストを安全に抽出
                    return extract_gemini_response_text(response)
                elif llm_provider == "openai":
                    response = openai_client.chat.completions.create(
                        model=model_name,
                        messages=[{"role": "user", "content": normalized_prompt}],
                        temperature=0.0
                    )
                    return response.choices[0].message.content
                elif llm_provider in ("claude", "anthropic"):
                    response = anthropic_client.messages.create(
                        model=model_name,
                        max_tokens=10000,
                        temperature=0.0,
                        messages=[{"role": "user", "content": normalized_prompt}]
                    )
                    return response.content[0].text
            else:
                tqdm.write(f"  ❓ プロンプトの正規化による変更はありませんでした")
                
        except Exception as retry_error:
            tqdm.write(f"  ! 正規化後の再試行も失敗しました: {str(retry_error)}")
        
        # 最終的にUnicodeEncodeErrorとして再発生
        raise e
    except Exception as e:
        error_type = type(e).__name__
        error_msg = f"{error_type}: {str(e)}"
        
        # IndexErrorの詳細な情報を追加
        if isinstance(e, IndexError):
            import traceback
            tqdm.write(f"  ! IndexError詳細: {traceback.format_exc()}")
        
        # ResourceExhaustedエラー（レート制限）の処理
        if "ResourceExhausted" in error_type or "ResourceExhausted" in str(e) or "429" in str(e):
            # レート制限状態を更新
            rate_limit_status[llm_provider]["hit"] = True
            rate_limit_status[llm_provider]["last_hit_time"] = time.time()
            
            # レスポンスから遅延時間情報を取得（あれば）
            retry_delay = None
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                try:
                    error_json = e.response.json()
                    if 'retry_delay' in error_json:
                        retry_seconds = error_json['retry_delay'].get('seconds', 0)
                        if retry_seconds > 0:
                            retry_delay = retry_seconds
                except:
                    pass
            
            # 待機時間を設定
            if retry_delay:
                wait_time = retry_delay + 5  # APIが推奨する時間+余裕
            else:
                # より長い待機時間を設定（リトライ回数に応じて増加）
                wait_time = 60 + (retry_count * 20)  
            
            # 待機時間を記録
            rate_limit_status[llm_provider]["waiting_period"] = wait_time
            
            tqdm.write(f"  ! レート制限エラーが発生しました (リトライ {retry_count}/{MAX_RETRIES}): {wait_time}秒待機します")
            time.sleep(wait_time)  # 明示的な待機
            raise HTTPStatusError(429, f"レート制限エラー: {str(e)}")
        
        # DeadlineExceededエラーを特別に処理
        if "DeadlineExceeded" in error_type or "Deadline Exceeded" in str(e) or "504" in str(e):
            tqdm.write(f"  ! DeadlineExceededエラーが発生しました (リトライ {retry_count}/{MAX_RETRIES}): {error_msg}")
            raise HTTPStatusError(504, f"DeadlineExceeded: {str(e)}")
        
        # リトライカウントを表示
        if retry_count > 1:
            tqdm.write(f"  ! API呼び出しエラー (リトライ {retry_count}/{MAX_RETRIES}): {error_msg}")
        else:
            tqdm.write(f"  ! API呼び出しエラー: {error_msg}")
        raise e

@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=4, min=15, max=240),  # さらに長いバックオフを設定
    retry=retry_if_exception_type(RETRY_EXCEPTIONS),
    reraise=True  # エラーを再発生させてメイン処理で捕捉する
)
def translate_text(text: str, target_lang: str = "ja", page_info=None, llm_provider: str = "gemini", model_name: str = None, previous_headers=None) -> tuple:
    """
    Translate the given text to the target language using the specified LLM provider.
    APIキーは.envから読み込み、google-generativeai、OpenAI、Anthropicライブラリを使用して翻訳を実行する。
    
    Args:
        text: 翻訳するテキスト
        target_lang: 翻訳先の言語
        page_info: {'current': 現在のページ番号, 'total': 合計ページ数} の形式の辞書
        llm_provider: 使用するLLMプロバイダー ("gemini", "openai", "claude", "anthropic")
        model_name: 使用するモデル名（省略時はデフォルト値を使用）
        previous_headers: 前のページで使用されたヘッダーのリスト
        
    Returns:
        tuple: (翻訳されたテキスト, 抽出されたヘッダーのリスト)
    """
    try:
        # レート制限状態を確認
        if rate_limit_status[llm_provider]["hit"]:
            current_time = time.time()
            elapsed_since_hit = current_time - rate_limit_status[llm_provider]["last_hit_time"]
            waiting_period = rate_limit_status[llm_provider]["waiting_period"]
            
            # 前回のレート制限からの経過時間が待機時間より少なければ待機
            if elapsed_since_hit < waiting_period:
                remaining_wait = waiting_period - elapsed_since_hit
                if remaining_wait > 0:
                    tqdm.write(f"  ⏱️ 前回のレート制限から {waiting_period}秒経過するまであと{remaining_wait:.1f}秒待機します")
                    time.sleep(remaining_wait)
            else:
                # 待機時間が経過したらレート制限フラグをリセット
                rate_limit_status[llm_provider]["hit"] = False
                tqdm.write(f"  ✓ レート制限の待機時間が経過しました。通常処理を再開します。")
        
        # ページ情報があれば、ログに残す
        if page_info:
            page_msg = f"ページ {page_info['current']}/{page_info['total']} の翻訳を開始"
            tqdm.write(f"  • {page_msg}")
        # APIキーの存在確認
        if llm_provider == "gemini" and not GEMINI_API_KEY:
            return "翻訳エラー: Gemini APIキーが設定されていません。.envファイルにGEMINI_API_KEYを設定してください。", []
        elif llm_provider == "openai" and not OPENAI_API_KEY:
            return "翻訳エラー: OpenAI APIキーが設定されていません。.envファイルにOPENAI_API_KEYを設定してください。", []
        elif llm_provider in ("claude", "anthropic") and not ANTHROPIC_API_KEY:
            return "翻訳エラー: Anthropic APIキーが設定されていません。.envファイルにANTHROPIC_API_KEYを設定してください。", []
        
        # テキストの文字数を取得
        char_count = len(text)
        
        # テキストのUnicode安全性を事前チェック
        is_safe, unicode_error = validate_text_for_api(text)
        if not is_safe:
            tqdm.write(f"  ⚠️ Unicode問題が検出されました: {unicode_error}")
            tqdm.write(f"  🔧 テキストの正規化を実行中...")
            
            # Unicode正規化を適用
            normalized_text, was_modified = normalize_unicode_text(text, aggressive=False)
            
            if was_modified:
                tqdm.write(f"  ✓ Unicode正規化が適用されました")
                text = normalized_text
                char_count = len(text)
                
                # 再度安全性をチェック
                is_safe_after, error_after = validate_text_for_api(text)
                if not is_safe_after:
                    tqdm.write(f"  ⚠️ 積極的な正規化を試行中...")
                    # より積極的な正規化を試行
                    aggressive_text, _ = normalize_unicode_text(text, aggressive=True)
                    text = aggressive_text
                    char_count = len(text)
                    tqdm.write(f"  ✓ 積極的な正規化が完了しました")
            else:
                tqdm.write(f"  ❓ 正規化による変更はありませんでした")
        
        # モデルとプロンプト準備
        # デフォルトモデル名決定
        if model_name is None:
            if llm_provider == "gemini":
                model_name = "gemini-2.5-flash-preview-04-17"  # 利用可能な最新のモデル
            elif llm_provider == "openai":
                model_name = "gpt-4.1"
            elif llm_provider in ("claude", "anthropic"):
                model_name = "claude-3.7-sonnet"

        # 翻訳リクエスト用のプロンプト
        previous_headers_text = ""
        if previous_headers and len(previous_headers) > 0:
            previous_headers_text = "\n以下は、これまでのページで検出されたヘッダーの一覧です。これらとの一貫性を保ったヘッダーに変換してください：\n"
            previous_headers_text += "\n".join(previous_headers)
            previous_headers_text += "\n"
        
        prompt = f"""あなたに渡すのは論文pdfの1ページを抽出したものです。次の文章を{target_lang}語に翻訳してください。
翻訳された文章のみを返してください。原文に忠実に翻訳し、自分で文章を足したりスキップしたりはしないでください。専門用語は無理に日本語にせず英単語、カタカナのままでもOKです。
だ・である調にしてください。

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

---
{previous_headers_text}
---

今回翻訳するページ：
{text}"""
        # リトライカウントの表示
        retry_count = 1
        if hasattr(translate_text, 'retry'):
            retry_obj = getattr(translate_text, 'retry')
            if hasattr(retry_obj, 'statistics') and retry_obj.statistics.get('attempt_number') is not None:
                retry_count = retry_obj.statistics.get('attempt_number')
        if retry_count > 1:
            page_str = f"ページ {page_info['current']}/{page_info['total']}" if page_info else "現在のページ"
            tqdm.write(f"  ↻ {page_str} の翻訳を再試行中 (試行 {retry_count}/{MAX_RETRIES})")
        
        # LLMプロバイダーを使用してリクエスト（リトライ機能付き）
        start_time = time.time()
        
        # リトライ機能付き呼び出し
        result = call_llm_with_retry(llm_provider, model_name, prompt)
        
        # ヘッダーの整形処理を適用
        result = clean_markdown_headers(result)
        
        elapsed_time = time.time() - start_time
        
        # ページ情報があれば、ログに残す（tqdmと競合しないように）
        if page_info:
            if retry_count > 1:
                tqdm.write(f"  ✓ ページ {page_info['current']}/{page_info['total']} ({char_count}文字) - {retry_count}回目の試行で {elapsed_time:.1f}秒で翻訳完了")
            else:
                tqdm.write(f"  ✓ ページ {page_info['current']}/{page_info['total']} ({char_count}文字) - {elapsed_time:.1f}秒で翻訳完了")
        
        return result, extract_headers(result)
    except RETRY_EXCEPTIONS as e:
        # リトライ対象のエラーの場合は再発生させてデコレータにキャッチさせる
        retry_count = 1
        if hasattr(translate_text, 'retry'):
            retry_obj = getattr(translate_text, 'retry')
            if hasattr(retry_obj, 'statistics') and retry_obj.statistics.get('attempt_number') is not None:
                retry_count = retry_obj.statistics.get('attempt_number')
        remaining = MAX_RETRIES - retry_count
        
        if remaining > 0:
            # まだリトライ回数が残っている場合
            page_str = f"ページ {page_info['current']}/{page_info['total']}" if page_info else "現在のページ"
            error_type = type(e).__name__
            
            # DeadlineExceededエラーを特別に処理
            if "DeadlineExceeded" in error_type or "Deadline Exceeded" in str(e) or "504" in str(e):
                tqdm.write(f"  ! {page_str} の翻訳で「DeadlineExceeded」エラーが発生しました。リトライします (残り{remaining}回)")
            # 504エラーを特別に処理
            elif isinstance(e, HTTPStatusError) and e.status_code == 504:
                tqdm.write(f"  ! {page_str} の翻訳で「504 タイムアウトエラー」が発生しました。リトライします (残り{remaining}回)")
            else:
                tqdm.write(f"  ! {page_str} の翻訳で「{error_type}」エラーが発生しました。リトライします (残り{remaining}回): {str(e)}")
            
            # エラーを再発生させてデコレータ側でリトライさせる
            raise
        else:
            # 最大リトライ回数に達した場合
            error_type = type(e).__name__
            error_msg = f"翻訳エラー (最大リトライ回数{MAX_RETRIES}回に達しました): {error_type} - {str(e)}"
            tqdm.write(f"  ✗ {error_msg}")
            return f"翻訳エラーが発生しました: {error_msg}", []
    except Exception as e:
        # リトライ対象外のエラー
        error_type = type(e).__name__
        error_msg = f"翻訳エラー ({error_type}): {str(e)}"
        tqdm.write(f"  ✗ {error_msg}")
        return f"翻訳エラーが発生しました: {error_msg}", []

if __name__ == "__main__":
    sample_text = "Hello, world!"
    translated, headers = translate_text(sample_text, "ja", llm_provider="openai")
    print("Translated text:", translated)
    print("Extracted headers:", headers)