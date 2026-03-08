# check_storage.py
import json
import psycopg2
from app.utils import get_redis_connection, get_pg_connection

def check_redis():
    r = get_redis_connection()
    data = r.get("latest_session")
    if data:
        print("🔹 Redis latest_session:")
        print(json.loads(data))
    else:
        print("⚠️ No latest_session found in Redis")

def check_postgres():
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, repo, files, overall_pre_confidence, overall_post_confidence, results
        FROM public.analysis_runs
        ORDER BY id DESC
        LIMIT 1
    """)
    row = cur.fetchone()
    if row:
        print("\n🔹 PostgreSQL latest run:")
        print(f"ID: {row[0]}, Repo: {row[1]}, Files: {row[2]}, Pre: {row[3]}, Post: {row[4]}")
        print("\nResults JSON:")
        print(json.dumps(row[5], indent=2))
    else:
        print("⚠️ No runs found in PostgreSQL")
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_redis()
    check_postgres()
