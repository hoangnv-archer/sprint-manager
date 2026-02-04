import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Sprint Velocity Analyzer", layout="wide")

# Kết nối dữ liệu
conn = st.connection("gsheets", type=GSheetsConnection)
URL = "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592"

try:
    # 1. Tìm hàng tiêu đề (Userstory/Todo)
    raw_df = conn.read(spreadsheet=URL, header=None)
    header_idx = None
    for i, row in raw_df.iterrows():
        if "Userstory/Todo" in row.values:
            header_idx = i
            break

    if header_idx is not None:
        # 2. Đọc dữ liệu từ hàng tiêu đề trở đi
        df = conn.read(spreadsheet=URL, skiprows=header_idx, ttl=0)
        df.columns = [str(c).strip() for c in df.columns]

        # 3. Xử lý số liệu (Sửa lỗi dấu phẩy 185,5 -> 185.5)
        for col in ['Estimate Dev', 'Real']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # 4. Lọc lấy các task có người phụ trách (PIC)
        df_clean = df[df['PIC'].notna() & (df['PIC'] != '#N/A') & (df['PIC'].str.strip() != '')].copy()

        st.title("🚀 Phân Tích Tốc Độ & Hiệu Suất Team")

        # 5. Tổng hợp dữ liệu theo PIC (Đã sửa lỗi cú pháp ở đây)
        # Tạo bảng thống kê: Tổng giờ dự kiến, Tổng giờ thực tế, Số lượng task
        velocity_df = df_clean.groupby('PIC').agg(
            total_est=('Estimate Dev', 'sum'),
            total_real=('Real', 'sum'),
            task_count=('Userstory/Todo', 'count')
        ).reset_index()

        # 6. Tính toán chỉ số hiệu suất
        # Hiệu suất % = (Dự kiến / Thực tế) * 100
        velocity_df['Efficiency'] = (velocity_df['total_est'] / velocity_df['total_real'] * 100).round(1)
        # Chỉ số tốc độ (Speed Ratio): Thực tế / Dự kiến
        velocity_df['Speed_Ratio'] = velocity_df['total_real'] / velocity_df['total_est']

        # --- HIỂN THỊ TỔNG HỢP ---
        st.subheader("📊 Bảng tổng hợp năng suất")
        st.dataframe(velocity_df[['PIC', 'task_count', 'total_est', 'total_real', 'Efficiency']], use_container_width=True)

        # --- PHÂN TÍCH TỐC ĐỘ CHI TIẾT ---
        st.subheader("🔍 Đánh giá tốc độ làm việc")
        cols = st.columns(len(velocity_df))
        
        for i, row in velocity_df.iterrows():
            with cols[i]:
                st.markdown(f"### **{row['PIC']}**")
                
                # Logic đánh giá tốc độ
                if row['Speed_Ratio'] < 0.9:
                    st.success("⚡ Tốc độ: RẤT NHANH")
                elif row['Speed_Ratio'] <= 1.1:
                    st.info("✅ Tốc độ: ĐÚNG HẠN")
                else:
                    st.warning("⚠️ Tốc độ: ĐANG CHẬM")
                
                st.metric("Hiệu suất", f"{row['Efficiency']}%")
                
                # Biểu đồ so sánh nhỏ
                chart_data = pd.DataFrame({
                    'Nhãn': ['Dự kiến', 'Thực tế'],
                    'Giờ': [row['total_est'], row['total_real']]
                })
                fig_mini = px.bar(chart_data, x='Nhãn', y='Giờ', color='Nhãn',
                                 color_discrete_map={'Dự kiến':'#636EFA', 'Thực tế':'#EF
