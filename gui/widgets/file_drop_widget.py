"""
ファイル・フォルダドラッグ&ドロップ対応ウィジェット
"""

import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFileDialog, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QPalette, QFont


class FileDropWidget(QFrame):
    """
    ファイル・フォルダのドラッグ&ドロップに対応したウィジェット
    """
    
    # シグナル
    path_selected = pyqtSignal(str)  # パスが選択された時
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.selected_path = ""
        self.accept_files = True
        self.accept_folders = True
        self.file_filter = "PDFファイル (*.pdf)"
        
        self._setup_ui()
        self._setup_drag_drop()
    
    def _setup_ui(self):
        """UIの設定"""
        self.setFrameStyle(QFrame.StyledPanel)
        # スタイルはテーマ適用時に設定
        
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(15)
        
        # アイコンラベル
        self.icon_label = QLabel("📁")
        self.icon_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(32)
        self.icon_label.setFont(font)
        
        # メインメッセージ
        self.main_label = QLabel("PDFファイルまたはフォルダをここにドラッグ&ドロップ")
        self.main_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.main_label.setFont(font)
        
        # サブメッセージ
        self.sub_label = QLabel("または下のボタンをクリックして選択")
        self.sub_label.setAlignment(Qt.AlignCenter)
        self.sub_label.setStyleSheet("color: #666666;")
        
        # 選択されたパス表示
        self.path_label = QLabel("")
        self.path_label.setAlignment(Qt.AlignCenter)
        # スタイルはテーマ適用時に設定
        self.path_label.hide()
        
        # ボタンレイアウト
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # ファイル/フォルダ選択ボタン（統一）
        self.select_button = QPushButton("📁 ファイル/フォルダ選択")
        self.select_button.clicked.connect(self._select_file_or_folder)
        # スタイルはテーマ適用時に設定
        
        # クリアボタン
        self.clear_button = QPushButton("🗑️ クリア")
        self.clear_button.clicked.connect(self._clear_selection)
        # スタイルはテーマ適用時に設定
        self.clear_button.hide()
        
        button_layout.addWidget(self.select_button)
        button_layout.addWidget(self.clear_button)
        
        # レイアウトに追加
        layout.addWidget(self.icon_label)
        layout.addWidget(self.main_label)
        layout.addWidget(self.sub_label)
        layout.addWidget(self.path_label)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.setMinimumHeight(200)
    
    def _setup_drag_drop(self):
        """ドラッグ&ドロップの設定"""
        self.setAcceptDrops(True)
    
    def set_file_filter(self, file_filter: str):
        """ファイルフィルターを設定"""
        self.file_filter = file_filter
    
    def set_accept_files(self, accept: bool):
        """ファイル受け入れの設定"""
        self.accept_files = accept
        self._update_button_text()
    
    def set_accept_folders(self, accept: bool):
        """フォルダ受け入れの設定"""
        self.accept_folders = accept
        self._update_button_text()
    
    def _update_button_text(self):
        """ボタンのテキストを更新"""
        if self.accept_files and self.accept_folders:
            self.select_button.setText("📁 ファイル/フォルダ選択")
        elif self.accept_files:
            self.select_button.setText("📄 ファイル選択")
        elif self.accept_folders:
            self.select_button.setText("📁 フォルダ選択")
        else:
            self.select_button.setText("選択")
    
    def get_selected_path(self) -> str:
        """選択されたパスを取得"""
        return self.selected_path
    
    def set_selected_path(self, path: str):
        """パスを設定"""
        if path and os.path.exists(path):
            self.selected_path = path
            self._update_display()
            self.path_selected.emit(path)
    
    def _update_display(self):
        """表示を更新"""
        if self.selected_path:
            # パスを短縮表示
            display_path = self.selected_path
            if len(display_path) > 60:
                display_path = "..." + display_path[-57:]
            
            self.path_label.setText(f"選択中: {display_path}")
            self.path_label.show()
            self.clear_button.show()
            
            # アイコンとメッセージを更新
            if os.path.isfile(self.selected_path):
                self.icon_label.setText("📄")
                self.main_label.setText("ファイルが選択されています")
            else:
                self.icon_label.setText("📁")
                self.main_label.setText("フォルダが選択されています")
            
            self.sub_label.setText("別のファイル/フォルダを選択するか、クリアしてください")
            
            # スタイルはテーマ適用時に設定
            if hasattr(self, 'theme_manager'):
                self.setStyleSheet(self.theme_manager.generate_frame_style("drop_area_selected"))
        else:
            self.path_label.hide()
            self.clear_button.hide()
            
            # 初期状態に戻す
            self.icon_label.setText("📁")
            self.main_label.setText("PDFファイルまたはフォルダをここにドラッグ&ドロップ")
            self.sub_label.setText("または下のボタンをクリックして選択")
            
            # スタイルはテーマ適用時に設定
            if hasattr(self, 'theme_manager'):
                self.setStyleSheet(self.theme_manager.generate_frame_style("drop_area"))
    
    def _select_file_or_folder(self):
        """ファイル/フォルダ選択ダイアログを開く（統一）"""
        from PyQt5.QtWidgets import QMenu, QAction
        
        # メニューを作成してファイルとフォルダの選択肢を提供
        menu = QMenu(self)
        
        if self.accept_files:
            file_action = QAction("📄 ファイル選択", self)
            file_action.triggered.connect(self._select_file)
            menu.addAction(file_action)
        
        if self.accept_folders:
            folder_action = QAction("📁 フォルダ選択", self)
            folder_action.triggered.connect(self._select_folder)
            menu.addAction(folder_action)
        
        # ボタンの下にメニューを表示
        button_pos = self.select_button.mapToGlobal(self.select_button.rect().bottomLeft())
        menu.exec_(button_pos)
    
    def _select_file(self):
        """ファイル選択ダイアログを開く"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "PDFファイルを選択",
            "",
            self.file_filter
        )
        
        if file_path:
            self.set_selected_path(file_path)
    
    def _select_folder(self):
        """フォルダ選択ダイアログを開く"""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "フォルダを選択"
        )
        
        if folder_path:
            self.set_selected_path(folder_path)
    
    def _clear_selection(self):
        """選択をクリア"""
        self.selected_path = ""
        self._update_display()
        self.path_selected.emit("")
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """ドラッグエンター時の処理"""
        if event.mimeData().hasUrls():
            # URLがある場合は受け入れる
            event.acceptProposedAction()
            
            # ホバー時のスタイル
            if hasattr(self, 'theme_manager'):
                colors = self.theme_manager.get_colors()
                hover_style = f"""
                    QFrame {{
                        border: 2px solid {colors['drop_area_border_hover']};
                        border-radius: 10px;
                        background-color: {colors['drop_area_hover']};
                    }}
                """
                self.setStyleSheet(hover_style)
        else:
            event.ignore()
    
    def dragLeaveEvent(self, event):
        """ドラッグリーブ時の処理"""
        # 元のスタイルに戻す
        self._update_display()
    
    def dropEvent(self, event: QDropEvent):
        """ドロップ時の処理"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                # 最初のURLを取得
                file_path = urls[0].toLocalFile()
                
                # ファイル・フォルダの検証
                if os.path.exists(file_path):
                    is_file = os.path.isfile(file_path)
                    is_folder = os.path.isdir(file_path)
                    
                    if (is_file and self.accept_files) or (is_folder and self.accept_folders):
                        # PDFファイルまたはPDFファイルを含むフォルダかチェック
                        if self._is_valid_path(file_path):
                            self.set_selected_path(file_path)
                            event.acceptProposedAction()
                        else:
                            self._show_error("PDFファイルまたはPDFファイルを含むフォルダを選択してください")
                    else:
                        self._show_error("サポートされていないファイル/フォルダタイプです")
                else:
                    self._show_error("無効なパスです")
        
        # スタイルを戻す
        self._update_display()
    
    def _is_valid_path(self, path: str) -> bool:
        """パスが有効かどうかチェック"""
        if os.path.isfile(path):
            # ファイルの場合、PDFファイルかチェック
            return path.lower().endswith('.pdf')
        elif os.path.isdir(path):
            # フォルダの場合、PDFファイルが含まれているかチェック
            import glob
            pdf_files = glob.glob(os.path.join(path, "*.pdf"))
            return len(pdf_files) > 0
        return False
    
    def _show_error(self, message: str):
        """エラーメッセージを表示"""
        # 一時的にエラーメッセージを表示
        original_text = self.main_label.text()
        self.main_label.setText(f"❌ {message}")
        self.main_label.setStyleSheet("color: #dc3545;")
        
        # 3秒後に元に戻す
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(3000, lambda: self._reset_error_message(original_text))
    
    def _reset_error_message(self, original_text: str):
        """エラーメッセージをリセット"""
        self.main_label.setText(original_text)
        self.main_label.setStyleSheet("")
    
    def apply_theme(self, theme_manager):
        """テーマを適用"""
        self.theme_manager = theme_manager
        colors = theme_manager.get_colors()
        
        # 基本フレームスタイル
        if self.selected_path:
            self.setStyleSheet(theme_manager.generate_frame_style("drop_area_selected"))
        else:
            self.setStyleSheet(theme_manager.generate_frame_style("drop_area"))
        
        # 選択されたパス表示のスタイル
        path_style = f"""
            QLabel {{
                color: {colors['button_primary']};
                font-weight: bold;
                background-color: {colors['surface']};
                padding: 8px;
                border-radius: 5px;
                border: 1px solid {colors['button_primary']};
            }}
        """
        self.path_label.setStyleSheet(path_style)
        
        # ボタンのスタイル
        self.select_button.setStyleSheet(theme_manager.generate_button_style("primary"))
        self.clear_button.setStyleSheet(theme_manager.generate_button_style("danger"))
        
        # サブメッセージの色
        sub_style = f"color: {colors['text_secondary']};"
        self.sub_label.setStyleSheet(sub_style)