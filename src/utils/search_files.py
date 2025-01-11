from datetime import datetime
from pathlib import Path


def get_sorted_date_folders(base_path):
    """
    指定されたベースパス内のフォルダを日付順にソートして返します。
    フォルダ名はYYYYMMDD形式である必要があります。
    """
    folders = []
    for entry in Path(base_path).iterdir():
        if entry.is_dir():
            try:
                # フォルダ名を日付としてパース
                folder_date = datetime.strptime(entry.name, "%Y%m%d")
                folders.append((folder_date, entry))
            except ValueError:
                # フォルダ名が日付形式でない場合は無視
                continue
    # 日付でソート（降順）
    folders.sort(reverse=True, key=lambda x: x[0])
    return [folder for _, folder in folders]


def find_file_in_folder(folder, sub_path, filename_pattern):
    """
    指定されたフォルダ内のサブパスとファイル名パターンに一致するファイルを探します。
    一致するファイルが見つかればそのパスを返し、見つからなければNoneを返します。
    """
    file_path = folder / sub_path / filename_pattern
    if file_path.exists():
        return str(file_path)
    return None


def main():
    base_path = r"\\path"  # ベースパスを適宜変更してください
    sub_folder = "作業用"

    # フォルダを日付順にソート
    sorted_folders = get_sorted_date_folders(base_path)

    if not sorted_folders:
        raise FileNotFoundError(
            "指定されたベースパス内に有効な日付フォルダが存在しません。"
        )

    # 受付リストを取得（最新フォルダ）
    latest_folder = sorted_folders[0]
    reception_list_filename = (
        "受付リスト_yyyymmdd.xlsx"  # 実際のファイル名に合わせて変更
    )
    reception_list_path = find_file_in_folder(
        latest_folder, sub_folder, reception_list_filename
    )

    if reception_list_path is None:
        raise FileNotFoundError(
            f"受付リストが見つかりません: {latest_folder / sub_folder / reception_list_filename}"
        )

    # 保護リストを取得（2番目に新しいフォルダ）
    if len(sorted_folders) >= 2:
        second_latest_folder = sorted_folders[1]
        protection_list_filename = (
            "保護リスト_yyyymmdd.xlsx"  # 実際のファイル名に合わせて変更
        )
        protection_list_path = find_file_in_folder(
            second_latest_folder, sub_folder, protection_list_filename
        )
    else:
        protection_list_path = None

    # 保護リストが存在しない場合はNoneを設定
    if protection_list_path is None:
        protection_list = None
    else:
        protection_list = protection_list_path

    # 受付リストのパス
    reception_list = reception_list_path

    # 結果の表示（デバッグ用）
    print(f"受付リスト: {reception_list}")
    print(f"保護リスト: {protection_list}")


if __name__ == "__main__":
    main()
