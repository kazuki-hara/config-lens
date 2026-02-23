# アーキテクチャ

ソースコードの構成・クラス設計・各モジュールの責務を説明します。

---

## ディレクトリ構成

```
config-lens/
├── main.py                    # エントリーポイント
├── pyproject.toml             # プロジェクト設定・依存関係
├── taskfile.yml               # タスクランナー定義
├── ConfigLens.spec            # PyInstaller ビルド設定
│
├── src/                       # アプリケーション本体
│   ├── __init__.py
│   ├── app.py                 # メインウィンドウ（DiffViewerApp）
│   ├── menu.py                # ナビゲーションバー（NavigationFrame）
│   ├── utils.py               # 汎用ユーティリティ関数
│   └── compare/               # 比較機能モジュール群
│       ├── __init__.py
│       ├── logic.py           # 差分計算ロジック
│       ├── view.py            # 比較ビュー UI
│       ├── ignore.py          # Ignore パターン管理
│       └── settings.py        # アプリ設定の永続化
│
├── tests/                     # テストコード
│   ├── __init__.py
│   ├── test_utils.py
│   ├── compare/
│   │   ├── __init__.py
│   │   ├── test_logic.py
│   │   └── test_ignore.py
│   └── fixtures/              # テスト用コンフィグファイル
│       ├── source.txt
│       ├── target.txt
│       ├── demo_source.txt
│       ├── demo_target.txt
│       └── config/
│
├── assets/                    # アイコン等の静的リソース
├── docs/                      # ドキュメント（本ディレクトリ）
└── scripts/                   # ビルド補助スクリプト
    └── generate_icon.py
```

---

## レイヤー構成

```
┌─────────────────────────────────────────────┐
│  エントリーポイント                           │
│  main.py → src/app.py::main()               │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│  プレゼンテーション層（UI）                   │
│  src/app.py       DiffViewerApp             │
│  src/menu.py      NavigationFrame           │
│  src/compare/view.py  CompareView           │
│  src/compare/ignore.py IgnorePatternDialog  │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│  ビジネスロジック層                           │
│  src/compare/logic.py                       │
│    HierarchicalDiffAnalyzer                 │
│    TextAlignedDiffComparator                │
│  src/compare/ignore.py                      │
│    IgnorePatternManager                     │
│  src/utils.py   汎用ユーティリティ           │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│  データ永続化層                              │
│  src/compare/settings.py  AppSettings       │
│  → settings.json（OS ユーザーデータ領域）    │
└─────────────────────────────────────────────┘
```

---

## 各モジュールの説明

### `main.py`

アプリケーションのエントリーポイントです。`src/app.py` の `main()` を呼び出すだけのシンプルなラッパーです。

```python
from src.app import main

if __name__ == "__main__":
    main()
```

---

### `src/app.py` — `DiffViewerApp`

`customtkinter.CTk` を継承したメインウィンドウクラスです。

| 要素 | 説明 |
|---|---|
| `_settings: AppSettings` | アプリ全体で共有する設定オブジェクト |
| `_nav_frame: NavigationFrame` | 左列のナビゲーションバー |
| `_compare_view: CompareView` | 右列の比較ビュー |
| `_show_compare_view()` | 比較ビューを前面に表示（将来の多ビュー切替に備えた設計） |

ウィンドウの初期サイズは `1400×800` px で、外観は `dark` モード、カラーテーマは `dark-blue` です。

**ウィジェット配置（grid）**

```
column 0 (weight=0, 固定幅)   column 1 (weight=1, 可変幅)
┌────────────────────┬─────────────────────────────────┐
│  NavigationFrame   │  CompareView                    │
│   (row=0, col=0)   │   (row=0, col=1)                │
└────────────────────┴─────────────────────────────────┘
```

---

### `src/menu.py` — `NavigationFrame`

アプリ左側に固定表示される縦型ナビゲーションバーです。

| 要素 | 説明 |
|---|---|
| `_on_compare: Callable[[], None]` | 比較ボタン押下時のコールバック |
| `_create_widgets()` | ウィジェットを構築する内部メソッド |

現在は「Text Diff Viewer」ボタン1つのみです。新しい機能を追加する場合はここにボタンを追加します。

---

### `src/utils.py` — ユーティリティ関数

階層構造の解析に必要な汎用関数を提供します。

#### `calcurate_hierarcihical_path(config: list[str]) -> list[list[str]]`

コンフィグの各行について、インデント量から階層パスを計算します。

```python
# 入力
config = [
    "interface GigabitEthernet0/1",
    " ip address 192.168.1.1 255.255.255.0",
    "interface GigabitEthernet0/2",
]

# 出力
[
    ["interface GigabitEthernet0/1"],
    ["interface GigabitEthernet0/1", "ip address 192.168.1.1 255.255.255.0"],
    ["interface GigabitEthernet0/2"],
]
```

#### `remove_plus_minus_from_diff_line(diff_line: str) -> str`

`unified_diff` が出力する `+` / `-` プレフィックスを除去します。インデントは保持されます。

---

### `src/compare/` — 比較機能モジュール群

比較機能に関するコード群です。UI・ロジック・Ignore 管理・設定永続化の4つのファイルに分離されています。

---

#### `src/compare/logic.py` — 差分計算ロジック

##### `HierarchicalDiffAnalyzer`

`hier_config` ライブラリを使い、ネットワーク機器コンフィグの**構造的差分**を解析するクラスです。

| メソッド | 説明 |
|---|---|
| `analyze_structural_diff(source, target)` | 追加行・削除行・変更なし行の階層パスリストを返す |

戻り値の辞書構造：

```python
{
    "additional_parts": [[...], ...],   # target にのみ存在
    "deletional_parts": [[...], ...],   # source にのみ存在
    "non_changed_parts": [[...], ...],  # 両方に存在
}
```

##### `TextAlignedDiffComparator`

2つのテキストを行単位で比較し、WinMerge のように**高さを揃えた**表示用データを生成するクラスです。すべてのメソッドはスタティックメソッドです。

| メソッド | 説明 |
|---|---|
| `compare_and_align(source, target)` | 高さを揃えた `(source行リスト, target行リスト)` を返す |
| `compare_and_align_with_diff_info(source, target)` | 上記に加え差分タイプリストを返す |
| `compare_and_align_with_structural_diff_info(source, target, platform)` | 構造的差分に基づくハイライト情報付きで返す |

**差分タイプ一覧**

| タイプ | 意味 |
|---|---|
| `equal` | 両方に存在し順番も一致 |
| `delete` | source にのみ存在（削除） |
| `insert` | target にのみ存在（追加） |
| `replace` | 内容が異なる行（テキスト差分） |
| `reorder` | 両方に存在するが記載順が異なる（構造的差分） |
| `empty` | パディング用の空行 |

**アルゴリズム概要**

1. 各行の階層パスを `calcurate_hierarcihical_path()` で計算し、`" > "` で結合したキーを生成する。  
   例: `"interface GigabitEthernet0/0 > ip address 10.0.0.1 255.255.255.0"`
2. `difflib.SequenceMatcher` でキーを比較し、`equal / replace / delete / insert` の opcodes を取得する。
3. opcodes に従って空行（パディング）を挿入し、左右の行数を揃える。
4. 構造的差分モードでは `hier_config` の解析結果と突き合わせて `reorder` を判定する。

---

#### `src/compare/view.py` — 比較ビュー UI

`CompareView` クラスが比較機能の UI 全体を管理します。

| 内部状態 | 説明 |
|---|---|
| `source_file_path / target_file_path` | 選択中のファイルパス |
| `_src_key_to_row / _tgt_key_to_row` | 階層パスキー → 行番号のマップ（クリックジャンプ用） |
| `_src_types / _tgt_types` | 比較済みの差分タイプリスト |
| `_ignore_manager` | Ignore パターン管理クラス |
| `_ignore_enabled_var` | Ignore 有効/無効の BooleanVar |
| `_has_compared` | 比較済みフラグ（Ignore トグル時の自動再比較に使用） |

**主要なメソッド**

| メソッド | 説明 |
|---|---|
| `_create_widgets()` | ツールバー・ヘッダー・テキストエリアを構築 |
| `_open_source_file() / _open_target_file()` | ファイル選択ダイアログを開く |
| `_compare_files()` | 比較を実行して結果を描画する |
| `_apply_ignore(text)` | Ignore パターンにマッチする行を空行に置換する |
| `_render_diff(...)` | 差分結果をテキストウィジェットに描画する |
| `_on_ignore_toggle(...)` | Ignore スイッチ変更時に自動再比較を行う |

**インライン差分ハイライト**

`_INLINE_DIFF_THRESHOLD = 0.4` 以上の類似度を持つ `replace` 行に対して、`difflib.SequenceMatcher` で文字単位の差分を計算しハイライトします。

---

#### `src/compare/ignore.py` — Ignore パターン管理

##### `IgnorePatternManager`

Ignore 対象の正規表現パターンを管理するクラスです。

| メソッド | 説明 |
|---|---|
| `get_patterns()` | 登録済みパターンのリストを返す（コピー） |
| `add_pattern(pattern)` | パターンを追加・保存する。重複・空・無効正規表現は例外を送出 |
| `remove_pattern(pattern)` | パターンを削除・保存する |
| `matches(line)` | 行テキストがいずれかのパターンにマッチするか判定する |

設定の保存先は `AppSettings` を通じて `settings.json` の `compare.ignore.patterns` セクションです。

##### `IgnorePatternDialog`

`ctk.CTkToplevel` を継承したモーダルダイアログで、パターンの一覧表示・追加・削除 UI を提供します。

---

#### `src/compare/settings.py` — アプリ設定の永続化

##### `AppSettings`

アプリ全体の設定を JSON ファイルで一元管理するクラスです。

| メソッド | 説明 |
|---|---|
| `get(*keys, default=None)` | ネストしたキーパスで設定値を取得する |
| `update(section_path, value)` | 指定セクションパスの値を更新して保存する |
| `settings_path` | 設定ファイルの絶対パス（プロパティ） |

**設定ファイルの構造**

```json
{
  "compare": {
    "ignore": {
      "patterns": [
        "^!",
        "^Building configuration"
      ]
    }
  }
}
```

新しい機能を追加する場合は、対応するセクションパスを追加するだけで既存のデータと共存できます。

**保存先**

| OS | パス |
|---|---|
| macOS | `~/Library/Application Support/ConfigLens/settings.json` |
| Windows | `%APPDATA%\ConfigLens\settings.json` |
| Linux | `~/.local/share/ConfigLens/settings.json` |

---

## 依存ライブラリ

| ライブラリ | 用途 |
|---|---|
| `customtkinter` | モダンな Tkinter ウィジェット（ダークテーマ対応 GUI） |
| `hier-config` | ネットワーク機器コンフィグの階層構造解析・差分計算 |
| `platformdirs` | OS 標準のユーザーデータディレクトリ取得 |
| `PyInstaller` | スタンドアロン実行ファイルのビルド |

---

## クラス関係図

```
DiffViewerApp (CTk)
├── NavigationFrame (CTkFrame)
│   └── [CTkButton on_compare callback]
└── CompareView (CTkFrame)
    ├── IgnorePatternManager
    │   └── AppSettings  ←→  settings.json
    ├── IgnorePatternDialog (CTkToplevel)  [モーダル]
    └── TextAlignedDiffComparator  [static methods]
        └── HierarchicalDiffAnalyzer  [static methods]
            └── hier_config (HConfig, get_hconfig)
```
