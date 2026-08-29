import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# 1. Load environment variables from the .env file
load_dotenv()

# Fetch the Database URL
DB_URL = os.getenv("DATABASE_URL")

if not DB_URL:
    raise ValueError("No DATABASE_URL found. Please make sure your .env file is properly configured and in the same directory.")

# Create the database engine
engine = create_engine(DB_URL)

# 2. Define the exact files to upload
files_to_upload = [
    "olist_geolocation_dataset.csv",
    "product_category_name_translation.csv",
    "olist_customers_dataset.csv",
    "olist_sellers_dataset.csv",
    "olist_products_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv"
]

def migrate_to_supabase():
    for file_name in files_to_upload:
        # Generate the table name by removing the .csv extension
        table_name = file_name.replace(".csv", "")
        print(f"Reading {file_name}...")
        
        try:
            # Load CSV into a Pandas DataFrame
            df = pd.read_csv(file_name)
            print(f"Uploading {len(df)} rows to {table_name}...")
            
            # Write the DataFrame to the Supabase PostgreSQL database
            df.to_sql(
                name=table_name,
                con=engine,
                if_exists="replace", # 'replace' drops the table if it exists and creates a new one
                index=False,
                method="multi",      # Uses multiple inserts for better performance
                chunksize=5000       # Chunks the data to prevent memory issues with large datasets
            )
            print(f"Successfully uploaded {table_name}!\n")
            
        except Exception as e:
            print(f"An error occurred while uploading {file_name}: {e}\n")

if __name__ == "__main__":
    migrate_to_supabase()