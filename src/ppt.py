from pptx import Presentation
import win32com.client
import os
import time
from PIL import Image
import glob
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

def pptx_to_png(input_pptx, output_folder, height=540):
    """
    PowerPointファイルの各スライドをPNG画像に変換する
    
    Parameters:
    input_pptx (str): 入力PowerPointファイルのパス
    output_folder (str): 出力画像を保存するフォルダのパス
    height (int): 出力画像の高さ（デフォルト: 540px）
    """
    os.makedirs(output_folder, exist_ok=True)
    
    powerpoint = win32com.client.Dispatch("PowerPoint.Application")
    powerpoint.Visible = True
    
    try:
        abs_path = os.path.abspath(input_pptx)
        presentation = powerpoint.Presentations.Open(abs_path)
        
        temp_folder = os.path.join(output_folder, "temp")
        os.makedirs(temp_folder, exist_ok=True)
        
        try:
            # BMPとして保存（画質劣化を防ぐため）
            presentation.SaveAs(
                os.path.join(temp_folder, "slide"),
                19  # ppSaveAsBMP = 19
            )
            
            time.sleep(2)
            
            # BMPファイルを検索してソート
            bmp_files = sorted(glob.glob(os.path.join(temp_folder, "*.BMP")))
            
            # 元のファイル名を取得（拡張子なし）
            original_filename = Path(input_pptx).stem
            
            for i, img_path in enumerate(bmp_files):
                img = Image.open(img_path)
                
                # アスペクト比を維持しながら高さを基準にリサイズ
                orig_width, orig_height = img.size
                aspect_ratio = orig_width / orig_height
                new_width = int(height * aspect_ratio)
                img = img.resize((new_width, height), Image.LANCZOS)
                
                # 元のファイル名を使用して出力ファイル名を設定
                output_path = os.path.join(output_folder, f"{original_filename}_p{i+1}.png")
                img.save(output_path, "PNG", optimize=True)
                print(f"Saved: {output_path}")
                
                os.remove(img_path)
            
        finally:
            presentation.Close()
            
    finally:
        powerpoint.Quit()
        try:
            os.rmdir(temp_folder)
        except:
            pass

def process_pptx_directory(input_root, output_root):
    """
    指定されたルートディレクトリ以下のPPTXファイルを再帰的に処理する
    
    Parameters:
    input_root (str): 入力PPTXファイルが含まれるルートディレクトリ
    output_root (str): 出力PNGファイルを保存するルートディレクトリ
    """
    input_root = Path(input_root)
    output_root = Path(output_root)
    
    # 再帰的にPPTXファイルを検索
    for pptx_path in input_root.rglob("*.pptx"):
        # 入力ファイルの相対パスを取得
        rel_path = pptx_path.relative_to(input_root)
        
        # 出力ディレクトリを作成（サブディレクトリ構造を維持）
        output_dir = output_root / rel_path.parent
        
        print(f"Processing: {pptx_path}")
        print(f"Output directory: {output_dir}")
        
        # PNG変換を実行
        pptx_to_png(str(pptx_path), str(output_dir))

def main():
    # tkinterのルートウィンドウを作成（非表示）
    root = tk.Tk()
    root.withdraw()
    
    # フォルダ選択ダイアログを表示
    input_folder = filedialog.askdirectory(
        title="変換するPPTXファイルが入っているフォルダを選択してください"
    )
    
    if not input_folder:  # キャンセルされた場合
        print("フォルダが選択されませんでした。")
        return
    
    # 入力フォルダのパスオブジェクトを作成
    input_path = Path(input_folder)
    
    # 出力フォルダ名を生成（入力フォルダ名_変換後）
    output_folder = input_path.parent / f"{input_path.name}_変換後"
    
    print(f"Input folder: {input_folder}")
    print(f"Output folder: {output_folder}")
    
    # 変換処理を実行
    process_pptx_directory(input_folder, output_folder)
    
    print("変換が完了しました。")

if __name__ == "__main__":
    main()