"""
Anthropic API プロバイダー実装

Anthropic Claude APIを使用した翻訳処理を提供する。
既存のtranslator.pyからAnthropic固有の機能を移行し、BaseProviderアーキテクチャに適合させる。
"""

import time
from typing import Dict, Any, Optional
from tqdm.auto import tqdm
import tenacity
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .base_provider import BaseProvider, APIError, HTTPStatusError, RateLimitError
from src.unicode_handler import normalize_unicode_text, validate_text_for_api


class AnthropicProvider(BaseProvider):
    """
    Anthropic APIプロバイダー
    
    Anthropic Claude APIを使用してテキスト翻訳を実行する。
    遅延インポートとエラーハンドリング機能を含む。
    """
    
    def __init__(self, api_key: str, model_name: Optional[str] = None, timeout: int = 500):
        """
        Anthropicプロバイダーの初期化
        
        Args:
            api_key: Anthropic API キー
            model_name: 使用するモデル名（Noneの場合はデフォルトを使用）
            timeout: タイムアウト時間（秒）
        """
        super().__init__(api_key, model_name, timeout)
        self._anthropic_client = None  # 遅延インポート用
        
        # Anthropic固有の設定
        self._generation_config = {
            "max_tokens": 100000,
            "temperature": 0.0
        }
    
    def get_default_model(self) -> str:
        """
        デフォルトのAnthropicモデル名を返す
        
        Returns:
            デフォルトモデル名
        """
        return "claude-3-7-sonnet"
    
    def _initialize_client(self):
        """
        Anthropic APIクライアントを遅延初期化する
        """
        if self._anthropic_client is None:
            try:
                import anthropic
                self._anthropic_client = anthropic.Anthropic(api_key=self.api_key, timeout=self.timeout)
                tqdm.write("Anthropic APIを初期化しました")
                    
            except ImportError as e:
                raise APIError(f"Anthropic APIライブラリが見つかりません: {e}")
            except Exception as e:
                raise APIError(f"Anthropic API初期化エラー: {e}")
    
    def _validate_response(self, response) -> str:
        """
        Anthropic APIレスポンスを検証し、テキストを抽出する
        
        Args:
            response: Anthropic APIのレスポンスオブジェクト
            
        Returns:
            抽出されたテキスト
            
        Raises:
            APIError: レスポンスの形式が不正な場合
        """
        # レスポンスの基本検証
        if not hasattr(response, 'content') or not response.content or len(response.content) == 0:
            raise APIError("Anthropic APIからの応答にcontentが含まれていません")
        
        # content[0]が存在するかチェック
        if not hasattr(response.content[0], 'text'):
            raise APIError("Anthropic APIからの応答の形式が不正です")
        
        text_content = response.content[0].text
        if not text_content:
            raise APIError("Anthropic APIからの応答が空です")
        
        return text_content
    
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
        Anthropic APIを使用してテキストを翻訳する
        
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
            # Anthropic API呼び出し
            response = self._anthropic_client.messages.create(
                model=self.model_name,
                max_tokens=self._generation_config["max_tokens"],
                temperature=self._generation_config["temperature"],
                messages=[{"role": "user", "content": prompt}]
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
                response = self._anthropic_client.messages.create(
                    model=self.model_name,
                    max_tokens=self._generation_config["max_tokens"],
                    temperature=self._generation_config["temperature"],
                    messages=[{"role": "user", "content": normalized_prompt}]
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
                    raise RateLimitError(f"Anthropic APIレート制限: {error_msg}")
                
                # その他のHTTPエラー
                elif status_code in [503, 504]:
                    tqdm.write(f"  ! サーバータイムアウトエラー ({status_code}): {error_msg}")
                    raise HTTPStatusError(status_code, f"Anthropic APIサーバーエラー: {error_msg}")
                else:
                    tqdm.write(f"  ! HTTP エラー ({status_code}): {error_msg}")
                    raise HTTPStatusError(status_code, f"Anthropic API HTTPエラー: {error_msg}")
            
            # レート制限関連のエラー（status_codeがない場合）
            elif "rate limit" in error_msg.lower() or "429" in error_msg:
                retry_count = getattr(self, '_retry_count', 1)
                wait_time = 60 + (retry_count * retry_count * 10)
                self.set_rate_limit_hit(wait_time)
                tqdm.write(f"  ! レート制限に達しました: {wait_time}秒待機します")
                time.sleep(wait_time)
                raise RateLimitError(f"Anthropic APIレート制限: {error_msg}")
            
            # その他のエラー
            else:
                tqdm.write(f"  ! Anthropic API呼び出しエラー ({error_type}): {error_msg}")
                raise APIError(f"Anthropic API呼び出しエラー: {error_msg}")
    
    def validate_api_key(self) -> bool:
        """
        Anthropic APIキーの有効性を検証する
        
        Returns:
            APIキーが有効な場合はTrue
        """
        try:
            self._initialize_client()
            # 簡単なテスト呼び出しで確認
            test_response = self._anthropic_client.messages.create(
                model=self.model_name,
                max_tokens=10,
                temperature=0.0,
                messages=[{"role": "user", "content": "Hello"}]
            )
            return test_response is not None and hasattr(test_response, 'content')
        except Exception as e:
            tqdm.write(f"Anthropic APIキー検証エラー: {str(e)}")
            return False
    
    def get_rate_limits(self) -> Dict[str, Any]:
        """
        Anthropic APIのレート制限設定を取得する
        
        Returns:
            レート制限に関する設定辞書
        """
        return {
            "max_requests_per_minute": 50,  # Anthropic APIの一般的な制限
            "max_tokens_per_minute": 40000,  # 概算値
            "max_requests_per_day": 1000,
            "provider": "anthropic"
        }