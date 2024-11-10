import unicodedata
from logging import getLogger

import networkx as nx
import pandas as pd

# ロギングの設定
logger = getLogger(__name__)


def normalize_org_name(name):
    """
    組織名を正規化（NFKC形式に変換し、小文字に統一）。
    """
    if pd.isna(name):
        return ""
    name = unicodedata.normalize("NFKC", name)
    name = name.lower()
    return name


def build_tree(df) -> nx.DiGraph:
    """
    データフレームからNetworkXの有向グラフ（ツリー）を構築。
    """
    G = nx.DiGraph()
    for _, row in df.iterrows():
        G.add_node(row["org_code"], name=row["org_name"], rank=row["rank"])
        if pd.notna(row["parent_code"]):
            G.add_edge(row["parent_code"], row["org_code"])

    # 循環チェック
    if not nx.is_directed_acyclic_graph(G):
        raise ValueError("グラフに循環が検出されました。ツリー構造に矛盾があります。")

    return G


def get_sorted_ancestors(G, org_code) -> list[str | None]:
    """
    指定された org_code のトポロジカルソートされた祖先リストを取得します（org_code は含まない）。

    Args:
        G (networkx.DiGraph): 有向グラフ
        org_code (str): 組織コード

    Returns:
        list[str]: トポロジカルソートされた祖先リスト
    """
    try:
        # 祖先ノードの取得
        ancestors = nx.ancestors(G, org_code)

        # サブグラフの作成
        subgraph = G.subgraph(ancestors)

        # トポロジカルソート
        sorted_ancestors = list(nx.topological_sort(subgraph))

        return sorted_ancestors

    except nx.NetworkXUnfeasible:
        logger.error("グラフにサイクルが存在します。トポロジカルソートができません。")
        return []
    except KeyError:
        logger.error(f"指定された組織コード '{org_code}' がグラフに存在しません。")
        return []


def assign_rank_columns(df, G):
    """
    ツリー構造に基づき、ランクごとのコードと名前の列を割り当てる。

    Parameters:
        df (pd.DataFrame): 組織データを含むデータフレーム。
        G (networkx.DiGraph): 組織ツリーを表す有向グラフ。


    Returns:
        pd.DataFrame: ランクごとの列が追加されたデータフレーム。
    """

    rank_levels = df["rank"].max()

    # ランクごとのコードと名前の列を初期化
    rank_code_cols = [f"rank{i}_code" for i in range(1, rank_levels + 1)]
    rank_name_cols = [f"rank{i}_name" for i in range(1, rank_levels + 1)]
    for col in rank_code_cols + rank_name_cols:
        df[col] = None

    cache_rank_dict = {}

    def assign_ranks(row):
        org_code = row["org_code"]
        rank_dict = {col: None for col in rank_code_cols + rank_name_cols}

        # 祖先ノードを取得（org_code 自身は含まない）
        ancestors = get_sorted_ancestors(G, org_code)

        # org_code 自身をパスに追加
        full_path = ancestors + [org_code]

        # ルートから org_code までのパスを順に処理
        for ancestor_code in full_path:
            if ancestor_code in cache_rank_dict:
                # キャッシュが存在する場合、キャッシュを使用
                ancestor_rank_dict = cache_rank_dict[ancestor_code]
            else:
                node = G.nodes[ancestor_code]
                rank = node.get("rank")
                if rank is None or not (1 <= rank <= rank_levels):
                    raise ValueError(
                        f"org_code '{ancestor_code}' の rank 値 '{rank}' が不正です。"
                    )

                rank_code_col = f"rank{rank}_code"
                rank_name_col = f"rank{rank}_name"

                ancestor_rank_dict = {
                    rank_code_col: ancestor_code,
                    rank_name_col: node.get("name"),
                }

                # 祖先ノードのランク辞書をキャッシュ
                cache_rank_dict[ancestor_code] = ancestor_rank_dict

            # 現在の rank_dict を更新
            for key, value in ancestor_rank_dict.items():
                if rank_dict.get(key) is None:
                    rank_dict[key] = value

        return pd.Series(rank_dict)

    # assign_ranks 関数を各行に適用し、新しい列を割り当て
    rank_data = df.apply(assign_ranks, axis=1)
    for col in rank_data.columns:
        df[col] = rank_data[col]

    return df


def find_duplicate_names(df):
    """
    組織名を正規化し、重複する名前を特定する。
    """
    df["org_name_normalized"] = df["org_name"].apply(normalize_org_name)

    df_target = df.copy()

    # 重複する組織名を確認
    duplicate_counts = df_target["org_name_normalized"].value_counts()

    duplicate_names = duplicate_counts[duplicate_counts > 1].index.tolist()
    df_duplicates = df_target[df_target["org_name_normalized"].isin(duplicate_names)]
    return df, df_duplicates


def prepare_mapping_table(G: nx.DiGraph, df_mapping: pd.DataFrame):
    """
    マッピングデータを準備する。

    Parameters:
    - G (nx.DiGraph): 組織ツリー
    - df_mapping (pd.DataFrame): 事前に用意されたマッピングデータ。

    Returns:
    - dict: 組織コードをキーとし、略称とランクを値とする辞書。
    """

    def sanitize_abbreviation(abbr):
        return abbr if pd.notna(abbr) and abbr.strip() != "" else ""

    def apply_rank(org_code):
        if org_code not in G.nodes:
            raise ValueError(f"略称組織コード '{org_code}' がグラフに存在しません。")
        return G.nodes[org_code]["rank"]

    df_mapping["abbreviation"] = df_mapping["abbreviation"].apply(sanitize_abbreviation)
    df_mapping["rank"] = df_mapping["org_code"].apply(apply_rank)

    mapping_dict = df_mapping.set_index("org_code")[["abbreviation", "rank"]].to_dict(
        orient="index"
    )
    return mapping_dict


def get_path_to_root_by_name(G: nx.DiGraph, org_code: str):
    """
    指定した組織コードからルートまでのパスを組織名（正規化）で取得。

    Parameters:
    - G (nx.DiGraph): 組織ツリーのグラフ。
    - org_code (str): 組織コード。

    Returns:
    - list of str: ルートから指定組織までの組織名（正規化）のリスト。
    """

    # トポロジカルソート
    sorted_ancestors = get_sorted_ancestors(G, org_code)

    # 組織名の正規化
    normalize_org_names = [
        normalize_org_name(G.nodes[org]["name"]) for org in sorted_ancestors
    ]
    return normalize_org_names


# 指定ノードからルート（始点）までのパスを取得する関数
def get_path_to_root(G: nx.DiGraph, org_code, normalized_name):
    """
    指定した組織コードからルートまでのパスを取得し、指定の組織名（正規化済み）が最初に出現するノードのランクを取得します。

    Parameters:
    - G (nx.DiGraph): 組織ツリーのグラフ。
    - org_code (str): 組織コード。
    - normalized_name (str): 正規化された組織名。

    Returns:
    - tuple: (パス上のノードのリスト, 見つかった組織名のランク)
    """
    # トポロジカルソート
    sorted_ancestors = get_sorted_ancestors(G, org_code)

    # 組織組織ランクの確定
    # ランクの初期化
    rank = 0

    # トポロジカル順序で走査し、指定の名前を持つノードを探す
    for node in sorted_ancestors:
        org_name_normalized = normalize_org_name(G.nodes[node].get("name", ""))
        if org_name_normalized == normalized_name:
            rank = G.nodes[node].get("rank", 0)
            break  # 見つかったらループを抜ける

    return sorted_ancestors, rank


def longest_common_prefix(list1, list2):
    """
    2つのリストの最長共通プレフィックスを返す。
    """
    min_length = min(len(list1), len(list2))
    prefix = []
    for i in range(min_length):
        if list1[i] == list2[i]:
            prefix.append(list1[i])
        else:
            break
    return prefix


def find_max_common_prefix(paths):
    """
    複数のパスから最長の共通プレフィックスを特定する。

    Parameters:
    - paths (list of list of str): 組織パスのリスト。

    Returns:
    - list of str: 最長共通プレフィックス。
    """
    if not paths:
        return []
    common_prefix = paths[0]
    for path in paths[1:]:
        common_prefix = longest_common_prefix(common_prefix, path)
        if not common_prefix:
            break
    return common_prefix


def assign_unique_identifier(df_duplicates, G, mapping_dict):
    """
    重複する組織名に対して、一意な識別子を決定して割り当てる。

    Parameters:
    - df_duplicates (pd.DataFrame): 重複する組織名を持つ組織のデータフレーム。
    - G (nx.DiGraph): 組織ツリーのグラフ。
    - mapping_dict (dict): 組織コードから略称へのマッピング辞書。

    Returns:
    - pd.DataFrame: 識別子が追加されたデータフレーム。
    """
    df_duplicates = df_duplicates.copy()
    df_duplicates["identifier"] = ""

    # グループごとに処理
    grouped = df_duplicates.groupby("org_name_normalized")

    for name, group in grouped:
        # 各組織のパスを取得（組織名で）
        paths = {
            row["org_code"]: get_path_to_root_by_name(G, row["org_code"])
            for _, row in group.iterrows()
        }

        # キューを用いたサブグループ処理
        queue = [list(paths.keys())]  # 初期サブグループは全org_codes

        while queue:
            current_org_codes = queue.pop(0)
            current_paths = [paths[org_code] for org_code in current_org_codes]
            common_prefix = find_max_common_prefix(current_paths)
            prefix_length = len(common_prefix)

            if prefix_length == 0:
                # 共通プレフィックスがない場合、ルート名を識別子として使用
                for org_code in current_org_codes:
                    identifier = G.nodes[org_code]["name"]
                    df_duplicates.loc[
                        df_duplicates["org_code"] == org_code, "identifier"
                    ] = identifier
                continue

            # 次のセグメントでサブグループを作成
            subgroups = {}
            for org_code in current_org_codes:
                path = paths[org_code]
                if len(path) > prefix_length:
                    next_segment = path[prefix_length]
                else:
                    next_segment = ""  # 共通プレフィックスのみの場合

                if next_segment not in subgroups:
                    subgroups[next_segment] = []
                subgroups[next_segment].append(org_code)

            # 各サブグループに対して識別子を割り当て
            for next_segment, org_codes in subgroups.items():
                if len(org_codes) == 1:
                    # 一つの組織コードの場合、識別子を割り当て
                    org_code = org_codes[0]

                    common_path_org_codes, common_org_rank = get_path_to_root(
                        G, org_code, next_segment
                    )

                    identifier = G.nodes[org_code]["name"]  # デフォルトは組織名

                    # マッピングデータに含まれる組織コードを確認
                    for k in mapping_dict:
                        if k in common_path_org_codes:
                            mapping_org = mapping_dict.get(k)

                            # マッピングデータの組織ランクを取得
                            seg_rank = mapping_org.get("rank")
                            if seg_rank >= common_org_rank:
                                identifier = mapping_org.get("abbreviation")
                                break  # 一度割り当てたら終了

                    df_duplicates.loc[
                        df_duplicates["org_code"] == org_code, "identifier"
                    ] = identifier
                else:
                    # 複数の組織コードが存在する場合、さらに分割が必要
                    queue.append(org_codes)

        # グループ内の全てのorg_codeに対して識別子が割り当てられていることを確認
        missing_identifiers = df_duplicates[
            (df_duplicates["org_name_normalized"] == name)
            & (df_duplicates["identifier"] == "")
        ]
        if not missing_identifiers.empty:
            for _, row in missing_identifiers.iterrows():
                org_code = row["org_code"]
                identifier = G.nodes[org_code]["name"]
                df_duplicates.loc[
                    df_duplicates["org_code"] == org_code, "identifier"
                ] = identifier

    return df_duplicates


def validate_mapping_data(df_duplicates_with_id):
    """
    マッピングデータに適切な識別子が存在するかを検証。
    存在しない場合、アラートを出力。
    """
    alerts = []
    for _, row in df_duplicates_with_id.iterrows():
        identifier = row.get("identifier")
        if identifier:
            continue
        else:
            alert_msg = f"組織名 '{row['org_name']}' (コード: {row['org_code']}) に適切な識別子が見つかりませんでした。"
            alerts.append(alert_msg)

    if alerts:
        for alert in alerts:
            logger.warning(alert)
    else:
        logger.info("すべての重複する組織に対して適切な識別子が割り当てられています。")


def add_abbreviations_to_names(df, df_duplicates, mapping_dict, G):
    """
    重複する組織名に対して、上位組織の略称または識別子を基に識別子を付与する。
    """
    # 一意な識別子を決定
    df_duplicates_with_id = assign_unique_identifier(df_duplicates, G, mapping_dict)

    # 識別子を検証
    validate_mapping_data(df_duplicates_with_id)

    # 識別子を組織名に追加する関数。丸括弧を付ける
    def append_identifier(row):
        return (
            f"{row['org_name']} ({row['identifier']})"
            if row["identifier"]
            else row["org_name"]
        )

    # 重複する組織名の組織名を更新
    for _, row in df_duplicates_with_id.iterrows():
        org_code = row["org_code"]
        org_rank = row["rank"]
        updated_name = append_identifier(row)
        rank_name_col = f"rank{org_rank}_name"
        df.loc[df["org_code"] == org_code, rank_name_col] = updated_name

    # 補助列を削除
    df.drop(
        ["org_name_normalized"],
        axis=1,
        inplace=True,
        errors="ignore",
    )

    return df


def create_organization(df: pd.DataFrame, df_mapping: pd.DataFrame):
    """
    組織データを処理し、識別子を付与したランクごとの組織名を出力します。

    Args:
        df (pd.DataFrame): 組織データが格納されたDataFrame（org_code, org_name, parent_code, rank）。
        df_mapping (pd.DataFrame): 事前に用意されたマッピングデータ。

    Returns:
        pd.DataFrame: 識別子が追加された最終的な組織データフレーム。
    """

    logger.info(f"組織データを{len(df)}件読み込みました。")

    # ツリー構築
    G = build_tree(df)

    # ランクごとのコードと名前の列を割り当て
    df = assign_rank_columns(df, G)

    # 重複する組織名を特定
    df, df_duplicates = find_duplicate_names(df)

    if not df_duplicates.empty:
        # マッピングデータを辞書に変換
        mapping_dict = prepare_mapping_table(G, df_mapping=df_mapping)

        # 識別子を組織名に付与
        df = add_abbreviations_to_names(df, df_duplicates, mapping_dict, G)
    else:
        logger.info("重複する組織名は存在しません。")

    return df
