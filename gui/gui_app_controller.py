"""
GUI用のアプリケーション制御層
既存のAppControllerを拡張してGUIに適した機能を提供する
"""

import sys
import os
import logging
from typing import Optional, Dict, Any, Callable, List, Tuple
from PyQt5.QtCore import QThread, pyqtSignal, QObject
import time

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app_controller import AppController, ProcessingResult


class ProcessingSignals(QObject):
    """処理進捗用のシグナル"""
    progress_updated = pyqtSignal(int, str)  # 進捗率, メッセージ
    file_started = pyqtSignal(str)  # ファイル名
    file_completed = pyqtSignal(str, bool)  # ファイル名, 成功フラグ
    page_progress = pyqtSignal(int, int, str)  # 現在ページ, 総ページ数, ファイル名
    error_occurred = pyqtSignal(str)  # エラーメッセージ
    processing_finished = pyqtSignal(bool, str)  # 成功フラグ, 結果メッセージ
    log_message = pyqtSignal(str, str)  # ログレベル, メッセージ


class ProcessingThread(QThread):
    """バックグラウンドでPDF処理を行うスレッド"""
    
    def __init__(self, controller: 'GuiAppController', input_path: str, 
                 output_dir: str, image_dir: str, force_overwrite: bool = False):
        super().__init__()
        self.controller = controller
        self.input_path = input_path
        self.output_dir = output_dir
        self.image_dir = image_dir
        self.force_overwrite = force_overwrite
        self.signals = ProcessingSignals()
        self._is_cancelled = False
    
    def run(self):
        """処理の実行"""
        try:
            success = self.controller.process_input_path_with_signals(
                self.input_path, 
                self.output_dir, 
                self.image_dir, 
                self.force_overwrite,
                self.signals
            )
            
            if not self._is_cancelled:
                message = "処理が正常に完了しました。" if success else "処理中にエラーが発生しました。"
                self.signals.processing_finished.emit(success, message)
                
        except Exception as e:
            if not self._is_cancelled:
                error_msg = f"処理中に予期しないエラーが発生しました: {str(e)}"
                self.signals.error_occurred.emit(error_msg)
                self.signals.processing_finished.emit(False, error_msg)
    
    def cancel(self):
        """処理のキャンセル"""
        self._is_cancelled = True
        self.terminate()
        self.wait()


class GuiAppController(AppController):
    """
    GUI用のアプリケーション制御層
    
    既存のAppControllerを拡張し、GUI向けの機能を追加する：
    - 非同期処理のサポート
    - 進捗報告
    - キャンセル機能
    - リアルタイムログ表示
    """
    
    def __init__(self, provider_name: str, model_name: Optional[str] = None):
        """
        GUI用アプリケーション制御層の初期化
        
        Args:
            provider_name: 使用するLLMプロバイダー名
            model_name: 使用するモデル名（省略時はデフォルト）
        """
        super().__init__(provider_name, model_name)
        
        # GUI用のログハンドラー設定
        self._setup_gui_logging()
        
        # 現在の処理スレッド
        self.current_thread: Optional[ProcessingThread] = None
        
        # 処理状態
        self.is_processing = False
    
    def _setup_gui_logging(self):
        """GUI用のログ設定"""
        # ログフォーマッターの設定
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # 既存のハンドラーを削除
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # ファイルハンドラーのみ追加（GUIでは画面にログを表示するため）
        file_handler = logging.FileHandler('gui_pdftranslate2md.log', encoding='utf-8')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        self.logger.setLevel(logging.INFO)
    
    def start_processing_async(self, input_path: str, output_dir: str, image_dir: str, 
                             force_overwrite: bool = False) -> ProcessingSignals:
        """
        非同期でPDF処理を開始する
        
        Args:
            input_path: 入力パス
            output_dir: 出力ディレクトリ
            image_dir: 画像出力ディレクトリ
            force_overwrite: 強制上書きフラグ
            
        Returns:
            処理進捗用のシグナルオブジェクト
        """
        if self.is_processing:
            raise RuntimeError("処理が既に実行中です")
        
        self.is_processing = True
        
        # 処理スレッドを作成
        self.current_thread = ProcessingThread(
            self, input_path, output_dir, image_dir, force_overwrite
        )
        
        # 処理完了時のコールバック
        self.current_thread.signals.processing_finished.connect(self._on_processing_finished)
        
        # スレッド開始
        self.current_thread.start()
        
        return self.current_thread.signals
    
    def cancel_processing(self) -> bool:
        """
        現在の処理をキャンセルする
        
        Returns:
            キャンセルが成功したかどうか
        """
        if self.current_thread and self.is_processing:
            self.current_thread.cancel()
            self.is_processing = False
            return True
        return False
    
    def _on_processing_finished(self, success: bool, message: str):
        """処理完了時のコールバック"""
        self.is_processing = False
        self.current_thread = None
    
    def process_input_path_with_signals(self, input_path: str, output_dir: str, 
                                      image_dir: str, force_overwrite: bool,
                                      signals: ProcessingSignals) -> bool:
        """
        シグナル通知付きでPDF処理を実行する
        
        Args:
            input_path: 入力パス
            output_dir: 出力ディレクトリ
            image_dir: 画像ディレクトリ
            force_overwrite: 強制上書きフラグ
            signals: 進捗通知用シグナル
            
        Returns:
            処理が成功したかどうか
        """
        try:
            signals.log_message.emit("INFO", f"処理を開始します: {input_path}")
            signals.progress_updated.emit(0, "処理を開始しています...")
            
            if os.path.isdir(input_path):
                return self._process_directory_with_signals(
                    input_path, output_dir, image_dir, force_overwrite, signals
                )
            elif os.path.isfile(input_path):
                return self._process_file_with_signals(
                    input_path, output_dir, image_dir, force_overwrite, signals
                )
            else:
                error_msg = f"入力パス '{input_path}' が見つかりません。"
                signals.error_occurred.emit(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"処理中にエラーが発生しました: {str(e)}"
            signals.error_occurred.emit(error_msg)
            signals.log_message.emit("ERROR", error_msg)
            return False
    
    def _process_directory_with_signals(self, input_dir: str, output_dir: str, 
                                      image_dir: str, force_overwrite: bool,
                                      signals: ProcessingSignals) -> bool:
        """ディレクトリ処理（シグナル通知付き）"""
        import glob
        
        # PDFファイルを検索
        pdf_files = glob.glob(os.path.join(input_dir, "*.pdf"))
        if not pdf_files:
            error_msg = f"ディレクトリ '{input_dir}' にPDFファイルが見つかりませんでした。"
            signals.error_occurred.emit(error_msg)
            return False
        
        total_files = len(pdf_files)
        processed_count = 0
        failed_count = 0
        
        signals.log_message.emit("INFO", f"{total_files}個のPDFファイルを処理します")
        
        for i, pdf_file in enumerate(pdf_files):
            if self.current_thread and self.current_thread._is_cancelled:
                signals.log_message.emit("INFO", "処理がキャンセルされました")
                return False
            
            # ファイル処理開始
            filename = os.path.basename(pdf_file)
            signals.file_started.emit(filename)
            signals.progress_updated.emit(
                int((i / total_files) * 100), 
                f"処理中: {filename} ({i+1}/{total_files})"
            )
            
            # 単一ファイル処理
            result = self._process_single_pdf_with_signals(
                pdf_file, output_dir, image_dir, force_overwrite, signals
            )
            
            # 結果記録
            if result.success:
                processed_count += 1
                signals.file_completed.emit(filename, True)
                if not result.skipped:
                    signals.log_message.emit("INFO", f"完了: {filename}")
                else:
                    signals.log_message.emit("INFO", f"スキップ: {filename}")
            else:
                failed_count += 1
                signals.file_completed.emit(filename, False)
                signals.log_message.emit("ERROR", f"失敗: {filename} - {result.error}")
        
        # 最終進捗更新
        signals.progress_updated.emit(100, "処理完了")
        
        # 結果サマリー
        success_rate = (processed_count / total_files) * 100
        summary = f"処理完了: 成功 {processed_count}/{total_files} ({success_rate:.1f}%)"
        signals.log_message.emit("INFO", summary)
        
        return failed_count == 0
    
    def _process_file_with_signals(self, input_file: str, output_dir: str, 
                                 image_dir: str, force_overwrite: bool,
                                 signals: ProcessingSignals) -> bool:
        """単一ファイル処理（シグナル通知付き）"""
        if not input_file.lower().endswith('.pdf'):
            error_msg = f"入力ファイル '{input_file}' はPDFファイルではありません。"
            signals.error_occurred.emit(error_msg)
            return False
        
        filename = os.path.basename(input_file)
        signals.file_started.emit(filename)
        signals.progress_updated.emit(0, f"処理中: {filename}")
        
        result = self._process_single_pdf_with_signals(
            input_file, output_dir, image_dir, force_overwrite, signals
        )
        
        signals.progress_updated.emit(100, "処理完了")
        signals.file_completed.emit(filename, result.success)
        
        if result.success:
            if result.skipped:
                signals.log_message.emit("INFO", f"スキップ: 既存ファイルが存在します")
            else:
                signals.log_message.emit("INFO", f"処理完了: {result.output_path}")
        else:
            signals.log_message.emit("ERROR", f"処理失敗: {result.error}")
        
        return result.success
    
    def _process_single_pdf_with_signals(self, input_pdf: str, output_dir: str, 
                                       image_dir: str, force_overwrite: bool,
                                       signals: ProcessingSignals) -> ProcessingResult:
        """単一PDF処理（シグナル通知付き）"""
        start_time = time.time()
        result = ProcessingResult(success=False)
        
        try:
            # 基本的な検証
            if not os.path.exists(input_pdf):
                result.error = f"入力ファイルが見つかりません: {input_pdf}"
                return result
            
            result.file_size = os.path.getsize(input_pdf)
            
            # 出力パス設定
            pdf_base = os.path.splitext(os.path.basename(input_pdf))[0]
            output_md = os.path.join(output_dir, f"{pdf_base}.md")
            result.output_path = output_md
            
            # 既存ファイルチェック
            if os.path.exists(output_md) and not force_overwrite:
                result.skipped = True
                result.success = True
                return result
            
            # ディレクトリ作成
            os.makedirs(output_dir, exist_ok=True)
            pdf_image_dir = os.path.join(image_dir, pdf_base)
            os.makedirs(pdf_image_dir, exist_ok=True)
            
            # PDF処理開始
            signals.log_message.emit("INFO", f"PDFからテキストを抽出中...")
            
            # テキスト抽出
            from src.pdf_extractor import extract_text, extract_images
            pages = extract_text(input_pdf)
            total_pages = len(pages)
            result.pages_processed = total_pages
            
            if total_pages == 0:
                result.error = "PDFからテキストを抽出できませんでした"
                return result
            
            signals.log_message.emit("INFO", f"{total_pages}ページを抽出しました")
            
            # 画像抽出
            signals.log_message.emit("INFO", "画像を抽出中...")
            image_paths = extract_images(input_pdf, pdf_image_dir)
            result.images_extracted = len(image_paths)
            signals.log_message.emit("INFO", f"{len(image_paths)}枚の画像を抽出しました")
            
            # 翻訳処理
            signals.log_message.emit("INFO", "翻訳を開始します...")
            translated_pages = []
            all_headers = []
            
            for i, page in enumerate(pages):
                if self.current_thread and self.current_thread._is_cancelled:
                    result.error = "処理がキャンセルされました"
                    return result
                
                page_info = {'current': i+1, 'total': total_pages}
                
                # ページ進捗通知
                signals.page_progress.emit(i+1, total_pages, pdf_base)
                progress = int(((i+1) / total_pages) * 80)  # 翻訳は全体の80%
                signals.progress_updated.emit(progress, f"翻訳中: ページ {i+1}/{total_pages}")
                
                # UIイベントループを維持してブロッキングを防ぐ
                from PyQt5.QtCore import QCoreApplication
                signals.log_message.emit("DEBUG", f"[GUI-DEBUG] ページ{i+1}処理前 - UIイベント処理実行 - {time.strftime('%H:%M:%S')}")
                QCoreApplication.processEvents()
                
                # 翻訳処理を確実に実行し、エラー時も次のページに進む
                try:
                    signals.log_message.emit("DEBUG", f"[GUI-DEBUG] ページ{i+1} - translate_page呼び出し開始 - {time.strftime('%H:%M:%S')}")
                    translate_start = time.time()
                    
                    # 翻訳処理を実行（途中で定期的にUIイベント処理）
                    translated_text, headers = self._translate_page_with_ui_updates(
                        page, page_info, all_headers, signals
                    )
                    
                    translate_duration = time.time() - translate_start
                    signals.log_message.emit("DEBUG", f"[GUI-DEBUG] ページ{i+1} - translate_page完了 - {time.strftime('%H:%M:%S')} (所要時間: {translate_duration:.2f}秒)")
                    translated_pages.append(translated_text)
                    all_headers.extend(headers)
                    signals.log_message.emit("INFO", f"ページ {i+1}/{total_pages} の翻訳が完了しました")
                    
                    # 翻訳完了後もUIイベントループを維持
                    signals.log_message.emit("DEBUG", f"[GUI-DEBUG] ページ{i+1}翻訳完了後 - UIイベント処理実行 - {time.strftime('%H:%M:%S')}")
                    QCoreApplication.processEvents()
                    
                except Exception as e:
                    error_msg = f"ページ {i+1} の翻訳に失敗しました: {str(e)}"
                    signals.log_message.emit("WARNING", error_msg)
                    signals.log_message.emit("DEBUG", f"[GUI-DEBUG] ページ{i+1}エラー処理 - {time.strftime('%H:%M:%S')}")
                    # エラー時もページを追加して、確実に次のページに進む
                    translated_pages.append(f"## 翻訳エラー\n\n{error_msg}\n\n---\n\n**原文:**\n\n{page}")
                    
                    # エラー処理後もUIイベントループを維持
                    signals.log_message.emit("DEBUG", f"[GUI-DEBUG] ページ{i+1}エラー後 - UIイベント処理実行 - {time.strftime('%H:%M:%S')}")
                    QCoreApplication.processEvents()
                    # エラー後も処理を継続
                    continue
                finally:
                    # 各ページ処理後の確実な状態更新
                    signals.log_message.emit("DEBUG", f"ページ {i+1}/{total_pages} の処理を完了し、次のページに進みます")
                    # 最終的にUIイベントループを維持
                    QCoreApplication.processEvents()
            
            # Markdown書き出し
            signals.progress_updated.emit(90, "Markdownファイルを作成中...")
            signals.log_message.emit("INFO", "Markdownファイルを作成中...")
            
            from src.markdown_writer import write_markdown
            write_markdown(output_md, translated_pages, image_paths)
            
            # 完了
            result.processing_time = time.time() - start_time
            result.success = True
            
            return result
            
        except Exception as e:
            result.processing_time = time.time() - start_time
            result.error = f"PDF処理中にエラーが発生しました: {str(e)}"
            return result
    
    def _translate_page_with_ui_updates(self, page: str, page_info: Dict[str, int],
                                      all_headers: List[str], signals: ProcessingSignals) -> Tuple[str, List[str]]:
        """
        UIイベント処理を組み込んだページ翻訳
        
        Args:
            page: 翻訳するページテキスト
            page_info: ページ情報
            all_headers: これまでのヘッダー一覧
            signals: シグナルオブジェクト
            
        Returns:
            翻訳結果とヘッダーのタプル
        """
        import threading
        import queue
        from PyQt5.QtCore import QCoreApplication
        
        # 結果を格納するキュー
        result_queue = queue.Queue()
        exception_queue = queue.Queue()
        
        def translation_worker():
            """翻訳処理を実行するワーカー関数"""
            try:
                translated_text, headers = self.translator_service.translate_page(
                    text=page,
                    page_info=page_info,
                    previous_headers=all_headers
                )
                result_queue.put((translated_text, headers))
            except Exception as e:
                exception_queue.put(e)
        
        # ワーカースレッドで翻訳処理を実行
        worker_thread = threading.Thread(target=translation_worker, daemon=True)
        worker_thread.start()
        
        # UI更新タイマー
        ui_update_interval = 0.5  # 0.5秒ごとにUI更新
        last_ui_update = time.time()
        elapsed_log_interval = 5  # 5秒ごとにログ出力
        last_log_time = time.time()
        
        # 翻訳処理の完了を待機（定期的にUIイベントを処理）
        while worker_thread.is_alive():
            current_time = time.time()
            
            # UI更新
            if current_time - last_ui_update >= ui_update_interval:
                QCoreApplication.processEvents()
                last_ui_update = current_time
            
            # 進捗ログ出力
            if current_time - last_log_time >= elapsed_log_interval:
                signals.log_message.emit("DEBUG", f"[GUI-DEBUG] 翻訳処理継続中... - {time.strftime('%H:%M:%S')}")
                last_log_time = current_time
            
            # 短時間待機
            worker_thread.join(timeout=0.1)
        
        # 例外が発生した場合
        if not exception_queue.empty():
            raise exception_queue.get()
        
        # 結果を取得
        if not result_queue.empty():
            return result_queue.get()
        else:
            raise Exception("翻訳処理が予期せず終了しました")
    
    def get_available_providers(self) -> List[Dict[str, str]]:
        """利用可能なプロバイダー一覧を取得"""
        return [
            {'id': 'gemini', 'name': 'Google Gemini'},
            {'id': 'openai', 'name': 'OpenAI GPT'},
            {'id': 'anthropic', 'name': 'Anthropic Claude'}
        ]
    
    def get_available_models(self, provider: str) -> List[str]:
        """指定プロバイダーで利用可能なモデル一覧を取得"""
        models = {
            'gemini': ['gemini-2.5-flash-preview-04-17'],
            'openai': ['gpt-4.1', 'gpt-4.1-mini'],
            'anthropic': ['claude-3-7-sonnet']
        }
        return models.get(provider, [])
    
    def test_provider_connection(self, provider: str, model: str = None) -> tuple[bool, str]:
        """
        プロバイダー接続をテストする
        
        Returns:
            tuple: (成功フラグ, メッセージ)
        """
        try:
            # 一時的にTranslatorServiceを作成してテスト
            from src.translator_service import TranslatorService
            test_service = TranslatorService(provider_name=provider, model_name=model)
            
            if test_service.validate_configuration():
                return True, f"{provider} プロバイダーへの接続が確認できました"
            else:
                return False, f"{provider} プロバイダーの設定に問題があります"
                
        except Exception as e:
            return False, f"{provider} プロバイダーのテストに失敗しました: {str(e)}"