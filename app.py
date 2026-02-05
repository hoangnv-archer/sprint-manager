import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Sprint Workload Analyzer", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
URL = "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592"

try:
    # 1. Đọc dữ liệu
    raw_df = conn.read(spreadsheet=URL, header=None)
    header_idx = None
    for i, row in raw_df.iterrows():
        if "Userstory/Todo" in row.values:
            header_idx = i
            break
            
    if header_idx is not None:
        df = conn.read(spreadsheet=URL, skiprows=header_idx)
        df.columns = [str(c).strip() for c in df.columns]
        
        # 2. Xử lý số liệu và chuẩn hóa State
        for col in ['Estimate Dev', 'Real']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        
        # Gán nhãn "None" cho các ô State trống
        df['State'] = df['State'].fillna('None').replace('', 'None')

        # 3. Lọc Team (Chỉ lấy những dòng đã giao PIC)
        valid_pics = ['Tài', 'Dương', 'QA', 'Quân', 'Phú']
        df_team = df[df['PIC'].isin(valid_pics)].copy()

        st.title("🚀 Phân Tích Khối Lượng & Hiệu Suất Team")

        # --- TÍNH TOÁN THEO LOGIC MỚI ---
        # Tính tổng giờ Est của các task State == "None" (Chưa làm)
        pending_work = df_team[df['State'] == 'None'].groupby('PIC')['Estimate Dev'].sum().reset_index()
        pending_work.columns = ['PIC', 'Pending_Est']

        # Tính tổng giờ Est và Real của các task đã/đang làm (State != "None")
        active_work = df_team[df['State'] != 'None'].groupby('PIC').agg({
            'Estimate Dev': 'sum',
            'Real': 'sum'
        }).reset_index()
        active_work.columns = ['PIC', 'Active_Est', 'Active_Real']

        # Gộp tất cả dữ liệu theo PIC
        pic_stats = pd.DataFrame({'PIC': valid_pics})
        pic_stats = pic_stats.merge(active_work, on='PIC', how='left')
        pic_stats = pic_stats.merge(pending_work, on='PIC', how='left').fillna(0)

        # Tổng Estimate của một người = Giờ đang làm + Giờ đang chờ (None)
        pic_stats['Total_Estimate'] = pic_stats['Active_Est'] + pic_stats['Pending_Est']

        # Hiệu suất làm việc (Chỉ tính trên những task đã bắt đầu làm để công bằng)
        pic_stats['Efficiency (%)'] = (pic_stats['Active_Est'] / pic_stats['Active_Real'] * 100).fillna(0).round(1)
        pic_stats.loc[pic_stats['Active_Real'] == 0, 'Efficiency (%)'] = 0

        # --- GIAO DIỆN ---
        st.subheader("👤 Chi tiết khối lượng từng thành viên")
        cols = st.columns(len(valid_pics))
        
        for i, row in pic_stats.iterrows():
            with cols[i]:
                st.write(f"### **{row['PIC']}**")
                st.metric("Tổng Est", f"{row['Total_Estimate']}h")
                st.write(f"✅ Đã làm: **{row['Active_Real']}h**")
                st.write(f"⏳ Đang chờ (None): **{row['Pending_Est']}h**")
                
                # Thanh tiến độ công việc của người đó
                progress_val = (row['Active_Real'] / row['Total_Estimate']) if row['Total_Estimate'] > 0 else 0
                st.progress(min(progress_val, 1.0))
                st.caption(f"Tiến độ: {row['Efficiency (%)']}%")

        st.divider()

        # --- BIỂU ĐỒ PHÂN TÍCH ---
        Để cập nhật giá trị Real-time (thời gian thực tế làm việc) vào biểu đồ so sánh với phần Dự kiến đang chờ (None), chúng ta cần gộp 3 chỉ số vào cùng một biểu đồ:

Thực tế đã làm (Real): Số giờ thực tế đã nhập.

Dự kiến đang chờ (None): Số giờ Estimate của các task có State trống.

Tổng dự tính (Estimate): Để đối chiếu xem thực tế đang chiếm bao nhiêu phần của kế hoạch.

Dưới đây là đoạn code đã được cập nhật lại logic xử lý dữ liệu (Melt) và cấu hình biểu đồ để hiển thị giá trị thời gian thực:

Python

        st.subheader("📊 Biểu đồ so sánh: Real-time vs Tồn đọng (None)")
        
        # 1. Chuẩn bị dữ liệu: Lấy Real, Estimate và Pending_Est
        # Giả sử pic_stats của bạn đã có các cột: PIC, Active_Real, Total_Estimate, Pending_Est
        fig_df = pic_stats.melt(
            id_vars='PIC', 
            value_vars=['Active_Real', 'Total_Estimate', 'Pending_Est'], 
            var_name='Trạng thái', 
            value_name='Số giờ'
        )
        
        # 2. Đổi tên nhãn hiển thị cho trực quan
        name_map = {
            'Active_Real': 'Thực tế (Real-time)', 
            'Total_Estimate': 'Tổng dự tính (Kế hoạch)',
            'Pending_Est': 'Dự kiến đang chờ (None)'
        }
        fig_df['Trạng thái'] = fig_df['Trạng thái'].replace(name_map)
        
        # 3. Vẽ biểu đồ cột nhóm (Grouped Bar) để so sánh trực diện Real-time với Kế hoạch
        fig = px.bar(
            fig_df, 
            x='PIC', 
            y='Số giờ', 
            color='Trạng thái', 
            barmode='group', # Chuyển sang group để so sánh realtime với kế hoạch dễ hơn
            text_auto='.1f', # Hiển thị giá trị số giờ trên đầu cột
            title="Phân tích khối lượng công việc Real-time",
            color_discrete_map={
                'Thực tế (Real-time)': '#00C853',      # Xanh lá (Hoàn thành)
                'Tổng dự tính (Kế hoạch)': '#636EFA', # Xanh dương (Tổng)
                'Dự kiến đang chờ (None)': '#FFD600'  # Vàng (Tồn đọng)
            }
        )
        
        # Tùy chỉnh thêm để biểu đồ chuyên nghiệp hơn
        fig.update_layout(
            xaxis_title="Thành viên Team",
            yaxis_title="Số giờ (h)",
            legend_title="Chỉ số",
            hovermode="x unified"
        )

        # 4. Bảng chi tiết (Highlight các task None)
        st.subheader("📋 Danh sách Task chi tiết")
        def style_rows(row):
            return ['background-color: #f5f5f5; color: #9e9e9e' if row.State == 'None' else '' for _ in row]

        st.dataframe(df_team[['Userstory/Todo', 'State', 'Estimate Dev', 'Real', 'PIC']].style.apply(style_rows, axis=1), 
                     use_container_width=True)
              
    else:
        st.error("Không tìm thấy tiêu đề 'Userstory/Todo'.")

except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
