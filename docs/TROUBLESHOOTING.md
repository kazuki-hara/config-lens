# トラブルシューティング

Config Lensのビルドと実行に関するよくある問題と解決方法をまとめています。

## 目次

- [ビルドエラー](#ビルドエラー)
- [実行時エラー](#実行時エラー)
- [macOS固有の問題](#macos固有の問題)
- [デバッグ方法](#デバッグ方法)

## ビルドエラー

### ModuleNotFoundError: No module named 'ui'

**症状**: ビルドは成功するが、実行時に`No module named 'ui'`というエラーが発生する。

**原因**: PyInstallerがローカルモジュールを検出できていない。

**解決方法**:

1. `__init__.py`ファイルの確認

````bash
# 各ディレクトリに__init__.pyがあることを確認
ls -la src/ui/__init__.py
ls -la src/services/__init__.py
````

2. ビルドログで検出されたモジュールを確認

````bash
pyinstaller --noconfirm config-lens.spec 2>&1 | grep "検出"
````

3. `config-lens.spec`でモジュールが正しく含まれているか確認

````python
# spec内で検出されたモジュールが表示されます
print("検出されたローカルモジュール:")
for module in sorted(local_modules):
    print(f"  - {module}")
````

4. 手動でhiddenimportsに追加（最終手段）

````python
BASE_HIDDEN_IMPORTS = [
    'customtkinter',
    'hier_config',
    'tkinter',
    'ui',                    # 追加
    'ui.main_window',        # 追加
    'ui.widgets',            # 追加
    'services',              # 追加
]
````

### CustomTkinterのリソースが見つからない

**症状**: `.dylib`ファイルが見つからないというエラー。

**原因**: CustomTkinterのネイティブライブラリが含まれていない。

**解決方法**:

````python
# config-lens.specで以下が設定されているか確認
customtkinter_datas = collect_data_files('customtkinter')
customtkinter_binaries = collect_dynamic_libs('customtkinter')

a = Analysis(
    # ...
    binaries=customtkinter_binaries,
    datas=customtkinter_datas,
    # ...
)
````

### Python 3.14の互換性警告

**症状**: `Pydantic V1 functionality isn't compatible with Python 3.14`という警告。

**原因**: 一部のライブラリがPython 3.14に未対応。

**解決方法**: Python 3.13を使用

````bash
# Python 3.13をインストール
uv python install 3.13

# .python-versionを作成
echo "3.13" > .python-version

# 仮想環境を再作成
rm -rf .venv
uv venv
uv sync

# 再ビルド
task clean
````

## 実行時エラー

### '_tkinter.tkapp' object has no attribute 'run'

**症状**: アプリを起動すると`'_tkinter.tkapp' object has no attribute 'run'`エラー。

**原因**: CustomTkinterの起動メソッドが間違っている。

**解決方法**: `mainloop()`メソッドを使用

````python
# ❌ 間違い
app = MainWindow()
app.run()

# ✅ 正しい
app = MainWindow()
app.mainloop()
````

src/main.pyの修正例：

````python
def main() -> None:
    """メインエントリーポイント"""
    from ui.main_window import MainWindow
    
    app = MainWindow()
    app.mainloop()  # run()ではなくmainloop()
````

### アプリが起動直後に終了する

**症状**: アプリを起動してもすぐに終了し、何も表示されない。

**診断方法**: デバッグビルドで実行

````bash
# デバッグビルド
task dev-build

# ターミナルから直接実行してエラーを確認
./dist/ConfigLens.app/Contents/MacOS/ConfigLens
````

**よくある原因と解決方法**:

1. **パスの問題**

````python
# src/main.pyでパスを適切に設定
def setup_application_path() -> Path:
    if getattr(sys, 'frozen', False):
        application_path = Path(sys._MEIPASS)
        sys.path.insert(0, str(application_path))
    else:
        application_path = Path(__file__).parent
        sys.path.insert(0, str(application_path))
    return application_path
````

2. **例外が握りつぶされている**

````python
# エラーをログファイルに出力
try:
    app.mainloop()
except Exception as e:
    error_log_path = Path.home() / "config-lens-error.log"
    with open(error_log_path, "w", encoding="utf-8") as f:
        f.write(traceback.format_exc())
    print(f"Error log: {error_log_path}")
````

3. **エラーログの確認**

````bash
# ホームディレクトリのエラーログを確認
cat ~/config-lens-error.log
````

### 移動後にアプリが起動しない

**症状**: ビルドしたアプリを別のディレクトリに移動すると起動しなくなる。

**原因**: コード署名の問題やGatekeeperの隔離属性。

**解決方法**:

1. アドホック署名

````bash
# アプリに署名
codesign --force --deep --sign - dist/ConfigLens.app

# 検証
codesign --verify --deep --verbose=2 dist/ConfigLens.app
````

2. 隔離属性の削除

````bash
# Gatekeeperの隔離属性を削除
xattr -cr dist/ConfigLens.app
````

3. 署名付きでビルド（推奨）

````bash
# Taskを使用
task build-signed
````

## macOS固有の問題

### "ConfigLens.app は破損しているため開けません"

**原因**: Gatekeeperがアプリを拒否している。

**解決方法**:

````bash
# 隔離属性を削除
xattr -cr dist/ConfigLens.app

# アドホック署名
codesign --force --deep --sign - dist/ConfigLens.app
````

または、システム環境設定で一時的に許可：

1. システム設定 > プライバシーとセキュリティ
2. "このまま開く"をクリック

### "開発元を確認できません"

**原因**: Apple Developer IDで署名されていない。

**解決方法**:

**オプション1**: アドホック署名（開発用）

````bash
task build-signed
````

**オプション2**: Developer ID署名（配布用）

````python
# config-lens.specで設定
exe = EXE(
    # ...
    codesign_identity='Developer ID Application: Your Name (TEAM_ID)',
    # ...
)
````

````bash
# 署名情報を確認
security find-identity -v -p codesigning
````

### App Transport Security (ATS)エラー

**症状**: ネットワーク通信が失敗する。

**解決方法**: Info.plistに設定を追加

````python
# config-lens.specのinfo_plistに追加
info_plist={
    # ...
    'NSAppTransportSecurity': {
        'NSAllowsArbitraryLoads': True
    },
}
````

## デバッグ方法

### 基本的なデバッグフロー

1. **デバッグビルドを作成**

````bash
task dev-build
````

2. **ターミナルから直接実行**

````bash
./dist/ConfigLens.app/Contents/MacOS/ConfigLens
````

3. **エラーメッセージとログを確認**

````bash
# エラーログ
cat ~/config-lens-error.log

# Consoleアプリでシステムログを確認
open -a Console
````

### 詳細なログ出力

src/main.pyにログ機能を追加：

````python
import logging

# ログ設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path.home() / 'config-lens-debug.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    logger.info("アプリケーション起動開始")
    try:
        # ...
        logger.info("GUI初期化完了")
    except Exception as e:
        logger.exception(f"エラー: {e}")
````

### PyInstallerのデバッグモード

````python
# config-lens.specで有効化
exe = EXE(
    # ...
    debug=True,
    console=True,
    # ...
)
````

### モジュールインポートのテスト

開発環境でインポートをテスト：

````python
# debug_imports.py
import sys
from pathlib import Path

src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

print("=== モジュールインポートテスト ===")
try:
    import ui
    print(f"✅ import ui: 成功")
    from ui.main_window import MainWindow
    print(f"✅ from ui.main_window import MainWindow: 成功")
except ImportError as e:
    print(f"❌ エラー: {e}")
````

実行：

````bash
python debug_imports.py
````

### ビルド内容の確認

````bash
# アプリケーションバンドルの内容を確認
ls -la dist/ConfigLens.app/Contents/MacOS/
ls -la dist/ConfigLens.app/Contents/Frameworks/

# 含まれているPythonモジュールを確認
cd dist/ConfigLens.app/Contents/Frameworks/
python3 -c "import sys; sys.path.insert(0, '.'); import pkgutil; print([m.name for m in pkgutil.iter_modules()])"
````

## よくある問題のチェックリスト

ビルドや実行で問題が発生した場合、以下を順番に確認してください：

- [ ] すべてのディレクトリに`__init__.py`が存在する
- [ ] Python 3.13を使用している（3.14は非推奨）
- [ ] `uv sync`で依存関係をインストール済み
- [ ] `config-lens.spec`が最新版である
- [ ] デバッグビルドでエラーメッセージを確認した
- [ ] エラーログファイル（`~/config-lens-error.log`）を確認した
- [ ] アプリに署名している（移動する場合）
- [ ] 隔離属性を削除している（他のMacで実行する場合）

## サポート情報

問題が解決しない場合は、以下の情報を含めてissueを作成してください：

1. エラーメッセージ全文
2. ビルドログ（`pyinstaller --noconfirm config-lens.spec 2>&1 | tee build.log`）
3. エラーログファイル（`~/config-lens-error.log`）
4. 環境情報

````bash
# 環境情報の取得
python --version
uv --version
sw_vers  # macOSバージョン
````
