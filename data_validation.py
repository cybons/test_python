import pandas as pd


def validate_location_codes(org_df: pd.DataFrame, location_df: pd.DataFrame):
    """
    org_df と location_dfに location_code が含まれているか確認します。
    org_df の location_code がすべて location_codes に含まれているかを確認します。
    足りない場合はエラーを出力します。

    Args:
        org_df (pd.DataFrame): 検証対象のデータフレーム。
        location_df (pd.DataFrame): 有効な location_df

    Raises:
        ValueError: org_df の location_code に location_codes に存在しない値が含まれている場合に発生します。
    """

    if "location_code" not in org_df.columns:
        raise KeyError("dfに location_code 列が存在しません。")

    if "location_code" not in location_df.columns:
        raise KeyError("location_df に location_code 列が存在しません。")

    location_codes = location_df["location_code"].tolist()

    # org_df の location_code がすべて location_codes に含まれているかを確認
    mask_exists_location = org_df["location_code"].isin(location_codes)
    missing_codes = org_df[~mask_exists_location]["location_code"].unique()

    # 足りない location_code があればエラーを出力
    if len(missing_codes) > 0:
        raise ValueError(
            f"以下の location_code が location_codes に含まれていません: {', '.join(missing_codes)}"
        )

    print("すべての location_code が有効です。")


def validate_changes(changes_df: pd.DataFrame):
    """
    変更点データフレームの検証を行います。

    Args:
        changes_df (pd.DataFrame): 変更点が特定されたデータフレーム。

    Raises:
        ValueError: 無効フラグが不正な値が含まれている場合。
    """
    # 無効フラグがNoneまたは1のみであることを確認
    if "disable_flag" in changes_df.columns:
        invalid_flags = changes_df[
            (changes_df["disable_flag"] != 1) & (changes_df["disable_flag"].notna())
        ]
        if not invalid_flags.empty:
            raise ValueError("無効フラグに不正な値が含まれています。")

    # flagがADDまたはUPDATEであることを確認
    if "flag" in changes_df.columns:
        if not changes_df["flag"].isin(["ADD", "UPDATE"]).all():
            raise ValueError("フラグに不正な値が含まれています。")
