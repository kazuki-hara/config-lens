# -*- mode: python ; coding: utf-8 -*-
"""
PyInstallerビルド設定ファイル

移動可能なmacOSアプリケーションバンドルを生成します。
"""
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT, BUNDLE
from pathlib import Path
import sys
import re

block_cipher = None

# プロジェクト設定
APP_NAME = 'ConfigLens'
BUNDLE_IDENTIFIER = 'com.kazuki.configlens'
SRC_PATH = Path('src').absolute()

print(f"\n{'=' * 60}")
print(f"プロジェクトパス: {SRC_PATH}")
print(f"{'=' * 60}\n")

# PYTHONPATHにsrcを追加
sys.path.insert(0, str(SRC_PATH.parent))
sys.path.insert(0, str(SRC_PATH))

# customtkinterのリソース収集
customtkinter_datas = collect_data_files('customtkinter')
customtkinter_binaries = collect_dynamic_libs('customtkinter')


def collect_local_modules(
    root_path: Path,
    exclude_patterns: list[str] | None = None
) -> list[str]:
    """
    指定されたディレクトリ配下のすべてのPythonモジュールを自動収集
    
    Args:
        root_path: スキャンするルートディレクトリ
        exclude_patterns: 除外する正規表現パターンのリスト
    
    Returns:
        検出されたモジュール名のリスト
    """
    modules = []
    exclude_patterns = exclude_patterns or []
    compiled_patterns = [re.compile(pattern) for pattern in exclude_patterns]
    
    def should_exclude(path: Path) -> bool:
        """パスが除外パターンにマッチするかチェック"""
        path_str = str(path.relative_to(root_path))
        return any(pattern.search(path_str) for pattern in compiled_patterns)
    
    print("パッケージを検出中...")
    
    # パッケージの検出（__init__.pyがあるディレクトリ）
    for init_file in root_path.rglob('__init__.py'):
        package_dir = init_file.parent
        
        if should_exclude(package_dir):
            print(f"  [除外] {package_dir.relative_to(root_path)}")
            continue
        
        rel_path = package_dir.relative_to(root_path)
        
        # ルートディレクトリの__init__.pyをスキップ
        if rel_path == Path('.'):
            continue
        
        # モジュール名を生成
        module_parts = list(rel_path.parts)
        module_name = '.'.join(module_parts)
        
        print(f"  [検出] {module_name} <- {rel_path}")
        modules.append(module_name)
        
        # サブモジュールの収集を試みる
        try:
            submodules = collect_submodules(module_name)
            for submodule in submodules:
                if submodule not in modules:
                    print(f"    [サブ] {submodule}")
                    modules.append(submodule)
        except Exception as e:
            print(f"    [警告] サブモジュール収集失敗: {e}")
    
    # トップレベルの.pyファイルを検出
    print("\nトップレベルモジュールを検出中...")
    for py_file in root_path.glob('*.py'):
        if py_file.name == '__init__.py':
            continue
        
        if should_exclude(py_file):
            print(f"  [除外] {py_file.name}")
            continue
        
        module_name = py_file.stem
        print(f"  [検出] {module_name}")
        modules.append(module_name)
    
    return list(set(modules))


# 除外パターン
EXCLUDE_PATTERNS = [
    r'test_.*',
    r'.*_test\.py',
    r'__pycache__',
    r'\..*',
    r'.*\.pyc',
]

# ローカルモジュールの自動収集
local_modules = collect_local_modules(SRC_PATH, EXCLUDE_PATTERNS)

print(f"\n{'=' * 60}")
print("検出されたローカルモジュール:")
print(f"{'=' * 60}")
for module in sorted(local_modules):
    print(f"  - {module}")
print(f"{'=' * 60}\n")

# 基本的な依存関係
BASE_HIDDEN_IMPORTS = [
    'customtkinter',
    'hier_config',
    'tkinter',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'tkinter.ttk',
]

# すべてのhiddenimports
all_hidden_imports = BASE_HIDDEN_IMPORTS + local_modules

print("すべてのhiddenimports:")
for imp in sorted(all_hidden_imports):
    print(f"  - {imp}")
print()

# Analysis設定
a = Analysis(
    ['src/main.py'],
    pathex=[str(SRC_PATH)],  # srcディレクトリをパスに追加
    binaries=customtkinter_binaries,
    datas=customtkinter_datas,
    hiddenimports=all_hidden_imports,
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=True,  # デバッグモードを一時的に有効化
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # コンソール出力を有効化
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)

app = BUNDLE(
    coll,
    name=f'{APP_NAME}.app',
    icon=None,
    bundle_identifier=BUNDLE_IDENTIFIER,
    info_plist={
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSHighResolutionCapable': 'True',
        'LSMinimumSystemVersion': '10.13.0',
        'NSAppleEventsUsageDescription': 'Config Lensがファイルにアクセスします。',
        'NSDesktopFolderUsageDescription': 'Config Lensがデスクトップにアクセスします。',
        'NSDocumentsFolderUsageDescription': 'Config Lensが書類フォルダにアクセスします。',
    },
)