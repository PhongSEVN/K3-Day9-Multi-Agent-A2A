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
| Payment Agent — đối soát `order_payments.csv` với tổng item + freight từ `order_items.csv` | `src/agents/payment_agent.py` | `order_id` + `items[]` (từ Order & Seller Agent) + `data/olist_order_payments_dataset.csv` | dict `payments[]`, `item_total_brl`, `freight_total_brl`, `payment_total_brl`, `reconciled` chuyển cho Policy Agent | Hoàn thành |
| Tính `financial_resolution` (đầu vào thô, chưa quyết định refund) | Hàm `analyze()` trong `payment_agent.py`, làm tròn 2 chữ số thập phân bằng `round(..., 2)` | Payment rows + item rows theo order | Số liệu tài chính dùng để Verifier build `financial_resolution` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ---------- | ------------------------------- | --------- |
| [Debug/tích hợp/tài liệu] | [Tên hoặc module] | [Kết quả và bằng chứng] |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| ----------------------- | ------------------------------ | ------------------- | --------------- |
| Đối soát payment case EC_004 (2 dòng payment) | `src/agents/payment_agent.py` | `order_id` từ case EC_004 | `item_total_brl=179.9`, `freight_total_brl=32.06`, `payment_total_brl=211.96`, `reconciled=true` | `python -m src.run_pipeline` rồi mở `output/EC_004.json` |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Case `EC_004.json` (khách hỏi "nhiều dòng thanh toán, sợ bị thu trùng"): order có 2 payment row, tổng `payment_value = 211.96` khớp `item_total (179.9) + freight_total (32.06) = 211.96` với sai số 0 BRL (≤ 0.10 theo README) → `reconciled=True`. Policy Agent dùng cờ này kết luận `primary_issue = "valid_split_payment"`, `recommended_refund_brl = 0.0`, `action = "explain_valid_split_payment"` — đúng ý nghĩa "không phải bị thu trùng, chỉ là trả góp nhiều dòng khớp tổng".

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Olist không có refund ledger hay transaction ID, nên Payment Agent phải tự đối soát: tổng `payment_value` theo `order_id` so với tổng giá item + freight. Đây là căn cứ để Policy Agent phân biệt `valid_split_payment` (đơn giao đúng hạn nhưng có nhiều payment row khớp tổng) với các case cần hoàn tiền.

### Cách triển khai

`data_loader.get_payments(order_id)` trả toàn bộ dòng `order_payments.csv` khớp `order_id`, sắp theo `payment_sequential`. `payment_agent.analyze()` tính `item_total = round(sum(price), 2)`, `freight_total = round(sum(freight_value), 2)` từ `items` do Order & Seller Agent đưa sang, `payment_total = round(sum(payment_value), 2)` từ các dòng payment, rồi so `abs(payment_total - (item_total + freight_total)) <= 0.10` (hằng số `RECONCILE_TOLERANCE_BRL = 0.10` đúng README mục 4) để set cờ `reconciled`. Việc build evidence ID `payment:<order_id>:<payment_sequential>` để Verifier Agent làm ở bước cuối dựa trên danh sách `payments[]` tôi trả về, tránh 2 module tự sinh ID trùng logic nhưng lệch dữ liệu.

### Input, output và contract

| Thành phần | Mô tả |
| ------------ | ------- |
| Input | `order_id` (từ Coordinator/Order & Seller Agent), `olist_order_payments_dataset.csv`, `olist_order_items_dataset.csv` |
| Output | `payment_ids`, `item_total_brl`, `freight_total_brl`, `payment_total_brl`, cờ đối soát (khớp/không khớp trong sai số 0.10 BRL) |
| Module phụ thuộc | Order & Seller Agent (cung cấp item list/`order_id` hợp lệ) |
| Module sử dụng output | Policy Agent (áp `valid_split_payment` hoặc tính `recommended_refund_brl`), Verifier Agent |
| Điều kiện lỗi cần xử lý | Order không có payment row; order không có item row (`item_total_brl`, `freight_total_brl` = `0.0` theo mục 6 README) |

### Cách xác minh

```bash
python -m src.run_pipeline
```

- **Kết quả mong đợi:** Case có ≥2 payment row và tổng khớp trong 0.10 BRL phải ra `valid_split_payment`, refund 0; case số tiền không khớp hoặc giao trễ phải rẽ nhánh khác.
- **Kết quả thực tế:** 50/50 case chạy xong; 9 case (`EC_004, EC_006, EC_014, EC_018, EC_020, EC_025, EC_030, EC_038, EC_046`) ra `primary_issue = "valid_split_payment"`, `recommended_refund_brl = 0.0`, đúng số payment ≥ 2 dòng khi tôi tra tay `order_payments.csv` cho `EC_004`.
- **Artifact/log:** `output/EC_004.json`, dòng `agent: "payment_agent"` trong `logging/trace.jsonl`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cách so khớp `payment_total_brl` với `item_total_brl + freight_total_brl` khi có nhiều payment row — vì payment/price là số thực (float), so bằng tuyệt đối (`==`) dễ sai do sai số dấu phẩy động.
- **Các phương án đã cân nhắc:** (1) So bằng tuyệt đối sau khi `round(..., 2)` cả hai vế; (2) Tính hiệu tuyệt đối `abs(payment_total - expected_total)` và so với ngưỡng dung sai `0.10` BRL như README quy định.
- **Phương án đã chọn:** Phương án (2) — `abs(payment_total - expected_total) <= 0.10`.
- **Lý do:** README mục 4 quy định rõ "sai số 0.10 BRL", tức đây không phải so khớp tuyệt đối mà là dung sai nghiệp vụ (làm tròn installment, phí phát sinh nhỏ); so bằng tuyệt đối sau `round` vẫn có thể trượt nếu 2 vế lệch đúng 0.01-0.09 BRL hợp lệ, sẽ bị coi nhầm là "không khớp".
- **Bằng chứng quyết định phù hợp:** Case `EC_004`: `payment_total_brl=211.96` so `item_total_brl+freight_total_brl=211.96` — hiệu 0.0, nằm trong ngưỡng, `reconciled=True`, khớp đúng kỳ vọng.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Không phải crash mà là 1 hành vi cạnh cần kiểm tra: khi order không có item lẫn payment row (`item_total=freight_total=payment_total=0.0`), công thức `abs(0 - 0) <= 0.10` cho `reconciled=True` một cách "tình cờ", có thể bị hiểu nhầm là case đã đối soát thành công.
- **Lệnh hoặc bước tái hiện:** Test thủ công case giả `claimed_order_id="ORDER_ID_KHONG_TON_TAI"` qua `coordinator_agent.process_case()`, xem `payment_agent` log trong `logging/trace.jsonl`.
- **Nguyên nhân gốc:** `reconciled` chỉ là điều kiện cần (README rule 5 còn yêu cầu `len(payments) >= 2`), nên `Policy Agent` không tự nhận case rỗng là `valid_split_payment` — nhưng bản thân cờ `reconciled=True` khi rỗng vẫn có thể gây hiểu nhầm nếu đọc riêng log `payment_agent` mà không đọc `policy_agent`.
- **Cách xử lý:** Xác nhận với Nhi (Policy Agent) rằng rule 5 luôn kiểm thêm `len(payments) >= 2` trước khi dùng `reconciled`, nên trường hợp rỗng tự động rơi xuống rule 6 (`unsupported_late_claim`) chứ không bị nhận nhầm — không cần sửa `payment_agent.py`, chỉ cần ghi rõ điều kiện phụ thuộc này trong `architecture.md` (mục 5, dòng "Payment Agent") để tránh member khác hiểu nhầm ý nghĩa cờ `reconciled` khi đọc riêng.
- **Cách xác minh sau khi sửa:** Chạy lại case giả — `logging/trace.jsonl` cho thấy `payment_agent.reconcile` log `reconciled: true` với `payment_count: 0`, nhưng `policy_agent.rule_decision` vẫn ra `primary_issue: "unsupported_late_claim"` (không phải `valid_split_payment`) vì thiếu điều kiện `len(payments) >= 2` — đúng như thiết kế.
- **Điều học được:** Một cờ boolean đơn lẻ (`reconciled`) không nên được đọc/diễn giải độc lập khỏi điều kiện đi kèm của nó trong rule engine; cần ghi rõ trong tài liệu để tránh member khác dùng lại cờ này sai ngữ cảnh.

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

1. Sau khi Order & Seller Agent xác định `items`, tôi lấy `order_id` đó tra `order_payments.csv`, tính 3 tổng (item/freight/payment) và cờ `reconciled`, đưa cho Delivery Agent (không cần dữ liệu của tôi) và Policy Agent (cần cả 3 tổng + cờ) để chọn `primary_issue`; cuối cùng Verifier đóng gói `financial_resolution` từ đúng 3 số tôi tính, không tính lại.
2. Evidence `payment:<order_id>:<payment_sequential>` chỉ hợp lệ nếu dòng payment đó thật sự tồn tại trong `order_payments.csv` — Verifier gọi lại `data_loader.payment_exists()` để xác nhận, nên nếu tôi generate sai `payment_sequential` (ví dụ đánh số từ 0 thay vì 1 như CSV gốc) thì evidence sẽ bị loại, ảnh hưởng trực tiếp điểm evidence 15%.
3. Verifier còn kiểm số tiền không âm và làm tròn đúng 2 chữ số — quan trọng với phần của tôi vì `item_total_brl`/`freight_total_brl`/`payment_total_brl` đều do tôi tính, sai làm tròn ở đây kéo sai luôn `recommended_refund_brl` (20% trọng số).
4. Cùng `policy_version = EC_POLICY_V1` đảm bảo ngưỡng dung sai 0.10 BRL tôi dùng để đối soát là thống nhất cho cả 50 case — nếu policy đổi ngưỡng giữa các lần chạy, cùng 1 case có thể lúc `reconciled=True` lúc `False`, không tái lập được.
5. Case thuộc phần của tôi (`valid_split_payment`, `unsupported_late_claim`, hoặc refund tính từ freight/payment) đúng khi 3 số `item_total_brl/freight_total_brl/payment_total_brl` khớp CSV gốc — tôi đã đối chiếu tay case `EC_004`: 2 dòng payment 174.98 + 36.98 (tổng 211.96) khớp `item_total (179.9) + freight_total (32.06)`.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Thanh Phúc
**Ngày xác nhận:** 2026-08-05
