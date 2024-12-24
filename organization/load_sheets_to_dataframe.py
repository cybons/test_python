import pandas as pd

def load_sheets_to_dataframe(file_path, sheet_names, start_row=23, start_col='B', end_col='H', expected_headers=None):
    """
    Excelファイルの指定シートからデータを読み込み、シート名と行番号を追加して
    すべてのデータを文字列型として統合したPandasのDataFrameを返します。

    Parameters:
    - file_path (str): 読み込むExcelファイルのパス。
    - sheet_names (list of str): 読み込むシート名のリスト。
    - start_row (int): データの開始行（0ベースのインデックス）。24行目なら23。
    - start_col (str): データの開始列（アルファベット）。Bなら 'B'。
    - end_col (str): データの終了列（アルファベット）。Hなら 'H'。
    - expected_headers (list of str): ヘッダー行に期待する列名のリスト。Noneの場合はチェックをスキップ。

    Returns:
    - pd.DataFrame: すべてのシートのデータを統合したDataFrame（すべての列が文字列型）。
    """
    # 列範囲を指定して読み込む
    usecols = f"{start_col}:{end_col}"
    
    # 複数のシートを一度に読み込む
    # sheet_name=None はすべてのシートを読み込む
    # ここでは指定されたシート名のみを読み込む
    df_dict = pd.read_excel(
        file_path,
        sheet_name=sheet_names,
        header=start_row,  # header に実際のヘッダー行のインデックスを指定
        usecols=usecols,
        dtype=str,
        engine='openpyxl'
    )
    
    all_data = []
    
    for sheet, df in df_dict.items():
        # ヘッダーのチェック
        if expected_headers:
            # ヘッダーが正しく読み込まれているか確認
            if list(df.columns) != expected_headers:
                print(f"シート '{sheet}' のヘッダーが期待されるものと一致しません。スキップします。")
                continue
        
        # データの開始行を調整
        # read_excel の header パラメータを使用しているため、既にヘッダーは設定済み
        # 必要に応じて行番号をリセット
        df = df.reset_index(drop=True)
        
        # 空行を削除
        df.dropna(how='all', inplace=True)
        
        # シート名の追加
        df['SheetName'] = sheet
        
        # 行番号の追加（元のExcelの行番号に対応）
        # 元のExcelの行番号 = start_row + 2 (header行の次) + df.index
        df['RowNumber'] = df.index + start_row + 2  # 1ベースに調整
        
        all_data.append(df)
    
    # 全てのデータを結合
    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
    else:
        final_df = pd.DataFrame()
    
    # 全ての列を文字列型に変換（念のため）
    final_df = final_df.astype(str)
    
    return final_df

# 使用例
if __name__ == "__main__":
    file_path = 'your_excel_file.xlsx'  # 対象のExcelファイルパスを指定
    
    # 読み込むシート名のリストを取得（例: シート1, シート2, ...）
    # ここでは全てのシートを対象とする場合、openpyxl でシート名を取得
    import openpyxl
    wb = openpyxl.load_workbook(file_path, read_only=True)
    all_sheet_names = wb.sheetnames
    wb.close()
    
    # 期待するヘッダーをリストとして定義（例）
    expected_headers = ['Header1', 'Header2', 'Header3', 'Header4', 'Header5', 'Header6', 'Header7']
    
    # 関数を実行
    df = load_sheets_to_dataframe(
        file_path=file_path,
        sheet_names=all_sheet_names,
        start_row=23,       # 24行目をヘッダーとするため0ベースで23
        start_col='B',      # B列
        end_col='H',        # H列
        expected_headers=expected_headers  # ヘッダーのチェック
    )
    
    print(df)
    
    # 必要に応じてCSVに保存
    # df.to_csv('output.csv', index=False, encoding='utf-8-sig')