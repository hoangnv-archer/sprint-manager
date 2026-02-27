import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import requests
from datetime import datetime, timezone, timedelta
import plotly.express as px
import sys
st.set_page_config(
    page_title="Sprint Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed", # Tự động thu gọn sidebar để đỡ chiếm chỗ trên mobile
)
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

# --- 2. XỬ LÝ DỮ LIỆU ---
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

            current_us = "General"
            processed_data = []
            
            for _, row in df.iterrows():
                title = str(row.get('Userstory/Todo', '')).strip()
                pic = str(row.get('PIC', '')).strip()
                state = str(row.get('State', '')).strip()
                
                if not title or title.lower() == 'nan': continue
                
                if (not pic or pic.lower() == 'nan') and (not state or state.lower() == 'nan'):
                    current_us = title
                else:
                    row_data = row.to_dict()
                    row_data['Assigned_US'] = current_us
                    processed_data.append(row_data)
            
            if not processed_data: return None
            df_final = pd.DataFrame(processed_data)
            df_final['PIC_Clean'] = df_final['PIC'].fillna('').astype(str).str.strip()
            df_final['State_Clean'] = df_final['State'].fillna('').astype(str).str.strip().str.lower()
            
            for col in ['Estimate Dev', 'Real']:
                if col in df_final.columns:
                    df_final[col] = pd.to_numeric(df_final[col].astype(str).str.replace('h',''), errors='coerce').fillna(0)
            
            df_team = df_final[df_final['PIC_Clean'].isin(config['pics'])].copy()
            done_states = ['done', 'cancel', 'dev done']
            
            stats = df_team.groupby('PIC_Clean').agg(
                total=('Userstory/Todo', 'count'),
                done_count=('State_Clean', lambda x: x.isin(done_states).sum()),
                doing_count=('State_Clean', lambda x: x.str.contains('progress').sum()),
                est_total=('Estimate Dev', 'sum'),
                real_total=('Real', 'sum')
            ).reset_index()
            stats.rename(columns={'PIC_Clean': 'PIC'}, inplace=True)

            def get_tasks_detail(pic):
                p_tasks = df_team[df_team['PIC_Clean'] == pic]
                done = p_tasks[p_tasks['State_Clean'].isin(done_states)].groupby('Assigned_US')['Userstory/Todo'].apply(list).to_dict()
                doing = p_tasks[p_tasks['State_Clean'].str.contains('progress')].groupby('Assigned_US')['Userstory/Todo'].apply(list).to_dict()
                pending = p_tasks[p_tasks['State_Clean'] == ''].groupby('Assigned_US')['Userstory/Todo'].apply(list).to_dict()
                
                return {
                    'done': done, 'doing': doing, 'pending': pending,
                    'pending_count': len(p_tasks[p_tasks['State_Clean'] == ''])
                }

            details = stats['PIC'].apply(get_tasks_detail)
            stats['details'] = details
            stats['pending_count'] = [x['pending_count'] for x in details]
            stats['percent'] = (stats['done_count'] / stats['total'] * 100).fillna(0).round(1)
            
            return stats
        return None
    except Exception as e:
        if "--action" not in sys.argv: st.error(f"Lỗi: {e}")
        return None

# --- 3. GIAO DIỆN STREAMLIT ---
st.set_page_config(page_title="Sprint Dashboard", layout="wide", initial_sidebar_state="collapsed")

# Sidebar chọn dự án
st.sidebar.title("📁 Dự án")
if 'selected_project' not in st.session_state:
    st.session_state.selected_project = list(PROJECTS.keys())[0]

for name in PROJECTS.keys():
    if st.sidebar.button(name, use_container_width=True, type="primary" if st.session_state.selected_project == name else "secondary"):
        st.session_state.selected_project = name
        st.rerun()

config = PROJECTS[st.session_state.selected_project]
pic_stats = get_data_and_process(st.session_state.selected_project)

if pic_stats is not None:
    s_no, s_start, s_end = get_current_sprint_info(config)
    st.title(f"🚀 {st.session_state.selected_project}")
    st.caption(f"📅 Sprint {int(s_no)}: {s_start.strftime('%d/%m')} - {s_end.strftime('%d/%m')}")

    # --- PHẦN TỔNG KẾT TOÀN TEAM ---
    st.divider()
    t_cols = st.columns(4)
    with t_cols[0]:
        st.metric("✅ Tổng Xong", f"{int(pic_stats['done_count'].sum())} task")
    with t_cols[1]:
        st.metric("🚧 Tổng Đang làm", f"{int(pic_stats['doing_count'].sum())} task")
    with t_cols[2]:
        st.metric("⏳ Tổng Tồn", f"{int(pic_stats['pending_count'].sum())} task", delta_color="inverse")
    with t_cols[3]:
        total_h = pic_stats['real_total'].sum()
        st.metric("⌚ Tổng Giờ Real", f"{round(total_h, 1)}h")
    st.divider()

    # --- DANH SÁCH PIC ---
    # Hiển thị dạng thẻ
    for i in range(0, len(pic_stats), 2): # Chia 2 cột trên mobile cho cân đối
        cols = st.columns(2)
        for j in range(2):
            idx = i + j
            if idx < len(pic_stats):
                row = pic_stats.iloc[idx]
                with cols[j]:
                    icon = PIC_ICONS.get(row['PIC'], DEFAULT_ICON)
                    st.markdown(f"#### {icon} {row['PIC']}")
                    st.progress(min(row['percent']/100, 1.0))
                    
                    # Thông số 3 loại task
                    c1, c2, c3 = st.columns(3)
                    c1.caption(f"✅ **{int(row['done_count'])}**")
                    c2.caption(f"🚧 **{int(row['doing_count'])}**")
                    c3.caption(f"⏳ **{int(row['pending_count'])}**")
                    
                    st.caption(f"⌚ {round(row['real_total'],1)}h / {round(row['est_total'],1)}h ({row['percent']}%)")
                    
                    with st.expander("Chi tiết Task"):
                        d = row['details']
                        if d['doing']:
                            st.write("🚧 **Đang làm:**")
                            for us, tasks in d['doing'].items():
                                st.markdown(f"- *{us}*")
                                for t in tasks: st.caption(f"  + {t}")
                            
                        if d['pending']:
                            st.write("⏳ **Chưa có State:**")
                            for us, tasks in d['pending'].items():
                                st.markdown(f"- *{us}*")
                                for t in tasks: st.caption(f"  + {t}")
            
                        if d['done']:
                            st.write("✅ **Đã xong:**")
                            for us, tasks in d['done'].items():
                                st.markdown(f"- *{us}*")
                                for t in tasks: st.caption(f"  + {t}")
                    st.divider()
                    st.write("") # Khoảng cách giữa các hàng

    st.plotly_chart(px.bar(pic_stats, x='PIC', y=['est_total', 'real_total'], barmode='group', title="Biểu đồ giờ dự án"), use_container_width=True)

else:
    st.info("Đang kiểm tra dữ liệu từ Google Sheets...")
