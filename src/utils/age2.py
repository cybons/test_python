import pandas as pd
import numpy as np
import os

class AgeGroupProcessor:
    """
    年齢グループの処理を行うクラス
    """

    def __init__(self, excel_path, sheet_name="Sheet1"):
        """
        コンストラクタ

        Parameters:
        - excel_path (str): 年齢ビンとラベルを定義したExcelファイルのパス
        - sheet_name (str): 読み込むシート名 (デフォルトは "Sheet1")
        """
        self.excel_path = excel_path
        self.sheet_name = sheet_name
        self.bins = None
        self.labels = None

    def _load_and_validate_bins_labels(self):
        """
        Excelファイルから年齢ビンとラベルを読み込み、バリデーションを行う内部メソッド
        
        Returns:
        - tuple: (bins, labels)
        """
        # ファイルの存在確認
        if not os.path.exists(self.excel_path):
            raise FileNotFoundError(f"指定されたExcelファイルが存在しません: {self.excel_path}")

        try:
            # A:C列を読み込む
            df_bins = pd.read_excel(self.excel_path, sheet_name=self.sheet_name, usecols="A:C")
        except Exception as e:
            raise ValueError(f"Excelファイルの読み込みに失敗しました: {e}")

        # ヘッダーの確認
        expected_headers = ['bin_start', 'bin_end', 'label']
        if not all(col in df_bins.columns for col in expected_headers):
            raise ValueError(f"Excelファイルのヘッダーが期待と異なります。期待されるヘッダー: {expected_headers}")

        # バリデーション
        self._validate_bin_columns(df_bins)

        # bin_end の最後の値が None（NaN）であることを確認
        last_bin_end = df_bins['bin_end'].iloc[-1]
        if not pd.isna(last_bin_end):
            raise ValueError("bin_end の最後の値は None（または空白）でなければなりません。")

        # binsとlabelsの作成
        bins = df_bins['bin_start'].tolist() + [df_bins['bin_end'].fillna(np.inf).tolist()[-1]]
        labels = df_bins['label'].tolist()

        # ビンの連続性と昇順のバリデーション
        if not all(bins[i] < bins[i+1] for i in range(len(bins)-1)):
            raise ValueError("ビンの境界値はすべて昇順で連続している必要があります。")

        return bins, labels

    def _validate_bin_columns(self, df_bins):
        """
        bin_start と bin_end の列のバリデーションを行う内部メソッド

        Parameters:
        - df_bins (pd.DataFrame): ビン情報のデータフレーム
        """
        # bin_start と bin_end が数値であることを確認
        if not pd.api.types.is_numeric_dtype(df_bins['bin_start']):
            raise ValueError("bin_start は数値型でなければなりません。")
        if not pd.api.types.is_numeric_dtype(df_bins['bin_end'].dropna()):
            raise ValueError("bin_end は数値型でなければなりません。")

        # bin_start が昇順であることを確認
        if not df_bins['bin_start'].is_monotonic_increasing:
            raise ValueError("bin_start は昇順でなければなりません。")

    def assign_age_group(self, df, age_column, new_column="age_group", fill_na_value="未設定"):
        """
        年齢をグループ化して新しい列を作成する

        Parameters:
        - df (pd.DataFrame): 対象のデータフレーム
        - age_column (str): 年齢が格納されている列名
        - new_column (str): 新しく作成する列名 (デフォルトは "age_group")
        - fill_na_value (str): 欠損値を埋める値 (デフォルトは "未設定")

        Returns:
        - pd.DataFrame: 新しい列が追加されたデータフレーム
        """
        # ビンとラベルの遅延読み込み
        if self.bins is None or self.labels is None:
            self.bins, self.labels = self._load_and_validate_bins_labels()

        df[new_column] = pd.cut(
            df[age_column],
            bins=self.bins,
            labels=self.labels,
            right=False,          # 各ビンの右側を含まない
            include_lowest=True    # 最初のビンに最小値を含める
        )
        
        # 欠損値を指定の値で埋める
        df[new_column].fillna(fill_na_value, inplace=True)
        
        return df

def main():
    """
    メイン処理
    """
    # Excelファイルからビンとラベルを読み込む
    excel_path = "age_bins_labels.xlsx"
    
    try:
        # AgeGroupProcessorのインスタンスを作成（この時点では何も読み込まない）
        processor = AgeGroupProcessor(excel_path)
        
        # データフレームの読み込み（例）
        df_local_user = pd.read_csv("local_user_data.csv")
        
        # 年齢グループを割り当てる（この時点でExcelファイルを読み込む）
        df_local_user = processor.assign_age_group(df_local_user, 'age')
        
        # 結果の確認
        print(df_local_user.head())
        
    except (ValueError, FileNotFoundError) as e:
        print(f"エラー: {e}")
        exit(1)

if __name__ == "__main__":
    main()