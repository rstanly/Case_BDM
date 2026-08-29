import os
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine
from dotenv import load_dotenv
import plotly.express as px
import math

# --- Configuration & Setup ---
st.set_page_config(page_title="Executive E-Commerce Overview", layout="wide")
st.title("🌐 Executive E-Commerce Business Overview")

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
    
    # Added s.seller_id to track marketplace size
    query = """
        SELECT 
            o.order_id,
            o.order_purchase_timestamp::date AS order_date,
            o.order_delivered_carrier_date::date AS carrier_date,
            o.order_delivered_customer_date::date AS delivery_date,
            o.order_estimated_delivery_date::date AS estimated_date,
            o.order_status,
            p.payment_value,
            p.payment_type,
            p.payment_installments,
            i.price,
            i.freight_value,
            COALESCE(pt.product_category_name_english, pr.product_category_name, 'Unknown') AS category,
            c.customer_state,
            c.customer_city,
            s.seller_id,
            s.seller_state,
            r.review_score,
            g.centroid_lat AS latitude,
            g.centroid_lng AS longitude
        FROM olist_orders_dataset o
        JOIN (
            SELECT order_id, SUM(payment_value) as payment_value, 
                   MAX(payment_type) as payment_type, MAX(payment_installments) as payment_installments
            FROM olist_order_payments_dataset GROUP BY order_id
        ) p ON o.order_id = p.order_id
        JOIN olist_order_items_dataset i ON o.order_id = i.order_id
        JOIN olist_products_dataset pr ON i.product_id = pr.product_id
        LEFT JOIN product_category_name_translation pt ON pr.product_category_name = pt.product_category_name
        JOIN olist_customers_dataset c ON o.customer_id = c.customer_id
        JOIN olist_sellers_dataset s ON i.seller_id = s.seller_id
        LEFT JOIN (
            SELECT order_id, MAX(review_score) as review_score 
            FROM olist_order_reviews_dataset GROUP BY order_id
        ) r ON o.order_id = r.order_id
        LEFT JOIN olist_geolocation_clean g ON c.customer_zip_code_prefix = g.geolocation_zip_code_prefix;
    """
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    
    # Format dates
    df['order_date'] = pd.to_datetime(df['order_date'])
    df['carrier_date'] = pd.to_datetime(df['carrier_date'])
    df['delivery_date'] = pd.to_datetime(df['delivery_date'])
    df['estimated_date'] = pd.to_datetime(df['estimated_date'])
    
    # Map state names
    df['customer_state_full'] = df['customer_state'].map(STATE_NAMES).fillna(df['customer_state'])
    df['seller_state_full'] = df['seller_state'].map(STATE_NAMES).fillna(df['seller_state'])
    
    # Advanced Calculations
    df['delivery_days'] = (df['delivery_date'] - df['order_date']).dt.days
    df['is_on_time'] = df['delivery_date'] <= df['estimated_date']
    
    return df

with st.spinner("Loading business data..."):
    df = load_master_data()

# --- SIDEBAR FILTERS ---
st.sidebar.header("🎯 Dashboard Filters")
filtered_df = df.copy()

with st.sidebar.expander("📦 Order Filters", expanded=True):
    min_date = df['order_date'].min().date()
    max_date = df['order_date'].max().date()
    date_range = st.date_input("Order Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    all_statuses = sorted(df['order_status'].dropna().unique().tolist())
    selected_status = st.multiselect("Order Status", options=all_statuses, default=['delivered'])

with st.sidebar.expander("🧑‍🤝‍🧑 Customer Filters"):
    all_cust_states = sorted(df['customer_state_full'].dropna().unique().tolist())
    selected_cust_states = st.multiselect("Customer State", options=all_cust_states, default=[])
    if selected_cust_states:
        available_cities = sorted(df[df['customer_state_full'].isin(selected_cust_states)]['customer_city'].dropna().unique().tolist())
    else:
        available_cities = sorted(df['customer_city'].dropna().unique().tolist())
    selected_cust_cities = st.multiselect("Customer City", options=available_cities, default=[])

with st.sidebar.expander("🏪 Seller Filters"):
    all_seller_states = sorted(df['seller_state_full'].dropna().unique().tolist())
    selected_seller_states = st.multiselect("Seller State", options=all_seller_states, default=[])

with st.sidebar.expander("🏷️ Product Filters"):
    all_categories = sorted(df['category'].dropna().unique().tolist())
    selected_categories = st.multiselect("Product Category", options=all_categories, default=[])
    max_price = math.ceil(df['price'].max())
    price_range = st.slider("Item Price Range (BRL)", 0, max_price, (0, max_price))

with st.sidebar.expander("💳 Payments & Reviews"):
    all_payments = sorted(df['payment_type'].dropna().unique().tolist())
    selected_payment = st.multiselect("Payment Type", options=all_payments, default=[])
    all_scores = sorted(df['review_score'].dropna().unique().tolist())
    selected_scores = st.multiselect("Review Score (1-5)", options=all_scores, default=[])

# --- APPLY FILTERS ---
if len(date_range) == 2:
    start_date, end_date = date_range
    filtered_df = filtered_df[(filtered_df['order_date'].dt.date >= start_date) & (filtered_df['order_date'].dt.date <= end_date)]

if selected_status:
    filtered_df = filtered_df[filtered_df['order_status'].isin(selected_status)]
if selected_cust_states:
    filtered_df = filtered_df[filtered_df['customer_state_full'].isin(selected_cust_states)]
if selected_cust_cities:
    filtered_df = filtered_df[filtered_df['customer_city'].isin(selected_cust_cities)]
if selected_seller_states:
    filtered_df = filtered_df[filtered_df['seller_state_full'].isin(selected_seller_states)]
if selected_categories:
    filtered_df = filtered_df[filtered_df['category'].isin(selected_categories)]
if selected_payment:
    filtered_df = filtered_df[filtered_df['payment_type'].isin(selected_payment)]
if selected_scores:
    filtered_df = filtered_df[filtered_df['review_score'].isin(selected_scores)]

filtered_df = filtered_df[(filtered_df['price'] >= price_range[0]) & (filtered_df['price'] <= price_range[1])]

# --- CALCULATE KPIs ---
total_orders = filtered_df['order_id'].nunique()
total_items = len(filtered_df)
total_revenue = filtered_df.drop_duplicates(subset=['order_id'])['payment_value'].sum()
avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

active_sellers = filtered_df['seller_id'].nunique()
avg_review = filtered_df['review_score'].mean() if not filtered_df.empty else 0

avg_delivery_time = filtered_df['delivery_days'].mean() if not filtered_df.empty else 0
on_time_subset = filtered_df.dropna(subset=['is_on_time', 'delivery_date'])
on_time_rate = (on_time_subset['is_on_time'].sum() / len(on_time_subset)) * 100 if not on_time_subset.empty else 0
avg_freight = filtered_df['freight_value'].mean() if not filtered_df.empty else 0

# --- RENDER KPI CARDS ---
st.markdown("### 💰 Financial Performance")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Total Revenue", value=f"R$ {total_revenue:,.0f}")
with col2:
    st.metric(label="Total Orders", value=f"{total_orders:,}")
with col3:
    st.metric(label="Avg Order Value (AOV)", value=f"R$ {avg_order_value:,.2f}")

st.markdown("### 🛍️ Marketplace & Customer Experience")
col4, col5, col6 = st.columns(3)
with col4:
    st.metric(label="Total Items Sold", value=f"{total_items:,}")
with col5:
    st.metric(label="Active Sellers", value=f"{active_sellers:,}")
with col6:
    st.metric(label="Average Customer Rating", value=f"{avg_review:,.2f} / 5.0")

st.markdown("### 🚚 Operational Health")
col7, col8, col9 = st.columns(3)
with col7:
    st.metric(label="On-Time Delivery Rate", value=f"{on_time_rate:,.1f}%")
with col8:
    st.metric(label="Avg Delivery Time", value=f"{avg_delivery_time:,.1f} Days")
with col9:
    st.metric(label="Avg Freight Cost per Item", value=f"R$ {avg_freight:,.2f}")

st.divider()

# --- RENDER CHARTS ROW 1 ---
col_chart1, col_chart2 = st.columns([2, 1])

with col_chart1:
    st.markdown("### 📈 Revenue Trends")
    if not filtered_df.empty:
        trend_df = filtered_df.drop_duplicates(subset=['order_id']).copy()
        trend_df['month'] = trend_df['order_date'].dt.to_period('M').dt.to_timestamp()
        monthly_trend = trend_df.groupby('month')['payment_value'].sum().reset_index()
        
        fig_line = px.line(monthly_trend, x='month', y='payment_value', markers=True, labels={'month': 'Date', 'payment_value': 'Revenue (BRL)'})
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("No data available.")

with col_chart2:
    st.markdown("### 💳 Payment Preferences")
    if not filtered_df.empty:
        payment_counts = filtered_df.drop_duplicates(subset=['order_id', 'payment_type'])['payment_type'].value_counts().reset_index()
        payment_counts.columns = ['payment_type', 'count']
        fig_donut = px.pie(payment_counts, names='payment_type', values='count', hole=0.4)
        fig_donut.update_layout(margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig_donut, use_container_width=True)
    else:
        st.info("No data available.")

st.divider()

# --- RENDER CHARTS ROW 2 ---
col_chart3, col_chart4 = st.columns(2)

with col_chart3:
    st.markdown("### 🏆 Top 10 Product Categories")
    if not filtered_df.empty:
        cat_df = filtered_df.groupby('category')['order_id'].count().reset_index()
        cat_df = cat_df.rename(columns={'order_id': 'items_sold'}).sort_values('items_sold', ascending=False).head(10)
        
        fig_bar = px.bar(cat_df, x='items_sold', y='category', orientation='h', labels={'items_sold': 'Items Sold', 'category': 'Category'})
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("No data available.")

with col_chart4:
    st.markdown("### 🗺️ Customer Geographic Distribution")
    if not filtered_df.empty:
        geo_df = filtered_df.dropna(subset=['latitude', 'longitude'])
        geo_grouped = geo_df.groupby(['latitude', 'longitude', 'customer_state_full']).size().reset_index(name='customer_density')
        
        fig_map = px.scatter_map(
            geo_grouped, 
            lat="latitude", 
            lon="longitude", 
            size="customer_density",
            color="customer_density",
            hover_name="customer_state_full", 
            color_continuous_scale=px.colors.sequential.Plasma,
            zoom=3, 
            center={"lat": -14.235, "lon": -51.925}, 
            map_style="carto-positron" 
        )
        fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.info("No geographic data available.")