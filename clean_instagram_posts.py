import pandas as pd
import os
print(os.getcwd())
df = pd.read_csv("instagram_posts.csv")
print(df)  
print(df.shape)
print(df.columns)
print(df.duplicated().sum())
print(df.drop_duplicates())
df.to_csv("instagram_posts_cleaned.csv", index=False, encoding="utf-8-sig")