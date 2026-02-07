# ビルド手順

Config LensをmacOSアプリケーションとしてビルドするための詳細な手順を説明します。

## 目次

- [前提条件](#前提条件)
- [基本的なビルド](#基本的なビルド)
- [ビルドオプション](#ビルドオプション)
- [ビルド設定](#ビルド設定)
- [配布用パッケージの作成](#配布用パッケージの作成)
- [よくある質問](#よくある質問)

## 前提条件

### 必須ツール

- Python 3.13以上（Python 3.14推奨）
- uv（パッケージマネージャー）
- PyInstaller 6.x以上
- Task（タスクランナー）

### 環境のセットアップ

````bash
# 依存関係のインストール
task install

# または直接uvを使用
uv sync
````

## 基本的なビルド

### 方法1: Taskを使用（推奨）

````bash
# リリースビルド
task build

# クリーンビルド
task clean

# ビルドして実行
task run
````

### 方法2: PyInstallerコマンドを直接使用

````bash
# .specファイルを使用したビルド
pyinstaller --noconfirm config-lens.spec

# コマンドラインオプションを使用
pyinstaller --noconfirm \
  --onedir \
  --windowed \
  --name="ConfigLens" \
  --add-data ".venv/lib/python3.14/site-packages/customtkinter:customtkinter/" \
  --hidden-import="customtkinter" \
  --hidden-import="hier_config" \
  src/main.py
````

## ビルドオプション

### PyInstallerの主要オプション

| オプション | 説明 | 推奨値 |
|----------|------|--------|
| `--noconfirm` | 既存ファイルの上書き確認をスキップ | 常に使用 |
| `--onedir` | 単一ディレクトリ形式でビルド | 推奨 |
| `--windowed` | コンソールウィンドウを非表示 | リリース時 |
| `--add-data` | データファイルを含める | customtkinter用 |
| `--hidden-import` | 動的インポートされるモジュールを明示 | 必要に応じて |
| `--icon` | アプリケーションアイコン | オプション |

### デバッグビルド

エラー調査のために、コンソール出力を有効にしてビルドします：

````bash
# Taskを使用
task dev-build

# 直接実行
./dist/ConfigLens.app/Contents/MacOS/ConfigLens
````

デバッグビルドでは以下の設定が有効になります：

- `console=True`: コンソールウィンドウを表示
- `debug=True`: デバッグ情報を出力

## ビルド設定

### config-lens.spec の構造

プロジェクトでは`config-lens.spec`ファイルでビルド設定を管理しています。

#### 主要な設定項目

**1. ローカルモジュールの自動収集**

````python
# srcディレクトリ内のすべてのPythonモジュールを自動検出
local_modules = collect_local_modules(SRC_PATH, EXCLUDE_PATTERNS)
````

新しいファイルやディレクトリを追加しても、自動的に検出されてビルドに含まれます。

**2. 除外パターン**

````python
EXCLUDE_PATTERNS = [
    r'test_.*',         # テストファイル
    r'.*_test\.py',     # テストファイル
    r'__pycache__',     # キャッシュ
    r'\..*',            # 隠しファイル
    r'.*\.pyc',         # コンパイル済みファイル
]
````

**3. CustomTkinterのリソース**

````python
# CustomTkinterのデータとバイナリを自動収集
customtkinter_datas = collect_data_files('customtkinter')
customtkinter_binaries = collect_dynamic_libs('customtkinter')
````

**4. リリース設定**

````python
exe = EXE(
    # ...
    debug=False,      # リリース時はFalse
    console=False,    # リリース時はFalse
    # ...
)
````

### specファイルのカスタマイズ

#### アプリケーション名の変更

````python
APP_NAME = 'ConfigLens'
````

#### バンドル識別子の変更

````python
BUNDLE_IDENTIFIER = 'com.kazuki.configlens'
````

#### アイコンの追加

````python
app = BUNDLE(
    # ...
    icon='path/to/icon.icns',  # .icns形式のアイコンファイル
    # ...
)
````

## 配布用パッケージの作成

### コード署名

macOSで配布するには、アドホック署名が必要です：

````bash
# Taskを使用
task build-signed

# または手動で署名
task build
codesign --force --deep --sign - dist/ConfigLens.app
````

### 署名の検証

````bash
# Taskを使用
task verify

# または手動で検証
codesign --verify --deep --verbose=2 dist/ConfigLens.app
spctl --assess --verbose=4 dist/ConfigLens.app
````

### DMGファイルの作成

配布用のDMGイメージを作成：

````bash
# Taskを使用
task create-dmg

# または手動で作成
mkdir -p dist/dmg
cp -R dist/ConfigLens.app dist/dmg/
hdiutil create -volname "ConfigLens" -srcfolder dist/dmg -ov -format UDZO dist/ConfigLens.dmg
rm -rf dist/dmg
````

### Gatekeeperの隔離属性を削除

アプリを他のMacで実行する場合：

````bash
# Taskを使用
task remove-quarantine

# または手動で削除
xattr -cr dist/ConfigLens.app
````

## ビルド出力

ビルドが成功すると、以下のディレクトリにファイルが生成されます：

````
dist/
├── ConfigLens.app/          # macOSアプリケーションバンドル
│   └── Contents/
│       ├── MacOS/
│       │   └── ConfigLens   # 実行ファイル
│       ├── Frameworks/      # Python & ライブラリ
│       └── Info.plist       # アプリケーション情報
└── ConfigLens/              # 中間ファイル（.appの展開元）

build/                       # ビルドキャッシュ（削除可能）
````

## パフォーマンス最適化

### UPX圧縮

実行ファイルのサイズを圧縮（デフォルトで有効）：

````python
exe = EXE(
    # ...
    upx=True,
    # ...
)
````

### 不要なモジュールの除外

````python
a = Analysis(
    # ...
    excludes=['matplotlib', 'numpy', 'pandas'],  # 使用しないモジュールを除外
    # ...
)
````

## よくある質問

### Q: ビルドに時間がかかりすぎる

A: 以下を試してください：

````bash
# キャッシュをクリア
rm -rf build dist

# 依存関係を最小限に
# pyproject.tomlで不要なパッケージを削除
````

### Q: ビルドサイズが大きい

A: 以下の最適化を検討：

1. 不要なライブラリを除外（`excludes`オプション）
2. UPX圧縮を有効化（デフォルトで有効）
3. `--strip`オプションでデバッグ情報を削除

### Q: 新しいモジュールが含まれない

A: `config-lens.spec`のローカルモジュール自動収集機能により、通常は自動的に含まれます。含まれない場合は：

````bash
# ビルドログでモジュール検出を確認
pyinstaller --noconfirm config-lens.spec 2>&1 | grep "検出"

# 手動で追加が必要な場合
# config-lens.specのBASE_HIDDEN_IMPORTSに追加
````

### Q: Python 3.14で互換性の警告が出る

A: Python 3.13の使用を推奨します：

````bash
# Python 3.13をインストール
uv python install 3.13

# .python-versionを作成
echo "3.13" > .python-version

# 仮想環境を再作成
rm -rf .venv
uv venv
uv sync
````

## トラブルシューティング

ビルド時の問題については、[トラブルシューティングガイド](TROUBLESHOOTING.md)を参照してください。
