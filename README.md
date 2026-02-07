# Config Lens

ネットワーク機器のコンフィグを解析・比較するGUIアプリケーション

## 概要

Config Lensは、Cisco等のネットワーク機器のコンフィグレーションファイルを解析し、差分を視覚的に表示するツールです。CustomTkinterを使用した直感的なGUIで、設定変更の確認や監査作業を効率化します。

## 特徴

- 🎨 モダンなGUI（CustomTkinter）
- 📊 コンフィグの差分表示
- 🔍 階層的な設定解析（hier-config）
- 🍎 macOSネイティブアプリケーション対応

## 必要要件

- Python 3.13以上（推奨）
- uv（パッケージマネージャー）
- Task（タスクランナー）

## クイックスタート

### 1. 環境のセットアップ

````bash
# 依存関係のインストール
task install

# または
uv sync
````

### 2. 開発環境で実行

````bash
# アプリケーションを起動
uv run python src/main.py
````

### 3. macOSアプリとしてビルド

````bash
# リリースビルド
task build

# ビルドして実行
task run

# クリーンビルド
task clean
````

## タスクコマンド

利用可能なタスクの一覧：

````bash
task                # タスク一覧を表示
task build          # リリースビルド
task build-signed   # 署名付きビルド
task run            # ビルドして実行
task dev-build      # デバッグビルド
task lint           # コードチェック
task lint-fix       # 自動修正
task type-check     # 型チェック
task test           # テスト実行
task check          # すべてのチェック実行
````

## プロジェクト構造

````
config-lens/
├── src/
│   ├── main.py              # エントリーポイント
│   ├── ui/                  # UIコンポーネント
│   │   ├── main_window.py   # メインウィンドウ
│   │   └── widgets/         # カスタムウィジェット
│   ├── services/            # ビジネスロジック
│   └── models/              # データモデル
├── tests/                   # テストコード
├── config-lens.spec         # PyInstallerビルド設定
├── Taskfile.yml            # タスク定義
└── pyproject.toml          # プロジェクト設定
````

## 技術スタック

- **言語**: Python 3.14
- **パッケージ管理**: uv
- **GUI**: CustomTkinter
- **コンフィグ解析**: hier-config
- **ビルドツール**: PyInstaller
- **リンター**: ruff
- **型チェック**: pyright
- **テスト**: pytest

## ドキュメント

- [ビルド手順](docs/BUILD.md) - 詳細なビルド手順とオプション
- [トラブルシューティング](docs/TROUBLESHOOTING.md) - よくある問題と解決方法

## 開発ガイドライン

開発時は以下のガイドラインに従ってください：

1. **コードスタイル**: PEP 8に準拠
2. **型ヒント**: すべての関数に型アノテーションを追加
3. **テスト**: 新機能には必ずテストを追加
4. **コミット**: [Conventional Commits](https://www.conventionalcommits.org/)形式を使用

### コミットメッセージ規約

- `feat:` 新機能の追加
- `fix:` バグ修正
- `docs:` ドキュメントの変更
- `style:` コードのスタイル変更
- `refactor:` リファクタリング
- `test:` テストの追加・修正
- `chore:` その他の変更

## ライセンス

TBD

## 作者

kazuki