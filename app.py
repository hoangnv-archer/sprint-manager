import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Sprint Velocity Analyzer", layout="wide")

# Kết nối dữ liệu an toàn
conn = st.connection("gsheets", type=GSheetsConnection)
URL = "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592"

try:
    # 1. Tìm hàng tiêu đề (thường là hàng 15 có chữ Userstory/Todo)
    raw_df = conn.read(spreadsheet=URL, header=None)
    header_idx = next((i for i, row in raw_df.iterrows() if "Userstory/Todo" in row.values), None)

    if header_idx is not None:
        # Đọc dữ liệu từ hàng tiêu đề trở đi
        df = conn.read(spreadsheet=URL, skiprows=header_idx, ttl=0)
        df.columns = [str(c).strip() for c in df.columns]

        # 2. Xử lý số liệu (Chuyển dấu phẩy 185,5 -> 185.5)
        for col in ['Estimate Dev', 'Real']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # 3. Lọc lấy các task có người phụ trách (PIC)
        df_clean = df[df['PIC'].notna() & (df['PIC'] != '#N/A') & (df['PIC'].str.strip() != '')].copy()

        st.title("🚀 Phân Tích Tốc Độ & Hiệu Suất Team")

        # 4. Tính toán tốc độ tổng hợp theo PIC
        velocity_df = df_clean.groupby('PIC').agg({
            'Estimate Dev': 'sum',
            'Real': 'sum',
