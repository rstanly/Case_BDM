import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# 1. Load environment variables
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

if not DB_URL:
    raise ValueError("No DATABASE_URL found. Please make sure your .env file is properly configured.")

# Create the database engine and set it to AUTOCOMMIT
# This makes the execution robust: one failed constraint won't abort the entire script
engine = create_engine(DB_URL).execution_options(isolation_level="AUTOCOMMIT")

# 2. Define the SQL commands to map the ERD relationships
sql_commands = [
    # --- Primary Keys ---
    # Updated to the exact column name found in the CSV
    "ALTER TABLE olist_geolocation_dataset ADD PRIMARY KEY (geolocation_zip_code_prefix);",
    "ALTER TABLE olist_customers_dataset ADD PRIMARY KEY (customer_id);",
    "ALTER TABLE olist_sellers_dataset ADD PRIMARY KEY (seller_id);",
    "ALTER TABLE olist_products_dataset ADD PRIMARY KEY (product_id);",
    "ALTER TABLE olist_orders_dataset ADD PRIMARY KEY (order_id);",
    
    # --- Foreign Keys ---
    # Link Orders to Customers
    "ALTER TABLE olist_orders_dataset ADD CONSTRAINT fk_order_customer FOREIGN KEY (customer_id) REFERENCES olist_customers_dataset(customer_id);",
    
    # Link Order Items to Orders, Products, and Sellers
    "ALTER TABLE olist_order_items_dataset ADD CONSTRAINT fk_item_order FOREIGN KEY (order_id) REFERENCES olist_orders_dataset(order_id);",
    "ALTER TABLE olist_order_items_dataset ADD CONSTRAINT fk_item_product FOREIGN KEY (product_id) REFERENCES olist_products_dataset(product_id);",
    "ALTER TABLE olist_order_items_dataset ADD CONSTRAINT fk_item_seller FOREIGN KEY (seller_id) REFERENCES olist_sellers_dataset(seller_id);",
    
    # Link Payments to Orders
    "ALTER TABLE olist_order_payments_dataset ADD CONSTRAINT fk_payment_order FOREIGN KEY (order_id) REFERENCES olist_orders_dataset(order_id);",
    
    # Link Reviews to Orders
    "ALTER TABLE olist_order_reviews_dataset ADD CONSTRAINT fk_review_order FOREIGN KEY (order_id) REFERENCES olist_orders_dataset(order_id);"
]

def apply_schema_constraints():
    with engine.connect() as connection:
        for command in sql_commands:
            print(f"Executing: {command[:75]}...")
            try:
                # Execute the SQL command securely
                connection.execute(text(command))
                print("✅ Success!\n")
            except Exception as e:
                # If a constraint fails, it safely prints the error and continues
                print(f"❌ Error applying constraint: {e}\n")

if __name__ == "__main__":
    print("Starting robust schema configuration...")
    apply_schema_constraints()
    print("Finished applying schema constraints!")