# Báo cáo nhóm T02 — Phân loại ưu tiên ảnh QC

## 00 · Thông tin chung

| Mục | Giá trị |
|---|---|
| Nhóm | G04 |
| Thử thách | T02 · Raw QC Triage |
| Chủ sở hữu / người review | Đinh Quốc Tiến |
| Repository | [K5-Day6-L2A-TienDQ-2A202603028-DataGovernanceAndPrivacy](https://github.com/NEITP/K5-Day6-L2A-TienDQ-2A202603028-DataGovernanceAndPrivacy) |
| Tag demo / final | `final-24h` · bản nộp hiện tại; metric chính thức cần GT từ giảng viên |
| Seed chạy | 42 |
| Ground truth | Chưa có trong bản checkout học viên; chưa thể tính metric chính thức |

## 01 · Bài toán

Pipeline xếp hạng các ảnh giao thông có khả năng không sử dụng được để người review kiểm tra trong ngân sách cố định 20 ảnh. Ảnh kém có thể che khuất người đi đường, biển báo hoặc biển số đối với hệ thống nhận diện phía sau; báo động giả quá nhiều làm mất thời gian review và có thể khiến nhóm loại bỏ những ảnh ban đêm vẫn hữu ích.

Đầu vào gồm `images.csv` và 96 ảnh JPEG xử lý offline. Đầu ra gồm một điểm cho mỗi ảnh trong `ranked_review.csv`, hàng đợi review 20 ảnh thuộc eval, audit log chỉ ghi nối tiếp và quyết định cho cả batch. Điểm số chỉ ưu tiên ảnh cần xem; người review chọn KEEP / RECAPTURE. Batch giữ trạng thái HOLD khi còn mục chưa được kết luận.

Chính sách quyết định yêu cầu có người review: nếu có SKIP, HOLD/escalate hoặc mục trong queue chưa review thì kết quả là HOLD; nếu đã review hết và có ít nhất một RECAPTURE thì kết quả là RECAPTURE; chỉ khi tất cả đều KEEP thì kết quả là KEEP. Chính sách này được cài sau vòng review hiện tại và không dùng nhãn ẩn.

## 02 · Dữ liệu và nguồn gốc

| Split | Số ảnh | Ngày | Chạng vạng | Đêm | Giấy phép |
|---|---:|---:|---:|---:|---|
| dev | 56 | 36 | 16 | 4 | CC0-1.0, dữ liệu tổng hợp |
| eval | 40 | 20 | 4 | 16 | CC0-1.0, dữ liệu tổng hợp |
| Tổng | 96 | 56 | 20 | 20 | CC0-1.0, dữ liệu tổng hợp |

Mỗi ảnh có kích thước 320×180. Các cột metadata là `image_id`, `path` tương đối, `camera_id`, `light` và `split`. Manifest ghi nguồn `synthetic:tools/make_fixtures.py (seed 42)`, giấy phép, split/group và SHA-256. Split eval được tách theo nhóm cảnh gốc (`img_XX`), không tách riêng từng ảnh bị biến đổi. Manifest đã được xác minh trong preflight; các lần chạy pipeline cũng vượt qua kiểm tra provenance nghiêm ngặt.

Nhãn ground truth theo đặc tả gồm `none`, `blur`, `glare`, `dark` hoặc `compression`, mức độ 0–2 và `is_defect`. Các nhãn này không có trong bản checkout hiện tại và pipeline không đọc chúng. Bài không dùng ảnh thực hoặc mô hình pretrained.

## 03 · Thiết kế

```text
images.csv + manifest
        ↓ kiểm tra đường dẫn, ID và provenance
đặc trưng ảnh (độ nét, độ sáng, bão hòa cục bộ, vết khối JPEG)
        ↓ tham chiếu robust chỉ từ dev theo camera/light; tính điểm theo trọng số
xếp hạng eval theo score → contact sheet 20 ảnh
        ↓ quyết định reviewer + audit log chỉ ghi nối tiếp
quyết định batch KEEP / RECAPTURE / HOLD + đầu ra CSV/JSON
```

PoC tính phương sai Laplacian để nhận biết mờ; thống kê độ sáng và tỷ lệ điểm ảnh tối để nhận biết thiếu sáng; bão hòa toàn ảnh và theo ô nhỏ để nhận biết lóa; cùng chênh lệch cường độ tại biên mỗi 8 pixel làm tín hiệu vết khối JPEG. Độ lệch của các đặc trưng được chuẩn hóa bằng median/MAD từ split `dev`, ưu tiên nhóm camera/light trùng khớp và dùng nhóm dự phòng khi số mẫu ít. Trọng số heuristic cố định: blur 0.40, dark 0.25, glare 0.20, compression 0.15. Không dùng mô hình học máy hoặc truy cập mạng.

Baseline Laplacian toàn cục xếp ảnh có phương sai thấp lên trước (`score = -laplacian_variance`). Đây là baseline một đặc trưng. Hai pipeline dùng cùng seed 42, eval pool và B=20. Chưa tính recall/precision xếp hạng vì chưa có GT của giảng viên.

## 04 · Kết quả chạy baseline và PoC

Cả hai lần chạy hoàn tất offline bằng Python 3.14.6 trên Windows 11, AMD64 Family 23 Model 104 Stepping 1. Baseline chạy 0.3233 giây cho 96 ảnh (0.337 giây/100 ảnh); PoC chạy 1.1855 giây cho 96 ảnh (1.235 giây/100 ảnh). Đây là thời gian end-to-end; thời gian thực tế thay đổi theo máy và lần chạy.

| Metric | Baseline Laplacian toàn cục | PoC nhiều đặc trưng | Trạng thái |
|---|---:|---:|---|
| Defect Recall@20 | Chưa có | Chưa có | Thiếu GT |
| Precision@20 | Chưa có | Chưa có | Thiếu GT |
| Số ảnh eval được xếp hạng | 40 | 40 | Cùng held-out pool |
| Ngân sách review | 20 | 20 | Cùng ngân sách |
| Thời gian / 100 ảnh đầu vào | 0.337 giây | 1.235 giây | Run info, end-to-end |

Chưa kết luận PoC tốt hơn baseline. Mỗi file dự đoán có đủ 96 ảnh; evaluator lọc `split=eval`. Score và trọng số được giữ cố định trong source hiện tại. Khi có overlay, không tinh chỉnh trọng số dựa trên nhãn eval.

## 05 · Quy trình đánh giá

- **Metric chính:** Defect Recall@B = số ảnh lỗi thật trong top B / tổng số ảnh lỗi thật trong eval. Giá trị cao hơn là tốt hơn.
- **Metric phụ:** Precision@B = số ảnh lỗi thật trong top B / B. Giá trị cao hơn là tốt hơn.
- **Pool:** chỉ dùng split eval, 40 ảnh; B=20. Xếp giảm dần theo score ổn định; seed 42.
- **Slice:** báo cáo theo điều kiện sáng (`day`, `dusk`, `night`) và camera (`cam_A`, `cam_B`). Eval có 20 ảnh ngày, 4 chạng vạng, 16 ban đêm; 28 ảnh cam_A, 12 ảnh cam_B.
- **Ngưỡng:** đây là bài toán xếp hạng với ngân sách cố định. Điểm cắt của queue là score ở hạng 20; không chọn ngưỡng chất lượng nhị phân bằng nhãn eval. Thống kê tham chiếu robust của PoC chỉ dùng dev.
- **Độ bất định:** eval chỉ có 40 ảnh nên cần báo tử số/mẫu số và tránh diễn giải quá mức các chênh lệch nhỏ. Nếu giảng viên yêu cầu, tính khoảng bootstrap từ nhãn evaluator; hiện chưa có GT nên chưa tính.
- **Lệnh đánh giá chính thức:**

```powershell
py -3.14 -m src.evaluate --track t02 --pred out\baseline\ranked_review.csv --run-name baseline --out reports\metrics_baseline.json
py -3.14 -m src.evaluate --track t02 --pred out\poc\ranked_review.csv --run-name poc --out reports\metrics_poc.json
py -3.14 -m src.compare reports\metrics_baseline.json reports\metrics_poc.json --out reports\table1_baseline_vs_poc.md
```

Các lệnh này cần `fixtures/t02_raw_qc/gt/labels.csv`, hiện chưa có trong repo.

## 06 · Phân tích failure mode

Các ví dụ và phân tích nguyên nhân dựa trên input được ghi trong [t02_failure_modes.md](t02_failure_modes.md), kèm [ảnh minh họa có chú thích](t02_failure_examples.png). Tóm tắt:

1. Một số ảnh đêm có cạnh nhìn thấy rõ nhưng xếp dưới ngưỡng ngân sách review. Độ tối riêng lẻ không phản ánh đáng tin cậy khả năng sử dụng; nhiễu và điều kiện cảnh làm nhiễu các đặc trưng toàn ảnh.
2. `img_17_2` và `img_05_3` có vùng bão hòa sáng tập trung. Tín hiệu theo ô nhỏ giúp đưa chúng lên queue, nhưng thuật toán không phân biệt được vùng sáng đó che biển số quan trọng hay chỉ là phần không ảnh hưởng của cảnh.
3. Median phương sai Laplacian trên dev khác nhau rõ giữa camera (`cam_A` ban ngày 955.0, `cam_B` ban ngày 235.8), là lý do chuẩn hóa theo camera. Nhóm nhỏ và ảnh cam_B thực sự bị mờ vẫn khó phân biệt.

Đây là các trường hợp nghi vấn từ ảnh và metadata, chưa phải false alarm hay miss đã được xác nhận bằng GT. Contact sheet đã được xem thủ công để mô tả ví dụ; các nhận xét bằng mắt không phải benchmark có nhãn và không dùng để tuyên bố Recall@20 hay Precision@20.

## 07 · Review người thật và quyết định

Người review là Đinh Quốc Tiến. Queue đã review được lưu tại [review_queue.csv](review_queue.csv); contact sheet được tạo tại `out/poc/contact_sheet.html`. Trong 20 quyết định hiện tại có: 6 KEEP, 2 RECAPTURE, 8 SKIP và 4 HOLD/escalate. Audit log nằm ở `out/poc/audit_log.jsonl`; quyết định nằm trong `out/poc/decision.json`, còn lịch sử CSV được lưu tại [decision_log.csv](decision_log.csv).

Quyết định hiện tại là **HOLD**, mã lý do `REVIEW_INCOMPLETE`: còn 12/20 mục ở trạng thái SKIP hoặc HOLD. Hai mục RECAPTURE không xóa bỏ các mục chưa kết luận. Đây là cổng yêu cầu hoàn tất review, không phải kết luận chất lượng mô hình. Cần xử lý các mục SKIP/HOLD, chạy lại pipeline và lưu snapshot review/audit mới trước khi kết luận batch.

## 08 · Chạy lại và kiểm thử

```powershell
py -3.14 -m src.main --config configs\lab.yaml --track t02 --output out\poc --run-name poc --offline --seed 42
py -3.14 -m src.main --config configs\lab.yaml --track t02 --output out\baseline --run-name baseline --pipeline src.examples.t02_laplacian_baseline --offline --seed 42
py -3.14 -m pytest -q
```

Các test riêng trong `tests/test_t02_decision_policy.py` kiểm tra ánh xạ quyết định reviewer và ghi audit, review chưa hoàn tất, mục trong queue chưa được review, RECAPTURE và trường hợp tất cả KEEP. `py -3.14 -m pytest -q` hoàn tất không lỗi; các test cần GT được skip vì chưa cài overlay giảng viên. `py -3.14 -m tools.preflight` báo 0 lỗi và 2 cảnh báo tùy chọn (không có `data/real/` và mô hình tùy chọn).

## 09 · Giới hạn và sử dụng có trách nhiệm

- Tất cả ảnh hiện có là dữ liệu tổng hợp; kết quả có thể không chuyển sang cảm biến, thời tiết, quang học, nén ảnh hoặc tác vụ nhận diện thực tế.
- Độ nét và độ sáng toàn ảnh không cho biết một vật thể hoặc biển số cụ thể có đọc được không. Với quyết định ảnh hưởng lớn cần kiểm tra ROI và có người xem.
- Nhóm dev theo camera/điều kiện sáng nhỏ khiến thống kê robust kém ổn định; nhóm thiếu mẫu phải dùng fallback. Trọng số là heuristic, không được học hoặc xác nhận bằng GT.
- RECAPTURE nhầm có thể loại mất ảnh đêm hữu ích; KEEP nhầm có thể đưa ảnh lỗi xuống bước sau. Giữ cổng review cho tới khi có chất lượng đo được và ngưỡng vận hành được domain owner thống nhất.
- Bài này không chứng minh tuân thủ pháp luật hay quyền riêng tư. Fixture là dữ liệu tổng hợp, không có dữ liệu cá nhân thật; triển khai trên ảnh thật cần được xem xét về thẩm quyền, lưu trữ, truy cập, bảo mật và quyền riêng tư.

## 10 · Bằng chứng đóng góp

Người review và chủ sở hữu dự án được ghi nhận là Đinh Quốc Tiến. Bằng chứng review là `reports/review_queue.csv`. Phần triển khai được thực hiện với hỗ trợ AI theo yêu cầu của học viên; đóng góp cá nhân của học viên gồm review, yêu cầu dự án và cấu hình metadata. Commit có phần triển khai chính: `5266907897473653410ee36cec79a2ccaec99ce1`. Chưa tạo tag final vì còn thiếu GT và còn quyết định review chưa chốt.

## 11 · Tài liệu tham khảo

| Tài liệu | Liên quan |
|---|---|
| [OpenCV: Laplace Operator](https://docs.opencv.org/3.3.0/d5/db5/tutorial_laplace_operator.html) | Cơ sở cho toán tử đạo hàm bậc hai dùng trong tín hiệu độ nét Laplacian; đáp ứng cao tự nó không chứng minh ảnh sử dụng được. |
| [Bộ dữ liệu ACDC về điều kiện bất lợi](https://acdc.vision.ee.ethz.ch/) | Bộ dữ liệu cảnh giao thông có điều kiện bất lợi, trong đó có ban đêm; gợi ý cần báo cáo riêng slice ánh sáng bất lợi. Không dùng làm input trong bài này. |
| [Khung quản trị rủi ro AI của NIST](https://airc.nist.gov/airmf-resources/airmf/) | Tài liệu tham khảo tự nguyện về ghi nhận rủi ro, giới hạn, giám sát của con người và đánh giá; không phải chứng nhận tuân thủ. |

---

## Bảng 3 · Checklist chốt khi nộp

- [x] Link repo và tag cuối cùng trong README; input fixture là dữ liệu tổng hợp, không có PII thật.
- [ ] Đúng 1 lệnh run, 1 lệnh evaluate, 1 lệnh tests; không cần download khi chạy.
- [ ] Có baseline/PoC metrics, ít nhất 1 failure case, reviewer evidence và decision log.
- [x] Có license/source provenance, data splits, seed, offline environment và ghi rõ GT/eval N (GT chưa được cung cấp; eval N=40).
- [x] Mỗi thành viên có ít nhất 1 commit thực chất và được nêu minh bạch trong bảng đóng góp (`5266907`).
