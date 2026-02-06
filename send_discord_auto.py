import requests
import pandas as pd
import os

# Lấy thông tin từ GitHub Secrets
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
SHEET_URL = os.environ.get("GSHEETS_URL")

def send_report():
    try:
        # Chuyển đổi link Sheet sang định dạng xuất CSV để đọc trực tiếp bằng Pandas
        # Cách này nhanh và ổn định hơn khi chạy tự động
        csv_url = SHEET_URL.replace('/edit?pli=1&', '/export?format=csv&')
        
        # Đọc dữ liệu (Bỏ qua các hàng trống đầu tiên cho đến khi gặp 'Userstory/Todo')
        df_raw = pd.read_csv(csv_url, header=None)
        header_row = df_raw[df_raw.eq("Userstory/Todo").any(axis=1)].index[0]
        df = pd.read_csv(csv_url, skiprows=header_row + 1)
        
        # Làm sạch dữ liệu
        df.columns = [str(c).strip() for c in df.columns]
        df['State_Clean'] = df['State'].fillna('None').replace('', 'None').str.strip().str.lower()
        
        valid_pics = ['Tài', 'Dương', 'QA', 'Quân', 'Phú', 'Thịnh', 'Đô', 'Tùng', 'Anim', 'Thắng VFX']
        df_team = df[df['PIC'].isin(valid_pics)].copy()

        # Tính toán
        pic_stats = df_team.groupby('PIC').agg(
            total=('Userstory/Todo', 'count'),
            done=('State_Clean', lambda x: x.isin(['done', 'cancel']).sum()),
            ip=('State_Clean', lambda x: (x == 'in progress').sum()),
            none=('State_Clean', lambda x: (x == 'none').sum())
        ).reset_index()

        # Soạn tin nhắn
        msg = "⏰ **BÁO CÁO TỰ ĐỘNG (8:30 AM)** ☀️\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━\n"
        for _, r in pic_stats.iterrows():
            progress = (r['done'] / r['total'] * 100) if r['total'] > 0 else 0
            icon = "🟢" if progress >= 80 else "🟡"
            msg += f"{icon} **{r['PIC']}**: `{progress:.1f}%` | Xong: `{int(r['done'])}` | IP: `{int(r['ip'])}` | None: `{int(r['none'])}` \n"
        
        # Gửi sang Discord
        response = requests.post(WEBHOOK_URL, json={"content": msg})
        if response.status_code in [200, 204]:
            print("✅ Gửi thành công!")
        else:
            print(f"❌ Lỗi Discord: {response.status_code}")

    except Exception as e:
        print(f"❌ Lỗi xử lý: {e}")

if __name__ == "__main__":
    send_report()
