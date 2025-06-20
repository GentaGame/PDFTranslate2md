# PDFTranslate2md GUI 使用方法

## 概要

PDFTranslate2md GUIは、PDFファイルをAI翻訳してMarkdownファイルに変換するためのデスクトップアプリケーションです。

## インストール

### 1. 基本依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. GUI用依存関係のインストール

```bash
pip install -r requirements-gui.txt
```

### 3. 環境変数の設定

`.env`ファイルを作成し、使用するAIプロバイダーのAPIキーを設定してください：

```env
# Google Gemini
GOOGLE_API_KEY=your_gemini_api_key_here

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# Anthropic Claude
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

## GUI起動方法

```bash
python run_gui.py
```

または

```bash
python -m gui.main_gui
```

## 基本的な使用方法

### 1. ファイル・フォルダの選択

- **ドラッグ&ドロップ**: PDFファイルまたはPDFファイルが含まれるフォルダを入力エリアにドラッグ&ドロップ
- **ボタン選択**: 「ファイル選択」または「フォルダ選択」ボタンをクリックして選択

### 2. 翻訳設定

- **プロバイダー**: 使用するAIプロバイダーを選択（Gemini/OpenAI/Anthropic）
- **モデル**: 使用するモデルを選択
- **接続テスト**: 「🔍 接続テスト」ボタンでAPIの接続を確認

### 3. 出力設定

- **出力先**: 翻訳されたMarkdownファイルの保存先ディレクトリ
- **画像保存先**: 抽出された画像の保存先ディレクトリ
- **強制上書き**: 既存ファイルを上書きするかのオプション

### 4. 処理実行

- **処理開始**: 「🚀 処理開始」ボタンをクリック
- **進捗確認**: 進捗ウィジェットでリアルタイム進捗を確認
- **キャンセル**: 処理中は「⏹️ キャンセル」ボタンで処理を中断可能

## 履歴機能

### 履歴の自動保存

処理を実行すると、設定が自動的に履歴に保存されます。

### 履歴の利用

- **履歴一覧**: 右パネルに過去の処理設定が表示
- **設定適用**: 履歴項目をダブルクリックまたは「📋 設定を適用」ボタンで設定を復元
- **履歴削除**: 不要な履歴は「🗑️ 削除」ボタンで削除

### 履歴管理

- **履歴更新**: 「🔄」ボタンで履歴を手動更新
- **履歴管理メニュー**: 「⋮」ボタンで履歴の一括削除、エクスポート/インポート機能

## 機能詳細

### ファイル・フォルダ処理

- **単一ファイル**: PDFファイルを1つずつ処理
- **バッチ処理**: フォルダ内の全PDFファイルを一括処理
- **進捗表示**: ファイル単位、ページ単位の詳細進捗

### 翻訳処理

- **AI翻訳**: 選択したプロバイダー・モデルで翻訳
- **画像抽出**: PDFから画像を自動抽出
- **エラーハンドリング**: 翻訳エラー時も処理を継続

### ログ・進捗表示

- **リアルタイムログ**: 処理状況をリアルタイム表示
- **進捗バー**: 全体進捗とファイル進捗を分けて表示
- **ログ保存**: ログをファイルに保存可能

## トラブルシューティング

### 起動エラー

```bash
# PyQt5が正しくインストールされているか確認
python -c "import PyQt5; print('PyQt5 OK')"

# 依存関係を再インストール
pip install -r requirements-gui.txt --force-reinstall
```

### API接続エラー

1. **APIキーの確認**: `.env`ファイルでAPIキーが正しく設定されているか確認
2. **接続テスト**: GUIの「🔍 接続テスト」ボタンで接続確認
3. **ネットワーク**: インターネット接続と必要なポートが開いているか確認

### 処理エラー

1. **入力ファイル**: PDFファイルが破損していないか確認
2. **権限**: 出力ディレクトリへの書き込み権限があるか確認
3. **ディスク容量**: 十分な空き容量があるか確認

### メモリエラー

- **大きなPDFファイル**: ファイルサイズが大きすぎる場合、ページ分割を検討
- **バッチ処理**: 一度に処理するファイル数を減らす

## 設定ファイル

### アプリケーション設定

GUIの設定は自動的に保存され、次回起動時に復元されます：

- ウィンドウサイズ・位置
- 最後に使用したプロバイダー・モデル
- 出力ディレクトリ設定

### 履歴ファイル

処理履歴は`gui_history.json`ファイルに保存されます。

## ショートカットキー

- **Ctrl+O**: ファイル選択ダイアログを開く
- **Ctrl+Q**: アプリケーション終了

## FAQ

### Q: 複数のPDFファイルを同時に処理できますか？

A: はい。フォルダを選択することで、フォルダ内の全PDFファイルをバッチ処理できます。

### Q: 処理中にPCをスリープモードにしても大丈夫ですか？

A: 処理が中断される可能性があります。長時間の処理中はスリープモードを無効にすることをお勧めします。

### Q: 異なるプロバイダーを同時に使用できますか？

A: 1回の処理では1つのプロバイダーのみ使用できます。異なるプロバイダーを使用する場合は、別々に処理を実行してください。

### Q: 履歴はどのくらい保存されますか？

A: 履歴に保存期限はありません。手動で削除するまで保持されます。

### Q: オフラインで使用できますか？

A: AI翻訳にはインターネット接続が必要です。PDF読み込みや基本機能はオフラインでも動作します。

## サポート

問題が発生した場合：

1. ログファイル（`gui_pdftranslate2md.log`）を確認
2. 設定ファイルをリセット（アプリケーション設定フォルダを削除）
3. GitHubのIssueで報告

## 更新履歴

### v1.0.0 (2025-01-12)
- 初回リリース
- PyQt5ベースのGUI実装
- 履歴機能
- ドラッグ&ドロップ対応
- リアルタイム進捗表示