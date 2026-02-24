# Changelog

このファイルはバージョンごとの変更内容を記録します。
形式は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。

---

## [0.2.0] - 2026-02-24

### 追加
- **Config Validator 機能** — 現在の running-config・設定変更内容・想定される running-configの 3 ファイルを入力し、差分が設定変更内容で説明できるかを検証する機能を追加
  - `change_remove`（黄）/ `remove`（赤、検証エラー）/ `change_add`（黄）/ `add`（緑、検証エラー）の 4層ハイライト
  - 設定変更内容の黄色行をクリックすると対応差分行をハイライト（連動機能）
  - 説明できない差分が調査導きの欠れは `unmatched`（グレー）として表示
- **ナビゲーションバーに 「Config Validator」 ボタンを追加**
- **ナビゲーションバーにアプリバージョンを表示**
- **左右テキストエリアの同期スクロール** — マウスホイール・スクロールバードラッグで左右が連動する（Windows / macOS / Linux 対応）

### 修正
- **replace ブロック内の行整列バグを修正** — 異なる設定行が誤って横に並んでいた問題を解決。replace ブロック内で改めて階層キーを再マッチングし、一致する行のみ横に並べるよう改善
- **macOS 配布時のフォルダ名不具合を修正**
- **macOS ビルド時のアドホック署名を適用**（ダウンロード後に起動できない問題を解決）

### 内部改善（影響なし）
- `PLATFORM_MAP` を `src/compare/platforms.py` に一元管理（`compare/view.py`・`validate/view.py` の重複定義を解消）
- `calcurate_hierarcihical_path` → `calculate_hierarchical_path` にリネーム（スペルミス修正）
- `validate/logic.py` の未使用定数 `LINE_NUM_WIDTH` を削除
- テストアーキテクチャ（`tests/validate/` 新設）とフィクスチャファイル（`eBGP/`・`vlan/`）を整備
- `docs/architecture.md`・`docs/development.md` を機能追加に合わせて更新

---

## [0.1.0] - 2026-02-23

### 追加
- ネットワーク機器のコンフィグファイルを2列で差分比較する機能
- 差分の色分け表示（追加: 緑、削除: 赤、変更なし: グレー）
- 階層構造を考慮した比較（Cisco IOS 対応）
- 無視パターン（正規表現）の登録・管理機能
- macOS / Windows 向けスタンドアロンアプリのビルド対応
