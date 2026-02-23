import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timezone, timedelta

# --- 1. CẤU HÌNH THỜI GIAN ---
VN_TZ = timezone(timedelta(hours=7))

def get_current_sprint_info(project_name):
    """
    Tính toán Sprint hiện tại (Chu kỳ 14 ngày)
    Giả định: 
    - Team 2 bắt đầu Sprint vào Thứ 2 ngày 09/02/2026 (Tuần A)
    - Final bắt đầu Sprint vào Thứ 2 ngày 16/02/2026 (Tuần B - So le)
    """
    now = datetime.now(VN_TZ).date()
    
    # Mốc thời gian gốc (Thứ 2 của một tuần nào đó làm chuẩn)
    base_date = datetime(2026, 2, 9).date() # Một ngày thứ 2 chuẩn
    
    days_diff = (now - base_date).days
    
    # Nếu là dự án Final (so le), ta dịch mốc gốc đi 7 ngày
    if project_name == "Sprint Dashboard Final":
        days_diff -= 7
        
    sprint_no = (days_diff // 14) + 1
    sprint_start = base_date + timedelta(days=(sprint_no - 1) * 14)
    if project_name == "Sprint Dashboard Final":
        sprint_start += timedelta(days=7)
        
    sprint_end = sprint_start + timedelta(days=11) # Kết thúc vào Thứ 6 tuần sau (12 ngày tính cả Thứ 2)
    
    return sprint_no, sprint_start, sprint_end

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

st.set_page_config(page_title="Sprint Dashboard", layout="wide")

if 'selected_project' not in st.session_state:
    st.session_state.selected_project = list(PROJECTS.keys())[0]

# --- SIDEBAR ---
st.sidebar.title("📂 Dự án & Sprint")
for project_name in PROJECTS.keys():
    s_no, s_start, s_end = get_current_sprint_info(project_name)
    btn_label = f"{project_name}\n(Sprint {s_no})"
    if st.sidebar.button(btn_label, use_container_width=True, 
                         type="primary" if st.session_state.selected_project == project_name else "secondary"):
        st.session_state.selected_project = project_name
        st.rerun()

config = PROJECTS[st.session_state.selected_project]
s_no, s_start, s_end = get_current_sprint_info(st.session_state.selected_project)

# --- 4. XỬ LÝ DỮ LIỆU ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read(spreadsheet=config['url'], header=None, ttl=0)
    header_idx = next((i for i, row in df_raw.iterrows() if "Userstory/Todo" in row.values), None)
            
    if header_idx is not None:
        df = conn.read(spreadsheet=config['url'], skiprows=header_idx, ttl=0)
        df.columns = [str(c).strip() for c in df.columns]

        # Chuẩn hóa
        for col in ['Estimate Dev', 'Real']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

        t_col = next((c for c in df.columns if "start" in c.lower()), None)
        df['State_Clean'] = df['State'].fillna('None').str.strip().str.lower()
        df_team = df[df['PIC'].isin(config['pics'])].copy()

        # Hiển thị thông tin Sprint
        st.title(f"🚀 {st.session_state.selected_project}")
        st.subheader(f"📅 Sprint {s_no} ({s_start.strftime('%d/%m')} - {s_end.strftime('%d/%m')})")

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

        cols = st.columns(5)
        for i, row in pic_stats.iterrows():
            with cols[i % 5]:
                st.metric(row['PIC'], f"{row['percent']}%")
                st.write(f"✅ {int(row['done'])} | 🚧 {int(row['doing'])} | ⏳ Tồn: {int(row['pending'])}")
                st.progress(min(row['percent']/100, 1.0))

        st.plotly_chart(px.bar(pic_stats, x='PIC', y=['est_total', 'real_total'], barmode='group'), use_container_width=True)

        st.subheader("📋 Danh sách Task")
        st.dataframe(df_team[['Userstory/Todo', 'State', 'PIC', 'Estimate Dev', 'Real']], use_container_width=True)

    else:
        st.error("Không tìm thấy dữ liệu.")
except Exception as e:
    st.error(f"Lỗi: {e}")
