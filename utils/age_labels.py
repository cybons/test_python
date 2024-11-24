import pandas as pd
import numpy as np
import os

def load_age_bins_labels(excel_path, sheet_name="Sheet1"):
    """
    Excelファイルから年齢ビンとラベルを読み込み、バリデーションを行います。

    Parameters:
    - excel_path (str): Excelファイルのパス
    - sheet_name (str): シート名 (デフォルトは "Sheet1")

    Returns:
    - bins (list): ビンの境界値リスト
    - labels (list): ラベルのリスト
    """
    # ファイルの存在確認
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"指定されたExcelファイルが存在しません: {excel_path}")

    try:
        # A:C列を読み込む
        df_bins = pd.read_excel(excel_path, sheet_name=sheet_name, usecols="A:C")
    except Exception as e:
        raise ValueError(f"Excelファイルの読み込みに失敗しました: {e}")

    # ヘッダーの確認
    expected_headers = ['bin_start', 'bin_end', 'label']
    if not all(col in df_bins.columns for col in expected_headers):
        raise ValueError(f"Excelファイルのヘッダーが期待と異なります。期待されるヘッダー: {expected_headers}")

    # bin_start と bin_end が数値であることを確認
    if not pd.api.types.is_numeric_dtype(df_bins['bin_start']):
        raise ValueError("bin_start は数値型でなければなりません。")
    if not pd.api.types.is_numeric_dtype(df_bins['bin_end'].dropna()):
        raise ValueError("bin_end は数値型でなければなりません。")

    # bin_start が昇順であることを確認
    if not df_bins['bin_start'].is_monotonic_increasing:
        raise ValueError("bin_start は昇順でなければなりません。")

    # bin_end の最後の値が None（NaN）であることを確認
    last_bin_end = df_bins['bin_end'].iloc[-1]
    if not pd.isna(last_bin_end):
        raise ValueError("bin_end の最後の値は None（または空白）でなければなりません。")

    # bin_end が None の行以外は昇順であることを確認
    bin_end = df_bins['bin_end'].fillna(np.inf).tolist()
    bin_start = df_bins['bin_start'].tolist()

    # 最終的なbinsリストを作成
    bins = bin_start + [bin_end[-1]]

    labels = df_bins['label'].tolist()

    return bins, labels

def assign_age_group(df, age_column, bins, labels, new_column="age_group"):
    """
    年齢をグループ化して新しい列を作成します。

    Parameters:
    - df (pd.DataFrame): 対象のデータフレーム
    - age_column (str): 年齢が格納されている列名
    - bins (list): 年齢のビン
    - labels (list): 各ビンに対応するラベル
    - new_column (str): 新しく作成する列名 (デフォルトは "age_group")

    Returns:
    - pd.DataFrame: 新しい列が追加されたデータフレーム
    """
    df[new_column] = pd.cut(
        df[age_column],
        bins=bins,
        labels=labels,
        right=False,          # 各ビンの右側を含まない
        include_lowest=True    # 最初のビンに最小値を含める
    )
    return df

def validate_age_bins(bins):
    """
    ビンが連続しており、昇順になっているかを検証します。

    Parameters:
    - bins (list): ビンの境界値リスト

    Raises:
    - ValueError: ビンが連続していない、または昇順でない場合
    """
    if not all(bins[i] < bins[i+1] for i in range(len(bins)-1)):
        raise ValueError("ビンの境界値はすべて昇順で連続している必要があります。")

# 実際の使用例
if __name__ == "__main__":
    # Excelファイルからビンとラベルを読み込む
    excel_path = "age_bins_labels.xlsx"
    try:
        bins, labels = load_age_bins_labels(excel_path)
        validate_age_bins(bins)
    except (ValueError, FileNotFoundError) as e:
        print(f"エラー: {e}")
        exit(1)

    # データフレームの読み込み（例）
    df_local_user = pd.read_csv("local_user_data.csv")

    # 年齢グループを割り当てる
    df_local_user = assign_age_group(df_local_user, 'age', bins, labels, new_column="age_group")

    # 欠損値を "未設定" とする場合
    df_local_user["age_group"].fillna("未設定", inplace=True)

    # 結果の確認
    print(df_local_user.head())