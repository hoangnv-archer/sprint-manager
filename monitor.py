import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import time
import pandas as pd

# 1. THÔNG TIN CẤU HÌNH
import os
# Lấy URL từ Secret của GitHub thay vì dán trực tiếp
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?gid=982443592#gid=982443592"
SHEET_NAME = "Todo" # Ví dụ: "Sheet1" hoặc "Sprint 2026"
ALLOWED_PICS = ["Quân", "Phú", "Tài", "Dương"] # Những người bạn muốn theo dõi

# Bộ nhớ tạm để tránh báo trùng
notified_tasks = set()

def main():
    # Kết nối Google Sheets
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    
    print("🚀 Bot Python đang quét Sheet...")

    while True:
        try:
            # Mở sheet và lấy toàn bộ dữ liệu
            sheet = client.open_by_url(SHEET_URL).worksheet(SHEET_NAME)
            data = sheet.get_all_records()
            df = pd.DataFrame(data)

            # Lọc Task: PIC trong list + State là Done/Dev Done + Estimate > 0
            # Lưu ý: Tên cột 'PIC', 'State', 'Estimate Dev' phải đúng 100% như trên Sheet
            mask = (
                df['PIC'].isin(ALLOWED_PICS) & 
                df['State'].str.lower().isin(['done', 'dev done']) &
                (pd.to_numeric(df['Estimate Dev'], errors='coerce') > 0)
            )
            
            new_tasks = df[mask]

            for _, row in new_tasks.iterrows():
                task_id = f"{row['Userstory/Todo']}_{row['PIC']}"
                
                if task_id not in notified_tasks:
                    # Gửi tin nhắn sang Discord
                    msg = {
                        "content": f"✅ **{row['PIC']}** vừa xong task: *{row['Userstory/Todo']}*"
                    }
                    requests.post(WEBHOOK_URL, json=msg)
                    
                    notified_tasks.add(task_id)
                    print(f"🔥 Đã báo task: {row['Userstory/Todo']}")

        except Exception as e:
            print(f"🔄 Đang chờ cập nhật hoặc lỗi: {e}")
        
        time.sleep(20) # Đợi 20 giây rồi quét tiếp

if __name__ == "__main__":
    main()
