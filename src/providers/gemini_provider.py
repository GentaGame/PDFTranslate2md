"""
Gemini API プロバイダー実装

Google Gemini APIを使用した翻訳処理を提供する。
既存のtranslator.pyからGemini固有の機能を移行し、BaseProviderアーキテクチャに適合させる。
"""

import time
from typing import Dict, Any, Optional
from tqdm.auto import tqdm
import tenacity
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .base_provider import BaseProvider, APIError, HTTPStatusError, RateLimitError
from src.unicode_handler import normalize_unicode_text, validate_text_for_api, detect_surrogate_pairs


class GeminiProvider(BaseProvider):
    """
    Google Gemini APIプロバイダー
    
    Gemini APIを使用してテキスト翻訳を実行する。
    遅延インポートとデバッグログ機能を含む。
    """
    
    def __init__(self, api_key: str, model_name: Optional[str] = None, timeout: int = 500):
        """
        Geminiプロバイダーの初期化
        
        Args:
            api_key: Gemini API キー
            model_name: 使用するモデル名（Noneの場合はデフォルトを使用）
            timeout: タイムアウト時間（秒）
        """
        super().__init__(api_key, model_name, timeout)
        self._genai = None  # 遅延インポート用
        
        # Gemini固有の設定
        self._generation_config = {
            "temperature": 0.0,
            "max_output_tokens": 100000
        }
    
    def get_default_model(self) -> str:
        """
        デフォルトのGeminiモデル名を返す
        
        Returns:
            デフォルトモデル名
        """
        return "gemini-2.5-flash-preview-05-20"
    
    def _initialize_client(self):
        """
        Gemini APIクライアントを遅延初期化する
        """
        if self._genai is None:
            try:
                from google import generativeai as genai
                genai.configure(api_key=self.api_key)
                self._genai = genai
                
                # バージョン情報を取得して表示
                try:
                    import google.generativeai
                    version_info = getattr(google.generativeai, '__version__', 'unknown')
                    tqdm.write(f"Gemini API ({version_info}) を初期化しました")
                except:
                    tqdm.write("Gemini APIを初期化しました")
                    
            except ImportError as e:
                raise APIError(f"Gemini APIライブラリが見つかりません: {e}")
            except Exception as e:
                raise APIError(f"Gemini API初期化エラー: {e}")
    
    def _extract_response_text(self, response) -> str:
        """
        Gemini APIレスポンスからテキストを安全に抽出する
        
        translator.pyのextract_gemini_response_text()関数を移行
        
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
        Gemini APIを使用してテキストを翻訳する
        
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
            # 🔍 DEBUG: API呼び出し前の情報
            tqdm.write(f"  🔍 DEBUG - Gemini API呼び出し:")
            tqdm.write(f"    - model_name: {self.model_name}")
            tqdm.write(f"    - prompt length: {len(prompt)} 文字")
            
            # Gemini APIモデルの作成と呼び出し
            model = self._genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt, generation_config=self._generation_config)
            
            # 🔍 DEBUG: API応答後の情報
            tqdm.write(f"  🔍 DEBUG - Gemini API応答受信:")
            tqdm.write(f"    - response received: {response is not None}")
            
            # レスポンスからテキストを抽出
            return self._extract_response_text(response)
            
        except UnicodeEncodeError as e:
            # UnicodeEncodeError専用の処理
            tqdm.write(f"  ! Unicode処理エラーが発生しました: {str(e)}")
            
            # プロンプトの再処理を試行
            tqdm.write(f"  🔧 プロンプトのUnicode正規化を実行中...")
            normalized_prompt, was_modified = normalize_unicode_text(prompt, aggressive=True)
            
            if was_modified:
                tqdm.write(f"  ↻ 正規化されたプロンプトで再試行中...")
                model = self._genai.GenerativeModel(self.model_name)
                response = model.generate_content(normalized_prompt, generation_config=self._generation_config)
                return self._extract_response_text(response)
            else:
                tqdm.write(f"  ❓ プロンプトの正規化による変更はありませんでした")
                raise e
                
        except Exception as e:
            # エラーハンドリング
            error_type = type(e).__name__
            error_msg = str(e)
            
            # レート制限エラーの処理
            if "ResourceExhausted" in error_type or "ResourceExhausted" in error_msg or "429" in error_msg:
                wait_time = 60 + (getattr(self, '_retry_count', 1) ** 2 * 10)
                self.set_rate_limit_hit(wait_time)
                tqdm.write(f"  ! レート制限に達しました: {wait_time}秒待機します")
                time.sleep(wait_time)
                raise RateLimitError(f"Gemini APIレート制限: {error_msg}")
            
            # その他のエラー
            tqdm.write(f"  ! Gemini API呼び出しエラー ({error_type}): {error_msg}")
            raise APIError(f"Gemini API呼び出しエラー: {error_msg}")
    
    def validate_api_key(self) -> bool:
        """
        Gemini APIキーの有効性を検証する
        
        Returns:
            APIキーが有効な場合はTrue
        """
        try:
            self._initialize_client()
            # 簡単なテスト呼び出しで確認
            model = self._genai.GenerativeModel(self.model_name)
            test_response = model.generate_content(
                "Hello", 
                generation_config={"temperature": 0.0, "max_output_tokens": 10}
            )
            return test_response is not None
        except Exception as e:
            tqdm.write(f"Gemini APIキー検証エラー: {str(e)}")
            return False
    
    def get_rate_limits(self) -> Dict[str, Any]:
        """
        Gemini APIのレート制限設定を取得する
        
        Returns:
            レート制限に関する設定辞書
        """
        return {
            "max_requests_per_minute": 60,  # Gemini APIの一般的な制限
            "max_tokens_per_minute": 1000000,  # 概算値
            "max_requests_per_day": 1500,
            "provider": "gemini"
        }