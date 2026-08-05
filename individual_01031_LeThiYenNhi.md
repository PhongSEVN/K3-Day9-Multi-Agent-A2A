# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung             |
| --------------- | --------------------- |
| Họ và tên       | Lê Thị Yến Nhi          |
| MSSV            | 2A202601031            |
| Khóa/Lớp        | K3                     |
| Vai trò chính   | Policy Agent + Verifier Agent |
| Ngày hoàn thành | 2026-08-05           |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------- | -------------------- | ---------------- | ------------------ | ------------ |
| Policy Agent — áp bảng quy tắc `EC_POLICY_V1` (mục 4 README) theo đúng thứ tự if/elif ưu tiên để chọn `primary_issue`, `responsible_parties`, `refund_brl`, `action`, `cause_code` | `src/agents/policy_agent.py` | dict facts từ Order & Seller Agent, Payment Agent, Delivery Agent | dict quyết định (`primary_issue`, `case_status`, `confidence`, `responsible_parties`, `cause_code`, `refund_brl`, `action`) chuyển cho Verifier Agent | Hoàn thành |
| Verifier Agent — build JSON cuối theo schema mục 6 README, lọc evidence ID không grounded, cắt giới hạn số lượng, ghi log cảnh báo | `src/agents/verifier_agent.py` | dict quyết định của Policy Agent + facts thô | `output/EC_xxx.json` hoàn chỉnh (luôn ghi, kể cả khi phát hiện vấn đề) | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ---------- | ------------------------------- | --------- |
| [Debug/tích hợp/tài liệu] | [Tên hoặc module] | [Kết quả và bằng chứng] |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| ----------------------- | ------------------------------ | ------------------- | --------------- |
| Test Verifier tự loại evidence ID không grounded (order giả không tồn tại trong CSV) | `src/agents/verifier_agent.py::_build_evidence_ids` | Case giả `claimed_order_id="ORDER_ID_KHONG_TON_TAI"` | `evidence_ids` chỉ còn `["policy:DELIVERY_WITHIN_ESTIMATE"]`, id `order:ORDER_ID_KHONG_TON_TAI` bị loại | Chạy `coordinator_agent.process_case()` trực tiếp trong Python REPL, in JSON kết quả |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Test thủ công với `claimed_order_id` không tồn tại trong `orders.csv`: `_build_evidence_ids()` tạo candidate `order:ORDER_ID_KHONG_TON_TAI` như bình thường, nhưng `schemas.evidence_id_is_grounded()` gọi `data_loader.order_exists()` trả `False` nên id này bị loại trước khi ghi file — output cuối chỉ còn `evidence_ids: ["policy:DELIVERY_WITHIN_ESTIMATE"]`, không có evidence "khống". Đây là bằng chứng cơ chế chống false-positive evidence (README mục 5) hoạt động đúng trên input thật, không chỉ trên 50 case chuẩn (vốn không có order giả).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Hệ thống phải ưu tiên dữ liệu có thể kiểm chứng thay vì tin hoàn toàn lời khiếu nại hoặc tự suy diễn sự kiện không tồn tại (Olist không có refund ledger, tracking checkpoint theo item...). Policy Agent áp đúng thứ tự ưu tiên 6 loại `primary_issue` trong README; Verifier Agent là chốt chặn cuối để evidence ID không hợp lệ / vượt giới hạn số lượng / sai số tiền không lọt ra file output (tránh hard gate 0 điểm).

### Cách triển khai

`policy_agent.decide()` là chuỗi `if/elif` đúng thứ tự bảng README mục 4: `canceled_order_paid` → `unavailable_order_paid` → `late_delivery_seller` → `late_delivery_logistics` → `valid_split_payment` → `unsupported_late_claim` → nhánh `else` (fallback, gắn `confidence` thấp hơn, log cảnh báo). Model `gpt-4o-mini` chỉ được gọi sau khi rule engine đã quyết xong, để chấm `confidence` blend `0.7 × base_confidence + 0.3 × llm_confidence` — không có đường nào cho LLM đổi `primary_issue`/số tiền.

`verifier_agent.build()` gọi `_build_evidence_ids()` sinh candidate evidence theo `primary_issue` (ví dụ `late_delivery_seller` thì ưu tiên `seller:`/`item:` của seller vi phạm), rồi lọc qua `schemas.evidence_id_is_grounded()` — hàm này tra ngược `data_loader` (`order_exists`, `item_exists`, `payment_exists`, `seller_exists`) để chỉ giữ id thật, không chỉ đúng regex. `_validate()` sau đó cắt mọi list vượt giới hạn (`MAX_ENTITY_IDS=5`, `MAX_EVIDENCE_IDS=10`, `MAX_ROOT_CAUSES=3`, `MAX_RESPONSIBLE_PARTIES=3`, `MAX_ACTIONS=5`) và log `problems` vào trace thay vì raise lỗi, để không bao giờ thiếu file output.

### Input, output và contract

| Thành phần | Mô tả |
| ------------ | ------- |
| Input | Evidence từ Order & Seller Agent, Payment Agent, Delivery Agent; `policy_version` từ `input/EC_xxx.json` |
| Output | JSON theo đúng schema mục 6 README, ghi vào `output/EC_xxx.json` |
| Module phụ thuộc | Order & Seller Agent, Payment Agent, Delivery Agent |
| Module sử dụng output | Coordinator Agent (ghi file cuối), quy trình chấm điểm |
| Điều kiện lỗi cần xử lý | Evidence ID sai định dạng hoặc không tồn tại trong CSV (false positive); `confidence` ngoài khoảng `[0, 1]`; vượt giới hạn số lượng ID/evidence/cause/action |

### Cách xác minh

```bash
python -m src.run_pipeline
```

- **Kết quả mong đợi:** 50/50 case ra đúng 1 trong 6 `primary_issue`, `confidence` trong `[0,1]`, mọi `evidence_ids` tồn tại thật trong CSV, không list nào vượt giới hạn.
- **Kết quả thực tế:** 50/50 case chạy xong; `logging/trace.jsonl` (550 dòng) có 0 dòng `"level": "warning"` và 0 dòng `"level": "error"` — nghĩa là không case chuẩn nào rơi vào nhánh fallback của Policy Agent hay bị Verifier phát hiện vấn đề (`problems` rỗng ở mọi dòng `verifier_agent.validate`).
- **Artifact/log:** `logging/trace.jsonl` (lọc `agent: "policy_agent"` và `agent: "verifier_agent"`), `output/EC_003.json` (case `canceled_order_paid`).

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Có nên để LLM (`gpt-4o-mini`, không công khai param count) trực tiếp chọn `primary_issue`/số tiền hoàn, hay chỉ để rule engine Python quyết định.
- **Các phương án đã cân nhắc:** (1) Đưa toàn bộ facts vào 1 prompt, để LLM tự chọn `primary_issue`, `refund_brl`, `evidence_ids`; (2) Rule engine Python quyết định 100% các trường bị chấm điểm, LLM chỉ chấm `confidence`/`rationale` trên kết quả đã có.
- **Phương án đã chọn:** Phương án (2).
- **Lý do:** README mục 4 nói rõ 50 case chính thức không mơ hồ — nghĩa là rule engine đủ để giải quyết đúng 100%; để LLM mini tự quyết số tiền/evidence ID có rủi ro hallucinate (sai định dạng, sai số tiền) trong khi các trường này chiếm 85% trọng số chấm điểm (README mục 8). Rủi ro không tương xứng lợi ích.
- **Bằng chứng quyết định phù hợp:** 50/50 case ra kết quả nhất quán 100% với rule table khi tôi dò tay lại theo `assessment.primary_issue` và bảng README mục 4 (ví dụ mọi case `order_status=canceled` + payment>0 đều ra đúng `canceled_order_paid`); `confidence` trung bình 0.93-0.96, không có case confidence thấp bất thường.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Không phải crash — mà là câu hỏi: nếu `order_id` không tồn tại trong CSV, `evidence_ids` có nên vẫn chứa `order:<id>` (id khách cung cấp) hay phải loại bỏ vì "không dựng được từ dữ liệu" (README mục 5)?
- **Lệnh hoặc bước tái hiện:** Test thủ công case giả `claimed_order_id="ORDER_ID_KHONG_TON_TAI"` qua `coordinator_agent.process_case()`, in `output["evidence_ids"]`.
- **Nguyên nhân gốc:** `_build_evidence_ids()` ban đầu luôn thêm `schemas.evidence_order(order_id)` vào candidate list không điều kiện — nếu không lọc lại, evidence "khống" (order không tồn tại) sẽ lọt ra file, vi phạm đúng định nghĩa false positive ở README mục 5.
- **Cách xử lý:** Không sửa `_build_evidence_ids()` (vẫn thêm candidate như cũ, code đơn giản hơn) mà xử lý ở bước lọc chung: mọi candidate đều phải qua `schemas.evidence_id_is_grounded()` trước khi được giữ lại, hàm này tra `data_loader.order_exists()` nên tự động loại `order:ORDER_ID_KHONG_TON_TAI`.
- **Cách xác minh sau khi sửa:** Chạy lại case giả — output thực tế chỉ còn `evidence_ids: ["policy:DELIVERY_WITHIN_ESTIMATE"]` (1 phần tử), không còn `order:ORDER_ID_KHONG_TON_TAI`; `verifier_agent.validate` log `problems: []` (không báo lỗi vì evidence_ids không rỗng), pipeline không crash và vẫn ghi file bình thường.
- **Điều học được:** Bộ lọc "grounded" nên áp dụng đồng nhất cho mọi loại evidence ở 1 điểm chốt chặn duy nhất (Verifier), thay vì để từng agent tự quyết định có nên thêm evidence hay không — dễ nhất quán và dễ audit hơn.

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

1. Tôi là 2 bước cuối chuỗi: Policy Agent nhận facts từ 3 agent domain (order/seller, payment, delivery), áp `EC_POLICY_V1` để chọn `primary_issue`; Verifier Agent nhận quyết định đó, build JSON đầy đủ, lọc/cắt theo giới hạn rồi mới cho Coordinator ghi ra `output/EC_xxx.json`.
2. Evidence ID và root-cause code là "chữ ký" chứng minh kết luận của tôi không phải suy diễn — mỗi `cause_code` tôi gán phải khớp đúng nhánh rule đã kích hoạt, và mỗi evidence ID phải trỏ về dòng dữ liệu thật (tôi tự kiểm bằng `evidence_id_is_grounded`); nếu tôi gán `cause_code` không khớp điều kiện thật, root cause 15% và evidence 15% đều sai theo README mục 8.
3. Đây chính là phần việc chính của tôi: ngoài parse schema, tôi cắt số lượng theo 5 giới hạn cứng, ép `confidence` về `[0,1]`, và quan trọng nhất là gọi lại `data_loader` để xác nhận từng evidence ID tồn tại thật trong CSV — không chỉ đúng regex `order:/item:/payment:/seller:/policy:`.
4. Dùng chung 50 case + 1 `policy_version` để bảng luật tôi áp là cố định cho tất cả — nếu đổi version giữa chừng, cùng 1 bộ facts có thể ra `primary_issue` khác nhau ở hai lần chạy, không thể tổng hợp điểm.
5. Một case đúng khi cả 6 trường trong output khớp README mục 8 (đặc biệt 3 trường tôi trực tiếp quyết: primary_issue/confidence 20%, root cause/responsible parties 15%, evidence 15% — tổng 50%). Tôi đã xác minh tầng hệ thống: 0/550 dòng trace là warning/error, `confidence` toàn bộ 50 case nằm trong 0.93-0.96 (không case nào rơi fallback thấp), nghĩa là rule engine áp được cho toàn bộ 50 case chuẩn mà không cần nhánh dự phòng.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Lê Thị Yến Nhi
**Ngày xác nhận:** 2026-08-05
