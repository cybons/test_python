import os
import zipfile

# チェック対象のディレクトリ
target_dir = r"H:\Book\整理終了"

# 許可する拡張子
allowed_extensions = {".jpg", ".png", ".jpeg"}


def check_zip_file(zip_path):
    invalid_files = []
    with zipfile.ZipFile(zip_path, "r") as zip:
        for file in zip.namelist():
            # フォルダ（末尾がスラッシュ）を無視
            if file.endswith("/"):
                continue
            # jpg, png以外のファイルをリストに追加
            if not any(file.lower().endswith(ext) for ext in allowed_extensions):
                invalid_files.append(file)
    return invalid_files


# サブフォルダを再帰的に検索
for root, _, files in os.walk(target_dir):
    for file in files:
        if file.endswith(".zip"):
            zip_path = os.path.join(root, file)
            # print(f"Checking: {zip_path}")
            invalid_files = check_zip_file(zip_path)
            if invalid_files:
                print(f"以下のjpg, png以外のファイルが見つかりました: {zip_path}")
                for invalid_file in invalid_files:
                    print(f"  - {invalid_file}")
            # else:
            #     print(f"問題ありません: {zip_path}")
