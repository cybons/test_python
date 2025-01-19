from dataclasses import dataclass
from typing import Optional

import pandas as pd

from .hierarchy import OrganizationHierarchy
from .similarity import OrganizationSimilarityAnalyzer


@dataclass
class UpdateResult:
    """組織更新の結果を保持するデータクラス"""

    renamed_orgs: dict[str, str]  # 名称変更された組織 {old_name: new_name}
    new_orgs: list[str]  # 新規追加された組織
    merged_orgs: dict[str, str]  # 統合された組織 {merged_org: target_org}


class OrganizationUpdateManager:
    """組織更新の一連の処理を管理するクラス"""

    def __init__(
        self,
        current_org_df: pd.DataFrame,
        new_org_df: pd.DataFrame,
        user_df: pd.DataFrame,
        engagement_flags: pd.DataFrame,
    ):
        """
        Parameters:
        - current_org_df: 現在の組織データ
        - new_org_df: 新規組織データ
        - user_df: ユーザーデータ
        - engagement_flags: Engagementユーザーフラグ
        """
        self.current_org_df = current_org_df
        self.new_org_df = new_org_df
        self.user_df = user_df
        self.engagement_flags = engagement_flags
        self.update_result: Optional[UpdateResult] = None

    def process_organization_update(self) -> UpdateResult:
        """組織更新の一連の処理を実行"""
        # フェーズ1: 組織構造の整理
        engagement_users = self._filter_engagement_users()
        similarity_result = self._analyze_organization_similarity(engagement_users)
        self.update_result = self._process_similarity_result(similarity_result)

        # フェーズ2: ユーザー管理
        updated_org_df = self._update_organization_master()
        admin_users = self._update_admin_users(updated_org_df)
        engagement_users = self._update_engagement_users(admin_users)

        # フェーズ3: 最終処理
        self._handle_small_organizations(engagement_users)
        final_org_df = self._finalize_organization_update()

        return self.update_result

    def _filter_engagement_users(self) -> pd.DataFrame:
        """Engagementユーザーのみを抽出"""
        return pd.merge(
            self.user_df,
            self.engagement_flags[self.engagement_flags["deliver_flag"]],
            on="user_code",
        )

    def _analyze_organization_similarity(self, engagement_users: pd.DataFrame):
        """組織の類似度分析を実行"""
        current_hierarchy = OrganizationHierarchy(
            engagement_users[
                engagement_users["org_id"].isin(self.current_org_df["org_id"])
            ]
        )
        new_hierarchy = OrganizationHierarchy(
            engagement_users[engagement_users["org_id"].isin(self.new_org_df["org_id"])]
        )

        analyzer = OrganizationSimilarityAnalyzer(current_hierarchy, new_hierarchy)
        return analyzer.compute_similarities()

    def _process_similarity_result(self, similarity_df: pd.DataFrame) -> UpdateResult:
        """類似度分析結果に基づいて組織の更新内容を決定"""
        renamed_orgs = {}
        new_orgs = []
        merged_orgs = {}

        # 高類似度の組織を名称変更対象として処理
        high_similarity = similarity_df[
            (similarity_df["jaccard_index"] >= 0.8)
            & (similarity_df["rank_difference"] == 0)
        ]
        for _, row in high_similarity.iterrows():
            renamed_orgs[row["org_hierarchy_x"]] = row["org_hierarchy_y"]

        # 新規組織の特定
        existing_orgs = set(renamed_orgs.values())
        new_orgs = [
            org for org in self.new_org_df["org_full_name"] if org not in existing_orgs
        ]

        return UpdateResult(renamed_orgs, new_orgs, merged_orgs)

    def _update_organization_master(self) -> pd.DataFrame:
        """組織マスタの更新"""
        if self.update_result is None:
            raise ValueError("組織更新結果が設定されていません")

        updated_df = self.current_org_df.copy()

        # 名称変更の適用
        for old_name, new_name in self.update_result.renamed_orgs.items():
            mask = updated_df["org_full_name"] == old_name
            updated_df.loc[mask, "org_full_name"] = new_name

        # 新規組織の追加
        new_orgs_df = self.new_org_df[
            self.new_org_df["org_full_name"].isin(self.update_result.new_orgs)
        ]
        updated_df = pd.concat([updated_df, new_orgs_df], ignore_index=True)

        return updated_df

    def _update_admin_users(self, org_df: pd.DataFrame) -> pd.DataFrame:
        """Admin Userの更新"""
        # ユーザーと組織の紐付けを更新
        admin_users = pd.merge(
            self.user_df, org_df[["org_id", "org_full_name"]], on="org_id", how="left"
        )
        return admin_users

    def _update_engagement_users(self, admin_users: pd.DataFrame) -> pd.DataFrame:
        """Engagementユーザーの更新"""
        # Engagementフラグに基づいてフィルタリング
        engagement_users = pd.merge(
            admin_users,
            self.engagement_flags[self.engagement_flags["deliver_flag"]],
            on="user_code",
        )
        return engagement_users

    def _handle_small_organizations(self, engagement_users: pd.DataFrame) -> None:
        """3名未満の組織の処理"""
        # 組織ごとのユーザー数を集計
        org_sizes = engagement_users.groupby("org_full_name").size()
        small_orgs = org_sizes[org_sizes < 3].index

        # 小規模組織の統合先を決定
        if not self.update_result:
            self.update_result = UpdateResult({}, [], {})

        for org in small_orgs:
            # 組織の階層構造から適切な統合先を決定
            parent_org = "/".join(org.split("/")[:-1])
            if parent_org and org_sizes.get(parent_org, 0) >= 3:
                self.update_result.merged_orgs[org] = parent_org

    def _finalize_organization_update(self) -> pd.DataFrame:
        """最終的な組織更新の適用"""
        if not self.update_result:
            raise ValueError("組織更新結果が設定されていません")

        final_df = self.current_org_df.copy()

        # 統合された組織の処理
        for merged_org, target_org in self.update_result.merged_orgs.items():
            # ユーザーの所属組織を更新
            mask = self.user_df["org_full_name"] == merged_org
            self.user_df.loc[mask, "org_full_name"] = target_org

            # 組織マスタから削除
            final_df = final_df[final_df["org_full_name"] != merged_org]

        return final_df
