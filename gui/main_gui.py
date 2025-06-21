"""
PDFTranslate2md GUI メインアプリケーション
PyQt5ベースのデスクトップGUIアプリケーション
"""

import sys
import os
import logging
from typing import Optional, Dict, Any
import traceback

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QLabel, QComboBox, 
                             QPushButton, QLineEdit, QCheckBox, QGroupBox,
                             QSplitter, QMessageBox, QStatusBar, QMenuBar,
                             QAction, QFileDialog, QDialog, QDialogButtonBox,
                             QTextEdit, QProgressDialog)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot, QThread, QSettings
from PyQt5.QtGui import QIcon, QFont, QPixmap, QDesktopServices
from PyQt5.Qt import QUrl

from gui.gui_app_controller import GuiAppController, ProcessingSignals
from gui.history_manager import ProcessingHistory
from gui.widgets import FileDropWidget, ProgressWidget, HistoryWidget
from gui.theme_manager import get_theme_manager
from gui.notification_manager import NotificationManager
from gui.settings_dialog import SettingsDialog


class AboutDialog(QDialog):
    """アバウトダイアログ"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PDFTranslate2md について")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout()
        
        # タイトル
        title = QLabel("PDFTranslate2md")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 説明
        description = QLabel(
            "PDFファイルをAI翻訳してMarkdownファイルに変換するツール\n\n"
            "対応プロバイダー:\n"
            "• Google Gemini\n"
            "• OpenAI GPT\n"
            "• Anthropic Claude\n\n"
            "機能:\n"
            "• PDF テキスト・画像抽出\n"
            "• AI による翻訳\n"
            "• Markdown 形式での出力\n"
            "• 処理履歴の管理\n"
            "• バッチ処理対応"
        )
        description.setAlignment(Qt.AlignCenter)
        description.setWordWrap(True)
        layout.addWidget(description)
        
        # 閉じるボタン
        close_button = QPushButton("閉じる")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
        
        self.setLayout(layout)


class MainWindow(QMainWindow):
    """メインウィンドウ"""
    
    def __init__(self):
        super().__init__()
        
        # アプリケーション設定
        self.settings = QSettings('PDFTranslate2md', 'GUI')
        
        # 制御層
        self.controller: Optional[GuiAppController] = None
        
        # 履歴保存管理フラグ
        self._history_saved_for_current_session = False
        
        # テーマ管理
        self.theme_manager = get_theme_manager()
        self.theme_manager.theme_changed.connect(self._on_theme_changed)
        
        # 通知管理
        self.notification_manager = NotificationManager(self)
        self._load_notification_settings()
        
        # UI初期化
        self._setup_ui()
        self._setup_menu()
        self._setup_status_bar()
        self._load_settings()
        
        # ウィンドウ設定
        self.setWindowTitle("PDFTranslate2md - PDF翻訳ツール")
        self.resize(1200, 800)
        
        # 初期状態
        self._reset_ui_state()
        
        # プロバイダー情報を読み込み
        self._load_provider_info()
        
        # テーマを適用
        self._apply_theme()
    
    def _setup_ui(self):
        """UIの設定"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # メインレイアウト
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(10)
        
        # スプリッター
        splitter = QSplitter(Qt.Horizontal)
        
        # 左パネル（設定）
        left_panel = self._create_left_panel()
        splitter.addWidget(left_panel)
        
        # 右パネル（履歴）
        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)
        
        # 分割比率設定
        splitter.setSizes([800, 400])
        
        main_layout.addWidget(splitter)
    
    def _create_left_panel(self) -> QWidget:
        """左パネル（設定・進捗）を作成"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(15)
        
        # 入力設定グループ
        input_group = QGroupBox("入力設定")
        input_layout = QVBoxLayout()
        
        self.file_drop_widget = FileDropWidget()
        self.file_drop_widget.path_selected.connect(self._on_input_path_changed)
        input_layout.addWidget(self.file_drop_widget)
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # 翻訳設定グループ
        translation_group = QGroupBox("翻訳設定")
        translation_layout = QVBoxLayout()
        
        # プロバイダー選択
        provider_layout = QHBoxLayout()
        provider_layout.addWidget(QLabel("プロバイダー:"))
        
        self.provider_combo = QComboBox()
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        provider_layout.addWidget(self.provider_combo)
        
        self.test_provider_button = QPushButton("🔍 接続テスト")
        self.test_provider_button.clicked.connect(self._test_provider_connection)
        # スタイルはテーマ適用時に設定
        provider_layout.addWidget(self.test_provider_button)
        
        translation_layout.addLayout(provider_layout)
        
        # モデル選択
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("モデル:"))
        
        self.model_combo = QComboBox()
        model_layout.addWidget(self.model_combo)
        
        translation_layout.addLayout(model_layout)
        
        translation_group.setLayout(translation_layout)
        layout.addWidget(translation_group)
        
        # 出力設定グループ
        output_group = QGroupBox("出力設定")
        output_layout = QVBoxLayout()
        
        # 出力ディレクトリ
        output_dir_layout = QHBoxLayout()
        output_dir_layout.addWidget(QLabel("出力先:"))
        
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("出力ディレクトリを選択...")
        output_dir_layout.addWidget(self.output_dir_edit)
        
        self.output_dir_button = QPushButton("📁")
        self.output_dir_button.clicked.connect(self._select_output_dir)
        self.output_dir_button.setFixedSize(30, 30)
        output_dir_layout.addWidget(self.output_dir_button)
        
        output_layout.addLayout(output_dir_layout)
        
        # 画像ディレクトリ
        image_dir_layout = QHBoxLayout()
        image_dir_layout.addWidget(QLabel("画像保存先:"))
        
        self.image_dir_edit = QLineEdit()
        self.image_dir_edit.setPlaceholderText("画像ディレクトリを選択...")
        image_dir_layout.addWidget(self.image_dir_edit)
        
        self.image_dir_button = QPushButton("📁")
        self.image_dir_button.clicked.connect(self._select_image_dir)
        self.image_dir_button.setFixedSize(30, 30)
        image_dir_layout.addWidget(self.image_dir_button)
        
        output_layout.addLayout(image_dir_layout)
        
        # オプション
        self.force_overwrite_check = QCheckBox("既存ファイルを強制上書き")
        output_layout.addWidget(self.force_overwrite_check)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        # 処理制御ボタン
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("🚀 処理開始")
        self.start_button.clicked.connect(self._start_processing)
        # スタイルはテーマ適用時に設定
        button_layout.addWidget(self.start_button)
        
        self.cancel_button = QPushButton("⏹️ キャンセル")
        self.cancel_button.clicked.connect(self._cancel_processing)
        self.cancel_button.setEnabled(False)
        # スタイルはテーマ適用時に設定
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # 進捗ウィジェット
        self.progress_widget = ProgressWidget()
        layout.addWidget(self.progress_widget)
        
        return panel
    
    def _create_right_panel(self) -> QWidget:
        """右パネル（履歴）を作成"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 履歴ウィジェット
        self.history_widget = HistoryWidget()
        self.history_widget.history_applied.connect(self._apply_history)
        layout.addWidget(self.history_widget)
        
        return panel
    
    def _setup_menu(self):
        """メニューバーの設定"""
        menubar = self.menuBar()
        
        # ファイルメニュー
        file_menu = menubar.addMenu("ファイル(&F)")
        
        open_action = QAction("開く(&O)", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_file_dialog)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("終了(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 編集メニュー
        edit_menu = menubar.addMenu("編集(&E)")
        
        settings_action = QAction("設定(&S)", self)
        settings_action.triggered.connect(self._show_settings)
        edit_menu.addAction(settings_action)
        
        # ヘルプメニュー
        help_menu = menubar.addMenu("ヘルプ(&H)")
        
        about_action = QAction("このアプリケーションについて(&A)", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
        
        help_menu.addSeparator()
        
        readme_action = QAction("README を開く", self)
        readme_action.triggered.connect(self._open_readme)
        help_menu.addAction(readme_action)
    
    def _setup_status_bar(self):
        """ステータスバーの設定"""
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("準備完了")
        
        # プロバイダー状態表示
        self.provider_status_label = QLabel("プロバイダー: 未設定")
        self.status_bar.addPermanentWidget(self.provider_status_label)
    
    def _load_settings(self):
        """設定を読み込み"""
        # ウィンドウ位置・サイズ
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        # 最後の設定
        last_provider = self.settings.value("last_provider", "")
        last_model = self.settings.value("last_model", "")
        last_output_dir = self.settings.value("last_output_dir", "")
        last_image_dir = self.settings.value("last_image_dir", "")
        force_overwrite = self.settings.value("force_overwrite", False, type=bool)
        
        if last_output_dir:
            self.output_dir_edit.setText(last_output_dir)
        if last_image_dir:
            self.image_dir_edit.setText(last_image_dir)
        
        self.force_overwrite_check.setChecked(force_overwrite)
    
    def _save_settings(self):
        """設定を保存"""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("last_provider", self.provider_combo.currentData())
        self.settings.setValue("last_model", self.model_combo.currentText())
        self.settings.setValue("last_output_dir", self.output_dir_edit.text())
        self.settings.setValue("last_image_dir", self.image_dir_edit.text())
        self.settings.setValue("force_overwrite", self.force_overwrite_check.isChecked())
    
    def _load_provider_info(self):
        """プロバイダー情報を読み込み"""
        try:
            # 一時的にコントローラーを作成してプロバイダー情報を取得
            temp_controller = GuiAppController("gemini")  # デフォルト
            providers = temp_controller.get_available_providers()
            
            self.provider_combo.clear()
            for provider in providers:
                self.provider_combo.addItem(provider['name'], provider['id'])
            
            # 最後の設定を復元
            last_provider = self.settings.value("last_provider", "")
            if last_provider:
                index = self.provider_combo.findData(last_provider)
                if index >= 0:
                    self.provider_combo.setCurrentIndex(index)
            
            self._on_provider_changed()
            
        except Exception as e:
            self.progress_widget.add_log("ERROR", f"プロバイダー情報の読み込みに失敗: {str(e)}")
    
    def _reset_ui_state(self):
        """UIの状態をリセット"""
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.status_bar.showMessage("準備完了")
        
        # 履歴保存フラグをリセット（新しい処理に備える）
        self._history_saved_for_current_session = False
    
    @pyqtSlot()
    def _on_provider_changed(self):
        """プロバイダーが変更された時"""
        provider_id = self.provider_combo.currentData()
        if not provider_id:
            return
        
        try:
            # 一時的にコントローラーを作成してモデル情報を取得
            temp_controller = GuiAppController(provider_id)
            models = temp_controller.get_available_models(provider_id)
            
            self.model_combo.clear()
            self.model_combo.addItems(models)
            
            # 最後の設定を復元
            if provider_id == self.settings.value("last_provider", ""):
                last_model = self.settings.value("last_model", "")
                if last_model and last_model in models:
                    self.model_combo.setCurrentText(last_model)
            
            # プロバイダー状態を更新
            self._update_provider_status()
            
        except Exception as e:
            self.progress_widget.add_log("ERROR", f"モデル情報の読み込みに失敗: {str(e)}")
    
    @pyqtSlot(str)
    def _on_input_path_changed(self, path: str):
        """入力パスが変更された時"""
        if path:
            # 出力ディレクトリが未設定の場合、入力パスと同じディレクトリを設定
            if not self.output_dir_edit.text():
                if os.path.isfile(path):
                    default_output = os.path.dirname(path)
                else:
                    default_output = path
                self.output_dir_edit.setText(default_output)
            
            # 画像ディレクトリが未設定の場合、出力ディレクトリ/imagesを設定
            if not self.image_dir_edit.text():
                output_dir = self.output_dir_edit.text()
                if output_dir:
                    self.image_dir_edit.setText(os.path.join(output_dir, "images"))
    
    def _update_provider_status(self):
        """プロバイダー状態を更新"""
        provider_id = self.provider_combo.currentData()
        model = self.model_combo.currentText()
        
        if provider_id and model:
            self.provider_status_label.setText(f"プロバイダー: {provider_id} / {model}")
        else:
            self.provider_status_label.setText("プロバイダー: 未設定")
    
    def _test_provider_connection(self):
        """プロバイダー接続をテスト"""
        provider_id = self.provider_combo.currentData()
        model = self.model_combo.currentText()
        
        if not provider_id:
            QMessageBox.warning(self, "エラー", "プロバイダーを選択してください。")
            return
        
        try:
            temp_controller = GuiAppController(provider_id, model)
            success, message = temp_controller.test_provider_connection(provider_id, model)
            
            if success:
                QMessageBox.information(self, "接続テスト", f"✅ {message}")
                self.progress_widget.add_log("INFO", f"接続テスト成功: {message}")
            else:
                QMessageBox.warning(self, "接続テスト", f"❌ {message}")
                self.progress_widget.add_log("ERROR", f"接続テスト失敗: {message}")
                
        except Exception as e:
            error_msg = f"接続テスト中にエラーが発生しました: {str(e)}"
            QMessageBox.critical(self, "エラー", error_msg)
            self.progress_widget.add_log("ERROR", error_msg)
    
    def _select_output_dir(self):
        """出力ディレクトリを選択"""
        dir_path = QFileDialog.getExistingDirectory(self, "出力ディレクトリを選択")
        if dir_path:
            self.output_dir_edit.setText(dir_path)
            
            # 画像ディレクトリが未設定の場合、自動設定
            if not self.image_dir_edit.text():
                self.image_dir_edit.setText(os.path.join(dir_path, "images"))
    
    def _select_image_dir(self):
        """画像ディレクトリを選択"""
        dir_path = QFileDialog.getExistingDirectory(self, "画像ディレクトリを選択")
        if dir_path:
            self.image_dir_edit.setText(dir_path)
    
    def _start_processing(self):
        """処理を開始"""
        # 入力検証
        input_path = self.file_drop_widget.get_selected_path()
        if not input_path:
            QMessageBox.warning(self, "エラー", "入力ファイルまたはフォルダを選択してください。")
            return
        
        provider_id = self.provider_combo.currentData()
        model = self.model_combo.currentText()
        if not provider_id or not model:
            QMessageBox.warning(self, "エラー", "プロバイダーとモデルを選択してください。")
            return
        
        output_dir = self.output_dir_edit.text().strip()
        if not output_dir:
            QMessageBox.warning(self, "エラー", "出力ディレクトリを指定してください。")
            return
        
        image_dir = self.image_dir_edit.text().strip()
        if not image_dir:
            image_dir = os.path.join(output_dir, "images")
            self.image_dir_edit.setText(image_dir)
        
        force_overwrite = self.force_overwrite_check.isChecked()
        
        try:
            # コントローラーを作成
            self.controller = GuiAppController(provider_id, model)
            
            # 非同期処理を開始
            signals = self.controller.start_processing_async(
                input_path, output_dir, image_dir, force_overwrite
            )
            
            # シグナル接続（Qt.QueuedConnectionを明示的に指定）
            from PyQt5.QtCore import Qt
            signals.progress_updated.connect(self.progress_widget.update_overall_progress, Qt.QueuedConnection)
            signals.file_started.connect(self.progress_widget.start_file_processing, Qt.QueuedConnection)
            signals.file_completed.connect(self.progress_widget.finish_file_processing, Qt.QueuedConnection)
            signals.page_progress.connect(self.progress_widget.update_page_progress, Qt.QueuedConnection)
            signals.error_occurred.connect(self.progress_widget.show_error, Qt.QueuedConnection)
            signals.processing_finished.connect(self._on_processing_finished, Qt.QueuedConnection)
            signals.log_message.connect(self.progress_widget.add_log, Qt.QueuedConnection)
            
            # UI状態更新
            self.start_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            self.status_bar.showMessage("処理中...")
            
            # 進捗ウィジェット初期化
            self.progress_widget.start_processing("処理を開始しています...")
            
            # 履歴ウィジェットの翻訳状態を設定（タイマー停止）
            self.history_widget.set_translation_state(True)
            
            # 履歴に追加
            self._save_current_settings_to_history()
            
        except Exception as e:
            error_msg = f"処理の開始に失敗しました: {str(e)}"
            QMessageBox.critical(self, "エラー", error_msg)
            self.progress_widget.add_log("ERROR", error_msg)
            self._reset_ui_state()
    
    def _cancel_processing(self):
        """処理をキャンセル"""
        if self.controller:
            reply = QMessageBox.question(
                self,
                "処理キャンセル",
                "処理をキャンセルしますか？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                if self.controller.cancel_processing():
                    self.progress_widget.add_log("WARNING", "処理がキャンセルされました")
                    self.status_bar.showMessage("処理がキャンセルされました")
                    # 履歴ウィジェットの翻訳状態をリセット（タイマー再開）
                    self.history_widget.set_translation_state(False)
                    # 処理キャンセル通知
                    self.notification_manager.notify_processing_cancelled("処理がキャンセルされました")
                    self._reset_ui_state()
    
    @pyqtSlot(bool, str)
    def _on_processing_finished(self, success: bool, message: str):
        """処理完了時のコールバック"""
        self.progress_widget.finish_processing(success, message)
        
        # 履歴ウィジェットの翻訳状態をリセット（タイマー再開）
        self.history_widget.set_translation_state(False)
        
        # 通知を先に送信（ダイアログ表示と同時）
        if success:
            self.status_bar.showMessage("処理完了")
            self.notification_manager.notify_processing_completed(True, "処理完了", "翻訳処理が正常に完了しました。")
            QMessageBox.information(self, "処理完了", "翻訳処理が正常に完了しました。")
        else:
            self.status_bar.showMessage("処理失敗")
            self.notification_manager.notify_processing_completed(False, "処理失敗", f"処理中にエラーが発生しました:\n{message}")
            QMessageBox.warning(self, "処理失敗", f"処理中にエラーが発生しました:\n{message}")
        
        self._reset_ui_state()
        self.controller = None
    
    def _save_current_settings_to_history(self):
        """現在の設定を履歴に保存（重複防止機能付き）"""
        # 重複保存防止ガード
        if self._history_saved_for_current_session:
            self.progress_widget.add_log("DEBUG", "履歴は既に保存済みです（重複保存を回避）")
            return
            
        try:
            input_path = self.file_drop_widget.get_selected_path()
            provider_id = self.provider_combo.currentData()
            model = self.model_combo.currentText()
            output_dir = self.output_dir_edit.text()
            image_dir = self.image_dir_edit.text()
            force_overwrite = self.force_overwrite_check.isChecked()
            
            # 履歴名を生成
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            name = f"{os.path.basename(input_path)} ({timestamp})"
            
            self.history_widget.add_history(
                name, input_path, provider_id, model,
                output_dir, image_dir, force_overwrite
            )
            
            # 履歴保存フラグを設定
            self._history_saved_for_current_session = True
            self.progress_widget.add_log("INFO", "設定を履歴に保存しました")
            
        except Exception as e:
            self.progress_widget.add_log("WARNING", f"履歴保存に失敗: {str(e)}")
    
    @pyqtSlot(object)
    def _apply_history(self, history: ProcessingHistory):
        """履歴を適用"""
        try:
            # ファイルパス
            self.file_drop_widget.set_selected_path(history.input_path)
            
            # プロバイダー
            provider_index = self.provider_combo.findData(history.provider)
            if provider_index >= 0:
                self.provider_combo.setCurrentIndex(provider_index)
                # モデルを設定（プロバイダー変更後に設定）
                QTimer.singleShot(100, lambda: self.model_combo.setCurrentText(history.model))
            
            # 出力設定
            self.output_dir_edit.setText(history.output_dir)
            self.image_dir_edit.setText(history.image_dir)
            self.force_overwrite_check.setChecked(history.force_overwrite)
            
            self.progress_widget.add_log("INFO", f"履歴を適用しました: {history.name}")
            self.status_bar.showMessage(f"履歴を適用: {history.name}")
            
        except Exception as e:
            error_msg = f"履歴の適用に失敗しました: {str(e)}"
            QMessageBox.warning(self, "エラー", error_msg)
            self.progress_widget.add_log("ERROR", error_msg)
    
    def _open_file_dialog(self):
        """ファイル選択ダイアログを開く"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "PDFファイルを選択",
            "",
            "PDFファイル (*.pdf)"
        )
        
        if file_path:
            self.file_drop_widget.set_selected_path(file_path)
    
    def _show_settings(self):
        """設定ダイアログを表示"""
        dialog = SettingsDialog(self)
        
        # 現在の設定を読み込み
        notification_settings = self.notification_manager.get_notification_settings()
        dialog.load_settings(notification_settings)
        
        if dialog.exec_() == QDialog.Accepted:
            # 通知設定を保存
            notification_settings = dialog.get_notification_settings()
            self.notification_manager.set_notification_settings(notification_settings)
            self._save_notification_settings()
    
    def _show_about(self):
        """アバウトダイアログを表示"""
        dialog = AboutDialog(self)
        dialog.exec_()
    
    def _open_readme(self):
        """READMEを開く"""
        readme_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "README.md")
        if os.path.exists(readme_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(readme_path))
        else:
            QMessageBox.information(self, "情報", "README.mdファイルが見つかりません。")
    
    def closeEvent(self, event):
        """ウィンドウ閉じる時の処理"""
        # 処理中の場合は確認
        if self.controller and self.controller.is_processing:
            reply = QMessageBox.question(
                self,
                "終了確認",
                "処理が実行中です。終了しますか？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                event.ignore()
                return
            
            # 処理をキャンセル
            self.controller.cancel_processing()
        
        # 設定を保存
        self._save_settings()
        self._save_notification_settings()
        
        # 通知マネージャーをクリーンアップ
        if hasattr(self, 'notification_manager'):
            self.notification_manager.cleanup()
        
        event.accept()
    
    def _apply_theme(self):
        """テーマを適用"""
        # ボタンのスタイルを更新
        self.test_provider_button.setStyleSheet(self.theme_manager.generate_button_style("info"))
        
        # 処理制御ボタンのスタイルを更新
        start_style = self.theme_manager.generate_button_style("success")
        start_style = start_style.replace("padding: 8px 16px;", "padding: 12px 24px; font-size: 14px;")
        self.start_button.setStyleSheet(start_style)
        
        cancel_style = self.theme_manager.generate_button_style("danger")
        cancel_style = cancel_style.replace("padding: 8px 16px;", "padding: 12px 24px; font-size: 14px;")
        self.cancel_button.setStyleSheet(cancel_style)
        
        # 出力ディレクトリ選択ボタンのスタイル
        dir_button_style = self.theme_manager.generate_button_style("secondary")
        dir_button_style = dir_button_style.replace("padding: 8px 16px;", "padding: 4px 8px;")
        self.output_dir_button.setStyleSheet(dir_button_style)
        self.image_dir_button.setStyleSheet(dir_button_style)
        
        # 子ウィジェットにもテーマを適用
        if hasattr(self, 'file_drop_widget'):
            self.file_drop_widget.apply_theme(self.theme_manager)
        if hasattr(self, 'progress_widget'):
            self.progress_widget.apply_theme(self.theme_manager)
        if hasattr(self, 'history_widget'):
            self.history_widget.apply_theme(self.theme_manager)
    
    def _on_theme_changed(self, theme_name: str):
        """テーマが変更された時の処理"""
        self._apply_theme()
    
    def _load_notification_settings(self):
        """通知設定を読み込み"""
        settings = self.settings.value("notification_settings", {})
        if settings:
            self.notification_manager.set_notification_settings(settings)
    
    def _save_notification_settings(self):
        """通知設定を保存"""
        settings = self.notification_manager.get_notification_settings()
        self.settings.setValue("notification_settings", settings)


def main():
    """メイン関数"""
    # アプリケーション作成
    app = QApplication(sys.argv)
    app.setApplicationName("PDFTranslate2md")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("PDFTranslate2md")
    
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('gui_pdftranslate2md.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    try:
        # メインウィンドウ作成・表示
        window = MainWindow()
        window.show()
        
        # イベントループ実行
        sys.exit(app.exec_())
        
    except Exception as e:
        error_msg = f"アプリケーションの起動に失敗しました:\n{str(e)}\n\n{traceback.format_exc()}"
        print(error_msg)
        
        # エラーダイアログ表示
        try:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("起動エラー")
            msg_box.setText("アプリケーションの起動に失敗しました。")
            msg_box.setDetailedText(error_msg)
            msg_box.exec_()
        except:
            pass
        
        sys.exit(1)


if __name__ == "__main__":
    main()