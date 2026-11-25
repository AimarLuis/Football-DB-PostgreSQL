"""Step 0 - Download the raw CSV files from Kaggle.

Dataset: "Football Data from Transfermarkt" (davidcariboo/player-scores), CC0 licence.
The files are NOT committed to the repository: anyone can get them again with

    python download_data.py

kagglehub keeps the files in its own cache folder (outside the repository) and
returns the path. config.data_dir() asks kagglehub for that same path.
"""
import os

from config import data_dir

path = data_dir()
print("Raw files are in:", path)
for name in sorted(os.listdir(path)):
    size_mb = os.path.getsize(os.path.join(path, name)) / 1e6
    print(f"  {name:28s} {size_mb:8.1f} MB")
