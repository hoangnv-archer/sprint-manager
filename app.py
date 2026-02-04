import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Sprint Velocity Analyzer", layout="wide")

# Kết nối Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
URL = "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592"

# 1. Đọc dữ liệu và tìm hàng tiêu đề (Userstory/Todo)
raw_df = conn.read(spreadsheet=URL, header=None)
header_idx = next((i for i, row in raw_df.iterrows() if "Userstory/Todo" in row.values), 14)

# 2. Xử lý dữ liệu chuẩn từ hàng tiêu đề
df = conn.read(spreadsheet=URL, skiprows=header_idx, ttl=0)
df.columns = [str(c).strip() for c in df.columns]

# Sửa lỗi số thập phân dấu phẩy (185,5 -> 185.5)
for col in ['Estimate Dev', 'Real']:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

# Lọc lấy các task thực tế (Dòng có tên PIC, bỏ qua dòng tiêu đề nhóm màu xám)
df_clean = df[df['PIC'].notna() & (df['PIC'].str.strip() != '') & (df['PIC'] != '#N/A')].copy()

st.title("🚀 Phân Tích Tốc Độ Team")

# 3. Gom nhóm dữ liệu theo từng người (PIC)
v_df = df_clean.groupby('PIC')[['Estimate Dev', 'Real']].sum().reset_index()

# Tính Hiệu suất: (Dự kiến / Thực tế) * 100
v_df['Hiệu suất (%)'] = (v_df['Estimate Dev'] / v_df['Real'] * 100).fillna(0).round(1)

# 4. Hiển thị bảng tổng hợp
st.subheader("📊 Bảng chỉ số năng suất")
st.dataframe(v_df, use_container_width=True)

# 5. Đánh giá Nhanh hay Chậm
st.subheader("🔍 Đánh giá chi tiết cá nhân")
cols = st.columns(len(v_df))

for idx, row in v_df.iterrows():
    with cols[idx]:
        st.write(f"**{row['PIC']}**")
        est = row['Estimate Dev']
        real = row['Real']
        
        # Logic: Thực tế > Dự kiến là Chậm, ngược lại là Nhanh
        if real > est:
            st.error(f"⚠️ Chậm {real-est:.1f}h")
        elif real < est and real > 0:
            st.success(f"⚡ Nhanh {est-real:.1f}h")
        else:
            st.info("✅ Đúng hạn")
            
        st.metric("Hiệu suất", f"{row['Hiệu suất (%)']}%")

# 6. Biểu đồ so sánh trực quan
fig = px.bar(v_df, x='PIC', y=['Estimate Dev', 'Real'], 
             barmode='group', title="So sánh Tổng giờ Dự kiến vs Thực tế")
st.plotly_chart(fig, use_container_width=True)
