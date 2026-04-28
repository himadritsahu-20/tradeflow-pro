import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.express as px
from datetime import datetime
import hashlib

st.set_page_config(page_title="TradeFlow Pro", layout="wide")

st.markdown("""
<style>
.metric-card { background: linear-gradient(45deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 15px; color: white; text-align: center; }
.live-badge { background: #00ff88; color: black; padding: 5px 12px; border-radius: 20px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_db():
    conn = sqlite3.connect('tradeflow.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT, role TEXT, store TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY, timestamp TEXT, username TEXT, store TEXT, product TEXT, quantity INTEGER, price REAL, profit REAL)''')
    
    # DEFAULT USERS
    default_users = [
        ('Himadri', hashlib.sha256('KIIT-24'.encode()).hexdigest()[:15], 'admin', None),
        ('admin', hashlib.sha256('123456'.encode()).hexdigest()[:15], 'admin', None)
    ]
    conn.executemany("INSERT OR IGNORE INTO users VALUES (?,?,?,?)", default_users)
    
    # SAMPLE SALES (for demo)
    sample_sales = [
        (datetime.now().isoformat(), 'Himadri', 'NYC', 'Laptop', 3, 1200, 900),
        (datetime.now().isoformat(), 'admin', 'LA', 'iPhone 15', 2, 999, 499)
    ]
    conn.executemany("INSERT OR IGNORE INTO sales VALUES (NULL,?,?,?,?,?,?,?)", sample_sales)
    
    conn.commit()
    return conn

conn = init_db()

# Session
if 'user' not in st.session_state:
    st.session_state.user = None

def login(username, password):
    phash = hashlib.sha256(password.encode()).hexdigest()[:15]
    df = pd.read_sql_query("SELECT * FROM users WHERE username=? AND password_hash=?", 
                          conn, params=(username, phash))
    return {'logged_in': True, 'username': username, 'role': df.iloc[0]['role']} if len(df) > 0 else None

# Sidebar
with st.sidebar:
    st.header("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("LOGIN"):
        user = login(username, password)
        if user:
            st.session_state.user = user
            st.rerun()
        else:
            st.error("❌ Wrong!")
    
    if st.session_state.user:
        st.success(f"👋 {st.session_state.user['username']}")
        if st.button("Logout"): st.session_state.user = None; st.rerun()

if not st.session_state.user:
    st.title("🏪 TradeFlow Pro")
    st.info("👈 Login sidebar")
    st.stop()

# Dashboard
st.title("🏪 TradeFlow Pro")
st.header(f"Welcome {st.session_state.user['username']}!")

# KPIs - FIXED
df_sales = pd.read_sql_query("SELECT * FROM sales", conn)
kpis = {
    'revenue': df_sales['price'].sum(),
    'profit': df_sales['profit'].sum(),
    'orders': len(df_sales)
}

col1, col2, col3 = st.columns(3)
col1.metric("💰 Revenue", f"${kpis['revenue']:,.0f}")
col2.metric("💵 Profit", f"${kpis['profit']:,.0f}")
col3.metric("📦 Orders", kpis['orders'])

# Sales Form
st.header("➕ Add Sale")
col1, col2 = st.columns(2)
with col1:
    store = st.selectbox("Store", ['NYC', 'LA', 'Chicago', 'Miami', 'Boston'])
    product = st.selectbox("Product", ['iPhone 15', 'MacBook', 'Samsung', 'Laptop', 'Headphones'])
with col2:
    qty = st.number_input("Qty", min_value=1, value=1)
    price = st.number_input("Price", min_value=100.0, value=999.0)

if st.button("🚀 Add Sale"):
    profit = price * 0.25 * qty
    conn.execute("INSERT INTO sales (timestamp,username,store,product,quantity,price,profit) VALUES (datetime('now'),?,?,?,?,?,?)",
                (st.session_state.user['username'], store, product, qty, price, profit))
    conn.commit()
    
    # Auto-export to file
    df_auto = pd.read_sql_query("SELECT * FROM sales", conn)
    df_auto.to_csv("TradeFlow_Master_Sync.xls", index=False)
    
    st.success("✅ Added & Auto-Exported to TradeFlow_Master_Sync.xls!")
    st.rerun()

# Charts - FIXED
if len(df_sales) > 0:
    st.header("📊 Analytics")
    col1, col2 = st.columns(2)
    
    with col1:
        store_df = df_sales.groupby('store')['price'].sum().reset_index()
        fig1 = px.bar(store_df, x='store', y='price', title="Revenue by Store")
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        prod_df = df_sales.groupby('product')['profit'].sum().reset_index()
        fig2 = px.pie(prod_df, values='profit', names='product', title="Profit by Product")
        st.plotly_chart(fig2, use_container_width=True)

# Table
st.subheader("📋 Recent Sales")
st.dataframe(df_sales[['timestamp','store','product','quantity','price','profit']].tail(10).round(2))

# Export & Import
col1, col2 = st.columns(2)

with col1:
    st.subheader("📤 Export Data")
    if st.button("📥 Export CSV"):
        csv = df_sales.to_csv(index=False)
        st.download_button("Download P&L", csv, "tradeflow_pnl.csv", "text/csv")

with col2:
    st.subheader("📥 Import Data")
    uploaded_file = st.file_uploader("Upload previous CSV/XLS export", type=["csv", "xls"])
    if uploaded_file is not None:
        if st.button("Load Data to DB"):
            try:
                # The export is a CSV regardless of .csv or .xls extension
                df_upload = pd.read_csv(uploaded_file)
                # Drop the old 'id' column so SQLite generates new fresh IDs automatically
                df_upload = df_upload.drop(columns=['id'], errors='ignore')
                
                # Recreate the table properly so the primary key autoincrement isn't destroyed
                conn.execute("DROP TABLE IF EXISTS sales")
                conn.execute('''CREATE TABLE sales (id INTEGER PRIMARY KEY, timestamp TEXT, username TEXT, store TEXT, product TEXT, quantity INTEGER, price REAL, profit REAL)''')
                
                # Append data safely
                df_upload.to_sql("sales", conn, if_exists="append", index=False)
                
                # Sync back to master file with new generated IDs
                df_auto = pd.read_sql_query("SELECT * FROM sales", conn)
                df_auto.to_csv("TradeFlow_Master_Sync.xls", index=False)
                
                st.success("✅ Data Imported & DB Fixed Successfully! Refreshing...")
                st.rerun()
            except Exception as e:
                st.error(f"Error reading file: {e}")