import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Sprint Analyzer Pro", layout="wide")

# 1. Kết nối Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
URL = "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592"

try:
    # Đọc dữ liệu thô để tìm hàng tiêu đề
    raw_df = conn.read(spreadsheet=URL, header=None)
    header_idx = next((i for i, row in raw_df.iterrows() if "Userstory/Todo" in row.values), None)

    if header_idx is not None:
        # Đọc dữ liệu từ hàng tiêu đề
        df = conn.read(spreadsheet=URL, skiprows=header_idx)
        df.columns = [str(c).strip() for c in df.columns]

        # Xử lý số liệu
        for col in ['Estimate Dev', 'Real']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

        # Chuẩn hóa State: Ô trống được coi là 'None'
        df['State'] = df['State'].fillna('None').replace('', 'None')

        # Lọc danh sách Team PIC
        valid_pics = ['Tài', 'Dương', 'QA', 'Quân', 'Phú']
        df_team = df[df['PIC'].isin(valid_pics)].copy()

        st.title("🚀 Sprint Backlog Performance Analysis")

        # --- LOGIC TIẾN ĐỘ THEO SỐ LƯỢNG TASK ---
        total_tasks = len(df_team)
        done_tasks = len(df_team[df_team['State'].str.lower() == 'done'])
        
        # --- TÍNH TOÁN KHỐI LƯỢNG THEO GIỜ ---
        # 1. Giờ đang chờ (State là None)
        pending_work = df_team[df_team['State'] == 'None'].groupby('PIC')['Estimate Dev'].sum().reset_index()
        pending_work.columns = ['PIC', 'Pending_Est']

        # 2. Giờ thực tế đã làm (Real-time) và Giờ dự tính tổng
        summary_work = df_team.groupby('PIC').agg({
            'Estimate Dev': 'sum',
            'Real': 'sum'
        }).reset_index()
        summary_work.columns = ['PIC', 'Total_Est', 'Active_Real']

        # Gộp dữ liệu vào bảng thống kê pic_stats
        pic_stats = pd.DataFrame({'PIC': valid_pics})
        pic_stats = pic_stats.merge(summary_work, on='PIC', how='left')
        pic_stats = pic_stats.merge(pending_work, on='PIC', how='left').fillna(0)

        # 3. Hiển thị Metrics tổng quát
        c1, c2, c3 = st.columns(3)
        c1.metric("Tổng Task", f"{total_tasks} Task")
        c2.metric("Task Hoàn Thành", f"{done_tasks} Task")
        
        if total_tasks > 0:
            progress = (done_tasks / total_tasks) * 100
            c3.metric("Tiến Độ (Số lượng Task)", f"{progress:.1f}%")
            st.progress(progress / 100)

        st.divider()

        # --- BIỂU ĐỒ SO SÁNH: REAL-TIME, KẾ HOẠCH, PENDING ---
        st.subheader("📊 Biểu đồ so sánh: Thực tế vs Kế hoạch vs Tồn đọng")
        
        # Chuẩn bị dữ liệu cho biểu đồ (Melt)
        chart_data = pic_stats[['PIC', 'Active_Real', 'Total_Est', 'Pending_Est']].copy()
        chart_data.columns = ['PIC', 'Thực tế (Real)', 'Tổng dự tính (Kế hoạch)', 'Đang chờ (None)']
        
        fig_df = chart_data.melt(id_vars='PIC', var_name='Loại chỉ số', value_name='Số giờ')

        if not fig_df.empty:
            fig = px.bar(
                fig_df, x='PIC', y='Số giờ', color='Loại chỉ số',
                barmode='group', text_auto='.1f',
                color_discrete_map={
                    'Thực tế (Real)': '#00C853',      # Xanh lá
                    'Tổng dự tính (Kế hoạch)': '#636EFA', # Xanh dương
                    'Đang chờ (None)': '#FFD600'      # Vàng
                }
            )
            fig.update_layout(height=500, margin=dict(t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)

        # --- BẢNG CHI TIẾT ---
        st.subheader("📋 Chi tiết danh sách Task")
        st.dataframe(df_team[['Userstory/Todo', 'State', 'Estimate Dev', 'Real', 'PIC']], use_container_width=True)

    else:
        st.error("Không tìm thấy hàng tiêu đề 'Userstory/Todo' trong Sheet.")

except Exception as e:
    st.error(f"Lỗi hệ thống: {e}") 
