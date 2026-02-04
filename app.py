import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Sprint Analytics Pro", layout="wide")

# Kết nối Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
URL = "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592"

try:
    # Bước 1: Đọc và tìm hàng tiêu đề (Header)
    raw_df = conn.read(spreadsheet=URL, header=None)
    header_idx = next((i for i, row in raw_df.iterrows() if "Userstory/Todo" in row.values), None)

    if header_idx is not None:
        df = conn.read(spreadsheet=URL, skiprows=header_idx, ttl=0)
        df.columns = [str(c).strip() for c in df.columns]

        # Bước 2: Chuẩn hóa số liệu (Sửa lỗi 185,5 -> 185.5) 
        for col in ['Estimate Dev', 'Real', 'Remain Dev']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Bước 3: Lọc lấy các dòng task thực tế (bỏ qua dòng tiêu đề nhóm màu xám) 
        df_clean = df[df['PIC'].notna() & (df['PIC'] != '#N/A') & (df['PIC'].str.strip() != '')].copy()

        st.title("📊 Phân Tích Hiệu Suất Sprint")

        # --- PHẦN 1: BURNDOWN CHART GIẢ LẬP ---
        st.subheader("📉 Sprint Burndown Chart (Dựa trên khối lượng còn lại)")
        total_est = df_clean['Estimate Dev'].sum()
        total_remain = df_clean['Remain Dev'].sum()
        
        # Tạo biểu đồ đơn giản thể hiện công việc còn lại so với mục tiêu
        fig_burn = go.Figure()
        fig_burn.add_trace(go.Bar(name='Đã làm', x=['Sprint Progress'], y=[total_est - total_remain]))
        fig_burn.add_trace(go.Bar(name='Còn lại (Remain)', x=['Sprint Progress'], y=[total_remain]))
        fig_burn.update_layout(barmode='stack', height=400)
        st.plotly_chart(fig_burn, use_container_width=True)

        # --- PHẦN 2: PHÂN TÍCH CHI TIẾT TỪNG NGƯỜI (PIC) ---
        st.subheader("👤 Phân tích năng suất cá nhân")
        
        # Tính toán chỉ số cho từng PIC
        pic_stats = df_clean.groupby('PIC').agg({
            'Estimate Dev': 'sum',
            'Real': 'sum',
            'Userstory/Todo': 'count'
        }).reset_index()

        # Tính toán nhanh hay chậm: (Real / Estimate)
        # > 1: Chậm (tốn nhiều thời gian hơn dự kiến)
        # < 1: Nhanh (xong sớm hơn dự kiến)
        pic_stats['Speed_Index'] = pic_stats['Real'] / pic_stats['Estimate Dev']
        
        cols = st.columns(len(pic_stats))
        for i, row in pic_stats.iterrows():
            with cols[i]:
                status = "🚀 Nhanh" if row['Speed_Index'] < 1 else "⚠️ Chậm"
                if row['Speed_Index'] == 1: status = "✅ Đúng hạn"
                
                st.metric(label=f"PIC: {row['PIC']}", value=f"{row['Real']}h / {row['Estimate Dev']}h", delta=status)
                st.write(f"Số Task: {row['Userstory/Todo']}")
                
                # Thanh tiến độ cá nhân
                efficiency = (1 / row['Speed_Index']) * 100 if row['Speed_Index'] > 0 else 0
                st.write(f"Hiệu suất: {efficiency:.1f}%")
                st.progress(min(efficiency/100, 1.0))

        # --- PHẦN 3: BIỂU ĐỒ SO SÁNH TRỰC QUAN ---
        fig_pic = px.bar(pic_stats, x='PIC', y=['Estimate Dev', 'Real'], 
                         title="So sánh Tổng giờ Dự kiến vs Thực tế", barmode='group')
        st.plotly_chart(fig_pic, use_container_width=True)

    else:
        st.error("Không tìm thấy hàng tiêu đề 'Userstory/Todo'!")

except Exception as e:
    st.error(f"Lỗi: {e}")
