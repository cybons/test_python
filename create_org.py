import logging
from dataclasses import dataclass
from typing import Dict, Optional

import pandas as pd

RANK_MAX = 7
COLUMN_RANK_CODE = "rank_code"  # rank_code1, rank_code2, ...
COLUMN_RANK_NAME = "rank_name"  # rank_name1, rank_name2, ...


@dataclass
class OrgNode:
    """組織ノードを表すデータクラス"""

    code: str
    name: str
    rank: Optional[int]
    parent_code: Optional[str]


class OrgTreeBuilder:
    """組織ツリーの構築と操作を行うクラス"""

    def __init__(self, df_org: pd.DataFrame):
        self.org_dict: Dict[str, OrgNode] = {}
        self.parent_child_dict: Dict[str, str] = {}
        self._build_org_structure(df_org)

    def _build_org_structure(self, df_org: pd.DataFrame) -> None:
        """組織構造の初期構築"""
        for _, row in df_org.iterrows():
            org_node = OrgNode(
                code=row["org_code"],
                name=row["org_name"],
                rank=row["rank"],
                parent_code=row["parent_org_code"]
                if pd.notna(row["parent_org_code"])
                else None,
            )

            self.org_dict[org_node.code] = org_node
            if org_node.parent_code:
                self.parent_child_dict[org_node.code] = org_node.parent_code

    def get_rank_info(self, org_code: str) -> Dict[str, Optional[str]]:
        """特定の組織コードに対するランク情報を取得"""
        rank_info = {}
        for i in range(1, RANK_MAX + 1):
            rank_info[f"{COLUMN_RANK_CODE}{i}"] = None
            rank_info[f"{COLUMN_RANK_NAME}{i}"] = None

        current_code = org_code
        visited = set()  # 循環参照防止

        while current_code and current_code not in visited:
            visited.add(current_code)
            current_org = self.org_dict.get(current_code)

            if not current_org:
                logging.error(f"組織コード '{current_code}' が存在しません。")
                break

            rank = current_org.rank
            if rank and 1 <= rank <= RANK_MAX:
                rank_info[f"{COLUMN_RANK_CODE}{rank}"] = current_code
                rank_info[f"{COLUMN_RANK_NAME}{rank}"] = current_org.name

            current_code = self.parent_child_dict.get(current_code)

        return rank_info


class RankProcessor:
    """ランク情報の処理を行うクラス"""

    @staticmethod
    def calculate_rank_data(
        df_org: pd.DataFrame, org_tree: OrgTreeBuilder
    ) -> pd.DataFrame:
        """組織全体のランク情報を計算"""
        logging.info("ランク情報を計算中...")
        rank_data = []
        for org_code in df_org["org_code"]:
            rank_info = org_tree.get_rank_info(org_code)
            rank_data.append(rank_info)

        return pd.DataFrame(rank_data)

    @staticmethod
    def fill_missing_ranks(df: pd.DataFrame, other_label: str) -> pd.DataFrame:
        """欠損しているランクを「その他」で埋める"""
        df = df.copy()

        for i in range(RANK_MAX, 0, -1):
            current_rank_name = f"{COLUMN_RANK_NAME}{i}"
            mask_missing = df[current_rank_name].isna()

            if i < RANK_MAX:
                lower_rank_name = f"{COLUMN_RANK_NAME}{i+1}"
                mask_insert_other = df[lower_rank_name].notna() & mask_missing
            else:
                mask_insert_other = mask_missing

            df.loc[mask_insert_other, current_rank_name] = other_label

        return df


def generate_org_column(input_file: str, other_label: str) -> pd.DataFrame:
    """メイン処理を実行する関数"""
    # CSVファイルの読み込み
    df_org = pd.read_csv(input_file)

    # 組織ツリーの構築
    org_tree = OrgTreeBuilder(df_org)

    # ランク情報の計算
    rank_processor = RankProcessor()
    df_rank = rank_processor.calculate_rank_data(df_org, org_tree)

    # データの結合
    df_org_with_rank = pd.concat([df_org, df_rank], axis=1)

    # 欠損ランクの処理
    df_final = rank_processor.fill_missing_ranks(df_org_with_rank, other_label)

    return df_final


# 使用例
if __name__ == "__main__":
    result_df = generate_org_column(
        input_file="organizations.csv", other_label="その他"
    )
