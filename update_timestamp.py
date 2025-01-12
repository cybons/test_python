import os
import time

MAX_FILENAME_LENGTH = 85  # ファイル名の最大文字数
MAX_FILENAME_BYTES = 255  # ファイル名の最大バイト数


def truncate_filename_by_bytes(filename, max_bytes):
    """
    ファイル名をバイト数で切り詰める関数
    """
    name, ext = os.path.splitext(filename)
    encoded_ext = ext.encode("utf-8")  # 拡張子をバイト数で計算
    available_bytes = max_bytes - len(encoded_ext)  # 拡張子分を引く

    encoded_name = name.encode("utf-8")  # ファイル名部分をバイト列にエンコード
    if len(encoded_name) > available_bytes:
        # バイト数をオーバーした場合、トリミング
        truncated_name = encoded_name[:available_bytes].decode("utf-8", "ignore")
    else:
        truncated_name = name

    return f"{truncated_name}{ext}"


def rename_files_in_folder(folder_path):
    """
    指定フォルダ内のファイルをリネームする関数。
    - バイト数で切り詰めた名前にリネーム。
    - リネーム結果が重複する場合はスキップ。
    """
    for root, _, files in os.walk(folder_path):
        for file in files:
            old_path = os.path.join(root, file)

            # ファイル名を切り詰め
            new_filename = truncate_filename_by_bytes(file, MAX_FILENAME_BYTES)
            new_path = os.path.join(root, new_filename)

            if old_path == new_path:
                # リネームの必要がない場合
                print(f"Skipping (no change needed): {file}")
                continue

            if os.path.exists(new_path):
                # リネーム結果が重複する場合
                print(f"Skipping (conflict): {new_filename}")
                continue

            # リネーム実行
            try:
                os.rename(old_path, new_path)
                print(f"Renamed: {file} -> {new_filename}")
            except Exception as e:
                print(f"Error renaming {file}: {e}")


def truncate_filename(filename, max_length):
    """
    ファイル名を最大文字数以内に切り詰める関数
    """
    name, ext = os.path.splitext(filename)
    # ファイル名部分を切り詰めて、拡張子を追加
    truncated_name = name[: max_length - len(ext.encode("utf-8"))]
    return f"{truncated_name}{ext}"


def update_file_dates(folder_path):
    # フォルダ内の全ファイルを取得
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".mp4"):  # mp4ファイルのみ対象
                file_path = os.path.join(root, file)

                # 作成日を取得
                creation_time = os.path.getctime(
                    file_path
                )  # 作成日（UNIXタイムスタンプ）
                formatted_creation_time = time.ctime(
                    creation_time
                )  # 可読フォーマット（デバッグ用）
                print(f"File: {file} | Creation Date: {formatted_creation_time}")

                # 最終更新日を作成日に変更
                os.utime(file_path, (creation_time, creation_time))
                print(f"Updated last modified date to: {formatted_creation_time}")


def count_char(folder_path):
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".mp4"):  # mp4ファイルのみ対象
                print(truncate_filename(file, MAX_FILENAME_LENGTH))


# 対象フォルダのパスを指定
target_folder = r"H:\AV"  # フォルダパスを指定
# update_file_dates(target_folder)
rename_files_in_folder(target_folder)
