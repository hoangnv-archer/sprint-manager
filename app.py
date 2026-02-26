import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import requests
from datetime import datetime, timezone, timedelta
import plotly.express as px
import sys

# --- 1. CẤU HÌNH ---
VN_TZ = timezone(timedelta(hours=7))
PIC_ICONS = {
    "Chuân": "🔧", "Việt": "💊", "Thắng": "✏️", "QA": "🔍",
    "Mai": "🌟", "Hải Anh": "✨", "Thuật": "🧬", "Hiếu": "💎",
    "Tài": "💰", "Dương": "🌊", "Quân": "⚔️", "Phú": "🏦",
    "Thịnh": "📈", "Đô": "🏰", "Tùng": "🌲", "Anim": "🎬",
    "Thắng VFX": "🎆", "Đạt": "🦥", "Bình": "🍶", "Hồng": "🌹", "Lâm": "🌲", "An": "🐞"
}
DEFAULT_ICON = "👤"

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
    },
    "Sprint Team Skybow": {
        "url": "https://docs.google.com/spreadsheets/d/157YuS6Sq_Sr6GGl-Ze0Jb0vaIbXZMvlZmU1Yqni-6g4/edit?pli=1&gid=982443592#gid=982443592",
        "pics": ['Đạt', 'Bình', 'QA', 'Lâm', 'Hồng', 'An'],
        "platform": "Telegram",
        "bot_token": "8722643729:AAGSvJtZVMRj-Wi2KwTctXSlJdWfMyVyxi8",
        "chat_id": "-1003176404805",
        "topic_id": 2447,
        "sprint_start_date": "2026-02-24",
        "base_sprint_no": 13
    }
}

def get_current_sprint_info(config):
    now = datetime.now(VN_TZ).date()
    base_date = datetime.strptime(config['sprint_start_date'], "%Y-%m-%d").date()
    days_diff = (now - base_date).days
    sprint_elapsed = max(0, days_diff // 14)
    current_sprint_no = config['base_sprint_no'] + sprint_elapsed
    current_sprint_start = base_date + timedelta(days=sprint_elapsed * 14)
    current_sprint_end = current_sprint_start + timedelta(days=11)
    return current_sprint_no, current_sprint_start, current_sprint_end

# --- XỬ LÝ DỮ LIỆU ---
@st.cache_data(ttl=60)
def get_data_and_process(config_name):
    config = PROJECTS[config_name]
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_raw = conn.read(spreadsheet=config['url'], header=None, ttl=0)
        
        header_idx = None
        for i, row in df_raw.iterrows():
            if any("Userstory/Todo" in str(val) for val in row.values):
                header_idx = i
                break
        
        if header_idx is not None:
            df = df_raw.iloc[header_idx:].copy()
            df.columns = df.iloc[0]
            df = df[1:].reset_index(drop=True)
            df.columns = [str(c).strip() for c in df.columns]
            
            # --- TỰ ĐỘNG NHẬN DIỆN CỘT (Fix lỗi 'Userstory') ---
            col_map = {c.lower().replace(" ", ""): c for c in df.columns}
            us_col = col_map.get('userstory', col_map.get('userstory/todo', df.columns[0]))
            pic_col = col_map.get('pic', 'PIC')
            todo_col = col_map.get('userstory/todo', df.columns[1])
            state_col = col_map.get('state', 'State')

            df['PIC_Clean'] = df[pic_col].fillna('').astype(str).str.strip()
            df['US_Clean'] = df[us_col].fillna('Khác').astype(str).str.strip()
            df['Todo_Clean'] = df[todo_col].fillna('').astype(str).str.strip()
            df['State_Clean'] = df[state_col].fillna('').astype(str).str.strip().str.lower()
            
            df = df[df['Todo_Clean'] != ""]
            
            for col in ['Estimate Dev', 'Real']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace('h','').str.replace(',','.'), errors='coerce').fillna(0)
                else: df[col] = 0
            
            df_team = df[df['PIC_Clean'].isin(config['pics'])].copy()
            done_states = ['done', 'cancel', 'dev done']
            
            stats = df_team.groupby('PIC_Clean').agg(
                total=('Todo_Clean', 'count'),
                done=('State_Clean', lambda x: x.isin(done_states).sum()),
                doing=('State_Clean', lambda x: x.str.contains('progress').sum()),
                est_total=('Estimate Dev', 'sum'),
                real_total=('Real', 'sum')
            ).reset_index()
            stats.rename(columns={'PIC_Clean': 'PIC'}, inplace=True)

            def get_grouped_tasks(pic):
                pending = df_team[(df_team['PIC_Clean'] == pic) & (df_team['State_Clean'] == '')]
                if pending.empty: return {}, 0
                grouped = pending.groupby('US_Clean')['Todo_Clean'].apply(list).to_dict()
                return grouped, len(pending)

            res = stats['PIC'].apply(get_grouped_tasks)
            stats['pending_grouped'] = [x[0] for x in res]
            stats['pending_count'] = [x[1] for x in res]
            stats['percent'] = (stats['done'] / stats['total'] * 100).fillna(0).round(1)
            
            return stats
        return None
    except Exception as e:
        st.error(f"Lỗi đọc dữ liệu: {e}")
        return None

# --- GỬI BÁO CÁO ---
def send_report_logic(project_name, config, pic_stats):
    s_no, s_start, s_end = get_current_sprint_info(config)
    time_str = datetime.now(VN_TZ).strftime('%H:%M')
    msg = f"🤖 **AUTO REPORT ({time_str})**\n🚩 **{project_name.upper()} - SPRINT {int(s_no)}**\n──────────────────────────────\n"
    for _, r in pic_stats.iterrows():
        icon = PIC_ICONS.get(r['PIC'], DEFAULT_ICON)
        msg += f"{icon} **{r['PIC']}**\n┣ Tiến độ: **{r['percent']}%**\n┣ ✅ Xong: {int(r['done'])} | 🚧 Đang: {int(r['doing'])}\n┣ ⌚ Giờ: {round(float(r['real_total']), 1)}h / {round(float(r['est_total']), 1)}h\n"
        if r['pending_count'] > 0:
            msg += f"┗ ⏳ **Trống State: {int(r['pending_count'])} việc**\n"
        else:
            msg += f"┗ ✅ Đã cập nhật đủ!\n"
        msg += "──────────────────────────────\n"

    try:
        if config['platform'] == "Telegram":
            url = f"https://api.telegram.org/bot{config['bot_token']}/sendMessage"
            requests.post(url, json={"chat_id": config['chat_id'], "text": msg, "parse_mode": "Markdown", "message_thread_id": config.get('topic_id')}, timeout=10)
        elif config['platform'] == "Discord" and "http" in str(config.get('webhook_url')):
            requests.post(config['webhook_url'], json={"content": msg}, timeout=10)
    except: pass

# --- GIAO DIỆN WEB ---
st.set_page_config(page_title="Sprint Dashboard", layout="wide")

if 'selected_project' not in st.session_state:
    st.session_state.selected_project = list(PROJECTS.keys())[0]

# Sidebar
st.sidebar.title("📁 Quản lý dự án")
for name in PROJECTS.keys():
    btn_type = "primary" if st.session_state.selected_project == name else "secondary"
    if st.sidebar.button(name, use_container_width=True, type=btn_type):
        st.session_state.selected_project = name
        st.rerun()

# Nội dung chính
config = PROJECTS[st.session_state.selected_project]
pic_stats = get_data_and_process(st.session_state.selected_project)

if pic_stats is not None:
    s_no, s_start, s_end = get_current_sprint_info(config)
    st.title(f"🚀 {st.session_state.selected_project}")
    st.subheader(f"🚩 Sprint {int(s_no)} ({s_start.strftime('%d/%m')} - {s_end.strftime('%d/%m')})")
    
    if st.sidebar.button("📤 Gửi báo cáo ngay"):
        send_report_logic(st.session_state.selected_project, config, pic_stats)
        st.sidebar.success("Đã gửi báo cáo!")

    cols = st.columns(5)
    for i, row in pic_stats.iterrows():
        with cols[i % 5]:
            icon = PIC_ICONS.get(row['PIC'], DEFAULT_ICON)
            st.metric(f"{icon} {row['PIC']}", f"{row['percent']}%")
            st.progress(min(row['percent']/100, 1.0))
            st.write(f"✅ {int(row['done'])} | ⏳ Tồn: **{int(row['pending_count'])}**")
            
            if row['pending_count'] > 0:
                with st.expander("Chi tiết task tồn"):
                    for us, tasks in row['pending_grouped'].items():
                        st.markdown(f"**📌 {us}**")
                        for t in tasks:
                            st.caption(f"• {t}")
            st.divider()
    
    st.plotly_chart(px.bar(pic_stats, x='PIC', y=['est_total', 'real_total'], barmode='group'), use_container_width=True)
else:
    st.info("Đang kiểm tra dữ liệu file Google Sheet...")
