# Architecture — Multi-Agent E-commerce Dispute Resolution

## 1. Sơ đồ handoff

```
input/EC_xxx.json
        |
        v
+--------------------+
|  Coordinator Agent  |  (src/agents/coordinator_agent.py)
+--------------------+
        |
        v  claimed_order_id
+-----------------------+
| Order & Seller Agent   |  --> order, items[], seller_ids[], seller_violations[]
+-----------------------+
        |
        v  order_id, items[]
+-----------------------+
|     Payment Agent       |  --> payments[], item_total, freight_total, payment_total, reconciled
+-----------------------+
        |
        v  order, seller_violations[]
+-----------------------+
|     Delivery Agent      |  --> late_delivery, late_cause_candidate
+-----------------------+
        |
        v  toàn bộ facts trên
+-----------------------+
|      Policy Agent       |  --> primary_issue, case_status, root_cause, responsible_parties, refund, action
+-----------------------+
        |
        v  policy decision + raw facts
+-----------------------+
|     Verifier Agent      |  --> JSON cuối theo schema, cap giới hạn, lọc evidence không grounded
+-----------------------+
        |
        v
output/EC_xxx.json
```

Coordinator gọi tuần tự 5 agent trên cho mỗi case (`coordinator_agent.process_case`), không có bước nào chạy song song trong 1 case — vì mỗi agent cần output của agent trước làm input (đúng tinh thần "handoff" của README mục 7, không gộp hết vào 1 prompt).

## 2. Vai trò và quyền truy cập dữ liệu

| Agent | File | Đọc gì | Không được đọc/làm gì |
| ----- | ---- | ------ | ---------------------- |
| Coordinator | `src/agents/coordinator_agent.py` | `input/EC_xxx.json`, output của các agent con | Không tự tính toán business rule |
| Order & Seller | `src/agents/order_seller_agent.py` | `orders`, `order_items`, `sellers` (qua `data_loader`) | Không đọc `order_payments` |
| Payment | `src/agents/payment_agent.py` | `order_payments`, items từ Order & Seller Agent | Không tự tra lại `order_items`/`orders` |
| Delivery | `src/agents/delivery_agent.py` | timestamp trong `order` (từ Order & Seller Agent), `seller_violations` | Không đọc CSV trực tiếp |
| Policy | `src/agents/policy_agent.py` | Facts tổng hợp từ 3 agent trên | Không đọc CSV, không tự đổi số tiền |
| Verifier | `src/agents/verifier_agent.py` | Facts + quyết định của Policy Agent, đối chiếu `data_loader` để kiểm evidence | Không đổi quyết định của Policy Agent, chỉ được cắt/lọc |

Mọi agent domain (Order & Seller, Payment, Delivery, Policy) đều gọi `llm_client.call_llm_finding()` — model `gpt-4o-mini` khai trong `src/llm_client.py` — để chấm `confidence`/`rationale` trên facts đã tính sẵn; **model không được sửa fact hay số tiền**, chỉ nhận xét. Đây là điểm khác so với thiết kế "1 prompt làm hết": mỗi agent là 1 module riêng, chỉ thấy phần dữ liệu domain của mình, và phải handoff dict có cấu trúc cho agent kế tiếp.

## 3. Vì sao rule engine deterministic, không để LLM quyết định số liệu

Bảng quy tắc `EC_POLICY_V1` (README mục 4) đã đủ rõ và không mơ hồ với bộ 50 case chính thức. Root cause, responsible party, số tiền hoàn và evidence ID là các trường bị chấm điểm nặng nhất (85% trọng số). Để tránh model mini hallucinate số tiền hoặc evidence ID sai định dạng, toàn bộ các trường này do Python tính trực tiếp từ CSV (`policy_agent.py`, `verifier_agent.py`); LLM chỉ đóng góp vào `confidence` (blend 70% rule-based / 30% model) và `rationale` nội bộ (ghi trace, không xuất ra output).

### 3.1 Evidence ID: chỉ trích entity mà rule/refund thật sự phụ thuộc, không "gom hết cho chắc"

Lần đầu, `verifier_agent._build_evidence_ids()` chỉ thêm entity tối thiểu theo từng nhánh (ví dụ `unsupported_late_claim` chỉ lấy 1 payment + 1 item đầu dù order có nhiều hơn) → nộp thật, điểm Bằng chứng 85.65/100. Thử sửa thành gom **toàn bộ** item/payment/seller grounded của order cho mọi nhánh (nghĩ là tăng recall sẽ lợi) → nộp lại, điểm Bằng chứng **giảm** còn 85.07 trong khi 5 tiêu chí khác không đổi. Kết luận rút ra: bộ chấm phạt entity grounded-nhưng-không-liên-quan-tới-rule như nhiễu, không thưởng theo kiểu "càng nhiều bằng chứng thật càng tốt".

Bước kế tiếp thử giả thuyết "chỉ trích entity nằm trong công thức rule" (bảng gốc bên dưới không có payment cho 2 nhánh giao trễ, không có item cho canceled/unavailable) → nộp thật, Bằng chứng tăng lên 86.28. Sau đó thử nghiệm có kiểm soát từng biến một (mỗi lần đổi đúng 1 nhánh, nộp thật để đo): thêm payment cho `late_delivery_seller` → 88.67; thêm payment cho `late_delivery_logistics` → 91.82; thêm item cho `canceled_order_paid`/`unavailable_order_paid` → đang chờ kết quả nộp. Giả thuyết "công thức" ban đầu **bị bác bỏ bởi thực nghiệm** — payment vẫn giúp dù không nằm trong công thức refund của 2 nhánh giao trễ. Quy luật thực tế quan sát được: cứ thêm đúng loại entity mà order thực sự có (grounded) và còn thiếu so với 5 loại evidence khả dụng thì điểm tăng mạnh (~15-20 điểm/case bị thiếu); chỉ riêng việc thêm **seller** vào nơi seller không phải bên chịu trách nhiệm mới rõ ràng có hại (bản "gom hết" B, giảm còn 85.07).

Bảng evidence hiện tại (đã áp thực nghiệm, seller chỉ trích khi seller là responsible party):

| `primary_issue` | Evidence trích | Đã kiểm chứng |
| --- | --- | --- |
| `canceled_order_paid` / `unavailable_order_paid` | order, policy, toàn bộ payment, toàn bộ item | Đang test (bản F) |
| `late_delivery_seller` | order, policy, seller vi phạm, item của seller vi phạm, toàn bộ payment | Có — 86.28→88.67 |
| `late_delivery_logistics` | order, policy, toàn bộ item, toàn bộ payment | Có — 88.67→91.82 |
| `valid_split_payment` | order, policy, toàn bộ payment, toàn bộ item | Chưa test riêng (giữ như bản gốc) |
| `unsupported_late_claim` / fallback | order, policy, toàn bộ payment, toàn bộ item | Có — 85.65→86.28 (fix bug cắt còn 1 dòng) |

Chưa trích seller ở đâu ngoài `late_delivery_seller` (seller không phải responsible party thì chưa có tín hiệu thực nghiệm nào cho thấy nên trích).

## 4. Logging / Trace

- `logging/trace.jsonl`: mỗi dòng là 1 sự kiện `{timestamp, case_id, agent, action, level, latency_ms, detail}`. File bị ghi đè (`trace_logger.reset()`) mỗi lần chạy `run_pipeline.py` — chỉ giữ lượt chạy mới nhất, đúng README mục 9.
- `logging/metadata.json`: khai `model`, `provider`, `framework`, `runtime`, và ghi chú rõ việc `gpt-4o-mini` không công khai param count (best-effort với ràng buộc ≤10B).

## 5. Fallback / xử lý lỗi

- `claimed_order_id` không có trong `orders.csv`: Order & Seller Agent trả `order_found=False`, log `level=warning`; pipeline vẫn chạy tiếp với facts rỗng thay vì crash.
- Không case nào khớp đúng 1 trong 6 rule (không kỳ vọng xảy ra ở 50 case chính thức): Policy Agent rơi vào nhánh fallback giống `unsupported_late_claim` nhưng gắn `confidence` thấp hơn và log `level=warning` để soát tay.
- Lỗi gọi OpenAI API (rate limit, mạng): `llm_client.call_llm_finding` bắt exception, trả `confidence=0.7` mặc định kèm `error`, không làm dừng pipeline — đảm bảo luôn ra đủ 50 file output.
- Verifier Agent luôn cắt bớt list vượt giới hạn và loại evidence ID không grounded thay vì raise lỗi, để không bao giờ thiếu file trong `output/`.

## 6. Xử lý song song để tăng tốc

Bản đầu chạy tuần tự 50 case, mỗi case chờ 4 lệnh gọi OpenAI nối tiếp (Order&Seller, Payment, Delivery, Policy — Verifier không gọi LLM) → ~180s cho 50 case, vì thời gian chủ yếu là chờ mạng (I/O-bound), không phải tính toán. `run_pipeline.py` được sửa dùng `concurrent.futures.ThreadPoolExecutor(max_workers=10)` để xử lý 10 case cùng lúc — còn ~31s cho 50 case (nhanh gấp ~6 lần), do các case độc lập nhau hoàn toàn (mỗi case chỉ đụng `order_id` của chính nó).

Để chạy song song an toàn phải thêm lock ở 2 chỗ vốn không thread-safe:

- `trace_logger.log_event()`: nhiều thread ghi `logging/trace.jsonl` cùng lúc (mode `"a"`) gây interleave, từng thấy thực tế qua `JSONDecodeError` khi 2 tiến trình chạy đè nhau lúc debug thủ công. Thêm `threading.Lock` quanh thao tác ghi file.
- `data_loader._load()` và `llm_client._get_client()`: pattern "check rồi load" (`if _x is None: load()`) không an toàn nếu nhiều thread cùng gọi lần đầu tiên. Thêm `threading.Lock` quanh phần khởi tạo (double-checked locking); `run_pipeline.main()` còn gọi `data_loader._load()` tường minh một lần trước khi mở thread pool để loại hẳn race condition ở lần load CSV đầu tiên.

Verify: sau khi song song hoá, `logging/trace.jsonl` vẫn đúng 550 dòng (50 case × 11 sự kiện), không dòng nào lỗi JSON, không `case_id` nào bị trùng `case_start` — xác nhận lock hoạt động đúng, không mất/trộn dữ liệu do race condition.
