import ctypes
import os
import shutil
import zipfile
from datetime import datetime


def is_hidden(filepath):
    """ファイルが隠しファイルかどうかを判定します（WindowsとUnix対応）。"""
    if os.name == "nt":
        # Windowsの場合
        attribute = ctypes.windll.kernel32.GetFileAttributesW(str(filepath))
        if attribute == -1:
            return False
        return bool(attribute & 2)  # FILE_ATTRIBUTE_HIDDEN = 0x2
    else:
        # Unix系の場合
        return os.path.basename(filepath).startswith(".")


def compress_files_with_timestamp(
    directory, base_name="archive", format="zip", separator="_"
):
    """指定したディレクトリ内の隠しファイルを除くすべてのファイルをタイムスタンプ付きで圧縮します。"""
    # 現在のタイムスタンプを取得
    timestamp = datetime.now().strftime("%y%m%d%H%M%S")
    archive_name = f"{base_name}{separator}{timestamp}.{format}"
    archive_path = os.path.join(directory, archive_name)

    # 圧縮対象のファイルをリストアップ
    files_to_compress = [
        f
        for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f))
        and not is_hidden(os.path.join(directory, f))
    ]

    # ZIP形式で圧縮
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in files_to_compress:
            file_path = os.path.join(directory, file)
            zipf.write(file_path, arcname=file)

    return archive_path


def move_to_old(directory, archive_path):
    """圧縮ファイルを'old'フォルダに移動します。"""
    old_dir = os.path.join(directory, "old")
    os.makedirs(old_dir, exist_ok=True)
    shutil.move(archive_path, old_dir)
    print(f"圧縮ファイルを '{old_dir}' に移動しました。")


def main():
    # 圧縮対象のディレクトリを指定（スクリプトと同じディレクトリを使用）
    target_dir = os.path.abspath(os.path.dirname(__file__))

    # 圧縮形式を確認（今回はZIPのみ）
    compression_format = "zip"

    # アーカイブのベース名を設定（例: archive）
    base_archive_name = "archive"

    # 区切り文字を設定（'_' または '-'）
    SEPARATOR = "_"  # アンダースコアの場合
    # SEPARATOR = '-'  # ハイフンの場合

    try:
        archive_path = compress_files_with_timestamp(
            target_dir,
            base_name=base_archive_name,
            format=compression_format,
            separator=SEPARATOR,
        )
        move_to_old(target_dir, archive_path)
    except Exception as e:
        print(f"エラーが発生しました: {e}")


if __name__ == "__main__":
    main()
