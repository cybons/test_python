import logging
import unicodedata

import networkx as nx
import pandas as pd

# ログの設定
logging.basicConfig(level=logging.INFO)


def normalize_org_name(name):
    """
    組織名を正規化（NFKC形式に変換し、小文字に統一）。
    """
    if pd.isna(name):
        return ""
    name = unicodedata.normalize("NFKC", name)
    name = name.lower()
    return name


# CSVファイルの読み込み（ファイル名は適宜変更してください）
df_org = pd.read_csv("organizations.csv")

# 正規化された組織名を格納するリストを初期化
normalized_names = []

# 有向グラフの作成
G = nx.DiGraph()

# ノードとエッジの追加（itertuplesを使用）
logging.info("グラフの構築を開始します...")
for row in df_org.itertuples(index=False):
    org_code = row.org_code
    org_name = row.org_name
    parent_code = row.parent_org_code
    rank = row.rank

    # 組織名の正規化
    normalized_name = normalize_org_name(org_name)
    normalized_names.append(normalized_name)

    # ノードの追加
    G.add_node(org_code, name=org_name, rank=rank, normalized_name=normalized_name)

    # エッジの追加（親組織が存在する場合）
    if pd.notna(parent_code):
        if parent_code not in G:
            message = f"親組織コード '{parent_code}' がグラフに存在しません。ノードを追加します。"
            logging.warning(message)
            G.add_node(parent_code, name="Unknown", rank=None, normalized_name="")
        G.add_edge(parent_code, org_code)

# 正規化された組織名をデータフレームに追加
df_org["normalized_org_name"] = normalized_names

# 各ノードの全親リストを事前に計算
logging.info("各ノードの全親リストを計算中...")
all_parents = {node: list(nx.ancestors(G, node)) for node in G.nodes()}


def get_rank_info_optimized(org_code, all_parents, G, max_rank=7):
    """
    指定された org_code に対して、ランク1から max_rank までの上位組織のコードと名前を取得します。

    Args:
        org_code (str): 組織コード
        all_parents (dict): 各ノードの全親リスト
        G (networkx.DiGraph): 組織の有向グラフ
        max_rank (int): 最大ランク数

    Returns:
        dict: ランクごとのコードと名前を含む辞書
    """
    rank_info = {f"rank{i}_code": None for i in range(1, max_rank + 1)}
    rank_info.update({f"rank{i}_name": None for i in range(1, max_rank + 1)})

    # リンクリスト（自分自身 + 全親）
    lineage = [org_code] + all_parents.get(org_code, [])

    for node in lineage:
        node_data = G.nodes.get(node, {})
        rank = node_data.get("rank")
        name = node_data.get("name")
        if rank and 1 <= rank <= max_rank:
            # 既にランクが設定されている場合はスキップ
            if rank_info.get(f"rank{rank}_code") is None:
                rank_info[f"rank{rank}_code"] = node
                rank_info[f"rank{rank}_name"] = name
        # すべてのランクが埋まったら終了
        if all(rank_info[f"rank{i}_code"] is not None for i in range(1, max_rank + 1)):
            break

    return rank_info


# ランク情報を計算
logging.info("ランク情報を計算中...")
rank_data = df_org["org_code"].apply(
    lambda x: pd.Series(get_rank_info_optimized(x, all_parents, G))
)

# 列名の設定
rank_columns = [f"rank{i}_code" for i in range(1, 8)] + [
    f"rank{i}_name" for i in range(1, 8)
]
rank_data.columns = rank_columns

# 元のデータフレームにランク情報を統合
df_org_with_rank = pd.concat([df_org, rank_data], axis=1)


# ルートノードの取得（入次数が0のノード）
def get_root_nodes(G):
    """
    有向グラフ G におけるルートノード（入次数が0のノード）を取得します。

    Args:
        G (networkx.DiGraph): 組織の有向グラフ

    Returns:
        list: ルートノードの組織コードのリスト
    """
    roots = [node for node, in_degree in G.in_degree() if in_degree == 0]
    return roots


# ルート一覧の取得と保存
root_nodes = get_root_nodes(G)
logging.info(f"ルートノードの一覧: {root_nodes}")

df_roots = df_org_with_rank[df_org_with_rank["org_code"].isin(root_nodes)]
print("ルートノードの詳細情報:")
print(df_roots)

df_roots.to_csv("root_organizations.csv", index=False)
logging.info("ルートノードの情報を 'root_organizations.csv' に保存しました。")


# 指定した組織の配下組織を取得する関数
def get_all_sub_organizations(G, org_code):
    """
    指定された組織コードに対して、配下のすべての組織を取得します。

    Args:
        G (networkx.DiGraph): 組織の有向グラフ
        org_code (str): 組織コード

    Returns:
        list: 配下の組織コードのリスト
    """
    if org_code not in G:
        logging.error(f"組織コード '{org_code}' がグラフに存在しません。")
        return []

    # NetworkX の descendants 関数を使用してすべての子孫を取得
    sub_orgs = list(nx.descendants(G, org_code))
    return sub_orgs


# 使用例
specified_org_code = "ORG001"  # 例として組織コード 'ORG001' を指定
sub_org_codes = get_all_sub_organizations(G, specified_org_code)
logging.info(f"組織コード '{specified_org_code}' の配下組織: {sub_org_codes}")

# 配下組織の詳細情報をデータフレームとして表示
df_sub_orgs = df_org_with_rank[df_org_with_rank["org_code"].isin(sub_org_codes)]
print(f"組織コード '{specified_org_code}' の配下組織の詳細情報:")
print(df_sub_orgs)

# 必要に応じて配下組織情報をCSVに保存
output_filename = f"sub_organizations_of_{specified_org_code}.csv"
df_sub_orgs.to_csv(output_filename, index=False)
logging.info(f"配下組織の情報を '{output_filename}' に保存しました。")

# 結果の確認
print(df_org_with_rank.head())

# 必要に応じてCSVに保存
df_org_with_rank.to_csv("organizations_with_rank.csv", index=False)

logging.info("処理が完了しました。'organizations_with_rank.csv' に結果を保存しました。")
