# flexible_filter.py
"""
組織の類似度判定を行うためのフィルタリングモジュール。
フラグの管理と処理順序を明確にした実装です。
"""

from dataclasses import dataclass
from typing import Callable, list
import pandas as pd

@dataclass
class RuleCondition:
    """フィルタリングルールの個別条件を表すデータクラス"""
    field: str
    operator: str
    value: any
    secondary_field: str | None = None

@dataclass
class FilterRule:
    """フィルタリングルールを表すデータクラス"""
    rule_id: str
    name: str
    description: str
    conditions: list[RuleCondition]
    action: str
    priority: int  # ルールの優先順位（低い数字が高優先）

class FlexibleOrganizationFilter:
    """
    組織の類似度を判定する柔軟なフィルタリングクラス
    
    フラグの説明：
    - is_similar: 組織の類似性が確認されたペア
    - is_excluded: 評価対象から除外するペア（同一組織の他の組み合わせなど）
    - needs_review: 自動判定できずレビューが必要なペア
    """
    
    def __init__(self, similarity_df: pd.DataFrame):
        self.df = similarity_df.copy()
        self.rules: list[FilterRule] = []
        self._initialize_operators()
        self._initialize_fields()
        
    def add_rule(self, rule: FilterRule):
        """ルールを追加し、優先順位でソート"""
        self.rules.append(rule)
        self.rules.sort(key=lambda x: x.priority)  # 優先順位でソート
    
    def apply_rules(self) -> pd.DataFrame:
        """
        すべてのルールを適用してフィルタリングを実行
        
        処理順序：
        1. 基本的なフィルタリング（ユーザー数3人未満の除外など）
        2. 優先順位順にルールを適用
        3. 類似組織の他の組み合わせを除外
        4. needs_reviewフラグの設定
        
        Returns:
            pd.DataFrame - フィルタリング結果を含むDataFrame
        """
        # フラグの初期化
        self.df["is_similar"] = False
        self.df["is_excluded"] = False
        self.df["needs_review"] = False
        self.df["matched_rules"] = ""
        
        # 基本的なフィルタリング
        self._apply_basic_filters()
        
        # ルールの適用（優先順位順）
        filtered_df = self.df[~self.df["is_excluded"]].copy()
        for rule in self.rules:
            self._apply_single_rule(filtered_df, rule)
            # 類似組織が見つかった場合、その組織の他の組み合わせを除外
            if rule.action == "mark_similar":
                self._exclude_related_pairs()
            # フィルタリング対象を更新
            filtered_df = self.df[
                ~self.df["is_excluded"] & ~self.df["is_similar"]
            ].copy()
        
        # needs_reviewフラグの設定
        # - is_excludedでなく
        # - is_similarでもない組織ペアがレビュー対象
        self.df["needs_review"] = (
            ~self.df["is_excluded"] & ~self.df["is_similar"]
        )
        
        return self.df
    
    def _apply_basic_filters(self):
        """基本的なフィルタリングルールの適用"""
        # 最小ユーザー数のチェック
        min_users_mask = (
            (self.df["num_users_df1"] < 3) | (self.df["num_users_df2"] < 3)
        )
        self.df.loc[min_users_mask, "is_excluded"] = True
    
    def _apply_single_rule(self, filtered_df: pd.DataFrame, rule: FilterRule):
        """単一のルールを適用"""
        for _, row in filtered_df.iterrows():
            if self._evaluate_rule(row, rule):
                if rule.action == "mark_similar":
                    self.df.at[_, "is_similar"] = True
                    # マッチしたルールを記録
                    current_rules = self.df.at[_, "matched_rules"]
                    self.df.at[_, "matched_rules"] = (
                        f"{current_rules},{rule.rule_id}"
                        if current_rules
                        else rule.rule_id
                    )
                elif rule.action == "exclude":
                    self.df.at[_, "is_excluded"] = True
    
    def _exclude_related_pairs(self):
        """
        類似組織として判定されたペアに関連する他の組み合わせを除外
        
        例：A-B が類似組織と判定された場合
        - A-C, A-D など、Aが含まれる他のペア
        - B-C, B-D など、Bが含まれる他のペア
        をis_excluded=Trueに設定
        """
        # 類似組織として判定されたペアを取得
        similar_pairs = self.df[self.df["is_similar"]]
        
        for _, row in similar_pairs.iterrows():
            # 組織Xに関連する他のペアを除外
            org_x_mask = (
                (self.df["org_hierarchy_x"] == row["org_hierarchy_x"])
                | (self.df["org_hierarchy_y"] == row["org_hierarchy_x"])
            )
            # 組織Yに関連する他のペアを除外
            org_y_mask = (
                (self.df["org_hierarchy_x"] == row["org_hierarchy_y"])
                | (self.df["org_hierarchy_y"] == row["org_hierarchy_y"])
            )
            
            # 既に類似判定されているペアは除外対象から除く
            exclude_mask = (
                (org_x_mask | org_y_mask)
                & ~self.df["is_similar"]
            )
            
            self.df.loc[exclude_mask, "is_excluded"] = True
    
    # その他のメソッド（_initialize_operators, _initialize_fields, _evaluate_condition, _evaluate_rule）は
    # 前回のコードと同じため省略

# 使用例
def create_sample_rules() -> list[FilterRule]:
    """優先順位付きのサンプルルールを作成"""
    rules = [
        FilterRule(
            rule_id="RULE1",
            name="小規模組織の移動",
            description="ユーザー数3-5人の小規模組織の移動ルール",
            conditions=[
                RuleCondition("num_users_df1", "between", [3, 5]),
                RuleCondition("num_users_df2", "between", [3, 5]),
                RuleCondition("intersection_size", ">=", 3),
                RuleCondition("group_movement_rate", ">=", 50),
                RuleCondition("rank_distance", "==", 0),
            ],
            action="mark_similar",
            priority=1  # 最優先
        ),
        FilterRule(
            rule_id="RULE2",
            name="大規模な移動",
            description="70%以上のメンバーが移動するケース",
            conditions=[
                RuleCondition("num_users_df1", ">=", 3),
                RuleCondition("num_users_df2", ">=", 3),
                RuleCondition("movement_rate", ">=", 70),
                RuleCondition("group_movement_rate", ">=", 50),
                RuleCondition("intersection_size", ">=", 3),
                RuleCondition("rank_distance", "==", 0),
            ],
            action="mark_similar",
            priority=2
        ),
        # 他のルールも同様に定義可能
    ]
    return rules