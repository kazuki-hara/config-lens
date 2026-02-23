# 開発ガイド

開発環境のセットアップからコード規約・テスト・CI/CD まで説明します。

---

## 必要なツール

| ツール | バージョン | 用途 |
|---|---|---|
| Python | 3.14 以上 | アプリケーション実行環境 |
| [uv](https://docs.astral.sh/uv/) | 最新版 | パッケージ管理・仮想環境 |
| [Task](https://taskfile.dev/) | 最新版 | タスクランナー |

---

## 開発環境のセットアップ

```bash
# 1. リポジトリをクローン
git clone <repository-url>
cd config-lens

# 2. 依存パッケージをインストール（開発依存含む）
uv sync --all-groups

# 3. アプリを起動して動作確認
task run
```

---

## タスク一覧

`task --list` でタスクを一覧表示できます。

| タスク | コマンド | 説明 |
|---|---|---|
| アプリ起動 | `task run` | アプリを直接起動（開発用） |
| テスト実行 | `task test` | pytest でテストを実行 |
| リント・型チェック | `task lint` | ruff + pyright でコード検査 |
| macOS ビルド | `task build:mac` | macOS 向け `.app` バンドルをビルド |
| Windows ビルド | `task build:win` | Windows 向け `.exe` をビルド |
| クロスプラットフォームビルド | `task build` | 現在の OS に合わせてビルド |
| クリーン | `task clean` | ビルド成果物（`build/` `dist/`）を削除 |
| アイコン生成 | `task icon:generate` | プレースホルダーアイコンを生成 |

---

## コード規約

[`.github/instructions/python.instructions.md`](../.github/instructions/python.instructions.md) に準拠します。

### スタイルガイド

- **型ヒント** — 関数の引数・戻り値に型ヒントを必ず付与する
- **命名規則** — 変数・関数はスネークケース、クラスはパスカルケース
- **インデント** — スペース4つ（タブ禁止）
- **行長** — 最大79文字
- **docstring** — Google 形式で記述する
- **f-string** — 文字列フォーマットは `f-string` を優先する
- **未使用インポート** — 不要なインポートは削除する

### Docstring の例（Google 形式）

```python
def calcurate_hierarcihical_path(config: list[str]) -> list[list[str]]:
    """階層構造を持つコンフィグの階層パスを計算する。

    Args:
        config: コンフィグの行のリスト

    Returns:
        各行の階層パスのリスト

    Example:
        >>> lines = ["interface Gi0/0", " no shutdown"]
        >>> result = calcurate_hierarcihical_path(lines)
        >>> result[1]
        ['interface Gi0/0', 'no shutdown']
    """
```

---

## リント・型チェック

```bash
# ruff でリント
uv run ruff check src tests

# pyright で型チェック
uv run pyright src
```

または、まとめて実行：

```bash
task lint
```

---

## テスト

[`.github/instructions/tests.instructions.md`](../.github/instructions/tests.instructions.md) に準拠します。

### テストの実行

```bash
# すべてのテストを実行
task test

# 直接 pytest を実行（オプション付き）
uv run pytest -v
uv run pytest tests/compare/test_logic.py -v
```

### テスト構成

| ファイル | テスト対象 |
|---|---|
| `tests/test_utils.py` | `src/utils.py` のユーティリティ関数 |
| `tests/compare/test_logic.py` | `src/compare/logic.py` の差分計算ロジック |
| `tests/compare/test_ignore.py` | `src/compare/ignore.py` の Ignore パターン管理 |

### フィクスチャファイル

`tests/fixtures/` にテスト用のコンフィグファイルが配置されています。

| ファイル | 用途 |
|---|---|
| `source.txt` | 比較元コンフィグ（主にロジックテスト用） |
| `target.txt` | 比較先コンフィグ（主にロジックテスト用） |
| `demo_source.txt` | デモ用コンフィグ |
| `demo_target.txt` | デモ用コンフィグ |
| `config/source_config.txt` | 詳細なコンフィグサンプル |
| `config/target_config.txt` | 詳細なコンフィグサンプル |

### テスト作成の指針

- `pytest` を使用し、各テストは独立して実行できること
- テスト関数・クラス名は `test_` プレフィックスで始める
- 設定ファイルを扱うテストは `tmp_path` フィクスチャを使い、本番データを汚染しない

```python
@pytest.fixture
def tmp_settings(tmp_path: Path) -> AppSettings:
    """一時ディレクトリを使用する AppSettings インスタンスを返す。"""
    import src.compare.settings as settings_module
    original_dir = settings_module._SETTINGS_DIR
    original_file = settings_module._SETTINGS_FILE
    try:
        settings_module._SETTINGS_DIR = tmp_path
        settings_module._SETTINGS_FILE = tmp_path / "settings.json"
        yield AppSettings()
    finally:
        settings_module._SETTINGS_DIR = original_dir
        settings_module._SETTINGS_FILE = original_file
```

---

## ビルド

### macOS 向けビルド

```bash
task build:mac
```

- `--onedir` + `--windowed` モードで `.app` バンドルを生成します。
- ビルド成果物: `dist/ConfigLens.app`
- `assets/icon.icns` が存在する場合、アイコンとして使用されます。

### Windows 向けビルド

```bash
task build:win
```

- `--onefile` + `--windowed` モードで単一 `.exe` を生成します。
- ビルド成果物: `dist/ConfigLens.exe`
- `assets/icon.ico` が存在する場合、アイコンとして使用されます。

### アイコンの準備

```bash
task icon:generate
```

`scripts/generate_icon.py` でプレースホルダーアイコンを生成できます。

---

## CI/CD

### ワークフロー概要

GitHub Actions でテスト・ビルド・リリースを自動化しています。

```
push / PR to main
      │
      ▼
┌─────────────┐
│  test-lint  │  テスト & リント（ubuntu-latest）
└──────┬──────┘
       │ 成功かつ push to main の場合のみ
       ├────────────────────┐
       ▼                    ▼
┌────────────┐     ┌────────────────┐
│ build-mac  │     │ build-windows  │  (並列実行)
│ (macos)    │     │ (windows)      │
└──────┬─────┘     └───────┬────────┘
       └──────────┬─────────┘
                  ▼
           ┌─────────┐
           │ release │  GitHub Releases に自動登録
           └─────────┘
```

### 各ジョブ

| ジョブ | ランナー | 実行内容 |
|---|---|---|
| `test-lint` | ubuntu-latest | `task test` → `task lint` |
| `build-mac` | macos-latest | `task build:mac` → zip 化 |
| `build-windows` | windows-latest | `task build:win` |
| `release` | ubuntu-latest | 両ビルド成果物を GitHub Releases に登録 |

### 動作ルール

- **PRのとき**: `test-lint` のみ実行。ビルド・リリースはスキップ。
- **mainへのpushのとき**: `test-lint` 通過後にビルドを並列実行し、両方成功したらリリースを作成。

### バージョン管理

`pyproject.toml` の `version` フィールドがリリースタグになります。

```toml
[project]
version = "1.2.0"  # ← ここを更新して main に push するとリリースが作られる
```

- 同一バージョンで再 push した場合: 既存のリリースが上書きされます
- バージョンを上げて push した場合: 新しいリリースが作成されます

---

## 新機能の追加手順

1. `feature/xxx` ブランチを作成する（詳細は [コントリビューション](contributing.md) 参照）
2. `src/compare/` 以下に新しいモジュールを追加する
3. ナビゲーションバーに対応するボタンを `src/menu.py` の `NavigationFrame` に追加する
4. `src/app.py` の `DiffViewerApp` に新しいビューのインスタンスを追加し、コールバックで切り替える
5. テストを `tests/` 以下に追加する（命名: `test_<機能名>.py`）
6. `task lint` と `task test` がすべてパスすることを確認する
