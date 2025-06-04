"""
プロバイダーパッケージ

LLMプロバイダーの管理とファクトリー機能を提供します。
"""

from typing import Optional, Dict, Any
from .base_provider import BaseProvider, APIError, HTTPStatusError, RateLimitError, ValidationError


# サポートされているプロバイダーの定義
SUPPORTED_PROVIDERS = {
    "gemini": {
        "class_name": "GeminiProvider",
        "module": "gemini_provider",
        "default_model": "gemini-2.5-flash-preview-05-20"
    },
    "openai": {
        "class_name": "OpenAIProvider",
        "module": "openai_provider",
        "default_model": "gpt-4.1"
    },
    "claude": {
        "class_name": "ClaudeProvider",
        "module": "claude_provider",
        "default_model": "claude-3-7-sonnet"
    },
    "anthropic": {
        "class_name": "AnthropicProvider",
        "module": "anthropic_provider",
        "default_model": "claude-3-7-sonnet"
    }
}


def create_provider(provider_name: str, api_key: str, model_name: Optional[str] = None, timeout: int = 500) -> BaseProvider:
    """
    指定されたプロバイダー名に基づいてプロバイダーインスタンスを作成する
    
    Args:
        provider_name: プロバイダー名 ("gemini", "openai", "claude", "anthropic")
        api_key: APIキー
        model_name: モデル名（Noneの場合はデフォルトモデルを使用）
        timeout: タイムアウト時間（秒）
        
    Returns:
        作成されたプロバイダーインスタンス
        
    Raises:
        ValueError: サポートされていないプロバイダー名が指定された場合
        ValidationError: APIキーが無効な場合
        ImportError: プロバイダーモジュールのインポートに失敗した場合
    """
    if not provider_name:
        raise ValueError("プロバイダー名が指定されていません")
    
    if not api_key:
        raise ValidationError("APIキーが指定されていません")
    
    # プロバイダー名を正規化（小文字化）
    provider_name = provider_name.lower().strip()
    
    # サポートされているプロバイダーかチェック
    if provider_name not in SUPPORTED_PROVIDERS:
        supported_list = ", ".join(SUPPORTED_PROVIDERS.keys())
        raise ValueError(
            f"サポートされていないプロバイダーです: '{provider_name}'\n"
            f"サポートされているプロバイダー: {supported_list}"
        )
    
    provider_config = SUPPORTED_PROVIDERS[provider_name]
    
    # モデル名が指定されていない場合はデフォルトを使用
    if model_name is None:
        model_name = provider_config["default_model"]
    
    try:
        # 動的にプロバイダーモジュールをインポート
        module_name = f".{provider_config['module']}"
        class_name = provider_config["class_name"]
        
        # プロバイダーモジュールのインポートを試行
        try:
            # 直接相対インポートを使用
            if provider_name == "gemini":
                from .gemini_provider import GeminiProvider as provider_class
            elif provider_name == "openai":
                from .openai_provider import OpenAIProvider as provider_class
            elif provider_name in ("claude", "anthropic"):
                from .anthropic_provider import AnthropicProvider as provider_class
            else:
                raise ImportError(f"未知のプロバイダー: {provider_name}")
                
        except ImportError:
            # まだ実装されていないプロバイダーの場合は一時的なエラーメッセージ
            raise ImportError(
                f"プロバイダー '{provider_name}' はまだ実装されていません。\n"
                f"モジュール '{module_name}' が見つかりません。"
            )
        
        # プロバイダーインスタンスを作成
        provider = provider_class(
            api_key=api_key,
            model_name=model_name,
            timeout=timeout
        )
        
        return provider
        
    except ImportError as e:
        raise ImportError(f"プロバイダー '{provider_name}' の初期化に失敗しました: {str(e)}")
    except Exception as e:
        raise ValidationError(f"プロバイダー '{provider_name}' の作成中にエラーが発生しました: {str(e)}")


def get_supported_providers() -> Dict[str, Dict[str, Any]]:
    """
    サポートされているプロバイダーの情報を取得する
    
    Returns:
        サポートされているプロバイダーの辞書
    """
    return SUPPORTED_PROVIDERS.copy()


def get_default_model(provider_name: str) -> str:
    """
    指定されたプロバイダーのデフォルトモデル名を取得する
    
    Args:
        provider_name: プロバイダー名
        
    Returns:
        デフォルトモデル名
        
    Raises:
        ValueError: サポートされていないプロバイダー名が指定された場合
    """
    provider_name = provider_name.lower().strip()
    
    if provider_name not in SUPPORTED_PROVIDERS:
        supported_list = ", ".join(SUPPORTED_PROVIDERS.keys())
        raise ValueError(
            f"サポートされていないプロバイダーです: '{provider_name}'\n"
            f"サポートされているプロバイダー: {supported_list}"
        )
    
    return SUPPORTED_PROVIDERS[provider_name]["default_model"]


def validate_provider_name(provider_name: str) -> bool:
    """
    プロバイダー名が有効かどうかを検証する
    
    Args:
        provider_name: 検証するプロバイダー名
        
    Returns:
        有効な場合はTrue、無効な場合はFalse
    """
    if not provider_name:
        return False
    
    return provider_name.lower().strip() in SUPPORTED_PROVIDERS


# 実装済みプロバイダーをインポート
try:
    from .gemini_provider import GeminiProvider
except ImportError:
    GeminiProvider = None

try:
    from .openai_provider import OpenAIProvider
except ImportError:
    OpenAIProvider = None

try:
    from .anthropic_provider import AnthropicProvider
except ImportError:
    AnthropicProvider = None

# パッケージから直接インポート可能にする
__all__ = [
    "BaseProvider",
    "APIError",
    "HTTPStatusError",
    "RateLimitError",
    "ValidationError",
    "create_provider",
    "get_supported_providers",
    "get_default_model",
    "validate_provider_name",
    "SUPPORTED_PROVIDERS",
    "GeminiProvider",
    "OpenAIProvider",
    "AnthropicProvider"
]