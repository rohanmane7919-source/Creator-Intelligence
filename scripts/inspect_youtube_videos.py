import os
import pandas as pd

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPTS_DIR)
DATA_DIR = os.path.join(ROOT_DIR, "data")
csv_path = os.path.join(DATA_DIR, "youtube_videos.csv") if os.path.exists(os.path.join(DATA_DIR, "youtube_videos.csv")) else "youtube_videos.csv"

df = pd.read_csv(csv_path)
print(df)  
print(df.shape)
print(df.columns)
print("Duplicates:", df.duplicated().sum())