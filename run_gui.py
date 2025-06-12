#!/usr/bin/env python3
"""
PDFTranslate2md GUI起動スクリプト

環境チェック機能を組み込み、問題がある場合は適切なエラーメッセージと
解決策を表示する。
"""

import sys
import os
import argparse
import subprocess
import platform
from pathlib import Path


def setup_qt_environment():
    """Qt環境の自動設定（macOS対応）"""
    if platform.system() == "Darwin":  # macOS
        try:
            import PyQt5
            # PyQt5のプラグインパスを自動設定
            qt_plugin_path = os.path.join(PyQt5.__path__[0], 'Qt5', 'plugins')
            if os.path.exists(qt_plugin_path):
                os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = qt_plugin_path
                print(f"🔧 Qt プラットフォームプラグインパスを設定: {qt_plugin_path}")
            else:
                print(f"⚠️  Qt プラグインディレクトリが見つかりません: {qt_plugin_path}")
        except ImportError:
            print("⚠️  PyQt5がインポートできないため、Qt環境設定をスキップします")


def check_environment_basic():
    """基本的な環境チェック"""
    issues = []
    
    # Python バージョンチェック
    if sys.version_info < (3, 8):
        issues.append("Python 3.8以上が必要です")
    
    # PyQt5のインポートチェック
    try:
        import PyQt5
        from PyQt5 import QtWidgets, QtCore
    except ImportError as e:
        issues.append(f"PyQt5のインポートに失敗: {str(e)}")
        issues.append("解決方法: pip install -r requirements-gui.txt")
    
    return issues


def run_full_environment_check():
    """包括的な環境チェックの実行"""
    print("🔍 環境チェックを実行しています...")
    
    try:
        # check_gui_environment.py を実行
        result = subprocess.run(
            [sys.executable, "check_gui_environment.py"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        print(result.stdout)
        if result.stderr:
            print("エラー出力:", result.stderr)
        
        return result.returncode == 0
        
    except FileNotFoundError:
        print("❌ check_gui_environment.py が見つかりません")
        return False
    except Exception as e:
        print(f"❌ 環境チェック実行中にエラー: {str(e)}")
        return False


def display_quick_help():
    """クイックヘルプの表示"""
    print("\n" + "="*60)
    print("🚀 PDFTranslate2md GUI")
    print("="*60)
    print()
    print("📖 使用方法:")
    print("  python run_gui.py              # 通常起動")
    print("  python run_gui.py --check      # 環境チェックのみ実行")
    print("  python run_gui.py --force      # 環境チェックをスキップして起動")
    print("  python run_gui.py --help       # このヘルプを表示")
    print()
    print("🔧 問題が発生した場合:")
    print("  1. 依存関係のインストール: pip install -r requirements-gui.txt")
    print("  2. 環境チェック実行: python check_gui_environment.py")
    print("  3. ドキュメント確認: docs/GUI_USAGE.md")
    print()


def display_error_help(issues):
    """エラーヘルプの表示"""
    print("\n" + "="*60)
    print("❌ GUI起動前チェックで問題が検出されました")
    print("="*60)
    
    for i, issue in enumerate(issues, 1):
        print(f"{i}. {issue}")
    
    print()
    print("🔧 修復手順:")
    
    # PyQt5関連の問題の場合
    if any("PyQt5" in issue for issue in issues):
        print("  PyQt5の問題が検出されました。以下を試してください:")
        print("  1. pip uninstall PyQt5 PyQt5-Qt5 PyQt5-sip")
        print("  2. pip install -r requirements-gui.txt")
        
        if platform.system() == "Darwin":  # macOS
            print("  3. macOSの場合、Qt環境は自動設定されますが、問題が続く場合は手動設定も可能です:")
            print("     export QT_QPA_PLATFORM_PLUGIN_PATH=$(python -c \"import PyQt5; print(PyQt5.__path__[0])\")/Qt5/plugins")
    
    print()
    print("📝 詳細な環境チェックを実行するには:")
    print("  python check_gui_environment.py")
    print()
    print("🚀 問題を無視して起動する場合（非推奨）:")
    print("  python run_gui.py --force")
    print()


def main():
    """メイン実行関数"""
    # プロジェクトルートをパスに追加
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)
    
    # Qt環境の自動設定（GUI起動前に実行）
    setup_qt_environment()
    
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(
        description="PDFTranslate2md GUI起動スクリプト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python run_gui.py              # 通常起動
  python run_gui.py --check      # 環境チェックのみ
  python run_gui.py --force      # 環境チェックをスキップ
        """
    )
    
    parser.add_argument(
        "--check", 
        action="store_true",
        help="環境チェックのみ実行して終了"
    )
    
    parser.add_argument(
        "--force", 
        action="store_true",
        help="環境チェックをスキップして強制起動（非推奨）"
    )
    
    parser.add_argument(
        "--help-gui", 
        action="store_true",
        help="GUIの使用方法ヘルプを表示"
    )
    
    args = parser.parse_args()
    
    # ヘルプ表示
    if args.help_gui:
        display_quick_help()
        return
    
    # 環境チェックのみ実行
    if args.check:
        success = run_full_environment_check()
        if success:
            print("\n✅ 環境チェック完了。GUIアプリケーションを起動できます。")
        else:
            print("\n❌ 環境に問題があります。上記の提案に従って修正してください。")
        return
    
    # 強制起動モード
    if args.force:
        print("⚠️  環境チェックをスキップしてGUIを起動します...")
    else:
        # 基本的な環境チェック
        print("🔍 基本的な環境をチェック中...")
        issues = check_environment_basic()
        
        if issues:
            display_error_help(issues)
            print("💡 詳細なチェックと修復提案を確認するには:")
            print("   python run_gui.py --check")
            print()
            print("❌ 環境チェックで問題が発見されたため、GUI起動を中止します。")
            print("   修正後に再度実行するか、--force オプションで強制起動してください。")
            sys.exit(1)
        else:
            print("✅ 基本的な環境チェックが完了しました。")
    
    # GUI起動
    try:
        print("🚀 GUIアプリケーションを起動中...")
        from gui.main_gui import main as gui_main
        gui_main()
        
    except ImportError as e:
        print(f"❌ GUIモジュールのインポートに失敗しました: {str(e)}")
        print()
        print("🔧 以下を確認してください:")
        print("  1. 必要な依存関係がインストールされているか")
        print("     pip install -r requirements-gui.txt")
        print("  2. guiディレクトリが存在するか")
        print("  3. 詳細な環境チェック: python check_gui_environment.py")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ GUI起動中にエラーが発生しました: {str(e)}")
        print()
        print("🔧 トラブルシューティング:")
        print("  1. 詳細な環境チェック: python check_gui_environment.py")
        print("  2. PyQt5の再インストール: pip uninstall PyQt5 && pip install -r requirements-gui.txt")
        
        if platform.system() == "Darwin":  # macOS
            print("  3. macOSの場合、Xcode Command Line Toolsの確認: xcode-select --install")
        
        print("  4. ドキュメント確認: docs/GUI_USAGE.md")
        sys.exit(1)


if __name__ == "__main__":
    main()