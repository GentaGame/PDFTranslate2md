"""
PDFTranslate2md GUI パッケージ
PyQt5ベースのデスクトップGUIアプリケーション
"""

from .main_gui import MainWindow, main
from .gui_app_controller import GuiAppController, ProcessingSignals
from .history_manager import HistoryManager, ProcessingHistory

__version__ = "1.0.0"
__all__ = [
    'MainWindow',
    'main',
    'GuiAppController',
    'ProcessingSignals',
    'HistoryManager',
    'ProcessingHistory'
]