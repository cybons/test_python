# rule_loader.py
"""
Excelファイルからフィルタリングルールを読み込むためのモジュール
"""

import pandas as pd
from typing import list
from .flexible_filter import FilterRule, RuleCondition

class RuleLoader:
    """
    Excelファイルからフィルタリングルールを読み込むクラス
    """
    
    def __init__(self, excel_path: str):
        """
        Parameters:
            excel_path: str - ルール定義が記載されたExcelファイルのパス
        """
        self.excel_path = excel_path
        self.rule_df = None
        self.condition_df = None
        
    def load_rules(self) -> list[FilterRule]:
        """
        Excelファイルからルールを読み込み、FilterRuleオブジェクトのリストを返す
        
        Returns:
            list[FilterRule] - ロードされたルールのリスト
        """
        # Ruleシートの読み込み
        self.rule_df = pd.read_excel(
            self.excel_path,
            sheet_name="Rules",
            dtype={
                "RuleID": str,
                "Name": str,
                "Description": str,
                "Action": str,
                "Enabled": bool
            }
        )
        
        # Conditionsシートの読み込み
        self.condition_df = pd.read_excel(
            self.excel_path,
            sheet_name="Conditions",
            dtype={
                "RuleID": str,
                "Field": str,
                "Operator": str,
                "Value": str,
                "SecondaryField": str
            }
        )
        
        # 有効なルールのみを処理
        active_rules = self.rule_df[self.rule_df["Enabled"]]
        
        return [self._create_rule(row) for _, row in active_rules.iterrows()]
    
    def _create_rule(self, rule_row: pd.Series) -> FilterRule:
        """
        ルール行からFilterRuleオブジェクトを作成
        
        Parameters:
            rule_row: pd.Series - Rulesシートの1行
        
        Returns:
            FilterRule - 作成されたルールオブジェクト
        """
        # ルールに関連する条件を取得
        rule_conditions = self.condition_df[
            self.condition_df["RuleID"] == rule_row["RuleID"]
        ]
        
        # 条件オブジェクトのリストを作成
        conditions = []
        for _, condition in rule_conditions.iterrows():
            # 値の変換（文字列で保存された値を適切な型に変換）
            value = self._convert_value(condition["Value"])
            
            # 条件オブジェクトの作成
            conditions.append(
                RuleCondition(
                    field=condition["Field"],
                    operator=condition["Operator"],
                    value=value,
                    secondary_field=condition["SecondaryField"]
                    if pd.notna(condition["SecondaryField"])
                    else None
                )
            )
        
        # FilterRuleオブジェクトの作成
        return FilterRule(
            rule_id=rule_row["RuleID"],
            name=rule_row["Name"],
            description=rule_row["Description"],
            conditions=conditions,
            action=rule_row["Action"]
        )
    
    def _convert_value(self, value_str: str) -> any:
        """
        文字列の値を適切な型に変換
        
        Parameters:
            value_str: str - 変換する値の文字列
        
        Returns:
            any - 変換された値
        """
        try:
            # リストの場合（[min, max]形式）
            if value_str.startswith("[") and value_str.endswith("]"):
                return eval(value_str)
            
            # 数値の場合
            if value_str.replace(".", "").isdigit():
                return float(value_str) if "." in value_str else int(value_str)
            
            # 真偽値の場合
            if value_str.lower() in ["true", "false"]:
                return value_str.lower() == "true"
            
            # その他の場合は文字列として返す
            return value_str
            
        except Exception as e:
            print(f"Warning: Error converting value '{value_str}': {e}")
            return value_str

# 使用例
if __name__ == "__main__":
    # ルールのロード
    loader = RuleLoader("organization_rules.xlsx")
    rules = loader.load_rules()
    
    # フィルターの初期化と実行
    from flexible_filter import FlexibleOrganizationFilter
    filter = FlexibleOrganizationFilter(similarity_df)
    
    # ロードしたルールを追加
    for rule in rules:
        filter.add_rule(rule)
    
    # フィルタリングの実行
    result_df = filter.apply_rules()