"""
翻訳サービス層

新しいプロバイダーアーキテクチャを使用した統合された翻訳サービス層。
既存のtranslator.pyから翻訳ロジックを移行し、プロバイダーの管理、
レート制限、リトライ機能、Unicode正規化を統合的に提供する。
"""

import os
import sys
import time
import re
from typing import Optional, Dict, Any, Tuple, List
from dotenv import load_dotenv
from tqdm.auto import tqdm

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 新しいプロバイダーアーキテクチャをインポート
from .providers import (
    create_provider,
    get_supported_providers,
    get_default_model,
    validate_provider_name,
    BaseProvider,
    APIError,
    HTTPStatusError,
    RateLimitError,
    ValidationError
)

# 既存のモジュールをインポート
from .retry_manager import RetryManager, RETRY_EXCEPTIONS
from .rate_limiter import RateLimiter, global_rate_limiter
from src.unicode_handler import normalize_unicode_text, validate_text_for_api


class TranslatorService:
    """
    翻訳サービスクラス
    
    新しいプロバイダーアーキテクチャを使用して翻訳機能を提供する。
    プロバイダーの自動選択、設定管理の一元化、エラーハンドリングの統一、
    レート制限とリトライ機能の統合を行う。
    """
    
    def __init__(self, provider_name: str, model_name: Optional[str] = None, timeout: int = 500):
        """
        翻訳サービスの初期化
        
        Args:
            provider_name: プロバイダー名 ("gemini", "openai", "claude", "anthropic")
            model_name: モデル名（Noneの場合はデフォルトモデルを使用）
            timeout: タイムアウト時間（秒）
            
        Raises:
            ValidationError: プロバイダー名が無効またはAPIキーが設定されていない場合
            ValueError: サポートされていないプロバイダーが指定された場合
        """
        self.provider_name = provider_name.lower().strip()
        self.timeout = timeout
        
        # プロバイダー名の検証
        if not validate_provider_name(self.provider_name):
            supported_providers = ", ".join(get_supported_providers().keys())
            raise ValueError(
                f"サポートされていないプロバイダーです: '{self.provider_name}'\n"
                f"サポートされているプロバイダー: {supported_providers}"
            )
        
        # .envファイルの読み込み
        self._load_environment()
        
        # APIキーの取得と検証
        self.api_key = self._get_api_key()
        if not self.api_key:
            raise ValidationError(f"{self._get_provider_display_name()}のAPIキーが設定されていません。")
        
        # モデル名の設定
        self.model_name = model_name or get_default_model(self.provider_name)
        
        # プロバイダーインスタンスの作成
        self.provider = create_provider(
            provider_name=self.provider_name,
            api_key=self.api_key,
            model_name=self.model_name,
            timeout=self.timeout
        )
        
        # リトライマネージャーとレート制限管理の初期化
        self.retry_manager = RetryManager(max_retries=5, multiplier=3, min_wait=10, max_wait=180)
        self.rate_limiter = global_rate_limiter
        
        tqdm.write(f"翻訳サービスを初期化しました: {self._get_provider_display_name()} ({self.model_name})")
    
    def _load_environment(self):
        """環境変数を読み込む"""
        dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        if not os.path.exists(dotenv_path):
            tqdm.write(f"\n警告: .envファイルが見つかりません。{dotenv_path} に.envファイルを作成してください。")
            tqdm.write("必要なAPIキーの設定例:")
            tqdm.write("GEMINI_API_KEY=your_gemini_api_key")
            tqdm.write("OPENAI_API_KEY=your_openai_api_key")
            tqdm.write("ANTHROPIC_API_KEY=your_anthropic_api_key\n")
        
        load_dotenv(dotenv_path)
    
    def _get_api_key(self) -> Optional[str]:
        """プロバイダーに対応するAPIキーを取得する"""
        key_mapping = {
            "gemini": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "claude": "ANTHROPIC_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY"
        }
        
        env_key = key_mapping.get(self.provider_name)
        if not env_key:
            return None
        
        return os.getenv(env_key)
    
    def _get_provider_display_name(self) -> str:
        """プロバイダーの表示名を取得する"""
        display_names = {
            "gemini": "Gemini API",
            "openai": "OpenAI API",
            "claude": "Claude API",
            "anthropic": "Anthropic API"
        }
        return display_names.get(self.provider_name, self.provider_name.title())
    
    def extract_headers(self, text: str) -> List[str]:
        """
        Markdownテキストからヘッダー（# で始まる行）を抽出する
        
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
    
    def clean_markdown_headers(self, text: str) -> str:
        """
        既存のMarkdownヘッダーのレベルを数字パターンに合わせて修正する
        既にヘッダー記号(#)がついている行のみを対象とする
        
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
    
    def _create_translation_prompt(self, text: str, target_lang: str, previous_headers: Optional[List[str]] = None) -> str:
        """
        翻訳用のプロンプトを作成する
        
        Args:
            text: 翻訳するテキスト
            target_lang: 翻訳先の言語
            previous_headers: 前のページで使用されたヘッダーのリスト
            
        Returns:
            作成されたプロンプト
        """
        # 前のページのヘッダー情報を含める
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
        
        return prompt
    
    def _call_provider_with_retry(self, prompt: str) -> str:
        """
        リトライ機能を持つプロバイダー呼び出し
        
        Args:
            prompt: 送信するプロンプト
            
        Returns:
            プロバイダーからの応答テキスト
            
        Raises:
            APIError: API呼び出しに失敗した場合
        """
        # リトライカウントを取得
        retry_count = self.retry_manager.get_retry_count(self._call_provider_with_retry)
        
        try:
            # タイムアウト付きでプロバイダーを使用してAPI呼び出し
            import threading
            import queue
            
            # 結果を格納するキュー
            result_queue = queue.Queue()
            exception_queue = queue.Queue()
            
            def api_call_worker():
                """API呼び出しを実行するワーカー関数"""
                try:
                    response = self.provider.translate("", prompt)
                    result_queue.put(response)
                except Exception as e:
                    exception_queue.put(e)
            
            # ワーカースレッドでAPI呼び出しを実行
            worker_thread = threading.Thread(target=api_call_worker, daemon=True)
            worker_thread.start()

            # タイムアウト時間を設定（最大500秒）
            timeout_seconds = 500
            start_time = time.time()
            
            # 結果を待機（定期的にUIイベントを処理）
            while worker_thread.is_alive():
                elapsed = time.time() - start_time
                
                if elapsed > timeout_seconds:
                    tqdm.write(f"  ⚠️ [GUI-DEBUG] API呼び出しタイムアウト ({timeout_seconds}秒)")
                    raise APIError(f"API呼び出しがタイムアウトしました ({timeout_seconds}秒)")
                
                # 短時間待機してUIイベントを処理
                worker_thread.join(timeout=0.1)
                
                # tqdmでの進捗表示
                if int(elapsed) % 5 == 0 and elapsed > 0:  # 5秒ごと
                    tqdm.write(f"  ⏳ [GUI-DEBUG] API応答待機中... ({elapsed:.0f}/{timeout_seconds}秒)")
            
            # 例外が発生した場合
            if not exception_queue.empty():
                raise exception_queue.get()
            
            # 結果を取得
            if not result_queue.empty():
                response = result_queue.get()
                return response
            else:
                raise APIError("API呼び出しが予期せず終了しました")
            
        except RateLimitError as e:
            # レート制限エラーの処理
            self.retry_manager.handle_resource_exhausted_error(
                e, self.provider_name, retry_count, self.rate_limiter
            )
            # エラーハンドリング後、適切にエラーを再発生させる
            raise APIError(f"レート制限エラーにより翻訳に失敗しました: {e}")
            
        except HTTPStatusError as e:
            # HTTPステータスエラーの処理
            self.retry_manager.handle_http_error(
                e, self.provider_name, retry_count, self.rate_limiter
            )
            # エラーハンドリング後、適切にエラーを再発生させる
            raise APIError(f"HTTPエラーにより翻訳に失敗しました: {e}")
            
        except UnicodeEncodeError as e:
            # UnicodeEncodeError処理
            def api_call_func(normalized_prompt):
                return self.provider.translate("", normalized_prompt)
            
            return self.retry_manager.handle_unicode_error(e, prompt, api_call_func)
            
        except Exception as e:
            error_type = type(e).__name__
            
            # ResourceExhaustedエラー（レート制限）の処理
            if "ResourceExhausted" in error_type or "ResourceExhausted" in str(e) or "429" in str(e):
                self.retry_manager.handle_resource_exhausted_error(
                    e, self.provider_name, retry_count, self.rate_limiter
                )
                # エラーハンドリング後、適切にエラーを再発生させる
                raise APIError(f"リソース枯渇エラーにより翻訳に失敗しました: {e}")
            
            # DeadlineExceededエラーを特別に処理
            elif "DeadlineExceeded" in error_type or "Deadline Exceeded" in str(e) or "504" in str(e):
                self.retry_manager.handle_deadline_exceeded_error(e, retry_count)
                # エラーハンドリング後、適切にエラーを再発生させる
                raise APIError(f"タイムアウトエラーにより翻訳に失敗しました: {e}")
            
            # その他の一般的なエラー
            else:
                self.retry_manager.handle_general_error(e, retry_count)
                # エラーハンドリング後、適切にエラーを再発生させる
                raise APIError(f"一般的なエラーにより翻訳に失敗しました: {e}")
    
    def translate_page(self, text: str, page_info: Optional[Dict[str, int]] = None, 
                      previous_headers: Optional[List[str]] = None, target_lang: str = "ja") -> Tuple[str, List[str]]:
        """
        1ページ分のテキストを翻訳する
        
        Args:
            text: 翻訳するテキスト
            page_info: {'current': 現在のページ番号, 'total': 合計ページ数} の形式の辞書
            previous_headers: 前のページで使用されたヘッダーのリスト
            target_lang: 翻訳先の言語
            
        Returns:
            tuple: (翻訳されたテキスト, 抽出されたヘッダーのリスト)
            
        Raises:
            ValidationError: 設定が無効な場合
            APIError: API呼び出しに失敗した場合
        """
        try:
            # レート制限状態を確認し、必要に応じて待機
            self.rate_limiter.check_and_wait_if_needed(self.provider_name)
            
            # ページ情報があれば、ログに残す
            if page_info:
                page_msg = f"ページ {page_info['current']}/{page_info['total']} の翻訳を開始"
                tqdm.write(f"  • {page_msg}")
            
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
            
            # 翻訳プロンプトの作成
            prompt = self._create_translation_prompt(text, target_lang, previous_headers)
            
            # リトライカウントの表示
            retry_count = self.retry_manager.get_retry_count(self.translate_page)
            if retry_count > 1:
                page_str = f"ページ {page_info['current']}/{page_info['total']}" if page_info else "現在のページ"
                tqdm.write(f"  ↻ {page_str} の翻訳を再試行中 (試行 {retry_count}/{self.retry_manager.max_retries})")
            
            # API呼び出しの実行
            start_time = time.time()
            
            # GUI用デバッグログ: API呼び出し開始
            tqdm.write(f"  🔄 [GUI-DEBUG] API呼び出し開始 - {time.strftime('%H:%M:%S')}")
            
            # リトライ機能付き呼び出し
            result = self._call_provider_with_retry(prompt)
            
            # GUI用デバッグログ: API呼び出し完了
            api_duration = time.time() - start_time
            tqdm.write(f"  ✅ [GUI-DEBUG] API呼び出し完了 - {time.strftime('%H:%M:%S')} (所要時間: {api_duration:.2f}秒)")
            
            # ヘッダーの整形処理を適用
            result = self.clean_markdown_headers(result)
            
            elapsed_time = time.time() - start_time
            
            # ページ情報があれば、ログに残す（tqdmと競合しないように）
            if page_info:
                if retry_count > 1:
                    tqdm.write(f"  ✓ ページ {page_info['current']}/{page_info['total']} ({char_count}文字) - {retry_count}回目の試行で {elapsed_time:.1f}秒で翻訳完了")
                else:
                    tqdm.write(f"  ✓ ページ {page_info['current']}/{page_info['total']} ({char_count}文字) - {elapsed_time:.1f}秒で翻訳完了")
            
            # ヘッダーを抽出して返す
            extracted_headers = self.extract_headers(result)
            return result, extracted_headers
            
        except RETRY_EXCEPTIONS as e:
            # リトライ対象のエラーの場合は新しいモジュールで処理
            retry_count = self.retry_manager.get_retry_count(self.translate_page)
            remaining = self.retry_manager.max_retries - retry_count
            
            # リトライ例外処理を新しいモジュールに委譲
            return self.retry_manager.handle_retry_exception(e, page_info, remaining)
            
        except Exception as e:
            # リトライ対象外のエラー
            error_type = type(e).__name__
            error_msg = f"翻訳エラー ({error_type}): {str(e)}"
            tqdm.write(f"  ✗ {error_msg}")
            return f"翻訳エラーが発生しました: {error_msg}", []
    
    def get_provider_info(self) -> Dict[str, Any]:
        """
        プロバイダー情報を取得する
        
        Returns:
            プロバイダー情報の辞書
        """
        return {
            "provider_name": self.provider_name,
            "display_name": self._get_provider_display_name(),
            "model_name": self.model_name,
            "timeout": self.timeout,
            "api_key_configured": bool(self.api_key),
            "supported_models": getattr(self.provider, 'get_supported_models', lambda: [])(),
            "rate_limit_status": self.rate_limiter.get_status(self.provider_name)
        }
    
    def validate_configuration(self) -> bool:
        """
        設定の妥当性を検証する
        
        Returns:
            設定が有効な場合True、無効な場合False
        """
        try:
            # プロバイダー名の検証
            if not validate_provider_name(self.provider_name):
                return False
            
            # APIキーの存在確認
            if not self.api_key:
                return False
            
            # プロバイダーインスタンスの存在確認
            if not self.provider:
                return False
            
            # プロバイダーの設定検証（実装されている場合）
            if hasattr(self.provider, 'validate_configuration'):
                return self.provider.validate_configuration()
            
            return True
            
        except Exception:
            return False
    
    def __str__(self) -> str:
        """文字列表現"""
        return f"TranslatorService({self.provider_name}, {self.model_name})"
    
    def __repr__(self) -> str:
        """デバッグ用文字列表現"""
        return (f"TranslatorService(provider_name='{self.provider_name}', "
                f"model_name='{self.model_name}', timeout={self.timeout})")


# 後方互換性のための関数
def translate_text(text: str, target_lang: str = "ja", page_info=None, llm_provider: str = "gemini", 
                  model_name: str = None, previous_headers=None) -> Tuple[str, List[str]]:
    """
    既存のtranslate_text関数との後方互換性を提供するラッパー関数
    
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
        # TranslatorServiceインスタンスを作成
        service = TranslatorService(provider_name=llm_provider, model_name=model_name)
        
        # 翻訳を実行
        return service.translate_page(
            text=text,
            page_info=page_info,
            previous_headers=previous_headers,
            target_lang=target_lang
        )
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = f"翻訳エラー ({error_type}): {str(e)}"
        tqdm.write(f"  ✗ {error_msg}")
        return f"翻訳エラーが発生しました: {error_msg}", []


# 後方互換性のための関数エクスポート
def extract_headers(text: str) -> List[str]:
    """ヘッダー抽出関数（後方互換性用）"""
    service = TranslatorService("gemini")  # ダミーインスタンス
    return service.extract_headers(text)


def clean_markdown_headers(text: str) -> str:
    """Markdownヘッダー整形関数（後方互換性用）"""
    service = TranslatorService("gemini")  # ダミーインスタンス
    return service.clean_markdown_headers(text)


if __name__ == "__main__":
    # テスト用コード
    sample_text = "# Introduction\n\nThis is a sample text for translation testing."
    
    try:
        # TranslatorServiceのテスト
        service = TranslatorService("gemini")
        print(f"サービス情報: {service}")
        print(f"プロバイダー情報: {service.get_provider_info()}")
        print(f"設定検証: {service.validate_configuration()}")
        
        # 翻訳テスト
        translated, headers = service.translate_page(sample_text)
        print(f"翻訳結果: {translated}")
        print(f"抽出されたヘッダー: {headers}")
        
    except Exception as e:
        print(f"テストエラー: {e}")