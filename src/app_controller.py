"""
アプリケーション制御層
PDFTranslate2mdのビジネスロジックを統合管理する制御層

このモジュールは、CLI層とビジネスロジック層を分離し、以下の機能を提供する：
- PDF処理のオーケストレーション
- 翻訳サービスとの連携
- ファイル処理とディレクトリ管理
- 進捗管理と結果レポート
- エラーハンドリングの統一
"""

import os
import sys
import glob
import time
import logging
from typing import Optional, Dict, Any, Tuple, List
from tqdm import tqdm

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 既存モジュールのインポート
from src.pdf_extractor import extract_text, extract_images
from src.markdown_writer import write_markdown
from src.translator_service import TranslatorService
from src.unicode_handler import normalize_unicode_text, validate_text_for_api


class ProcessingResult:
    """処理結果を表すデータクラス"""
    
    def __init__(self, success: bool, output_path: str = None, error: str = None, 
                 skipped: bool = False, processing_time: float = 0.0):
        self.success = success
        self.output_path = output_path
        self.error = error
        self.skipped = skipped
        self.processing_time = processing_time
        self.pages_processed = 0
        self.images_extracted = 0
        self.file_size = 0


class AppController:
    """
    アプリケーション制御層のメインクラス
    
    PDF処理のオーケストレーション、翻訳サービスの管理、
    ファイル処理、進捗管理を統合的に提供する。
    """
    
    def __init__(self, provider_name: str, model_name: Optional[str] = None):
        """
        アプリケーション制御層の初期化
        
        Args:
            provider_name: 使用するLLMプロバイダー名
            model_name: 使用するモデル名（省略時はデフォルト）
            
        Raises:
            ValueError: プロバイダー名が無効な場合
            ValidationError: APIキーが設定されていない場合
        """
        self.provider_name = provider_name
        self.model_name = model_name
        
        # ログ設定
        self.logger = logging.getLogger(__name__)
        
        # 翻訳サービスの初期化
        try:
            self.translator_service = TranslatorService(
                provider_name=provider_name,
                model_name=model_name
            )
            self.logger.info(f"翻訳サービスを初期化しました: {provider_name} ({model_name})")
        except Exception as e:
            self.logger.error(f"翻訳サービスの初期化に失敗しました: {str(e)}")
            raise
        
        # 処理統計
        self.processing_stats = {
            'total_files': 0,
            'processed_files': 0,
            'skipped_files': 0,
            'failed_files': 0,
            'total_pages': 0,
            'total_images': 0,
            'total_processing_time': 0.0,
            'start_time': None,
            'end_time': None
        }
    
    def process_single_pdf(self, input_pdf: str, output_dir: str, image_dir: str, 
                          force_overwrite: bool = False) -> ProcessingResult:
        """
        単一のPDFファイルを処理する
        
        Args:
            input_pdf: 入力PDFファイルのパス
            output_dir: 出力ディレクトリのパス
            image_dir: 画像出力ディレクトリのパス
            force_overwrite: 既存ファイルの強制上書きフラグ
            
        Returns:
            ProcessingResult: 処理結果
        """
        start_time = time.time()
        result = ProcessingResult(success=False)
        
        try:
            # 入力ファイルの存在確認
            if not os.path.exists(input_pdf):
                error_msg = f"入力ファイルが見つかりません: {input_pdf}"
                self.logger.error(error_msg)
                result.error = error_msg
                return result
            
            # ファイルサイズを取得
            result.file_size = os.path.getsize(input_pdf)
            
            # 出力ファイル名を生成
            pdf_base = os.path.splitext(os.path.basename(input_pdf))[0]
            output_md = os.path.join(output_dir, f"{pdf_base}.md")
            result.output_path = output_md
            
            # 既存ファイルのチェック
            if os.path.exists(output_md) and not force_overwrite:
                self.logger.info(f"スキップ: 既存ファイルが存在します: {pdf_base}.md")
                result.skipped = True
                result.success = True
                return result
            
            # 出力ディレクトリの作成
            os.makedirs(output_dir, exist_ok=True)
            
            # 画像出力ディレクトリの設定と作成
            pdf_image_dir = os.path.join(image_dir, pdf_base)
            os.makedirs(pdf_image_dir, exist_ok=True)
            
            self.logger.info(f"PDFファイルの処理を開始: {input_pdf}")
            print(f"PDFファイル '{input_pdf}' の処理を開始します...")
            
            # PDFからテキストを抽出
            print(f"PDFファイル '{input_pdf}' からテキストを抽出中...")
            pages = extract_text(input_pdf)
            total_pages = len(pages)
            result.pages_processed = total_pages
            
            if total_pages == 0:
                error_msg = "PDFからテキストを抽出できませんでした"
                self.logger.warning(error_msg)
                result.error = error_msg
                return result
            
            print(f"合計 {total_pages} ページが抽出されました。")
            
            # PDFから画像を抽出
            print(f"PDFから画像を抽出しています... 保存先: {pdf_image_dir}")
            image_paths = extract_images(input_pdf, pdf_image_dir)
            result.images_extracted = len(image_paths)
            print(f"{len(image_paths)}枚の画像が保存されました: {pdf_image_dir}")
            
            # 翻訳処理
            print("翻訳を開始します...")
            translated_pages = []
            all_headers = []
            
            # プログレスバーを使用して翻訳を実行
            for i, page in enumerate(tqdm(pages, desc="翻訳処理中", unit="ページ")):
                page_info = {'current': i+1, 'total': total_pages}
                
                try:
                    # 翻訳サービスを使用して翻訳
                    translated_text, headers = self.translator_service.translate_page(
                        text=page,
                        page_info=page_info,
                        previous_headers=all_headers
                    )
                    translated_pages.append(translated_text)
                    all_headers.extend(headers)
                    
                except Exception as e:
                    error_msg = f"ページ {page_info['current']}/{page_info['total']} の翻訳に失敗しました: {str(e)}"
                    self.logger.error(error_msg)
                    tqdm.write(f"\n❌ {error_msg}")
                    # エラーメッセージを翻訳結果として追加
                    translated_pages.append(f"## 翻訳エラー\n\n{error_msg}\n\n---\n\n**原文:**\n\n{page}")
                    continue
            
            # Markdownファイルの書き出し
            print("\n翻訳完了。Markdownファイルに書き出しています...")
            write_markdown(output_md, translated_pages, image_paths)
            
            # 処理時間の計算
            result.processing_time = time.time() - start_time
            
            # 成功の記録
            result.success = True
            self.logger.info(f"処理完了: {output_md} (処理時間: {result.processing_time:.1f}秒)")
            print(f"処理完了: Markdownファイルが作成されました: {output_md}")
            
            return result
            
        except Exception as e:
            result.processing_time = time.time() - start_time
            error_msg = f"PDFファイル処理中にエラーが発生しました: {str(e)}"
            result.error = error_msg
            self.logger.error(error_msg)
            print(f"❌ {error_msg}")
            return result
    
    def process_pdf_directory(self, input_dir: str, output_dir: str, image_dir: str, 
                             force_overwrite: bool = False) -> Tuple[List[str], List[str], List[str]]:
        """
        ディレクトリ内のすべてのPDFファイルを処理する
        
        Args:
            input_dir: 入力ディレクトリのパス
            output_dir: 出力ディレクトリのパス
            image_dir: 画像出力ディレクトリのパス
            force_overwrite: 既存ファイルの強制上書きフラグ
            
        Returns:
            tuple: (処理されたファイルのリスト, スキップされたファイルのリスト, 失敗したファイルのリスト)
        """
        self.processing_stats['start_time'] = time.time()
        
        # PDFファイルを検索
        pdf_files = glob.glob(os.path.join(input_dir, "*.pdf"))
        if not pdf_files:
            error_msg = f"ディレクトリ '{input_dir}' にPDFファイルが見つかりませんでした。"
            self.logger.error(error_msg)
            print(f"エラー: {error_msg}")
            return [], [], []
        
        self.processing_stats['total_files'] = len(pdf_files)
        print(f"ディレクトリ '{input_dir}' 内の {len(pdf_files)} 個のPDFファイルを処理します...")
        
        processed_files = []
        skipped_files = []
        failed_files = []
        
        # 各PDFファイルを処理
        for pdf_file in pdf_files:
            result = self.process_single_pdf(pdf_file, output_dir, image_dir, force_overwrite)
            
            # 統計の更新
            self.processing_stats['total_pages'] += result.pages_processed
            self.processing_stats['total_images'] += result.images_extracted
            self.processing_stats['total_processing_time'] += result.processing_time
            
            if result.success:
                if result.skipped:
                    skipped_files.append(result.output_path)
                    self.processing_stats['skipped_files'] += 1
                else:
                    processed_files.append(result.output_path)
                    self.processing_stats['processed_files'] += 1
            else:
                failed_files.append(pdf_file)
                self.processing_stats['failed_files'] += 1
        
        self.processing_stats['end_time'] = time.time()
        
        # 結果の表示
        self._display_batch_results(processed_files, skipped_files, failed_files)
        
        return processed_files, skipped_files, failed_files
    
    def _display_batch_results(self, processed_files: List[str], skipped_files: List[str], 
                              failed_files: List[str]) -> None:
        """
        バッチ処理の結果を表示する
        
        Args:
            processed_files: 処理されたファイルのリスト
            skipped_files: スキップされたファイルのリスト
            failed_files: 失敗したファイルのリスト
        """
        print("\n" + "="*50)
        print("処理結果サマリー")
        print("="*50)
        
        if processed_files:
            print(f"\n✅ 処理完了: {len(processed_files)}個のファイル")
            for file in processed_files:
                print(f"  - {file}")
        
        if skipped_files:
            print(f"\n⏭️  スキップ: {len(skipped_files)}個のファイル")
            for file in skipped_files:
                print(f"  - {file}")
            print("  💡 スキップされたファイルを処理するには --force オプションを使用してください。")
        
        if failed_files:
            print(f"\n❌ 失敗: {len(failed_files)}個のファイル")
            for file in failed_files:
                print(f"  - {file}")
        
        # 統計情報の表示
        stats = self.processing_stats
        total_time = stats['end_time'] - stats['start_time'] if stats['end_time'] else 0
        
        print(f"\n📊 処理統計:")
        print(f"  - 合計ファイル数: {stats['total_files']}")
        print(f"  - 処理済み: {stats['processed_files']}")
        print(f"  - スキップ: {stats['skipped_files']}")
        print(f"  - 失敗: {stats['failed_files']}")
        print(f"  - 合計ページ数: {stats['total_pages']}")
        print(f"  - 合計画像数: {stats['total_images']}")
        print(f"  - 合計処理時間: {total_time:.1f}秒")
        if stats['processed_files'] > 0:
            avg_time = stats['total_processing_time'] / stats['processed_files']
            print(f"  - 平均処理時間: {avg_time:.1f}秒/ファイル")
    
    def get_processing_status(self) -> Dict[str, Any]:
        """
        現在の処理状況を取得する
        
        Returns:
            処理状況の辞書
        """
        return {
            'provider_info': self.translator_service.get_provider_info(),
            'processing_stats': self.processing_stats.copy(),
            'configuration_valid': self.translator_service.validate_configuration()
        }
    
    def validate_configuration(self) -> Tuple[bool, List[str]]:
        """
        設定の妥当性を検証する
        
        Returns:
            tuple: (設定が有効かどうか, エラーメッセージのリスト)
        """
        errors = []
        
        try:
            # 翻訳サービスの設定検証
            if not self.translator_service.validate_configuration():
                errors.append("翻訳サービスの設定が無効です")
            
            # プロバイダー情報の取得
            provider_info = self.translator_service.get_provider_info()
            if not provider_info.get('api_key_configured', False):
                errors.append(f"{provider_info.get('display_name', 'プロバイダー')}のAPIキーが設定されていません")
            
        except Exception as e:
            errors.append(f"設定検証中にエラーが発生しました: {str(e)}")
        
        return len(errors) == 0, errors
    
    def setup_directories(self, output_dir: str, image_dir: str) -> Tuple[str, str]:
        """
        出力ディレクトリを設定・作成する
        
        Args:
            output_dir: 出力ディレクトリのパス（Noneの場合は現在のディレクトリを使用）
            image_dir: 画像出力ディレクトリのパス（Noneの場合は自動設定）
            
        Returns:
            tuple: (作成された出力ディレクトリのパス, 作成された画像ディレクトリのパス)
        """
        # 出力ディレクトリの設定
        if not output_dir:
            output_dir = os.getcwd()
        os.makedirs(output_dir, exist_ok=True)
        
        # 画像ディレクトリの設定
        if not image_dir:
            image_dir = os.path.join(output_dir, "images")
        os.makedirs(image_dir, exist_ok=True)
        
        return output_dir, image_dir
    
    def process_input_path(self, input_path: str, output_dir: str, image_dir: str, 
                          force_overwrite: bool = False) -> bool:
        """
        入力パス（ファイルまたはディレクトリ）を処理する
        
        Args:
            input_path: 入力パス
            output_dir: 出力ディレクトリ
            image_dir: 画像出力ディレクトリ
            force_overwrite: 強制上書きフラグ
            
        Returns:
            処理が成功した場合True、失敗した場合False
        """
        try:
            if os.path.isdir(input_path):
                # ディレクトリの場合
                processed, skipped, failed = self.process_pdf_directory(
                    input_path, output_dir, image_dir, force_overwrite
                )
                return len(failed) == 0
            
            elif os.path.isfile(input_path):
                # ファイルの場合
                if not input_path.lower().endswith('.pdf'):
                    print(f"エラー: 入力ファイル '{input_path}' はPDFファイルではありません。")
                    return False
                
                result = self.process_single_pdf(input_path, output_dir, image_dir, force_overwrite)
                
                if result.skipped:
                    print(f"スキップ: 出力先に既に '{os.path.basename(result.output_path)}' が存在します。上書きするには --force オプションを使用してください。")
                    return True
                
                return result.success
            
            else:
                print(f"エラー: 入力パス '{input_path}' が見つかりません。")
                return False
                
        except Exception as e:
            error_msg = f"入力パスの処理中にエラーが発生しました: {str(e)}"
            self.logger.error(error_msg)
            print(f"❌ {error_msg}")
            return False
    
    def get_summary_info(self, output_dir: str, image_dir: str) -> Dict[str, str]:
        """
        処理完了後のサマリー情報を取得する
        
        Args:
            output_dir: 出力ディレクトリ
            image_dir: 画像ディレクトリ
            
        Returns:
            サマリー情報の辞書
        """
        return {
            'output_dir': output_dir,
            'image_dir': image_dir,
            'provider': self.translator_service.get_provider_info()['display_name'],
            'model': self.model_name or "デフォルト"
        }
    
    def __str__(self) -> str:
        """文字列表現"""
        return f"AppController({self.provider_name}, {self.model_name})"
    
    def __repr__(self) -> str:
        """デバッグ用文字列表現"""
        return f"AppController(provider_name='{self.provider_name}', model_name='{self.model_name}')"


# ユーティリティ関数
def validate_input_path(input_path: str) -> Tuple[bool, str]:
    """
    入力パスの妥当性を検証する
    
    Args:
        input_path: 検証する入力パス
        
    Returns:
        tuple: (有効かどうか, エラーメッセージ)
    """
    if not input_path:
        return False, "入力パスが指定されていません"
    
    if not os.path.exists(input_path):
        return False, f"入力パス '{input_path}' が見つかりません"
    
    if os.path.isfile(input_path) and not input_path.lower().endswith('.pdf'):
        return False, f"入力ファイル '{input_path}' はPDFファイルではありません"
    
    return True, ""


def validate_provider_settings(provider_name: str, model_name: Optional[str] = None) -> Tuple[bool, List[str]]:
    """
    プロバイダー設定の妥当性を検証する
    
    Args:
        provider_name: プロバイダー名
        model_name: モデル名
        
    Returns:
        tuple: (設定が有効かどうか, エラーメッセージのリスト)
    """
    errors = []
    
    try:
        # TranslatorServiceを一時的に作成して検証
        temp_service = TranslatorService(provider_name=provider_name, model_name=model_name)
        if not temp_service.validate_configuration():
            errors.append("プロバイダー設定が無効です")
    except Exception as e:
        errors.append(f"プロバイダー設定の検証中にエラーが発生しました: {str(e)}")
    
    return len(errors) == 0, errors