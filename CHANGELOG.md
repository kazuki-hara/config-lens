# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- PyInstallerによるmacOSアプリケーションビルド機能
- 自動モジュール収集機能（config-lens.spec）
- Taskfileによるビルドタスク管理
- コード署名サポート
- DMG配布パッケージ作成機能
- 包括的なビルドドキュメント（docs/BUILD.md）
- トラブルシューティングガイド（docs/TROUBLESHOOTING.md）
- CustomTkinterベースのGUI実装

### Changed

- Python 3.13を推奨バージョンに変更（3.14の互換性問題を回避）
- プロジェクト構造をdocs/ディレクトリに整理

### Fixed

- ModuleNotFoundエラーの修正（ローカルモジュールの自動検出）
- CustomTkinterリソース読み込みの問題を解決
- アプリケーション移動時の起動問題を修正
- `mainloop()`メソッドの正しい使用方法を実装

## [0.1.0] - 2026-02-08

### Added

- 初期プロジェクトセットアップ
- 基本的なプロジェクト構造
- uvによるパッケージ管理
- ruffとpyrightによるコード品質管理
- pytestによるテスト環境

[Unreleased]: https://github.com/username/config-lens/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/username/config-lens/releases/tag/v0.1.0
