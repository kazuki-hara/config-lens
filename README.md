# ConfigLens

ネットワーク機器のコンフィグを比較・差分確認するためのGUIアプリケーションです。

## 動作環境

| 項目 | 要件 |
|---|---|
| Python | 3.14 以上 |
| パッケージ管理 | [uv](https://docs.astral.sh/uv/) |
| タスクランナー | [Task](https://taskfile.dev/) |

## セットアップ

```bash
# 依存パッケージをインストール
uv sync --all-groups
```

## 開発用コマンド

| コマンド | 説明 |
|---|---|
| `task run` | アプリを直接起動（開発用） |
| `task test` | pytestでテストを実行 |
| `task lint` | ruff + pyright でリント・型チェック |
| `task build` | 現在のOSに合わせてビルド |
| `task build:mac` | macOS向け `.app` バンドルをビルド |
| `task build:win` | Windows向け `.exe` をビルド |
| `task clean` | ビルド成果物を削除 |

## インストール（リリース版）

[Releases](../../releases/latest) ページから最新版をダウンロードしてください。

### macOS

1. `ConfigLens-mac.zip` をダウンロードして展開する
2. `ConfigLens.app` をアプリケーションフォルダに移動する
3. 初回起動時は`システム設定`→`プライバシーとセキュリティ`でConfigLensを許可する必要があります。

   > macOS のセキュリティ警告が表示された場合は「開く」をクリックします。
   > ターミナルで以下を実行してから起動することもできます。
   > ```bash
   > xattr -d com.apple.quarantine /Applications/ConfigLens.app
   > ```

### Windows

1. `ConfigLens.exe` をダウンロードする
2. ダブルクリックして起動する

---

## CI/CD

mainブランチへのpush・マージ時に GitHub Actions が自動実行されます。

### ワークフロー構成

```
push / PR to main
      │
      ▼
┌─────────────┐
│  test-lint  │  テスト & リント（ubuntu）
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

### 各ジョブの詳細

| ジョブ | ランナー | 実行内容 |
|---|---|---|
| `test-lint` | ubuntu-latest | `task test` → `task lint` |
| `build-mac` | macos-latest | `task build:mac` → `dist/ConfigLens.app` をzip化 |
| `build-windows` | windows-latest | `task build:win` → `dist/ConfigLens.exe` |
| `release` | ubuntu-latest | 両ビルド成果物をGitHub Releasesに登録 |

### 動作ルール

- **PRのとき**: `test-lint` のみ実行。ビルド・リリースはスキップ。
- **mainへのpushのとき**: `test-lint` 通過後にビルドを並列実行し、両方成功したらリリースを作成。

### バージョン管理

`pyproject.toml` の `version` フィールドの値をリリースタグとして使用します（例: `version = "1.2.0"` → タグ `v1.2.0`）。

```toml
# pyproject.toml
[project]
version = "1.2.0"  # ← ここを更新してmainにpushするとリリースが作られる
```

- 同じバージョンで再pushした場合は既存のリリースが上書きされます
- バージョンを上げてpushすると新しいリリースが作成されます
