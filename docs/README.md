# ドキュメント

Config Lensプロジェクトのドキュメント集です。

## ドキュメント一覧

### [ビルド手順](BUILD.md)

PyInstallerを使用してmacOSアプリケーションとしてビルドする方法を詳しく説明しています。

**主な内容**:
- 基本的なビルド手順
- ビルドオプションの説明
- config-lens.specの設定方法
- 配布用パッケージの作成
- よくある質問

**対象読者**: 開発者、ビルド担当者

### [トラブルシューティング](TROUBLESHOOTING.md)

ビルドと実行に関するよくある問題と解決方法をまとめています。

**主な内容**:
- ビルドエラーの解決方法
- 実行時エラーの対処法
- macOS固有の問題
- デバッグ方法
- チェックリスト

**対象読者**: すべてのユーザー

## クイックリンク

### ビルド関連

- [基本的なビルド](BUILD.md#基本的なビルド)
- [デバッグビルド](BUILD.md#デバッグビルド)
- [配布用パッケージの作成](BUILD.md#配布用パッケージの作成)

### トラブルシューティング

- [ModuleNotFoundエラー](TROUBLESHOOTING.md#modulenotfounderror-no-module-named-ui)
- [アプリが起動しない](TROUBLESHOOTING.md#アプリが起動直後に終了する)
- [移動後に起動しない](TROUBLESHOOTING.md#移動後にアプリが起動しない)

## その他のドキュメント

プロジェクトルートの以下のファイルも参照してください：

- [README.md](../README.md) - プロジェクト概要とクイックスタート
- [pyproject.toml](../pyproject.toml) - プロジェクト設定
- [Taskfile.yml](../Taskfile.yml) - タスク定義
- [config-lens.spec](../config-lens.spec) - PyInstallerビルド設定

## 貢献

ドキュメントの改善や追加に関する提案は、issueまたはプルリクエストで受け付けています。
