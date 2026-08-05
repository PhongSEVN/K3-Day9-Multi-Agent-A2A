# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung             |
| --------------- | --------------------- |
| Họ và tên       | Nguyễn Văn Phong       |
| MSSV            | 2A202601241            |
| Khóa/Lớp        | K3                     |
| Vai trò chính   | Coordinator Agent       |
| Ngày hoàn thành | 2026-08-05           |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------- | -------------------- | ---------------- | ------------------ | ------------ |
| Coordinator Agent — nhận case, gọi lần lượt Order & Seller / Delivery / Payment Agent, đưa 3 bộ fact cho Policy Agent, rồi build + verify | `src/coordinator.py` (`Coordinator.process_case()`) | 1 dict case đã parse từ `input/EC_xxx.json` | payload JSON cuối theo schema, sau khi Verifier Agent thông qua | Hoàn thành |
| Entrypoint chạy toàn bộ 50 case, ghi `output/`, `logging/trace.jsonl`, `logging/metadata.json` | `run_pipeline.py` (root), `src/config.py`, `src/data_store.py` | 50 file `input/EC_001.json` → `EC_050.json` | 50 file `output/EC_xxx.json`, trace + metadata đầy đủ | Hoàn thành |
| Reconcile 4 nhánh git phân kỳ của nhóm (`main`, `nhi`, `hoang`, `feature/payment_agent_phuc`), xác định nhánh nào là bản nộp cuối | `git` (branch/merge, không phải file code) | Điểm thật từng nhánh (nộp qua leaderboard) | Repo `main` chốt là bản nộp, các nhánh khác giữ nguyên làm tham khảo | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ---------- | ------------------------------- | --------- |
| Đối chiếu độc lập thiết kế evidence/entity giữa nhánh của tôi và nhánh `hoang` của Hoàng | Toàn nhóm | Xác nhận 2 implementation độc lập hội tụ cùng 1 kết luận (item/payment luôn trích, seller chỉ trích khi là responsible party) — tăng độ tin cậy thiết kế trước khi chốt bản nộp |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| ----------------------- | ------------------------------ | ------------------- | --------------- |
| Chạy `run_pipeline.py` cho toàn bộ 50 case trên nhánh `main` | `run_pipeline.py`, `src/coordinator.py` | 50/50 `output/EC_xxx.json`, `logging/metadata.json` ghi `succeeded: 50, failed: 0` | `python run_pipeline.py` rồi `python -c "import json,glob; [json.load(open(f,encoding='utf-8')) for f in glob.glob('output/EC_*.json')]"` — không lỗi |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Tự chạy lại `run_pipeline.py` (không dùng lại file `output/` cũ) trên máy khác, `logging/metadata.json` ghi `started_at`/`finished_at` chênh **278.3 giây** cho 50 case (chạy tuần tự, không song song), `succeeded: 50, failed: 0`; đối chiếu output mới sinh ra với bản đã commit — `confidence = 1.0` ở toàn bộ 50 case, cấu trúc `evidence_ids` từng nhánh khớp 100% với mô tả trong `architecture.md`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Coordinator phải nhận `claimed_order_id`, gọi đúng thứ tự các agent chuyên trách domain (Order & Seller, Delivery, Payment — Delivery và Payment độc lập với nhau, chỉ Payment cần `item_total`/`freight_total` do Order & Seller tính trước), gộp 3 bộ fact cho Policy Agent ra quyết định, rồi build payload và để Verifier Agent gác cổng trước khi ghi file. Ngoài phần code, vấn đề lớn hơn nảy sinh giữa chừng: 4 thành viên tự build 4 nhánh git độc lập (kiến trúc code khác hẳn nhau), cần một quy trình để chọn ra bản nộp cuối cùng dựa trên **điểm thật**, không phải cảm tính.

### Cách triển khai

`Coordinator.process_case()`: `order_seller_agent.run()` → `delivery_agent.run()` (đọc thẳng `orders` qua `DataStore`, không phụ thuộc Order & Seller) và `payment_agent.run(..., order_facts.item_total, order_facts.freight_total)` (cần tổng tiền do Order & Seller tính) → `policy_agent.run(order_facts, delivery_facts, payment_facts)` gọi `policy_rules.decide()` (rule engine thuần Python) → `output_builder.build_output()` gộp thành payload → `verifier_agent.run()` kiểm schema (`pydantic`) + tra ngược từng evidence ID vào `DataStore`, **raise lỗi nếu sai thay vì âm thầm ghi file bẩn**. `run_pipeline.py` ở root gọi `Coordinator` cho từng file trong `input/`, ghi `output/EC_xxx.json`, và ghi `logging/metadata.json` (model, thời gian chạy, số case thành công/fail).

Về phần điều phối nhóm: khi phát hiện repo có 4 nhánh (`main` của tôi, `nhi`, `hoang`, `feature/payment_agent_phuc`) với 4 kiến trúc code khác nhau hoàn toàn, không thể merge tự động — quyết định dựa vào điểm thật đã nộp của từng nhánh (nhánh `main` báo 100.00/100, các nhánh khác 92-95) để chọn `main` làm bản nộp cuối, giữ nguyên các nhánh khác không xoá.

### Input, output và contract

| Thành phần | Mô tả |
| ------------ | ------- |
| Input | `input/EC_xxx.json`: `case_id`, `opened_at`, `customer_request.claimed_order_id`, `policy_version` |
| Output | `output/EC_xxx.json` theo schema mục 6 README, validate bằng `src/schema.py` (`CaseOutput`, pydantic) |
| Module phụ thuộc | `order_seller_agent`, `delivery_agent`, `payment_agent`, `policy_agent`, `verifier_agent`, `output_builder`, `data_store` |
| Module sử dụng output | Verifier Agent (gác cổng cuối), quy trình nộp bài (nén `output/` thành zip) |
| Điều kiện lỗi cần xử lý | `claimed_order_id` không có trong `orders.csv` (`order_found=False`, các agent sau tự trả fact rỗng/`None` hợp lệ, không crash); Verifier phát hiện vấn đề → case bị loại khỏi `output/` thay vì ghi file sai |

### Cách xác minh

```bash
python run_pipeline.py
python -c "import json,glob; n=[json.load(open(f,encoding='utf-8')) for f in sorted(glob.glob('output/EC_*.json'))]; print(len(n))"
```

- **Kết quả mong đợi:** 50 file `output/EC_001.json`..`EC_050.json`, `logging/metadata.json` ghi `succeeded: 50, failed: 0`.
- **Kết quả thực tế:** Chạy lại thành công, in ra `50`; `metadata.json` xác nhận `succeeded: 50, failed: 0`; thời gian chạy 278.3 giây (tuần tự, không song song hoá — điểm có thể cải thiện thêm nếu có thời gian).
- **Artifact/log:** `output/EC_001.json`..`EC_050.json`, `logging/trace.jsonl`, `logging/metadata.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** 4 thành viên trong nhóm mỗi người tự build 1 pipeline hoàn chỉnh trên nhánh git riêng (`main`, `nhi`, `hoang`, `feature/payment_agent_phuc`) trong lúc thi, không biết nhánh nào đúng/tốt hơn cho tới khi có điểm thật.
- **Các phương án đã cân nhắc:** (1) Cố merge code của các nhánh lại thành 1 bản duy nhất; (2) Chọn nguyên 1 nhánh có điểm thật cao nhất làm bản nộp, không merge.
- **Phương án đã chọn:** (2) — chọn nguyên nhánh `main` (100.00/100).
- **Lý do:** 4 nhánh có cấu trúc file hoàn toàn khác nhau (`coordinator_agent.py` vs `coordinator.py`, `data_loader.py` vs `data_store.py`...), merge tự động chắc chắn conflict và tốn thời gian sửa tay trong lúc gần hết giờ thi hơn là so điểm thật rồi chọn thẳng nhánh tốt nhất.
- **Bằng chứng quyết định phù hợp:** Nhánh `main` có điểm nộp thật 100.00/100 (cao nhất trong 4 nhánh, nhánh `nhi` chỉ 95.59); tự chạy lại `main` xác nhận cấu trúc/logic đúng như tài liệu, không phát sinh lỗi.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Không phải lỗi code — mà là phát hiện qua `git fetch`/`git log --graph --all` giữa chừng thi: repo có 4 nhánh phân kỳ, mỗi nhánh chứa 1 bộ code + `output/` + `architecture.md` khác nhau, không nhánh nào biết về 3 nhánh kia.
- **Lệnh hoặc bước tái hiện:** `git branch -a`, `git log --graph --oneline --all --decorate -25`.
- **Nguyên nhân gốc:** Cả nhóm làm việc song song trên cùng repo mà không thống nhất trước 1 nhánh chung để cùng push — mỗi người tự tạo nhánh/commit riêng khi thấy pipeline của mình chạy được.
- **Cách xử lý:** Không sửa code các nhánh khác; chỉ đối chiếu điểm thật đã nộp của từng nhánh (dựa trên số liệu thành viên báo lại), xác nhận `main` cao nhất, rồi thống nhất cả nhóm dùng `main` làm bản nộp cuối — các nhánh khác giữ nguyên, không xoá, để có thể tham khảo lại nếu cần.
- **Cách xác minh sau khi sửa:** `git checkout main && git pull`, chạy lại `run_pipeline.py` xác nhận 50/50 case thành công, cấu trúc evidence/entity khớp đúng bản đã nộp điểm 100.
- **Điều học được:** Với repo nhóm chấm điểm theo thời gian thực, nên thống nhất **1 nhánh chung duy nhất** để push ngay từ đầu, tránh tình trạng 4 người 4 bản không ai biết bản nào đang là "chính thức" cho tới phút chót.

Nếu chưa xử lý xong:

- **Phạm vi bị ảnh hưởng:** Không còn — đã chốt `main` làm bản nộp, các nhánh khác không ảnh hưởng tới zip nộp cuối.
- **Những gì đã loại trừ:** Đã loại trừ khả năng merge code (rủi ro conflict cao hơn lợi ích, không kịp thời gian).
- **Bước tiếp theo:** Không còn cần thiết cho bản nộp; có thể tham khảo thêm ý tưởng song song hoá (`ThreadPoolExecutor`) từ nhánh `nhi` để giảm 278s xuống dưới 1 phút nếu nhóm muốn tối ưu thêm sau khi đã có điểm tốt.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Case đi từ `input/EC_xxx.json` qua các agent domain (order/seller, payment, delivery), tổng hợp evidence, áp policy, verify, rồi ghi ra `output/EC_xxx.json` như thế nào?
2. Evidence ID và root-cause code dùng để đo đúng/sai của kết luận ra sao (đối chiếu mục 5, 6 README)?
3. Verifier Agent kiểm tra gì ngoài việc parse đúng schema (giới hạn số lượng ID, số tiền làm tròn, evidence tồn tại thật trong CSV)?
4. Vì sao phải dùng cùng bộ 50 case và cùng policy version cho toàn bộ pipeline?
5. Một case được coi là xử lý đúng dựa trên artifact và tiêu chí nào (bảng trọng số chấm điểm mục 8 README)?

**Câu trả lời:**

1. `run_pipeline.py` đọc từng file `input/EC_xxx.json`, gọi `Coordinator.process_case()`. Coordinator lấy `claimed_order_id` cho Order & Seller Agent (status/item/seller/`late_seller_ids`), Delivery Agent (so `delivered_customer_date` vs `estimated_delivery_date`), Payment Agent (tổng payment); cả 3 bộ fact đưa cho Policy Agent áp `EC_POLICY_V1` (if/elif thuần Python trong `policy_rules.py`) ra `Decision`; `output_builder.build_output()` gộp thành payload; Verifier Agent kiểm schema + evidence tồn tại thật rồi mới cho ghi `output/EC_xxx.json`.
2. Evidence ID phải trỏ đúng dòng dữ liệu thật — Verifier dùng regex tách từng loại (`order:`/`item:`/`payment:`/`seller:`/`policy:`) rồi tra ngược `DataStore` xác nhận tồn tại, không chỉ đúng định dạng. Root-cause code lấy từ bảng `ROOT_CAUSE_BY_ISSUE` cố định 1-1 với `primary_issue`, không tự sinh mã mới.
3. Verifier còn validate toàn bộ schema bằng `pydantic` (`CaseOutput.model_validate`), và **raise lỗi khiến case bị loại khỏi `output/`** nếu có vấn đề — khác với cách xử lý "ghi file kèm cảnh báo" tôi từng làm ở bản nháp trước đó; cách của `main` khắt khe hơn, không có case nào lọt ra ngoài nếu chưa qua kiểm chứng.
4. Dùng chung 50 case + `policy_version=EC_POLICY_V1` để mọi agent áp cùng 1 bộ luật cố định — nếu khác nhau giữa các lần chạy, không thể so sánh/đối chiếu điểm giữa các nhánh git khác nhau như tôi vừa làm ở mục 5-6.
5. Case đúng khi khớp 6 tiêu chí trọng số README mục 8. Điểm đặc biệt phát hiện được: `primary_issue` đúng 100% (đã verify tay) không tự động cho 100 điểm — `confidence` phải phản ánh đúng độ chắc chắn thật (1.0 khi rule match sạch, không hạ thấp "cho khiêm tốn") thì mới đạt điểm tối đa ở tiêu chí Đánh giá case; nộp thật của nhóm xác nhận tổng 100.00/100.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Văn Phong
**Ngày xác nhận:** 2026-08-05
