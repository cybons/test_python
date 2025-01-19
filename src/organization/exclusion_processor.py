"""
除外対象者の処理を行うモジュール
各種除外者リスト（産休・育休・休職・申請による除外）を統合して処理し、
システムユーザー情報と連携する
"""

from dataclasses import dataclass

import pandas as pd


@dataclass
class ExclusionConfig:
    """除外理由の設定を保持するデータクラス"""

    code: str
    name: str
    sheet_name: str
    required_columns: list[str]


class ExclusionProcessor:
    """
    各種除外対象者リストを処理・統合するクラス
    """

    # 除外理由の定義
    CONFIGS = {
        "maternity": ExclusionConfig(
            code="01",
            name="産休",
            sheet_name="産休取得者",
            required_columns=["社員番号", "氏名", "開始日", "終了予定日"],
        ),
        "childcare": ExclusionConfig(
            code="02",
            name="育休",
            sheet_name="育休取得者",
            required_columns=["社員番号", "氏名", "開始日", "終了予定日"],
        ),
        "leave": ExclusionConfig(
            code="03",
            name="休職",
            sheet_name="休職者",
            required_columns=["社員番号", "氏名", "休職開始日"],
        ),
        "transfer": ExclusionConfig(
            code="04",
            name="出向",
            sheet_name="出向者",
            required_columns=["社員番号", "氏名"],
        ),
    }

    def __init__(self, system_user_df: pd.DataFrame):
        """
        初期化

        Parameters:
        - system_user_df: システムユーザー情報のDataFrame
        """
        # システムユーザー情報を保持
        self.system_user_df = system_user_df
        # 各種除外者のDataFrameを保持
        self.exclusion_dfs: dict[str, pd.DataFrame] = {}
        # 統合された除外者リスト
        self.combined_df: pd.DataFrame = None
        # ユーザーごとの除外理由を保持する辞書
        self.user_exclusions: dict[str, set[str]] = {}

    def add_exclusion_data(self, category: str, df: pd.DataFrame) -> None:
        """
        除外対象者のDataFrameを追加

        Parameters:
        - category: 除外カテゴリ（'maternity', 'childcare', 'leave', 'transfer'）
        - df: 除外対象者のDataFrame
        """
        if category not in self.CONFIGS:
            raise ValueError(f"Invalid category: {category}")

        config = self.CONFIGS[category]

        # 必須カラムの確認
        missing_cols = set(config.required_columns) - set(df.columns)
        if missing_cols:
            raise ValueError(f"Missing required columns for {category}: {missing_cols}")

        # DataFrameを標準形式に変換
        standardized_df = self._standardize_df(df, category)
        self.exclusion_dfs[category] = standardized_df

        # ユーザーごとの除外理由を更新
        for user_id in standardized_df["社員番号"]:
            if user_id not in self.user_exclusions:
                self.user_exclusions[user_id] = set()
            self.user_exclusions[user_id].add(config.name)

    def process_exclusions(self) -> None:
        """
        全ての除外対象者データを処理し、統合する
        """
        if not self.exclusion_dfs:
            raise ValueError("No exclusion data added")

        # 各DataFrameを結合
        dfs_to_combine = []
        for category, df in self.exclusion_dfs.items():
            config = self.CONFIGS[category]
            df = df.copy()
            df["exclusion_type"] = config.name
            df["exclusion_code"] = config.code
            dfs_to_combine.append(df)

        # 基本情報の統合
        self.combined_df = pd.concat(dfs_to_combine, ignore_index=True)

        # 除外理由をカンマ区切りの文字列として追加
        self.combined_df["exclusion_reasons"] = self.combined_df["社員番号"].apply(
            lambda x: ",".join(sorted(self.user_exclusions.get(x, [])))
        )

        # 重複を排除（同一社員番号の場合は最初のレコードを保持）
        self.combined_df = self.combined_df.drop_duplicates(
            subset=["社員番号"], keep="first"
        )

        # システムユーザー情報と結合
        self._merge_system_user_info()

    def _merge_system_user_info(self) -> None:
        """
        統合された除外者リストにシステムユーザー情報を結合する
        """
        # システムユーザー情報から必要な列を選択
        system_info = self.system_user_df[["社員番号", "メールアドレス", "所属組織"]]

        # 結合
        self.combined_df = pd.merge(
            self.combined_df, system_info, on="社員番号", how="left"
        )

    def export_to_excel(self, output_path: str) -> None:
        """
        除外対象者リストをExcelファイルに出力

        Parameters:
        - output_path: 出力先のExcelファイルパス
        """
        if self.combined_df is None:
            raise ValueError(
                "No processed data available. Run process_exclusions first."
            )

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            # 統合シートの出力（出力順を調整）
            columns_order = [
                "社員番号",
                "氏名",
                "メールアドレス",
                "所属組織",
                "exclusion_reasons",
                "開始日",
                "終了予定日",
                "exclusion_type",
                "exclusion_code",
            ]

            # 存在する列のみを選択
            output_columns = [
                col for col in columns_order if col in self.combined_df.columns
            ]

            self.combined_df[output_columns].to_excel(
                writer, sheet_name="全除外対象者", index=False
            )

            # 除外理由別シートの出力
            for reason in set().union(*self.user_exclusions.values()):
                reason_df = self.combined_df[
                    self.combined_df["exclusion_reasons"].str.contains(reason, na=False)
                ].copy()

                if not reason_df.empty:
                    reason_df.to_excel(
                        writer, sheet_name=f"{reason}対象者", index=False
                    )

    def get_all_excluded_users(self) -> list[str]:
        """全除外対象者の社員番号リストを取得"""
        return list(self.user_exclusions.keys())

    def get_excluded_users_by_reason(self, reason: str) -> list[str]:
        """
        特定の除外理由を持つユーザーの社員番号リストを取得

        Parameters:
        - reason: 除外理由（'産休', '育休', '休職', '出向'）
        """
        return [
            user_id
            for user_id, reasons in self.user_exclusions.items()
            if reason in reasons
        ]

    def get_active_users(self) -> pd.DataFrame:
        """
        除外対象者を除いた有効なユーザーリストを取得

        Returns:
        - pd.DataFrame: 有効なユーザーの情報を含むDataFrame
        """
        if self.system_user_df is None:
            raise ValueError("System user information is not available")

        # 除外対象者の社員番号リストを取得
        excluded_users = self.get_all_excluded_users()

        # システムユーザーから除外対象者を除外
        active_users = self.system_user_df[
            ~self.system_user_df["社員番号"].isin(excluded_users)
        ].copy()

        return active_users

    def get_exclusion_summary(self) -> pd.DataFrame:
        """
        除外理由ごとの集計を取得

        Returns:
        - pd.DataFrame: 除外理由ごとの対象者数を含むDataFrame
        """
        if not self.user_exclusions:
            return pd.DataFrame(columns=["除外理由", "対象者数"])

        # 全ての除外理由を取得
        all_reasons = set().union(*self.user_exclusions.values())

        # 各理由の対象者数をカウント
        summary_data = []
        for reason in sorted(all_reasons):
            count = len(self.get_excluded_users_by_reason(reason))
            summary_data.append({"除外理由": reason, "対象者数": count})

        # 合計行を追加
        summary_data.append(
            {
                "除外理由": "合計（ユニーク）",
                "対象者数": len(self.get_all_excluded_users()),
            }
        )

        return pd.DataFrame(summary_data)

    def _standardize_df(self, df: pd.DataFrame, category: str) -> pd.DataFrame:
        """
        DataFrameを標準形式に変換する内部メソッド

        Parameters:
        - df: 変換対象のDataFrame
        - category: 除外カテゴリ
        """
        standardized = df.copy()

        # 日付カラムの標準化
        date_columns = {
            "maternity": {"開始日": "開始日", "終了予定日": "終了予定日"},
            "childcare": {"開始日": "開始日", "終了予定日": "終了予定日"},
            "leave": {"休職開始日": "開始日", "復職予定日": "終了予定日"},
            "transfer": {"出向開始日": "開始日", "出向終了日": "終了予定日"},
        }

        if category in date_columns:
            for orig_col, new_col in date_columns[category].items():
                if orig_col in standardized.columns:
                    standardized[new_col] = pd.to_datetime(standardized[orig_col])

        return standardized


# 使用例
if __name__ == "__main__":
    # システムユーザー情報のサンプル
    system_users = pd.DataFrame(
        {
            "社員番号": ["001", "002", "003", "004"],
            "氏名": ["山田花子", "鈴木美咲", "佐藤優子", "田中美咲"],
            "メールアドレス": [
                "hanako@example.com",
                "misaki.s@example.com",
                "yuko.s@example.com",
                "misaki.t@example.com",
            ],
            "所属組織": ["営業部", "開発部", "人事部", "営業部"],
        }
    )

    # プロセッサーのインスタンスを作成
    processor = ExclusionProcessor(system_users)

    # 産休データを追加
    maternity_df = pd.DataFrame(
        {
            "社員番号": ["001", "002"],
            "氏名": ["山田花子", "鈴木美咲"],
            "開始日": ["2024-01-01", "2024-02-01"],
            "終了予定日": ["2024-07-01", "2024-08-01"],
        }
    )
    processor.add_exclusion_data("maternity", maternity_df)

    # 育休データを追加（一部ユーザーは産休と重複）
    childcare_df = pd.DataFrame(
        {
            "社員番号": ["001", "003"],
            "氏名": ["山田花子", "佐藤優子"],
            "開始日": ["2024-01-15", "2024-03-01"],
            "終了予定日": ["2024-12-31", "2024-12-31"],
        }
    )
    processor.add_exclusion_data("childcare", childcare_df)

    # データを処理
    processor.process_exclusions()

    # Excelに出力
    processor.export_to_excel("excluded_users.xlsx")
