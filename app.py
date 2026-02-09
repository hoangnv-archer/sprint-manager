import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, time, timedelta

# --- 1. HÀM TÍNH GIỜ LÀM VIỆC (8:30 - 18:00) ---
def calculate_working_hours(start_dt, end_dt):
    if pd.isna(start_dt) or start_dt > end_dt:
        return 0
    total_seconds = 0
    curr = start_dt
    while curr.date() <= end_dt.date():
        if curr.weekday() < 5: # Thứ 2 - Thứ 6
            morn_s = datetime.combine(curr.date(), time(8, 30))
            morn_e = datetime.combine(curr.date(), time(12, 0))
            aft_s = datetime.combine(curr.date(), time(13, 30))
            aft_e = datetime.combine(curr.date(), time(18, 0))
            
            # Tính thời gian thực làm trong ca sáng và ca chiều
            s_m, e_m = max(curr, morn_s), min(end_dt, morn_e)
            if s_m < e_m: total_seconds += (e_m - s_m).total_seconds()
            
            s_a, e_a = max(curr, aft_s), min(end_dt, aft_e)
            if s_a < e_a: total_seconds += (e_a - s_a).total_seconds()
            
        curr = (curr + timedelta(days=1)).replace(hour=8, minute=30, second=0)
    return total_seconds / 3600

st.set_page_config(page_title="Sprint Workload Analyzer", layout="wide")

# --- 2. KẾT NỐI VÀ ĐỌC DỮ LIỆU ---
conn = st.connection("gsheets", type=GSheetsConnection)
URL = "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592"

try:
    raw_df = conn.read(spreadsheet=URL, header=None)
    header_idx = next((i for i, row in raw_df.iterrows() if "Userstory/Todo" in row.values), None)
            
    if header_idx is not None:
        df = conn.read(spreadsheet=URL, skiprows=header_idx)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Xử lý định dạng số
        for col in ['Estimate Dev', 'Real']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        
        # Xử lý cột Start_time cho tính năng mới
        if 'Start_time' in df.columns:
            df['Start_time'] = pd.to_datetime(df['Start_time'], errors='coerce')
        
        # Chuẩn hóa trạng thái (Tính năng cũ)
        df['State_Clean'] = df['State'].fillna('None').replace('', 'None').str.strip().str.lower()
        valid_pics = ['Tài', 'Dương', 'QA', 'Quân', 'Phú', 'Thịnh', 'Đô', 'Tùng', 'Anim', 'Thắng VFX']
        df_team = df[df['PIC'].isin(valid_pics)].copy()

        # --- 3. LOGIC CẢNH BÁO OVER ESTIMATE (MỚI) ---
        now = datetime.now()
        over_est_list = []
        for _, row in df_team.iterrows():
            if row['State_Clean'] == 'in progress' and not pd.isna(row['Start_time']):
                actual = calculate_working_hours(row['Start_time'], now)
                est = float(row['Estimate Dev'])
                if est > 0 and actual > est:
                    over_est_list.append({
                        "PIC": row['PIC'], 
                        "Task": row['Userstory/Todo'], 
                        "Actual": round(actual, 1), 
                        "Est": est
                    })

        st.title("🚀 Sprint Workload & Performance")

        # Hiển thị cảnh báo ngay đầu trang nếu có task quá giờ
        if over_est_list:
            st.warning(f"🚨 Có {len(over_est_list)} task đang vượt quá thời gian Estimate!")
            with st.expander("Chi tiết task vượt Estimate"):
                st.table(pd.DataFrame(over_est_list))

        # --- 4. TÍNH TOÁN STATS (Tính năng cũ) ---
        pic_stats = df_team.groupby('PIC').agg(
            total_tasks=('Userstory/Todo', 'count'),
            done_tasks=('State_Clean', lambda x: x.isin(['done', 'cancel']).sum()),
            inprogress_tasks=('State_Clean', lambda x: (x == 'in progress').sum()),
            none_tasks=('State_Clean', lambda x: (x == 'none').sum()),
            active_real=('Real', 'sum'),
            total_est=('Estimate Dev', 'sum')
        ).reset_index()
        
        pic_stats['Progress_Task'] = (pic_stats['done_tasks'] / pic_stats['total_tasks'] * 100).fillna(0).round(1)

        # --- 5. HIỂN THỊ METRICS PIC (Tính năng cũ) ---
        st.subheader("👤 Trạng thái Task theo PIC")
        cols = st.columns(5)
        for i, row in pic_stats.iterrows():
            with cols[i % 5]:
                st.markdown(f"### **{row['PIC']}**")
                st.metric("Tiến độ", f"{row['Progress_Task']}%")
                st.write(f"✅ Hoàn thành: **{int(row['done_tasks'])}**")
                st.write(f"🚧 In Progress: **{int(row['inprogress_tasks'])}**")
                st.write(f"⏳ Chưa làm: **{int(row['none_tasks'])}**")
                st.progress(min(row['Progress_Task']/100, 1.0))
                st.divider()

        # --- 6. BIỂU ĐỒ (Tính năng cũ) ---
        st.subheader("📊 Biểu đồ thời gian làm việc")
        fig_df = pic_stats[['PIC', 'active_real', 'total_est']].copy()
        fig_df.columns = ['PIC', 'Thực tế (Real)', 'Dự tính (Est)']
        fig = px.bar(fig_df.melt(id_vars='PIC'), x='PIC', y='value', color='variable', barmode='group', text_auto='.1f')
        st.plotly_chart(fig, use_container_width=True)

        # --- 7. GỬI DISCORD (Tính năng cũ + Cảnh báo mới) ---
        st.sidebar.subheader("📢 Báo cáo Discord")
        webhook_url = st.sidebar.text_input("Webhook URL:", type="password")
        if st.sidebar.button("📤 Gửi báo cáo chi tiết"):
            if webhook_url:
                msg = "📊 **SPRINT STATUS REPORT** 📊\n━━━━━━━━━━━━━━━━━━━━━\n"
                for _, r in pic_stats.iterrows():
                    msg += f"👤 **{r['PIC']}** | `{r['Progress_Task']}%` Done\n"
                    msg += f"• Xong: `{int(r['done_tasks'])}` | Đang làm: `{int(r['inprogress_tasks'])}` \n"
                
                # Thêm phần cảnh báo vào tin nhắn Discord (Sửa lỗi thụt lề tại đây)
                if over_est_list:
                    msg += "\n🚨 **CẢNH BÁO VƯỢT ESTIMATE**\n"
                    for item in over_est_list:
                        msg += f"• {item['PIC']}: {item['Task']} (`{item['Actual']}h`/{item['Est']}h)\n"
                
                response = requests.post(webhook_url, json={"content": msg})
                if response.status_code in [200, 204]:
                    st.sidebar.success("Đã gửi báo cáo!")
                else:
                    st.sidebar.error(f"Lỗi: {response.status_code}")

        # --- 8. CHI TIẾT DANH SÁCH (Tính năng cũ) ---
        st.subheader("📋 Chi tiết danh sách Task")
        st.dataframe(df_team[['Userstory/Todo', 'State', 'PIC', 'Estimate Dev', 'Real', 'Start_time']], use_container_width=True)
            
    else:
        st.error("Không tìm thấy hàng tiêu đề 'Userstory/Todo'.")

except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
