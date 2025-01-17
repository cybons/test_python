# flexible_filter.py
"""
組織の類似度判定を行うためのフィルタリングモジュール。
複雑な条件の組み合わせと、時系列データの比較に対応します。
"""

from dataclasses import dataclass
from typing import Callable, list
import pandas as pd

@dataclass
class RuleCondition:
    """
    フィルタリングルールの個別条件を表すデータクラス
    
    Attributes:
        field: str - 判定対象のフィールド名
        operator: str - 演算子
        value: any - 比較値
        secondary_field: str | None - 比較対象の2つ目のフィールド（移動率などの計算時に使用）
    """
    field: str
    operator: str
    value: any
    secondary_field: str | None = None

@dataclass
class FilterRule:
    """
    フィルタリングルールを表すデータクラス
    
    Attributes:
        rule_id: str - ルールの一意識別子
        name: str - ルールの名前
        description: str - ルールの説明
        conditions: list[RuleCondition] - 条件のリスト
        action: str - ルールが適用された時のアクション（"mark_similar" | "exclude" など）
    """
    rule_id: str
    name: str
    description: str
    conditions: list[RuleCondition]
    action: str

class FlexibleOrganizationFilter:
    """
    組織の類似度を判定する柔軟なフィルタリングクラス
    """
    
    def __init__(self, similarity_df: pd.DataFrame):
        """
        Parameters:
            similarity_df: pd.DataFrame - 類似度計算結果のDataFrame
        """
        self.df = similarity_df.copy()
        self.rules: list[FilterRule] = []
        self._initialize_operators()
        self._initialize_fields()
        
    def _initialize_operators(self):
        """演算子とその実装を初期化"""
        self.operators = {
            ">=": lambda x, y: x >= y,
            ">": lambda x, y: x > y,
            "<=": lambda x, y: x <= y,
            "<": lambda x, y: x < y,
            "==": lambda x, y: x == y,
            "!=": lambda x, y: x != y,
            "in": lambda x, y: x in y,
            "between": lambda x, y: y[0] <= x <= y[1],
            "ratio_gte": self._calculate_ratio_gte,
        }
        
    def _initialize_fields(self):
        """計算フィールドの定義を初期化"""
        self.field_calculators = {
            "movement_rate": self._calculate_movement_rate,
            "group_movement_rate": self._calculate_group_movement_rate,
            "rank_distance": self._calculate_rank_distance,
        }
    
    def add_rule(self, rule: FilterRule):
        """
        フィルタリングルールを追加
        
        Parameters:
            rule: FilterRule - 追加するルール
        """
        self.rules.append(rule)
    
    def _calculate_ratio_gte(self, value: float, threshold: float, secondary_value: float = None) -> bool:
        """
        比率が閾値以上かどうかを判定
        
        Parameters:
            value: float - 分子となる値
            threshold: float - 閾値
            secondary_value: float - 分母となる値
        """
        if secondary_value is None or secondary_value == 0:
            return False
        return (value / secondary_value) >= threshold
    
    def _calculate_movement_rate(self, row: pd.Series) -> float:
        """
        メンバーの移動率を計算
        
        Parameters:
            row: pd.Series - データフレームの1行
        """
        return row["intersection_size"] / row["num_users_df1"] * 100
    
    def _calculate_group_movement_rate(self, row: pd.Series) -> float:
        """
        グループ内の移動率を計算
        
        Parameters:
            row: pd.Series - データフレームの1行
        """
        total_users = (row["num_users_df1"] + row["num_users_df2"]) / 2
        return row["intersection_size"] / total_users * 100 if total_users > 0 else 0
    
    def _calculate_rank_distance(self, row: pd.Series) -> int:
        """
        組織ランクの距離を計算
        
        Parameters:
            row: pd.Series - データフレームの1行
        """
        return abs(row["org_rank_df1"] - row["org_rank_df2"])
    
    def _evaluate_condition(self, row: pd.Series, condition: RuleCondition) -> bool:
        """
        単一の条件を評価
        
        Parameters:
            row: pd.Series - データフレームの1行
            condition: RuleCondition - 評価する条件
        """
        # 計算フィールドの処理
        if condition.field in self.field_calculators:
            field_value = self.field_calculators[condition.field](row)
        else:
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
        return all(self._evaluate_condition(row, condition) for condition in rule.conditions)
    
    def apply_rules(self) -> pd.DataFrame:
        """
        すべてのルールを適用してフィルタリングを実行
        
        Returns:
            pd.DataFrame - フィルタリング結果を含むDataFrame
        """
        # 結果格納用の列を初期化
        self.df["is_similar"] = False
        self.df["matched_rules"] = ""
        self.df["is_excluded"] = False
        
        # 各行に対してすべてのルールを評価
        for _, row in self.df.iterrows():
            for rule in self.rules:
                if self._evaluate_rule(row, rule):
                    if rule.action == "mark_similar":
                        self.df.at[_, "is_similar"] = True
                        self.df.at[_, "matched_rules"] = (
                            f"{self.df.at[_, 'matched_rules']},{rule.rule_id}" 
                            if self.df.at[_, "matched_rules"] 
                            else rule.rule_id
                        )
                    elif rule.action == "exclude":
                        self.df.at[_, "is_excluded"] = True
                        
        return self.df

# 使用例
def create_sample_rules() -> list[FilterRule]:
    """サンプルルールを作成"""
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
            action="mark_similar"
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
            action="mark_similar"
        ),
        # 他のルールも同様に定義可能
    ]
    return rules

if __name__ == "__main__":
    # サンプルデータの作成
    data = {
        "org_hierarchy_x": ["A", "B", "C"],
        "org_hierarchy_y": ["A'", "B'", "C'"],
        "num_users_df1": [4, 10, 2],
        "num_users_df2": [4, 8, 2],
        "intersection_size": [3, 7, 2],
        "org_rank_df1": [2, 3, 1],
        "org_rank_df2": [2, 3, 1],
    }
    
    df = pd.DataFrame(data)
    
    # フィルターの初期化と実行
    filter = FlexibleOrganizationFilter(df)
    for rule in create_sample_rules():
        filter.add_rule(rule)
    
    result_df = filter.apply_rules()
    print(result_df)