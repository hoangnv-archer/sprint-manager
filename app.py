import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import requests
import io

st.set_page_config(page_title="Sprint Workload Analyzer", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
URL = "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592"

try:
    # 1. Đọc dữ liệu
    raw_df = conn.read(spreadsheet=URL, header=None)
    header_idx = None
    for i, row in raw_df.iterrows():
        if "Userstory/Todo" in row.values:
            header_idx = i
            break
            
    if header_idx is not None:
        df = conn.read(spreadsheet=URL, skiprows=header_idx)
        df.columns = [str(c).strip() for c in df.columns]
        
        # 2. Xử lý số liệu và chuẩn hóa State
        for col in ['Estimate Dev', 'Real']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        
        # Gán nhãn "None" cho các ô State trống (để đếm task chưa làm)
        df['State'] = df['State'].fillna('None').replace('', 'None')

        # 3. Lọc Team
        valid_pics = ['Tài', 'Dương', 'QA', 'Quân', 'Phú', 'Thịnh', 'Đô', 'Tùng', 'Anim', 'Thắng VFX']
        df_team = df[df['PIC'].isin(valid_pics)].copy()

        st.title("🚀 Phân Tích Khối Lượng & Tiến Độ Team")

        # --- TÍNH TOÁN LOGIC MỚI ---
        # A. Tính số lượng Task để tính % Tiến độ
        task_counts = df_team.groupby('PIC').agg(
            total_tasks=('Userstory/Todo', 'count'),
            done_tasks=('State', lambda x: (x.str.strip().str.lower() == 'done').sum())
        ).reset_index()
        task_counts['Progress_Task_Based'] = (task_counts['done_tasks'] / task_counts['total_tasks'] * 100).fillna(0).round(1)

        # B. Tính tổng giờ Pending (State == "None")
        pending_work = df_team[df_team['State'] == 'None'].groupby('PIC')['Estimate Dev'].sum().reset_index()
        pending_work.columns = ['PIC', 'Pending_Est']

        # C. Tính tổng giờ Active (State != "None")
        active_work = df_team[df_team['State'] != 'None'].groupby('PIC').agg({
            'Estimate Dev': 'sum',
            'Real': 'sum'
        }).reset_index()
        active_work.columns = ['PIC', 'Active_Est', 'Active_Real']

        # D. Gộp tất cả dữ liệu
        pic_stats = pd.DataFrame({'PIC': valid_pics})
        pic_stats = pic_stats.merge(active_work, on='PIC', how='left')
        pic_stats = pic_stats.merge(pending_work, on='PIC', how='left')
        pic_stats = pic_stats.merge(task_counts, on='PIC', how='left').fillna(0)

        # Tổng Estimate = Giờ của task đang làm + task chưa có state
        pic_stats['Total_Estimate'] = pic_stats['Active_Est'] + pic_stats['Pending_Est']

        # --- GIAO DIỆN METRICS ---
        st.subheader("👤 Tiến độ theo số lượng Task & Khối lượng giờ")
        
        # Chia cột dựa trên số lượng thành viên (tối đa 5 cột mỗi hàng để tránh bị nhỏ quá)
        rows_needed = (len(valid_pics) // 5) + (1 if len(valid_pics) % 5 > 0 else 0)
        for r in range(rows_needed):
            current_batch = valid_pics[r*5 : (r+1)*5]
            cols = st.columns(len(current_batch))
            for i, pic_name in enumerate(current_batch):
                row = pic_stats[pic_stats['PIC'] == pic_name].iloc[0]
                with cols[i]:
                    st.markdown(f"### **{row['PIC']}**")
                    # Hiển thị % tiến độ dựa trên số task Done / Tổng task
                    st.metric("Tiến độ Task", f"{row['Progress_Task_Based']}%", 
                              delta=f"{int(row['done_tasks'])}/{int(row['total_tasks'])} Done")
                    
                    st.write(f"✅ Thời gian thực tế đã làm: **{row['Active_Real']}h**")
                    st.write(f"⏳ Thời gian estimate còn tồn đọng: **{row['Pending_Est']}h**")
                    
                    # Thanh progress trực quan theo số lượng Task
                    st.progress(min(row['Progress_Task_Based']/100, 1.0))

        st.divider()

        # --- BIỂU ĐỒ PHÂN TÍCH ---
        st.subheader("📊 Biểu đồ so sánh: Thực tế vs Kế hoạch vs Tồn đọng")

        chart_data = pic_stats[['PIC', 'Active_Real', 'Total_Estimate', 'Pending_Est']].copy()
        chart_data.columns = ['PIC', 'Thực tế (Real-time)', 'Tổng dự tính (Kế hoạch)', 'Dự kiến đang chờ (None)']

        fig_df = chart_data.melt(id_vars='PIC', var_name='Trạng thái', value_name='Số giờ')

        if not fig_df.empty:
            fig = px.bar(
                fig_df, x='PIC', y='Số giờ', color='Trạng thái', 
                barmode='group', text_auto='.1f',
                color_discrete_map={
                    'Thực tế (Real-time)': '#00C853',
                    'Tổng dự tính (Kế hoạch)': '#636EFA',
                    'Dự kiến đang chờ (None)': '#FFD600'
                }
            )
            fig.update_layout(xaxis_title="Thành viên Team", yaxis_title="Số giờ (h)", height=500)
            st.plotly_chart(fig, use_container_width=True)

        # 4. Bảng chi tiết
        st.subheader("📋 Danh sách Task chi tiết")
        def style_rows(row):
            return ['background-color: #f5f5f5; color: #9e9e9e' if row.State == 'None' else '' for _ in row]

        st.dataframe(df_team[['Userstory/Todo', 'State', 'Estimate Dev', 'Real', 'PIC']].style.apply(style_rows, axis=1), 
                     use_container_width=True)
              
    else:
        st.error("Không tìm thấy tiêu đề 'Userstory/Todo'.")

except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")


# --- TÍNH NĂNG GỬI BÁO CÁO CHI TIẾT QUA DISCORD (TEXT) ---
st.sidebar.divider()
st.sidebar.subheader("📢 Gửi báo cáo Text")
webhook_url = st.sidebar.text_input("Dán Discord Webhook URL:", type="password", key="discord_text_url")

if st.sidebar.button("📤 Gửi báo cáo đầy đủ vào Discord"):
    if webhook_url:
        try:
            # 1. Tính toán các chỉ số tổng quát
            total_tasks = len(df_team)
            done_tasks = len(df_team[df_team['State'].str.lower() == 'done'])
            progress_total = (done_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            # 2. Xây dựng nội dung tin nhắn (Dùng Markdown Discord)
            message = "🚀 **SPRINT PERFORMANCE REPORT** 🚀\n"
            message += f"📊 **Tiến độ chung:** `{progress_total:.1f}%` ({done_tasks}/{total_tasks} Task Done)\n"
            message += "━━━━━━━━━━━━━━━━━━━━━\n"
            
            # 3. Duyệt qua từng thành viên trong pic_stats để lấy số liệu chi tiết
            for _, row in pic_stats.iterrows():
                # Chọn icon dựa trên tiến độ task
                icon = "🟢" if row['Progress_Task_Based'] >= 80 else "🟡" if row['Progress_Task_Based'] >= 50 else "🔴"
                
                message += f"{icon} **{row['PIC']}**\n"
                message += f"   • Tiến độ: `{row['Progress_Task_Based']}%` (Task)\n"
                message += f"   • Đã làm: `{row['Active_Real']:.1f}h` | Chờ: `{row['Pending_Est']:.1f}h`\n"
                message += f"   • Tổng Est: `{row['Total_Estimate']:.1f}h` \n\n"
            
            message += "━━━━━━━━━━━━━━━━━━━━━\n"
            message += "💡 *Cập nhật lúc:* " + pd.Timestamp.now().strftime('%H:%M - %d/%m/%Y') + "\n"
            message += "🔗 [Xem Dashboard chi tiết tại đây](https://your-streamlit-link.streamlit.app/)"

            # 4. Gửi yêu cầu đến Discord
            payload = {"content": message}
            response = requests.post(webhook_url, json=payload)
            
            if response.status_code in [200, 204]:
                st.sidebar.success("✅ Đã gửi báo cáo thành công!")
            else:
                st.sidebar.error(f"❌ Lỗi: {response.status_code}")
                
        except Exception as e:
            st.sidebar.error(f"❌ Lỗi khi xử lý dữ liệu: {e}")
    else:
        st.sidebar.warning("⚠️ Vui lòng nhập Webhook URL!")
