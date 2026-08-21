import duckdb

# 1. Connect to your existing database file
conn = duckdb.connect("market_data.duckdb")

# 2. Define the table name and target output file path
ticker = "TSLA"
csv_filename = f"{ticker}_history.csv"

print(f"Reading {ticker}_history from DuckDB and exporting to {csv_filename}...")

# 3. Use DuckDB's native COPY command to export directly to a CSV file
conn.execute(f"""
    COPY {ticker}_history 
    TO '{csv_filename}' 
    (HEADER, DELIMITER ',')
""")

print("Export complete! File generated successfully.")

# 4. Verification: Query the CSV directly using SQL without loading it into memory
print("\nVerifying CSV file content (First 3 rows):")
preview = conn.execute(f"SELECT timestamp, open, close FROM '{csv_filename}' LIMIT 3").fetchall()
for row in preview:
    print(row)

# Close the database connection
conn.close()

