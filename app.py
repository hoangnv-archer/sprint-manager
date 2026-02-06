import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import requests

st.set_page_config(page_title="Sprint Workload Analyzer", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
URL = "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592"

try:
    raw_df = conn.read(spreadsheet=URL, header=None)
    header_idx = next((i for i, row in raw_df.iterrows() if "Userstory/Todo" in row.values), None)
            
    if header_idx is not None:
        df = conn.read(spreadsheet=URL, skiprows=header_idx)
        df.columns = [str(c).strip() for c in df.columns]
        for col in ['Estimate Dev', 'Real']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        
        # Chuẩn hóa State
        df['State_Clean'] = df['State'].fillna('None').replace('', 'None').str.strip().str.lower()
        valid_pics = ['Tài', 'Dương', 'QA', 'Quân', 'Phú', 'Thịnh', 'Đô', 'Tùng', 'Anim', 'Thắng VFX']
        df_team = df[df['PIC'].isin(valid_pics)].copy()

        st.title("🚀 Sprint Workload & Performance")

        # --- LOGIC TÍNH TOÁN CHI TIẾT TASK ---
        # Tính toán theo từng người
        pic_stats = df_team.groupby('PIC').agg(
            total_tasks=('Userstory/Todo', 'count'),
            done_tasks=('State_Clean', lambda x: (x == 'done').sum()),
            inprogress_tasks=('State_Clean', lambda x: (x == 'in progress').sum()),
            none_tasks=('State_Clean', lambda x: (x == 'none').sum()),
            active_real=('Real', 'sum'),
            total_est=('Estimate Dev', 'sum')
        ).reset_index()
        
        # Task chưa hoàn thành = Tổng - Done
        pic_stats['pending_total'] = pic_stats['total_tasks'] - pic_stats['done_tasks']
        pic_stats['Progress_Task'] = (pic_stats['done_tasks'] / pic_stats['total_tasks'] * 100).fillna(0).round(1)

        # --- GIAO DIỆN METRICS ---
        st.subheader("👤 Chi tiết trạng thái Task theo PIC")
        cols = st.columns(5)
        for i, row in pic_stats.iterrows():
            with cols[i % 5]:
                st.markdown(f"### **{row['PIC']}**")
                st.metric("Tiến độ", f"{row['Progress_Task']}%")
                st.write(f"✅ Hoàn thành: **{int(row['done_tasks'])}**")
                st.write(f"🚧 In Progress: **{int(row['inprogress_tasks'])}**")
                st.write(f"⏳ Chưa làm (None): **{int(row['none_tasks'])}**")
                st.write(f"❌ Chưa xong: **{int(row['pending_total'])}**")
                st.progress(min(row['Progress_Task']/100, 1.0))
                st.divider()

        # --- BIỂU ĐỒ ---
        st.subheader("📊 Biểu đồ so sánh thời gian Real-time")
        fig_df = pic_stats[['PIC', 'active_real', 'total_est']].copy()
        fig_df.columns = ['PIC', 'Thực tế (Real)', 'Tổng dự tính (Est)']
        fig = px.bar(fig_df.melt(id_vars='PIC'), x='PIC', y='value', color='variable', barmode='group', text_auto='.1f')
        st.plotly_chart(fig, use_container_width=True)

        # --- DISCORD WEBHOOK ---
        st.sidebar.subheader("📢 Discord Detailed Report")
        webhook_url = st.sidebar.text_input("Webhook URL:", type="password")
        if st.sidebar.button("📤 Gửi báo cáo chi tiết"):
            if webhook_url:
                msg = "📊 **SPRINT TASK STATUS REPORT** 📊\n"
                msg += "━━━━━━━━━━━━━━━━━━━━━\n"
                for _, r in pic_stats.iterrows():
                    msg += f"👤 **{r['PIC']}** | `{r['Progress_Task']}%` Done\n"
                    msg += f"• Hoàn thành: `{int(r['done_tasks'])}` task\n"
                    msg += f"• Đang làm: `{int(r['inprogress_tasks'])}` | Chưa làm: `{int(r['none_tasks'])}` \n"
                    msg += f"• Tổng chưa xong: `{int(r['pending_total'])}` task\n"
                    msg += f"• Giờ thực tế: `{r['active_real']:.1f}h` / `{r['total_est']:.1f}h` \n"
                    msg += "─────────────────────\n"
                
                requests.post(webhook_url, json={"content": msg})
                st.sidebar.success("Đã gửi báo cáo chi tiết!")

        st.subheader("📋 Bảng dữ liệu thô")
        st.dataframe(df_team[['Userstory/Todo', 'State', 'PIC', 'Estimate Dev', 'Real']], use_container_width=True)
              
    else: st.error("Không tìm thấy hàng tiêu đề phù hợp.")
except Exception as e: st.error(f"Lỗi: {e}")
