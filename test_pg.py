import psycopg2
from psycopg2.extras import Json

def main():
    try:
        conn = psycopg2.connect(
            dbname="reviewdb",
            user="postgres",
            password="admin123",
            host="localhost",
            port="5432"
        )
        cur = conn.cursor()

        # Insert a dummy row
        cur.execute(
            """
            INSERT INTO public.analysis_runs
            (repo, files, overall_pre_confidence, overall_post_confidence, results)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                "dummy_repo",
                1,
                95.0,
                97.0,
                Json({"message": "This is a test insert"})
            )
        )
        conn.commit()
        print("✅ Dummy row inserted successfully")

        # Fetch back the latest row
        cur.execute(
            """
            SELECT id, repo, files, overall_pre_confidence, overall_post_confidence, created_at
            FROM public.analysis_runs
            ORDER BY id DESC
            LIMIT 1;
            """
        )
        print("Latest row:", cur.fetchone())

        cur.close()
        conn.close()
    except Exception as e:
        print("❌ Insert failed:", e)

if __name__ == "__main__":
    main()
