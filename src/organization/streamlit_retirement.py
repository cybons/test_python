# retirement_app.py
"""
退職者処理アプリケーション

StreamlitによるGUIと、ベクトル化された退職者処理ロジックを提供します。
"""

import streamlit as st
from datetime import datetime
from typing import tuple
import pandas as pd
import io

class RetirementProcessor:
    """退職者の処理を行うクラス（ベクトル化処理版）"""

    def __init__(
        self,
        retirement_df: pd.DataFrame,
        user_df: pd.DataFrame,
        target_date: datetime,
        employment_change_keywords: list[str] = None
    ):
        """
        初期化メソッド

        Args:
            retirement_df: 退職者情報のDataFrame
            user_df: ユーザー情報のDataFrame
            target_date: 処理基準日
            employment_change_keywords: 雇用形態変更を示すキーワードのリスト
        """
        self.retirement_df = retirement_df.copy()
        self.user_df = user_df.copy()
        self.target_date = target_date
        self.employment_change_keywords = (
            employment_change_keywords or ["雇用形態切替", "雇用形態変更"]
        )
        
        # DataFrameの前処理
        self._preprocess_dataframes()

    def _preprocess_dataframes(self) -> None:
        """DataFrameの前処理を行います（ベクトル化処理）"""
        # 日付型への変換
        self.retirement_df["退職日"] = pd.to_datetime(self.retirement_df["退職日"])
        
        # 雇用形態変更フラグの作成
        employment_change_mask = self.retirement_df["退職理由"].str.contains(
            "|".join(self.employment_change_keywords),
            na=False
        )

        # 指定日以前のデータかつ雇用形態変更でないデータでフィルタリング
        self.retirement_df = self.retirement_df[
            (self.retirement_df["退職日"] <= self.target_date) &
            (~employment_change_mask)
        ]
        
        # 退職日で降順ソートし、最新の退職情報を取得
        self.retirement_df = (
            self.retirement_df.sort_values("退職日", ascending=False)
            .drop_duplicates(subset=["社員番号"], keep="first")
        )

    def process_retirements(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        退職者の処理を実行します（ベクトル化処理）

        Returns:
            tuple[pd.DataFrame, pd.DataFrame]: 
                - 確定した退職者のDataFrame
                - 再雇用の可能性がある退職者のDataFrame
        """
        # 社員番号での照合
        employee_id_mask = self.retirement_df["社員番号"].isin(self.user_df["社員番号"])
        
        # 確定退職者と要確認者の分類
        confirmed_retirees = self.retirement_df[~employee_id_mask].copy()
        reemployment_check = self.retirement_df[employee_id_mask].copy()
        
        # 要確認者に理由を追加
        reemployment_check["確認理由"] = "社員番号一致（再雇用の可能性）"

        return confirmed_retirees, reemployment_check

def main():
    st.set_page_config(page_title="退職者処理システム", layout="wide")
    st.title("退職者処理システム")

    # サイドバーに処理日の設定を配置
    st.sidebar.header("処理設定")
    target_date = st.sidebar.date_input(
        "処理基準日",
        value=datetime.now(),
        help="この日付までに退職する社員を処理対象とします"
    )

    # ファイルアップロード部分
    st.header("データ入力")
    col1, col2 = st.columns(2)
    
    with col1:
        retirement_file = st.file_uploader(
            "退職者リストをアップロード",
            type=["csv"],
            help="退職者情報が記載されたCSVファイル"
        )

    with col2:
        user_file = st.file_uploader(
            "ユーザーリストをアップロード",
            type=["csv"],
            help="現在の社員情報が記載されたCSVファイル"
        )

    if retirement_file and user_file:
        try:
            # CSVファイルの読み込み
            retirement_df = pd.read_csv(retirement_file)
            user_df = pd.read_csv(user_file)

            # 処理実行
            processor = RetirementProcessor(
                retirement_df=retirement_df,
                user_df=user_df,
                target_date=target_date
            )

            confirmed_retirees, reemployment_check = processor.process_retirements()

            # 結果の表示
            st.header("処理結果")
            
            # メトリクス表示
            col1, col2 = st.columns(2)
            with col1:
                st.metric("確定退職者数", len(confirmed_retirees))
            with col2:
                st.metric("要確認者数", len(reemployment_check))

            # タブで結果を表示
            tab1, tab2 = st.tabs(["確定退職者", "要確認者"])
            
            with tab1:
                st.subheader("確定退職者リスト")
                st.dataframe(
                    confirmed_retirees,
                    use_container_width=True,
                    hide_index=True
                )

            with tab2:
                st.subheader("要確認者リスト")
                st.dataframe(
                    reemployment_check,
                    use_container_width=True,
                    hide_index=True
                )

            # エクスポートボタン
            st.download_button(
                label="結果をExcelファイルとしてダウンロード",
                data=_create_excel_download(confirmed_retirees, reemployment_check),
                file_name=f"退職者処理結果_{target_date.strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"エラーが発生しました: {str(e)}")
            st.stop()

def _create_excel_download(confirmed_df: pd.DataFrame, check_df: pd.DataFrame) -> bytes:
    """Excelファイルをバイトデータとして作成"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        confirmed_df.to_excel(writer, sheet_name="確定退職者", index=False)
        check_df.to_excel(writer, sheet_name="要確認リスト", index=False)
    return output.getvalue()

if __name__ == "__main__":
    main()
