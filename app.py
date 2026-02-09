import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, time, timedelta

# --- 1. HÀM TÍNH GIỜ LÀM VIỆC CHUẨN ---
def calculate_working_hours(start_dt, end_dt):
    if pd.isna(start_dt) or start_dt > end_dt:
        return 0
    total_seconds = 0
    curr = start_dt
    while curr.date() <= end_dt.date():
        if curr.weekday() < 5: 
            morn_s, morn_e = datetime.combine(curr.date(), time(8, 30)), datetime.combine(curr.date(), time(12, 0))
            aft_s, aft_e = datetime.combine(curr.date(), time(13, 30)), datetime.combine(curr.date(), time(18, 0))
            s_m, e_m = max(curr, morn_s), min(end_dt, morn_e)
            if s_m < e_m: total_seconds += (e_m - s_m).total_seconds()
            s_a, e_a = max(curr, aft_s), min(end_dt, aft_e)
            if s_a < e_a: total_seconds += (e_a - s_a).total_seconds()
        curr = (curr + timedelta(days=1)).replace(hour=8, minute=30, second=0)
    return total_seconds / 3600

st.set_page_config(page_title="Sprint Workload Analyzer", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)
URL = "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592"

try:
    df_raw = conn.read(spreadsheet=URL, header=None, ttl=0)
    header_idx = next((i for i, row in df_raw.iterrows() if "Userstory/Todo" in row.values), None)
            
    if header_idx is not None:
        df = conn.read(spreadsheet=URL, skiprows=header_idx, ttl=0)
        df.columns = [str(c).strip() for c in df.columns]
        
        # --- DÒ TÌM CỘT START TIME ---
        found_start_col = next((c for c in df.columns if "Start" in c), None)
        if found_start_col:
            df['Start_DT'] = pd.to_datetime(df[found_start_col], errors='coerce')
            df['Start_Display'] = df[found_start_col].astype(str).replace(['nan', 'NaT'], '')
        else:
            df['Start_DT'] = pd.NaT
            df['Start_Display'] = ""

        # Chuẩn hóa số
        for col in ['Estimate Dev', 'Real']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        
        df['State_Clean'] = df['State'].fillna('None').str.strip().str.lower()
        valid_pics = ['Tài', 'Dương', 'QA', 'Quân', 'Phú', 'Thịnh', 'Đô', 'Tùng', 'Anim', 'Thắng VFX']
        df_team = df[df['PIC'].isin(valid_pics)].copy()

        # --- LOGIC CẢNH BÁO (DÙNG CHUNG CHO APP & DISCORD) ---
        now = datetime.now()
        over_est_list = []
        for _, row in df_team.iterrows():
            if row['State_Clean'] == 'in progress' and not pd.isna(row['Start_DT']):
                actual_h = calculate_working_hours(row['Start_DT'], now)
                est_h = float(row['Estimate Dev'])
                if est_h > 0 and actual_h > est_h:
                    over_est_list.append({
                        "PIC": row['PIC'], 
                        "Task": row['Userstory/Todo'], 
                        "Actual": round(actual_h, 1), 
                        "Est": est_h
                    })

        st.title("🚀 Sprint Workload & Performance")

        # Hiển thị cảnh báo trên App
        if over_est_list:
            st.warning(f"🚨 Có {len(over_est_list)} task đang vượt quá thời gian Estimate!")
            st.table(pd.DataFrame(over_est_list))

        # --- THỐNG KÊ PIC ---
        pic_stats = df_team.groupby('PIC').agg(
            total_tasks=('Userstory/Todo', 'count'),
            done_tasks=('State_Clean', lambda x: x.isin(['done', 'cancel']).sum()),
            inprogress_tasks=('State_Clean', lambda x: (x == 'in progress').sum())
        ).reset_index()
        pic_stats['pending_total'] = pic_stats['total_tasks'] - pic_stats['done_tasks']
        pic_stats['Progress'] = (pic_stats['done_tasks'] / pic_stats['total_tasks'] * 100).fillna(0).round(1)

        # Hiển thị Metrics
        cols = st.columns(5)
        for i, row in pic_stats.iterrows():
            with cols[i % 5]:
                st.markdown(f"### **{row['PIC']}**")
                st.metric("Tiến độ", f"{row['Progress']}%")
                st.write(f"✅ Xong: {int(row['done_tasks'])} | 🚧 Làm: {int(row['inprogress_tasks'])}")
                st.write(f"🚩 Còn lại: **{int(row['pending_total'])}**")
                st.progress(min(row['Progress']/100, 1.0))
                st.divider()

        # --- PHẦN GỬI DISCORD (ĐÃ FIX) ---
        st.sidebar.subheader("📢 Báo cáo Discord")
        webhook_url = st.sidebar.text_input("Webhook URL:", type="password")
        if st.sidebar.button("📤 Gửi báo cáo chi tiết"):
            if webhook_url:
                # Tạo nội dung tin nhắn
                msg = "📊 **SPRINT STATUS REPORT**\n━━━━━━━━━━━━━━━━━━━━━\n"
                for _, r in pic_stats.iterrows():
                    msg += f"👤 **{r['PIC']}** | `{r['Progress']}%` Done\n"
                
                # THÊM CẢNH BÁO VÀO TIN NHẮN DISCORD
                if over_est_list:
                    msg += "\n🚨 **CẢNH BÁO VƯỢT ESTIMATE**\n"
                    for item in over_est_list:
                        msg += f"• {item['PIC']}: {item['Task']} (`{item['Actual']}h`/{item['Est']}h)\n"
                
                requests.post(webhook_url, json={"content": msg})
                st.sidebar.success("Đã gửi báo cáo thành công!")

        # Biểu đồ và Bảng
        st.plotly_chart(px.bar(pic_stats, x='PIC', y=['total_tasks', 'done_tasks'], barmode='group'), use_container_width=True)
        st.subheader("📋 Chi tiết danh sách Task")
        st.dataframe(df_team[['Userstory/Todo', 'State', 'PIC', 'Estimate Dev', 'Real', 'Start_display' if 'Start_display' in df_team.columns else found_start_col]], use_container_width=True)

    else:
        st.error("Không tìm thấy hàng tiêu đề 'Userstory/Todo'.")
except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
