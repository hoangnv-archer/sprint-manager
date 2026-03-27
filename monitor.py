import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import pandas as pd
import os
import sys

# 1. THÔNG TIN CẤU HÌNH (Lấy từ GitHub Secrets)
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit#gid=982443592"
SHEET_NAME = "Todo"
ALLOWED_PICS = ["Quân", "Phú", "Tài", "Dương"]

def main():
    try:
        # Kết nối Google Sheets
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # Đảm bảo file credentials.json đã được tạo từ secret ở bước workflow
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        
        # Mở sheet
        spreadsheet = client.open_by_url(SHEET_URL)
        worksheet = spreadsheet.worksheet(SHEET_NAME)
        
        # Lấy dữ liệu
        data = worksheet.get_all_records()
        if not data:
            print("Sheet trống.")
            return

        df = pd.DataFrame(data)

        # 2. LÀM SẠCH TÊN CỘT (Xóa khoảng trắng thừa)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Đảm bảo các cột cần thiết tồn tại
        required_cols = ['PIC', 'State', 'Estimate Dev', 'Userstory/Todo']
        for col in required_cols:
            if col not in df.columns:
                print(f"❌ Lỗi: Thiếu cột '{col}' trên Sheet.")
                sys.exit(1)

        # 3. LỌC TASK: PIC thuộc list + State Done + Estimate > 0
        # Thêm điều kiện: Chỉ báo những task chưa có dấu 'Done' ở cột cuối (cột G chẳng hạn)
        # Ở đây tôi giả định bạn tạo thêm 1 cột tên là 'Notified' ở cuối cùng
        
        mask = (
            df['PIC'].isin(ALLOWED_PICS) & 
            df['State'].str.lower().isin(['done', 'dev done']) &
            (pd.to_numeric(df['Estimate Dev'], errors='coerce') > 0)
        )
        
        new_tasks = df[mask]
        
        if new_tasks.empty:
            print("Không có task nào mới hoàn thành.")
            return

        print(f"Tìm thấy {len(new_tasks)} task tiềm năng...")

        for index, row in new_tasks.iterrows():
            # Logic báo tin nhắn đơn giản
            pic_name = row['PIC']
            task_name = row['Userstory/Todo']
            
            msg = {
                "username": "Bot Thông Báo Task",
                "content": f"✅ **{pic_name}** vừa xong task: *{task_name}*"
            }
            
            response = requests.post(WEBHOOK_URL, json=msg)
            
            if response.status_code == 204 or response.status_code == 200:
                print(f"🔥 Đã báo task: {task_name}")
            else:
                print(f"❌ Lỗi Discord: {response.status_code}")

    except Exception as e:
        print(f"❌ Lỗi hệ thống: {e}")
        sys.exit(1) # Báo lỗi để GitHub Actions hiển thị đỏ

if __name__ == "__main__":
    main()
