import pandas as pd

from .constants import ORG_FULL_NAME


class OrganizationHierarchy:
    """
    組織階層情報を管理し、ユーザーと組織の関係を処理するクラス。
    """

    def __init__(self, df: pd.DataFrame, org_col: str = ORG_FULL_NAME):
        """
        組織階層のデータフレームを初期化します。

        Parameters:
        - df: pandas.DataFrame - ユーザーと組織情報が含まれるデータフレーム
        - org_col: str - 組織名を含む列の名前
        """
        self.df = df
        self.org_col = org_col
        self.exploded_df = None
        self.aggregated_df = None

    def process(self) -> None:
        """組織階層データを処理し、エクスプロードおよび集計を実行します。"""

        self.exploded_df = self._explode_hierarchical_orgs()
        self.aggregated_df = self._aggregate_users_per_org()
        self._assign_rank_to_organizations()

    def _explode_hierarchical_orgs(self) -> pd.DataFrame:
        """
        組織名を階層ごとに分割し、エクスプロードされたデータフレームを返します。

        Returns:
        - exploded_df: pandas.DataFrame - エクスプロードされたデータフレーム
        """

        org_hierarchy_series = (
            self.df[self.org_col]
            .str.split("/")
            .apply(
                lambda parts: ["/".join(parts[:i]) for i in range(1, len(parts) + 1)]
            )
        )
        exploded_df = self.df.assign(org_hierarchy=org_hierarchy_series).explode(
            "org_hierarchy"
        )
        return exploded_df[["user_code", "org_hierarchy"]]

    def _aggregate_users_per_org(self) -> pd.DataFrame:
        """
        エクスプロードされたデータフレームを基に、組織ごとにユーザーを集計します。

        Returns:
        - org_to_users: pandas.DataFrame - ORG_FULL_NAME、user_set、num_usersを含むデータフレーム
        """

        if self.exploded_df is None:
            raise ValueError("Must call process() first")

        org_to_users = (
            self.exploded_df.groupby("org_hierarchy")["user_code"]
            .agg(set)
            .reset_index()
        )
        org_to_users.rename(
            columns={"org_hierarchy": ORG_FULL_NAME, "user_code": "user_set"},
            inplace=True,
        )
        org_to_users["num_users"] = org_to_users["user_set"].str.len()
        return org_to_users

    def _assign_rank_to_organizations(self) -> None:
        """
        各組織にランク情報を付与します。ランクは組織階層の深さに基づきます。
        """
        if self.aggregated_df is None:
            raise ValueError("Must call process() first")

        # 組織名に含まれる "/" の数に基づいてランクを計算（ルートがランク1）
        self.aggregated_df["org_rank"] = (
            self.aggregated_df[ORG_FULL_NAME].str.count("/") + 1
        )
