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
            (rank0_pairs["jaccard_index"] >= jaccard_threshold) |
            (rank0_pairs["cosine_similarity"] >= cosine_threshold)
        ]

        # 詳細な統計情報をログに記録
        self.rank_stats = rank_stats  # インスタンス変数として保存
        print(f"Rank statistics:\n{rank_stats}")
        print(f"Using thresholds - Jaccard: {jaccard_threshold:.3f}, Cosine: {cosine_threshold:.3f}")
        print(f"Number of high similarity rank 0 pairs: {len(rank0_high_similarity)}")
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
    
    # 各ランクの平均類似度を考慮した動的な除外
    for rank in rank_stats.index:
        if rank == 0:
            continue  # ランク0は特別に扱う
            
        rank_data = rank_stats.loc[rank]
        jaccard_mean = rank_data[("jaccard_index", "mean")]
        cosine_mean = rank_data[("cosine_similarity", "mean")]
        pair_count = rank_data[("jaccard_index", "count")]
        
        # ペア数が少ない場合は慎重に判断
        if pair_count < self.thresholds.min_pair_count:
            rank_threshold = self.thresholds.rank_min_threshold
        else:
            # ランクが上がるごとに要求される類似度の閾値を下げる
            rank_threshold = max(
                self.thresholds.rank_min_threshold,
                jaccard_threshold * (1 - rank * self.thresholds.rank_decay_rate)
            )
            
        # 平均類似度が閾値を下回る場合、そのランクのペアを除外
        if jaccard_mean < rank_threshold and cosine_mean < (rank_threshold * 1.5):
            exclude_mask |= (
                (self.df["rank_difference_abs"] == rank) &
                (self.df["jaccard_index"] < jaccard_mean * self.thresholds.high_percentile)
            )
    
    # 除外フラグの設定
    self.df.loc[exclude_mask & ~self.df["is_similar"], "is_excluded"] = True
    
    
    
    
# デフォルトの閾値を使用
filter = FlexibleOrganizationFilter(similarity_df)

# カスタム閾値を設定
custom_thresholds = SimilarityThresholds(
    base_jaccard=0.35,         # より緩い基本閾値
    base_cosine=0.45,
    rank_decay_rate=0.15,      # よりゆるやかな減衰
    rank_min_threshold=0.15,   # より高い最小閾値
    mean_adjustment=0.75,      # より厳しい平均値調整
    high_percentile=1.3,       # より寛容な高類似度判定
    min_pair_count=3           # より少ないペア数でも判断
)
filter_custom = FlexibleOrganizationFilter(similarity_df, thresholds=custom_thresholds) 