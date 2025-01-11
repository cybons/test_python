import matplotlib.pyplot as plt
import networkx as nx

plt.rcParams["font.family"] = (
    "MS Gothic"  # インストールされている日本語フォント名に変更してください
)
plt.rcParams["axes.unicode_minus"] = False  # マイナス記号の表示を正常化

# グラフの生成（有向グラフ）
G = nx.DiGraph()

# ノードの追加（各ステップ）
G.add_node("起票", role="start")
G.add_node("部署確認")
G.add_node("責任者ボックス")
G.add_node("専門部署ボックス")
G.add_node("承認")
G.add_node("完了", role="end")

# エッジの追加（フローの流れ）
G.add_edge("起票", "部署確認")
G.add_edge("部署確認", "責任者ボックス")
G.add_edge("部署確認", "専門部署ボックス")
G.add_edge("責任者ボックス", "承認")
G.add_edge("専門部署ボックス", "承認")
G.add_edge("承認", "完了")

# ノードの位置を手動で指定
pos = {
    "起票": (0, 2),
    "部署確認": (1, 2),
    "責任者ボックス": (2, 3),
    "専門部署ボックス": (2, 1),
    "承認": (3, 2),
    "完了": (4, 2),
}

# ノードの描画
nx.draw(
    G,
    pos,
    with_labels=True,
    node_size=3000,
    node_color="lightblue",
    font_size=12,
    font_weight="bold",
    font_family="MS Gothic",
)

# エッジラベルの追加
edge_labels = {
    ("部署確認", "責任者ボックス"): "責任者経由",
    ("部署確認", "専門部署ボックス"): "専門部署経由",
}
nx.draw_networkx_edge_labels(
    G, pos, edge_labels=edge_labels, font_size=10, font_family="MS Gothic"
)

# グラフの表示
plt.title("ワークフロー図", fontsize=16)
plt.axis("off")  # 軸を非表示にする
plt.show()
