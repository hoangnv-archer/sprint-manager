import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import requests
from datetime import datetime, timezone, timedelta
import plotly.express as px

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

# --- 2. HÀM SOẠN TIN NHẮN CHUẨN (Fix lỗi thiếu Sprint trên GitHub Action) ---
def send_report_logic(project_name, config, pic_stats):
    s_no, s_start, s_end = get_current_sprint_info(config)
    
    if config['platform'] == "Discord":
        msg = f"**{project_name.upper()} - SPRINT {int(s_no)}**\n"
        msg += f"({s_start.strftime('%d/%m')} - {s_end.strftime('%d/%m')})\n"
        msg += "──────────────────────────────\n"
        for _, r in pic_stats.iterrows():
            msg += f"🟢 **{r['PIC']}**: `{r['percent']}%` hoàn thành\n"
            msg += f"✅ **Xong/Cancel: {int(r['done'])}**\n"
            msg += f"🚧 Đang làm: {int(r['doing'])}\n"
            msg += f"⏳ Chưa làm: {int(r['pending'])}\n"
            msg += f"⏱️ Giờ: `{r['real_total']}h` / `{r['est_total']}h` (Real/Est)\n"
            msg += "──────────────────────────────\n"
        requests.post(config['webhook_url'], json={"content": msg})
    
    else:
        icons = ["🔧", "👽", "✨", "🌟", "🔍", "👾", "✏️", "💊"]
        msg = f"🤖 **AUTO REPORT ({datetime.now(VN_TZ).strftime('%d/%m %H:%M')})**\n"
        msg += f"🚩 **SPRINT {int(s_no)}**\n"
        msg += "──────────────────────────────\n"
        for i, (_, r) in enumerate(pic_stats.iterrows()):
            icon = icons[i % len(icons)]
            msg += f"{icon} **{r['PIC']}**\n"
            msg += f"┣ Tiến độ: **{r['percent']}%**\n"
            msg += f"┣ ✅ Xong: {int(r['done'])} | 🚧 Đang: {int(r['doing'])}\n"
            msg += f"┗ ⌚ Giờ: {r['real_total']}h / {r['est_total']}h (Real/Est)\n"
            msg += "──────────────────────────────\n"
        
        url_tg = f"https://api.telegram.org/bot{config['bot_token']}/sendMessage"
        payload = {"chat_id": config['chat_id'], "text": msg, "parse_mode": "Markdown"}
        if "topic_id" in config: payload["message_thread_id"] = config['topic_id']
        requests.post(url_tg, json=payload)

# --- 3. CẤU HÌNH DỰ ÁN ---
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
    }
}

# --- 4. HÀM XỬ LÝ DỮ LIỆU CHUNG ---
def get_processed_data(config):
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read(spreadsheet=config['url'], header=None, ttl=0)
    header_idx = next((i for i, row in df_raw.iterrows() if "Userstory/Todo" in row.values), None)
    if header_idx is None: return None
    
    df = conn.read(spreadsheet=config['url'], skiprows=header_idx, ttl=0)
    df.columns = [str(c).strip() for c in df.columns]
    df['PIC'] = df['PIC'].fillna('').str.strip()
    df['State_Clean'] = df['State'].fillna('None').str.strip().str.lower()
    for col in ['Estimate Dev', 'Real']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    
    df_team = df[df['PIC'].isin(config['pics'])].copy()
    done_states = ['done', 'cancel', 'dev done']
    pic_stats = df_team.groupby('PIC').agg(
        total=('Userstory/Todo', 'count'),
        done=('State_Clean', lambda x: x.isin(done_states).sum()),
        doing=('State_Clean', lambda x: x.str.contains('progress').sum()),
        est_total=('Estimate Dev', 'sum'),
        real_total=('Real', 'sum')
    ).reset_index()
    pic_stats['percent'] = (pic_stats['done'] / pic_stats['total'] * 100).fillna(0).round(1)
    pic_stats['pending'] = pic_stats['total'] - pic_stats['done']
    return pic_stats

# --- 5. CHẠY GIAO DIỆN WEB ---
def run_web():
    st.set_page_config(page_title="Sprint Dashboard", layout="wide")
    if 'selected_project' not in st.session_state:
        st.session_state.selected_project = list(PROJECTS.keys())[0]

    st.sidebar.title("📁 Dự án")
    for name, p_cfg in PROJECTS.items():
        s_no, _, _ = get_current_sprint_info(p_cfg)
        btn_type = "primary" if st.session_state.selected_project == name else "secondary"
        if st.sidebar.button(f"{name}\nSprint {int(s_no)}", use_container_width=True, type=btn_type):
            st.session_state.selected_project = name
            st.rerun()

    config = PROJECTS[st.session_state.selected_project]
    pic_stats = get_processed_data(config)
    s_no, s_start, s_end = get_current_sprint_info(config)

    if pic_stats is not None:
        st.title(f"🚀 {st.session_state.selected_project}")
        st.subheader(f"🚩 Sprint {int(s_no)} ({s_start.strftime('%d/%m')} - {s_end.strftime('%d/%m')})")
        
        st.sidebar.divider()
        if st.sidebar.button(f"📤 Bắn báo cáo {config['platform']}"):
            send_report_logic(st.session_state.selected_project, config, pic_stats)
            st.sidebar.success("Đã gửi báo cáo!")

        cols = st.columns(5)
        for i, row in pic_stats.iterrows():
            with cols[i % 5]:
                st.metric(row['PIC'], f"{row['percent']}%")
                st.progress(min(row['percent']/100, 1.0))
                st.write(f"✅ {int(row['done'])} | 🚧 {int(row['doing'])} | ⏳ Tồn: **{int(row['pending'])}**")
                st.caption(f"Est: {row['est_total']}h | Real: {row['real_total']}h")
                st.write("---")
        
        st.plotly_chart(px.bar(pic_stats, x='PIC', y=['est_total', 'real_total'], barmode='group'), use_container_width=True)
    else:
        st.error("Không tìm thấy dữ liệu hoặc lỗi cấu hình bảng tính.")

# --- 6. CHẠY TỰ ĐỘNG (GITHUB ACTIONS) ---
if __name__ == "__main__":
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx() is not None:
            run_web()
        else:
            raise ImportError
    except ImportError:
        # Code cho GitHub Actions
        for name, cfg in PROJECTS.items():
            stats = get_processed_data(cfg)
            if stats is not None:
                send_report_logic(name, cfg, stats)
