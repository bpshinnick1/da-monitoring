import pandas as pd
from sqlalchemy import create_engine, text
import os

# ── Connection ─────────────────────────────────────────────────────────────────
# Update these credentials if yours differ
DB_USER     = "postgres"
DB_PASSWORD = "postgres"
DB_HOST     = "localhost"
DB_PORT     = "5432"
DB_NAME     = "da_monitoring"

engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "generated")


def load_table(filename: str, table: str, parse_dates: list = None):
    filepath = os.path.join(DATA_DIR, filename)
    df = pd.read_csv(filepath, parse_dates=parse_dates)
    df.to_sql(table, engine, if_exists="append", index=False)
    print(f"  → {len(df):,} rows loaded into {table}")
    return df


if __name__ == "__main__":
    print("Loading data into PostgreSQL...\n")

    print("Loading premium_bordereaux...")
    load_table(
        "premium_bordereaux.csv",
        "premium_bordereaux",
        parse_dates=["inception_date", "expiry_date"]
    )

    print("Loading claims_bordereaux...")
    load_table(
        "claims_bordereaux.csv",
        "claims_bordereaux",
        parse_dates=["date_of_loss", "date_reported"]
    )

    print("Loading monthly_submissions...")
    load_table(
        "monthly_submissions.csv",
        "monthly_submissions",
        parse_dates=["month_end_date", "submission_date"]
    )

    print("\nVerifying row counts...")
    with engine.connect() as conn:
        for table in ["coverholders", "premium_bordereaux", "claims_bordereaux", "monthly_submissions"]:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            print(f"  {table}: {count:,} rows")

    print("\nDone.")