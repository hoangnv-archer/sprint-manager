import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Velocity Analyzer", layout="wide")

# Kết nối Sheet
conn = st.connection("gsheets", type=GSheetsConnection)
URL = "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592"

# 1. Đọc và tìm hàng tiêu đề
raw_df = conn.read(spreadsheet=URL, header=None)
header_idx = next((i for i, row in raw_df.iterrows() if "Userstory/Todo" in row.values), 14)

# 2. Xử lý dữ liệu
df = conn.read(spreadsheet=URL, skiprows=header_idx, ttl=0)
df.columns = [str(c).strip() for c in df.columns]

# Sửa lỗi số thập phân dấu phẩy
for c in ['Estimate Dev', 'Real']:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

# Lọc các dòng có PIC (bỏ dòng tiêu đề màu xám)
df_clean = df[df['PIC'].notna() & (df['PIC'].str.strip() != '')].copy()

st.title("🚀 Phân Tích Tốc Độ Sprint")

# 3. Tổng hợp tốc độ theo từng người
v_df = df_clean.groupby('PIC')[['Estimate Dev', 'Real']].sum().reset_index()
v_df['Efficiency'] = (v_df['Estimate Dev'] / v_df['Real'] * 100).fillna(0).round(1)

# Hiển thị bảng dữ liệu
st.subheader("📊 Bảng chỉ số năng suất")
st.dataframe(v_df, use_container_width
