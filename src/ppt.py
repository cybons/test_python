from pptx import Presentation
import win32com.client
import os
import time
from PIL import Image

def pptx_to_png(input_pptx, output_folder, width=960):
    """
    PowerPointファイルの各スライドをPNG画像に変換する
    
    Parameters:
    input_pptx (str): 入力PowerPointファイルのパス
    output_folder (str): 出力画像を保存するフォルダのパス
    width (int): 出力画像の横幅（デフォルト: 960px）
    """
    # 出力フォルダの作成
    os.makedirs(output_folder, exist_ok=True)
    
    # PowerPointアプリケーションの起動
    powerpoint = win32com.client.Dispatch("PowerPoint.Application")
    powerpoint.Visible = True  # デバッグ時に表示させる場合はTrue
    
    try:
        # プレゼンテーションを開く
        abs_path = os.path.abspath(input_pptx)
        presentation = powerpoint.Presentations.Open(abs_path)
        
        # 一時的な保存フォルダ（フルサイズの画像用）
        temp_folder = os.path.join(output_folder, "temp")
        os.makedirs(temp_folder, exist_ok=True)
        
        try:
            # 各スライドを画像として保存
            presentation.SaveAs(
                os.path.join(temp_folder, "slide"),
                17  # ppSaveAsPNG = 17
            )
            
            # PowerPointが画像の保存を完了するまで少し待機
            time.sleep(2)
            
            # 保存された画像をリサイズして指定フォルダに移動
            for i, file in enumerate(sorted(os.listdir(temp_folder))):
                if file.endswith(".PNG"):
                    # 画像を開く
                    img_path = os.path.join(temp_folder, file)
                    img = Image.open(img_path)
                    
                    # アスペクト比を維持しながらリサイズ
                    orig_width, orig_height = img.size
                    aspect_ratio = orig_height / orig_width
                    new_height = int(width * aspect_ratio)
                    img = img.resize((width, new_height), Image.LANCZOS)
                    
                    # リサイズした画像を保存
                    output_path = os.path.join(output_folder, f"slide_{i+1}.png")
                    img.save(output_path, "PNG", optimize=True)
                    print(f"Saved: {output_path}")
                    
                    # 元の画像を削除
                    os.remove(img_path)
            
        finally:
            # プレゼンテーションを閉じる
            presentation.Close()
            
    finally:
        # PowerPointアプリケーションを終了
        powerpoint.Quit()
        
        # 一時フォルダの削除
        try:
            os.rmdir(temp_folder)
        except:
            pass

# 使用例
if __name__ == "__main__":
    pptx_to_png("input.pptx", "output_images")