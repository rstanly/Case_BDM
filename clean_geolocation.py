import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# 1. Load environment variables
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

if not DB_URL:
    raise ValueError("No DATABASE_URL found. Please make sure your .env file is properly configured.")

# Create the database engine and set it to AUTOCOMMIT
engine = create_engine(DB_URL).execution_options(isolation_level="AUTOCOMMIT")

# 2. Define the SQL commands to clean the geolocation data
sql_commands = [
    # Drop the clean table if it already exists (prevents errors if you run this twice)
    "DROP TABLE IF EXISTS olist_geolocation_clean CASCADE;",
    
    # Create the new clean table with grouped zip codes and average coordinates
    """
    CREATE TABLE olist_geolocation_clean AS
    SELECT 
        geolocation_zip_code_prefix,
        MAX(geolocation_city) as city,
        MAX(geolocation_state) as state,
        AVG(geolocation_lat) as centroid_lat,
        AVG(geolocation_lng) as centroid_lng
    FROM olist_geolocation_dataset
    GROUP BY geolocation_zip_code_prefix;
    """,
    
    # Apply the Primary Key to the new clean table
    "ALTER TABLE olist_geolocation_clean ADD PRIMARY KEY (geolocation_zip_code_prefix);"
]

def clean_geolocation_table():
    with engine.connect() as connection:
        for command in sql_commands:
            # Print a preview of the command being executed
            preview = command.strip().replace('\n', ' ')
            print(f"Executing: {preview[:75]}...")
            
            try:
                # Execute the SQL command securely
                connection.execute(text(command))
                print("✅ Success!\n")
            except Exception as e:
                print(f"❌ Error applying command: {e}\n")

if __name__ == "__main__":
    print("Starting geolocation cleanup...")
    clean_geolocation_table()
    print("Finished cleaning geolocation data!")