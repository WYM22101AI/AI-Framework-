import duckdb

# Connect to a local DuckDB file database
conn = duckdb.connect("market_data.duckdb")

# Create a table with 'id' and 'name' columns
conn.execute(
    """
    CREATE TABLE IF NOT EXISTS test (
        id INTEGER,
        name VARCHAR
    )
"""
)

# Insert a single row of data into the table
conn.execute("INSERT INTO test VALUES (1, 'Hello DuckDB')")

# Query all rows and fetch the results as a list of tuples
result = conn.execute("SELECT * FROM test").fetchall()

# Print the retrieved data
print(result)

# Close the database connection
conn.close()
