import psycopg2
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

hostname = os.getenv('DB_HOST')
port = os.getenv('DB_PORT')
database = os.getenv('DB_NAME')
username = os.getenv('DB_USER')
password = os.getenv('DB_PASSWORD')

class DatabaseConnection:
    def __init__(self):
        self.connection = None
        self.connect()

    def connect(self):
        try:
            self.connection = psycopg2.connect(
                host=hostname,
                port=port,
                database=database,
                user=username,
                password=password
            )
            print("Database connection established")
        except Exception as error:
            print(f"Error connecting to database: {error}")
            self.connection = None

    def execute_query(self, query):
        if not self.connection:
            self.connect()
            if not self.connection:
                return None

        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            colnames = [desc[0] for desc in cursor.description]
            return pd.DataFrame(rows, columns=colnames)
        except Exception as error:
            print(f"Query execution error: {error}")
            if "connection" in str(error).lower():
                print("Attempting to reconnect...")
                self.connect()
                return self.execute_query(query) if self.connection else None
            return None
        finally:
            if cursor:
                cursor.close()

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None
            print("Database connection closed")

## Example usage
# db = DatabaseConnection()
# query = "SELECT * FROM country"
# df = db.execute_query(query)
# print(df)

# if done with the connection, close it
# db.close()
