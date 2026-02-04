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
    
    # 2. Tìm hàng tiêu đề (Userstory/Todo)
    header_idx = None
    for i, row in raw_df.iterrows():
        if "Userstory/Todo" in row.values:
            header_idx = i
            break

    if header_idx is not None:
        # 3. Đọc dữ liệu từ hàng tiêu đề trở đi
        df = conn.read(spreadsheet=URL, skiprows=header_idx, ttl=0)
        df.columns = [str(c).strip() for c in df.columns]

        # 4. Xử lý số liệu
        for c in ['Estimate Dev', 'Real']:
            if c in df.columns:
                df[c] = df[c].astype(str).str.replace(',', '.')
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

        # 5. Lọc task thực tế (Dòng có PIC)
        df_tasks = df[df['PIC'].notna() & (df['PIC'] != '')].copy()

        st.title("🚀 Phân Tích Tốc Độ Team")

        # 6. Gom nhóm tính tổng theo PIC
        v_df = df_tasks.groupby('PIC').agg({'Estimate Dev': 'sum', 'Real': 'sum'}).reset_index()

        # 7. Tính hiệu suất (%)
        v_df['Hiệu suất (%)'] = (v_df['Estimate Dev'] / v_df['Real'] * 100).fillna(0).round(1)

        # HIỂN THỊ BẢNG TỔNG HỢP
        st.subheader("📊 Bảng chỉ số tốc độ")
        st.table(v_df)

        # 8. Phân tích chi tiết từng người
        st.subheader("🔍 Đánh giá Nhanh / Chậm")
        cols = st.columns(len(v_df))
        
        for idx, row in v_df.iterrows():
            with cols[idx]:
                name = row['PIC']
                est = row['Estimate Dev']
                real = row['Real']
                
                st.write(f"**{name}**")
                if real > est:
                    st.error(f"⚠️ Chậm {real-est:.1f}h")
                elif real < est and real > 0:
                    st.success(f"⚡ Nhanh {est-real:.1f}h")
                else:
                    st.info("✅ Đúng hạn")
                
                st.metric("Hiệu suất", f"{row['Hiệu suất (%)']}%")

        # 9. Biểu đồ so sánh
        fig = px
