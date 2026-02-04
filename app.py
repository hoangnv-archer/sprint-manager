import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Sprint Velocity Analyzer", layout="wide")

# Kết nối dữ liệu an toàn
conn = st.connection("gsheets", type=GSheetsConnection)
URL = "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592"

try:
    # 1. Dò tìm hàng tiêu đề thực tế (Userstory/Todo)
    raw_df = conn.read(spreadsheet=URL, header=None)
    header_idx = next((i for i, row in raw_df.iterrows() if "Userstory/Todo" in row.values), None)

    if header_idx is not None:
        # Đọc dữ liệu từ hàng tiêu đề trở đi
        df = conn.read(spreadsheet=URL, skiprows=header_idx, ttl=0)
        df.columns = [str(c).strip() for c in df.columns]

        # 2. Xử lý định dạng số (185,5 -> 185.5)
        for col in ['Estimate Dev', 'Real']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # 3. Lọc lấy các dòng task có người phụ trách (PIC)
        # Loại bỏ các dòng tiêu đề nhóm màu xám
        df_clean = df[df['PIC'].notna() & (df['PIC'] != '#N/A') & (df['PIC'].str.strip() != '')].copy()

        st.title("🚀 Phân Tích Tốc Độ Team")

        # --- BẢNG TỔNG HỢP TỐC ĐỘ ---
        st.subheader("📊 Bảng tổng hợp hiệu suất theo cá nhân")
        
        # Nhóm dữ liệu theo từng người
        velocity_df = df_clean.groupby('PIC').agg({
            'Estimate Dev': 'sum',
            'Real': 'sum',
            'Userstory/Todo': 'count'
        }).reset_index()

        # Tính toán chỉ số Tốc độ (Velocity Index)
        # Index < 1: Làm nhanh hơn dự kiến (Tốt)
        # Index > 1: Làm chậm hơn dự kiến (Cần lưu ý)
        velocity_df['Speed_Index'] = velocity_df['Real'] / velocity_df['Estimate Dev']
        velocity_df['Năng suất (%)'] = (velocity_df['Estimate Dev'] / velocity_df['Real'] * 100).round(1)

        # Hiển thị bảng tổng hợp
        st.table(velocity_df[['PIC', 'Userstory/Todo', 'Estimate Dev', 'Real', 'Năng suất (%)']])

        # --- PHÂN TÍCH CHI TIẾT ---
        st.subheader("🔍 Đánh giá chi tiết")
        cols = st.columns(len(velocity_df))
        
        for i, row in velocity_df.iterrows():
            with cols[i]:
                st.write(f"**PIC: {row['PIC']}**")
                
                # Logic đánh giá
                if row['Speed_Index'] < 0.9:
                    st.success("Tốc độ: RẤT NHANH")
                elif row['Speed_Index'] <= 1.1:
                    st.info("Tốc độ: ĐÚNG HẠN")
                else:
                    st.warning("Tốc độ: ĐANG CHẬM")
                
                # Biểu đồ thanh nhỏ so sánh Est vs Real
                st.bar_chart(data=row[['Estimate Dev', 'Real']], height=
