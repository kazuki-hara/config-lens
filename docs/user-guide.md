# ユーザーガイド

ConfigLens を実際に使うためのガイドです。

---

## インストール

### リリース版（推奨）

[GitHub Releases](../../../releases/latest) から最新版をダウンロードしてください。

#### macOS

1. `ConfigLens-mac.zip` をダウンロードして展開する。
2. `ConfigLens.app` をアプリケーションフォルダへ移動する。
3. 初回起動時は`システム設定`→`プライバシーとセキュリティ`でConfigLensを許可する必要があります。

   > macOS のセキュリティ警告が表示された場合は「開く」をクリックします。
   > ターミナルで以下を実行してから起動することもできます。
   > ```bash
   > xattr -d com.apple.quarantine /Applications/ConfigLens.app
   > ```

#### Windows

1. `ConfigLens.exe` をダウンロードする。
2. ダブルクリックして起動する。

---

## 画面構成

```
┌─────────────────────────────────────────────────────────────────┐
│  ナビゲーションバー（左列）  │  コンテンツエリア（右列）           │
│                              │                                   │
│  Config Lens                 │  ツールバー                       │
│  ─────────                   │  ┌──────────────────────────────┐│
│  Menu                        │  │ Source File  │ Target File   ││
│  [Text Diff Viewer]          │  │  [Open]      │  [Open]       ││
│                              │  │ Platform: [CISCO_IOS ▼]      ││
│                              │  │ [Compare] [Manage Ignore...]  ││
│                              │  └──────────────────────────────┘│
│                              │                                   │
│                              │  差分表示エリア                   │
│                              │  Source          │  Target       │
│                              │  ────────────────│───────────── │
│                              │  （比較結果）     │（比較結果）  │
└─────────────────────────────────────────────────────────────────┘
```

| 領域 | 説明 |
|---|---|
| ナビゲーションバー | 機能を切り替えるサイドメニュー |
| ツールバー | ファイル選択・プラットフォーム指定・比較実行・Ignore 設定 |
| 差分表示エリア | Source と Target を2列で並べて差分をハイライト表示 |

---

## 基本的な使い方

### 1. ファイルを選択する

ツールバーの「**Open**」ボタンを2つクリックし、比較する2つのコンフィグファイルを選択します。

- **Source File（左列）** — 比較元（通常は現在の running-config）
- **Target File（右列）** — 比較先（通常は期待する状態や別機器の config）

### 2. プラットフォームを選択する

`Platform` ドロップダウンから機器の種類を選択します。

| プラットフォーム | 状態 |
|---|---|
| CISCO_IOS | 対応済み |
| CISCO_NXOS | 未対応（将来実装予定） |
| CISCO_XR | 未対応（将来実装予定） |
| ARISTA_EOS | 未対応（将来実装予定） |
| JUNIPER_JUNOS | 未対応（将来実装予定） |
| FORTINET_FORTIOS | 未対応（将来実装予定） |

> 未対応プラットフォームを選択した場合、階層構造の解析が正しく機能しない場合があります。

### 3. 比較を実行する

「**Compare**」ボタンをクリックします。

差分が計算され、差分表示エリアに結果が表示されます。

---

## 差分表示の見方

### 色の意味

| 背景色 | 意味 | 例 |
|---|---|---|
| 赤（暗め） | Source にのみ存在する行（削除） | Source 側にある設定が Target にない |
| 緑（暗め） | Target にのみ存在する行（追加） | Target 側にある設定が Source にない |
| 黄（暗め） | 両方に存在するが記載順が異なる行（順番違い） | 構造的には同じだが並び順が違う |
| 通常（ハイライトなし） | 完全一致 | 対応行が完全に同じ |

### インライン差分

`replace` タイプの行（内容が異なる行）では、行内の**文字単位**での差分もハイライトされます。

### 空行

対応する行が存在しない場合、空行（パディング）が挿入され、左右の高さが揃えられます。

### 行番号

差分表示の各行の先頭に行番号が表示されます（例: `   1  interface GigabitEthernet0/0`）。

---

## クリックジャンプ

差分行（reorder タイプ）をクリックすると、対応する行へジャンプして強調表示されます。
これにより、記載順が異なる行の対応関係を素早く把握できます。

---

## Ignore パターン

コメント行やバナーなど、比較対象から除外したい行を正規表現で登録できます。

### パターンの管理

1. ツールバーの「**Manage Ignore Patterns**」をクリックする。
2. ダイアログが開いたら、入力欄に正規表現を入力して「追加」ボタンを押す。
3. 不要なパターンは一覧から選択して「削除」ボタンで削除する。

### Ignore の有効・無効切り替え

ツールバーの「**Enable Ignore**」スイッチで Ignore を一時的に無効にできます。  
スイッチを切り替えると自動的に再比較が実行されます。

### パターンの例

| パターン | 説明 |
|---|---|
| `^!` | `!` で始まるコメント行 |
| `^Building configuration` | `Building configuration` 行 |
| `^Current configuration` | `Current configuration` 行 |
| `ntp clock-period` | NTP クロック行 |

### 設定の保存場所

登録したパターンは OS 標準のユーザーデータディレクトリに自動保存されます。

| OS | 保存パス |
|---|---|
| macOS | `~/Library/Application Support/ConfigLens/settings.json` |
| Windows | `%APPDATA%\ConfigLens\settings.json` |
| Linux | `~/.local/share/ConfigLens/settings.json` |

---

## よくある質問（FAQ）

### Q. macOS で「開発元を確認できません」と表示される

A. 右クリック → 「開く」を選択してください。または以下のコマンドを実行してください。

```bash
xattr -d com.apple.quarantine /Applications/ConfigLens.app
```

### Q. 比較がうまくいかない / 差分が予想と違う

A. 以下を確認してください。

- Platform が正しく選択されているか（現在は `CISCO_IOS` のみ対応）
- Ignore パターンが意図しない行を除外していないか（「Enable Ignore」をオフにして再比較）

### Q. 設定（Ignore パターン）をリセットしたい

A. 設定ファイルを削除してください。

```
# macOS
rm ~/Library/Application\ Support/ConfigLens/settings.json

# Windows（PowerShell）
Remove-Item "$env:APPDATA\ConfigLens\settings.json"
```
