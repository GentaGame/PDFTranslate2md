# PDFTranslate2md

PDFファイルからテキストを抽出し、LLMのAPIを使用して翻訳し、Markdownファイルとして保存するPythonツールです。学術論文や技術文書を効率的に翻訳するために設計されています。

## 主な機能

- PDFファイルからテキストを抽出
- 抽出したテキストをGemini APIで日本語（または指定した言語）に翻訳
- ページ単位で翻訳を実施し、進捗状況を表示
- Markdownフォーマットで保存（見出し構造を保持）
- PDFの各ページを高品質な画像として保存
- 翻訳時にMarkdownの見出し構造を自動的に整形
- フォルダ内の全PDFファイルを一括処理
- 出力先ディレクトリを指定可能（Obsidianなどのノートアプリと連携しやすい）
- 参考文献の番号とテキスト内の引用をリンク化
- 既存の出力ファイルがある場合は処理をスキップ（--forceオプションで上書き可能）

## インストール方法

1. リポジトリをクローンする
```bash
git clone <repository-url>
cd PDFTranslate2md
```

2. 必要なパッケージをインストール
```bash
pip install -r requirements.txt
```

3. `.env`ファイルを作成し、Gemini APIキーを設定
```
GEMINI_API_KEY=your_api_key_here
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

### 基本的な使用方法

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

## 注意事項

- 大きなPDFファイルの処理には時間がかかることがあります
- Gemini APIの利用には有効なAPIキーが必要です
- 一部の複雑なレイアウトのPDFではテキスト抽出の精度が低下する場合があります