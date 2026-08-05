# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung             |
| --------------- | --------------------- |
| Họ và tên       | Nguyễn Thanh Phúc       |
| MSSV            | 2A202601345            |
| Khóa/Lớp        | K3                     |
| Vai trò chính   | Payment Agent           |
| Ngày hoàn thành | 2026-08-05           |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------- | -------------------- | ---------------- | ------------------ | ------------ |
| Payment Agent — tra `order_payments` qua `DataStore`, tính tổng `payment_total`, log so sánh với `item_total+freight_total` để audit | `src/agents/payment_agent.py` (`PaymentAgent.run()`) | `order_id`, `item_total`, `freight_total` (từ Order & Seller Agent) | `PaymentFacts` (dataclass: `payments[]`, `payment_total`) chuyển cho Policy Agent | Hoàn thành |
| Nhánh riêng `feature/payment_agent_phuc` để phát triển/test độc lập trước khi thống nhất dùng nhánh `main` | Git branch, `individual_01345_NguyenThanhPhuc.md` | Code payment agent tự viết | Đã merge kiến thức/đối chiếu vào bản `main` cuối cùng của nhóm | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ---------- | ------------------------------- | --------- |
| Merge nhánh `origin/hoang` vào nhánh của mình để đối chiếu logic Delivery Agent | Hoàng | Xác nhận payment/delivery facts độc lập nhau, không cần sửa gì thêm khi Coordinator gộp |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| ----------------------- | ------------------------------ | ------------------- | --------------- |
| Tính tổng payment case EC_004 (2 dòng payment) | `src/agents/payment_agent.py` | `payment_total = 211.96` | `python run_pipeline.py` rồi mở `output/EC_004.json` |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Case `EC_004.json` (khách hỏi "nhiều dòng thanh toán, sợ bị thu trùng"): order có 2 dòng `order_payments` (174.98 + 36.98 = 211.96). `PaymentAgent.run()` trả `payment_total=211.96`; hàm `_is_reconciled()` trong `policy_rules.py` (Policy Agent gọi, không phải tôi tự tính cờ) so `abs(211.96 - (179.9+32.06)) = 0.0 ≤ 0.10 BRL` → khớp. Policy Agent kết luận `primary_issue="valid_split_payment"`, `recommended_refund_brl=0.0`, `action="explain_valid_split_payment"` — khớp `output/EC_004.json` thực tế.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Olist không có refund ledger hay transaction ID, nên phải tự đối soát: tổng `payment_value` theo `order_id` so với tổng giá item + freight. Đây là căn cứ cho Policy Agent phân biệt `valid_split_payment` (nhiều dòng thanh toán nhưng khớp tổng, không phải thu trùng) khỏi các case cần hoàn tiền thật.

### Cách triển khai

`PaymentAgent.run(case_id, store, order_id, item_total, freight_total)`: `store.get_payments(order_id)` trả toàn bộ dòng payment của order; lặp từng dòng, `value = float(row["payment_value"]) if pd.notna(row["payment_value"]) else 0.0` (guard giá trị thiếu), cộng dồn vào `payment_total`, mỗi dòng làm tròn 2 chữ số ngay khi tạo `PaymentFact`. Điểm quan trọng: **agent của tôi không tự tính cờ "reconciled"** — chỉ trả tổng tiền + danh sách payment thô; việc so khớp `abs(payment_total - (item_total+freight_total)) <= AMOUNT_TOLERANCE_BRL` (hằng số 0.10 trong `src/config.py`) được `_is_reconciled()` trong `policy_rules.py` làm, để logic đối soát nằm 1 chỗ duy nhất (rule engine), Payment Agent chỉ là nguồn dữ liệu thô đáng tin cậy.

### Input, output và contract

| Thành phần | Mô tả |
| ------------ | ------- |
| Input | `order_id`, `item_total`, `freight_total` (từ Order & Seller Agent qua Coordinator), đọc `order_payments` qua `DataStore` |
| Output | `PaymentFacts(payments: list[PaymentFact], payment_total: float)`, có property `payment_count` |
| Module phụ thuộc | `src/data_store.py`, Order & Seller Agent (cần `item_total`/`freight_total` trước) |
| Module sử dụng output | Policy Agent (`_is_reconciled()`, `payment_count >= 2` để xét `valid_split_payment`), `output_builder.py` (build `payment_ids`, `financial_resolution.payment_total_brl`) |
| Điều kiện lỗi cần xử lý | Order không có payment row → `payments=[]`, `payment_total=0.0` (không crash); `payment_value` thiếu/`NaN` ở 1 dòng → tính là `0.0` cho dòng đó, không loại cả dòng |

### Cách xác minh

```bash
python run_pipeline.py
```

- **Kết quả mong đợi:** Case có ≥2 payment row và tổng khớp trong 0.10 BRL phải ra `valid_split_payment`, refund 0.
- **Kết quả thực tế:** Tự chạy lại 50/50 case; 9 case ra `valid_split_payment` với `payment_count >= 2` và `recommended_refund_brl = 0.0`, khớp tay khi tra `order_payments.csv` cho `EC_004` (174.98 + 36.98 = 211.96).
- **Artifact/log:** `output/EC_004.json`, dòng `agent: "payment_agent"` trong `logging/trace.jsonl` (`tool_result` có `payment_total`, `expected_total`).

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Ai chịu trách nhiệm tính cờ "payment có khớp tổng item+freight hay không" — để ngay trong Payment Agent, hay để Policy Agent (rule engine) tính?
- **Các phương án đã cân nhắc:** (1) Payment Agent tự tính và trả sẵn cờ `reconciled: bool`; (2) Payment Agent chỉ trả số liệu thô (`payment_total`, danh sách `payments`), Policy Agent tự so khớp khi cần.
- **Phương án đã chọn:** (2).
- **Lý do:** Ngưỡng dung sai 0.10 BRL là 1 phần của **chính sách** (`EC_POLICY_V1`), không phải sự thật dữ liệu — để nó sống trong `policy_rules.py` cùng các hằng số khác (`AMOUNT_TOLERANCE_BRL` trong `config.py`) giúp toàn bộ logic nghiệp vụ nằm 1 chỗ, dễ audit/đổi version chính sách sau này mà không phải sửa Payment Agent.
- **Bằng chứng quyết định phù hợp:** 50/50 case chạy đúng; log `tool_result` của Payment Agent luôn có `expected_total` để tôi tự đối chiếu tay mà không cần đọc code Policy Agent, tách bạch rõ ràng "tôi cung cấp số liệu" khỏi "ai quyết định số liệu đó nghĩa là gì".

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Không phải crash — câu hỏi cạnh: order không có payment row nào (`payments=[]`, `payment_total=0.0`) thì có bị Policy Agent hiểu nhầm là "khớp tổng" (`0.0 == 0.0`) một cách tình cờ không?
- **Lệnh hoặc bước tái hiện:** Test thủ công `PaymentAgent().run(case_id, store, "ORDER_ID_KHONG_TON_TAI", 0.0, 0.0)`.
- **Nguyên nhân gốc:** `_is_reconciled(0.0, 0.0, 0.0)` thật sự trả `True` (0 ≈ 0) — nhưng đây không phải bug: `valid_split_payment` còn yêu cầu thêm `payment_count >= 2` (trong `policy_rules.decide()`), nên order rỗng (`payment_count=0`) không bao giờ rơi vào nhánh đó, tự động rớt xuống `unsupported_late_claim` hoặc fallback.
- **Cách xử lý:** Xác nhận với Nhi (giữ `policy_rules.py`) rằng điều kiện `payment_count >= 2` luôn đi kèm `_is_reconciled()`, không dùng cờ khớp/không khớp độc lập — không cần sửa `payment_agent.py`.
- **Cách xác minh sau khi sửa:** Test case giả xác nhận `payment_total=0.0` nhưng `primary_issue` không bao giờ là `valid_split_payment` khi `payment_count < 2`.
- **Điều học được:** Một điều kiện toán học đúng cục bộ (`0 == 0`) có thể gây hiểu nhầm nếu tách khỏi điều kiện đi kèm của nó trong rule engine — luôn đọc trọn vẹn nhánh `if` chứ không chỉ 1 biểu thức con.

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

1. Sau khi Order & Seller Agent tính `item_total`/`freight_total`, Coordinator đưa 2 số đó cho tôi cùng `order_id`; tôi tra `order_payments` trả `payment_total` + danh sách dòng payment. Policy Agent nhận cả 3 bộ fact (order/seller, delivery, payment), tự so khớp và ra `primary_issue`; `output_builder.py` build entity/evidence từ đúng dữ liệu tôi trả, Verifier kiểm rồi Coordinator ghi file.
2. Evidence `payment:<order_id>:<seq>` chỉ hợp lệ nếu dòng đó thật sự tồn tại trong `order_payments.csv` — Verifier tra ngược `DataStore.payment_exists()`. Nếu tôi đánh số `payment_sequential` sai so với CSV gốc, evidence bị loại và case bị Verifier raise lỗi, không được ghi ra `output/` — mất điểm evidence (15%) lẫn có thể mất trắng case đó (hard gate).
3. Verifier còn validate toàn bộ payload qua `pydantic` (`CaseOutput`) — số tiền âm, sai kiểu dữ liệu, thiếu field đều bị bắt ở đây; case lỗi sẽ **không** có mặt trong `output/` (khác với thiết kế "ghi kèm cảnh báo" tôi từng thấy ở bản nháp khác của nhóm).
4. Cùng `policy_version=EC_POLICY_V1` đảm bảo ngưỡng dung sai 0.10 BRL thống nhất cho toàn bộ 50 case và giữa các nhánh git khác nhau của nhóm — nếu không, kết quả không thể so sánh khi nhóm đối chiếu điểm giữa các bản.
5. Case thuộc phần tôi đúng khi `payment_total`/`item_total`/`freight_total` khớp CSV gốc — tự đối chiếu tay `EC_004`: 174.98 + 36.98 = 211.96 khớp `179.9 + 32.06`. Nhóm đã nộp thật nhánh `main` và đạt **100.00/100**.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Thanh Phúc
**Ngày xác nhận:** 2026-08-05
