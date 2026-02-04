import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Sprint Velocity", layout="wide")

# 1. Kết nối và đọc dữ liệu
conn = st.connection("gsheets", type=GSheetsConnection)
URL = "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592"

try:
    # Đọc thô để tìm hàng tiêu đề
    raw_df = conn.read(spreadsheet=URL, header=None)
    header_idx = next((i for i, row in raw_df.iterrows() if "Userstory/Todo" in row.values), None)

    if header_idx is not None:
        # Đọc dữ liệu chuẩn
        df = conn.read(spreadsheet=URL, skiprows=header_idx, ttl=0)
        df.columns = [str(c).strip() for c in df.columns]

        # Xử lý số liệu (185,5 -> 185.5)
        for c in ['Estimate Dev', 'Real']:
            if c in df.columns:
                df[c] = df[c].astype(str).str.replace(',', '.')
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

        # Lọc task có PIC (bỏ dòng tiêu đề màu xám)
        df_tasks = df[df['PIC'].notna() & (df['PIC'].str.strip() != '')].copy()

        st.title("🚀 Phân Tích Tốc Độ Team")

        # 2. Tổng hợp theo từng người
        v_df = df_tasks.groupby('PIC').agg({'Estimate Dev': 'sum', 'Real': 'sum'}).reset_index()
        v_df['Hiệu suất (%)'] = (v_df['Estimate Dev'] / v_df['Real'] * 100).fillna(0).round(1)
