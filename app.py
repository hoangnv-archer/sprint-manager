import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import requests
from datetime import datetime, timezone, timedelta
import plotly.express as px
import sys

# --- 1. CỐ ĐỊNH MÚI GIỜ VIỆT NAM ---
VN_TZ = timezone(timedelta(hours=7))

# --- 2. ĐỊNH NGHĨA ICON CHO TỪNG NGƯỜI (PIC) ---
PIC_ICONS = {
    "Chuân": "🔧",
    "Việt": "💊",
    "Thắng": "✏️",
    "QA": "🔍",
    "Mai": "🌟",
    "Hải Anh": "✨",
    "Thuật": "🧬",
    "Hiếu": "💎",
    "Tài": "💰",
    "Dương": "🌊",
    "Quân": "⚔️",
    "Phú": "🏦",
    "Thịnh": "📈",
    "Đô": "🏰",
    "Tùng": "🌲",
    "Anim": "🎬",
    "Thắng VFX": "🎆",
    "Đạt": "🦥",
    "Bình": "🍶",
    "Hồng": "🌹",
    "Lâm": "🌲"
}
DEFAULT_ICON = "👤"

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

# --- 3. CẤU HÌNH CÁC DỰ ÁN ---
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
        "webhook_url": "YOUR_DISCORD_WEBHOOK_URL",
        "sprint_start_date": "2026-02-16", 
        "base_sprint_no": 6
    },
    "Sprint Team Skybow": {
        "url": "https://docs.google.com/spreadsheets/d/157YuS6Sq_Sr6GGl-Ze0Jb0vaIbXZMvlZmU1Yqni-6g4/edit?pli=1&gid=982443592#gid=982443592",
        "pics": ['Đạt', 'Bình', 'QA', 'Lâm', 'Hồng'],
        "platform": "Telegram", # Hoặc Discord
        "bot_token": "8722643729:AAGSvJtZVMRj-Wi2KwTctXSlJdWfMyVyxi8",
        "chat_id": "-1003176404805I",
        "topic_id": 2447, # Để 0 nếu không dùng Topic/Thread
        "sprint_start_date": "2026-02-24", # Ngày bắt đầu Sprint 1 của dự án này
        "base_sprint_no": 13
    }
}

# --- 4. HÀM XỬ LÝ DATA (Có Cache) ---
@st.cache_data(ttl=300)
def get_data_and_process(config_name):
    config = PROJECTS[config_name]
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_raw = conn.read(spreadsheet=config['url'], header=None, ttl=0)
        header_idx = next((i for i, row in df_raw.iterrows() if "Userstory/Todo" in row.values), None)
        
        if header_idx is not None:
            df = df_raw.iloc[header_idx:].copy()
            df.columns = df.iloc[0]
            df = df[1:].reset_index(drop=True)
            df.columns = [str(c).strip() for c in df.columns]
            
            df['PIC'] = df['PIC'].fillna('').astype(str).str.strip()
            df['State_Clean'] = df['State'].fillna('None').astype(str).str.strip().str.lower()
            
            for col in ['Estimate Dev', 'Real']:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace('h', '', case=False).str.replace(',', '.')
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            df_team = df[df['PIC'].isin(config['pics'])].copy()
            done_states = ['done', 'cancel', 'dev done']
            
           def get_empty_state_tasks(x):
                # Lọc những task của PIC này mà State_Clean là chuỗi rỗng
                empty_tasks = x[x['State_Clean'] == '']['Userstory/Todo'].tolist()
                return ", ".join(empty_tasks) if empty_tasks else "Không có"

            stats = df_team.groupby('PIC').agg(
                total=('Userstory/Todo', 'count'),
                done=('State_Clean', lambda x: x.isin(done_states).sum()),
                doing=('State_Clean', lambda x: x.str.contains('progress').sum()),
                est_total=('Estimate Dev', 'sum'),
                real_total=('Real', 'sum'),
                # Chỉ lấy danh sách tên task có state trống
                pending_list=('PIC', lambda x: get_empty_state_tasks(df_team.loc[x.index]))
            ).reset_index()
            
            stats['percent'] = (stats['done'] / stats['total'] * 100).fillna(0).round(1)
            # Đếm số lượng task có state trống
            stats['pending_count'] = stats['pending_list'].apply(lambda x: 0 if x == "Không có" else len(x.split(", ")))
            
            return stats
        return None
    except Exception: return None
# --- 5. HÀM GỬI TIN NHẮN ---
def send_report_logic(project_name, config, pic_stats):
    s_no, s_start, s_end = get_current_sprint_info(config)
    time_str = datetime.now(VN_TZ).strftime('%H:%M')
    
    if config['platform'] == "Discord":
        msg = f"**{project_name.upper()} - SPRINT {int(s_no)}**\n({s_start.strftime('%d/%m')} - {s_end.strftime('%d/%m')})\n──────────────────────────────\n"
        for _, r in pic_stats.iterrows():
            icon = PIC_ICONS.get(r['PIC'], DEFAULT_ICON)
            msg += f"{icon} **{r['PIC']}**: `{r['percent']}%` hoàn thành\n✅ Xong: {int(r['done'])} | 🚧 Đang: {int(r['doing'])}\n⏱️ Giờ: `{round(float(r['real_total']), 1)}h` / `{round(float(r['est_total']), 1)}h` (Real/Est)\n──────────────────────────────\n"
        requests.post(config['webhook_url'], json={"content": msg})
    else:
        msg = f"🤖 **AUTO REPORT ({time_str})**\n🚩 **SPRINT {int(s_no)}** ({s_start.strftime('%d/%m')} - {s_end.strftime('%d/%m')})\n──────────────────────────────\n"
        for _, r in pic_stats.iterrows():
            icon = PIC_ICONS.get(r['PIC'], DEFAULT_ICON)
            msg += f"{icon} **{r['PIC']}**\n┣ Tiến độ: **{r['percent']}%**\n┣ ✅ Xong: {int(r['done'])} | 🚧 Đang: {int(r['doing'])}\n┗ ⌚ Giờ: {round(float(r['real_total']), 1)}h / {round(float(r['est_total']), 1)}h\n──────────────────────────────\n"
        
        url_tg = f"https://api.telegram.org/bot{config['bot_token']}/sendMessage"
        payload = {"chat_id": config['chat_id'], "text": msg, "parse_mode": "Markdown"}
        if "topic_id" in config and config['topic_id'] != 0: 
            payload["message_thread_id"] = config['topic_id']
        requests.post(url_tg, json=payload)

# --- 6. LOGIC CHẠY (GITHUB ACTIONS VS WEB) ---
if "--action" in sys.argv:
    for name in PROJECTS.keys():
        stats = get_data_and_process.__wrapped__(name)
        if isinstance(stats, pd.DataFrame):
            send_report_logic(name, PROJECTS[name], stats)
    sys.exit(0)

st.set_page_config(page_title="Sprint Dashboard", layout="wide")
if 'selected_project' not in st.session_state:
    st.session_state.selected_project = list(PROJECTS.keys())[0]

st.sidebar.title("📁 Quản lý dự án")
for name, p_cfg in PROJECTS.items():
    s_no_side, _, _ = get_current_sprint_info(p_cfg)
    btn_type = "primary" if st.session_state.selected_project == name else "secondary"
    if st.sidebar.button(f"{name}\nSprint {int(s_no_side)}", use_container_width=True, key=f"btn_{name}", type=btn_type):
        st.session_state.selected_project = name
        st.rerun()

config = PROJECTS[st.session_state.selected_project]
pic_stats = get_data_and_process(st.session_state.selected_project)
s_no, s_start, s_end = get_current_sprint_info(config)

st.title(f"🚀 {st.session_state.selected_project}")
st.subheader(f"🚩 Sprint {int(s_no)} ({s_start.strftime('%d/%m')} - {s_end.strftime('%d/%m')})")

if st.sidebar.button(f"📤 Bắn báo cáo {config['platform']}"):
    if isinstance(pic_stats, pd.DataFrame):
        send_report_logic(st.session_state.selected_project, config, pic_stats)
        st.sidebar.success("Đã gửi báo cáo!")

if isinstance(pic_stats, pd.DataFrame):
    cols = st.columns(5)
    for i, row in pic_stats.iterrows():
        with cols[i % 5]:
            user_icon = PIC_ICONS.get(row['PIC'], DEFAULT_ICON)
            st.metric(f"{user_icon} {row['PIC']}", f"{row['percent']}%")
            st.progress(min(row['percent']/100, 1.0))
            st.write(f"⏱️ **{round(float(row['real_total']), 1)}h** / {round(float(row['est_total']), 1)}h")
            st.write(f"✅ {int(row['done'])} | 🚧 {int(row['doing'])} | ⏳ Tồn: {int(row['pending'])}")
            st.divider()
    st.plotly_chart(px.bar(pic_stats, x='PIC', y=['est_total', 'real_total'], barmode='group'), use_container_width=True)
