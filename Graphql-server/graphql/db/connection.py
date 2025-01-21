import psycopg2
from psycopg2 import pool

# Initialize a connection pool for PostgreSQL
try:
    connection_pool = pool.SimpleConnectionPool(
        1,  # Minimum number of connections in the pool
        10,  # Maximum number of connections in the pool
        user="myuser",
        password="mypassword",
        host="db",  # Host address of the database server
        port="5432",  # Database port
        database="mydatabase"  # Name of the database
    )
except Exception as e:
    print("Error connecting to PostgreSQL:", e)
    raise

def execute_query(query, params=None):
    connection = connection_pool.getconn()  # Get a connection from the pool
    try:
        with connection:  # Ensure the transaction is committed automatically
            with connection.cursor() as cursor:
                cursor.execute(query, params)  # Execute the query
                if cursor.description:  # Check if the query returns data (e.g., SELECT or RETURNING)
                    return cursor.fetchall()  # Fetch and return all rows
    except Exception as e:
        print(f"Error executing query: {e}")
        raise
    finally:
        connection_pool.putconn(connection)  # Return the connection to the pool
