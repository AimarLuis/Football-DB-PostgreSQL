"""The only place with connection settings (pattern of Practice 9: db.py + password.txt).

password.txt holds the PostgreSQL password in one line and is listed in .gitignore.
"""
import os

import kagglehub
import psycopg2

DATASET = "davidcariboo/player-scores/versions/679"   # fixed version = same numbers every time
DB_NAME = "football"
HERE = os.path.dirname(os.path.abspath(__file__))


def data_dir():
    """Folder with the raw CSV files (downloads them the first time)."""
    return kagglehub.dataset_download(DATASET)


def read_password():
    with open(os.path.join(HERE, "password.txt")) as f:
        return f.read().strip()


def connect(dbname=DB_NAME):
    """Open a new psycopg2 connection to the local PostgreSQL server."""
    # lc_messages=C: server error messages in plain English (no accents broken in the console)
    return psycopg2.connect(host="localhost", port=5432, dbname=dbname,
                            user="postgres", password=read_password(),
                            options="-c lc_messages=C")
