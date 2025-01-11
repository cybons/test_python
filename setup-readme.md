# 開発環境セットアップガイド

## フォルダ構成
```
プロジェクトルート/
  ├── Dockerfile          # ベースイメージの定義
  ├── requirements.txt    # Pythonパッケージの依存関係
  ├── docker-compose.yml  # 開発環境の設定
  ├── .devcontainer/
  │   └── devcontainer.json  # VSCode開発環境の設定
  └── src/               # ソースコード
```

## 初回セットアップ

1. 必要なツールのインストール
   - Docker Desktop
   - Visual Studio Code
   - VSCode拡張機能: Dev Containers

2. ベースイメージの作成
   ```bash
   # プロジェクトルートディレクトリで実行
   docker build -t my-python-app .
   ```

3. VSCodeでの開発環境セットアップ
   1. VSCodeでプロジェクトのルートディレクトリを開く
   2. コマンドパレット（Cmd/Ctrl + Shift + P）を開く
   3. "Dev Containers: Reopen in Container" を選択
   4. 初回は開発用コンテナの構築に数分かかる場合があります

## 2回目以降の接続方法

1. VSCodeでプロジェクトのルートディレクトリを開く
2. 右下に表示される "Reopen in Container" をクリック
   - または、コマンドパレット（Cmd/Ctrl + Shift + P）から "Dev Containers: Reopen in Container" を選択

## 開発用コンテナの再作成

以下のような場合に開発用コンテナの再作成が必要になることがあります：
- `docker-compose.yml` や `devcontainer.json` の設定を変更した場合
- Python パッケージの依存関係（requirements.txt）を更新した場合
- コンテナの状態がおかしくなった場合

再作成の手順：
1. VSCode上で開発用コンテナに接続している状態で：
   - コマンドパレット（Cmd/Ctrl + Shift + P）を開く
   - "Dev Containers: Rebuild Container" を選択

または

2. Docker Desktopから：
   1. 該当のコンテナを停止・削除
   2. VSCodeで "Dev Containers: Reopen in Container" を実行

## トラブルシューティング

- VSCode拡張機能が正しく動作しない場合：
  - コンテナを再構築してください
  - または、コマンドパレット → "Developer: Reload Window" を実行

- Pythonパッケージが認識されない場合：
  1. コマンドパレット → "Python: Select Interpreter" を実行
  2. コンテナ内のPythonインタープリタを選択

- コンテナへの接続が切れる場合：
  - `docker-compose.yml` に `tty: true` と `stdin_open: true` が設定されているか確認
  - Docker Desktopのリソース設定（メモリ、CPU）を確認
