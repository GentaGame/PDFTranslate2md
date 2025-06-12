# PDFTranslate2md

PDFファイルからテキストを抽出し、LLMのAPIを使用して翻訳し、Markdownファイルとして保存するPythonツールです。学術論文や技術文書を効率的に翻訳するために設計されています。

## 主な機能

### 📱 GUIアプリケーション（NEW!）
- **PyQt5ベースのデスクトップGUI**: 直感的な操作でPDF翻訳
- **ドラッグ&ドロップ対応**: ファイル・フォルダを簡単に選択
- **リアルタイム進捗表示**: 処理状況をリアルタイム監視
- **履歴機能**: 処理設定の保存・呼び出し・管理
- **バッチ処理**: 複数PDFファイルの一括処理
- **キャンセル機能**: 処理中断とエラーハンドリング

### 🖥️ CLIツール
- PDFファイルからテキストを抽出
- 抽出したテキストを多様なLLM APIで日本語（または指定した言語）に翻訳
- ページ単位で翻訳を実施し、進捗状況を表示
- Markdownフォーマットで保存（見出し構造を保持）
- PDFの各ページを高品質な画像として保存
- 翻訳時にMarkdownの見出し構造を自動的に整形
- フォルダ内の全PDFファイルを一括処理
- 出力先ディレクトリを指定可能（Obsidianなどのノートアプリと連携しやすい）
- 参考文献の番号とテキスト内の引用をリンク化
- 既存の出力ファイルがある場合は処理をスキップ（--forceオプションで上書き可能）

### 🤖 対応AIプロバイダー
- **Google Gemini**: gemini-1.5-pro-latest, gemini-1.5-flash-latest
- **OpenAI**: gpt-4o, gpt-4o-mini, gpt-4-turbo
- **Anthropic Claude**: claude-3-5-sonnet, claude-3-5-haiku, claude-3-opus

## インストール方法

1. リポジトリをクローンする
```bash
git clone <repository-url>
cd PDFTranslate2md
```

2. 必要なパッケージをインストール

**CLIのみ使用する場合:**
```bash
pip install -r requirements.txt
```

**GUI版を使用する場合（推奨）:**
```bash
pip install -r requirements.txt
pip install -r requirements-gui.txt
```

**macOS環境でのGUI依存関係インストール:**
```bash
# 環境チェック実行（推奨）
python check_gui_environment.py

# 基本的なインストール
pip install -r requirements-gui.txt

# 問題が発生した場合の修復手順:
# 1. 既存のPyQt5を完全削除
pip uninstall PyQt5 PyQt5-Qt5 PyQt5-sip -y

# 2. 特定バージョンで再インストール
pip install PyQt5==5.15.7 PyQt5-Qt5==5.15.2 PyQt5-sip==12.11.0

# 3. Xcode Command Line Toolsの確認（必要に応じて）
xcode-select --install

# 4. 環境変数設定（問題が続く場合）
export QT_QPA_PLATFORM_PLUGIN_PATH=$(python -c "import PyQt5; print(PyQt5.__path__[0])")/Qt5/plugins
```

3. `.env`ファイルを作成し、使用するプロバイダーのAPIキーを設定
```env
# 使用するプロバイダーのAPIキーを設定
GOOGLE_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

## 環境変数設定

- GEMINI_API_KEY: Google Gemini APIキー
- OPENAI_API_KEY: OpenAI APIキー
- ANTHROPIC_API_KEY: Anthropic (Claude) APIキー

## 依存ライブラリ

- PyPDF2: PDFからテキスト抽出
- PyMuPDF (fitz): PDFからの画像抽出
- python-dotenv: 環境変数管理
- google-generativeai: Gemini APIとの連携
- tqdm: 進捗状況の表示
- Pillow
- openai
- anthropic

## 使用方法

### 🖥️ GUI版（推奨）

```bash
# GUI版を起動
python run_gui.py
```

**GUIの主な機能:**
- ドラッグ&ドロップでファイル・フォルダ選択
- プロバイダー・モデル選択
- リアルタイム進捗表示
- 履歴機能で設定の保存・呼び出し
- 処理のキャンセル機能

詳細な使用方法は [`docs/GUI_USAGE.md`](docs/GUI_USAGE.md) を参照してください。

### 💻 CLI版

```bash
# 単一のPDFファイルを処理
python src/main.py input.pdf

# ディレクトリ内のすべてのPDFファイルを処理
python src/main.py input_directory
```

これにより、入力PDFと同じ名前（拡張子が.md）のMarkdownファイルが生成されます。

### オプション指定

```bash
python src/main.py input.pdf \
  [-p gemini|openai|claude|anthropic] \
  [-m モデル名] \
  [-o output_directory] \
  [-i images_directory] \
  [-f, --force]
```

#### オプション説明:
- `-p, --provider`: 使用するLLMプロバイダー（デフォルト: gemini）
- `-m, --model-name`: LLMモデル名（指定しない場合はプロバイダー毎のデフォルト）
- `-o, --output-dir`: 出力先ディレクトリ（指定しない場合は現在のディレクトリ）
- `-i, --image-dir`: 画像出力ディレクトリ（指定しない場合は出力ディレクトリ内の"images"フォルダ）
- `-f, --force`: 既存のMarkdownファイルが存在する場合も強制的に上書きする

### ディレクトリ処理の例

```bash
# フォルダ内のすべてのPDFを処理して特定のフォルダに出力（Obsidianのフォルダなど）
python src/main.py /path/to/pdf_folder -o /path/to/obsidian/notes

# PDFファイルの画像を特定のフォルダに保存
python src/main.py /path/to/pdf_folder -o /path/to/output -i /path/to/output/images
```

### PDF抽出ツールの単体使用

テキストと画像の抽出のみを行う場合:

```bash
python src/pdf_extractor.py input.pdf -o images_directory
```

#### オプション説明:
- `-o, --output_dir`: 抽出した画像の保存先ディレクトリ
- `-t, --text_only`: テキストのみを抽出する
- `-i, --images_only`: 画像のみを抽出する

## Obsidianなどのノートアプリとの連携

出力先ディレクトリを指定することで、直接Obsidianのノートフォルダに翻訳結果を保存できます。
各PDFファイルは個別のMarkdownファイルとして出力され、画像はPDF名のサブフォルダに整理されるため、
ノート管理がしやすくなっています。

### 参考文献のリンク

論文の参考文献と本文中の引用（[1], [2]など）が自動的にリンク化されます。
これにより、Obsidianなどのマークダウンビューアで参考文献をクリックすると、
対応する参考文献の位置にジャンプできます。

### バッチ処理と再実行

フォルダ内の複数のPDFを処理する際、既に出力先に同名の.mdファイルが存在する場合は
処理をスキップします。これによりAPI呼び出しのコストを削減できます。

既存ファイルを上書きするには `--force` オプションを使用します：
```bash
python src/main.py /path/to/pdf_folder -o /path/to/output -f
```

## 出力例

入力PDFに対して以下の出力が得られます：

1. Markdownファイル（翻訳済みテキスト）
2. 各ページの高品質画像（imagesディレクトリ内）

## 📁 プロジェクト構造

```
PDFTranslate2md/
├── src/                      # コアライブラリ
│   ├── main.py              # CLI エントリーポイント
│   ├── app_controller.py    # アプリケーション制御層
│   ├── pdf_extractor.py     # PDF処理
│   ├── translator_service.py # 翻訳サービス
│   └── providers/           # AIプロバイダー実装
├── gui/                      # GUI アプリケーション
│   ├── main_gui.py          # メインGUIアプリケーション
│   ├── gui_app_controller.py # GUI用制御層
│   ├── history_manager.py   # 履歴管理
│   └── widgets/             # カスタムウィジェット
├── docs/                     # ドキュメント
│   ├── GUI_USAGE.md         # GUI使用方法
│   └── GUI_ARCHITECTURE_DESIGN.md
├── examples/                 # サンプル・設定例
├── requirements.txt          # 基本依存関係
├── requirements-gui.txt      # GUI用依存関係
└── run_gui.py               # GUI起動スクリプト
```

## ⚡ クイックスタート

### GUI版（初心者向け）

1. **インストール:**
   ```bash
   git clone <repository-url>
   cd PDFTranslate2md
   pip install -r requirements.txt requirements-gui.txt
   ```

2. **APIキー設定:**
   ```bash
   cp .env.example .env
   # .envファイルを編集してAPIキーを設定
   ```

3. **GUI起動:**
   ```bash
   python run_gui.py
   ```

4. **使用:**
   - PDFファイルをドラッグ&ドロップ
   - プロバイダー・モデルを選択
   - 「🚀 処理開始」をクリック

### CLI版（上級者向け）

```bash
# 基本使用
python src/main.py input.pdf -p gemini -o output_dir

# プロバイダー指定
python src/main.py folder/ -p openai -m gpt-4o

# バッチ処理
python src/main.py pdfs/ -o translated/ -i images/ -f
```

## 🎯 サンプル・テスト

```bash
# GUI設定例とテスト
python examples/sample_gui_config.py

# 依存関係チェック
python -c "import PyQt5; print('GUI Ready!')"
```

## 📋 要件

- **Python**: 3.8以上
- **OS**: Windows, macOS, Linux
- **メモリ**: 4GB以上推奨
- **ネットワーク**: AI API接続用

## 🔧 トラブルシューティング

### 環境チェックと診断
```bash
# 包括的な環境チェック実行
python check_gui_environment.py

# 基本的な環境チェックのみ
python run_gui.py --check

# 環境チェックをスキップして強制起動（非推奨）
python run_gui.py --force
```

### GUI起動エラー

#### macOS環境での一般的な問題
```bash
# 1. PyQt5の完全再インストール
pip uninstall PyQt5 PyQt5-Qt5 PyQt5-sip -y
pip install PyQt5==5.15.7 PyQt5-Qt5==5.15.2 PyQt5-sip==12.11.0

# 2. Xcode Command Line Toolsの確認
xcode-select --print-path
# 出力がない場合は以下を実行:
xcode-select --install

# 3. 環境変数設定（プラットフォームプラグインエラーの場合）
export QT_QPA_PLATFORM_PLUGIN_PATH=$(python -c "import PyQt5; print(PyQt5.__path__[0])")/Qt5/plugins

# 4. Homebrewを使用した代替インストール（最終手段）
brew install pyqt@5
```

#### Linux環境での問題
```bash
# Qt5関連パッケージのインストール
sudo apt-get install qt5-default libqt5gui5 libqt5widgets5  # Ubuntu/Debian
sudo yum install qt5-qtbase-devel  # RHEL/CentOS

# X11 DISPLAYの設定確認
echo $DISPLAY
export DISPLAY=:0.0  # 必要に応じて設定
```

#### Windows環境での問題
```bash
# Visual C++ Redistributableの確認
# https://aka.ms/vs/17/release/vc_redist.x64.exe

# PyQt5の再インストール
pip install --upgrade pip
pip install -r requirements-gui.txt --force-reinstall
```

### API接続エラー
- `.env`ファイルでAPIキー確認
- GUIの「🔍 接続テスト」で接続確認
- ネットワーク・ファイアウォール設定確認
- プロキシ環境の場合は適切な設定が必要

### パフォーマンス問題
```bash
# メモリ使用量の確認
python -c "import psutil; print(f'Available memory: {psutil.virtual_memory().available / 1024**3:.1f} GB')"

# 大きなPDFファイルの分割処理
# GUIの「バッチサイズ」設定を調整
```

### その他の問題
```bash
# 依存関係の確認
python examples/sample_gui_config.py

# Python環境の確認
python --version
pip list | grep PyQt5

# ログファイルの確認（問題発生時）
# GUI起動時に生成されるログを確認
```

## 📖 ドキュメント

- [GUI使用方法](docs/GUI_USAGE.md)
- [アーキテクチャ設計](docs/GUI_ARCHITECTURE_DESIGN.md)

## 注意事項

- 大きなPDFファイルの処理には時間がかかることがあります
- AI APIの利用には有効なAPIキーが必要です
- 一部の複雑なレイアウトのPDFではテキスト抽出の精度が低下する場合があります
- GUI版では処理中にスリープモードにならないよう注意してください