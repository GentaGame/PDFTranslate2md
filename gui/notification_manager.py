"""
通知管理モジュール
OS通知と音声通知を提供する
"""

import os
import platform
import subprocess
import threading
from typing import Optional
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon


class NotificationManager(QObject):
    """通知管理クラス"""
    
    # 通知シグナル
    notification_clicked = pyqtSignal(str)  # 通知ID
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # システム情報
        self.system = platform.system().lower()
        self.is_darwin = self.system == "darwin"  # macOS
        self.is_windows = self.system == "windows"
        self.is_linux = self.system == "linux"
        
        # 通知設定
        self.enable_os_notifications = True
        self.enable_sound_notifications = False  # OS通知を使用する場合は独自音声は不要
        self.sound_file_path = None
        
        # システムトレイアイコン（Windows/Linux用）
        self.system_tray = None
        self._setup_system_tray()
        
        # 通知履歴
        self.notification_history = []
        self.max_history = 10
    
    def _setup_system_tray(self):
        """システムトレイアイコンの設定"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        
        try:
            self.system_tray = QSystemTrayIcon()
            
            # アイコン設定（デフォルトアイコンまたはアプリアイコン）
            icon_path = self._get_app_icon_path()
            if icon_path and os.path.exists(icon_path):
                self.system_tray.setIcon(QIcon(icon_path))
            
            # メニュー設定
            menu = QMenu()
            
            # 通知設定
            self.os_notification_action = QAction("OS通知", self)
            self.os_notification_action.setCheckable(True)
            self.os_notification_action.setChecked(self.enable_os_notifications)
            self.os_notification_action.triggered.connect(self._toggle_os_notifications)
            menu.addAction(self.os_notification_action)
            
            self.sound_notification_action = QAction("音声通知", self)
            self.sound_notification_action.setCheckable(True)
            self.sound_notification_action.setChecked(self.enable_sound_notifications)
            self.sound_notification_action.triggered.connect(self._toggle_sound_notifications)
            menu.addAction(self.sound_notification_action)
            
            menu.addSeparator()
            
            # 履歴表示
            history_action = QAction("通知履歴", self)
            history_action.triggered.connect(self._show_notification_history)
            menu.addAction(history_action)
            
            self.system_tray.setContextMenu(menu)
            self.system_tray.show()
            
        except Exception as e:
            print(f"システムトレイの設定に失敗: {e}")
    
    def _get_app_icon_path(self) -> Optional[str]:
        """アプリケーションアイコンのパスを取得"""
        # プロジェクトルートのアイコンファイルを探す
        possible_paths = [
            "icon.png",
            "icon.ico",
            "app_icon.png",
            "app_icon.ico",
            "assets/icon.png",
            "assets/icon.ico"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def _toggle_os_notifications(self, checked: bool):
        """OS通知の有効/無効を切り替え"""
        self.enable_os_notifications = checked
    
    def _toggle_sound_notifications(self, checked: bool):
        """音声通知の有効/無効を切り替え"""
        self.enable_sound_notifications = checked
    
    def _show_notification_history(self):
        """通知履歴を表示"""
        if not self.notification_history:
            self._show_simple_notification("通知履歴", "通知履歴はありません")
            return
        
        # 最新の5件を表示
        recent_notifications = self.notification_history[-5:]
        history_text = "\n".join([
            f"• {notif['title']} ({notif['timestamp']})"
            for notif in recent_notifications
        ])
        
        self._show_simple_notification("通知履歴", history_text)
    
    def notify_processing_completed(self, success: bool, message: str, details: str = ""):
        """
        処理完了通知を送信
        
        Args:
            success: 処理が成功したかどうか
            message: メッセージ
            details: 詳細情報
        """
        if success:
            title = "✅ 処理完了"
            notification_type = "success"
        else:
            title = "❌ 処理失敗"
            notification_type = "error"
        
        # 通知を送信
        self._send_notification(title, message, details, notification_type)
    
    def notify_processing_cancelled(self, message: str):
        """処理キャンセル通知を送信"""
        self._send_notification("⏹️ 処理キャンセル", message, "", "warning")
    
    def _send_notification(self, title: str, message: str, details: str = "", 
                          notification_type: str = "info"):
        """通知を送信"""
        import datetime
        
        # 通知履歴に追加
        notification = {
            'title': title,
            'message': message,
            'details': details,
            'type': notification_type,
            'timestamp': datetime.datetime.now().strftime("%H:%M:%S")
        }
        
        self.notification_history.append(notification)
        if len(self.notification_history) > self.max_history:
            self.notification_history.pop(0)
        
        # OS通知を送信
        if self.enable_os_notifications:
            self._send_os_notification(title, message, details, notification_type)
        
        # 音声通知を送信（OS通知を使用していない場合のみ）
        elif self.enable_sound_notifications:
            self._play_notification_sound(notification_type)
    
    def _send_os_notification(self, title: str, message: str, details: str, 
                             notification_type: str):
        """OS通知を送信"""
        try:
            if self.is_darwin:  # macOS
                self._send_macos_notification(title, message, details)
            elif self.is_windows:  # Windows
                self._send_windows_notification(title, message, details)
            elif self.is_linux:  # Linux
                self._send_linux_notification(title, message, details)
            else:
                # システムトレイ通知（フォールバック）
                self._send_system_tray_notification(title, message)
                
        except Exception as e:
            print(f"OS通知の送信に失敗: {e}")
            # フォールバック: システムトレイ通知
            self._send_system_tray_notification(title, message)
    
    def _send_macos_notification(self, title: str, message: str, details: str):
        """macOS通知を送信"""
        try:
            # osascriptを使用してmacOS通知を送信（標準通知音付き）
            script = f'''
            display notification "{message}" with title "{title}" sound name "Glass"
            '''
            
            subprocess.run(['osascript', '-e', script], 
                         capture_output=True, text=True, check=True)
            
        except subprocess.CalledProcessError as e:
            print(f"macOS通知の送信に失敗: {e}")
            # フォールバック: システムトレイ通知
            self._send_system_tray_notification(title, message)
    
    def _send_windows_notification(self, title: str, message: str, details: str):
        """Windows通知を送信"""
        try:
            # Windows 10/11のトースト通知
            from win10toast import ToastNotifier
            
            toaster = ToastNotifier()
            toaster.show_toast(
                title,
                message,
                duration=5,
                threaded=True
            )
            
        except ImportError:
            # win10toastが利用できない場合はシステムトレイ通知
            self._send_system_tray_notification(title, message)
        except Exception as e:
            print(f"Windows通知の送信に失敗: {e}")
            self._send_system_tray_notification(title, message)
    
    def _send_linux_notification(self, title: str, message: str, details: str):
        """Linux通知を送信"""
        try:
            # notify-sendコマンドを使用
            subprocess.run([
                'notify-send',
                title,
                message,
                '--urgency=normal',
                '--app-name=PDFTranslate2md'
            ], capture_output=True, check=True)
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            # notify-sendが利用できない場合はシステムトレイ通知
            self._send_system_tray_notification(title, message)
    
    def _send_system_tray_notification(self, title: str, message: str):
        """システムトレイ通知を送信"""
        if self.system_tray and self.system_tray.isSystemTrayAvailable():
            self.system_tray.showMessage(
                title,
                message,
                QSystemTrayIcon.Information,
                5000  # 5秒間表示
            )
    
    def _show_simple_notification(self, title: str, message: str):
        """シンプルな通知を表示"""
        if self.system_tray and self.system_tray.isSystemTrayAvailable():
            self.system_tray.showMessage(
                title,
                message,
                QSystemTrayIcon.Information,
                3000
            )
    
    def _play_notification_sound(self, notification_type: str):
        """通知音を再生"""
        try:
            if self.is_darwin:  # macOS
                self._play_macos_sound(notification_type)
            elif self.is_windows:  # Windows
                self._play_windows_sound(notification_type)
            elif self.is_linux:  # Linux
                self._play_linux_sound(notification_type)
                
        except Exception as e:
            print(f"通知音の再生に失敗: {e}")
    
    def _play_macos_sound(self, notification_type: str):
        """macOSで通知音を再生"""
        try:
            # macOSのシステムサウンドを使用
            sound_name = "Glass" if notification_type == "success" else "Basso"
            
            script = f'''
            set volume output volume 50
            play sound "{sound_name}"
            '''
            
            subprocess.run(['osascript', '-e', script], 
                         capture_output=True, text=True, check=True)
            
        except subprocess.CalledProcessError:
            # フォールバック: ビープ音
            print('\a')
    
    def _play_windows_sound(self, notification_type: str):
        """Windowsで通知音を再生"""
        try:
            import winsound
            
            # Windowsのシステムサウンドを使用
            if notification_type == "success":
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            elif notification_type == "error":
                winsound.MessageBeep(winsound.MB_ICONHAND)
            else:
                winsound.MessageBeep(winsound.MB_ICONINFORMATION)
                
        except ImportError:
            # winsoundが利用できない場合はビープ音
            print('\a')
    
    def _play_linux_sound(self, notification_type: str):
        """Linuxで通知音を再生"""
        try:
            # paplayコマンドを使用（PulseAudio）
            subprocess.run(['paplay', '/usr/share/sounds/freedesktop/stereo/complete.oga'], 
                         capture_output=True, check=True)
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                # aplayコマンドを使用（ALSA）
                subprocess.run(['aplay', '/usr/share/sounds/sound-icons/glass-water-1.wav'], 
                             capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                # フォールバック: ビープ音
                print('\a')
    
    def set_sound_file(self, file_path: str):
        """カスタム音声ファイルを設定"""
        if os.path.exists(file_path):
            self.sound_file_path = file_path
    
    def get_notification_settings(self) -> dict:
        """通知設定を取得"""
        return {
            'enable_os_notifications': self.enable_os_notifications,
            'enable_sound_notifications': self.enable_sound_notifications,
            'sound_file_path': self.sound_file_path
        }
    
    def set_notification_settings(self, settings: dict):
        """通知設定を設定"""
        self.enable_os_notifications = settings.get('enable_os_notifications', True)
        self.enable_sound_notifications = settings.get('enable_sound_notifications', False)
        self.sound_file_path = settings.get('sound_file_path')
        
        # UI更新
        if hasattr(self, 'os_notification_action'):
            self.os_notification_action.setChecked(self.enable_os_notifications)
        if hasattr(self, 'sound_notification_action'):
            self.sound_notification_action.setChecked(self.enable_sound_notifications)
    
    def cleanup(self):
        """リソースのクリーンアップ"""
        if self.system_tray:
            self.system_tray.hide()
            self.system_tray.deleteLater() 