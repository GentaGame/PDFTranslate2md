# PDFTranslate2md

PDFファイルからテキストを抽出し、Gemini APIを使用して翻訳し、Markdownファイルとして保存するPythonツールです。学術論文や技術文書を効率的に翻訳するために設計されています。

## 主な機能

- PDFファイルからテキストを抽出
- 抽出したテキストをGemini APIで日本語（または指定した言語）に翻訳
- ページ単位で翻訳を実施し、進捗状況を表示
- Markdownフォーマットで保存（見出し構造を保持）
- PDFの各ページを高品質な画像として保存
- 翻訳時にMarkdownの見出し構造を自動的に整形

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

## 依存ライブラリ

- PyPDF2: PDFからテキスト抽出
- PyMuPDF (fitz): PDFからの画像抽出
- python-dotenv: 環境変数管理
- google-generativeai: Gemini APIとの連携
- tqdm: 進捗状況の表示

## 使用方法

### 基本的な使用方法

```bash
python src/main.py input.pdf
```

これにより、入力PDFと同じ名前（拡張子が.md）のMarkdownファイルが生成されます。

### オプション指定

```bash
python src/main.py input.pdf -o output.md -i images_directory
```

#### オプション説明:
- `-o, --output`: 出力Markdownファイルのパス（指定しない場合、入力PDFと同名の.mdファイル）
- `-i, --image_dir`: 画像出力ディレクトリ（指定しない場合、"images"フォルダ）

### PDF抽出ツールの単体使用

テキストと画像の抽出のみを行う場合:

```bash
python src/pdf_extractor.py input.pdf -o images_directory
```

#### オプション説明:
- `-o, --output_dir`: 抽出した画像の保存先ディレクトリ
- `-t, --text_only`: テキストのみを抽出する
- `-i, --images_only`: 画像のみを抽出する

## 出力例

入力PDFに対して以下の出力が得られます：

1. Markdownファイル（翻訳済みテキスト）
2. 各ページの高品質画像（imagesディレクトリ内）

## 注意事項

- 大きなPDFファイルの処理には時間がかかることがあります
- Gemini APIの利用には有効なAPIキーが必要です
- 一部の複雑なレイアウトのPDFではテキスト抽出の精度が低下する場合があります