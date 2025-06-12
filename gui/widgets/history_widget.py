"""
履歴表示・管理ウィジェット
処理履歴の表示、選択、削除機能を提供
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
                             QListWidgetItem, QPushButton, QLabel, QFrame,
                             QMessageBox, QMenu, QInputDialog, QFileDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon
from typing import List, Optional
import os
from datetime import datetime

from gui.history_manager import HistoryManager, ProcessingHistory


class HistoryItemWidget(QWidget):
    """履歴項目の表示ウィジェット"""
    
    def __init__(self, history: ProcessingHistory, parent=None):
        super().__init__(parent)
        self.history = history
        
        # ラベルの参照を保持
        self.name_label = None
        self.use_count_label = None
        self.input_label = None
        self.provider_label = None
        self.output_label = None
        self.time_label = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """UIの設定"""
        layout = QVBoxLayout()
        layout.setSpacing(4)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # 名前とタイムスタンプ
        header_layout = QHBoxLayout()
        
        self.name_label = QLabel(self.history.name)
        name_font = QFont()
        name_font.setBold(True)
        name_font.setPointSize(11)
        self.name_label.setFont(name_font)
        # スタイルはテーマ適用時に設定
        header_layout.addWidget(self.name_label)
        
        header_layout.addStretch()
        
        # 使用回数
        self.use_count_label = QLabel(f"使用回数: {self.history.use_count}")
        # スタイルはテーマ適用時に設定
        header_layout.addWidget(self.use_count_label)
        
        layout.addLayout(header_layout)
        
        # 詳細情報
        details_layout = QVBoxLayout()
        details_layout.setSpacing(2)
        
        # 入力パス
        self.input_label = QLabel(f"📁 入力: {self._truncate_path(self.history.input_path)}")
        # スタイルはテーマ適用時に設定
        details_layout.addWidget(self.input_label)
        
        # プロバイダーとモデル
        self.provider_label = QLabel(f"🔧 {self.history.provider} / {self.history.model}")
        # スタイルはテーマ適用時に設定
        details_layout.addWidget(self.provider_label)
        
        # 出力先
        self.output_label = QLabel(f"📤 出力: {self._truncate_path(self.history.output_dir)}")
        # スタイルはテーマ適用時に設定
        details_layout.addWidget(self.output_label)
        
        # 最終使用日時
        last_used = datetime.fromisoformat(self.history.last_used)
        time_diff = self._get_time_diff(last_used)
        self.time_label = QLabel(f"🕒 最終使用: {time_diff}")
        # スタイルはテーマ適用時に設定
        details_layout.addWidget(self.time_label)
        
        layout.addLayout(details_layout)
        
        self.setLayout(layout)
        
        # ホバー効果（スタイルはテーマ適用時に設定）
    
    def _truncate_path(self, path: str, max_length: int = 50) -> str:
        """パスを短縮表示"""
        if len(path) <= max_length:
            return path
        return "..." + path[-(max_length-3):]
    
    def _get_time_diff(self, dt: datetime) -> str:
        """時間差を人間にわかりやすい形式で表示"""
        now = datetime.now()
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days}日前"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}時間前"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}分前"
        else:
            return "たった今"
    
    def apply_theme(self, theme_manager):
        """テーマを適用"""
        colors = theme_manager.get_colors()
        
        # 名前ラベルのスタイル
        self.name_label.setStyleSheet(f"color: {colors['text_primary']};")
        
        # 使用回数ラベルのスタイル
        self.use_count_label.setStyleSheet(f"color: {colors['text_secondary']}; font-size: 10px;")
        
        # 詳細情報ラベルのスタイル
        self.input_label.setStyleSheet(f"color: {colors['text_secondary']}; font-size: 10px;")
        self.provider_label.setStyleSheet(f"color: {colors['button_primary']}; font-size: 10px;")
        self.output_label.setStyleSheet(f"color: {colors['button_success']}; font-size: 10px;")
        self.time_label.setStyleSheet(f"color: {colors['text_disabled']}; font-size: 10px;")
        
        # ホバー効果
        hover_style = f"""
            QWidget:hover {{
                background-color: {colors['history_item_hover']};
                border-radius: 4px;
            }}
        """
        self.setStyleSheet(hover_style)


class HistoryWidget(QWidget):
    """
    履歴表示・管理ウィジェット
    """
    
    # シグナル
    history_selected = pyqtSignal(object)  # ProcessingHistory
    history_applied = pyqtSignal(object)   # ProcessingHistory
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.history_manager = HistoryManager()
        self.current_histories: List[ProcessingHistory] = []
        self.is_translating = False  # 翻訳処理中フラグ
        
        self._setup_ui()
        self._load_histories()
        
        # 定期的に履歴を更新（5分間隔に変更）
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_histories)
        self.refresh_timer.start(300000)  # 5分間隔（300000ms）
    
    def _setup_ui(self):
        """UIの設定"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # タイトルとコントロール
        header_layout = QHBoxLayout()
        
        title_label = QLabel("処理履歴")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # 履歴管理ボタン
        self.refresh_button = QPushButton("🔄")
        self.refresh_button.setToolTip("履歴を更新")
        self.refresh_button.clicked.connect(self._refresh_histories)
        self.refresh_button.setFixedSize(30, 30)
        self.refresh_button.setStyleSheet("""
            QPushButton {
                border: 1px solid #bdc3c7;
                border-radius: 15px;
                background-color: #ecf0f1;
            }
            QPushButton:hover {
                background-color: #d5dbdb;
            }
        """)
        header_layout.addWidget(self.refresh_button)
        
        self.menu_button = QPushButton("⋮")
        self.menu_button.setToolTip("履歴管理メニュー")
        self.menu_button.clicked.connect(self._show_menu)
        self.menu_button.setFixedSize(30, 30)
        self.menu_button.setStyleSheet("""
            QPushButton {
                border: 1px solid #bdc3c7;
                border-radius: 15px;
                background-color: #ecf0f1;
            }
            QPushButton:hover {
                background-color: #d5dbdb;
            }
        """)
        header_layout.addWidget(self.menu_button)
        
        layout.addLayout(header_layout)
        
        # 統計情報
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-size: 11px;
                padding: 4px;
                background-color: #f8f9fa;
                border-radius: 4px;
                border: 1px solid #e9ecef;
            }
        """)
        layout.addWidget(self.stats_label)
        
        # 履歴リスト
        self.history_list = QListWidget()
        # スタイルはテーマ適用時に設定
        self.history_list.itemClicked.connect(self._on_history_selected)
        self.history_list.itemDoubleClicked.connect(self._on_history_double_clicked)
        self.history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.history_list)
        
        # アクションボタン
        button_layout = QHBoxLayout()
        
        self.apply_button = QPushButton("📋 設定を適用")
        self.apply_button.clicked.connect(self._apply_selected_history)
        self.apply_button.setEnabled(False)
        self.apply_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        button_layout.addWidget(self.apply_button)
        
        self.delete_button = QPushButton("🗑️ 削除")
        self.delete_button.clicked.connect(self._delete_selected_history)
        self.delete_button.setEnabled(False)
        self.delete_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        button_layout.addWidget(self.delete_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 空の状態メッセージ
        self.empty_label = QLabel("履歴がありません\n処理を実行すると履歴が保存されます")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("""
            QLabel {
                color: #95a5a6;
                font-style: italic;
                padding: 40px;
            }
        """)
        self.empty_label.hide()
        layout.addWidget(self.empty_label)
        
        self.setLayout(layout)
    
    def _load_histories(self):
        """履歴を読み込み"""
        self.current_histories = self.history_manager.get_history_list()
        self._update_history_display()
        self._update_stats()
    
    def _update_history_display(self):
        """履歴表示を更新"""
        self.history_list.clear()
        
        if not self.current_histories:
            self.empty_label.show()
            self.history_list.hide()
            return
        
        self.empty_label.hide()
        self.history_list.show()
        
        for history in self.current_histories:
            # カスタムウィジェットを作成
            item_widget = HistoryItemWidget(history)
            
            # テーマを適用（テーママネージャーが利用可能な場合）
            if hasattr(self, 'theme_manager'):
                item_widget.apply_theme(self.theme_manager)
            
            # リストアイテムを作成
            list_item = QListWidgetItem()
            list_item.setData(Qt.UserRole, history)
            
            # ウィジェットをリストアイテムに設定
            self.history_list.addItem(list_item)
            self.history_list.setItemWidget(list_item, item_widget)
            
            # アイテムのサイズを調整
            list_item.setSizeHint(item_widget.sizeHint())
    
    def _update_stats(self):
        """統計情報を更新"""
        stats = self.history_manager.get_history_stats()
        
        if stats['total_count'] == 0:
            self.stats_label.setText("履歴なし")
        else:
            text = f"📊 合計: {stats['total_count']}件"
            if stats['most_used_provider']:
                text += f" | よく使用: {stats['most_used_provider']}"
            if stats['total_usage'] > 0:
                text += f" | 累計使用: {stats['total_usage']}回"
            self.stats_label.setText(text)
    
    def _refresh_histories(self):
        """履歴を更新"""
        self.history_manager.load_history()
        self._load_histories()
    
    def _on_history_selected(self, item: QListWidgetItem):
        """履歴が選択された時"""
        history = item.data(Qt.UserRole)
        if history:
            self.apply_button.setEnabled(True)
            self.delete_button.setEnabled(True)
            self.history_selected.emit(history)
    
    def _on_history_double_clicked(self, item: QListWidgetItem):
        """履歴がダブルクリックされた時"""
        self._apply_selected_history()
    
    def _apply_selected_history(self):
        """選択された履歴を適用"""
        current_item = self.history_list.currentItem()
        if current_item:
            history = current_item.data(Qt.UserRole)
            if history:
                # 使用回数を更新
                self.history_manager.update_history_usage(history.id)
                self._load_histories()  # 表示を更新
                
                # シグナルを発信
                self.history_applied.emit(history)
    
    def _delete_selected_history(self):
        """選択された履歴を削除"""
        current_item = self.history_list.currentItem()
        if current_item:
            history = current_item.data(Qt.UserRole)
            if history:
                reply = QMessageBox.question(
                    self,
                    "履歴削除",
                    f"履歴「{history.name}」を削除しますか？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    if self.history_manager.delete_history(history.id):
                        self._load_histories()
                        self.apply_button.setEnabled(False)
                        self.delete_button.setEnabled(False)
                        QMessageBox.information(self, "削除完了", "履歴を削除しました。")
                    else:
                        QMessageBox.warning(self, "削除エラー", "履歴の削除に失敗しました。")
    
    def _show_context_menu(self, position):
        """コンテキストメニューを表示"""
        item = self.history_list.itemAt(position)
        if item:
            history = item.data(Qt.UserRole)
            
            menu = QMenu(self)
            
            apply_action = menu.addAction("📋 設定を適用")
            apply_action.triggered.connect(self._apply_selected_history)
            
            menu.addSeparator()
            
            rename_action = menu.addAction("✏️ 名前を変更")
            rename_action.triggered.connect(lambda: self._rename_history(history))
            
            delete_action = menu.addAction("🗑️ 削除")
            delete_action.triggered.connect(self._delete_selected_history)
            
            menu.exec_(self.history_list.mapToGlobal(position))
    
    def _show_menu(self):
        """履歴管理メニューを表示"""
        menu = QMenu(self)
        
        clear_action = menu.addAction("🗑️ 全履歴削除")
        clear_action.triggered.connect(self._clear_all_history)
        
        menu.addSeparator()
        
        export_action = menu.addAction("📤 履歴エクスポート")
        export_action.triggered.connect(self._export_history)
        
        import_action = menu.addAction("📥 履歴インポート")
        import_action.triggered.connect(self._import_history)
        
        menu.exec_(self.menu_button.mapToGlobal(self.menu_button.rect().bottomLeft()))
    
    def _rename_history(self, history: ProcessingHistory):
        """履歴の名前を変更"""
        new_name, ok = QInputDialog.getText(
            self,
            "名前変更",
            "新しい名前を入力してください:",
            text=history.name
        )
        
        if ok and new_name.strip():
            history.name = new_name.strip()
            self.history_manager.save_history()
            self._load_histories()
    
    def _clear_all_history(self):
        """全履歴を削除"""
        reply = QMessageBox.question(
            self,
            "全履歴削除",
            "全ての履歴を削除しますか？\nこの操作は取り消せません。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.history_manager.clear_all_history():
                self._load_histories()
                self.apply_button.setEnabled(False)
                self.delete_button.setEnabled(False)
                QMessageBox.information(self, "削除完了", "全ての履歴を削除しました。")
            else:
                QMessageBox.warning(self, "削除エラー", "履歴の削除に失敗しました。")
    
    def _export_history(self):
        """履歴をエクスポート"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "履歴エクスポート",
            f"history_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON files (*.json)"
        )
        
        if filename:
            if self.history_manager.export_history(filename):
                QMessageBox.information(self, "エクスポート完了", f"履歴をエクスポートしました:\n{filename}")
            else:
                QMessageBox.warning(self, "エクスポートエラー", "履歴のエクスポートに失敗しました。")
    
    def _import_history(self):
        """履歴をインポート"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "履歴インポート",
            "",
            "JSON files (*.json)"
        )
        
        if filename:
            reply = QMessageBox.question(
                self,
                "履歴インポート",
                "既存の履歴とマージしますか？\n「No」を選択すると既存履歴は置き換えられます。",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes
            )
            
            if reply != QMessageBox.Cancel:
                merge = reply == QMessageBox.Yes
                if self.history_manager.import_history(filename, merge):
                    self._load_histories()
                    QMessageBox.information(self, "インポート完了", "履歴をインポートしました。")
                else:
                    QMessageBox.warning(self, "インポートエラー", "履歴のインポートに失敗しました。")
    
    def add_history(self, name: str, input_path: str, provider: str, model: str,
                   output_dir: str, image_dir: str, force_overwrite: bool) -> str:
        """履歴を追加"""
        history_id = self.history_manager.add_history(
            name, input_path, provider, model, output_dir, image_dir, force_overwrite
        )
        self._load_histories()
        return history_id
    
    def get_selected_history(self) -> Optional[ProcessingHistory]:
        """選択された履歴を取得"""
        current_item = self.history_list.currentItem()
        if current_item:
            return current_item.data(Qt.UserRole)
        return None
    def set_translation_state(self, is_translating: bool):
        """翻訳状態を設定し、タイマーを制御"""
        self.is_translating = is_translating
        
        if is_translating:
            # 翻訳開始時はタイマーを停止
            if self.refresh_timer.isActive():
                self.refresh_timer.stop()
        else:
            # 翻訳終了時はタイマーを再開（5分間隔）
            if not self.refresh_timer.isActive():
                self.refresh_timer.start(300000)  # 5分間隔
    
    def pause_auto_refresh(self):
        """自動更新を一時停止"""
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()
    
    def resume_auto_refresh(self):
        """自動更新を再開"""
        if not self.refresh_timer.isActive() and not self.is_translating:
            self.refresh_timer.start(300000)  # 5分間隔
    
    def apply_theme(self, theme_manager):
        """テーマを適用"""
        self.theme_manager = theme_manager
        colors = theme_manager.get_colors()
        
        # 履歴リストのスタイル
        self.history_list.setStyleSheet(theme_manager.generate_list_style())
        
        # 統計情報ラベルのスタイル
        stats_style = f"""
            QLabel {{
                color: {colors['text_secondary']};
                font-size: 11px;
                padding: 4px;
                background-color: {colors['history_stats_bg']};
                border-radius: 4px;
                border: 1px solid {colors['history_stats_border']};
            }}
        """
        self.stats_label.setStyleSheet(stats_style)
        
        # ボタンのスタイル
        self.apply_button.setStyleSheet(theme_manager.generate_button_style("primary"))
        self.delete_button.setStyleSheet(theme_manager.generate_button_style("danger"))
        
        # 小さなボタンのスタイル
        small_button_style = theme_manager.generate_button_style("secondary")
        small_button_style = small_button_style.replace("padding: 8px 16px;", "padding: 4px 8px;")
        
        refresh_style = f"""
            QPushButton {{
                border: 1px solid {colors['border']};
                border-radius: 15px;
                background-color: {colors['surface_variant']};
                color: {colors['text_primary']};
            }}
            QPushButton:hover {{
                background-color: {colors['surface']};
            }}
        """
        self.refresh_button.setStyleSheet(refresh_style)
        self.menu_button.setStyleSheet(refresh_style)
        
        # 空メッセージのスタイル
        empty_style = f"""
            QLabel {{
                color: {colors['text_disabled']};
                font-style: italic;
                padding: 40px;
            }}
        """
        self.empty_label.setStyleSheet(empty_style)