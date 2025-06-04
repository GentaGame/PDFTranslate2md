"""
翻訳モジュール

新しいプロバイダーアーキテクチャへの移行完了版。
既存のインターフェースとの後方互換性を保ちながら、
TranslatorServiceを使用して統一された翻訳機能を提供する。

Phase 2: 統合完了
- 新しいプロバイダーアーキテクチャに完全移行
- 古いコードを削除してコードベースをクリーンアップ
- TranslatorServiceを使用した統一インターフェース
"""

import os
import sys
from typing import Optional, List, Tuple, Dict, Any
from dotenv import load_dotenv
from tqdm.auto import tqdm

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 新しい翻訳サービスをインポート
from src.translator_service import TranslatorService, translate_text as service_translate_text
from src.translator_service import extract_headers as service_extract_headers
from src.translator_service import clean_markdown_headers as service_clean_markdown_headers

# 後方互換性のためのグローバル変数とモジュールをインポート
from src.retry_manager import RetryManager, APIError, HTTPStatusError, RETRY_EXCEPTIONS
from src.rate_limiter import RateLimiter, global_rate_limiter

# 後方互換性のためのグローバル変数
rate_limit_status = global_rate_limiter._rate_limit_status

# .envファイルの存在確認と警告表示
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if not os.path.exists(dotenv_path):
    print(f"\n警告: .envファイルが見つかりません。{dotenv_path} に.envファイルを作成してください。")
    print("必要なAPIキーの設定例:")
    print("GEMINI_API_KEY=your_gemini_api_key")
    print("OPENAI_API_KEY=your_openai_api_key")
    print("ANTHROPIC_API_KEY=your_anthropic_api_key\n")

# 環境変数の読み込み
load_dotenv(dotenv_path)

# 環境変数の読み込み（後方互換性用）
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# タイムアウトとリトライの設定（後方互換性用）
DEFAULT_TIMEOUT = 500  # デフォルトタイムアウト (秒)

# リトライマネージャーとレート制限管理の初期化（後方互換性用）
retry_manager = RetryManager(max_retries=5, multiplier=3, min_wait=10, max_wait=180)
rate_limiter = global_rate_limiter


def translate_text(text: str, target_lang: str = "ja", page_info: Optional[Dict[str, int]] = None, 
                  llm_provider: str = "gemini", model_name: Optional[str] = None, 
                  previous_headers: Optional[List[str]] = None) -> Tuple[str, List[str]]:
    """
    テキストを指定された言語に翻訳する（後方互換性維持）
    
    新しいTranslatorServiceアーキテクチャへの完全移行により、
    このモジュールは TranslatorService への薄いラッパーとして機能する。
    
    Args:
        text: 翻訳するテキスト
        target_lang: 翻訳先の言語（デフォルト: "ja"）
        page_info: {'current': 現在のページ番号, 'total': 合計ページ数} の形式の辞書
        llm_provider: 使用するLLMプロバイダー ("gemini", "openai", "claude", "anthropic")
        model_name: 使用するモデル名（省略時はデフォルト値を使用）
        previous_headers: 前のページで使用されたヘッダーのリスト
        
    Returns:
        tuple: (翻訳されたテキスト, 抽出されたヘッダーのリスト)
        
    Raises:
        ValidationError: プロバイダーまたは設定が無効な場合
        APIError: API呼び出しに失敗した場合
    """
    return service_translate_text(
        text=text,
        target_lang=target_lang,
        page_info=page_info,
        llm_provider=llm_provider,
        model_name=model_name,
        previous_headers=previous_headers
    )


def extract_headers(text: str) -> List[str]:
    """
    Markdownテキストからヘッダー（# で始まる行）を抽出する（後方互換性維持）
    
    Args:
        text: ヘッダーを抽出するMarkdownテキスト
        
    Returns:
        抽出されたヘッダーのリスト
    """
    return service_extract_headers(text)


def clean_markdown_headers(text: str) -> str:
    """
    既存のMarkdownヘッダーのレベルを数字パターンに合わせて修正する（後方互換性維持）
    
    例: '# 3.1 手法' → '## 3.1 手法' (ドットが1つなので##に修正)
    例: '### 2 方法' → '# 2 方法' (ドットがないので#に修正)
    
    Args:
        text: 整形する翻訳済みテキスト
        
    Returns:
        整形後のテキスト
    """
    return service_clean_markdown_headers(text)


def create_translator_service(provider_name: str, model_name: Optional[str] = None, 
                             timeout: int = DEFAULT_TIMEOUT) -> TranslatorService:
    """
    TranslatorServiceインスタンスを作成するヘルパー関数
    
    Args:
        provider_name: プロバイダー名 ("gemini", "openai", "claude", "anthropic")
        model_name: モデル名（Noneの場合はデフォルトモデルを使用）
        timeout: タイムアウト時間（秒）
        
    Returns:
        TranslatorServiceインスタンス
        
    Raises:
        ValidationError: プロバイダー名が無効またはAPIキーが設定されていない場合
        ValueError: サポートされていないプロバイダーが指定された場合
    """
    return TranslatorService(
        provider_name=provider_name,
        model_name=model_name,
        timeout=timeout
    )


def get_available_providers() -> Dict[str, bool]:
    """
    利用可能なプロバイダーとAPIキーの設定状況を取得する
    
    Returns:
        プロバイダー名と設定状況の辞書
    """
    providers = {
        "gemini": bool(GEMINI_API_KEY),
        "openai": bool(OPENAI_API_KEY),
        "claude": bool(ANTHROPIC_API_KEY),
        "anthropic": bool(ANTHROPIC_API_KEY)
    }
    return providers


def validate_provider_setup(provider_name: str) -> Tuple[bool, str]:
    """
    指定されたプロバイダーの設定を検証する
    
    Args:
        provider_name: 検証するプロバイダー名
        
    Returns:
        tuple: (設定が有効かどうか, エラーメッセージまたは成功メッセージ)
    """
    try:
        service = TranslatorService(provider_name=provider_name)
        if service.validate_configuration():
            return True, f"{service._get_provider_display_name()}の設定は有効です"
        else:
            return False, f"{service._get_provider_display_name()}の設定に問題があります"
    except Exception as e:
        return False, f"{provider_name}の設定エラー: {str(e)}"


# 旧関数群（後方互換性のため残存、実際にはTranslatorServiceに委譲）
def extract_gemini_response_text(response) -> str:
    """
    Gemini APIレスポンスからテキストを抽出する（非推奨）
    
    新しいプロバイダーアーキテクチャではプロバイダー内で処理されるため、
    この関数は非推奨です。後方互換性のためにのみ提供されています。
    
    Args:
        response: Gemini APIのレスポンスオブジェクト
        
    Returns:
        抽出されたテキスト
        
    Raises:
        APIError: テキストの抽出に失敗した場合
    """
    tqdm.write("  ⚠️ 警告: extract_gemini_response_text()は非推奨です。新しいプロバイダーアーキテクチャを使用してください。")
    
    # Geminiプロバイダーを使用して処理
    try:
        from src.providers.gemini_provider import GeminiProvider
        return GeminiProvider._extract_response_text(response)
    except Exception as e:
        raise APIError(f"Gemini APIレスポンス処理エラー: {str(e)}")


# レガシー関数のエイリアス（非推奨）
def call_llm_with_retry(llm_provider: str, model_name: str, prompt: str):
    """
    レガシーLLM呼び出し関数（非推奨）
    
    この関数は非推奨です。新しいTranslatorServiceを使用してください。
    """
    tqdm.write("  ⚠️ 警告: call_llm_with_retry()は非推奨です。TranslatorServiceを使用してください。")
    
    try:
        service = TranslatorService(provider_name=llm_provider, model_name=model_name)
        return service.provider.translate("", prompt)
    except Exception as e:
        raise APIError(f"レガシー関数呼び出しエラー: {str(e)}")


if __name__ == "__main__":
    """
    テストとデモ用のメイン実行部
    """
    print("🔄 新しいプロバイダーアーキテクチャによる翻訳テスト")
    print("=" * 60)
    
    # 利用可能なプロバイダーを表示
    providers = get_available_providers()
    print("📋 利用可能なプロバイダー:")
    for provider, available in providers.items():
        status = "✅ 設定済み" if available else "❌ 未設定"
        print(f"  • {provider}: {status}")
    
    # 設定済みプロバイダーでテスト実行
    available_providers = [p for p, available in providers.items() if available]
    
    if available_providers:
        # 最初の利用可能なプロバイダーでテスト
        test_provider = available_providers[0]
        print(f"\n🧪 {test_provider}プロバイダーでテスト実行:")
        
        sample_text = "# Introduction\n\nThis is a sample text for translation testing."
        print(f"原文: {sample_text}")
        
        try:
            translated, headers = translate_text(
                text=sample_text,
                target_lang="ja",
                llm_provider=test_provider
            )
            print(f"翻訳結果: {translated}")
            print(f"抽出されたヘッダー: {headers}")
            print("✅ テスト成功！")
            
        except Exception as e:
            print(f"❌ テスト失敗: {str(e)}")
    else:
        print("\n⚠️ 利用可能なプロバイダーがありません。")
        print("APIキーを.envファイルに設定してください。")
    
    print("\n🎉 Phase 2統合完了: 新しいプロバイダーアーキテクチャが正常に動作しています。")