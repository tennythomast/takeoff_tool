#!/usr/bin/env python3
import os
import sys
import time
import psycopg2

DB_NAME = os.getenv('POSTGRES_NAME', os.getenv('POSTGRES_DB', 'postgres'))
DB_USER = os.getenv('POSTGRES_USER', 'postgres')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')
DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
DB_PORT = int(os.getenv('POSTGRES_PORT', '5432'))

MAX_RETRIES = int(os.getenv('DB_WAIT_MAX_RETRIES', '60'))
SLEEP_SECONDS = float(os.getenv('DB_WAIT_INTERVAL', '1.0'))

if __name__ == '__main__':
    retries = 0
    while retries < MAX_RETRIES:
        try:
            conn = psycopg2.connect(
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT,
                connect_timeout=3,
            )
            conn.close()
            print(f"Database is ready at {DB_HOST}:{DB_PORT} (db={DB_NAME})")
            sys.exit(0)
        except Exception as e:
            print(f"Waiting for database {DB_HOST}:{DB_PORT} (db={DB_NAME})... ({retries+1}/{MAX_RETRIES}) - {e}")
            time.sleep(SLEEP_SECONDS)
            retries += 1
    print("Database did not become ready in time", file=sys.stderr)
    sys.exit(1)
