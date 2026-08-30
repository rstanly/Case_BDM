Here is the .env file 
DATABASE_URL=postgresql://postgres.ydfbqgtlvnyqvkdcudtp:Kishorek2817s@aws-1-ap-northeast-2.pooler.supabase.com:5432/postgres

---

```markdown
# Brazilian E-Commerce Operations & Logistics Dashboard

A complete data engineering and analytics pipeline that transforms the Olist Brazilian E-Commerce dataset into a fully relational PostgreSQL database on Supabase. This project includes automated Python ETL scripts to clean and map geographic data, enforce strict referential integrity, and power a dynamic Streamlit dashboard tailored for supply chain analysis, specifically focusing on middle-mile and last-mile delivery metrics.

## 📦 Dataset
This project uses the public **Brazilian E-Commerce Public Dataset by Olist**.
* **Download the dataset here:** [Kaggle - Brazilian E-Commerce Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce?resource=download)

Extract the downloaded archive and place the following CSV files directly into the root directory of this project:
* `olist_geolocation_dataset.csv`
* `product_category_name_translation.csv`
* `olist_customers_dataset.csv`
* `olist_sellers_dataset.csv`
* `olist_products_dataset.csv`
* `olist_orders_dataset.csv`
* `olist_order_items_dataset.csv`
* `olist_order_payments_dataset.csv`
* `olist_order_reviews_dataset.csv`

---

## 🛠️ Prerequisites

1. Ensure you have Python installed.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt

```

3. Set up a PostgreSQL database using [Supabase](https://supabase.com/).
4. Create a `.env` file in the root directory using the provided `.env.example` template and add your database connection string.

---

## 🚀 Setup & Execution

Follow these scripts in order to build the database architecture and launch the visualization tool.

### Step 1: Upload Raw Data

Uploads the raw CSV files into Supabase using Pandas and SQLAlchemy.

```bash
python data_upload.py

```

### Step 2: Enforce Core Schema

Applies Primary Keys and Foreign Keys to the main operational tables (Orders, Customers, Items, Products, Sellers, Payments, and Reviews) to lock in referential integrity.

```bash
python apply_schema.py

```

### Step 3: Clean Geographic Data

The raw geolocation dataset contains duplicate zip codes with multiple coordinate points. This script creates a new clean table (`olist_geolocation_clean`) that groups zip codes by their geographic centroid (average latitude and longitude) to prevent Cartesian explosions during mapping.

```bash
python clean_geolocation.py

```

### Step 4: Finalize Relational Links

Injects placeholder records for missing master data and builds the final foreign keys linking the Customers and Sellers tables to the newly cleaned Geolocation table.

```bash
python link_geolocation.py

```

### Step 5: Launch the Dashboard

Starts the interactive Streamlit web application. The dashboard features live SQL queries, dynamic sidebar filters (by date, state, product category, and order status), and a Plotly Maplibre heatmap for geographic customer segmentation.

```bash
streamlit run dashboard.py

```

---

## 📊 Dashboard Features

* **Financial & Order KPIs:** Track total revenue, order volume, and average basket sizes.
* **Geographic Demand Heatmap:** Interactive plotting of customer density across Brazilian states for network planning.
* **Sales Volume Tracking:** Horizontal bar charts filtering top-moving product categories.
* **Revenue Trends:** Time-series analysis of monthly fulfillment and payment values.

```

***

This covers the entire pipeline from raw Kaggle data to the finished UI. Are you planning to deploy this Streamlit app to Streamlit Community Cloud next, or will you be keeping it running locally for your operations research?

```
