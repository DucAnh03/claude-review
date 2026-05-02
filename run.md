python d:/aaaaaaaaaaaaaaaaaaaaaaaaa/claude_flow_review/review_core.py --repo tool_monitor --commit b58927b --task "Đọc dữ liệu chi tiêu từ file CSV, hoặc dùng demo data có sẵn nếu không truyền file. Validate từng dòng: date đúng format YYYY-MM-DD, category không rỗng, amount là số dương. Bỏ qua dòng lỗi nhưng vẫn gom lỗi lại và in ra cuối chương trình. Tạo báo cáo gồm tổng chi, chi theo danh mục, chi theo ngày, và khoản chi lớn nhất."

Bước 1: Script core (Python) - Nhận commit hash + repo name - cd đến repo dir - git checkout commit - Gọi claude --print với context - Parse output → tạo file .md
↓
Bước 2: SQLite DB nhỏ - Lưu mapping: repo_name → local_dir - Lưu history review
↓  
Bước 3: Slack Bot - Nhận message từ channel - Parse format: review [repo] [commit] [desc] - Gọi script Bước 1 - Upload file .md + summary lên Slack
↓
Bước 4: Job Queue - Xử lý concurrent requests

pip install slack-bolt python-dotenv

cd "D:\aaaaaaaaaaaaaaaaaaaaaaaaa\claude_flow_review\review-ui"
npm run dev

cd "D:\aaaaaaaaaaaaaaaaaaaaaaaaa\claude_flow_review"
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
