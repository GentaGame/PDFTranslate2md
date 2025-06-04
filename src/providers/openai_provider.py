"""
OpenAI API プロバイダー実装

OpenAI APIを使用した翻訳処理を提供する。
既存のtranslator.pyからOpenAI固有の機能を移行し、BaseProviderアーキテクチャに適合させる。
"""

import time
from typing import Dict, Any, Optional
from tqdm.auto import tqdm
import tenacity
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .base_provider import BaseProvider, APIError, HTTPStatusError, RateLimitError
from src.unicode_handler import normalize_unicode_text, validate_text_for_api


class OpenAIProvider(BaseProvider):
    """
    OpenAI APIプロバイダー
    
    OpenAI APIを使用してテキスト翻訳を実行する。
    遅延インポートとエラーハンドリング機能を含む。
    """
    
    def __init__(self, api_key: str, model_name: Optional[str] = None, timeout: int = 500):
        """
        OpenAIプロバイダーの初期化
        
        Args:
            api_key: OpenAI API キー
            model_name: 使用するモデル名（Noneの場合はデフォルトを使用）
            timeout: タイムアウト時間（秒）
        """
        super().__init__(api_key, model_name, timeout)
        self._openai_client = None  # 遅延インポート用
        
        # OpenAI固有の設定
        self._generation_config = {
            "temperature": 0.0
        }
    
    def get_default_model(self) -> str:
        """
        デフォルトのOpenAIモデル名を返す
        
        Returns:
            デフォルトモデル名
        """
        return "gpt-4.1"
    
    def _initialize_client(self):
        """
        OpenAI APIクライアントを遅延初期化する
        """
        if self._openai_client is None:
            try:
                import openai
                self._openai_client = openai.OpenAI(api_key=self.api_key, timeout=self.timeout)
                tqdm.write("OpenAI APIを初期化しました")
                    
            except ImportError as e:
                raise APIError(f"OpenAI APIライブラリが見つかりません: {e}")
            except Exception as e:
                raise APIError(f"OpenAI API初期化エラー: {e}")
    
    def _validate_response(self, response) -> str:
        """
        OpenAI APIレスポンスを検証し、テキストを抽出する
        
        Args:
            response: OpenAI APIのレスポンスオブジェクト
            
        Returns:
            抽出されたテキスト
            
        Raises:
            APIError: レスポンスの形式が不正な場合
        """
        # レスポンスの基本検証
        if not response.choices or len(response.choices) == 0:
            raise APIError("OpenAI APIからの応答にchoicesが含まれていません")
        
        # メッセージの存在確認
        if not hasattr(response.choices[0], 'message') or not hasattr(response.choices[0].message, 'content'):
            raise APIError("OpenAI APIからの応答の形式が不正です")
        
        content = response.choices[0].message.content
        if not content:
            raise APIError("OpenAI APIからの応答が空です")
        
        return content
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=3, min=10, max=180),
        retry=retry_if_exception_type((
            ConnectionError, TimeoutError, HTTPStatusError, APIError,
            UnicodeEncodeError, Exception
        )),
        reraise=True
    )
    def translate(self, text: str, prompt: str) -> str:
        """
        OpenAI APIを使用してテキストを翻訳する
        
        Args:
            text: 翻訳対象のテキスト（現在は使用されていない、promptに含まれる）
            prompt: 翻訳プロンプト
            
        Returns:
            翻訳されたテキスト
            
        Raises:
            APIError: API呼び出しでエラーが発生した場合
            RateLimitError: レート制限に達した場合
        """
        # クライアントの初期化
        self._initialize_client()
        
        # レート制限チェック
        if not self.check_rate_limit():
            remaining_time = self._rate_limit_status["waiting_period"] - (
                time.time() - self._rate_limit_status["last_hit_time"]
            )
            raise RateLimitError(f"レート制限中: あと{remaining_time:.1f}秒待機してください")
        
        # テキストの前処理とバリデーション
        is_valid, error_msg = validate_text_for_api(prompt)
        if not is_valid:
            tqdm.write(f"  🔧 プロンプトのUnicode正規化を実行中... 理由: {error_msg}")
            normalized_prompt, was_modified = normalize_unicode_text(prompt, aggressive=True)
            if was_modified:
                tqdm.write(f"  ↻ 正規化されたプロンプトを使用します")
                prompt = normalized_prompt
            else:
                tqdm.write(f"  ❓ プロンプトの正規化による変更はありませんでした")
        
        try:
            # OpenAI API呼び出し
            response = self._openai_client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=self._generation_config["temperature"]
            )
            
            # レスポンスの検証とテキスト抽出
            return self._validate_response(response)
            
        except UnicodeEncodeError as e:
            # UnicodeEncodeError専用の処理
            tqdm.write(f"  ! Unicode処理エラーが発生しました: {str(e)}")
            
            # プロンプトの再処理を試行
            tqdm.write(f"  🔧 プロンプトのUnicode正規化を実行中...")
            normalized_prompt, was_modified = normalize_unicode_text(prompt, aggressive=True)
            
            if was_modified:
                tqdm.write(f"  ↻ 正規化されたプロンプトで再試行中...")
                response = self._openai_client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": normalized_prompt}],
                    temperature=self._generation_config["temperature"]
                )
                return self._validate_response(response)
            else:
                tqdm.write(f"  ❓ プロンプトの正規化による変更はありませんでした")
                raise e
                
        except Exception as e:
            # エラーハンドリング
            error_type = type(e).__name__
            error_msg = str(e)
            
            # HTTPエラーの詳細処理
            if hasattr(e, 'status_code'):
                status_code = e.status_code
                
                # レート制限エラー (429) の処理
                if status_code == 429:
                    retry_count = getattr(self, '_retry_count', 1)
                    wait_time = 60 + (retry_count * retry_count * 10)
                    self.set_rate_limit_hit(wait_time)
                    tqdm.write(f"  ! レート制限に達しました: {wait_time}秒待機します")
                    time.sleep(wait_time)
                    raise RateLimitError(f"OpenAI APIレート制限: {error_msg}")
                
                # その他のHTTPエラー
                elif status_code in [503, 504]:
                    tqdm.write(f"  ! サーバータイムアウトエラー ({status_code}): {error_msg}")
                    raise HTTPStatusError(status_code, f"OpenAI APIサーバーエラー: {error_msg}")
                else:
                    tqdm.write(f"  ! HTTP エラー ({status_code}): {error_msg}")
                    raise HTTPStatusError(status_code, f"OpenAI API HTTPエラー: {error_msg}")
            
            # レート制限関連のエラー（status_codeがない場合）
            elif "rate limit" in error_msg.lower() or "429" in error_msg:
                retry_count = getattr(self, '_retry_count', 1)
                wait_time = 60 + (retry_count * retry_count * 10)
                self.set_rate_limit_hit(wait_time)
                tqdm.write(f"  ! レート制限に達しました: {wait_time}秒待機します")
                time.sleep(wait_time)
                raise RateLimitError(f"OpenAI APIレート制限: {error_msg}")
            
            # その他のエラー
            else:
                tqdm.write(f"  ! OpenAI API呼び出しエラー ({error_type}): {error_msg}")
                raise APIError(f"OpenAI API呼び出しエラー: {error_msg}")
    
    def validate_api_key(self) -> bool:
        """
        OpenAI APIキーの有効性を検証する
        
        Returns:
            APIキーが有効な場合はTrue
        """
        try:
            self._initialize_client()
            # 簡単なテスト呼び出しで確認
            test_response = self._openai_client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "Hello"}],
                temperature=0.0,
                max_tokens=10
            )
            return test_response is not None and len(test_response.choices) > 0
        except Exception as e:
            tqdm.write(f"OpenAI APIキー検証エラー: {str(e)}")
            return False
    
    def get_rate_limits(self) -> Dict[str, Any]:
        """
        OpenAI APIのレート制限設定を取得する
        
        Returns:
            レート制限に関する設定辞書
        """
        return {
            "max_requests_per_minute": 500,  # OpenAI APIの一般的な制限（プランによる）
            "max_tokens_per_minute": 200000,  # 概算値
            "max_requests_per_day": 10000,
            "provider": "openai"
        }