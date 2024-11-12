import tkinter as tk
from tkinter import filedialog, messagebox
import os
from datetime import datetime
import sys

class FileSelector:
    def __init__(self, master, label_text, selector_type='file', file_types=None, initial_path=None):
        """
        ファイルまたはフォルダ選択フレームを初期化します。

        :param master: 親ウィジェット
        :param label_text: 選択ボックスのラベルテキスト
        :param selector_type: 'file' または 'folder' を指定
        :param file_types: ファイルダイアログで許可するファイル拡張子のリスト（'file' タイプのみ）
        :param initial_path: テキストボックスの初期パス。省略時は実行ファイルのパス（'file' タイプ）またはホームディレクトリ（'folder' タイプ）を使用
        """
        self.master = master
        self.label_text = label_text
        self.selector_type = selector_type
        self.file_types = file_types
        self.initial_path = initial_path if initial_path else self.get_default_initial_path()

        # フレームの作成
        self.frame = tk.Frame(master)
        self.frame.pack(padx=10, pady=5, fill=tk.X)

        # ラベル
        self.label = tk.Label(self.frame, text=label_text)
        self.label.pack(side=tk.LEFT)

        # ボタン
        self.button = tk.Button(self.frame, text="選択", command=self.select)
        self.button.pack(side=tk.LEFT, padx=5)

        # テキストボックス
        self.text = tk.Text(self.frame, height=2, width=50)
        self.text.pack(side=tk.LEFT, padx=5)
        self.text.bind("<FocusOut>", self.on_focus_out)

        # 更新日時ラベル
        self.mod_label = tk.Label(master, text="")
        self.mod_label.pack()

        # 設定初期値
        self.set_initial_path()

    def get_default_initial_path(self):
        """初期パスを取得します。'file' タイプなら実行ファイルのパス、'folder' タイプならホームディレクトリを返します。"""
        if self.selector_type == 'file':
            if getattr(sys, 'frozen', False):
                # PyInstallerなどで実行されている場合
                return os.path.abspath(sys.executable)
            else:
                # 通常のPythonスクリプトとして実行されている場合
                return os.path.abspath(__file__)
        elif self.selector_type == 'folder':
            return os.path.expanduser("~")
        else:
            return ""

    def set_initial_path(self):
        """初期パスをテキストボックスに設定し、更新日時を表示します。"""
        if os.path.exists(self.initial_path):
            self.text.delete("1.0", tk.END)
            self.text.insert(tk.END, self.initial_path)
            self.display_mod_time(self.initial_path)
        else:
            self.text.delete("1.0", tk.END)
            self.text.insert(tk.END, "")
            self.mod_label.config(text="")

    def select(self):
        """ファイルまたはフォルダ選択ダイアログを開き、選択されたパスをテキストボックスに表示します。"""
        if self.selector_type == 'file':
            file_path = filedialog.askopenfilename(filetypes=self.file_types)
            if file_path:
                self.text.delete("1.0", tk.END)
                self.text.insert(tk.END, file_path)
                self.display_mod_time(file_path)
        elif self.selector_type == 'folder':
            folder_path = filedialog.askdirectory()
            if folder_path:
                self.text.delete("1.0", tk.END)
                self.text.insert(tk.END, folder_path)
                self.display_mod_time(folder_path)

    def on_focus_out(self, event):
        """テキストボックスからフォーカスが外れたときに呼び出されます。"""
        path = self.text.get("1.0", tk.END).strip()
        self.display_mod_time(path)

    def display_mod_time(self, path):
        """ファイルまたはフォルダの最終更新日時を表示します。"""
        if os.path.exists(path):
            try:
                mod_time = os.path.getmtime(path)
                readable_time = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
                self.mod_label.config(text=f"最終更新日: {readable_time}")
            except Exception as e:
                self.mod_label.config(text=f"更新日取得エラー: {e}")
        else:
            self.mod_label.config(text="有効なパスを入力してください。")

    def get_path(self):
        """テキストボックスからパスを取得します。"""
        return self.text.get("1.0", tk.END).strip()

class FileSelectorApp:
    def __init__(self, master, file_configs):
        """
        アプリケーションのメインウィンドウを初期化します。

        :param master: Tkインスタンス
        :param file_configs: 各選択ボックスの設定を含むリスト。各要素は辞書で以下のキーを持つ:
                             - 'label': ラベルテキスト
                             - 'type': 'file' または 'folder'
                             - 'file_types': ファイルダイアログのファイルタイプフィルタ（'file' タイプのみ、省略可）
                             - 'initial_path': 初期パス（省略可）
        """
        self.master = master
        master.title("ファイル・フォルダ選択アプリ")

        self.file_selectors = []
        for config in file_configs:
            selector = FileSelector(
                master,
                label_text=config.get('label', '選択'),
                selector_type=config.get('type', 'file'),
                file_types=config.get('file_types') if config.get('type', 'file') == 'file' else None,
                initial_path=config.get('initial_path')
            )
            self.file_selectors.append(selector)

        # 実行ボタンと閉じるボタンのフレーム
        self.action_frame = tk.Frame(master)
        self.action_frame.pack(padx=10, pady=10)

        self.execute_button = tk.Button(self.action_frame, text="実行", command=self.execute)
        self.execute_button.pack(side=tk.LEFT, padx=5)

        self.close_button = tk.Button(self.action_frame, text="閉じる", command=master.quit)
        self.close_button.pack(side=tk.LEFT, padx=5)

    def execute(self):
        """すべてのパスを取得し、存在を確認した上で処理を実行します。"""
        file_paths = [selector.get_path() for selector in self.file_selectors]

        # パスの存在確認
        for idx, (path, config) in enumerate(zip(file_paths, file_configs), start=1):
            if config.get('type', 'file') == 'file' and not os.path.isfile(path):
                messagebox.showerror("エラー", f"{config.get('label', 'ファイル')} が存在しません。\nパス: {path}")
                return
            elif config.get('type', 'file') != 'file' and not os.path.isdir(path):
                messagebox.showerror("エラー", f"{config.get('label', 'フォルダ')} が存在しません。\nパス: {path}")
                return

        # パスの確認後、処理を実行
        # ここに実際の処理を追加します。以下は例としてメッセージボックスに表示します。
        info_lines = []
        for config, path in zip(file_configs, file_paths):
            info_lines.append(f"{config.get('label', '選択')}: {path}")
        info_text = "\n".join(info_lines) + "\n処理を実行しました。"

        messagebox.showinfo("実行", info_text)

if __name__ == "__main__":
    root = tk.Tk()

    # ファイル選択ボックスとフォルダ選択ボックスの設定リスト
    file_configs = [
        {
            'label': '入力ファイル1',
            'type': 'file',
            'file_types': [("テキストファイル", "*.txt"), ("CSVファイル", "*.csv"), ("全てのファイル", "*.*")],
            'initial_path': None  # 初期パスを指定しない場合、実行ファイルのパスが使用されます
        },
        {
            'label': '入力ファイル2',
            'type': 'file',
            'file_types': [("画像ファイル", "*.png *.jpg *.jpeg"), ("全てのファイル", "*.*")],
            'initial_path': None
        },
        {
            'label': 'エクスポートフォルダ',
            'type': 'folder',
            'initial_path': None  # 初期パスを指定しない場合、ホームディレクトリが使用されます
        },
        # 必要に応じてさらにファイル選択ボックスやフォルダ選択ボックスを追加
        # {
        #     'label': 'ファイル3',
        #     'type': 'file',
        #     'file_types': [("PDFファイル", "*.pdf"), ("全てのファイル", "*.*")],
        #     'initial_path': "/path/to/default/file3.pdf"
        # },
        # {
        #     'label': '設定フォルダ',
        #     'type': 'folder',
        #     'initial_path': "/path/to/default/settings_folder"
        # },
        # ...
    ]

    app = FileSelectorApp(root, file_configs)
    root.mainloop()