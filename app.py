import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.title("📊 Sprint Dashboard Bảo Mật")

# Kết nối an toàn bằng Secrets đã cài đặt
conn = st.connection("gsheets", type=GSheetsConnection)

# Đọc dữ liệu (Thay link trình duyệt của file Sheet vào đây, link này không cần publish)
df = conn.read(spreadsheet="https://docs.google.com/spreadsheets/d/xxx/edit#gid=0")

st.dataframe(df)
try:
    # Đọc dữ liệu từ Google Sheets
    df = pd.read_csv(LINK_CSV)
    
    # Làm sạch dữ liệu: Chuyển dấu phẩy thành dấu chấm để máy hiểu là số
    for col in ['Estimate', 'Actual']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '.').astype(float)

    # Hiển thị các chỉ số tổng quát
    col1, col2, col3 = st.columns(3)
    with col1:
        total_tasks = len(df)
        done_tasks = len(df[df['Docs'] == 'Done'])
        st.metric("Tiến độ", f"{(done_tasks/total_tasks)*100:.1f}%")
    with col2:
        st.metric("Tổng Estimate", f"{df['Estimate'].sum()}h")
    with col3:
        diff = df['Actual'].sum() - df['Estimate'].sum()
        st.metric("Chênh lệch thực tế", f"{df['Actual'].sum()}h", delta=f"{diff:.1f}h", delta_color="inverse")

    # Biểu đồ
    st.subheader("Biểu đồ khối lượng công việc")
    fig = px.bar(df, x=df.columns[0], y=['Estimate', 'Actual'], barmode='group')
    st.plotly_chart(fig, use_container_width=True)

    # Bảng dữ liệu
    st.subheader("Danh sách chi tiết")
    st.dataframe(df)

except Exception as e:
    st.error(f"Lỗi: Không thể đọc dữ liệu. Hãy kiểm tra link CSV. Chi tiết: {e}")
