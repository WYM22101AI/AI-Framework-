import duckdb

conn = duckdb.connect("data/market_data.duckdb")

print(conn.execute("SHOW TABLES").fetchall())

conn.close()



import duckdb

DB_PATH = "data/market_data.duckdb"

conn = duckdb.connect(DB_PATH)

print("Connected to:", DB_PATH)

print("\nTables:")
print(conn.execute("SHOW TABLES").fetchall())

conn.close()



import duckdb

conn = duckdb.connect("data/market_data.duckdb")

print(
    conn.execute(
        "SELECT COUNT(*) FROM TSLA_history_adjusted"
    ).fetchone()
)

conn.close()