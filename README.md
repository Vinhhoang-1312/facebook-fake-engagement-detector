# Facebook Fake Engagement Detector

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Tests](https://img.shields.io/badge/tests-16%20passed-2ea44f)
![Coverage](https://img.shields.io/badge/coverage-86.58%25-2ea44f)
![License](https://img.shields.io/badge/license-MIT-blue)

Ứng dụng Python chạy local để thu thập dữ liệu **Facebook Page mà bạn có quyền quản lý**
qua Meta Graph API, lưu snapshot, phát hiện engagement bất thường và giải thích bằng bằng
chứng. Điểm số là **anomaly risk**, không phải phần trăm tài khoản giả và không phải kết luận
gian lận.

## Quick start (offline, không cần token)

```powershell
python -m pip install -e .
python -m fake_like_detector.cli demo
python -m fake_like_detector.cli analyze
python -m streamlit run src/fake_like_detector/dashboard/app.py
```

Nếu máy không cho pip ghi vào Python hệ thống, dùng môi trường local:

```powershell
python -m venv .venv --system-site-packages
.\.venv\Scripts\python.exe -m pip install -e . --no-deps --no-build-isolation
.\.venv\Scripts\python.exe -m fake_like_detector.cli demo
```

## Workflow

```powershell
# Tạo database/schema
python -m fake_like_detector.cli init-db

# Thu thập một snapshot (mock hoặc Meta theo .env)
python -m fake_like_detector.cli collect

# Chạy detector và in evidence-level result
python -m fake_like_detector.cli analyze

# Kiểm tra field Meta được cấp quyền trước khi collect live
python -m fake_like_detector.cli audit-fields
```

Các lớp chính:

- `PageDataProvider`: adapter dữ liệu; có `MockProvider` và `MetaGraphProvider`.
- `Repository`: SQLite idempotent; cùng post/timestamp không bị ghi trùng.
- Feature pipeline: baseline bằng median/MAD, tốc độ tăng và quality ratio.
- Detector + fusion: evidence có mã, coverage, counter-evidence và confidence.
- Dashboard: Overview, Posts, Post Detail, Data Health và Review Queue.

## Live Meta mode

Sao chép `.env.example` thành `.env`, đặt `FLED_PROVIDER=meta`, rồi cung cấp Page ID,
Page access token và Graph API version. Token chỉ nằm trong `.env`; không commit, không gửi
vào log. Chạy `python -m fake_like_detector.cli audit-fields` trước để biết tài khoản/app hiện
được Meta cho phép đọc field nào.

Ứng dụng không crawl HTML, không lấy cookie trình duyệt, không gọi private GraphQL endpoint,
và không cố vượt cơ chế chống bot của Facebook.

## Cách đọc kết quả

- `normal`: không thấy anomaly đáng kể trong dữ liệu hiện có.
- `watch`: có tín hiệu yếu; nên tiếp tục thu thập.
- `suspicious` / `highly_suspicious`: nhiều evidence bất thường, cần người kiểm tra.
- `insufficient_data`: baseline, số snapshot hoặc field coverage chưa đủ.

Không thể kết luận chính xác “bao nhiêu like là từ account fake” chỉ từ aggregate counts.
Muốn nghiên cứu coordination ở account level cần dữ liệu actor hợp pháp, privacy review và một
pipeline graph riêng; MVP này cố ý không giả lập dữ liệu đó.

## Token safety và vận hành

- Không commit `.env`; xoay/thu hồi token trong Meta nếu nghi bị lộ.
- Chỉ dùng Page access token và quyền mà Meta đã duyệt cho Page bạn quản lý.
- Thu thập nhiều snapshot theo lịch (ví dụ mỗi 15–60 phút) để temporal detector có ý nghĩa.
- Meta có thể thay đổi version/field/quyền; chạy `audit-fields` sau khi đổi token hoặc API version.
- Test không gọi mạng và không chứa thông tin cá nhân thật.
