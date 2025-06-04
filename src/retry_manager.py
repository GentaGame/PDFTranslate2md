"""
リトライ管理モジュール

既存のtranslator.pyから複雑なリトライ機能を分離して独立したモジュールとして実装。
tenacityライブラリを使用したリトライ設定、Unicode正規化エラーの自動回復機能、
詳細なエラーログとリトライ情報を提供する。
"""

import time
import requests.exceptions
import http.client
import urllib.error
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from tqdm.auto import tqdm
from unicode_handler import normalize_unicode_text


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


class RetryManager:
    """
    リトライ管理クラス
    
    プロバイダー非依存のリトライロジックを提供し、設定可能なリトライ回数・待機時間、
    エラー種別による適切な処理分岐、進捗表示（tqdm）との連携を行う。
    """
    
    def __init__(self, max_retries: int = 5, multiplier: int = 3, min_wait: int = 10, max_wait: int = 180):
        """
        リトライマネージャーの初期化
        
        Args:
            max_retries: 最大リトライ回数
            multiplier: 指数バックオフの乗数
            min_wait: 最小待機時間（秒）
            max_wait: 最大待機時間（秒）
        """
        self.max_retries = max_retries
        self.multiplier = multiplier
        self.min_wait = min_wait
        self.max_wait = max_wait
        
    def create_retry_decorator(self):
        """
        tenacityを使用したリトライデコレータを作成
        
        Returns:
            retry decorator
        """
        return retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=self.multiplier, min=self.min_wait, max=self.max_wait),
            retry=retry_if_exception_type(RETRY_EXCEPTIONS),
            reraise=True
        )
    
    def get_retry_count(self, func):
        """
        現在のリトライ回数を取得
        
        Args:
            func: リトライデコレータが適用された関数
            
        Returns:
            int: 現在のリトライ回数
        """
        retry_count = 1
        if hasattr(func, 'retry'):
            retry_obj = getattr(func, 'retry')
            if hasattr(retry_obj, 'statistics') and retry_obj.statistics.get('attempt_number') is not None:
                retry_count = retry_obj.statistics.get('attempt_number')
        return retry_count
    
    def handle_http_error(self, e, llm_provider: str, retry_count: int, rate_limiter=None):
        """
        HTTPエラーの処理
        
        Args:
            e: HTTPエラー例外
            llm_provider: LLMプロバイダー名
            retry_count: 現在のリトライ回数
            rate_limiter: レート制限管理オブジェクト（省略可能）
        """
        status_code = e.response.status_code if hasattr(e, 'response') and hasattr(e.response, 'status_code') else 0
        
        # 504エラーや503エラーの場合は特別なエラーとして再発生
        if status_code in [503, 504]:
            error_msg = f"サーバータイムアウトエラー ({status_code}): {str(e)}"
            if retry_count > 1:
                tqdm.write(f"  ! {status_code} タイムアウトエラー (リトライ {retry_count}/{self.max_retries}): {error_msg}")
            else:
                tqdm.write(f"  ! {status_code} タイムアウトエラー: {error_msg}")
            raise HTTPStatusError(status_code, error_msg)
        
        # レート制限エラー (429) の処理
        elif status_code == 429:
            error_msg = f"レート制限エラー (429): {str(e)}"
            
            if rate_limiter:
                # レート制限管理オブジェクトを使用して状態を更新
                rate_limiter.set_rate_limit_hit(llm_provider)
                
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
                rate_limiter.set_waiting_period(llm_provider, wait_time)
                
                tqdm.write(f"  ! レート制限に達しました (リトライ {retry_count}/{self.max_retries}): {wait_time}秒待機します")
                time.sleep(wait_time)  # 明示的な待機
            
            raise HTTPStatusError(429, error_msg)
        
        # その他のHTTPエラー
        error_msg = f"HTTP エラー ({status_code}): {str(e)}"
        if retry_count > 1:
            tqdm.write(f"  ! HTTP エラー (リトライ {retry_count}/{self.max_retries}): {error_msg}")
        else:
            tqdm.write(f"  ! HTTP エラー: {error_msg}")
        raise e
    
    def handle_unicode_error(self, e, prompt: str, api_call_func):
        """
        UnicodeEncodeErrorの処理と自動回復
        
        Args:
            e: UnicodeEncodeError例外
            prompt: 元のプロンプト
            api_call_func: API呼び出し関数（正規化されたプロンプトで再実行用）
            
        Returns:
            API呼び出しの結果または再発生した例外
        """
        error_msg = f"UnicodeEncodeError: {str(e)}"
        tqdm.write(f"  ! Unicode処理エラーが発生しました: {error_msg}")
        
        # プロンプトの再処理を試行
        try:
            tqdm.write(f"  🔧 プロンプトのUnicode正規化を実行中...")
            normalized_prompt, was_modified = normalize_unicode_text(prompt, aggressive=True)
            
            if was_modified:
                tqdm.write(f"  ↻ 正規化されたプロンプトで再試行中...")
                # 正規化されたプロンプトで再度API呼び出し
                return api_call_func(normalized_prompt)
            else:
                tqdm.write(f"  ❓ プロンプトの正規化による変更はありませんでした")
                
        except Exception as retry_error:
            tqdm.write(f"  ! 正規化後の再試行も失敗しました: {str(retry_error)}")
        
        # 最終的にUnicodeEncodeErrorとして再発生
        raise e
    
    def handle_resource_exhausted_error(self, e, llm_provider: str, retry_count: int, rate_limiter=None):
        """
        ResourceExhaustedエラー（レート制限）の処理
        
        Args:
            e: ResourceExhaustedエラー例外
            llm_provider: LLMプロバイダー名
            retry_count: 現在のリトライ回数
            rate_limiter: レート制限管理オブジェクト（省略可能）
        """
        if rate_limiter:
            # レート制限状態を更新
            rate_limiter.set_rate_limit_hit(llm_provider)
            
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
            rate_limiter.set_waiting_period(llm_provider, wait_time)
            
            tqdm.write(f"  ! レート制限エラーが発生しました (リトライ {retry_count}/{self.max_retries}): {wait_time}秒待機します")
            time.sleep(wait_time)  # 明示的な待機
            
        raise HTTPStatusError(429, f"レート制限エラー: {str(e)}")
    
    def handle_deadline_exceeded_error(self, e, retry_count: int):
        """
        DeadlineExceededエラーの処理
        
        Args:
            e: DeadlineExceededエラー例外
            retry_count: 現在のリトライ回数
        """
        error_msg = f"DeadlineExceeded: {str(e)}"
        tqdm.write(f"  ! DeadlineExceededエラーが発生しました (リトライ {retry_count}/{self.max_retries}): {error_msg}")
        raise HTTPStatusError(504, error_msg)
    
    def handle_general_error(self, e, retry_count: int):
        """
        一般的なエラーの処理
        
        Args:
            e: エラー例外
            retry_count: 現在のリトライ回数
        """
        error_type = type(e).__name__
        error_msg = f"{error_type}: {str(e)}"
        
        # IndexErrorの詳細な情報を追加
        if isinstance(e, IndexError):
            import traceback
            tqdm.write(f"  ! IndexError詳細: {traceback.format_exc()}")
        
        # リトライカウントを表示
        if retry_count > 1:
            tqdm.write(f"  ! API呼び出しエラー (リトライ {retry_count}/{self.max_retries}): {error_msg}")
        else:
            tqdm.write(f"  ! API呼び出しエラー: {error_msg}")
        raise e
    
    def handle_retry_exception(self, e, page_info=None, remaining_retries: int = 0):
        """
        リトライ例外の処理
        
        Args:
            e: リトライ対象のエラー例外
            page_info: ページ情報（省略可能）
            remaining_retries: 残りリトライ回数
            
        Returns:
            処理結果またはエラーメッセージ
        """
        if remaining_retries > 0:
            # まだリトライ回数が残っている場合
            page_str = f"ページ {page_info['current']}/{page_info['total']}" if page_info else "現在のページ"
            error_type = type(e).__name__
            
            # DeadlineExceededエラーを特別に処理
            if "DeadlineExceeded" in error_type or "Deadline Exceeded" in str(e) or "504" in str(e):
                tqdm.write(f"  ! {page_str} の翻訳で「DeadlineExceeded」エラーが発生しました。リトライします (残り{remaining_retries}回)")
            # 504エラーを特別に処理
            elif isinstance(e, HTTPStatusError) and e.status_code == 504:
                tqdm.write(f"  ! {page_str} の翻訳で「504 タイムアウトエラー」が発生しました。リトライします (残り{remaining_retries}回)")
            else:
                tqdm.write(f"  ! {page_str} の翻訳で「{error_type}」エラーが発生しました。リトライします (残り{remaining_retries}回): {str(e)}")
            
            # エラーを再発生させてデコレータ側でリトライさせる
            raise
        else:
            # 最大リトライ回数に達した場合
            error_type = type(e).__name__
            error_msg = f"翻訳エラー (最大リトライ回数{self.max_retries}回に達しました): {error_type} - {str(e)}"
            tqdm.write(f"  ✗ {error_msg}")
            return f"翻訳エラーが発生しました: {error_msg}", []