class PathResolver:
    """単純なファイルパス解決クラス"""
    
    @staticmethod
    def resolve_file(file_path: Path) -> Path:
        """
        ファイルパスを解決する
        一時ファイル($~)を除外し、パターンマッチの場合は最初のファイルを返す
        """
        if file_path.exists():
            return file_path
            
        # パターンマッチング
        parent = file_path.parent
        pattern = file_path.name
        matched_files = [
            f for f in parent.glob(pattern)
            if not f.name.startswith('$~')  # 一時ファイルを除外
        ]
        
        if not matched_files:
            raise FileNotFoundError(f"File not found: {file_path}")
            
        return matched_files[0]