"""
進捗表示ウィジェット
リアルタイムでの処理進捗とログ表示を提供
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QProgressBar, QTextEdit, QPushButton, QFrame,
                             QSplitter, QScrollArea)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QFont, QTextCursor


class LogLevel:
    """ログレベル定数"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class ProgressWidget(QWidget):
    """
    処理進捗とログを表示するウィジェット
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.is_processing = False
        self.current_file = ""
        self.total_files = 0
        self.processed_files = 0
        
        self._setup_ui()
        
        # ログ自動スクロール用タイマー
        self.scroll_timer = QTimer()
        self.scroll_timer.timeout.connect(self._auto_scroll_log)
        self.scroll_timer.start(100)  # 100ms間隔
    
    def _setup_ui(self):
        """UIの設定"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # 進捗情報セクション
        progress_frame = QFrame()
        progress_frame.setFrameStyle(QFrame.StyledPanel)
        progress_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        progress_layout = QVBoxLayout(progress_frame)
        progress_layout.setSpacing(8)
        
        # タイトル
        title_label = QLabel("処理進捗")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        progress_layout.addWidget(title_label)
        
        # 全体進捗
        overall_layout = QHBoxLayout()
        overall_layout.addWidget(QLabel("全体進捗:"))
        
        self.overall_progress = QProgressBar()
        self.overall_progress.setMinimum(0)
        self.overall_progress.setMaximum(100)
        self.overall_progress.setValue(0)
        # スタイルはテーマ適用時に設定
        overall_layout.addWidget(self.overall_progress)
        
        self.overall_label = QLabel("待機中...")
        self.overall_label.setMinimumWidth(150)
        overall_layout.addWidget(self.overall_label)
        progress_layout.addLayout(overall_layout)
        
        # ファイル進捗
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("ファイル進捗:"))
        
        self.file_progress = QProgressBar()
        self.file_progress.setMinimum(0)
        self.file_progress.setMaximum(100)
        self.file_progress.setValue(0)
        # スタイルはテーマ適用時に設定
        file_layout.addWidget(self.file_progress)
        
        self.file_label = QLabel("待機中...")
        self.file_label.setMinimumWidth(150)
        file_layout.addWidget(self.file_label)
        progress_layout.addLayout(file_layout)
        
        # 現在の処理情報
        self.status_label = QLabel("処理待機中...")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-style: italic;
                padding: 5px;
                background-color: #e9ecef;
                border-radius: 4px;
            }
        """)
        progress_layout.addWidget(self.status_label)
        
        layout.addWidget(progress_frame)
        
        # ログセクション
        log_frame = QFrame()
        log_frame.setFrameStyle(QFrame.StyledPanel)
        log_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        log_layout = QVBoxLayout(log_frame)
        log_layout.setSpacing(8)
        
        # ログタイトルとコントロール
        log_title_layout = QHBoxLayout()
        
        log_title = QLabel("処理ログ")
        log_title.setFont(title_font)
        log_title_layout.addWidget(log_title)
        
        log_title_layout.addStretch()
        
        # ログクリアボタン
        self.clear_log_button = QPushButton("ログクリア")
        self.clear_log_button.clicked.connect(self.clear_log)
        self.clear_log_button.setStyleSheet("""
            QPushButton {
                padding: 4px 12px;
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        log_title_layout.addWidget(self.clear_log_button)
        
        log_layout.addLayout(log_title_layout)
        
        # ログテキスト表示
        self.log_text = QTextEdit()
        self.log_text.setMinimumHeight(200)
        self.log_text.setReadOnly(True)
        # スタイルはテーマ適用時に設定
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_frame)
        
        self.setLayout(layout)
    
    def reset_progress(self):
        """進捗をリセット"""
        self.is_processing = False
        self.current_file = ""
        self.total_files = 0
        self.processed_files = 0
        
        self.overall_progress.setValue(0)
        self.file_progress.setValue(0)
        self.overall_label.setText("待機中...")
        self.file_label.setText("待機中...")
        self.status_label.setText("処理待機中...")
    
    def start_processing(self, message: str = "処理を開始しています..."):
        """処理開始"""
        self.is_processing = True
        self.reset_progress()
        self.status_label.setText(message)
        self.add_log(LogLevel.INFO, message)
    
    def finish_processing(self, success: bool, message: str):
        """処理終了"""
        self.is_processing = False
        
        if success:
            self.overall_progress.setValue(100)
            self.file_progress.setValue(100)
            self.overall_label.setText("完了")
            self.file_label.setText("完了")
            self.status_label.setText("✅ " + message)
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #155724;
                    font-weight: bold;
                    padding: 5px;
                    background-color: #d4edda;
                    border: 1px solid #c3e6cb;
                    border-radius: 4px;
                }
            """)
            self.add_log(LogLevel.INFO, f"✅ {message}")
        else:
            self.status_label.setText("❌ " + message)
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #721c24;
                    font-weight: bold;
                    padding: 5px;
                    background-color: #f8d7da;
                    border: 1px solid #f5c6cb;
                    border-radius: 4px;
                }
            """)
            self.add_log(LogLevel.ERROR, f"❌ {message}")
    
    @pyqtSlot(int, str)
    def update_overall_progress(self, progress: int, message: str):
        """全体進捗を更新"""
        self.overall_progress.setValue(max(0, min(100, progress)))
        self.overall_label.setText(f"{progress}%")
        self.status_label.setText(message)
        
        # UIの即座更新を強制実行
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()
    
    @pyqtSlot(int, int, str)
    def update_page_progress(self, current_page: int, total_pages: int, filename: str):
        """ページ進捗を更新"""
        if total_pages > 0:
            progress = int((current_page / total_pages) * 100)
            self.file_progress.setValue(progress)
            self.file_label.setText(f"ページ {current_page}/{total_pages}")
            self.status_label.setText(f"翻訳中: {filename} - ページ {current_page}/{total_pages}")
            
            # UIの即座更新を強制実行
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()
    
    @pyqtSlot(str)
    def start_file_processing(self, filename: str):
        """ファイル処理開始"""
        self.current_file = filename
        self.file_progress.setValue(0)
        self.file_label.setText(f"処理中: {filename}")
        self.add_log(LogLevel.INFO, f"📄 処理開始: {filename}")
        
        # UIの即座更新を強制実行
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()
    
    @pyqtSlot(str, bool)
    def finish_file_processing(self, filename: str, success: bool):
        """ファイル処理終了"""
        self.processed_files += 1
        
        if success:
            self.file_progress.setValue(100)
            self.file_label.setText(f"完了: {filename}")
            self.add_log(LogLevel.INFO, f"✅ 完了: {filename}")
        else:
            self.file_label.setText(f"失敗: {filename}")
            self.add_log(LogLevel.ERROR, f"❌ 失敗: {filename}")
        
        # UIの即座更新を強制実行
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()
    
    @pyqtSlot(str)
    def show_error(self, error_message: str):
        """エラーメッセージを表示"""
        self.add_log(LogLevel.ERROR, error_message)
        self.status_label.setText(f"❌ {error_message}")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #721c24;
                font-weight: bold;
                padding: 5px;
                background-color: #f8d7da;
                border: 1px solid #f5c6cb;
                border-radius: 4px;
            }
        """)
    
    @pyqtSlot(str, str)
    def add_log(self, level: str, message: str):
        """ログメッセージを追加"""
        from datetime import datetime
        import html
        
        # タイムスタンプを追加
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # メッセージの前処理：HTMLエスケープと改行変換（全改行コード対応）
        escaped_message = html.escape(message)
        # \r\n, \r, \n すべてを <br> に変換
        import re
        formatted_content = re.sub(r'(\r\n|\r|\n)', '<br>', escaped_message)
        
        # テーマカラーを取得（テーマが設定されている場合）
        if hasattr(self, 'theme_manager') and self.theme_manager:
            colors = self.theme_manager.get_colors()
            timestamp_color = colors['text_secondary']
            text_color = colors['text_primary']
        else:
            # フォールバック色
            timestamp_color = "#6c757d"
            text_color = "#333333"
        
        # レベルに応じてスタイルを設定
        if level == LogLevel.ERROR:
            color = "#dc3545"
            prefix = "❌"
        elif level == LogLevel.WARNING:
            color = "#ffc107"
            prefix = "⚠️"
        elif level == LogLevel.INFO:
            color = "#28a745"
            prefix = "ℹ️"
        else:  # DEBUG
            color = "#6c757d"
            prefix = "🔍"
        
        # HTMLでフォーマット（テーマ対応）
        import textwrap
        formatted_message = textwrap.dedent(f"""\
            <div style="margin: 2px 0; color: {text_color};">
                <span style="color: {timestamp_color};">[{timestamp}]</span>
                <span style="color: {color}; font-weight: bold;">{prefix} {level}:</span>
                <span>{formatted_content}</span>
            </div>
        """)
        
        # ログに追加
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertHtml(formatted_message)
        
        # 自動スクロール（少し遅延させる）
        QTimer.singleShot(50, self._scroll_to_bottom)
    
    def _auto_scroll_log(self):
        """ログの自動スクロール"""
        if self.is_processing:
            self._scroll_to_bottom()
    
    def _scroll_to_bottom(self):
        """ログを最下部にスクロール"""
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_log(self):
        """ログをクリア"""
        self.log_text.clear()
        self.add_log(LogLevel.INFO, "ログがクリアされました")
    
    def get_log_content(self) -> str:
        """ログの内容を取得"""
        return self.log_text.toPlainText()
    
    def save_log_to_file(self, filepath: str) -> bool:
        """ログをファイルに保存"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.get_log_content())
            self.add_log(LogLevel.INFO, f"ログを保存しました: {filepath}")
            return True
        except Exception as e:
            self.add_log(LogLevel.ERROR, f"ログの保存に失敗しました: {str(e)}")
            return False
    
    def set_file_count(self, total: int):
        """総ファイル数を設定"""
        self.total_files = total
        self.processed_files = 0
        if total > 0:
            self.add_log(LogLevel.INFO, f"処理対象: {total}個のファイル")
    
    def apply_theme(self, theme_manager):
        """テーマを適用"""
        self.theme_manager = theme_manager
        colors = theme_manager.get_colors()
        
        # プログレスバーのスタイル
        self.overall_progress.setStyleSheet(theme_manager.generate_progress_style("overall"))
        self.file_progress.setStyleSheet(theme_manager.generate_progress_style("file"))
        
        # ログテキストのスタイル（HTMLコンテンツとの整合性を確保）
        log_style = theme_manager.generate_log_style()
        self.log_text.setStyleSheet(log_style)
        
        # フレームのスタイル（進捗情報とログセクション）
        frame_style = theme_manager.generate_frame_style("default")
        # ウィジェット内のすべてのフレームにスタイルを適用
        frames = self.findChildren(QFrame)
        for frame in frames:
            frame.setStyleSheet(frame_style)
        
        # ステータスラベルの色を更新
        status_style = f"""
            QLabel {{
                color: {colors['text_secondary']};
                font-style: italic;
                padding: 5px;
                background-color: {colors['surface_variant']};
                border-radius: 4px;
            }}
        """
        self.status_label.setStyleSheet(status_style)
        
        # クリアボタンのスタイル
        clear_button_style = theme_manager.generate_button_style("secondary")
        clear_button_style = clear_button_style.replace("padding: 8px 16px;", "padding: 4px 12px; font-size: 12px;")
        self.clear_log_button.setStyleSheet(clear_button_style)
        
        # 既存のログを再描画してテーマ反映
        self._reformat_existing_logs()
    
    def _reformat_existing_logs(self):
        """既存のログをテーマに合わせて再フォーマット"""
        if not hasattr(self, 'theme_manager') or not self.theme_manager:
            return
            
        # 現在のログ内容を取得
        current_text = self.log_text.toPlainText()
        if not current_text.strip():
            return
            
        # ログをクリアして、テーマ適用済みメッセージを追加
        self.log_text.clear()
        self.add_log(LogLevel.INFO, "テーマが適用されました")