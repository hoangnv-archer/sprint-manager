import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Sprint Analyzer Pro", layout="wide")

# Kết nối an toàn qua Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

# Dán link trình duyệt file Sheet của bạn vào đây
URL = "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592"

try:
    # 1. Đọc dữ liệu thô (không lấy header) để dò tìm hàng tiêu đề thực sự
    raw_df = conn.read(spreadsheet=URL, header=None)
    
    # Tìm hàng chứa chữ "Userstory/Todo" để xác định header
    header_idx = None
    for i, row in raw_df.iterrows():
        if "Userstory/Todo" in row.values:
            header_idx = i
            break
            
    if header_idx is not None:
        # Đọc lại dữ liệu bắt đầu từ hàng tiêu đề đã tìm thấy
        df = conn.read(spreadsheet=URL, skiprows=header_idx)
        
        # Làm sạch tên cột (xóa khoảng trắng thừa)
        df.columns = [str(c).strip() for c in df.columns]
        
        # 2. Xử lý số liệu: Chuyển '185,5' thành 185.5
        for col in ['Estimate Dev', 'Real', 'Remain Dev']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # 3. Lọc dữ liệu: Chỉ lấy dòng có PIC và bỏ qua dòng 'Summary' (hàng ngay dưới header)
        # Chúng ta lọc bỏ dòng có chứa tổng số 185.5 bằng cách kiểm tra PIC hợp lệ
        valid_pics = ['Tài', 'Dương', 'QA', 'Quân', 'Phú'] # Bạn có thể thêm tên team vào đây
        df_clean = df[df['PIC'].isin(valid_pics)].copy()

        # 4. Giao diện Dashboard
        st.title("🚀 Sprint Backlog Analysis")
        
        # Tính toán các chỉ số
        total_est = df_clean['Estimate Dev'].sum()
        total_real = df_clean['Real'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Tổng Giờ Dự Tính (Est)", f"{total_est:.1f}h")
        c2.metric("Thực Tế Đã Làm (Real)", f"{total_real:.1f}h")
        
        # Tính % hoàn thành
        done_tasks = len(df_clean[df_clean['State'] == 'Done'])
        total_tasks = len(df_clean)
        if total_tasks > 0:
            progress = (done_tasks / total_tasks) * 100
            c3.metric("Tiến độ Sprint", f"{progress:.1f}%")

        # 5. Biểu đồ theo PIC
        st.subheader("Phân bổ khối lượng theo thành viên")
        pic_chart = df_clean.groupby('PIC')[['Estimate Dev', 'Real']].sum().reset_index()
        fig = px.bar(pic_chart, x='PIC', y=['Estimate Dev', 'Real'], barmode='group')
        st.plotly_chart(fig, use_container_width=True)

        # 6. Bảng danh sách task (đã lọc sạch)
        st.subheader("Danh sách Task chi tiết")
        st.dataframe(df_clean[['Userstory/Todo', 'State', 'Estimate Dev', 'Real', 'PIC']])
              
        # --- TÍNH NĂNG MỚI: ĐÁNH GIÁ HIỆU SUẤT CÁ NHÂN ---
        st.subheader("👤 Phân tích Hiệu suất từng thành viên")
        
        # Gom nhóm dữ liệu theo PIC
        pic_stats = df_clean.groupby('PIC').agg({
            'Estimate Dev': 'sum',
            'Real': 'sum',
            'Userstory/Todo': 'count'
        }).reset_index()

        # Tính chỉ số hiệu suất: Hiệu suất (%) = (Dự tính / Thực tế) * 100
        # Nếu > 100% là làm nhanh (xong sớm), < 100% là làm chậm (lố giờ)
        pic_stats['Efficiency'] = (pic_stats['Estimate Dev'] / pic_stats['Real'] * 100).fillna(0).round(1)
        # Thay thế giá trị vô hạn (nếu Real = 0)
        pic_stats.loc[pic_stats['Real'] == 0, 'Efficiency'] = 0

        # Hiển thị Metric cho từng người
        cols = st.columns(len(pic_stats))
        for i, row in pic_stats.iterrows():
            with cols[i]:
                name = row['PIC']
                eff = row['Efficiency']
                
                # Logic đánh giá tốc độ
                if eff > 105:
                    status = "⚡ Nhanh"
                    color = "normal" # Màu xanh mặc định của delta
                elif eff < 95 and eff > 0:
                    status = "⚠️ Chậm"
                    color = "inverse" # Màu đỏ
                else:
                    status = "✅ Đúng hạn"
                    color = "off" # Màu xám/bình thường

                st.metric(label=f"PIC: {name}", value=f"{eff}%", delta=status, delta_color=color)
                st.caption(f"Dự tính: {row['Estimate Dev']}h | Thực tế: {row['Real']}h")

        # Biểu đồ so sánh trực quan
        st.divider()
        st.subheader("📈 So sánh khối lượng Dự kiến vs Thực tế")
        fig = px.bar(pic_stats, x='PIC', y=['Estimate Dev', 'Real'], 
                     barmode='group', text_auto=True,
                     labels={'value': 'Số giờ (h)', 'variable': 'Loại'},
                     color_discrete_map={'Estimate Dev': '#636EFA', 'Real': '#EF553B'})
        st.plotly_chart(fig, use_container_width=True)

        # 6. Bảng danh sách task
        st.subheader("📋 Chi tiết danh sách Task")
        st.dataframe(df_clean[['Userstory/Todo', 'State', 'Estimate Dev', 'Real', 'PIC']], use_container_width=True)
        
    else:
        st.error("Không tìm thấy hàng tiêu đề 'Userstory/Todo'. Vui lòng kiểm tra lại cấu trúc Sheet.")

except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
