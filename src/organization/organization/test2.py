def _exclude_by_rank_difference(self):
    """
    ランク差と類似度に基づいて、不要な組織ペアを除外
    
    除外ロジック:
    1. 各組織に対して、ランク0での類似度を優先的に評価
    2. 高類似度のランク0ペアがある組織は、より高いランク差のペアを除外
    3. それ以外の組織は、類似度とランク差に基づいて判断
    """
    # 既に除外またはsimilarとマークされていないペアのみを対象
    target_pairs = self.df[~self.df["is_excluded"] & ~self.df["is_similar"]].copy()
    
    # 組織ごとの統計を計算
    org_stats = {}
    for org in pd.unique(target_pairs["org_hierarchy_x"]):
        # 対象組織のペアを抽出
        org_pairs = target_pairs[target_pairs["org_hierarchy_x"] == org]
        
        # ランク差ごとの統計を計算
        rank_stats = org_pairs.groupby("rank_difference_abs").agg({
            "jaccard_index": ["max", "mean", "count"],
            "cosine_similarity": ["max", "mean"]
        }).round(3)
        
        org_stats[org] = rank_stats
    
    # 除外マスクの初期化
    exclude_mask = pd.Series(False, index=self.df.index)
    
    # 組織ごとに判定
    for org, rank_stats in org_stats.items():
        # 組織のペアを取得
        org_mask = self.df["org_hierarchy_x"] == org
        
        if 0 in rank_stats.index:  # ランク0のペアが存在する場合
            rank0_stats = rank_stats.loc[0]
            max_jaccard = rank0_stats[("jaccard_index", "max")]
            max_cosine = rank0_stats[("cosine_similarity", "max")]
            
            # ランク0で高類似度のペアが存在する場合
            if (max_jaccard >= self.thresholds.base_jaccard or 
                max_cosine >= self.thresholds.base_cosine):
                
                # より高いランクのペアを除外
                exclude_mask |= (
                    org_mask & 
                    (self.df["rank_difference_abs"] > 0) &
                    (self.df["jaccard_index"] < max_jaccard * self.thresholds.high_percentile)
                )
                continue
        
        # ランク0で高類似度ペアがない場合は、ランクごとに判定
        for rank, stats in rank_stats.iterrows():
            pair_count = stats[("jaccard_index", "count")]
            max_jaccard = stats[("jaccard_index", "max")]
            
            # ペア数が少ない場合は慎重に判断
            if pair_count < self.thresholds.min_pair_count:
                rank_threshold = self.thresholds.rank_min_threshold
            else:
                # ランクが上がるごとに要求される類似度の閾値を下げる
                rank_threshold = max(
                    self.thresholds.rank_min_threshold,
                    self.thresholds.base_jaccard * (1 - rank * self.thresholds.rank_decay_rate)
                )
            
            # 類似度が閾値を下回る場合、そのランクのペアを除外
            if max_jaccard < rank_threshold:
                exclude_mask |= (
                    org_mask & 
                    (self.df["rank_difference_abs"] == rank)
                )
    
        # 極端に類似度が低いペアは除外
        exclude_mask |= (
            org_mask &
            (self.df["jaccard_index"] < self.thresholds.rank_min_threshold) &
            (self.df["cosine_similarity"] < self.thresholds.rank_min_threshold * 1.5) &
            (self.df["rank_difference_abs"] > 0)  # ランク0は除外しない
        )
    
    # 統計情報をログに出力
    print("\nOrganization Statistics:")
    for org, stats in org_stats.items():
        print(f"\nOrganization: {org}")
        print(stats.to_string())
    
    # 除外フラグの設定
    self.df.loc[exclude_mask & ~self.df["is_similar"], "is_excluded"] = True