from dataclasses import dataclass
from typing import Set

import pandas as pd
from constants import ORG_FULL_NAME


@dataclass
class OrganizationNode:
    full_name: str
    user_set: Set[str]
    num_users: int

    @property
    def hierarchy_level(self) -> int:
        return self.full_name.count("/") + 1


class OrganizationHierarchy:
    def __init__(self, df: pd.DataFrame, org_col: str = "group_full_name"):
        self.df = df
        self.org_col = org_col
        self.exploded_df = None
        self.aggregated_df = None

    def process(self) -> None:
        """Process the organization hierarchy data."""
        self.exploded_df = self._explode_hierarchical_orgs()
        self.aggregated_df = self._aggregate_users_per_org()

    def _explode_hierarchical_orgs(self) -> pd.DataFrame:
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
