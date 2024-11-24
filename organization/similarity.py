from dataclasses import dataclass

import numpy as np
import pandas as pd

from .constants import ORG_HIERARCHY_X, ORG_HIERARCHY_Y
from .hierarchy import OrganizationHierarchy


@dataclass
class SimilarityMetrics:
    """指数をまとめるデータクラス"""

    jaccard_index: float
    cosine_similarity: float
    sorensen_dice: float
    overlap_coefficient: float
    membership_ratio: float


class OrganizationSimilarityAnalyzer:
    """2つの組織の類似度を計算するためのクラス"""

    def __init__(
        self, hierarchy1: OrganizationHierarchy, hierarchy2: OrganizationHierarchy
    ):
        """
        2つの組織階層を初期化します。

        Parameters:
        - hierarchy1: OrganizationHierarchy - 最初の組織階層
        - hierarchy2: OrganizationHierarchy - 2番目の組織階層
        """
        self.hierarchy1 = hierarchy1
        self.hierarchy2 = hierarchy2

    def compute_similarities(
        self, sort_by: list = None, ascending: list = None
    ) -> pd.DataFrame:
        """
        2つの組織階層間の類似度指標を計算し、ソートを適用した結果をデータフレームとして返します。

        Parameters:
        - sort_by: list, optional - ソート基準とする列名のリスト。
                                     デフォルトは ["org_rank_df1", "jaccard_index", ORG_HIERARCHY_X]
        - ascending: list, optional - 各ソート基準に対する昇順/降順の指定。
                                    デフォルトは [True, True, True]

        Returns:
        - pd.DataFrame - 類似度指標を含むソート済みのデータフレーム
        """
        intersection = self._generate_org_pairs()
        jaccard_df = self._merge_user_counts(intersection)
        similarities_df = self._calculate_similarity_metrics(jaccard_df)

        # ソートの適用
        similarities_df = self._sort_similarities(similarities_df, sort_by, ascending)

        return similarities_df

    def _sort_similarities(
        self, df: pd.DataFrame, sort_by: list = None, ascending: list = None
    ) -> pd.DataFrame:
        """
        類似度データフレームを指定された基準でソートします。

        Parameters:
        - df: pandas.DataFrame - ソート対象のデータフレーム
        - sort_by: list, optional - ソート基準とする列名のリスト。
                                     デフォルトは ["org_rank_df1", "jaccard_index", ORG_HIERARCHY_X]
        - ascending: list, optional - 各ソート基準に対する昇順/降順の指定。
                                    デフォルトは [True, True, True]

        Returns:
        - pandas.DataFrame - ソート済みのデータフレーム
        """
        if sort_by is None:
            sort_by = [
                "org_rank_df1",
                "rank_difference_abs",
                "jaccard_index",
                ORG_HIERARCHY_X,
            ]

        if ascending is None:
            ascending = [True, True, True, True]

        return df.sort_values(by=sort_by, ascending=ascending)

    def _generate_org_pairs(self) -> pd.DataFrame:
        """
        2つの組織階層のユーザーコードを基に、組織ペアごとの共通ユーザー数をカウントし、データフレームとして返します。

        Returns:
        - intersection: pandas.DataFrame - 組織のペアとintersection_sizeを含むデータフレーム
        """
        if self.hierarchy1.exploded_df is None or self.hierarchy2.exploded_df is None:
            raise ValueError("Both hierarchies must be processed first")

        user_orgs = pd.merge(
            self.hierarchy1.exploded_df,
            self.hierarchy2.exploded_df,
            how="inner",
            on="user_code",
        )

        return (
            user_orgs.groupby([ORG_HIERARCHY_X, ORG_HIERARCHY_Y])
            .size()
            .reset_index(name="intersection_size")
        )

    def _calculate_similarity_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        提供されたデータフレームに基づいて類似度指標を計算し、ランク情報を追加した新しいデータフレームを返します。

        Parameters:
        - df: pandas.DataFrame - 組織ペアごとのユーザー数データフレーム

        Returns:
        - pandas.DataFrame - 類似度指標とランク情報を含むデータフレーム
        """
        intersection_size = df["intersection_size"].values
        num_users_df1 = df["num_users_df1"].values
        num_users_df2 = df["num_users_df2"].values

        metrics = self._compute_metrics_numpy(
            intersection_size, num_users_df1, num_users_df2
        )

        for metric_name, values in metrics.__dict__.items():
            df[metric_name] = values

        df["same_org_name"] = df[ORG_HIERARCHY_X] == df[ORG_HIERARCHY_Y]

        df["rank_difference_abs"] = (df["org_rank_df1"] - df["org_rank_df2"]).abs()
        df["rank_difference"] = df["org_rank_df1"] - df["org_rank_df2"]

        return df

    def _merge_user_counts(self, intersection_df: pd.DataFrame):
        """
        組織ペアごとの共通ユーザー数 (intersection_size) に、各組織の総ユーザー数 (num_users_df1 と num_users_df2) を結合します。

        Parameters:
        - intersection: pandas.DataFrame - ORG_HIERARCHY_X、ORG_HIERARCHY_Y、intersection_sizeを含むデータフレーム

        Returns:
        - jaccard_df: pandas.DataFrame - ORG_HIERARCHY_X、ORG_HIERARCHY_Y、intersection_size、num_users_df1、num_users_df2を含むデータフレーム
        """

        jaccard_df = (
            intersection_df.merge(
                self.hierarchy1.aggregated_df[
                    ["org_full_name", "num_users", "org_rank"]
                ],
                left_on=ORG_HIERARCHY_X,
                right_on="org_full_name",
                how="left",
            )
            .rename(columns={"num_users": "num_users_df1", "org_rank": "org_rank_df1"})
            .drop(columns=["org_full_name"])
        )

        jaccard_df = (
            jaccard_df.merge(
                self.hierarchy2.aggregated_df[
                    ["org_full_name", "num_users", "org_rank"]
                ],
                left_on=ORG_HIERARCHY_Y,
                right_on="org_full_name",
                how="left",
            )
            .rename(columns={"num_users": "num_users_df2", "org_rank": "org_rank_df2"})
            .drop(columns=["org_full_name"])
        )

        return jaccard_df

    @staticmethod
    def _compute_metrics_numpy(
        intersection_size: np.ndarray,
        num_users_df1: np.ndarray,
        num_users_df2: np.ndarray,
    ) -> SimilarityMetrics:
        """
        NumPy を活用して、ベクトル化された操作で複数の類似度指標を効率的に計算します。

        Parameters:
        - intersection_size: np.ndarray - 共通ユーザー数
        - num_users_df1: np.ndarray - 組織1のユーザー数
        - num_users_df2: np.ndarray - 組織2のユーザー数

        Returns:
        - SimilarityMetrics - 計算された類似度指標を含むデータクラス
        """
        # ジャッカード指数
        union_size = num_users_df1 + num_users_df2 - intersection_size
        jaccard_index = np.divide(
            intersection_size,
            union_size,
            out=np.zeros_like(intersection_size, dtype=float),
            where=union_size != 0,
        )

        # コサイン類似度
        cosine_similarity = np.divide(
            intersection_size,
            np.sqrt(num_users_df1) * np.sqrt(num_users_df2),
            out=np.zeros_like(intersection_size, dtype=float),
            where=(num_users_df1 > 0) & (num_users_df2 > 0),
        )

        # ソレンセン・ディケッタ指数
        sorensen_dice = np.divide(
            2 * intersection_size,
            num_users_df1 + num_users_df2,
            out=np.zeros_like(intersection_size, dtype=float),
            where=(num_users_df1 + num_users_df2) > 0,
        )

        # オーバーラップ係数
        min_size = np.minimum(num_users_df1, num_users_df2)
        overlap_coefficient = np.divide(
            intersection_size,
            min_size,
            out=np.zeros_like(intersection_size, dtype=float),
            where=min_size > 0,
        )

        # 所属割合
        membership_ratio = np.divide(
            intersection_size,
            (num_users_df1 + num_users_df2) / 2,
            out=np.zeros_like(intersection_size, dtype=float),
            where=((num_users_df1 + num_users_df2) / 2) != 0,
        )

        return SimilarityMetrics(
            jaccard_index,
            cosine_similarity,
            sorensen_dice,
            overlap_coefficient,
            membership_ratio,
        )
