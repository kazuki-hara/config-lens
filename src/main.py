"""Config Lens - エントリーポイント"""
import sys
from pathlib import Path


def setup_application_path() -> Path:
    """
    アプリケーションのパスを設定
    
    PyInstallerでバンドルされた場合と通常実行時の両方に対応し、
    アプリケーションがどこに移動されても正しく動作するようにします。
    
    Returns:
        Path: アプリケーションのベースパス
    """
    if getattr(sys, 'frozen', False):
        # PyInstallerでバンドルされている場合
        # sys._MEIPASSは一時展開ディレクトリを指す
        application_path = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        
        # 実行可能ファイルのパス（移動先のパス）
        executable_path = Path(sys.executable).parent
        
        print(f"[INFO] Bundled mode")
        print(f"[INFO] _MEIPASS: {application_path}")
        print(f"[INFO] Executable: {executable_path}")
    else:
        # 通常のPythonスクリプトとして実行されている場合
        application_path = Path(__file__).parent
        print(f"[INFO] Development mode")
        print(f"[INFO] Application path: {application_path}")
    
    # sys.pathにアプリケーションパスを追加
    if str(application_path) not in sys.path:
        sys.path.insert(0, str(application_path))
    
    return application_path


def main() -> None:
    """メインエントリーポイント"""
    import traceback
    
    try:
        # パス設定
        _ = setup_application_path()
        
        # 環境情報の表示
        print(f"[INFO] Python version: {sys.version}")
        print(f"[INFO] Platform: {sys.platform}")
        
        # アプリケーションのインポートと起動
        from ui.main_window import MainWindow
        
        print("[INFO] MainWindowをインスタンス化します...")
        app = MainWindow()
        
        print("[INFO] アプリケーションを起動します...")
        # CustomTkinterではmainloop()を使用
        app.mainloop()
        
    except Exception as e:
        error_msg = f"アプリケーション起動エラー:\n{traceback.format_exc()}"
        print(error_msg, file=sys.stderr)
        
        # エラーログをホームディレクトリに保存
        error_log_path = Path.home() / "config-lens-error.log"
        try:
            with open(error_log_path, "w", encoding="utf-8") as f:
                f.write(error_msg)
            print(f"[ERROR] ログファイル: {error_log_path}")
        except Exception as log_error:
            print(f"[ERROR] ログ保存失敗: {log_error}")
        
        # macOSダイアログでエラー表示
        try:
            import subprocess
            subprocess.run([
                "osascript", "-e",
                f'display dialog "エラーが発生しました:\\n{str(e)[:200]}\\n\\nログ: {error_log_path}" '
                f'buttons {{"OK"}} default button "OK" with icon stop'
            ])
        except Exception:
            pass
        
        sys.exit(1)


if __name__ == "__main__":
    main()