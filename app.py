import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timezone, timedelta

# --- 1. CỐ ĐỊNH MÚI GIỜ VIỆT NAM ---
VN_TZ = timezone(timedelta(hours=7))

def get_current_sprint_info(config):
    now = datetime.now(VN_TZ).date()
    base_date = datetime.strptime(config['sprint_start_date'], "%Y-%m-%d").date()
    base_sprint_no = config['base_sprint_no']
    days_diff = (now - base_date).days
    sprint_elapsed = max(0, days_diff // 14)
    current_sprint_no = base_sprint_no + sprint_elapsed
    current_sprint_start = base_date + timedelta(days=sprint_elapsed * 14)
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

# --- 2. CẤU HÌNH DỰ ÁN ---
PROJECTS = {
    "Sprint Team Infinity": {
        "url": "https://docs.google.com/spreadsheets/d/1hentY_r7GNVwJWM3wLT7LsA3PrXQidWnYahkfSwR9Kw/edit?pli=1&gid=982443592#gid=982443592",
        "pics": ['Chuân', 'Việt', 'Thắng', 'QA', 'Mai', 'Hải Anh', 'Thuật', 'Hiếu'],
        "platform": "Telegram",
        "bot_token": "8535993887:AAFDNSLk9KRny99kQrAoQRbgpKJx_uHbkpw",
        "chat_id": "-1002102856307",
        "topic_id": 18251,
        "sprint_start_date": "2026-02-09", 
        "base_sprint_no": 31                
    },
    "Sprint Team Debuffer": {
        "url": "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592",
        "pics": ['Tài', 'Dương', 'QA', 'Quân', 'Phú', 'Thịnh', 'Đô', 'Tùng', 'Anim', 'Thắng VFX'],
        "platform": "Discord",
        "webhook_url": "https://discord.com/api/webhooks/1469191941261492386/gZ1sx5hnTojIKw5kp5quEotwIldRmCIlhXkZBu9M1Ejs-ZgEUtGsYHlS2CwIWguNbrzc",
        "sprint_start_date": "2026-02-16", 
        "base_sprint_no": 6
    }
}

st.set_page_config(page_title="Sprint Monitoring Tool", layout="wide")

if 'selected_project' not in st.session_state:
    st.session_state.selected_project = list(PROJECTS.keys())[0]

# --- 3. SIDEBAR ---
st.sidebar.title("📁 Quản lý dự án")
for project_name, p_config in PROJECTS.items():
    s_no, s_start, s_end = get_current_sprint_info(p_config)
    btn_type = "primary" if st.session_state.selected_project == project_name else "secondary"
    if st.sidebar.button(f"{project_name}\n(Sprint {int(s_no)})", use_container_width=True, type=btn_type):
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

        # Clean dữ liệu
        df['PIC'] = df['PIC'].fillna('').str.strip()
        df['State_Clean'] = df['State'].fillna('None').str.strip().str.lower()
        for col in ['Estimate Dev', 'Real']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

        df_team = df[df['PIC'].isin(config['pics'])].copy()

        # --- GIAO DIỆN CHÍNH (WEB) ---
        st.title(f"🚀 {st.session_state.selected_project}")
        st.subheader(f"🚩 Sprint {int(s_no)} ({s_start.strftime('%d/%m')} - {s_end.strftime('%d/%m')})")
        st.divider()

        # Thống kê PIC
        done_states = ['done', 'cancel', 'dev done']
        pic_stats = df_team.groupby('PIC').agg(
            total=('Userstory/Todo', 'count'),
            done=('State_Clean', lambda x: x.isin(done_states).sum()),
            doing=('State_Clean', lambda x: x.str.contains('progress').sum()),
            est_total=('Estimate Dev', 'sum'),
            real_total=('Real', 'sum')
        ).reset_index()
        
        pic_stats['pending'] = pic_stats['total'] - pic_stats['done']
        pic_stats['percent'] = (pic_stats['done'] / pic_stats['total'] * 100).fillna(0).round(1)

        # Hiển thị Metrics dạng Box PIC
        cols = st.columns(5)
        for i, row in pic_stats.iterrows():
            with cols[i % 5]:
                st.metric(row['PIC'], f"{row['percent']}%")
                st.progress(min(row['percent']/100, 1.0))
                st.write(f"✅ {int(row['done'])} | 🚧 {int(row['doing'])} | ⏳ Tồn: **{int(row['pending'])}**")
                st.caption(f"Est: {row['est_total']}h | Real: {row['real_total']}h")
                st.write("---")

        # --- LOGIC GỬI BÁO CÁO (PHÂN BIỆT TELE & DISCORD) ---
        st.sidebar.divider()
        if st.sidebar.button(f"📤 Bắn báo cáo {config['platform']}"):
            if config['platform'] == "Discord":
                # FORMAT TEAM DEBUFFER (DISCORD - ẢNH 1)
                msg = f"**{st.session_state.selected_project.upper()} - SPRINT {int(s_no)}**\n"
                msg += f"({s_start.strftime('%d/%m')} - {s_end.strftime('%d/%m')})\n"
                msg += "──────────────────────────────\n"
                for _, r in pic_stats.iterrows():
                    msg += f"🟢 **{r['PIC']}**: `{r['percent']}%` hoàn thành\n"
                    msg += f"✅ **Xong/Cancel: {int(r['done'])}**\n"
                    msg += f"🚧 Đang làm: {int(r['doing'])}\n"
                    msg += f"⏳ Chưa làm: {int(r['pending'])}\n"
                    msg += "──────────────────────────────\n"
                requests.post(config['webhook_url'], json={"content": msg})
                st.sidebar.success("Đã gửi Discord!")

            else:
                # FORMAT TEAM INFINITY (TELEGRAM - ẢNH 2)
                icons = ["🔧", "👽", "✨", "🌟", "🔍", "👾", "✏️", "💊"]
                msg = f"🤖 **AUTO REPORT ({datetime.now(VN_TZ).strftime('%d/%m %H:%M')})**\n"
                msg += f"🚩 **SPRINT {int(s_no)}**\n"
                msg += "──────────────────────────────\n"
                for i, (_, r) in enumerate(pic_stats.iterrows()):
                    icon = icons[i % len(icons)]
                    msg += f"{icon} **{r['PIC']}**\n"
                    msg += f"┣ Tiến độ: **{r['percent']}%**\n"
                    msg += f"┣ ✅ Xong: {int(r['done'])} | 🚧 Đang: {int(r['doing'])}\n"
                    msg += f"┗ ⌚ Giờ: {r['real_total']}h / {r['est_total']}h\n"
                    msg += "──────────────────────────────\n"
                
                url_tg = f"https://api.telegram.org/bot{config['bot_token']}/sendMessage"
                payload = {"chat_id": config['chat_id'], "text": msg, "parse_mode": "Markdown"}
                if "topic_id" in config: payload["message_thread_id"] = config['topic_id']
                requests.post(url_tg, json=payload)
                st.sidebar.success("Đã gửi Telegram!")

        # BIỂU ĐỒ & BẢNG CHI TIẾT
        st.plotly_chart(px.bar(pic_stats, x='PIC', y=['est_total', 'real_total'], barmode='group'), use_container_width=True)
        with st.expander("📋 Xem chi tiết danh sách Task"):
            st.dataframe(df_team[['Userstory/Todo', 'State', 'PIC', 'Estimate Dev', 'Real']], use_container_width=True)

    else:
        st.error("Không tìm thấy hàng tiêu đề 'Userstory/Todo'.")
except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
