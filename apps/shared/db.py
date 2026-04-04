import os

import psycopg2


def connect():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "jesse_signal_executor"),
        user=os.getenv("POSTGRES_USER", "app_user"),
        password=os.getenv("POSTGRES_PASSWORD", "app_password"),
    )
