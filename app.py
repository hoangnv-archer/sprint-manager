import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Sprint Velocity", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
URL = "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592"

try:
    # 1. Đọc dữ liệu thô
    raw_df = conn.read(spreadsheet=URL, header=None)
    
    # 2. Tìm hàng tiêu đề có chữ Userstory/Todo
    header_idx = None
    for i, row in raw_df.iterrows():
        if "Userstory/Todo" in row.values:
            header_idx = i
            break

    if header_idx is not None:
        # Đọc dữ liệu từ hàng tiêu đề
        df = conn.read(spreadsheet=URL, skiprows=header_idx, ttl=0)
        df.columns = [str(c).strip() for c in df.columns]

        # 3. Chuyển đổi số (xử lý dấu phẩy)
        for c in ['Estimate Dev', 'Real']:
            if c in df.columns:
                df[c] = df[c].astype(str).str.replace(',', '.')
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

        # 4. Lọc bỏ dòng tiêu đề nhóm (dòng không có tên PIC)
        df_tasks = df[df['PIC'].notna() & (df['PIC'] != '') & (df['PIC'] != '#N/A')].copy()

        st.title("🚀 Tổng hợp Tốc độ Team")

        # 5. Gom nhóm dữ liệu theo từng người
        # Tính Tổng Dự Kiến (Est), Tổng Thực Tế (Real)
        v_df = df_tasks.groupby('PIC')[['Estimate Dev', 'Real']].sum().reset_index()

        # Tính Hiệu suất: (Dự kiến / Thực tế) * 100
        v_df['Efficiency'] = (v_df['Estimate Dev'] / v_df['Real'] * 100).fillna(0).round(1)

        # Hiển thị bảng tổng hợp
        st.subheader("📊 Bảng chỉ số năng suất")
        st.table(v_df)

        # 6. Đánh giá Nhanh/Chậm
        st.subheader("🔍 Phân tích tốc độ cá nhân")
        cols = st.columns(len(v_df))
        for
