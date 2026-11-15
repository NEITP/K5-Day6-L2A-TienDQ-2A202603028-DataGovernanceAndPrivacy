# reports/ · Danh mục báo cáo và bằng chứng

| Tệp | Người tạo / nguồn | Cách tạo hoặc cập nhật |
|---|---|---|
| `group_report.md` | Nhóm | Hoàn thiện báo cáo T02 theo nội dung dự án |
| `metric_contract.md` | Nhóm | Khai báo protocol metric đã chốt; bộ học viên không có GT nên Recall/Precision ghi N/A |
| `t02_failure_modes.md` | Nhóm | Phân tích chỉ dựa trên input về ảnh đêm, lóa cục bộ và các trường hợp cam_B |
| `t02_failure_examples.png` | Nhóm | Ảnh ghép có chú thích từ input, minh họa phân tích failure mode |
| `review_queue.csv` | Pipeline + reviewer | Bản chụp hàng đợi 20 ảnh sau review do reviewer xuất |
| `decision.json` / `decision_log.csv` | Pipeline | Quyết định cho batch và lịch sử quyết định, sao chép từ `out/poc/` |
| `audit_log.jsonl` | Pipeline + reviewer | Nhật ký audit chỉ ghi nối tiếp, sao chép từ `out/poc/` |
| `team_contributions.csv` | Nhóm | Bằng chứng tác giả và review hiện tại; cập nhật commit SHA sau khi commit |
| `metrics_baseline.json`, `metrics_poc.json`, `table1_baseline_vs_poc.md` | Script | Tạo bằng `src.evaluate` / `src.compare` khi có GT phù hợp; không chỉnh sửa thủ công. Bộ học viên hiện không có GT nên các metric này không được tạo cho bản nộp. |

Các tệp metric và bảng so sánh được sinh bằng script, không sửa tay. Với bộ dữ liệu học viên hiện tại, không có nhãn GT để tính Recall@20 hoặc Precision@20; không lấy nhận xét trực quan hay quyết định review thay cho metric có GT.
