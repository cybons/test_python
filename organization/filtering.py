import logging
from dataclasses import dataclass
from typing import Optional, Union

import pandas as pd

from .constants import OPERATOR_MAPPING


@dataclass
class FilterCondition:
    """フィルタリング条件を表すデータクラス

    Returns:
        _type_: _description_
    """

    condition_id: str  # 条件の一意識別子
    similarity_index: Optional[str]  # 類似度指標の名前
    operator: str  # 演算子（例: '>', '<', '==', etc.）
    group_min_users: Optional[int]  # グループの最小ユーザー数
    group_max_users: Optional[int]  # グループの最大ユーザー数
    column: str  # フィルタリング対象の列名
    value: Union[float, int]  # フィルタリングに使用する値
    description: str  # 条件の説明

    @classmethod
    def from_series(cls, series: pd.Series) -> "FilterCondition":
        """pandas.Seriesからフィルタリング条件を生成"""
        return cls(
            condition_id=series["Condition ID"],
            similarity_index=series["Similarity Index"]
            if pd.notna(series["Similarity Index"])
            else None,
            operator=series["Operator"],
            group_min_users=series["Group Min Users"]
            if pd.notna(series["Group Min Users"])
            else None,
            group_max_users=series["Group Max Users"]
            if pd.notna(series["Group Max Users"])
            else None,
            column=series["Column"] if pd.notna(series["Column"]) else None,
            value=series["Value"],
            description=series["Description"],
        )


class OrganizationFilter:
    """組織の類似度データに対するフィルタリング処理を行うクラス"""

    def __init__(self, similarity_df: pd.DataFrame, conditions_path: str):
        """
        コンストラクタ

        Parameters:
            similarity_df (pd.DataFrame): 類似度計算結果のDataFrame
            conditions_path (str): フィルタリング条件を含むExcelファイルのパス
        """
        self.similarity_df = similarity_df.copy()
        self.conditions_path = conditions_path
        self.logger = logging.getLogger(__name__)

    def apply_filters(self) -> pd.DataFrame:
        """
        フィルタリング条件を適用し、結果のDataFrameを返す

        Returns:
            pd.DataFrame: フィルタリング結果を含むDataFrame
        """
        try:
            # 条件の読み込みとバリデーション
            conditions = self._load_and_validate_conditions()

            # フィルタリング用の列を初期化
            self._initialize_filter_columns()

            # 基本的なフィルタリング（ユーザー数が3人未満のペアを除外）
            self._apply_basic_filters()

            # フィルタリング対象のデータを取得
            filtered_df = self.similarity_df[~self.similarity_df["exclude"]].copy()

            # 各条件を適用
            for condition in conditions:
                self._apply_condition(filtered_df, condition)

            # 高類似度ペアに基づく除外フラグの設定
            self._set_exclude_flags()

            return self.similarity_df

        except Exception as e:
            self.logger.error(f"Error during filtering: {str(e)}")
            raise

    def _load_and_validate_conditions(self) -> list[FilterCondition]:
        """
        Excelファイルからフィルタリング条件を読み込み、演算子のバリデーションを行います。
        複数の条件がある場合は、各条件を個別の行として処理します。

        Returns:
            list[FilterCondition]: フィルタリング条件のリスト
        """
        try:
            conditions_df = pd.read_excel(self.conditions_path)

            # 必須列の確認
            required_columns = {
                "Condition ID",
                "Similarity Index",
                "Operator",
                "Group Min Users",
                "Group Max Users",
                "Column",
                "Value",
                "Description",
            }
            missing_columns = required_columns - set(conditions_df.columns)
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")

            # 演算子のバリデーション
            invalid_operators = set(conditions_df["Operator"].dropna()) - set(
                OPERATOR_MAPPING.keys()
            )
            if invalid_operators:
                raise ValueError(f"Unsupported operators found: {invalid_operators}")

            # FilterConditionオブジェクトのリストを作成
            return [
                FilterCondition.from_series(row) for _, row in conditions_df.iterrows()
            ]

        except Exception as e:
            self.logger.error(f"Error loading conditions: {str(e)}")
            raise

    def _initialize_filter_columns(self) -> None:
        """フィルタリング用の列を初期化"""
        self.similarity_df["exclude"] = False  # 除外フラグの初期化
        self.similarity_df["is_high_similarity"] = False  # 高類似度フラグの初期化
        self.similarity_df["matched_conditions"] = [
            [] for _ in range(len(self.similarity_df))
        ]  # マッチした条件のリストを初

    def _apply_basic_filters(self) -> None:
        """基本的なフィルタリングを適用（ユーザー数が3人未満のペアを除外）"""
        self.similarity_df.loc[
            (self.similarity_df["num_users_df1"] < 3)
            | (self.similarity_df["num_users_df2"] < 3),
            "exclude",
        ] = True  # ユーザー数が3未満の行に除外フラグを設定

    def _apply_condition(
        self, filtered_df: pd.DataFrame, condition: FilterCondition
    ) -> None:
        """
        単一の条件をDataFrameに適用

        Excelファイルからフィルタリング条件を読み込み、'exclude' と 'is_high_similarity' 列を追加します。
        'exclude' 列はフィルタリングせずに全てのペアに対して設定します。
        'matched_conditions' 列には、'is_high_similarity=True' となった際にマッチした条件のIDをリストとして記録します。

        Parameters:
            filtered_df (pd.DataFrame): フィルタリング対象のDataFrame
            condition (FilterCondition): 適用する条件
        """
        # 条件の初期化（全てTrueで開始）
        mask = pd.Series([True] * len(filtered_df), index=filtered_df.index)

        # グループの最小ユーザー数の条件
        if condition.group_min_users is not None:
            mask &= (filtered_df["num_users_df1"] >= condition.group_min_users) & (
                filtered_df["num_users_df2"] >= condition.group_min_users
            )

        # グループの最大ユーザー数の条件
        if condition.group_max_users is not None:
            mask &= (filtered_df["num_users_df1"] <= condition.group_max_users) & (
                filtered_df["num_users_df2"] <= condition.group_max_users
            )

        # 類似度指標の条件
        if condition.similarity_index is not None:
            op_func = OPERATOR_MAPPING[condition.operator]
            mask &= op_func(filtered_df[condition.similarity_index], condition.value)

        # 追加条件の適用
        if condition.column is not None:
            op_func = OPERATOR_MAPPING[condition.operator]
            mask &= op_func(filtered_df[condition.column], condition.value)

        # 条件を満たす行のインデックスを取得
        matched_indices = filtered_df[mask].index

        # 高類似度フラグを設定
        self.similarity_df.loc[matched_indices, "is_high_similarity"] = True

        # matched_conditionsの更新
        for idx in matched_indices:
            if isinstance(self.similarity_df.at[idx, "matched_conditions"], list):
                self.similarity_df.at[idx, "matched_conditions"].append(
                    condition.condition_id
                )
            else:
                self.similarity_df.at[idx, "matched_conditions"] = [
                    condition.condition_id
                ]

    def _set_exclude_flags(self) -> None:
        """高類似度ペアが存在する場合、同じ組織名の他のペアをexclude=Trueに設定"""
        high_similarity_pairs = self.similarity_df[
            self.similarity_df["is_high_similarity"]
        ]

        if not high_similarity_pairs.empty:

            def set_flags(org_column: str):
                """指定された組織名列に基づいて除外フラグを設定するヘルパー関数"""
                orgs_to_exclude = pd.unique(high_similarity_pairs[org_column])
                self.similarity_df.loc[
                    (self.similarity_df[org_column].isin(orgs_to_exclude))
                    & (~self.similarity_df.index.isin(high_similarity_indices)),
                    "exclude",
                ] = True

            high_similarity_indices = (
                high_similarity_pairs.index
            )  # 高類似度ペア自体のインデックスを取得

            # df1_org_full_nameに基づく除外フラグの設定
            set_flags("df1_org_full_name")

            # df2_org_full_nameに基づく除外フラグの設定
            set_flags("df2_org_full_name")
