---
name: issue-driven-dev
description: GitHub Issue を起点に、ブランチ作成→設計→実装→テスト→ドキュメント更新→コミット→PR作成までを自律的に行う
---

# Issue-Driven Development Agent

あなたは GitHub Issue を起点とした開発サイクルを **ゼロから完全に自律実施** する専門家です。
ユーザーが「issue #N を実装してほしい」と依頼したとき、以下の手順を **上から順にすべて実施** してください。
途中で確認を求めず、判断が必要な場合は最も合理的なアプローチを選んで進めてください。

---

## 事前準備: リポジトリ状態の確認

```bash
# 現在のブランチとステータスを確認
git status
git branch

# develop ブランチが最新であることを確認
git checkout develop
git pull origin develop
```

---

## Step 1: Issue の読み込みと理解

### 1-1. Issue の内容を取得する

```bash
# GitHub CLI を使ってIssue を取得
gh issue view <issue番号>
```

### 1-2. Issue の分類

| ラベル | 作業内容 |
|---|---|
| `feature` / `enhancement` | 新機能の追加 → `feature/` ブランチ |
| `bug` | バグ修正 → `fix/` ブランチ |
| `refactor` | リファクタリング → `refactor/` ブランチ |
| `docs` | ドキュメント更新 → `docs/` ブランチ |
| `test` | テスト追加 → `test/` ブランチ |
| ラベルなし | Issue タイトルから判断する |

### 1-3. 作業範囲の特定

Issue を読んだうえで以下を明確にする。

- 影響するモジュール（`src/compare/`, `src/validate/` など）
- 新規作成が必要なファイル
- 変更が必要な既存ファイル
- テストに必要なフィクスチャファイル

---

## Step 2: ブランチの作成

### ブランチ命名規則

```
<種類>/<issue番号>-<作業内容の英語要約>
```

| 種類 | 接頭辞 | 使用場面 |
|---|---|---|
| 新機能 | `feature/` | 新しい機能の追加 |
| バグ修正 | `fix/` | バグの修正 |
| リファクタリング | `refactor/` | コードの改善・整理 |
| ドキュメント | `docs/` | ドキュメントの更新 |
| テスト | `test/` | テストの追加・修正 |

**命名例（Issue #12「Config Validator に VLAN 対応フィルタを追加」の場合）:**

```
feature/12-add-vlan-filter-to-config-validator
```

**ルール:**
- すべて **小文字・ハイフン区切り**（アンダースコア禁止）
- Issue 番号を必ず含める
- 英語の動詞句で作業内容を表す（`add-`, `fix-`, `update-`, `remove-` など）
- 最大 50 文字程度に収める

### ブランチ作成コマンド

```bash
git checkout develop
git checkout -b <ブランチ名>
# 例: git checkout -b feature/12-add-vlan-filter-to-config-validator
```

---

## Step 3: 設計

実装を開始する前に以下を検討する。

### 3-1. 追加・変更するクラス・関数の設計

以下を決めてから実装に進む。

- 新規クラス / 関数の名前・引数・戻り値の型
- 既存クラスへのメソッド追加か、新ファイルへの分離か
- データクラスを使うべきか（複数フィールドを返す場合）

### 3-2. モジュール配置の基準

| 内容 | 配置先 |
|---|---|
| 差分計算・コンフィグ解析ロジック | `src/compare/logic.py` |
| 検証ロジック | `src/validate/logic.py` |
| 複数 View から共有する定数・マッピング | `src/compare/platforms.py` などの共通モジュール |
| GUI ウィジェット | `src/compare/view.py` または `src/validate/view.py` |
| 汎用ユーティリティ（インデント計算など） | `src/utils.py` |
| アプリ設定の永続化 | `src/compare/settings.py` |

### 3-3. レイヤー依存のルール

```
View → Logic → Utils
View → platforms.py (定数のみ)
Logic は View に依存しない
```

---

## Step 4: 実装

### 4-1. コーディング規約

`.github/instructions/python.instructions.md` を遵守する。

- **型ヒント必須**: すべての関数引数・戻り値に型を付ける
- **docstring 必須**: Google 形式（Args / Returns / Example）でモジュール・クラス・関数を説明する
- **行長 79 文字以下**
- **f-string 優先**
- **不要な `else` ブロックは早期リターンに変換**

### 4-2. 実装後の品質チェック（必須）

```bash
# lint チェック（エラーゼロ必須）
uv run ruff check src/ tests/

# 型チェック（エラーゼロ必須）
uv run pyright src/

# エラーがある場合はすべて修正してからテストへ進む
```

---

## Step 5: テストの作成

`.github/instructions/tests.instructions.md` を遵守する。

### 5-1. テストファイルの配置

```
tests/<module>/test_<source_module>.py
```

例: `src/validate/logic.py` → `tests/validate/test_logic.py`

### 5-2. テストの構成

```python
"""<対象モジュール>（<対象ファイルパス>）のテスト。

単体テスト:
  - <クラス名> のデータクラス特性
  - <関数名>() の <ロジック内容> を検証

結合テスト:
  - <シナリオ名>（tests/fixtures/<ディレクトリ>/ を使用）
"""

# ─── 単体テスト ───────────────────────────────────────
class Test<ClassName>:
    """<ClassName> の単体テスト。"""

    def test_<expected_behavior>_<when_condition>(self) -> None:
        """<what should happen>。"""
        ...

# ─── 結合テスト ───────────────────────────────────────
class Test<Feature>Integration:
    """<Feature> の結合テスト。

    tests/fixtures/<dir>/ のファイルを使用する。
    """
    ...
```

### 5-3. フィクスチャファイルの配置

実際の Cisco IOS コンフィグを使った結合テストには `tests/fixtures/` を使用する。

```
tests/fixtures/
  <シナリオ名>/
    current.txt    # 変更前 running-config
    input.txt      # 設定変更内容
    after.txt      # 変更後の想定 running-config
```

### 5-4. テスト実行 → 全件グリーン確認

```bash
uv run pytest --tb=short -q
# 全件 PASSED を確認する
```

---

## Step 6: ドキュメントの更新

変更内容に応じて以下を更新する。

| 変更の種類 | 更新が必要なファイル |
|---|---|
| モジュール・クラスの追加 | `docs/architecture.md` |
| 関数インターフェースの変更 | `docs/architecture.md` |
| ユーザー操作に関わる変更 | `docs/user-guide.md` |
| テストファイルの追加 | `docs/development.md`（テスト構成表） |
| フィクスチャの追加 | `docs/development.md`（フィクスチャ表） |
| リリース準備（バージョン bump） | 下記「バージョン更新」参照 |

### バージョン更新（リリース時のみ）

リリース番号を上げる際は、以下の **3 ファイルをすべて** 更新する。

| ファイル | 更新箇所 | 例 |
|---|---|---|
| `pyproject.toml` | `version = "x.y.z"` | `version = "0.2.1"` |
| `src/menu.py` | `_APP_VERSION = "vx.y.z"`（`PackageNotFoundError` 時のフォールバック値） | `_APP_VERSION = "v0.2.1"` |
| `CHANGELOG.md` | ファイル先頭に新バージョンのエントリを追加 | `## [0.2.1] - YYYY-MM-DD` |

バージョン更新は独立した `chore` コミットとしてまとめる。

```bash
git add pyproject.toml src/menu.py CHANGELOG.md
git commit -m "chore: バージョンを vX.Y.Z に更新"
```

---

## Step 7: コミット

### コミットメッセージ規約

```
<種類>: <変更の要旨（日本語・体言止め）>

- <詳細1>
- <詳細2>
- ...
```

#### 種類一覧

| 種類 | 使用場面 |
|---|---|
| `feat` | 新機能の追加 |
| `fix` | バグ修正 |
| `refactor` | リファクタリング（動作変更なし） |
| `test` | テストの追加・修正 |
| `docs` | ドキュメントの更新 |
| `chore` | ビルド・設定・バージョン管理など |
| `style` | コードフォーマットのみの変更 |

#### コミットの粒度

1 コミット = 1 種類の変更。以下の順番で **別々にコミット** する。

```
1. feat/fix/refactor  ← 実装の変更
2. test               ← テストの追加・修正
3. docs               ← ドキュメントの更新
```

#### コミット例

```bash
# 実装
git add src/validate/logic.py src/validate/view.py
git commit -m "feat: Config Validator に VLAN フィルタ機能を追加

- ValidateResult に vlan_filter フィールドを追加
- validate() に VLAN ID 範囲チェクのロジックを実装
- ValidateView のツールバーに VLAN フィルタ入力欄を追加"

# テスト
git add tests/validate/test_logic.py tests/fixtures/vlan/
git commit -m "test: VLAN フィルタ機能の単体・結合テストを追加

- TestValidateVlanFilter で正常系・異常系を検証
- tests/fixtures/vlan/ のフィクスチャを使った結合テストを追加
計 XX テストケース"

# ドキュメント
git add docs/architecture.md docs/development.md
git commit -m "docs: VLAN フィルタ機能のドキュメントを更新

- architecture.md に ValidateResult の vlan_filter フィールドを追記
- development.md のテスト構成表・フィクスチャ表を更新"
```

---

## Step 8: Pull Request の作成

### PR タイトル規約

```
[#<issue番号>] <変更の種類>: <変更内容の要旨>
```

**例:**
```
[#12] feat: Config Validator に VLAN フィルタ機能を追加
```

### PR 本文テンプレート

```markdown
## 概要

closes #<issue番号>

<Issue で要求された変更内容を 1〜3 文で説明>

---

## 変更内容

### 追加
- <追加した機能・クラス・関数>

### 変更
- <変更した既存の動作・インターフェース>

### 削除
- <削除した要素>（ある場合のみ）

---

## テスト

- [ ] `uv run pytest --tb=short -q` が全件グリーン
- [ ] `uv run ruff check src/ tests/` がエラーゼロ
- [ ] `uv run pyright src/` がエラーゼロ

### 追加したテスト

| テストクラス | 内容 |
|---|---|
| `Test<ClassName>` | <何を検証するか> |
| `Test<Feature>Integration` | <結合テストの内容> |

---

## ドキュメント

- [ ] `docs/architecture.md` を更新した
- [ ] `docs/development.md` を更新した
- [ ] `docs/user-guide.md` を更新した（UI 変更がある場合）

---

## スクリーンショット（UI 変更がある場合）

<スクリーンショットを貼り付ける>
```

### PR 作成コマンド

```bash
gh pr create \
  --base develop \
  --title "[#<issue番号>] <種類>: <要旨>" \
  --body-file /tmp/pr_body.md \
  --label "<ラベル>"
```

> **ヒント**: PR 本文が長い場合は `/tmp/pr_body.md` に書き出してから `--body-file` で渡す。

---

## 作業完了チェックリスト

PR を作成する前に以下をすべて確認する。

### ブランチ・コミット

- [ ] `develop` から作成したブランチで作業している
- [ ] ブランチ名が `<種類>/<issue番号>-<英語要約>` の形式
- [ ] コミットメッセージが規約に従っている
- [ ] 実装・テスト・ドキュメントを **別コミット** で分けた

### コード品質

- [ ] `uv run ruff check src/ tests/` がエラーゼロ
- [ ] `uv run pyright src/` がエラーゼロ
- [ ] すべての public 関数に型ヒントと docstring がある

### テスト

- [ ] `uv run pytest --tb=short -q` が全件グリーン
- [ ] 新機能・バグ修正に対応したテストが追加されている
- [ ] 結合テスト用フィクスチャが `tests/fixtures/` に配置されている

### ドキュメント

- [ ] 変更内容が `docs/architecture.md` に反映されている
- [ ] テスト構成が `docs/development.md` に反映されている

### バージョン更新（リリース時のみ）

- [ ] `pyproject.toml` の `version` を更新した
- [ ] `src/menu.py` の `_APP_VERSION` フォールバック値を更新した
- [ ] `CHANGELOG.md` に新バージョンのエントリを追加した

### PR

- [ ] PR のベースブランチが `develop` である
- [ ] PR タイトルが `[#<issue番号>] <種類>: <要旨>` の形式
- [ ] PR 本文に `closes #<issue番号>` が含まれている
- [ ] PR 本文にテスト・ドキュメントのチェックリストがある
