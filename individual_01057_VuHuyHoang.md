# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung             |
| --------------- | --------------------- |
| Họ và tên       | Vũ Huy Hoàng            |
| MSSV            | 2A202601057            |
| Khóa/Lớp        | K3                     |
| Vai trò chính   | Delivery Agent          |
| Ngày hoàn thành | 2026-08-05           |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------- | -------------------- | ---------------- | ------------------ | ------------ |
| Delivery Agent — so `order_delivered_customer_date` với `order_estimated_delivery_date` | `src/agents/delivery_agent.py` (`DeliveryAgent.run()`) | `order_id` (tự đọc `orders` qua `DataStore`, không phụ thuộc agent khác) | `DeliveryFacts` (dataclass: 3 timestamp + `delivered_after_estimate`) chuyển cho Policy Agent | Hoàn thành |
| Nhánh `hoang` — tự build pipeline hoàn chỉnh độc lập để đối chiếu thiết kế với bản `main` | Git branch `origin/hoang` (4 commit: implement delivery agent → complete pipeline → make evidence issue-aware → restore entities + calibrate confidence) | Code + `output/` tự chạy | Xác nhận độc lập cùng 1 kết luận thiết kế evidence/confidence với `main` — tăng độ tin cậy trước khi nhóm chọn `main` làm bản nộp | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ---------- | ------------------------------- | --------- |
| Tự thử nghiệm "scope evidence theo issue" rồi "restore lại entities đầy đủ + calibrate confidence" trên nhánh riêng | Toàn nhóm | Kết quả trùng khớp độc lập với phát hiện trên nhánh `main`/`nhi`: entity phải đầy đủ không điều kiện, evidence mới lọc theo trách nhiệm — dữ liệu chéo giúp nhóm tự tin chọn thiết kế cuối nhanh hơn |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| ----------------------- | ------------------------------ | ------------------- | --------------- |
| Xác định case EC_009 giao trễ nhưng không phải lỗi seller | `src/agents/delivery_agent.py` | `delivered_after_estimate=True` | `python run_pipeline.py` rồi mở `output/EC_009.json` |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Case `EC_009.json` (order `3aaee056441dcae251f360b1c71a7279`): `order_delivered_customer_date` muộn hơn `order_estimated_delivery_date` → `DeliveryFacts.delivered_after_estimate = True`. Vì Order & Seller Agent không tìm thấy seller nào vi phạm (`late_seller_ids=[]`), Policy Agent tự kết luận `primary_issue="late_delivery_logistics"` — bản thân Delivery Agent **không** quyết seller hay logistics chịu trách nhiệm, chỉ trả sự kiện "có trễ hay không". Khớp `output/EC_009.json` thực tế: `responsible_parties=[{"party_type":"logistics_provider","party_id":"LOGISTICS_PROVIDER"}]`, `recommended_refund_brl=12.36` (bằng `freight_total`).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Cùng phản ánh "giao trễ" nhưng cần tách 2 câu hỏi độc lập: (1) đơn có thực sự giao muộn hơn ngày ước tính cho khách hay không (việc của tôi), và (2) nếu có, ai chịu trách nhiệm — seller bàn giao trễ cho carrier, hay carrier/logistics giao chậm dù seller đã bàn giao đúng hạn (việc của Policy Agent, dựa trên fact của cả tôi lẫn Order & Seller Agent).

### Cách triển khai

`DeliveryAgent.run(case_id, store, order_id)` tự gọi `store.get_order(order_id)` — **không nhận `late_seller_ids` làm input**, hoàn toàn độc lập với Order & Seller Agent. Nếu order không tồn tại, trả `DeliveryFacts` với mọi field `None`. Nếu có: lấy `order_estimated_delivery_date`, `order_delivered_customer_date`, `order_delivered_carrier_date`; nếu cả `delivered_customer` và `estimated` đều `pd.notna()` thì `delivered_after_estimate = bool(delivered_customer > estimated)`, ngược lại (đơn chưa giao) để `None` (không phải `False` — `None` nghĩa là "chưa biết", `False` nghĩa là "biết chắc không trễ", 2 ý nghĩa khác nhau). Việc quyết seller hay logistics chịu trách nhiệm **hoàn toàn nằm trong `policy_rules.decide()`**: chỉ khi `delivery_facts.delivered_after_estimate is True` mới xét tiếp `order_facts.late_seller_ids` để rẽ nhánh — tôi không cần biết gì về seller cả.

### Input, output và contract

| Thành phần | Mô tả |
| ------------ | ------- |
| Input | `order_id`, đọc trực tiếp `orders` qua `DataStore` — không nhận fact từ agent khác |
| Output | `DeliveryFacts(order_estimated_delivery_date, order_delivered_carrier_date, order_delivered_customer_date, delivered_after_estimate)` |
| Module phụ thuộc | `src/data_store.py` |
| Module sử dụng output | Policy Agent (`policy_rules.decide()` dùng `delivered_after_estimate` làm điều kiện rẽ nhánh chính) |
| Điều kiện lỗi cần xử lý | `order_id` không tồn tại → mọi field `None`; đơn chưa giao (`delivered_customer_date` rỗng) → `delivered_after_estimate=None`, không bị hiểu nhầm là "không trễ" |

### Cách xác minh

```bash
python run_pipeline.py
```

- **Kết quả mong đợi:** Case giao trễ có seller vi phạm → `late_delivery_seller`; giao trễ nhưng seller đúng hạn → `late_delivery_logistics`; giao đúng/sớm hạn → không gắn cờ trễ.
- **Kết quả thực tế:** Tự chạy lại 50/50 case; 8 case `late_delivery_logistics` đều có `late_seller_ids=[]` (Order & Seller Agent xác nhận không seller nào vi phạm), khớp tay khi đối chiếu timestamp `EC_009`.
- **Artifact/log:** `output/EC_009.json`, dòng `agent: "delivery_agent"` trong `logging/trace.jsonl`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Delivery Agent có nên tự nhận `late_seller_ids` làm input để tự quyết `late_delivery_seller` vs `late_delivery_logistics`, hay chỉ trả sự kiện thời gian thuần túy và để Policy Agent tổng hợp?
- **Các phương án đã cân nhắc:** (1) Delivery Agent nhận thêm `late_seller_ids`, tự trả về `root_cause_candidate` cụ thể; (2) Delivery Agent hoàn toàn độc lập, chỉ trả `delivered_after_estimate`, việc rẽ nhánh để 100% trong `policy_rules.decide()`.
- **Phương án đã chọn:** (2).
- **Lý do:** Giữ Delivery Agent không phụ thuộc Order & Seller Agent giúp 2 agent này có thể chạy song song thật sự (không có dependency chéo), code đơn giản hơn (agent chỉ trả 1 sự kiện thời gian, không tự "đoán" trách nhiệm), và toàn bộ logic rẽ nhánh nằm gọn 1 nơi (`policy_rules.py`) — dễ audit hơn là rải rác quyết định ở nhiều agent.
- **Bằng chứng quyết định phù hợp:** 50/50 case chạy đúng, không có case nào cần Delivery Agent biết về seller mà vẫn phân loại đúng `late_delivery_seller`/`late_delivery_logistics`; nhóm nộp thật đạt 100.00/100.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Câu hỏi thiết kế trước khi viết code: `order_delivered_customer_date` hoặc `order_estimated_delivery_date` có thể là `NaN`/rỗng (đơn chưa giao) — so sánh trực tiếp giá trị rỗng dễ crash hoặc cho kết quả sai (coi nhầm là "không trễ").
- **Lệnh hoặc bước tái hiện:** Gọi thử `DeliveryAgent().run(case_id, store, order_id)` với 1 order có `order_delivered_customer_date` rỗng.
- **Nguyên nhân gốc:** So sánh `>` trực tiếp giữa `NaT`/`NaN` với timestamp thật trong pandas không raise lỗi nhưng trả `False` một cách âm thầm — dễ nhầm "chưa giao" thành "giao đúng hạn".
- **Cách xử lý:** Dùng `pd.notna()` guard tường minh cho cả 2 giá trị trước khi so sánh; nếu 1 trong 2 rỗng, trả `delivered_after_estimate=None` (không phải `True`/`False`) — Policy Agent coi `None` khác `False`, không tự ý gán "không trễ" cho đơn chưa giao.
- **Cách xác minh sau khi sửa:** Test order chưa giao trả đúng `delivered_after_estimate=None`, không rơi vào nhánh `late_delivery_*` lẫn `unsupported_late_claim` một cách sai lệch.
- **Điều học được:** Với dữ liệu có thể thiếu, nên dùng 3 trạng thái (`True`/`False`/`None`) thay vì ép về boolean 2 trạng thái — tránh việc "không biết" bị hiểu nhầm thành "biết là không".

Nếu chưa xử lý xong:

- **Phạm vi bị ảnh hưởng:** [Không có — đã xử lý xong.]
- **Những gì đã loại trừ:** [N/A]
- **Bước tiếp theo:** [N/A]

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Case đi từ `input/EC_xxx.json` qua các agent domain (order/seller, payment, delivery), tổng hợp evidence, áp policy, verify, rồi ghi ra `output/EC_xxx.json` như thế nào?
2. Evidence ID và root-cause code dùng để đo đúng/sai của kết luận ra sao (đối chiếu mục 5, 6 README)?
3. Verifier Agent kiểm tra gì ngoài việc parse đúng schema (giới hạn số lượng ID, số tiền làm tròn, evidence tồn tại thật trong CSV)?
4. Vì sao phải dùng cùng bộ 50 case và cùng policy version cho toàn bộ pipeline?
5. Một case được coi là xử lý đúng dựa trên artifact và tiêu chí nào (bảng trọng số chấm điểm mục 8 README)?

**Câu trả lời:**

1. Tôi chạy độc lập song song với Order & Seller Agent (không phụ thuộc nhau), chỉ trả `delivered_after_estimate`. Policy Agent gộp fact của tôi với `late_seller_ids` (Order & Seller) và `payment_total` (Payment) để ra `primary_issue` cuối; `output_builder.py` build JSON, Verifier kiểm rồi Coordinator ghi `output/EC_xxx.json`.
2. Root-cause code (`CARRIER_DELIVERED_AFTER_ESTIMATE` cho logistics, `SELLER_HANDOFF_AFTER_LIMIT` cho seller) do Policy Agent gán dựa trên tổ hợp fact của tôi + Order & Seller Agent — nếu tôi tính sai `delivered_after_estimate`, cả root cause (15%) lẫn evidence liên quan đều sai theo, dù Order & Seller Agent tính `late_seller_ids` đúng 100%.
3. Verifier tra ngược từng evidence ID vào `DataStore`, và raise lỗi khiến case bị loại khỏi `output/` nếu có vấn đề — không có khái niệm "ghi file kèm cảnh báo" trong thiết kế `main`.
4. Dùng chung 50 case + `EC_POLICY_V1` để định nghĩa "trễ" nhất quán (cùng phép so `delivered_customer_date > estimated_delivery_date`) cho mọi case, không lệch chuẩn giữa các lần chạy hay giữa nhánh git khác nhau của nhóm khi đối chiếu điểm.
5. Case thuộc phần giao hàng đúng khi `delivered_after_estimate` khớp thật 2 mốc thời gian trong CSV, độc lập hoàn toàn với việc seller có vi phạm hay không — tôi đã đối chiếu tay `EC_009`: giao trễ thật, và vì Order & Seller Agent xác nhận không seller nào vi phạm nên đúng là lỗi logistics. Nhóm nộp thật nhánh `main` đạt **100.00/100**.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Vũ Huy Hoàng
**Ngày xác nhận:** 2026-08-05
