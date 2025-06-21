"""
設定ダイアログモジュール
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, 
                             QLabel, QComboBox, QPushButton, QLineEdit, 
                             QCheckBox, QGroupBox, QDialogButtonBox, QWidget,
                             QFileDialog)
from PyQt5.QtCore import Qt


class SettingsDialog(QDialog):
    """設定ダイアログ"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("設定")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout()
        
        # タブウィジェット
        tab_widget = QTabWidget()
        
        # API設定タブ
        api_tab = self._create_api_tab()
        tab_widget.addTab(api_tab, "API設定")
        
        # UI設定タブ
        ui_tab = self._create_ui_tab()
        tab_widget.addTab(ui_tab, "UI設定")
        
        # 通知設定タブ
        notification_tab = self._create_notification_tab()
        tab_widget.addTab(notification_tab, "通知設定")
        
        layout.addWidget(tab_widget)
        
        # ボタン
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def _create_api_tab(self) -> QWidget:
        """API設定タブを作成"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        api_info = QLabel(
            "API設定は環境変数（.env）ファイルで設定してください。\n"
            "詳細はREADME.mdを参照してください。"
        )
        api_info.setWordWrap(True)
        layout.addWidget(api_info)
        
        return tab
    
    def _create_ui_tab(self) -> QWidget:
        """UI設定タブを作成"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.auto_save_history = QCheckBox("履歴を自動保存する")
        self.auto_save_history.setChecked(True)
        layout.addWidget(self.auto_save_history)
        
        self.confirm_overwrite = QCheckBox("既存ファイル上書き時に確認する")
        self.confirm_overwrite.setChecked(True)
        layout.addWidget(self.confirm_overwrite)
        
        return tab
    
    def _create_notification_tab(self) -> QWidget:
        """通知設定タブを作成"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 通知設定グループ
        notification_group = QGroupBox("通知設定")
        notification_layout = QVBoxLayout()
        
        self.enable_os_notifications = QCheckBox("OS通知を有効にする")
        self.enable_os_notifications.setChecked(True)
        self.enable_os_notifications.setToolTip("処理完了時にOSの通知機能を使用します（標準通知音付き）")
        self.enable_os_notifications.toggled.connect(self._on_os_notification_toggled)
        notification_layout.addWidget(self.enable_os_notifications)
        
        self.enable_sound_notifications = QCheckBox("独自音声通知を有効にする")
        self.enable_sound_notifications.setChecked(False)
        self.enable_sound_notifications.setToolTip("OS通知を使用していない場合のみ有効です。OS通知を使用している場合はOSが自動的に効果音を鳴らします。")
        notification_layout.addWidget(self.enable_sound_notifications)
        
        # カスタム音声ファイル設定
        sound_layout = QHBoxLayout()
        sound_layout.addWidget(QLabel("カスタム音声ファイル:"))
        
        self.sound_file_edit = QLineEdit()
        self.sound_file_edit.setPlaceholderText("カスタム音声ファイルを選択...")
        sound_layout.addWidget(self.sound_file_edit)
        
        self.sound_file_button = QPushButton("📁")
        self.sound_file_button.clicked.connect(self._select_sound_file)
        self.sound_file_button.setFixedSize(30, 30)
        sound_layout.addWidget(self.sound_file_button)
        
        notification_layout.addLayout(sound_layout)
        
        # テスト通知ボタン
        test_layout = QHBoxLayout()
        
        self.test_success_notification = QPushButton("✅ 成功通知テスト")
        self.test_success_notification.clicked.connect(self._test_success_notification)
        test_layout.addWidget(self.test_success_notification)
        
        self.test_error_notification = QPushButton("❌ エラー通知テスト")
        self.test_error_notification.clicked.connect(self._test_error_notification)
        test_layout.addWidget(self.test_error_notification)
        
        notification_layout.addLayout(test_layout)
        
        notification_group.setLayout(notification_layout)
        layout.addWidget(notification_group)
        
        # 通知履歴グループ
        history_group = QGroupBox("通知履歴")
        history_layout = QVBoxLayout()
        
        self.show_notification_history = QPushButton("通知履歴を表示")
        self.show_notification_history.clicked.connect(self._show_notification_history)
        history_layout.addWidget(self.show_notification_history)
        
        history_group.setLayout(history_layout)
        layout.addWidget(history_group)
        
        return tab
    
    def _select_sound_file(self):
        """音声ファイルを選択"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "音声ファイルを選択",
            "",
            "音声ファイル (*.wav *.mp3 *.ogg *.aiff *.m4a)"
        )
        
        if file_path:
            self.sound_file_edit.setText(file_path)
    
    def _test_success_notification(self):
        """成功通知をテスト"""
        if hasattr(self.parent(), 'notification_manager'):
            self.parent().notification_manager.notify_processing_completed(
                True, "翻訳処理が正常に完了しました", "テスト用の通知です"
            )
    
    def _test_error_notification(self):
        """エラー通知をテスト"""
        if hasattr(self.parent(), 'notification_manager'):
            self.parent().notification_manager.notify_processing_completed(
                False, "処理中にエラーが発生しました", "テスト用の通知です"
            )
    
    def _show_notification_history(self):
        """通知履歴を表示"""
        if hasattr(self.parent(), 'notification_manager'):
            # 通知履歴を表示する処理はNotificationManager内で実装済み
            pass
    
    def _on_os_notification_toggled(self, checked: bool):
        """OS通知の有効/無効切り替え時の処理"""
        if checked:
            # OS通知を有効にした場合、独自音声通知を無効にする
            self.enable_sound_notifications.setChecked(False)
            self.enable_sound_notifications.setEnabled(False)
        else:
            # OS通知を無効にした場合、独自音声通知を有効にできるようにする
            self.enable_sound_notifications.setEnabled(True)
    
    def load_settings(self, notification_settings: dict):
        """設定を読み込み"""
        self.enable_os_notifications.setChecked(notification_settings.get('enable_os_notifications', True))
        self.enable_sound_notifications.setChecked(notification_settings.get('enable_sound_notifications', False))
        self.sound_file_edit.setText(notification_settings.get('sound_file_path', ''))
        
        # OS通知の状態に応じて独自音声通知の有効/無効を設定
        if self.enable_os_notifications.isChecked():
            self.enable_sound_notifications.setChecked(False)
            self.enable_sound_notifications.setEnabled(False)
        else:
            self.enable_sound_notifications.setEnabled(True)
    
    def get_notification_settings(self) -> dict:
        """通知設定を取得"""
        return {
            'enable_os_notifications': self.enable_os_notifications.isChecked(),
            'enable_sound_notifications': self.enable_sound_notifications.isChecked(),
            'sound_file_path': self.sound_file_edit.text()
        } 