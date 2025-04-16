# PDFTranslate2md

PDFファイルからテキストを抽出し、Markdownファイルとして保存するPythonツール。将来的にはGemini APIなどを使用して翻訳機能も追加予定。

## 機能

- PDFファイルからテキストを抽出
- 抽出したテキストをMarkdownファイルとして保存
- ページごとに区切りを入れて出力
- （将来）抽出したテキストを翻訳して出力

## 実装計画

### モジュール構造

1. **PDF抽出モジュール (PDFExtractor)**
   - PyPDF2 または pdfminer.six ライブラリを使用
   - PDFファイルからページごとにテキストを抽出
   - 抽出したテキストをリスト形式で返却

2. **Markdown出力モジュール (MarkdownWriter)**
   - 抽出したテキストをMarkdownファイルとして保存
   - ページごとに区切りを入れて出力

3. **将来的な拡張**
   - 翻訳モジュール (Translator) の追加
   - Gemini APIなど、様々な翻訳サービスに対応できるよう設計

### フロー図

```mermaid
graph TD
    A[main.py] --> B[PDFExtractor.extract(pdf_path)]
    B --> C[各ページのテキスト取得]
    C --> D[ページごとに区切りを挿入]
    D --> E[結果をリストで返却]
    A --> F[MarkdownWriter.write(markdown_path, text_list)]
    F --> G[.mdファイルにテキスト書き出し]
    A --> H[将来的なTranslatorモジュール（オプション）]
```

## 使用方法

```bash
python src/main.py input.pdf output.md
```

## 必要なライブラリ

- PyPDF2 または pdfminer.six (PDFテキスト抽出用)