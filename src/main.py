"""
PDFTranslate2md - CLI エントリーポイント

PDFファイルを翻訳してMarkdownファイルに変換するCLIツール。
Phase 3リファクタリング後のCLI層は、コマンドライン引数の解析と
AppControllerへの処理委譲のみを担当する。
"""

import sys
import os
import argparse
import logging
from .app_controller import AppController, validate_input_path, validate_provider_settings


def setup_logging(unicode_debug: bool = False) -> None:
    """
    ログ設定を初期化する
    
    Args:
        unicode_debug: Unicode処理の詳細ログを有効にするかどうか
    """
    # 基本ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('pdftranslate2md.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Unicode処理のデバッグ設定
    if unicode_debug:
        unicode_logger = logging.getLogger('unicode_handler')
        unicode_logger.setLevel(logging.DEBUG)
        logging.getLogger('pdf_extractor').setLevel(logging.DEBUG)
        logging.getLogger('translator').setLevel(logging.DEBUG)
        logging.getLogger('markdown_writer').setLevel(logging.DEBUG)
        print("Unicode処理の詳細ログを有効にしました")


def parse_arguments() -> argparse.Namespace:
    """
    コマンドライン引数を解析する
    
    Returns:
        解析されたコマンドライン引数
    """
    parser = argparse.ArgumentParser(
        description='PDFから翻訳されたMarkdownファイルを生成するツール',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  %(prog)s document.pdf                    # 単一PDFを処理
  %(prog)s documents/ -o output/           # ディレクトリ内のすべてのPDFを処理
  %(prog)s document.pdf -p openai -m gpt-4 # OpenAI GPT-4を使用
  %(prog)s documents/ -f                   # 既存ファイルを強制上書き

サポートされているプロバイダー:
  gemini, openai, claude, anthropic
        """
    )
    
    # 必須引数
    parser.add_argument(
        'input',
        help='入力PDFファイルまたはPDFファイルを含むディレクトリのパス'
    )
    
    # オプション引数
    parser.add_argument(
        '-o', '--output-dir',
        help='出力ディレクトリのパス（指定しない場合、現在のディレクトリが使用されます）'
    )
    parser.add_argument(
        '-i', '--image-dir',
        help='画像出力ディレクトリ（指定しない場合、出力ディレクトリ内の"images"フォルダが使用されます）'
    )
    parser.add_argument(
        '-p', '--provider',
        help='使用するLLMプロバイダー（gemini, openai, claude, anthropic）',
        default='gemini',
        choices=['gemini', 'openai', 'claude', 'anthropic']
    )
    parser.add_argument(
        '-m', '--model-name',
        help='LLMモデル名（指定しない場合はプロバイダーのデフォルト）'
    )
    parser.add_argument(
        '-f', '--force',
        help='既存のMarkdownファイルが存在する場合も強制的に上書きする',
        action='store_true'
    )
    parser.add_argument(
        '--unicode-debug',
        help='Unicode処理の詳細ログを出力する',
        action='store_true'
    )
    
    return parser.parse_args()


def display_startup_info(args: argparse.Namespace) -> None:
    """
    起動時の情報を表示する
    
    Args:
        args: コマンドライン引数
    """
    print("PDFTranslate2md を起動中...")
    print(f"使用するAIプロバイダー: {args.provider}")
    
    if args.model_name:
        print(f"モデル: {args.model_name}")
    
    # 入力パスの情報
    if os.path.isdir(args.input):
        print(f"入力ディレクトリ: {args.input}")
    else:
        print(f"入力ファイル: {args.input}")


def main() -> int:
    """
    メイン関数
    
    Returns:
        終了コード（0: 成功, 1: エラー）
    """
    try:
        # コマンドライン引数の解析
        args = parse_arguments()
        
        # ログ設定
        setup_logging(args.unicode_debug)
        
        # 起動情報の表示
        display_startup_info(args)
        
        # 入力パスの事前検証
        is_valid, error_msg = validate_input_path(args.input)
        if not is_valid:
            print(f"エラー: {error_msg}")
            return 1
        
        # プロバイダー設定の事前検証
        config_valid, config_errors = validate_provider_settings(args.provider, args.model_name)
        if not config_valid:
            print("エラー: プロバイダー設定に問題があります:")
            for error in config_errors:
                print(f"  - {error}")
            return 1
        
        # アプリケーション制御層の初期化
        try:
            app_controller = AppController(
                provider_name=args.provider,
                model_name=args.model_name
            )
        except Exception as e:
            print(f"エラー: アプリケーションの初期化に失敗しました: {str(e)}")
            return 1
        
        # 出力ディレクトリの設定
        output_dir, image_dir = app_controller.setup_directories(
            args.output_dir, args.image_dir
        )
        
        # 設定の最終検証
        config_valid, validation_errors = app_controller.validate_configuration()
        if not config_valid:
            print("エラー: 設定の検証に失敗しました:")
            for error in validation_errors:
                print(f"  - {error}")
            return 1
        
        # メイン処理の実行
        success = app_controller.process_input_path(
            input_path=args.input,
            output_dir=output_dir,
            image_dir=image_dir,
            force_overwrite=args.force
        )
        
        if not success:
            print("\n処理中にエラーが発生しました。詳細はログファイルを確認してください。")
            return 1
        
        # サマリー情報の表示
        summary = app_controller.get_summary_info(output_dir, image_dir)
        print(f"\n出力ディレクトリ: {summary['output_dir']}")
        print(f"画像ディレクトリ: {summary['image_dir']}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n処理が中断されました。")
        return 1
    except Exception as e:
        print(f"\n予期しないエラーが発生しました: {str(e)}")
        logging.exception("予期しないエラー")
        return 1


if __name__ == "__main__":
    sys.exit(main())