import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timezone, timedelta

# --- 1. CỐ ĐỊNH MÚI GIỜ VIỆT NAM ---
VN_TZ = timezone(timedelta(hours=7))

def get_current_sprint_info(config):
    """
    Tính toán Sprint dựa trên ngày bắt đầu được setup riêng cho từng dự án
    """
    now = datetime.now(VN_TZ).date()
    # Lấy ngày bắt đầu và số Sprint gốc từ config
    base_date = datetime.strptime(config['sprint_start_date'], "%Y-%m-%d").date()
    base_sprint_no = config['base_sprint_no']
    
    # Tính số ngày đã trôi qua kể từ mốc setup
    days_diff = (now - base_date).days
    
    # Chu kỳ 14 ngày (2 tuần). max(0) để tránh số âm nếu setup ngày tương lai
    sprint_elapsed = max(0, days_diff // 14)
    current_sprint_no = base_sprint_no + sprint_elapsed
    
    # Ngày bắt đầu của Sprint hiện tại
    current_sprint_start = base_date + timedelta(days=sprint_elapsed * 14)
    # Ngày kết thúc (Thứ 6 tuần sau = 11 ngày kể từ Thứ 2)
    current_sprint_end = current_sprint_start + timedelta(days=11)
    
    return current_sprint_no, current_sprint_start, current_sprint_end

def get_actual_hours(start_val):
    if pd.isna(start_val) or str(start_val).strip().lower() in ['none', '', 'nat', 'nan']:
        return 0
    try:
        start_dt = pd.to_datetime(start_val, errors='coerce')
        if pd.isna(start_dt): return 0
        now_vn = datetime.now(VN_TZ)
        if start_dt.year < 2000: 
            start_dt = start_dt.replace(year=now_vn.year, month=now_vn.month, day=now_vn.day)
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=VN_TZ)
        return max(0, (now_vn - start_dt).total_seconds() / 3600)
    except: return 0

# --- 2. CẤU HÌNH DỰ ÁN (SETUP TẠI ĐÂY) ---
PROJECTS = {
    "Sprint Team Infinity": {
        "url": "https://docs.google.com/spreadsheets/d/1hentY_r7GNVwJWM3wLT7LsA3PrXQidWnYahkfSwR9Kw/edit?pli=1&gid=982443592#gid=982443592",
        "pics": ['Chuân', 'Việt', 'Thắng', 'QA', 'Mai', 'Hải Anh', 'Thuật', 'Hiếu'],
        "platform": "Telegram",
        "bot_token": "8535993887:AAFDNSLk9KRny99kQrAoQRbgpKJx_uHbkpw",
        "chat_id": "-1002102856307",
        "topic_id": 18251,
        # Setup Sprint:
        "sprint_start_date": "2026-02-09", 
        "base_sprint_no": 1                
    },
    "Sprint Team Debuffer": {
        "url": "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592",
        "pics": ['Tài', 'Dương', 'QA', 'Quân', 'Phú', 'Thịnh', 'Đô', 'Tùng', 'Anim', 'Thắng VFX'],
        "platform": "Discord",
        # Setup Sprint (So le):
        "sprint_start_date": "2026-02-16", 
        "base_sprint_no": 1
    }
}

st.set_page_config(page_title="Sprint Dashboard", layout="wide")

if 'selected_project' not in st.session_state:
    st.session_state.selected_project = list(PROJECTS.keys())[0]

# --- 3. SIDEBAR ---
st.sidebar.title("📁 Quản lý Sprint")
for project_name, p_config in PROJECTS.items():
    s_no, s_start, s_end = get_current_sprint_info(p_config)
    btn_label = f"{project_name}\n(Sprint {int(s_no)})"
    if st.sidebar.button(btn_label, use_container_width=True, 
                         type="primary" if st.session_state.selected_project == project_name else "secondary"):
        st.session_state.selected_project = project_name
        st.rerun()

config = PROJECTS[st.session_state.selected_project]
s_no, s_start, s_end = get_current_sprint_info(config)

# --- 4. XỬ LÝ DỮ LIỆU ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read(spreadsheet=config['url'], header=None, ttl=0)
    header_idx = next((i for i, row in df_raw.iterrows() if "Userstory/Todo" in row.values), None)
            
    if header_idx is not None:
        df = conn.read(spreadsheet=config['url'], skiprows=header_idx, ttl=0)
        df.columns = [str(c).strip() for c in df.columns]

        # Chuẩn hóa số
        for col in ['Estimate Dev', 'Real']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

        t_col = next((c for c in df.columns if "start" in c.lower()), None)
        df['State_Clean'] = df['State'].fillna('None').str.strip().str.lower()
        df_team = df[df['PIC'].isin(config['pics'])].copy()

        # Hiển thị Tiêu đề & Thông tin Sprint
        st.title(f"🚀 {st.session_state.selected_project}")
        st.info(f"📅 **Sprint {int(s_no)}**: Từ {s_start.strftime('%d/%m/%Y')} đến {s_end.strftime('%d/%m/%Y')} (Kết thúc Thứ 6)")

        # --- LOGIC CẢNH BÁO LỐ GIỜ ---
        over_est_list = []
        if t_col:
            for _, row in df_team.iterrows():
                if 'progress' in str(row['State_Clean']):
                    actual_h = get_actual_hours(row[t_col])
                    est_h = float(row['Estimate Dev'])
                    if est_h > 0 and actual_h > est_h:
                        over_est_list.append({
                            "PIC": row['PIC'], "Task": row['Userstory/Todo'], 
                            "Thực tế": f"{round(actual_h, 2)}h", "Vượt": f"{round((actual_h - est_h) * 60)}p"
                        })

        if over_est_list:
            st.error(f"🚨 CẢNH BÁO LỐ GIỜ TRONG SPRINT")
            st.table(pd.DataFrame(over_est_list))

        # --- THỐNG KÊ PIC ---
        pic_stats = df_team.groupby('PIC').agg(
            total=('Userstory/Todo', 'count'),
            done=('State_Clean', lambda x: x.isin(['done', 'cancel', 'dev done']).sum()),
            doing=('State_Clean', lambda x: x.str.contains('progress').sum()),
            est_total=('Estimate Dev', 'sum'),
            real_total=('Real', 'sum')
        ).reset_index()
        pic_stats['pending'] = pic_stats['total'] - pic_stats['done']
        pic_stats['percent'] = (pic_stats['done'] / pic_stats['total'] * 100).fillna(0).round(1)

        st.subheader("👤 Trạng thái chi tiết PIC")
        cols = st.columns(5)
        for i, row in pic_stats.iterrows():
            with cols[i % 5]:
                st.metric(row['PIC'], f"{row['percent']}%")
                st.write(f"✅ {int(row['done'])} | 🚧 {int(row['doing'])} | ⏳ Tồn: {int(row['pending'])}")
                st.progress(min(row['percent']/100, 1.0))
                st.divider()

        st.plotly_chart(px.bar(pic_stats, x='PIC', y=['est_total', 'real_total'], barmode='group', title="So sánh Giờ Dự kiến vs Thực tế"), use_container_width=True)

        # --- GỬI BÁO CÁO ---
        st.sidebar.divider()
        if st.sidebar.button(f"📤 Bắn báo cáo {config['platform']}"):
            msg = f"📊 **REPORT: {st.session_state.selected_project} (Sprint {int(s_no)})**\n"
            for _, r in pic_stats.iterrows():
                msg += f"• {r['PIC']}: {r['percent']}% (Tồn: {int(r['pending'])})\n"
            if over_est_list:
                msg += "\n🚨 **LỐ GIỜ:** " + ", ".join([f"{x['PIC']}" for x in over_est_list])
            
            if config['platform'] == "Discord":
                webhook_url = st.sidebar.text_input("Dán Webhook:", type="password")
                if webhook_url: requests.post(webhook_url, json={"content": msg})
            else:
                url_tg = f"https://api.telegram.org/bot{config['bot_token']}/sendMessage"
                requests.post(url_tg, json={"chat_id": config['chat_id'], "text": msg})
            st.sidebar.success("Đã gửi!")

        st.subheader("📋 Bảng chi tiết Task")
        st.dataframe(df_team[['Userstory/Todo', 'State', 'PIC', 'Estimate Dev', 'Real']], use_container_width=True)

    else:
        st.error("Không tìm thấy hàng tiêu đề 'Userstory/Todo'.")
except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
