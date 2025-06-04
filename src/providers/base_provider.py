"""
プロバイダー基底クラス

各LLMプロバイダーが実装すべき共通インターフェースを定義する抽象基底クラス。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import time


class BaseProvider(ABC):
    """
    LLMプロバイダーの基底クラス
    
    各プロバイダー（Gemini、OpenAI、Anthropic等）は、この基底クラスを継承し、
    必要なメソッドを実装する必要があります。
    """
    
    def __init__(self, api_key: str, model_name: Optional[str] = None, timeout: int = 500):
        """
        基底プロバイダーの初期化
        
        Args:
            api_key: APIキー
            model_name: 使用するモデル名（Noneの場合はデフォルトモデルを使用）
            timeout: タイムアウト時間（秒）
        """
        if not api_key:
            raise ValueError("APIキーが設定されていません")
        
        self.api_key = api_key
        self.model_name = model_name or self.get_default_model()
        self.timeout = timeout
        
        # レート制限の状態管理
        self._rate_limit_status = {
            "hit": False,
            "last_hit_time": 0,
            "waiting_period": 0
        }
    
    @abstractmethod
    def translate(self, text: str, prompt: str) -> str:
        """
        テキストを翻訳する
        
        Args:
            text: 翻訳対象のテキスト
            prompt: 翻訳プロンプト
            
        Returns:
            翻訳されたテキスト
            
        Raises:
            APIError: API呼び出しでエラーが発生した場合
        """
        pass
    
    @abstractmethod
    def get_default_model(self) -> str:
        """
        デフォルトモデル名を取得する
        
        Returns:
            デフォルトモデル名
        """
        pass
    
    @abstractmethod
    def validate_api_key(self) -> bool:
        """
        APIキーの有効性を検証する
        
        Returns:
            APIキーが有効な場合はTrue、無効な場合はFalse
        """
        pass
    
    @abstractmethod
    def get_rate_limits(self) -> Dict[str, Any]:
        """
        レート制限設定を取得する
        
        Returns:
            レート制限に関する設定辞書
            - max_requests_per_minute: 1分間の最大リクエスト数
            - max_tokens_per_minute: 1分間の最大トークン数
            - max_requests_per_day: 1日の最大リクエスト数
        """
        pass
    
    def check_rate_limit(self) -> bool:
        """
        現在のレート制限状態をチェックする
        
        Returns:
            レート制限に引っかかっていない場合はTrue
        """
        if not self._rate_limit_status["hit"]:
            return True
        
        current_time = time.time()
        elapsed_time = current_time - self._rate_limit_status["last_hit_time"]
        
        # 待機期間が経過した場合はレート制限をリセット
        if elapsed_time >= self._rate_limit_status["waiting_period"]:
            self._rate_limit_status["hit"] = False
            self._rate_limit_status["last_hit_time"] = 0
            self._rate_limit_status["waiting_period"] = 0
            return True
        
        return False
    
    def set_rate_limit_hit(self, waiting_period: int = 60):
        """
        レート制限に引っかかったことを記録する
        
        Args:
            waiting_period: 待機時間（秒）
        """
        self._rate_limit_status["hit"] = True
        self._rate_limit_status["last_hit_time"] = time.time()
        self._rate_limit_status["waiting_period"] = waiting_period
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        現在使用中のモデル情報を取得する
        
        Returns:
            モデル情報の辞書
        """
        return {
            "provider": self.__class__.__name__.replace("Provider", "").lower(),
            "model_name": self.model_name,
            "timeout": self.timeout,
            "rate_limit_status": self._rate_limit_status.copy()
        }
    
    def __str__(self) -> str:
        """
        プロバイダーの文字列表現
        """
        provider_name = self.__class__.__name__.replace("Provider", "")
        return f"{provider_name}({self.model_name})"
    
    def __repr__(self) -> str:
        """
        プロバイダーの詳細表現
        """
        return f"{self.__class__.__name__}(model_name='{self.model_name}', timeout={self.timeout})"


class APIError(Exception):
    """APIエラーの基底クラス"""
    pass


class HTTPStatusError(APIError):
    """HTTPステータスエラー"""
    def __init__(self, status_code: int, message: Optional[str] = None):
        self.status_code = status_code
        self.message = message or f"HTTPステータスエラー: {status_code}"
        super().__init__(self.message)


class RateLimitError(APIError):
    """レート制限エラー"""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        super().__init__(message)


class ValidationError(APIError):
    """バリデーションエラー"""
    pass