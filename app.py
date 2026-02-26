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

# --- 2. QUẢN LÝ DỰ ÁN ---
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
    base_sprint_no = config['base_sprint_no']
    days_diff = (now - base_date).days
    sprint_elapsed = max(0, days_diff // 14)
    current_sprint_no = base_sprint_no + sprint_elapsed
    current_sprint_start = base_date + timedelta(days=sprint_elapsed * 14)
    current_sprint_end = current_sprint_start + timedelta(days=11)
    return current_sprint_no, current_sprint_start, current_sprint_end

# --- 3. XỬ LÝ DỮ LIỆU ---
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
            df['Userstory'] = df['Userstory'].fillna('Khác').astype(str).str.strip()
            df['Userstory/Todo'] = df['Userstory/Todo'].fillna('').astype(str).str.strip()
            df['State_Clean'] = df['State'].fillna('').astype(str).str.strip().str.lower()
            
            df = df[df['Userstory/Todo'] != ""]
            
            for col in ['Estimate Dev', 'Real']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace('h','').str.replace(',','.'), errors='coerce').fillna(0)
            
            df_team = df[df['PIC'].isin(config['pics'])].copy()
            done_states = ['done', 'cancel', 'dev done']
            
            # Grouping theo PIC
            stats = df_team.groupby('PIC').agg(
                total=('Userstory/Todo', 'count'),
                done=('State_Clean', lambda x: x.isin(done_states).sum()),
                doing=('State_Clean', lambda x: x.str.contains('progress').sum()),
                est_total=('Estimate Dev', 'sum'),
                real_total=('Real', 'sum')
            ).reset_index()

            # Logic Group theo Userstory cho App
            def get_grouped_tasks(pic):
                pending = df_team[(df_team['PIC'] == pic) & (df_team['State_Clean'] == '')]
                if pending.empty: return {}, 0
                # Group: { Userstory: [Task1, Task2] }
                grouped = pending.groupby('Userstory')['Userstory/Todo'].apply(list).to_dict()
                return grouped, len(pending)

            res = stats['PIC'].apply(get_grouped_tasks)
            stats['pending_grouped'] = [x[0] for x in res]
            stats['pending_count'] = [x[1] for x in res]
            stats['percent'] = (stats['done'] / stats['total'] * 100).fillna(0).round(1)
            
            return stats
        return None
    except: return None

# --- 4. GỬI BÁO CÁO (Chỉ hiện số lượng) ---
def send_report_logic(project_name, config, pic_stats):
    s_no, s_start, s_end = get_current_sprint_info(config)
    time_str = datetime.now(VN_TZ).strftime('%H:%M')
    
    msg = f"🤖 **AUTO REPORT ({time_str})**\n🚩 **{project_name.upper()} - SPRINT {int(s_no)}**\n──────────────────────────────\n"
    for _, r in pic_stats.iterrows():
        icon = PIC_ICONS.get(r['PIC'], DEFAULT_ICON)
        msg += f"{icon} **{r['PIC']}**\n┣ Tiến độ: **{r['percent']}%**\n┣ ✅ Xong: {int(r['done'])} | 🚧 Đang: {int(r['doing'])}\n┣ ⌚ Giờ: {round(float(r['real_total']), 1)}h / {round(float(r['est_total']), 1)}h\n"
        
        # Chỉ hiển thị số lượng tồn
        if r['pending_count'] > 0:
            msg += f"┗ ⏳ **Trống State: {int(r['pending_count'])} việc**\n"
        else:
            msg += f"┗ ✅ Đã điền đủ trạng thái!\n"
        msg += "──────────────────────────────\n"

    try:
        if config['platform'] == "Telegram":
            url = f"https://api.telegram.org/bot{config['bot_token']}/sendMessage"
            payload = {"chat_id": config['chat_id'], "text": msg, "parse_mode": "Markdown"}
            if config.get('topic_id'): payload["message_thread_id"] = config['topic_id']
            requests.post(url, json=payload, timeout=10)
        elif config['platform'] == "Discord":
            requests.post(config['webhook_url'], json={"content": msg}, timeout=10)
    except: pass

# --- 5. GIAO DIỆN WEB ---
st.set_page_config(page_title="Sprint Dashboard", layout="wide")

if "--action" in sys.argv:
    for name, cfg in PROJECTS.items():
        data = get_data_and_process.__wrapped__(name)
        if isinstance(data, pd.DataFrame): send_report_logic(name, cfg, data)
    sys.exit(0)

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
    
    if st.sidebar.button("📤 Bắn báo cáo"):
        send_report_logic(st.session_state.selected_project, config, pic_stats)
        st.sidebar.success("Đã gửi!")

    cols = st.columns(5)
    for i, row in pic_stats.iterrows():
        with cols[i % 5]:
            icon = PIC_ICONS.get(row['PIC'], DEFAULT_ICON)
            st.metric(f"{icon} {row['PIC']}", f"{row['percent']}%")
            st.progress(min(row['percent']/100, 1.0))
            st.write(f"✅ {int(row['done'])} | ⏳ Tồn: **{int(row['pending_count'])}**")
            
            # Hiển thị Group theo Userstory trên App
            if row['pending_count'] > 0:
                with st.expander("Chi tiết task tồn"):
                    for us, tasks in row['pending_grouped'].items():
                        st.markdown(f"**📌 {us}**")
                        for t in tasks:
                            st.caption(f"• {t}")
            st.divider()
    
    st.plotly_chart(px.bar(pic_stats, x='PIC', y=['est_total', 'real_total'], barmode='group'), use_container_width=True)
