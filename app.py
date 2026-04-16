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
    "Thịnh": "📈", "Đô": "🏰", "Thành": "🏰", "Anim": "🎬",
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
        "pics": ['Tài', 'Dương', 'QA', 'Quân', 'Phú', 'Thịnh', 'Đô', 'Thành', 'Anim', 'Thắng VFX'],
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

# --- 1.1 HÀM LƯU TRỮ DỮ LIỆU CHI TIẾT PIC ---
def archive_sprint_data(config, stats):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        s_no, s_start, s_end = get_current_sprint_info(config)
        new_entries_list = []
        for _, row in stats.iterrows():
            new_entries_list.append({
                "Sprint": int(s_no),
                "PIC": row['PIC'],
                "Done_Rate": f"{row['percent']}%",
                "Est_Sprint": round(row['est_sprint'], 1),
                "Real_Sprint": round(row['real_sprint'], 1),
                "Real_Extra": round(row['real_extra'], 1),
                "Tasks_Done": int(row['done_count']),
                "Tasks_Total": int(row['total']),
                "Updated_At": datetime.now(VN_TZ).strftime('%H:%M:%S %d/%m/%Y')
            })
        new_entries_df = pd.DataFrame(new_entries_list)
        try:
            history_df = conn.read(spreadsheet=config['url'], worksheet="History", ttl=0)
            if not history_df.empty:
                history_df['Sprint'] = pd.to_numeric(history_df['Sprint'], errors='coerce')
                history_df = history_df[history_df['Sprint'] != int(s_no)]
                updated_history = pd.concat([history_df, new_entries_df], ignore_index=True)
            else:
                updated_history = new_entries_df
        except:
            updated_history = new_entries_df
        conn.update(spreadsheet=config['url'], worksheet="History", data=updated_history)
        return True
    except Exception as e:
        st.error(f"Lỗi lưu trữ: {e}")
        return False

# --- 1.2 HÀM NHẮC NHỞ REAL-TIME RIÊNG BIỆT (MỚI) ---
def send_realtime_reminder(project_name, config, missing_df):
    if missing_df.empty:
        st.sidebar.success("✅ Mọi người đã điền đủ giờ!")
        return
    
    time_now = datetime.now(VN_TZ).strftime('%H:%M')
    msg = f"🔔 **NHẮC NHỞ CẬP NHẬT GIỜ REAL ({time_now})**\n"
    msg += f"🚩 Dự án: {project_name}\n"
    msg += "──────────────────────────────\n"
    
    for pic in missing_df['PIC_Clean'].unique():
        pic_tasks = missing_df[missing_df['PIC_Clean'] == pic]
        icon = PIC_ICONS.get(pic, DEFAULT_ICON)
        
        # Chỉ hiển thị tên in đậm, không dùng ID/Tag
        msg += f"{icon} **{pic}** ơi, điền giờ Real cho:\n"
        for _, t in pic_tasks.iterrows():
            msg += f"  • _{t['Userstory/Todo'][:40]}..._ ({t['Estimate Dev']}h)\n"
            
    msg += "──────────────────────────────\n"
    msg += "👉 *Vui lòng điền Real sau 5p hoàn thành task!*"
    try:
        if config['platform'] == "Telegram":
            url = f"https://api.telegram.org/bot{config['bot_token']}/sendMessage"
            requests.post(url, json={"chat_id": config['chat_id'], "text": msg, "parse_mode": "Markdown", "message_thread_id": config.get('topic_id')}, timeout=10)
        elif config['platform'] == "Discord":
            requests.post(config['webhook_url'], json={"content": msg}, timeout=10)
        st.sidebar.warning("🚀 Đã bắn tin nhắc nhở riêng!")
    except Exception as e:
        st.sidebar.error(f"Lỗi: {e}")

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
            if not processed_data: return None, None
            df_final = pd.DataFrame(processed_data)
            df_final['PIC_Clean'] = df_final['PIC'].fillna('').astype(str).str.strip()
            df_final['State_Clean'] = df_final['State'].fillna('').astype(str).str.strip().str.lower()
            for col in ['Estimate Dev', 'Real']:
                if col in df_final.columns:
                    df_final[col] = pd.to_numeric(df_final[col].astype(str).str.replace('h',''), errors='coerce').fillna(0)
            df_team = df_final[df_final['PIC_Clean'].isin(config['pics'])].copy()
            done_states = ['done', 'cancel', 'dev done']
            df_team['Is_Extra'] = df_team['Estimate Dev'] <= 0
            stats = df_team.groupby('PIC_Clean').agg(
                total=('Userstory/Todo', 'count'),
                done_count=('State_Clean', lambda x: x.isin(done_states).sum()),
                doing_count=('State_Clean', lambda x: x.str.contains('progress').sum()),
                est_sprint=('Estimate Dev', 'sum'),
                real_sprint=('Real', lambda x: x[df_team.loc[x.index, 'Is_Extra'] == False].sum()),
                real_extra=('Real', lambda x: x[df_team.loc[x.index, 'Is_Extra'] == True].sum()),
                real_total=('Real', 'sum')
            ).reset_index()
            stats.rename(columns={'PIC_Clean': 'PIC'}, inplace=True)
            def get_structured_tasks(pic):
                p_df = df_team[df_team['PIC_Clean'] == pic]
                def group_tasks(subset):
                    if subset.empty: return {}
                    return subset.groupby('Assigned_US')[['Userstory/Todo', 'State', 'Real', 'Estimate Dev']].apply(lambda x: x.to_dict('records')).to_dict()
                return {
                    'pending_grouped': group_tasks(p_df[p_df['State_Clean'] == '']),
                    'sprint_grouped': group_tasks(p_df[(p_df['Is_Extra'] == False) & (p_df['State_Clean'] != '')]),
                    'extra_grouped': group_tasks(p_df[(p_df['Is_Extra'] == True) & (p_df['State_Clean'] != '')]),
                    'pending_count': len(p_df[p_df['State_Clean'] == ''])
                }
            details = stats['PIC'].apply(get_structured_tasks)
            stats['details'] = details
            stats['pending_count'] = stats['details'].apply(lambda x: x['pending_count'])
            stats['percent'] = (stats['done_count'] / stats['total'] * 100).fillna(0).round(1)
            return stats, df_team
    except Exception as e:
        st.error(f"Lỗi: {e}")
    return None, None

# (Hàm send_report_logic giữ nguyên như cũ)
def send_report_logic(project_name, config, pic_stats):
    s_no, _, _ = get_current_sprint_info(config)
    time_str = datetime.now(VN_TZ).strftime('%H:%M')
    msg = f"🤖 **AUTO REPORT ({time_str})**\n🚩 **{project_name.upper()} - SPRINT {int(s_no)}**\n──────────────────────────────\n"
    for _, r in pic_stats.iterrows():
        icon = PIC_ICONS.get(r['PIC'], DEFAULT_ICON)
        msg += f"{icon} **{r['PIC']}** ({r['percent']}%)\n"
        msg += f"┣ 📅 Sprint: {round(r['real_sprint'],1)}h/{round(r['est_sprint'],1)}h\n"
        if r['real_extra'] > 0: msg += f"┣ 🆘 Ngoài Sprint: {round(r['real_extra'],1)}h\n"
        stt = f"┗ ✅: {int(r['done_count'])} | 🚧: {int(r['doing_count'])}"
        if r['pending_count'] > 0: stt += f" | ⚠️ Trống: {int(r['pending_count'])}"
        msg += stt + "\n──────────────────────────────\n"
    try:
        if config['platform'] == "Telegram":
            url = f"https://api.telegram.org/bot{config['bot_token']}/sendMessage"
            requests.post(url, json={"chat_id": config['chat_id'], "text": msg, "parse_mode": "Markdown", "message_thread_id": config.get('topic_id')}, timeout=10)
        elif config['platform'] == "Discord":
            requests.post(config['webhook_url'], json={"content": msg}, timeout=10)
    except Exception as e: st.sidebar.error(f"Lỗi: {e}")

# --- 4. GIAO DIỆN WEB ---
st.set_page_config(page_title="Sprint Dashboard", page_icon="🚀", layout="wide")
st.sidebar.title("📁 Projects")
if 'selected_project' not in st.session_state: st.session_state.selected_project = list(PROJECTS.keys())[0]

for name in PROJECTS.keys():
    if st.sidebar.button(name, use_container_width=True, type="primary" if st.session_state.selected_project == name else "secondary"):
        st.session_state.selected_project = name
        st.rerun()

config = PROJECTS[st.session_state.selected_project]
pic_stats, df_team = get_data_and_process(st.session_state.selected_project)

if pic_stats is not None:
    # 1. Lấy dữ liệu thô để lọc task thiếu Real
    # Logic: State là done/dev done VÀ Estimate > 0 VÀ Real chưa điền
    done_states_reminder = ['done', 'dev done']
    missing_real_df = df_team[
        (df_team['State_Clean'].isin(done_states_reminder)) & 
        (df_team['Estimate Dev'] > 0) & 
        ((df_team['Real'] == 0) | (df_team['Real'].isna()))
    ].copy()

    st.sidebar.divider()
    st.sidebar.subheader("🎯 Kiểm soát Real-time")
    
    if not missing_real_df.empty:
        st.sidebar.error(f"⚠️ {len(missing_real_df)} task chưa điền Real!")
        if st.sidebar.button("🔔 Bắn tin nhắc nhở", use_container_width=True, type="primary"):
            send_realtime_reminder(st.session_state.selected_project, config, missing_real_df)
        
        with st.sidebar.expander("Danh sách chi tiết"):
            for _, r in missing_real_df.iterrows():
                st.caption(f"• **{r['PIC_Clean']}**: {r['Userstory/Todo'][:25]}...")
    else:
        st.sidebar.success("💎 Tuyệt vời! Đã điền đủ giờ.")

    # --- SIDEBAR: 📤 GỬI REPORT ---
    st.sidebar.divider()
    if st.sidebar.button("📤 Gửi báo cáo Bot", use_container_width=True):
        send_report_logic(st.session_state.selected_project, config, pic_stats)
        st.sidebar.success("Đã gửi báo cáo Bot!")
    if st.sidebar.button("💾 Lưu trữ Sprint chi tiết", use_container_width=True):
        if archive_sprint_data(config, pic_stats):
            st.sidebar.success(f"Đã lưu chi tiết Sprint {int(s_no)}!")

    # (Phần hiển thị bảng biểu, metrics phía dưới giữ nguyên)
    st.divider()
    t_cols = st.columns(4)
    t_cols[0].metric("📅 Tổng Sprint Est", f"{round(pic_stats['est_sprint'].sum(),1)}h")
    t_cols[1].metric("⌚ Thực tế Sprint", f"{round(pic_stats['real_sprint'].sum(),1)}h")
    t_cols[2].metric("🆘 Ngoài Sprint", f"{round(pic_stats['real_extra'].sum(),1)}h")
    t_cols[3].metric("⏳ Tổng Trống State", f"{int(pic_stats['pending_count'].sum())}")
    
    # ... các phần hiển thị Lịch sử và chi tiết PIC như trước ...
    
    # --- PHẦN HIỂN THỊ LỊCH SỬ ---
    with st.expander("📜 Lịch sử hiệu suất chi tiết (Worksheet: History)"):
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            history_df = conn.read(spreadsheet=config['url'], worksheet="History", ttl=0)
            if not history_df.empty:
                # Lọc nhanh theo PIC
                all_pics = ["Tất cả"] + sorted(history_df['PIC'].unique().tolist())
                sel_pic = st.selectbox("Lọc theo thành viên:", all_pics)
                
                plot_df = history_df if sel_pic == "Tất cả" else history_df[history_df['PIC'] == sel_pic]
                
                fig_hist = px.line(plot_df, x="Sprint", y="Real_Sprint", color="PIC",
                                   title=f"Xu hướng giờ làm thực tế: {sel_pic}", markers=True)
                st.plotly_chart(fig_hist, use_container_width=True)
                
                st.dataframe(plot_df.sort_values(["Sprint", "PIC"], ascending=[False, True]), use_container_width=True)
            else:
                st.info("Chưa có dữ liệu lịch sử.")
        except:
            st.warning("Vui lòng tạo worksheet 'History' với các cột: Sprint, PIC, Done_Rate, Est_Sprint, Real_Sprint, Real_Extra, Tasks_Done, Tasks_Total, Updated_At")

    st.divider()

    # (Vòng lặp hiển thị chi tiết PIC hiện tại giữ nguyên)
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
                    
                    m1, m2 = st.columns(2)
                    m1.metric("Sprint Real/Est", f"{round(row['real_sprint'],1)}h/{round(row['est_sprint'],1)}h")
                    m2.metric("Ngoài Sprint", f"{round(row['real_extra'],1)}h")
                    
                    with st.expander("🔍 Chi tiết theo User Story"):
                        d = row['details']
                        if d['pending_grouped']:
                            st.error(f"⚠️ **Chưa cập nhật State ({row['pending_count']} task):**")
                            for us, tasks in d['pending_grouped'].items():
                                st.markdown(f"**📌 {us}**")
                                for t in tasks: st.caption(f"└ {t['Userstory/Todo']}")
                        
                        if d['sprint_grouped']:
                            st.info("📅 **Sprint Tasks:**")
                            for us, tasks in d['sprint_grouped'].items():
                                st.markdown(f"**📌 {us}**")
                                for t in tasks: st.caption(f"└ {t['Userstory/Todo']} (`{t['State']}` | {t['Real']}h/{t['Estimate Dev']}h)")
                        
                        if d['extra_grouped']:
                            st.warning("🆘 **Ngoài Sprint:**")
                            for us, tasks in d['extra_grouped'].items():
                                st.markdown(f"**📌 {us}**")
                                for t in tasks: st.caption(f"└ {t['Userstory/Todo']} (`{t['State']}` | {t['Real']}h)")
                st.divider()

    st.write("### 📊 Bản đồ phân bổ hiện tại")
    fig = px.scatter(pic_stats, x="total", y="real_total", size="real_total", color="PIC",
                     hover_name="PIC", labels={"total": "Tổng số Task", "real_total": "Tổng giờ thực tế (h)"})
    st.plotly_chart(fig, use_container_width=True)

# --- 5. LOGIC CHẠY TỰ ĐỘNG (DÀNH CHO GITHUB ACTIONS) ---
if __name__ == "__main__":
    # Kiểm tra xem có đang chạy qua Terminal/GitHub Actions với tham số không
    if len(sys.argv) > 1 and sys.argv[1] == '--action':
        action_name = sys.argv[2]
        print(f"🚀 Bắt đầu chạy Auto Report ngầm cho: {action_name}")
        
        # Xác định dự án dựa trên tham số truyền vào
        project_key = None
        if action_name == 'skybow':
            project_key = "Sprint Team Skybow"
        elif action_name == 'infinity':
            project_key = "Sprint Team Infinity"
        elif action_name == 'debuffer':
            project_key = "Sprint Team Debuffer"
            
        if not project_key:
            print("❌ Lỗi: Không tìm thấy cấu hình cho action này.")
            sys.exit(1)
            
        config = PROJECTS[project_key]
        pic_stats, df_team = get_data_and_process(project_key)
        
        if pic_stats is not None:
            # Tự động gửi báo cáo mà không cần bấm nút
            send_report_logic(project_key, config, pic_stats)
            print(f"✅ Đã gửi báo cáo thành công cho {project_key}!")
        else:
            print("❌ Lỗi: Không lấy được dữ liệu từ Google Sheets.")
            
        # Chạy xong thì thoát luôn, không render giao diện Web nữa
        sys.exit(0)
