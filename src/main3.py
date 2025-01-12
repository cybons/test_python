import pandas as pd

# リストからデータフレームを作成する
data = {
    '名前': ['Alice', 'Bob', 'Charlie'],
    '年齢': [25, 30, 35],
    '性別': ['女性', '男性', 'その他']
}
df = pd.DataFrame(data)

# データフレームを表示する
print(df)

# データフレームの列を取得する
names = df['名前']
ages = df['年齢']

# 列を追加する
df['都市'] = ['東京', '大阪', '札幌']

# 条件に合うデータをフィルタリングする
filtered_df = df[df['年齢'] > 30]

# データフレームをCSVファイルに保存する
df.info()