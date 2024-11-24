from dataclasses import dataclass

import numpy as np
import pandas as pd
from constants import ORG_HIERARCHY_X, ORG_HIERARCHY_Y
from hierarchy import OrganizationHierarchy


@dataclass
class SimilarityMetrics:
    jaccard_index: float
    cosine_similarity: float
    sorensen_dice: float
    overlap_coefficient: float
    membership_ratio: float


class OrganizationSimilarityAnalyzer:
    def __init__(
        self, hierarchy1: OrganizationHierarchy, hierarchy2: OrganizationHierarchy
    ):
        self.hierarchy1 = hierarchy1
        self.hierarchy2 = hierarchy2

    def compute_similarities(self) -> pd.DataFrame:
        """Compute similarity metrics between two organization hierarchies."""
        intersection = self._generate_org_pairs()
        jaccard_df = self._merge_user_counts(intersection)
        return self._calculate_similarity_metrics(jaccard_df)

    def _generate_org_pairs(self) -> pd.DataFrame:
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
        intersection_size = df["intersection_size"].values
        num_users_df1 = df["num_users_df1"].values
        num_users_df2 = df["num_users_df2"].values

        metrics = self._compute_metrics_numpy(
            intersection_size, num_users_df1, num_users_df2
        )

        for metric_name, values in metrics.__dict__.items():
            df[metric_name] = values

        df["same_org_name"] = df[ORG_HIERARCHY_X] == df[ORG_HIERARCHY_Y]
        df["org_rank_df1"] = df[ORG_HIERARCHY_X].str.count("/") + 1
        df["org_rank_df2"] = df[ORG_HIERARCHY_Y].str.count("/") + 1
        df["rank_difference"] = (df["org_rank_df1"] - df["org_rank_df2"]).abs()

        return df

    def _merge_user_counts(self, intersection):
        """
        組織ペアごとの共通ユーザー数に、各組織の総ユーザー数を結合します。

        Parameters:
        - intersection: pandas.DataFrame - org_hierarchy_df1、org_hierarchy_df2、intersection_sizeを含むデータフレーム
        - aggregated_df1: pandas.DataFrame - org_full_name、user_set、num_usersを含むdf1の集計データフレーム
        - aggregated_df2: pandas.DataFrame - org_full_name、user_set、num_usersを含むdf2の集計データフレーム

        Returns:
        - jaccard_df: pandas.DataFrame - org_hierarchy_df1、org_hierarchy_df2、intersection_size、num_users_df1、num_users_df2を含むデータフレーム
        """

        jaccard_df = (
            intersection.merge(
                self.hierarchy1.aggregated_df[["org_full_name", "num_users"]],
                left_on=ORG_HIERARCHY_X,
                right_on="org_full_name",
                how="left",
            )
            .rename(columns={"num_users": "num_users_df1"})
            .drop(columns=["org_full_name"])
        )

        jaccard_df = (
            jaccard_df.merge(
                self.hierarchy2.aggregated_df[["org_full_name", "num_users"]],
                left_on=ORG_HIERARCHY_Y,
                right_on="org_full_name",
                how="left",
            )
            .rename(columns={"num_users": "num_users_df2"})
            .drop(columns=["org_full_name"])
        )

        return jaccard_df

    @staticmethod
    def _compute_metrics_numpy(
        intersection_size: np.ndarray,
        num_users_df1: np.ndarray,
        num_users_df2: np.ndarray,
    ) -> SimilarityMetrics:
        # ... (existing numpy calculation logic) ...
        pass
