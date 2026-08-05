# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung             |
| --------------- | --------------------- |
| Họ và tên       | Phạm Khánh Linh        |
| MSSV            | 2A202601507            |
| Khóa/Lớp        | K3                     |
| Vai trò chính   | Order & Seller Agent    |
| Ngày hoàn thành | 2026-08-05           |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------- | -------------------- | ---------------- | ------------------ | ------------ |
| Order & Seller Agent — tra `orders.csv`, `order_items.csv`, `sellers.csv` theo `claimed_order_id`, xác định `order_status`, danh sách item/seller, mốc `shipping_limit_date` | `src/agents/order_seller_agent.py` | `claimed_order_id` từ Coordinator + `data/olist_orders_dataset.csv`, `olist_order_items_dataset.csv`, `olist_sellers_dataset.csv` | dict `order`, `items[]`, `seller_ids[]`, `seller_violations[]` chuyển cho Payment/Delivery Agent | Hoàn thành |
| Quy tắc xác định seller vi phạm khi order có nhiều item | Hàm so sánh `order_delivered_carrier_date > shipping_limit_date` theo từng seller trong `order_seller_agent.py::analyze()` | Item rows theo order | Danh sách seller vi phạm (nếu có), dùng cho `SELLER_HANDOFF_AFTER_LIMIT` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ---------- | ------------------------------- | --------- |
| [Debug/tích hợp/tài liệu] | [Tên hoặc module] | [Kết quả và bằng chứng] |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| ----------------------- | ------------------------------ | ------------------- | --------------- |
| Tra order EC_001 (`e2a03ccf5ea816036608b2d8c3ab8e60`), phát hiện seller bàn giao muộn | `src/agents/order_seller_agent.py` | `claimed_order_id` | `seller_violations = ["f7496d659ca9fdaf323c0aae84176632"]` | `python -m src.run_pipeline` rồi mở `output/EC_001.json` |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Case `EC_001.json` (khách báo "giao trễ"): `order_seller_agent` phát hiện `order_delivered_carrier_date` (2018-...) muộn hơn `shipping_limit_date` của item duy nhất trong đơn, đưa seller `f7496d659ca9fdaf323c0aae84176632` vào `seller_violations`. Delivery Agent + Policy Agent dùng cờ này để kết luận `primary_issue = "late_delivery_seller"` thay vì đổ lỗi logistics — khớp `output/EC_001.json` thực tế đã ghi.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Không thể kết luận trách nhiệm chỉ từ nội dung khiếu nại của khách. Order & Seller Agent phải xác định trạng thái đơn thực tế (`canceled`/`unavailable`/khác), danh sách item và seller liên quan, và mốc `shipping_limit_date` seller phải bàn giao — làm căn cứ cho Delivery Agent và Policy Agent phân biệt trách nhiệm seller vs logistics.

### Cách triển khai

`data_loader.get_order()`/`get_items()` tra `orders.csv`/`order_items.csv` theo `claimed_order_id` (index sẵn theo `order_id` để O(1)); `order_seller_agent.analyze()` gom `seller_ids = sorted({item["seller_id"] for item in items})`. Với mỗi item, so `order_delivered_carrier_date` (chung cả đơn) với `shipping_limit_date` của chính item đó bằng `pandas.to_datetime` (không đổi múi giờ, so trực tiếp giá trị CSV theo đúng lưu ý README mục 2) — seller nào có ít nhất 1 item bị `carrier_date > shipping_limit_date` thì vào `seller_violations`. Việc build chuỗi evidence ID (`item:<order_id>:<n>`, `seller:<seller_id>`) được để cho Verifier Agent (Nhi) làm ở bước cuối, agent này chỉ trả dict fact thô để tránh 2 nơi tự sinh evidence ID lệch nhau.

### Input, output và contract

| Thành phần | Mô tả |
| ------------ | ------- |
| Input | `claimed_order_id` (từ Coordinator), `olist_orders_dataset.csv`, `olist_order_items_dataset.csv`, `olist_sellers_dataset.csv` |
| Output | `order_status`, `item_ids`, `seller_ids`, cờ `seller_handoff_after_limit` theo seller |
| Module phụ thuộc | Coordinator Agent (nhận `claimed_order_id`) |
| Module sử dụng output | Delivery Agent (đối chiếu carrier/estimate), Policy Agent (chọn `responsible_parties`), Verifier Agent |
| Điều kiện lỗi cần xử lý | `claimed_order_id` không có trong `orders.csv`; order không có item row (`item_ids`, `seller_ids` để rỗng theo mục 6 README) |

### Cách xác minh

```bash
python -m src.run_pipeline
```

- **Kết quả mong đợi:** Case có `claimed_order_id` hợp lệ trả về đúng `order_status`, `seller_ids` không rỗng khi order có item, `seller_violations` chỉ chứa seller thực sự bàn giao muộn.
- **Kết quả thực tế:** Cả 50/50 case chạy xong không crash; `output/EC_001.json`, `EC_022.json`, `EC_029.json`, `EC_033.json`, `EC_034.json`, `EC_037.json`, `EC_043.json`, `EC_044.json` đều ra `primary_issue = "late_delivery_seller"` với đúng 1 `seller_ids` khớp `evidence_ids` chứa `seller:<id>`.
- **Artifact/log:** `output/EC_001.json`, dòng `agent: "order_seller_agent"` trong `logging/trace.jsonl`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** So sánh `order_delivered_carrier_date` (cột dùng chung cho cả đơn trong `orders.csv`) với `shipping_limit_date` (cột riêng theo từng dòng `order_items.csv`) — cần chọn kiểu dữ liệu và cách ép kiểu khi so sánh datetime giữa 2 bảng khác nguồn.
- **Các phương án đã cân nhắc:** (1) So sánh chuỗi ISO trực tiếp (string compare); (2) Parse cả hai cột bằng `pandas.to_datetime` rồi so sánh kiểu `Timestamp`.
- **Phương án đã chọn:** Parse bằng `pandas.to_datetime(..., errors="coerce")` cho cả `order_delivered_carrier_date` và `shipping_limit_date`, chỉ so sánh khi cả hai không phải `NaT`.
- **Lý do:** String compare có thể sai nếu định dạng giờ/mili-giây không đồng nhất tuyệt đối giữa 2 file CSV; parse về `Timestamp` loại bỏ rủi ro đó và cho phép guard case thiếu dữ liệu (`NaT`) mà không crash, đúng lưu ý README mục 2 "so sánh theo giá trị trong CSV, không đổi múi giờ" — `to_datetime` mặc định không tự đổi timezone khi cột nguồn không có offset.
- **Bằng chứng quyết định phù hợp:** 50/50 case chạy xong, không có exception nào từ so sánh datetime; 8 case ra `late_delivery_seller` đều có đúng 1 seller trong `seller_violations` khớp thủ công khi tra `order_items.csv` bằng `claimed_order_id`.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Không phải lỗi runtime mà là câu hỏi thiết kế: nếu `claimed_order_id` khách gửi lên không có trong `orders.csv` thì agent phải trả gì để Payment/Delivery Agent phía sau không crash?
- **Lệnh hoặc bước tái hiện:** Test thủ công với case giả `claimed_order_id = "ORDER_ID_KHONG_TON_TAI"` qua `coordinator_agent.process_case()`.
- **Nguyên nhân gốc:** `data_loader.get_order()` trả `None` khi không tìm thấy `order_id` trong index; nếu trả thẳng `None` cho các agent sau (vốn gọi `order.get(...)`) sẽ crash với `AttributeError`.
- **Cách xử lý:** `order_seller_agent.analyze()` luôn trả `order_found` (bool) tách riêng, còn `order` giữ nguyên `None`; `coordinator_agent.py` chuẩn hoá `order = order_seller["order"] or {}` trước khi truyền tiếp, và tự log `level="warning"` khi `order_found=False`.
- **Cách xác minh sau khi sửa:** Chạy lại test case giả — pipeline không crash, trả `output` hợp lệ với `order_ids = ["ORDER_ID_KHONG_TON_TAI"]`, `item_ids`/`seller_ids` rỗng; dòng trace `order_seller_agent | lookup | level: warning | detail.found: false` xuất hiện đúng như kỳ vọng.
- **Điều học được:** Agent đầu chuỗi handoff phải tách rõ "không tìm thấy" (`None`/`False`) khỏi "rỗng hợp lệ" (`{}`/`[]`), nếu không các agent phía sau dễ nhầm 2 trường hợp và crash hoặc suy luận sai.

Nếu chưa xử lý xong:

- **Phạm vi bị ảnh hưởng:** [Module/artifact.]
- **Những gì đã loại trừ:** [Các giả thuyết đã kiểm tra.]
- **Bước tiếp theo:** [Hành động có thể kiểm chứng.]

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Case đi từ `input/EC_xxx.json` qua các agent domain (order/seller, payment, delivery), tổng hợp evidence, áp policy, verify, rồi ghi ra `output/EC_xxx.json` như thế nào?
2. Evidence ID và root-cause code dùng để đo đúng/sai của kết luận ra sao (đối chiếu mục 5, 6 README)?
3. Verifier Agent kiểm tra gì ngoài việc parse đúng schema (giới hạn số lượng ID, số tiền làm tròn, evidence tồn tại thật trong CSV)?
4. Vì sao phải dùng cùng bộ 50 case và cùng policy version cho toàn bộ pipeline?
5. Một case được coi là xử lý đúng dựa trên artifact và tiêu chí nào (bảng trọng số chấm điểm mục 8 README)?

**Câu trả lời:**

1. Case bắt đầu ở `input/EC_xxx.json`. Tôi nhận `claimed_order_id`, tra ra `order`/`items`/`seller_violations` và đưa cho Payment Agent (đối soát tiền) rồi Delivery Agent (so timestamp). Policy Agent gộp cả 3 nguồn để chọn `primary_issue` theo bảng luật, Verifier build JSON cuối và lọc evidence sai trước khi Coordinator ghi ra `output/EC_xxx.json`.
2. Evidence ID phải "dựng được" từ chính dữ liệu tôi tra ra — ví dụ `seller:<id>` chỉ hợp lệ nếu seller đó thật sự có trong `sellers.csv` và thật sự nằm trong `seller_violations` của case; root-cause code như `SELLER_HANDOFF_AFTER_LIMIT` phải khớp với điều kiện tôi tính (`carrier_date > shipping_limit_date`), nếu không khớp thì bị coi là kết luận sai theo README mục 5-6.
3. Ngoài parse schema, Verifier còn tra ngược `data_loader` để chắc mỗi evidence tôi/agent khác đưa ra là có thật (không phải id tôi "đoán" đúng định dạng nhưng sai giá trị), và cắt bớt nếu vượt giới hạn 5 entity/10 evidence.
4. Vì rule `EC_POLICY_V1` áp cho tất cả agent — nếu case của tôi và case của bạn khác dùng version policy khác nhau thì kết quả `late_delivery_seller` vs `late_delivery_logistics` có thể lệch chuẩn so sánh, không thể chấm điểm công bằng giữa 50 case.
5. Với phần của tôi, case đúng khi `order_status`, `item_ids`, `seller_ids` khớp thật với CSV và `seller_violations` chỉ chứa seller thật sự vi phạm — tôi đã đối chiếu tay case EC_001 (order `e2a03ccf...`) và xác nhận seller `f7496d659ca9fdaf323c0aae84176632` đúng là seller có `shipping_limit_date` bị vượt.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phạm Khánh Linh
**Ngày xác nhận:** 2026-08-05
