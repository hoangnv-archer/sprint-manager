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
        "sprint_start_date": "2026-03-02", 
        "base_sprint_no": 33                
    },
    "Sprint Team Debuffer": {
        "url": "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592",
        "pics": ['Tài', 'Dương', 'QA', 'Quân', 'Phú', 'Thịnh', 'Đô', 'Tùng', 'Anim', 'Thắng VFX'],
        "platform": "Discord",
        "webhook_url": "https://discord.com/api/webhooks/1469191941261492386/gZ1sx5hnTojIKw5kp5quEotwIldRmCIlhXkZBu9M1Ejs-ZgEUtGsYHlS2CwIWguNbrzc",
        "sprint_start_date": "2026-02-23", 
        "base_sprint_no": 7
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

            # Xử lý gán Userstory cho từng dòng Task
            current_us = "General"
            processed_data = []
            
            for _, row in df.iterrows():
                title = str(row.get('Userstory/Todo', '')).strip()
                pic = str(row.get('PIC', '')).strip()
                state = str(row.get('State', '')).strip()
                
                if not title: continue
                
                # Logic: Nếu không có PIC và không có State -> Đây là dòng Userstory
                if (not pic or pic == 'nan') and (not state or state == 'nan'):
                    current_us = title
                else:
                    # Đây là một Task
                    row_data = row.to_dict()
                    row_data['Assigned_US'] = current_us
                    processed_data.append(row_data)
            
            df_final = pd.DataFrame(processed_data)
            df_final['PIC_Clean'] = df_final['PIC'].fillna('').astype(str).str.strip()
            df_final['State_Clean'] = df_final['State'].fillna('').astype(str).str.strip().str.lower()
            
            # Chỉ lấy dữ liệu của team
            df_team = df_final[df_final['PIC_Clean'].isin(config['pics'])].copy()
            done_states = ['done', 'cancel', 'dev done']
            
            # Thống kê
            stats = df_team.groupby('PIC_Clean').agg(
                total=('Userstory/Todo', 'count'),
                done=('State_Clean', lambda x: x.isin(done_states).sum()),
                doing=('State_Clean', lambda x: x.str.contains('progress').sum()),
                est_total=('Estimate Dev', lambda x: pd.to_numeric(x.astype(str).str.replace('h',''), errors='coerce').sum()),
                real_total=('Real', lambda x: pd.to_numeric(x.astype(str).str.replace('h',''), errors='coerce').sum())
            ).reset_index()
            stats.rename(columns={'PIC_Clean': 'PIC'}, inplace=True)

            # Gom nhóm task trống state theo US (Chỉ dùng cho App)
            def get_grouped_pending(pic):
                pending = df_team[(df_team['PIC_Clean'] == pic) & (df_team['State_Clean'] == '')]
                if pending.empty: return {}, 0
                grouped = pending.groupby('Assigned_US')['Userstory/Todo'].apply(list).to_dict()
                return grouped, len(pending)

            res = stats['PIC'].apply(get_grouped_pending)
            stats['pending_grouped'] = [x[0] for x in res]
            stats['pending_count'] = [x[1] for x in res]
            stats['percent'] = (stats['done'] / stats['total'] * 100).fillna(0).round(1)
            
            return stats
        return None
    except Exception as e:
        st.error(f"Lỗi: {e}")
        return None

# --- GỬI BÁO CÁO (Chỉ hiện tổng số) ---
def send_report_logic(project_name, config, pic_stats):
    s_no, s_start, s_end = get_current_sprint_info(config)
    time_str = datetime.now(VN_TZ).strftime('%H:%M')
    msg = f"🤖 **AUTO REPORT ({time_str})**\n🚩 **{project_name.upper()} - SPRINT {int(s_no)}**\n──────────────────────────────\n"
    for _, r in pic_stats.iterrows():
        icon = PIC_ICONS.get(r['PIC'], DEFAULT_ICON)
        msg += f"{icon} **{r['PIC']}**\n┣ Tiến độ: **{r['percent']}%**\n┣ ✅ Xong: {int(r['done'])} | 🚧 Đang: {int(r['doing'])}\n"
        
        # Ở ĐÂY: Chỉ ghi tổng số, không liệt kê task
        if r['pending_count'] > 0:
            msg += f"┗ ⏳ **Trống State: {int(r['pending_count'])} task**\n"
        else:
            msg += f"┗ ✅ Đã cập nhật đủ!\n"
        msg += "──────────────────────────────\n"

    try:
        if config['platform'] == "Telegram":
            url = f"https://api.telegram.org/bot{config['bot_token']}/sendMessage"
            requests.post(url, json={"chat_id": config['chat_id'], "text": msg, "parse_mode": "Markdown", "message_thread_id": config.get('topic_id')}, timeout=10)
        elif config['platform'] == "Discord":
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
            
            # TRÊN APP: Hiển thị group theo Userstory
            if row['pending_count'] > 0:
                with st.expander("Chi tiết task tồn"):
                    for us, tasks in row['pending_grouped'].items():
                        st.markdown(f"**📌 {us}**")
                        for t in tasks:
                            st.caption(f"• {t}")
            st.divider()
    
    st.plotly_chart(px.bar(pic_stats, x='PIC', y=['est_total', 'real_total'], barmode='group'), use_container_width=True)
else:
    st.info("Không tìm thấy dữ liệu phù hợp...")
