# flexible_filter.py
"""
組織の類似度判定を行うためのフィルタリングモジュール。
条件評価をベクトル化して高速化しています。
"""

from dataclasses import dataclass

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
    """組織の類似度を判定する柔軟なフィルタリングクラス（ベクトル化版）"""

    def __init__(self, similarity_df: pd.DataFrame):
        self.df = similarity_df.copy()
        self.rules: list[FilterRule] = []
        self._initialize_operators()

    def _initialize_operators(self):
        """演算子とその実装を初期化（ベクトル化対応）"""
        self.operators = {
            ">=": lambda x, y: x >= y,
            ">": lambda x, y: x > y,
            "<=": lambda x, y: x <= y,
            "<": lambda x, y: x < y,
            "==": lambda x, y: x == y,
            "!=": lambda x, y: x != y,
            "in": lambda x, y: x.isin(y),
            "between": lambda x, y: (x >= y[0]) & (x <= y[1]),
        }

    def _calculate_ratio_gte_vectorized(
        self, values: pd.Series, threshold: float, secondary_values: pd.Series = None
    ) -> pd.Series:
        """比率計算のベクトル化版"""
        if secondary_values is None or (secondary_values == 0).all():
            return pd.Series(False, index=values.index)
        return (values / secondary_values) >= threshold

    def _evaluate_condition_vectorized(
        self, filtered_df: pd.DataFrame, condition: RuleCondition
    ) -> pd.Series:
        """
        条件評価のベクトル化版

        Parameters:
            filtered_df: pd.DataFrame - フィルタリング対象のDataFrame
            condition: RuleCondition - 評価する条件

        Returns:
            pd.Series - 条件を満たすかどうかのブール値シリーズ
        """
        # OrganizationSimilarityAnalyzerで計算済みの値を使用
        field_values = filtered_df[condition.field]

        operator_func = self.operators[condition.operator]
        return operator_func(field_values, condition.value)

    def _evaluate_rule_vectorized(
        self, filtered_df: pd.DataFrame, rule: FilterRule
    ) -> pd.Series:
        """
        ルール評価のベクトル化版

        Parameters:
            filtered_df: pd.DataFrame - フィルタリング対象のDataFrame
            rule: FilterRule - 評価するルール

        Returns:
            pd.Series - ルールを満たすかどうかのブール値シリーズ
        """
        # 全ての条件をベクトル化して評価
        condition_results = [
            self._evaluate_condition_vectorized(filtered_df, condition)
            for condition in rule.conditions
        ]

        # 全ての条件をAND結合
        return pd.concat(condition_results, axis=1).all(axis=1)

    def _apply_single_rule(self, filtered_df: pd.DataFrame, rule: FilterRule):
        """ルール適用のベクトル化版"""
        # ルールの条件を一括評価
        rule_mask = self._evaluate_rule_vectorized(filtered_df, rule)

        # マッチした行のインデックスを取得
        matched_indices = filtered_df.index[rule_mask]

        if not matched_indices.empty:
            if rule.action == "mark_similar":
                # is_similarフラグを一括設定
                self.df.loc[matched_indices, "is_similar"] = True

                # matched_rulesの更新（これは各行個別の処理が必要）
                for idx in matched_indices:
                    current_rules = self.df.at[idx, "matched_rules"]
                    self.df.at[idx, "matched_rules"] = (
                        f"{current_rules},{rule.rule_id}"
                        if current_rules
                        else rule.rule_id
                    )

            elif rule.action == "exclude":
                # is_excludedフラグを一括設定
                self.df.loc[matched_indices, "is_excluded"] = True

    def _exclude_related_pairs_vectorized(self):
        """関連ペアの除外処理のベクトル化版"""
        # 類似組織として判定されたペアを取得
        similar_pairs = self.df[self.df["is_similar"]]

        if not similar_pairs.empty:
            # 全ての類似ペアに関連する組織のマスクを作成
            org_x_mask = self.df["org_hierarchy_x"].isin(
                similar_pairs["org_hierarchy_x"]
            ) | self.df["org_hierarchy_x"].isin(similar_pairs["org_hierarchy_y"])
            org_y_mask = self.df["org_hierarchy_y"].isin(
                similar_pairs["org_hierarchy_x"]
            ) | self.df["org_hierarchy_y"].isin(similar_pairs["org_hierarchy_y"])

            # 除外対象のマスク作成（既に類似判定されているペアは除く）
            exclude_mask = (org_x_mask | org_y_mask) & ~self.df["is_similar"]

            # 一括で除外フラグを設定
            self.df.loc[exclude_mask, "is_excluded"] = True

    def _evaluate_condition(self, row: pd.Series, condition: RuleCondition) -> bool:
        """
        単一の条件を評価

        Parameters:
            row: pd.Series - データフレームの1行
            condition: RuleCondition - 評価する条件
        """
        # OrganizationSimilarityAnalyzerで計算済みの値を使用
        field_value = row[condition.field]

        # 演算子による評価
        operator_func = self.operators[condition.operator]
        if condition.secondary_field:
            secondary_value = row[condition.secondary_field]
            return operator_func(field_value, condition.value, secondary_value)
        else:
            return operator_func(field_value, condition.value)

    def _evaluate_rule(self, row: pd.Series, rule: FilterRule) -> bool:
        """
        ルールのすべての条件を評価

        Parameters:
            row: pd.Series - データフレームの1行
            rule: FilterRule - 評価するルール
        """
        return all(
            self._evaluate_condition(row, condition) for condition in rule.conditions
        )

    def apply_rules(self) -> pd.DataFrame:
        """ルール適用メソッドはほぼ同じ（_exclude_related_pairs を _exclude_related_pairs_vectorized に変更）"""
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
            if rule.action == "mark_similar":
                self._exclude_related_pairs_vectorized()
            filtered_df = self.df[
                ~self.df["is_excluded"] & ~self.df["is_similar"]
            ].copy()

        # needs_reviewフラグの一括設定
        self.df["needs_review"] = ~self.df["is_excluded"] & ~self.df["is_similar"]

        return self.df

    def _apply_basic_filters(self):
        """基本的なフィルタリングルールの適用"""
        # 最小ユーザー数のチェック
        min_users_mask = (self.df["num_users_df1"] < 3) | (self.df["num_users_df2"] < 3)
        self.df.loc[min_users_mask, "is_excluded"] = True
        
        
 
def _exclude_by_rank_difference(self):
    """
    ランク差と類似度に基づいて、不要な組織ペアを除外
    
    除外ロジック:
    1. ランク0（同階層）の組織ペアで高類似度のものがある場合:
       - より高いランク差の組織ペアを除外
    2. ランク0の組織ペアがない、または類似度が低い場合:
       - ランク1の組織ペアも検討対象として残す
    3. すべてのランクで類似度が低い場合:
       - ランク差が大きすぎる組織ペアを除外
    """
    # 既に除外またはsimilarとマークされていないペアのみを対象
    target_pairs = self.df[~self.df["is_excluded"] & ~self.df["is_similar"]].copy()
    
    # ランク差ごとに類似度の最大値を確認
    rank_stats = target_pairs.groupby("rank_difference_abs").agg({
        "jaccard_index": ["max", "mean"],
        "cosine_similarity": ["max", "mean"]
    }).round(3)
    
    # ランク0の組織ペアの存在と類似度を確認
    rank0_pairs = target_pairs[target_pairs["rank_difference_abs"] == 0]
    has_high_similarity_rank0 = False
    
    if not rank0_pairs.empty:
        # ランク0での高類似度ペアの確認
        rank0_high_similarity = rank0_pairs[
            (rank0_pairs["jaccard_index"] >= 0.4) |
            (rank0_pairs["cosine_similarity"] >= 0.5)
        ]
        has_high_similarity_rank0 = not rank0_high_similarity.empty
    
    # 除外マスクの作成
    exclude_mask = pd.Series(False, index=self.df.index)
    
    if has_high_similarity_rank0:
        # ランク0に高類似度ペアがある場合、ランク差2以上を除外
        exclude_mask |= (self.df["rank_difference_abs"] >= 2)
    else:
        # ランク0に高類似度ペアがない場合の処理
        rank1_pairs = target_pairs[target_pairs["rank_difference_abs"] == 1]
        
        if not rank1_pairs.empty:
            rank1_high_similarity = rank1_pairs[
                (rank1_pairs["jaccard_index"] >= 0.3) |
                (rank1_pairs["cosine_similarity"] >= 0.4)
            ]
            
            if not rank1_high_similarity.empty:
                # ランク1に高類似度ペアがある場合、ランク差3以上を除外
                exclude_mask |= (self.df["rank_difference_abs"] >= 3)
            else:
                # すべてのランクで類似度が低い場合、ランク差4以上を除外
                exclude_mask |= (self.df["rank_difference_abs"] >= 4)
    
    # 極端に類似度が低いペアの除外
    exclude_mask |= (
        (self.df["jaccard_index"] < 0.1) &
        (self.df["cosine_similarity"] < 0.15) &
        (self.df["rank_difference_abs"] > 0)  # ランク0は除外しない
    )
    
    # 除外フラグの設定
    self.df.loc[exclude_mask & ~self.df["is_similar"], "is_excluded"] = True