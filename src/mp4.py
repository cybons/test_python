import os

from mutagen.mp4 import MP4

source_folder = r"H:\AV"


def add_filename_to_metadata(folder):
    for filename in os.listdir(folder):
        if filename.endswith(".mp4"):
            filepath = os.path.join(folder, filename)
            try:
                video = MP4(filepath)
                # タイトルまたはコメントにファイル名を書き込む
                video["\xa9nam"] = filename  # タイトル（©namタグ）
                video.save()
                print(f"Metadata updated: {filename}")
            except Exception as e:
                print(f"Error updating {filename}: {e}")


# 実行
add_filename_to_metadata(source_folder)
