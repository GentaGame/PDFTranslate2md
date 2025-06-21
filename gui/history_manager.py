"""
履歴管理モジュール
処理設定の保存・読み込み・管理を行う
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class ProcessingHistory:
    """処理履歴を表すデータクラス"""
    id: str
    name: str
    input_path: str
    provider: str
    model: str
    output_dir: str
    image_dir: str
    force_overwrite: bool
    created_at: str
    last_used: str
    use_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessingHistory':
        """辞書から復元"""
        return cls(**data)


class HistoryManager:
    """
    処理履歴の管理クラス
    設定の保存、読み込み、削除などを管理する
    """
    
    def __init__(self, history_file: str = "gui_history.json"):
        """
        履歴管理の初期化
        
        Args:
            history_file: 履歴保存ファイル名
        """
        self.history_file = history_file
        self.history_list: List[ProcessingHistory] = []
        self.logger = logging.getLogger(__name__)
        
        # 履歴ファイルの読み込み
        self.load_history()
    
    def load_history(self) -> None:
        """履歴ファイルから履歴を読み込む"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.history_list = [ProcessingHistory.from_dict(item) for item in data]
                self.logger.info(f"履歴を読み込みました: {len(self.history_list)}件")
            else:
                self.history_list = []
                self.logger.info("履歴ファイルが存在しません。新規作成します。")
        except Exception as e:
            self.logger.error(f"履歴の読み込みに失敗しました: {str(e)}")
            self.history_list = []
    
    def save_history(self) -> bool:
        """履歴をファイルに保存する"""
        try:
            data = [history.to_dict() for history in self.history_list]
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.logger.info(f"履歴を保存しました: {len(self.history_list)}件")
            return True
        except Exception as e:
            self.logger.error(f"履歴の保存に失敗しました: {str(e)}")
            return False
    
    def add_history(self, name: str, input_path: str, provider: str, model: str,
                   output_dir: str, image_dir: str, force_overwrite: bool) -> str:
        """
        新しい履歴項目を追加する
        
        Args:
            name: 設定名
            input_path: 入力パス
            provider: プロバイダー名
            model: モデル名
            output_dir: 出力ディレクトリ
            image_dir: 画像ディレクトリ
            force_overwrite: 強制上書きフラグ
            
        Returns:
            追加された履歴のID
        """
        now = datetime.now().isoformat()
        history_id = f"history_{len(self.history_list)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 重複チェック（同じ設定が既に存在する場合は更新）
        existing = self.find_similar_history(input_path, provider, model, output_dir)
        if existing:
            existing.last_used = now
            existing.use_count += 1
            existing.name = name  # 名前は更新
            existing.force_overwrite = force_overwrite
            self.save_history()
            return existing.id
        
        history = ProcessingHistory(
            id=history_id,
            name=name,
            input_path=input_path,
            provider=provider,
            model=model,
            output_dir=output_dir,
            image_dir=image_dir,
            force_overwrite=force_overwrite,
            created_at=now,
            last_used=now,
            use_count=1
        )
        
        self.history_list.append(history)
        self.save_history()
        self.logger.info(f"履歴を追加しました: {name}")
        
        return history_id
    
    def find_similar_history(self, input_path: str, provider: str, model: str, 
                           output_dir: str) -> Optional[ProcessingHistory]:
        """
        類似の履歴項目を検索する
        
        Args:
            input_path: 入力パス
            provider: プロバイダー名
            model: モデル名
            output_dir: 出力ディレクトリ
            
        Returns:
            類似の履歴項目（見つからない場合はNone）
        """
        for history in self.history_list:
            if (history.input_path == input_path and 
                history.provider == provider and 
                history.model == model and 
                history.output_dir == output_dir):
                return history
        return None
    
    def get_history_list(self) -> List[ProcessingHistory]:
        """履歴一覧を取得する（使用回数の多い順でソート）"""
        return sorted(self.history_list, key=lambda x: (x.use_count, x.last_used), reverse=True)
    
    def get_recent_history(self, limit: int = 10) -> List[ProcessingHistory]:
        """最近使用した履歴を取得する"""
        sorted_history = sorted(self.history_list, key=lambda x: x.last_used, reverse=True)
        return sorted_history[:limit]
    
    def get_history_by_id(self, history_id: str) -> Optional[ProcessingHistory]:
        """IDで履歴を取得する"""
        for history in self.history_list:
            if history.id == history_id:
                return history
        return None
    
    def update_history_usage(self, history_id: str) -> bool:
        """履歴の使用回数と最終使用日時を更新する"""
        history = self.get_history_by_id(history_id)
        if history:
            history.use_count += 1
            history.last_used = datetime.now().isoformat()
            self.save_history()
            return True
        return False
    
    def delete_history(self, history_id: str) -> bool:
        """履歴を削除する"""
        for i, history in enumerate(self.history_list):
            if history.id == history_id:
                deleted_history = self.history_list.pop(i)
                self.save_history()
                self.logger.info(f"履歴を削除しました: {deleted_history.name}")
                return True
        return False
    
    def clear_all_history(self) -> bool:
        """全ての履歴を削除する"""
        self.history_list.clear()
        return self.save_history()
    
    def get_history_stats(self) -> Dict[str, Any]:
        """履歴の統計情報を取得する"""
        if not self.history_list:
            return {
                'total_count': 0,
                'most_used_provider': None,
                'most_used_model': None,
                'total_usage': 0
            }
        
        # プロバイダー別使用回数
        provider_usage = {}
        model_usage = {}
        total_usage = 0
        
        for history in self.history_list:
            provider_usage[history.provider] = provider_usage.get(history.provider, 0) + history.use_count
            model_usage[history.model] = model_usage.get(history.model, 0) + history.use_count
            total_usage += history.use_count
        
        most_used_provider = max(provider_usage.items(), key=lambda x: x[1])[0] if provider_usage else None
        most_used_model = max(model_usage.items(), key=lambda x: x[1])[0] if model_usage else None
        
        return {
            'total_count': len(self.history_list),
            'most_used_provider': most_used_provider,
            'most_used_model': most_used_model,
            'total_usage': total_usage,
            'provider_usage': provider_usage,
            'model_usage': model_usage
        }
    
    def export_history(self, export_file: str) -> bool:
        """履歴をエクスポートする"""
        try:
            data = {
                'export_date': datetime.now().isoformat(),
                'history_count': len(self.history_list),
                'history': [history.to_dict() for history in self.history_list]
            }
            
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"履歴をエクスポートしました: {export_file}")
            return True
        except Exception as e:
            self.logger.error(f"履歴のエクスポートに失敗しました: {str(e)}")
            return False
    
    def import_history(self, import_file: str, merge: bool = True) -> bool:
        """
        履歴をインポートする
        
        Args:
            import_file: インポートファイル
            merge: 既存履歴とマージするかどうか
            
        Returns:
            インポートが成功したかどうか
        """
        try:
            with open(import_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            imported_history = [ProcessingHistory.from_dict(item) for item in data.get('history', [])]
            
            if merge:
                # 既存履歴とマージ（重複は避ける）
                for new_history in imported_history:
                    existing = self.get_history_by_id(new_history.id)
                    if not existing:
                        self.history_list.append(new_history)
            else:
                # 既存履歴を置き換え
                self.history_list = imported_history
            
            self.save_history()
            self.logger.info(f"履歴をインポートしました: {len(imported_history)}件")
            return True
        except Exception as e:
            self.logger.error(f"履歴のインポートに失敗しました: {str(e)}")
            return False