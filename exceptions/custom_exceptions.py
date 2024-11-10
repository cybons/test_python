class UserProcessorError(Exception):
    """ユーザープロセッサにおける基本的なエクセプションクラス"""

    pass


class ColumnRenameError(UserProcessorError):
    """列のリネームに失敗した際のエクセプション"""

    def __init__(self, missing_columns, dataframe_name):
        self.missing_columns = missing_columns
        self.dataframe_name = dataframe_name
        message = f"Missing columns for renaming in {dataframe_name}: {missing_columns}"
        super().__init__(message)
