import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# 1. Load environment variables
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

if not DB_URL:
    raise ValueError("No DATABASE_URL found.")

# Create the database engine
engine = create_engine(DB_URL).execution_options(isolation_level="AUTOCOMMIT")

# 2. Define commands to fix missing data and apply constraints
sql_commands = [
    # --- Step 1: Inject missing Customer zip codes ---
    # Explicitly casting NULL to double precision so PostgreSQL accepts it
    """
    INSERT INTO olist_geolocation_clean (geolocation_zip_code_prefix, city, state, centroid_lat, centroid_lng)
    SELECT DISTINCT customer_zip_code_prefix, 'Unknown', 'Unknown', CAST(NULL AS double precision), CAST(NULL AS double precision)
    FROM olist_customers_dataset
    WHERE customer_zip_code_prefix NOT IN (SELECT geolocation_zip_code_prefix FROM olist_geolocation_clean);
    """,
    
    # --- Step 2: Inject missing Seller zip codes ---
    """
    INSERT INTO olist_geolocation_clean (geolocation_zip_code_prefix, city, state, centroid_lat, centroid_lng)
    SELECT DISTINCT seller_zip_code_prefix, 'Unknown', 'Unknown', CAST(NULL AS double precision), CAST(NULL AS double precision)
    FROM olist_sellers_dataset
    WHERE seller_zip_code_prefix NOT IN (SELECT geolocation_zip_code_prefix FROM olist_geolocation_clean);
    """,
    
    # --- Step 3: Apply the Foreign Keys safely ---
    "ALTER TABLE olist_customers_dataset ADD CONSTRAINT fk_customer_geo FOREIGN KEY (customer_zip_code_prefix) REFERENCES olist_geolocation_clean(geolocation_zip_code_prefix);",
    "ALTER TABLE olist_sellers_dataset ADD CONSTRAINT fk_seller_geo FOREIGN KEY (seller_zip_code_prefix) REFERENCES olist_geolocation_clean(geolocation_zip_code_prefix);"
]

def fix_and_link():
    with engine.connect() as connection:
        for command in sql_commands:
            preview = command.strip().replace('\n', ' ')[:75]
            print(f"Executing: {preview}...")
            try:
                connection.execute(text(command))
                print("✅ Success!\n")
            except Exception as e:
                print(f"❌ Error: {e}\n")

if __name__ == "__main__":
    print("Fixing missing zip codes and linking tables...")
    fix_and_link()
    print("Database schema is now fully complete and connected!")