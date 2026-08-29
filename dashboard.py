import os
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine
from dotenv import load_dotenv
import plotly.express as px

# --- Configuration & Setup ---
st.set_page_config(page_title="Dynamic Operations Dashboard", layout="wide")
st.title("⚡ Dynamic E-Commerce Operations Dashboard")

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    st.error("DATABASE_URL missing. Please check your .env file.")
    st.stop()

# --- Brazilian State Mapping ---
STATE_NAMES = {
    'AC': 'Acre', 'AL': 'Alagoas', 'AP': 'Amapá', 'AM': 'Amazonas', 'BA': 'Bahia', 
    'CE': 'Ceará', 'DF': 'Distrito Federal', 'ES': 'Espírito Santo', 'GO': 'Goiás', 
    'MA': 'Maranhão', 'MT': 'Mato Grosso', 'MS': 'Mato Grosso do Sul', 'MG': 'Minas Gerais', 
    'PA': 'Pará', 'PB': 'Paraíba', 'PR': 'Paraná', 'PE': 'Pernambuco', 'PI': 'Piauí', 
    'RJ': 'Rio de Janeiro', 'RN': 'Rio Grande do Norte', 'RS': 'Rio Grande do Sul', 
    'RO': 'Rondônia', 'RR': 'Roraima', 'SC': 'Santa Catarina', 'SP': 'São Paulo', 
    'SE': 'Sergipe', 'TO': 'Tocantins'
}

# --- Data Fetching (Cached for Performance) ---
@st.cache_data(ttl=600) 
def load_master_data():
    engine = create_engine(DB_URL)
    
    query = """
        SELECT 
            o.order_id,
            o.order_purchase_timestamp::date AS order_date,
            o.order_status,
            p.payment_value,
            p.payment_type,
            COALESCE(pt.product_category_name_english, pr.product_category_name, 'Unknown') AS category,
            c.customer_state,
            g.centroid_lat AS latitude,
            g.centroid_lng AS longitude
        FROM olist_orders_dataset o
        JOIN (
            SELECT order_id, SUM(payment_value) as payment_value, MAX(payment_type) as payment_type 
            FROM olist_order_payments_dataset GROUP BY order_id
        ) p ON o.order_id = p.order_id
        JOIN olist_order_items_dataset i ON o.order_id = i.order_id
        JOIN olist_products_dataset pr ON i.product_id = pr.product_id
        LEFT JOIN product_category_name_translation pt ON pr.product_category_name = pt.product_category_name
        JOIN olist_customers_dataset c ON o.customer_id = c.customer_id
        LEFT JOIN olist_geolocation_clean g ON c.customer_zip_code_prefix = g.geolocation_zip_code_prefix;
    """
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    
    # Format dates and map full state names
    df['order_date'] = pd.to_datetime(df['order_date'])
    df['state_full_name'] = df['customer_state'].map(STATE_NAMES).fillna(df['customer_state'])
    return df

with st.spinner("Loading semantic model..."):
    df = load_master_data()

# --- SIDEBAR FILTERS ---
st.sidebar.header("🎯 Dashboard Filters")

min_date = df['order_date'].min().date()
max_date = df['order_date'].max().date()
date_range = st.sidebar.date_input("Order Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

all_states = sorted(df['state_full_name'].dropna().unique().tolist())
selected_states = st.sidebar.multiselect("Filter by State", options=all_states, default=[])

all_categories = sorted(df['category'].dropna().unique().tolist())
selected_categories = st.sidebar.multiselect("Filter by Product Category", options=all_categories, default=[])

all_statuses = sorted(df['order_status'].dropna().unique().tolist())
selected_status = st.sidebar.multiselect("Filter by Order Status", options=all_statuses, default=['delivered'])

all_payments = sorted(df['payment_type'].dropna().unique().tolist())
selected_payment = st.sidebar.multiselect("Filter by Payment Type", options=all_payments, default=[])

# --- APPLY FILTERS ---
filtered_df = df.copy()

if len(date_range) == 2:
    start_date, end_date = date_range
    filtered_df = filtered_df[(filtered_df['order_date'].dt.date >= start_date) & (filtered_df['order_date'].dt.date <= end_date)]

if selected_states:
    filtered_df = filtered_df[filtered_df['state_full_name'].isin(selected_states)]
if selected_categories:
    filtered_df = filtered_df[filtered_df['category'].isin(selected_categories)]
if selected_status:
    filtered_df = filtered_df[filtered_df['order_status'].isin(selected_status)]
if selected_payment:
    filtered_df = filtered_df[filtered_df['payment_type'].isin(selected_payment)]

# --- CALCULATE KPIs ---
total_orders = filtered_df['order_id'].nunique()
total_revenue = filtered_df.drop_duplicates(subset=['order_id'])['payment_value'].sum()
avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

# --- RENDER KPI CARDS ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Total Revenue", value=f"R$ {total_revenue:,.0f}")
with col2:
    st.metric(label="Total Orders", value=f"{total_orders:,}")
with col3:
    st.metric(label="Avg Order Value", value=f"R$ {avg_order_value:,.2f}")

st.divider()

# --- RENDER CHARTS ---
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("### 📈 Revenue Over Time")
    if not filtered_df.empty:
        trend_df = filtered_df.drop_duplicates(subset=['order_id']).copy()
        trend_df['month'] = trend_df['order_date'].dt.to_period('M').dt.to_timestamp()
        monthly_trend = trend_df.groupby('month')['payment_value'].sum().reset_index()
        
        fig_line = px.line(monthly_trend, x='month', y='payment_value', markers=True, labels={'month': 'Date', 'payment_value': 'Revenue (BRL)'})
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("No data available.")

with col_right:
    st.markdown("### 🏆 Top Categories by Volume")
    if not filtered_df.empty:
        cat_df = filtered_df.groupby('category')['order_id'].count().reset_index()
        cat_df = cat_df.rename(columns={'order_id': 'items_sold'}).sort_values('items_sold', ascending=False).head(10)
        
        fig_bar = px.bar(cat_df, x='items_sold', y='category', orientation='h', labels={'items_sold': 'Items Sold', 'category': 'Category'})
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("No data available.")

st.divider()

# --- RENDER INTERACTIVE MAP ---
st.markdown("### 🗺️ Interactive Demand Heatmap")
if not filtered_df.empty:
    geo_df = filtered_df.dropna(subset=['latitude', 'longitude'])
    
    # Group by coordinates and the full state name for tooltips
    geo_grouped = geo_df.groupby(['latitude', 'longitude', 'state_full_name']).size().reset_index(name='customer_density')
    
    # Create an interactive Plotly map using the updated syntax
    fig_map = px.scatter_map(
        geo_grouped, 
        lat="latitude", 
        lon="longitude", 
        size="customer_density",
        color="customer_density",
        hover_name="state_full_name", # Shows full state name on hover
        color_continuous_scale=px.colors.sequential.Plasma,
        zoom=3, 
        center={"lat": -14.235, "lon": -51.925}, # Centers on Brazil
        map_style="carto-positron" # Updated for Plotly 5.24.0+
    )
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    
    st.plotly_chart(fig_map, use_container_width=True)
else:
    st.info("No geographic data available for the selected filters.")