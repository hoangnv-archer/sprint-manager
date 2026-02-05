import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Sprint Analyzer Pro", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
URL = "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592"

try:
    raw_df = conn.read(spreadsheet=URL, header=None)
    header_idx = None
    for i, row in raw_df.iterrows():
        if "Userstory/Todo" in row.values:
            header_idx = i
            break
            
    if header_idx is not None:
        df = conn.read(spreadsheet=URL, skiprows=header_idx)
        df.columns = [str(c).strip() for c in df.columns]
        
        # 2. Xử lý số liệu
        for col in ['Estimate Dev', 'Real', 'Remain Dev']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # 3. Lọc dữ liệu: PIC hợp lệ
        valid_pics = ['Tài', 'Dương', 'QA', 'Quân', 'Phú'] 
        df_clean = df[df['PIC'].isin(valid_pics)].copy()

        # Đảm bảo cột State không bị khoảng trắng thừa
        df_clean['State'] = df_clean['State'].astype(str).str.strip()

        st.title("🚀 Sprint Backlog Performance Analysis")
        
        # --- TÍNH TOÁN HIỆU SUẤT VÀ TỒN ĐỘNG ---
        # Lọc riêng các task chưa làm (State == "None")
        df_pending = df_clean[df_clean['State'].str.lower() == 'none'].copy()
        
        # Gom nhóm dữ liệu theo PIC
        pic_stats = df_clean.groupby('PIC').agg({
            'Estimate Dev': 'sum',
            'Real': 'sum'
        }).reset_index()

        # Tính tổng giờ "None" (Chưa làm) cho từng PIC
        pending_stats = df_pending.groupby('PIC')['Estimate Dev'].sum().reset_index()
        pending_stats.columns = ['PIC', 'Pending Hours']

        # Gộp dữ liệu
        final_stats = pd.merge(pic_stats, pending_stats, on='PIC', how='left').fillna(0)

        # Hiệu suất: Chỉ tính trên những task đã bắt đầu làm (có Real > 0 hoặc State != None)
        # Ở đây tính tổng quát để bạn thấy tốc độ chung
        final_stats['Efficiency'] = (final_stats['Estimate Dev'] / final_stats['Real'] * 100).fillna(0).round(1)
        final_stats.loc[final_stats['Real'] == 0, 'Efficiency'] = 0

        # --- GIAO DIỆN ---
        st.subheader("👤 Đánh giá năng suất và Khối lượng chưa làm")
        
        cols = st.columns(len(final_stats))
        for i, row in final_stats.iterrows():
            with cols[i]:
                name = row['PIC']
                pending = row['Pending Hours']
                eff = row['Efficiency']
                
                # Hiển thị hiệu suất (Tốc độ làm việc)
                st.metric(label=f"PIC: {name}", value=f"{eff}%", 
                          delta=f"{pending}h chưa làm", delta_color="inverse")
                
                st.write(f"⌛ Dự kiến còn: **{pending}h**")
                st.progress(min(eff/200, 1.0) if eff > 0 else 0)

        st.divider()

        # --- BIỂU ĐỒ PHÂN TÍCH ---
        st.subheader("📊 So sánh Dự kiến, Thực tế và Tồn đọng (None)")
        
        # Chuẩn bị dữ liệu cho biểu đồ
        fig_data = final_stats.melt(id_vars='PIC', value_vars=['Estimate Dev', 'Real', 'Pending Hours'],
                                    var_name='Loại', value_name='Số giờ')
        
        fig = px.bar(fig_data, x='PIC', y='Số giờ', color='Loại', 
                     barmode='group', text_auto=True,
                     color_discrete_map={
                         'Estimate Dev': '#636EFA', 
                         'Real': '#EF553B', 
                         'Pending Hours': '#FECB52' # Màu vàng cho các task chưa làm
                     })
        st.plotly_chart(fig, use_container_width=True)

        # 6. Bảng danh sách task có highlight task "None"
        st.subheader("📋 Chi tiết danh sách Task")
        
        # Thêm màu để phân biệt task None trong bảng
        def highlight_none(row):
            return ['background-color: #fff9c4' if row.State.lower() == 'none' else '' for _ in row]

        st.dataframe(df_clean[['Userstory/Todo', 'State', 'Estimate Dev', 'Real', 'PIC']].style.apply(highlight_none, axis=1), 
                     use_container_width=True)
              
    else:
        st.error("Không tìm thấy hàng tiêu đề 'Userstory/Todo'.")

except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
