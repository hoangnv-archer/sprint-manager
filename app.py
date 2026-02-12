import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timezone, timedelta

# --- 1. CỐ ĐỊNH MÚI GIỜ VIỆT NAM ---
VN_TZ = timezone(timedelta(hours=7))

def get_actual_hours(start_val):
    if pd.isna(start_val) or str(start_val).strip().lower() in ['none', '', 'nat', 'nan']:
        return 0
    try:
        # Ép kiểu datetime
        start_dt = pd.to_datetime(start_val, errors='coerce')
        if pd.isna(start_dt):
            return 0
            
        # Xử lý nếu PIC chỉ nhập giờ (ví dụ 10:30) mà thiếu ngày
        now_vn = datetime.now(VN_TZ)
        if start_dt.year < 2000: 
            start_dt = start_dt.replace(year=now_vn.year, month=now_vn.month, day=now_vn.day)

        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=VN_TZ)
        
        diff = now_vn - start_dt
        return max(0, diff.total_seconds() / 3600) 
    except:
        return 0

# --- 2. CẤU HÌNH ---
PROJECTS = {
    "Sprint Team 2": {
        "url": "https://docs.google.com/spreadsheets/d/1hentY_r7GNVwJWM3wLT7LsA3PrXQidWnYahkfSwR9Kw/edit?pli=1&gid=982443592#gid=982443592",
        "pics": ['Chuân', 'Việt', 'Thắng', 'QA', 'Mai', 'Hải Anh', 'Thuật', 'Hiếu'],
        "platform": "Telegram",
        "bot_token": "8535993887:AAFDNSLk9KRny99kQrAoQRbgpKJx_uHbkpw",
        "chat_id": "-1002102856307",
        "topic_id": 18251
    },
    "Sprint Dashboard Final": {
        "url": "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592",
        "pics": ['Tài', 'Dương', 'QA', 'Quân', 'Phú', 'Thịnh', 'Đô', 'Tùng', 'Anim', 'Thắng VFX'],
        "platform": "Discord"
    }
}

st.set_page_config(page_title="Sprint Multi-Project Dashboard", layout="wide")

# --- 3. SIDEBAR CHỌN DỰ ÁN ---
if 'selected_project' not in st.session_state:
    st.session_state.selected_project = list(PROJECTS.keys())[0]

st.sidebar.title("📁 Danh sách dự án")
for project_name in PROJECTS.keys():
    btn_type = "primary" if st.session_state.selected_project == project_name else "secondary"
    if st.sidebar.button(project_name, use_container_width=True, type=btn_type):
        st.session_state.selected_project = project_name
        st.rerun()

config = PROJECTS[st.session_state.selected_project]

# --- 4. XỬ LÝ DỮ LIỆU ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read(spreadsheet=config['url'], header=None, ttl=0)
    header_idx = next((i for i, row in df_raw.iterrows() if "Userstory/Todo" in row.values), None)
            
    if header_idx is not None:
        df = conn.read(spreadsheet=config['url'], skiprows=header_idx, ttl=0)
        df.columns = [str(c).strip() for c in df.columns]

        # Chuẩn hóa số (Đơn vị Giờ)
        for col in ['Estimate Dev', 'Real']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.').str.replace('None', '0').str.strip()
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Tìm cột thời gian
        t_col = next((c for c in df.columns if "start" in c.lower()), None)
        df['State_Clean'] = df['State'].fillna('None').str.strip().str.lower()
        df_team = df[df['PIC'].isin(config['pics'])].copy()

        # --- LOGIC CẢNH BÁO LỐ GIỜ ---
        over_est_list = []
        if t_col:
            for _, row in df_team.iterrows():
                if 'progress' in str(row['State_Clean']):
                    actual_h = get_actual_hours(row[t_col])
                    est_h = float(row['Estimate Dev'])
                    if est_h > 0 and actual_h > est_h:
                        over_est_list.append({
                            "PIC": row['PIC'], 
                            "Task": row['Userstory/Todo'], 
                            "Thực tế": f"{round(actual_h, 2)}h ({round(actual_h*60)}p)", 
                            "Dự kiến": f"{round(est_h, 2)}h ({round(est_h*60)}p)",
                            "Vượt": f"{round((actual_h - est_h) * 60)} phút"
                        })

        st.title(f"🚀 {st.session_state.selected_project}")

        # Hiển thị thông báo lố giờ (Nếu có)
        if over_est_list:
            st.error(f"🚨 PHÁT HIỆN {len(over_est_list)} TASK LÀM QUÁ GIỜ DỰ KIẾN!")
            st.table(pd.DataFrame(over_est_list))

        # --- THỐNG KÊ CHI TIẾT ---
        pic_stats = df_team.groupby('PIC').agg(
            total=('Userstory/Todo', 'count'),
            done=('State_Clean', lambda x: x.isin(['done', 'cancel', 'dev done']).sum()),
            doing=('State_Clean', lambda x: x.str.contains('progress').sum()),
            est_total=('Estimate Dev', 'sum'),
            real_total=('Real', 'sum')
        ).reset_index()
        
        pic_stats['pending'] = pic_stats['total'] - pic_stats['done']
        pic_stats['percent'] = (pic_stats['done'] / pic_stats['total'] * 100).fillna(0).round(1)

        st.subheader("👤 Trạng thái chi tiết từng PIC")
        cols = st.columns(5)
        for i, row in pic_stats.iterrows():
            with cols[i % 5]:
                st.markdown(f"#### **{row['PIC']}**")
                st.metric("Tiến độ", f"{row['percent']}%")
                st.write(f"✅ Xong: {int(row['done'])} | 🚧 Đang: {int(row['doing'])}")
                st.write(f"⏳ **Tồn: {int(row['pending'])} task**")
                st.progress(min(row['percent']/100, 1.0))
                st.divider()

        # Biểu đồ so sánh giờ
        st.plotly_chart(px.bar(pic_stats, x='PIC', y=['est_total', 'real_total'], 
                               barmode='group', title="So sánh Tổng giờ Dự kiến vs Thực tế (Hours)"), 
                               use_container_width=True)

        # --- GỬI BÁO CÁO NHANH ---
        st.sidebar.divider()
        st.sidebar.subheader("📢 Gửi báo cáo")
        if st.sidebar.button(f"📤 Bắn báo cáo {config['platform']}"):
            msg = f"📊 **REPORT: {st.session_state.selected_project}**\n"
            for _, r in pic_stats.iterrows():
                msg += f"👤 {r['PIC']}: {r['percent']}% (Xong: {int(r['done'])}/Tồn: {int(r['pending'])})\n"
            
            if over_est_list:
                msg += "\n🚨 **CẢNH BÁO LỐ GIỜ:**\n"
                for item in over_est_list:
                    msg += f"🔥 {item['PIC']}: {item['Task']} (Lố {item['Vượt']})\n"

            if config['platform'] == "Discord":
                # Webhook URL dự phòng nếu không nhập từ Sidebar
                webhook_url = "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL" 
                requests.post(webhook_url, json={"content": msg})
            else:
                url_tg = f"https://api.telegram.org/bot{config['bot_token']}/sendMessage"
                payload = {"chat_id": config['chat_id'], "message_thread_id": config['topic_id'], "text": msg, "parse_mode": "HTML"}
                requests.post(url_tg, json=payload)
            st.sidebar.success("Đã gửi báo cáo thành công!")

        # --- BẢNG CHI TIẾT TASK ---
        st.subheader("📋 Chi tiết danh sách Task")
        # Hiển thị các cột quan trọng nhất
        display_cols = ['Userstory/Todo', 'State', 'PIC', 'Estimate Dev', 'Real']
        if t_col: display_cols.append(t_col)
        st.dataframe(df_team[display_cols], use_container_width=True)

    else:
        st.error("Không tìm thấy hàng tiêu đề 'Userstory/Todo'. Hãy kiểm tra lại Sheet.")
except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
