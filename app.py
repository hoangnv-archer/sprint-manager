import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import requests
from datetime import datetime, timezone, timedelta
import plotly.express as px
import sys

# --- 1. CẤU HÌNH CHUNG ---
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
        "base_sprint_no": 33,
        "sprint_duration": 11
    },
    "Sprint Team Debuffer": {
        "url": "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592",
        "pics": ['Tài', 'Dương', 'QA', 'Quân', 'Phú', 'Thịnh', 'Đô', 'Tùng', 'Anim', 'Thắng VFX'],
        "platform": "Discord",
        "webhook_url": "https://discord.com/api/webhooks/1469191941261492386/gZ1sx5hnTojIKw5kp5quEotwIldRmCIlhXkZBu9M1Ejs-ZgEUtGsYHlS2CwIWguNbrzc",
        "sprint_start_date": "2026-02-23", 
        "base_sprint_no": 7,
        "sprint_duration": 11
    },
    "Sprint Team Skybow": {
        "url": "https://docs.google.com/spreadsheets/d/157YuS6Sq_Sr6GGl-Ze0Jb0vaIbXZMvlZmU1Yqni-6g4/edit?pli=1&gid=982443592#gid=982443592",
        "pics": ['Đạt', 'Bình', 'QA', 'Lâm', 'Hồng', 'An'],
        "platform": "Telegram",
        "bot_token": "8722643729:AAGSvJtZVMRj-Wi2KwTctXSlJdWfMyVyxi8",
        "chat_id": "-1003176404805",
        "topic_id": 2447,
        "sprint_start_date": "2026-02-24",
        "base_sprint_no": 13,
        "sprint_duration": 13
    }
}

def get_current_sprint_info(config):
    now = datetime.now(VN_TZ).date()
    base_date = datetime.strptime(config['sprint_start_date'], "%Y-%m-%d").date()
    days_diff = (now - base_date).days
    sprint_elapsed = max(0, days_diff // 14)
    current_sprint_no = config['base_sprint_no'] + sprint_elapsed
    current_sprint_start = base_date + timedelta(days=sprint_elapsed * 14)
    duration = config.get('sprint_duration', 11)
    current_sprint_end = current_sprint_start + timedelta(days=duration)
    return current_sprint_no, current_sprint_start, current_sprint_end

# --- 2. XỬ LÝ DỮ LIỆU ---
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

            # --- PHÂN TÍCH HIỆU SUẤT & DỰ BÁO ---
            stats['burn_rate'] = (stats['real_total'] / stats['est_total']).replace([float('inf'), -float('inf')], 0).fillna(0).round(2)
            
            now_dt = datetime.now(VN_TZ)
            s_no, s_start, _ = get_current_sprint_info(config)
            days_passed = max(1, (now_dt.date() - s_start).days)
            stats['velocity'] = (stats['real_total'] / days_passed).round(1)

            def predict_finish(row):
                remaining_h = max(0, row['est_total'] - row['real_total'])
                if row['velocity'] > 0:
                    days_needed = remaining_h / row['velocity']
                    return (now_dt.date() + timedelta(days=int(days_needed))).strftime('%d/%m')
                return "N/A"
            stats['eta'] = stats.apply(predict_finish, axis=1)

            def evaluate_perf(rate):
                if rate == 0: return "⚪ Trống"
                if 0.8 <= rate <= 1.2: return "🟢 Ổn định"
                if rate < 0.8: return "⚡ Nhanh"
                return "🔴 Chậm"
            stats['perf_status'] = stats['burn_rate'].apply(evaluate_perf)

            def get_tasks_detail(pic):
                p_tasks = df_team[df_team['PIC_Clean'] == pic]
                return {
                    'done': p_tasks[p_tasks['State_Clean'].isin(done_states)].groupby('Assigned_US')['Userstory/Todo'].apply(list).to_dict(),
                    'doing': p_tasks[p_tasks['State_Clean'].str.contains('progress')].groupby('Assigned_US')['Userstory/Todo'].apply(list).to_dict(),
                    'pending': p_tasks[p_tasks['State_Clean'] == ''].groupby('Assigned_US')['Userstory/Todo'].apply(list).to_dict(),
                    'pending_count': len(p_tasks[p_tasks['State_Clean'] == ''])
                }

            details = stats['PIC'].apply(get_tasks_detail)
            stats['details'] = details
            stats['pending_count'] = [x['pending_count'] for x in details]
            stats['percent'] = (stats['done_count'] / stats['total'] * 100).fillna(0).round(1)
            return stats
    except Exception as e:
        if "--action" in sys.argv: print(f"❌ Lỗi: {e}")
        else: st.error(f"Lỗi hệ thống: {e}")
    return None

# --- 3. GỬI BÁO CÁO ---
def send_report_logic(project_name, config, pic_stats):
    s_no, _, _ = get_current_sprint_info(config)
    time_str = datetime.now(VN_TZ).strftime('%H:%M')
    msg = f"🤖 **AUTO REPORT ({time_str})**\n🚩 **{project_name.upper()} - SPRINT {int(s_no)}**\n──────────────────────────────\n"
    for _, r in pic_stats.iterrows():
        icon = PIC_ICONS.get(r['PIC'], DEFAULT_ICON)
        eta_str = f"🏁 Xong dự kiến: {r['eta']}" if r['eta'] != "N/A" else "🏁 Chưa đủ dữ liệu dự báo"
        msg += f"{icon} **{r['PIC']}** ({r['perf_status']})\n┣ {eta_str}\n┣ Tiến độ: **{r['percent']}%**\n┣ ✅ Xong: {int(r['done_count'])} | 🚧 Đang: {int(r['doing_count'])}\n┣ ⌚ V: {r['velocity']}h/d | 🔥 Rate: {r['burn_rate']}x\n"
        if r['pending_count'] > 0: msg += f"┗ ⚠️ **Trống State: {int(r['pending_count'])} task**\n"
        else: msg += f"┗ ✅ Đã cập nhật đủ!\n"
        msg += "──────────────────────────────\n"

    try:
        if config['platform'] == "Telegram":
            url = f"https://api.telegram.org/bot{config['bot_token']}/sendMessage"
            requests.post(url, json={"chat_id": config['chat_id'], "text": msg, "parse_mode": "Markdown", "message_thread_id": config.get('topic_id')}, timeout=10)
        elif config['platform'] == "Discord" and "http" in str(config.get('webhook_url')):
            requests.post(config['webhook_url'], json={"content": msg}, timeout=10)
    except Exception as e: print(f"Lỗi gửi tin nhắn: {e}")

# --- 4. GIAO DIỆN WEB ---
if "--action" in sys.argv:
    target = sys.argv[2].lower() if len(sys.argv) > 2 else "all"
    for name, cfg in PROJECTS.items():
        if target == "all" or target in name.lower():
            stats = get_data_and_process(name)
            if stats is not None: send_report_logic(name, cfg, stats)
    sys.exit(0)

else:
    st.set_page_config(page_title="Sprint Dashboard", page_icon="🚀", layout="wide", initial_sidebar_state="collapsed")
    st.sidebar.title("📁 Dự án")
    if 'selected_project' not in st.session_state: st.session_state.selected_project = list(PROJECTS.keys())[0]

    for name in PROJECTS.keys():
        if st.sidebar.button(name, use_container_width=True, type="primary" if st.session_state.selected_project == name else "secondary"):
            st.session_state.selected_project = name
            st.rerun()

    config = PROJECTS[st.session_state.selected_project]
    pic_stats = st.cache_data(ttl=60)(get_data_and_process)(st.session_state.selected_project)

    if pic_stats is not None:
        s_no, s_start, s_end = get_current_sprint_info(config)
        st.title(f"🚀 {st.session_state.selected_project}")
        st.caption(f"📅 Sprint {int(s_no)}: {s_start.strftime('%d/%m')} - {s_end.strftime('%d/%m')}")
        
        if st.sidebar.button("📤 Gửi báo cáo ngay"):
            send_report_logic(st.session_state.selected_project, config, pic_stats)
            st.sidebar.success("Đã gửi thành công!")

        st.divider()
        t_cols = st.columns(4)
        t_cols[0].metric("✅ Tổng Xong", f"{int(pic_stats['done_count'].sum())}")
        t_cols[1].metric("🚧 Tổng Đang làm", f"{int(pic_stats['doing_count'].sum())}")
        t_cols[2].metric("⏳ Tổng Tồn", f"{int(pic_stats['pending_count'].sum())}")
        t_cols[3].metric("⌚ Tổng Real", f"{round(pic_stats['real_total'].sum(), 1)}h")
        st.divider()

        for i in range(0, len(pic_stats), 2):
            cols = st.columns(2)
            for j in range(2):
                idx = i + j
                if idx < len(pic_stats):
                    row = pic_stats.iloc[idx]
                    with cols[j]:
                        icon = PIC_ICONS.get(row['PIC'], DEFAULT_ICON)
                        st.markdown(f"#### {icon} {row['PIC']}")
                        st.progress(min(row['percent']/100, 1.0))
                        
                        p1, p2, p3 = st.columns(3)
                        p1.metric("Hiệu suất", f"{row['burn_rate']}x", row['perf_status'], delta_color="off")
                        p2.metric("Tốc độ", f"{row['velocity']}h/d")
                        p3.metric("Dự kiến Xong", row['eta'])

                        c1, c2, c3 = st.columns(3)
                        c1.caption(f"✅ {int(row['done_count'])}")
                        c2.caption(f"🚧 {int(row['doing_count'])}")
                        c3.caption(f"⏳ {int(row['pending_count'])}") # Đã khôi phục hiển thị Pending
                        
                        with st.expander("Chi tiết Task"):
                            d = row['details']
                            # Hiển thị các task chưa có State
                            if d['pending']:
                                st.error("⏳ **Chưa có State (Cần cập nhật):**")
                                for us, t_list in d['pending'].items():
                                    st.markdown(f"📌 *{us}*")
                                    for t in t_list: st.caption(f"  + {t}")
                            
                            if d['doing']:
                                st.info("🚧 **Đang làm:**")
                                for us, t_list in d['doing'].items():
                                    st.markdown(f"📌 *{us}*")
                                    for t in t_list: st.caption(f"  + {t}")
                    st.divider()

        # Biểu đồ Performance Scatter
        st.write("### 📊 Phân tích năng lực PIC")
        fig_perf = px.scatter(
            pic_stats, x="total", y="velocity", size="real_total", color="perf_status",
            hover_name="PIC", labels={"total": "Số lượng Task", "velocity": "Tốc độ (Giờ/Ngày)"},
            color_discrete_map={"🟢 Ổn định": "#2ecc71", "🔴 Chậm": "#e74c3c", "⚡ Nhanh": "#3498db", "⚪ Trống": "#95a5a6"}
        )
        st.plotly_chart(fig_perf, use_container_width=True)
