import pandas as pd
df = pd.read_csv("youtube_videos.csv")
print(df)  
print(df.shape)
print(df.columns)
print(df.duplicated().sum())