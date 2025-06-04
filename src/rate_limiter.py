"""
レート制限管理モジュール

既存のtranslator.pyからレート制限機能を分離して独立したモジュールとして実装。
プロバイダー別レート制限管理、前回のレート制限からの経過時間計算、
待機時間の自動調整機能、スレッドセーフな状態管理を提供する。
"""

import time
import threading
from typing import Dict, Any
from tqdm.auto import tqdm


class RateLimiter:
    """
    レート制限管理クラス
    
    プロバイダー別のレート制限状態を管理し、前回のレート制限からの経過時間を計算、
    動的な待機時間の調整、スレッドセーフな状態管理を提供する。
    """
    
    def __init__(self):
        """
        レート制限管理の初期化
        """
        # レート制限ステータスを管理する辞書
        self._rate_limit_status: Dict[str, Dict[str, Any]] = {
            "gemini": {"hit": False, "last_hit_time": 0, "waiting_period": 0},
            "openai": {"hit": False, "last_hit_time": 0, "waiting_period": 0},
            "anthropic": {"hit": False, "last_hit_time": 0, "waiting_period": 0},
            "claude": {"hit": False, "last_hit_time": 0, "waiting_period": 0},
        }
        
        # スレッドセーフティのためのロック
        self._lock = threading.Lock()
    
    def get_status(self, provider: str) -> Dict[str, Any]:
        """
        指定されたプロバイダーのレート制限状態を取得
        
        Args:
            provider: プロバイダー名
            
        Returns:
            レート制限状態の辞書
        """
        with self._lock:
            if provider not in self._rate_limit_status:
                # 新しいプロバイダーの場合はデフォルト状態を設定
                self._rate_limit_status[provider] = {"hit": False, "last_hit_time": 0, "waiting_period": 0}
            return self._rate_limit_status[provider].copy()
    
    def set_rate_limit_hit(self, provider: str):
        """
        レート制限ヒット状態を設定
        
        Args:
            provider: プロバイダー名
        """
        with self._lock:
            if provider not in self._rate_limit_status:
                self._rate_limit_status[provider] = {"hit": False, "last_hit_time": 0, "waiting_period": 0}
            
            self._rate_limit_status[provider]["hit"] = True
            self._rate_limit_status[provider]["last_hit_time"] = time.time()
    
    def set_waiting_period(self, provider: str, waiting_period: float):
        """
        待機時間を設定
        
        Args:
            provider: プロバイダー名
            waiting_period: 待機時間（秒）
        """
        with self._lock:
            if provider not in self._rate_limit_status:
                self._rate_limit_status[provider] = {"hit": False, "last_hit_time": 0, "waiting_period": 0}
            
            self._rate_limit_status[provider]["waiting_period"] = waiting_period
    
    def reset_rate_limit(self, provider: str):
        """
        レート制限状態をリセット
        
        Args:
            provider: プロバイダー名
        """
        with self._lock:
            if provider not in self._rate_limit_status:
                self._rate_limit_status[provider] = {"hit": False, "last_hit_time": 0, "waiting_period": 0}
            else:
                self._rate_limit_status[provider]["hit"] = False
                self._rate_limit_status[provider]["waiting_period"] = 0
    
    def check_and_wait_if_needed(self, provider: str) -> bool:
        """
        レート制限状態を確認し、必要に応じて待機
        
        Args:
            provider: プロバイダー名
            
        Returns:
            bool: 待機が発生した場合True、そうでなければFalse
        """
        with self._lock:
            if provider not in self._rate_limit_status:
                self._rate_limit_status[provider] = {"hit": False, "last_hit_time": 0, "waiting_period": 0}
                return False
            
            status = self._rate_limit_status[provider]
            
            # レート制限ヒット状態でない場合は待機不要
            if not status["hit"]:
                return False
            
            current_time = time.time()
            elapsed_since_hit = current_time - status["last_hit_time"]
            waiting_period = status["waiting_period"]
            
            # 前回のレート制限からの経過時間が待機時間より少なければ待機
            if elapsed_since_hit < waiting_period:
                remaining_wait = waiting_period - elapsed_since_hit
                if remaining_wait > 0:
                    tqdm.write(f"  ⏱️ 前回のレート制限から {waiting_period}秒経過するまであと{remaining_wait:.1f}秒待機します")
                    
                    # ロックを一時的に解放して待機（他のスレッドがブロックされないように）
                    self._lock.release()
                    try:
                        time.sleep(remaining_wait)
                    finally:
                        self._lock.acquire()
                    
                    return True
            else:
                # 待機時間が経過したらレート制限フラグをリセット
                status["hit"] = False
                tqdm.write(f"  ✓ レート制限の待機時間が経過しました。通常処理を再開します。")
                return False
        
        return False
    
    def calculate_dynamic_wait_time(self, provider: str, retry_count: int, base_wait: int = 60) -> float:
        """
        動的な待機時間を計算
        
        Args:
            provider: プロバイダー名
            retry_count: 現在のリトライ回数
            base_wait: 基本待機時間（秒）
            
        Returns:
            計算された待機時間（秒）
        """
        # プロバイダー別の調整ファクター
        provider_factors = {
            "gemini": 1.0,
            "openai": 1.2,
            "anthropic": 1.0,
            "claude": 1.0,
        }
        
        factor = provider_factors.get(provider, 1.0)
        
        # リトライ回数に応じて指数的に増加する待機時間
        wait_time = base_wait * factor + (retry_count * retry_count * 10 * factor)
        
        # 最大待機時間の制限（5分）
        max_wait = 300
        return min(wait_time, max_wait)
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """
        すべてのプロバイダーのレート制限状態を取得
        
        Returns:
            全プロバイダーのレート制限状態辞書
        """
        with self._lock:
            return {provider: status.copy() for provider, status in self._rate_limit_status.items()}
    
    def clear_all_limits(self):
        """
        すべてのプロバイダーのレート制限状態をクリア
        """
        with self._lock:
            for provider in self._rate_limit_status:
                self._rate_limit_status[provider] = {"hit": False, "last_hit_time": 0, "waiting_period": 0}
    
    def get_elapsed_time_since_hit(self, provider: str) -> float:
        """
        最後のレート制限ヒットからの経過時間を取得
        
        Args:
            provider: プロバイダー名
            
        Returns:
            経過時間（秒）
        """
        with self._lock:
            if provider not in self._rate_limit_status:
                return float('inf')  # 無限大を返す（制限がない状態）
            
            status = self._rate_limit_status[provider]
            if not status["hit"]:
                return float('inf')  # 無限大を返す（制限がない状態）
            
            return time.time() - status["last_hit_time"]
    
    def is_rate_limited(self, provider: str) -> bool:
        """
        指定されたプロバイダーがレート制限中かどうかを確認
        
        Args:
            provider: プロバイダー名
            
        Returns:
            bool: レート制限中の場合True
        """
        with self._lock:
            if provider not in self._rate_limit_status:
                return False
            
            status = self._rate_limit_status[provider]
            if not status["hit"]:
                return False
            
            current_time = time.time()
            elapsed_since_hit = current_time - status["last_hit_time"]
            
            return elapsed_since_hit < status["waiting_period"]
    
    def get_remaining_wait_time(self, provider: str) -> float:
        """
        指定されたプロバイダーの残り待機時間を取得
        
        Args:
            provider: プロバイダー名
            
        Returns:
            残り待機時間（秒）、制限がない場合は0
        """
        with self._lock:
            if provider not in self._rate_limit_status:
                return 0.0
            
            status = self._rate_limit_status[provider]
            if not status["hit"]:
                return 0.0
            
            current_time = time.time()
            elapsed_since_hit = current_time - status["last_hit_time"]
            waiting_period = status["waiting_period"]
            
            remaining = waiting_period - elapsed_since_hit
            return max(0.0, remaining)


# グローバルインスタンス（後方互換性のため）
global_rate_limiter = RateLimiter()

# 後方互換性のためのグローバル変数
rate_limit_status = global_rate_limiter._rate_limit_status