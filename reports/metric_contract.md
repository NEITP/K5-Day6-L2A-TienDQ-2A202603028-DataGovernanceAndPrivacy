# T02 · Quy ước metric — Raw QC Triage

Tài liệu này ghi lại quy ước đánh giá của thí nghiệm. Bộ dữ liệu học viên không được cung cấp nhãn ground truth (GT), vì vậy các metric cần GT được ghi là **N/A** và không được dùng để tinh chỉnh thuật toán.

| Hạng mục | Quy ước đã chốt |
|---|---|
| Track | T02 · Raw QC Triage (ưu tiên ảnh cần kiểm tra chất lượng) |
| Metric chính theo đặc tả | Defect Recall@B (độ bao phủ ảnh lỗi trong B ảnh được ưu tiên) |
| Chiều đánh giá | Cao hơn là tốt hơn |
| Đơn vị | Ảnh |
| Công thức metric chính | TP / (TP + FN); TP là số ảnh có lỗi GT trong top B; mẫu số là tổng số ảnh lỗi GT trong split eval |
| Metric phụ theo đặc tả | Precision@B = số ảnh có lỗi GT trong top B / B |
| Ghép dự đoán với nhãn | Ghép chính xác theo `image_id`; evaluator lọc nhãn có `split=eval` |
| Tập ứng viên | 40 ảnh eval trong fixture cố định gồm 96 ảnh; chia split theo nhóm cảnh |
| Ngân sách review | B=20 |
| Seed | 42 |
| Chính sách điểm PoC | Điểm bất thường có trọng số cố định: blur 0.40, dark 0.25, glare 0.20, compression 0.15; tham chiếu đặc trưng robust tính từ dev theo camera/light, có fallback |
| Chính sách baseline | Một tín hiệu độ nét Laplacian toàn ảnh, xếp ảnh có phương sai thấp lên trước (`score = -laplacian_variance`); không khớp ngưỡng bằng nhãn |
| Split đánh giá | `eval`; tuyệt đối không dùng để hiệu chỉnh tham chiếu, trọng số hoặc chính sách |
| Báo cáo lỗi | Ảnh lỗi bị bỏ sót là ảnh lỗi GT ngoài top 20; báo động giả là ảnh không lỗi GT nằm trong top 20; cả hai cần nhãn GT |
| Phân lát | `light` (day/dusk/night) và `camera_id` (cam_A/cam_B) |
| Bất định | Thông thường cần báo số đếm và mẫu số; nếu được yêu cầu, bootstrap trên ảnh eval với dự đoán cố định và nêu rõ N nhỏ. Không thể tính các khoảng này từ bộ học viên vì không có GT. |
| Trạng thái metric cho bản nộp | Defect Recall@20: N/A; Precision@20: N/A. Đây là giới hạn của dữ liệu được phát cho học viên, không phải metric đang chờ được bổ sung. |
| Ghi nhận protocol | 2026-11-15 · Chủ sở hữu/người review: Đinh Quốc Tiến; mã nguồn và cấu hình được quản lý trong Git của dự án. |

Giữ nguyên ngân sách, tập ứng viên, seed và định nghĩa điểm giữa baseline và PoC. Không thay đổi chúng sau khi xem kết quả eval chính thức. Nếu baseline hoặc PoC cho kết quả metric bằng 0 thì báo cáo trực tiếp giá trị 0; không tính phần trăm cải thiện khi mẫu số bằng 0. Với bản học viên hiện tại, không có GT nên không suy diễn metric từ nhận xét trực quan hay quyết định review thủ công.
