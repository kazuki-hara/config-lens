# コントリビューションガイド

プロジェクトへの貢献方法・ブランチ戦略・コミット規約を説明します。

---

## ブランチ戦略

| ブランチ | 役割 |
|---|---|
| `main` | 本番リリース済みのコード。CI が通ったコードのみマージされる |
| `develop` | 次のリリースに向けた開発コードの統合先 |
| `feature/xxx` | 新機能の開発用ブランチ |
| `hotfix/xxx` | 本番環境の緊急修正用ブランチ |
| `release/xxx` | リリース準備用ブランチ |

### ブランチ命名例

```
feature/add-arista-support
feature/improve-inline-diff
hotfix/fix-crash-on-empty-file
release/v1.1.0
```

### 開発フロー

```
main ←──────────────────────────────── PR ─── release/xxx
  │                                              ↑
  └─ develop ←── PR ─── feature/xxx ────────────┘
                 ↑
                作業ブランチ（feature/xxx）
```

```bash
# 新機能開発の場合
git checkout develop
git pull origin develop
git checkout -b feature/xxx

# 開発・コミット後
git push origin feature/xxx
# → develop へ PR を作成する

# 緊急修正の場合
git checkout main
git checkout -b hotfix/xxx

# 修正・コミット後
git push origin hotfix/xxx
# → main へ PR を作成する
```

---

## コミットメッセージ規約

[Conventional Commits](https://www.conventionalcommits.org/ja/v1.0.0/) に準拠します。

### フォーマット

```
<type>: <summary>
```

### タイプ一覧

| タイプ | 意味 | 例 |
|---|---|---|
| `feat` | 新機能の追加 | `feat: Arista EOS の比較に対応` |
| `fix` | バグ修正 | `fix: 空ファイル選択時のクラッシュを修正` |
| `docs` | ドキュメントの変更 | `docs: ユーザーガイドに FAQ を追加` |
| `style` | コードスタイルの変更（フォーマット等） | `style: ruff のフォーマットを適用` |
| `refactor` | リファクタリング（機能変化なし） | `refactor: CompareView を小クラスに分割` |
| `test` | テストの追加・修正 | `test: test_ignore に境界値テストを追加` |
| `chore` | ビルドやツール関連の変更 | `chore: PyInstaller を 6.19 にアップデート` |

### 良いコミットメッセージの例

```
feat: Ignore パターンの CSV インポート機能を追加

- IgnorePatternManager に import_from_csv() メソッドを追加
- IgnorePatternDialog にインポートボタンを追加
- tests/compare/test_ignore.py に対応テストを追加
```

---

## プルリクエスト（PR）の手順

1. **前準備**  
   最新の `develop` から `feature/xxx` ブランチを作成する（上記参照）。

2. **実装**  
   機能を実装し、テストと docstring を追加する。

3. **ローカルチェック**  
   PR 作成前に以下をすべてパスさせる。

   ```bash
   task test   # すべてのテストが GREEN
   task lint   # ruff・pyright がエラーなし
   ```

4. **PR 作成**  
   `develop` ブランチへの PR を作成する。PR の説明には以下を含める。

   - 変更内容の概要
   - テスト方法
   - スクリーンショット（UI の変更がある場合）

5. **レビュー対応**  
   レビューコメントに対応し、必要な修正を行う。

6. **マージ**  
   レビュー承認後、スカッシュマージまたは通常マージでマージする。

---

## リリース手順

```bash
# 1. pyproject.toml のバージョンを更新
# version = "0.1.0" → "0.2.0"

# 2. CHANGELOG.md を更新する

# 3. release/vX.Y.Z ブランチを作成・PR → develop → main
git checkout -b release/v0.2.0
# 変更をコミット...
git push origin release/v0.2.0

# 4. release/* → develop → main の順にマージ
# 5. main へのマージが GitHub Actions を起動し、自動でリリースが作成される
```

---

## コードレビューのチェックリスト

PR レビュー時に以下を確認してください。

- [ ] `task test` がすべてパスしている
- [ ] `task lint` がエラーなし
- [ ] 型ヒントが適切に付与されている
- [ ] docstring（Google 形式）が記述されている
- [ ] 新しいパブリック API にはテストが追加されている
- [ ] UI を変更した場合はスクリーンショットが添付されている
- [ ] コミットメッセージの規約に従っている
