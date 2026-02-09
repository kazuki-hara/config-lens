# ConfigTextbox ウィジェット

ネットワーク機器の設定ファイルを表示し、特定の行をハイライトする機能を持つカスタムテキストボックスウィジェットです。

## 特徴

- **テキスト表示**: 設定ファイルの内容を読み取り専用で表示
- **行ハイライト**: 特定の行を色付きでハイライト表示
- **複数スタイル対応**: 異なるハイライトスタイルを同時に使用可能
- **カスタマイズ可能**: 独自のハイライトスタイルを追加可能

## デフォルトのハイライトスタイル

| スタイル名 | 背景色 | 用途 |
|-----------|--------|------|
| `default` | 黄色 (#FFE066) | 一般的なハイライト |
| `add` | 緑色 (#C6F6D5) | 追加された行 |
| `remove` | 赤色 (#FED7D7) | 削除された行 |
| `modify` | 薄黄色 (#FEF08A) | 変更された行 |

## 使用方法

### 基本的な使用

```python
from ui.widgets.config_textbox import ConfigTextbox

# ウィジェットの作成
textbox = ConfigTextbox(
    master=parent,
    width=800,
    height=600,
    font=("Courier", 12)
)

# テキストの設定（読み取り専用）
config_text = "interface GigabitEthernet0/0\n  ip address 192.168.1.1 255.255.255.0"
textbox.set_text(config_text, readonly=True)

# 特定の行をハイライト
textbox.highlight_lines([1, 2], style_name="default")
```

### 複数のスタイルを使用

```python
# 追加された行を緑でハイライト
textbox.highlight_lines([3, 5, 7], style_name="add")

# 削除された行を赤でハイライト
textbox.highlight_lines([10, 12], style_name="remove")

# 変更された行を黄色でハイライト
textbox.highlight_lines([15], style_name="modify")
```

### ハイライトのクリア

```python
# 特定のスタイルのハイライトをクリア
textbox.clear_highlights(style_name="add")

# すべてのハイライトをクリア
textbox.clear_highlights()
```

### カスタムスタイルの追加

```python
from ui.widgets.config_textbox import HighlightStyle

# カスタムスタイルを定義
custom_style = HighlightStyle(
    background="#FF6B6B",
    foreground="white"
)

# スタイルを追加
textbox.add_highlight_style("error", custom_style)

# カスタムスタイルを使用
textbox.highlight_lines([20, 21], style_name="error")
```

### 利用可能なスタイルの取得

```python
# 登録されているスタイル名のリストを取得
available_styles = textbox.get_available_styles()
print(available_styles)
# 出力: ['default', 'add', 'remove', 'modify', 'error']
```

## API リファレンス

### ConfigTextbox クラス

#### メソッド

##### `set_text(text: str, readonly: bool = True) -> None`

テキストボックスにテキストを設定します。

**引数:**
- `text` (str): 表示するテキスト
- `readonly` (bool): 読み取り専用にするかどうか（デフォルト: True）

##### `highlight_lines(line_numbers: list[int], style_name: str = "default") -> None`

指定された行番号のリストをハイライトします。

**引数:**
- `line_numbers` (list[int]): ハイライトする行番号のリスト（1から始まる）
- `style_name` (str): 使用するハイライトスタイル名

**例外:**
- `ValueError`: 指定されたスタイル名が存在しない場合

##### `clear_highlights(style_name: str | None = None) -> None`

ハイライトをクリアします。

**引数:**
- `style_name` (str | None): クリアするスタイル名。Noneの場合はすべてクリア

##### `add_highlight_style(name: str, style: HighlightStyle) -> None`

新しいハイライトスタイルを追加します。

**引数:**
- `name` (str): スタイル名（タグ名として使用）
- `style` (HighlightStyle): ハイライトスタイル

##### `get_available_styles() -> list[str]`

利用可能なハイライトスタイルのリストを取得します。

**戻り値:**
- list[str]: スタイル名のリスト

### HighlightStyle データクラス

#### 属性

- `background` (str): 背景色（例: "#FFE066"）
- `foreground` (str): 文字色（例: "black"）
- `font_weight` (Literal["normal", "bold"]): フォント太さ（デフォルト: "normal"）※現在未実装

## 実装例

MainWindowでの使用例は以下の通りです：

```python
# src/ui/main_window.py
from ui.widgets.config_textbox import ConfigTextbox

class MainWindow(customtkinter.CTk):
    def setup_ui(self) -> None:
        # ConfigTextboxの作成
        self.config_textbox = ConfigTextbox(
            master=self,
            width=1100,
            height=600,
            font=("Courier", 12),
        )
        self.config_textbox.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="nsew")
    
    def display_config_with_diff(self, config_text: str, added_lines: list[int], removed_lines: list[int]) -> None:
        """設定を表示し、差分をハイライトする"""
        self.config_textbox.set_text(config_text)
        self.config_textbox.highlight_lines(added_lines, style_name="add")
        self.config_textbox.highlight_lines(removed_lines, style_name="remove")
```

## 将来の拡張

以下の機能を将来追加することを検討しています：

- [ ] フォント太さ（bold）のサポート
- [ ] 行範囲のハイライト（開始行から終了行まで）
- [ ] ハイライトの優先度設定
- [ ] 行番号の表示
- [ ] 検索・ハイライト機能
- [ ] ハイライトのエクスポート／インポート

## トラブルシューティング

### Q: ハイライトが表示されない

A: 以下を確認してください：
- 行番号が1から始まっているか（0ではない）
- 指定した行番号がテキストの行数を超えていないか
- スタイル名が正しいか（`get_available_styles()`で確認）

### Q: 読み取り専用でもハイライトできますか？

A: はい、`set_text(text, readonly=True)`で設定した後でも、`highlight_lines()`でハイライトできます。内部で一時的に編集可能にして、ハイライト後に元の状態に戻します。

## ライセンス

このウィジェットはプロジェクトのライセンスに従います。
