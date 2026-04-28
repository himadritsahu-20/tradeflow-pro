import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.express as px
from datetime import datetime
import hashlib
import time

# Page config
st.set_page_config(page_title="TradeFlow Pro", layout="wide")

# Custom CSS
st.markdown("""
<style>
.metric-card { background: linear-gradient(45deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 15px; color: white; text-align: center; }
.live-badge { background: #00ff88; color: black; padding: 5px 12px; border-radius: 20px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Database
@st.cache_resource
def init_db():
    conn = sqlite3.connect('tradeflow.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT, role TEXT, store TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY, timestamp TEXT, username TEXT, store TEXT, product TEXT, quantity INTEGER, price REAL, profit REAL)''')
    conn.commit()
    return conn

conn = init_db()

# User session
if 'user' not in st.session_state:
    st.session_state.user = None

def login(username, password):
    phash = hashlib.sha256(password.encode()).hexdigest()[:15]
    df = pd.read_sql_query("SELECT * FROM users WHERE username=? AND password_hash=?", 
                          conn, params=(username, phash))
    if len(df) > 0:
        return {'logged_in': True, 'username': username, 'role': df.iloc[0]['role']}
    return None

# Sidebar Login
with st.sidebar:
    st.header("🔐 Login")
    username = st.text_input("Username", placeholder="Himadri")
    password = st.text_input("Password", type="password", placeholder="29092005")
    if st.button("LOGIN"):
        user = login(username, password)
        if user:
            st.session_state.user = user
            st.success(f"✅ {user['username']} logged in!")
        else:
            st.error("❌ Wrong credentials")
    
    if st.session_state.user:
        st.info(f"👋 {st.session_state.user['username']}")
        if st.button("🚪 Logout"):
            st.session_state.user = None
            st.rerun()

if not st.session_state.user:
    st.title("🏪 TradeFlow Pro")
    st.info("👈 Login in sidebar")
    st.stop()

# Main Dashboard
st.title("🏪 TradeFlow Pro")
st.header(f"Welcome {st.session_state.user['username']}!")

# KPIs
conn = sqlite3.connect('tradeflow.db', check_same_thread=False)
df_sales = pd.read_sql_query("SELECT * FROM sales", conn)
kpis = {
    'revenue': df_sales['price'].sum() if len(df_sales)>0 else 0,
    'profit': df_sales['profit'].sum() if len(df_sales)>0 else 0,
    'orders': len(df_sales)
}

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"""
    <div class="metric-card">
        <h1>${kpis['revenue']:,.0f}</h1>
        <p>💰 Revenue</p>
        <span class="live-badge">LIVE</span>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <h1>${kpis['profit']:,.0f}</h1> 
        <p>💵 Profit</p>
        <span class="live-badge">LIVE</span>
    </div>
    """, unsafe_allow_html=True)

# Sales Form
if st.session_state.user['role'] != 'viewer':
    st.header("➕ Add Sale")
    col1, col2 = st.columns(2)
    with col1:
        store = st.selectbox("Store", ['NYC','LA','Chicago'])
        product = st.selectbox("Product", ['iPhone 15','MacBook','Laptop'])
    with col2:
        qty = st.number_input("Quantity", min_value=1, max_value=50, value=1)
        price = st.number_input("Price $", min_value=100.0, value=999.0)
    
    if st.button("🚀 Add Sale", type="primary"):
        profit = (price * 0.25) * qty
        conn.execute("""INSERT INTO sales (timestamp, username, store, product, quantity, price, profit) 
                       VALUES (datetime('now'), ?,?,?,?, ?, ?)""", 
                    (st.session_state.user['username'], store, product, qty, price, profit))
        conn.commit()
        st.success("✅ Sale added! Refresh page for live update")
        st.rerun()

# Charts
st.header("📊 Analytics")
col1, col2 = st.columns(2)

with col1:
    store_rev = df_sales.groupby('store')['price'].sum().sort_values(ascending=False)
    fig1 = px.bar(x=store_rev.index, y=store_rev.values, title="Revenue by Store")
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    prod_profit = df_sales.groupby('product')['profit'].sum()
    fig2 = px.pie(values=prod_profit.values, names=prod_profit.index, title="Profit by Product")
    st.plotly_chart(fig2, use_container_width=True)

# Recent Sales
st.subheader("📋 Recent Sales")
st.dataframe(df_sales[['timestamp','store','product','quantity','price','profit']].tail(20).round(2))

# Export
if st.button("📥 Download P&L CSV"):
    filename = f"tradeflow_pnl_{st.session_state.user['username']}.csv"
    df_sales.to_csv(filename, index=False)
    st.download_button("Download", df_sales.to_csv(index=False), filename, "text/csv")