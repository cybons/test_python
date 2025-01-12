from dataclasses import dataclass, field


@dataclass
class SheetConfig:
    """シートの詳細を返す
    -------
        column_names: list[str]
            全列名
        key_columns: list[str]
            キー列
        drop_cols: list[str]
            削除列を取得
        columns_to_compare: list[str]
            比較対象列
    """

    column_names: list[str] = field(default_factory=list)
    key_columns: list[str] = field(default_factory=list)
    drop_cols: list[str] = field(default_factory=list)
    columns_to_compare: list[str] = field(default_factory=list)
