"""
テーマ管理クラス
ダークモード/ライトモードの自動切り替えとスタイル管理
"""

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtGui import QPalette, QColor
from typing import Dict, Any
import sys


class ThemeManager(QObject):
    """
    テーマ管理クラス
    システムのダークモード設定を検出し、アプリケーション全体のテーマを管理
    """
    
    # シグナル
    theme_changed = pyqtSignal(str)  # テーマが変更された時
    
    def __init__(self):
        super().__init__()
        
        self._current_theme = self._detect_system_theme()
        self._colors = self._initialize_colors()
        
        # システムテーマの変更を監視するタイマー
        self._monitor_timer = QTimer()
        self._monitor_timer.timeout.connect(self._check_theme_change)
        self._monitor_timer.start(5000)  # 5秒間隔でチェック
    
    def _detect_system_theme(self) -> str:
        """システムのテーマを検出"""
        try:
            app = QApplication.instance()
            if app:
                palette = app.palette()
                # ウィンドウの背景色で判定
                window_color = palette.color(QPalette.Window)
                # 明度が128未満の場合はダークテーマとみなす
                brightness = (window_color.red() + window_color.green() + window_color.blue()) / 3
                return "dark" if brightness < 128 else "light"
        except Exception:
            pass
        
        # macOSの場合の追加チェック
        if sys.platform == "darwin":
            try:
                import subprocess
                result = subprocess.run(
                    ["defaults", "read", "-g", "AppleInterfaceStyle"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0 and "Dark" in result.stdout:
                    return "dark"
            except Exception:
                pass
        
        return "light"  # デフォルトはライトテーマ
    
    def _initialize_colors(self) -> Dict[str, Dict[str, str]]:
        """カラーパレットを初期化"""
        return {
            "light": {
                # 基本色
                "background": "#ffffff",
                "surface": "#f8f9fa",
                "surface_variant": "#f1f3f4",
                "border": "#dee2e6",
                "border_hover": "#007acc",
                "text_primary": "#212529",
                "text_secondary": "#6c757d",
                "text_disabled": "#adb5bd",
                
                # ドラッグ&ドロップエリア
                "drop_area_bg": "#f9f9f9",
                "drop_area_hover": "#f0f8ff",
                "drop_area_border": "#cccccc",
                "drop_area_border_hover": "#007acc",
                "drop_area_selected": "#f8fff8",
                "drop_area_selected_border": "#28a745",
                
                # ボタン色
                "button_primary": "#007acc",
                "button_primary_hover": "#005999",
                "button_success": "#28a745",
                "button_success_hover": "#218838",
                "button_danger": "#dc3545",
                "button_danger_hover": "#c82333",
                "button_secondary": "#6c757d",
                "button_secondary_hover": "#5a6268",
                "button_info": "#17a2b8",
                "button_info_hover": "#138496",
                
                # プログレスバー
                "progress_bg": "#e9ecef",
                "progress_chunk": "#007acc",
                "progress_chunk_file": "#28a745",
                
                # ログ
                "log_bg": "#ffffff",
                "log_border": "#ced4da",
                "log_error": "#dc3545",
                "log_warning": "#ffc107",
                "log_info": "#28a745",
                "log_debug": "#6c757d",
                
                # ステータス
                "status_success_bg": "#d4edda",
                "status_success_border": "#c3e6cb",
                "status_success_text": "#155724",
                "status_error_bg": "#f8d7da",
                "status_error_border": "#f5c6cb",
                "status_error_text": "#721c24",
                
                # 履歴
                "history_item_bg": "#ffffff",
                "history_item_hover": "#ecf0f1",
                "history_item_selected": "#3498db",
                "history_border": "#bdc3c7",
                "history_stats_bg": "#f8f9fa",
                "history_stats_border": "#e9ecef",
            },
            "dark": {
                # 基本色
                "background": "#1e1e1e",
                "surface": "#2d2d30",
                "surface_variant": "#3e3e42",
                "border": "#555555",
                "border_hover": "#0d7377",
                "text_primary": "#ffffff",
                "text_secondary": "#cccccc",
                "text_disabled": "#808080",
                
                # ドラッグ&ドロップエリア
                "drop_area_bg": "#2d2d30",
                "drop_area_hover": "#264653",
                "drop_area_border": "#555555",
                "drop_area_border_hover": "#0d7377",
                "drop_area_selected": "#2a9d8f",
                "drop_area_selected_border": "#2a9d8f",
                
                # ボタン色
                "button_primary": "#0d7377",
                "button_primary_hover": "#14a085",
                "button_success": "#2a9d8f",
                "button_success_hover": "#21867a",
                "button_danger": "#e63946",
                "button_danger_hover": "#d62828",
                "button_secondary": "#6c757d",
                "button_secondary_hover": "#5a6268",
                "button_info": "#0d7377",
                "button_info_hover": "#14a085",
                
                # プログレスバー
                "progress_bg": "#3e3e42",
                "progress_chunk": "#0d7377",
                "progress_chunk_file": "#2a9d8f",
                
                # ログ
                "log_bg": "#1e1e1e",
                "log_border": "#555555",
                "log_error": "#e63946",
                "log_warning": "#f77f00",
                "log_info": "#2a9d8f",
                "log_debug": "#cccccc",
                
                # ステータス
                "status_success_bg": "#2a9d8f",
                "status_success_border": "#21867a",
                "status_success_text": "#ffffff",
                "status_error_bg": "#e63946",
                "status_error_border": "#d62828",
                "status_error_text": "#ffffff",
                
                # 履歴
                "history_item_bg": "#2d2d30",
                "history_item_hover": "#3e3e42",
                "history_item_selected": "#0d7377",
                "history_border": "#555555",
                "history_stats_bg": "#2d2d30",
                "history_stats_border": "#555555",
            }
        }
    
    def _check_theme_change(self):
        """テーマの変更をチェック"""
        current_theme = self._detect_system_theme()
        if current_theme != self._current_theme:
            self._current_theme = current_theme
            self.theme_changed.emit(current_theme)
    
    def get_current_theme(self) -> str:
        """現在のテーマを取得"""
        return self._current_theme
    
    def is_dark_theme(self) -> bool:
        """ダークテーマかどうか"""
        return self._current_theme == "dark"
    
    def get_color(self, key: str) -> str:
        """色を取得"""
        return self._colors[self._current_theme].get(key, "#000000")
    
    def get_colors(self) -> Dict[str, str]:
        """現在のテーマの全色を取得"""
        return self._colors[self._current_theme].copy()
    
    def generate_button_style(self, button_type: str = "primary") -> str:
        """ボタンのスタイルを生成"""
        colors = self.get_colors()
        
        style_map = {
            "primary": ("button_primary", "button_primary_hover"),
            "success": ("button_success", "button_success_hover"),
            "danger": ("button_danger", "button_danger_hover"),
            "secondary": ("button_secondary", "button_secondary_hover"),
            "info": ("button_info", "button_info_hover"),
        }
        
        if button_type not in style_map:
            button_type = "primary"
        
        bg_key, hover_key = style_map[button_type]
        
        return f"""
            QPushButton {{
                background-color: {colors[bg_key]};
                color: {colors['text_primary']};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover:enabled {{
                background-color: {colors[hover_key]};
            }}
            QPushButton:disabled {{
                background-color: {colors['text_disabled']};
                color: {colors['text_secondary']};
            }}
        """
    
    def generate_frame_style(self, frame_type: str = "default") -> str:
        """フレームのスタイルを生成"""
        colors = self.get_colors()
        
        if frame_type == "drop_area":
            return f"""
                QFrame {{
                    border: 2px dashed {colors['drop_area_border']};
                    border-radius: 10px;
                    background-color: {colors['drop_area_bg']};
                }}
                QFrame:hover {{
                    border-color: {colors['drop_area_border_hover']};
                    background-color: {colors['drop_area_hover']};
                }}
            """
        elif frame_type == "drop_area_selected":
            return f"""
                QFrame {{
                    border: 2px solid {colors['drop_area_selected_border']};
                    border-radius: 10px;
                    background-color: {colors['drop_area_selected']};
                }}
            """
        else:  # default
            return f"""
                QFrame {{
                    background-color: {colors['surface']};
                    border: 1px solid {colors['border']};
                    border-radius: 8px;
                }}
            """
    
    def generate_progress_style(self, progress_type: str = "overall") -> str:
        """プログレスバーのスタイルを生成"""
        colors = self.get_colors()
        
        chunk_color = colors["progress_chunk_file"] if progress_type == "file" else colors["progress_chunk"]
        
        return f"""
            QProgressBar {{
                border: 1px solid {colors['border']};
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
                background-color: {colors['progress_bg']};
                color: {colors['text_primary']};
            }}
            QProgressBar::chunk {{
                background-color: {chunk_color};
                border-radius: 4px;
            }}
        """
    
    def generate_log_style(self) -> str:
        """ログのスタイルを生成"""
        colors = self.get_colors()
        
        return f"""
            QTextEdit {{
                background-color: {colors['log_bg']};
                border: 1px solid {colors['log_border']};
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                padding: 8px;
                color: {colors['text_primary']};
            }}
        """
    
    def generate_list_style(self) -> str:
        """リストのスタイルを生成"""
        colors = self.get_colors()
        
        return f"""
            QListWidget {{
                border: 1px solid {colors['history_border']};
                border-radius: 6px;
                background-color: {colors['history_item_bg']};
                alternate-background-color: {colors['surface']};
                color: {colors['text_primary']};
            }}
            QListWidget::item {{
                border-bottom: 1px solid {colors['border']};
                padding: 4px;
            }}
            QListWidget::item:selected {{
                background-color: {colors['history_item_selected']};
                color: {colors['text_primary']};
            }}
            QListWidget::item:hover {{
                background-color: {colors['history_item_hover']};
            }}
        """


# グローバルテーママネージャーのインスタンス
_theme_manager = None

def get_theme_manager() -> ThemeManager:
    """テーママネージャーのシングルトンインスタンスを取得"""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager