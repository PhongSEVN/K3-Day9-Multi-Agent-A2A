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
| Delivery Agent — so sánh `order_delivered_customer_date` với `order_estimated_delivery_date`, tái dùng `seller_violations` để suy ra bên chịu trách nhiệm | `src/agents/delivery_agent.py` | `order` (dict từ Order & Seller Agent) + `seller_violations[]` | `late_delivery` (bool), `late_cause_candidate` chuyển cho Policy Agent | Hoàn thành |
| Phân loại nguyên nhân ứng viên `late_delivery_seller` vs `late_delivery_logistics` | Hàm `analyze()` trong `delivery_agent.py` | Kết quả so sánh timestamp + cờ vi phạm seller | Root-cause candidate (không tự gán `cause_code`, để Policy Agent gán) | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ---------- | ------------------------------- | --------- |
| [Debug/tích hợp/tài liệu] | [Tên hoặc module] | [Kết quả và bằng chứng] |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| ----------------------- | ------------------------------ | ------------------- | --------------- |
| Phân biệt giao trễ do logistics (không phải seller) cho case EC_009 | `src/agents/delivery_agent.py` | `order`, `seller_violations=[]` | `late_delivery=true`, `late_cause_candidate="late_delivery_logistics"` | `python -m src.run_pipeline` rồi mở `output/EC_009.json` |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Case `EC_009.json` (order `3aaee056441dcae251f360b1c71a7279`): `order_delivered_customer_date` muộn hơn `order_estimated_delivery_date`, nhưng Order & Seller Agent không phát hiện seller nào vi phạm `shipping_limit_date` (`seller_violations=[]`) → tôi trả `late_cause_candidate="late_delivery_logistics"`. Policy Agent dùng cờ này ra `primary_issue="late_delivery_logistics"`, `responsible_parties=[{"party_type":"logistics_provider","party_id":"LOGISTICS_PROVIDER"}]`, `recommended_refund_brl=12.36` (đúng bằng `freight_total_brl`) — khớp `output/EC_009.json` thực tế.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Cùng một phản ánh "giao trễ" nhưng trách nhiệm khác nhau tùy timestamp thực tế: nếu carrier nhận hàng sau `shipping_limit_date` thì seller chịu trách nhiệm; nếu carrier nhận đúng hạn nhưng giao khách vẫn trễ so với `order_estimated_delivery_date` thì logistics chịu trách nhiệm; nếu giao không muộn hơn ước tính thì claim có thể bị bác bỏ (`unsupported_late_claim`).

### Cách triển khai

`delivery_agent.analyze()` không tự đọc CSV — nhận thẳng dict `order` (đã có timestamp) từ Order & Seller Agent và `seller_violations` đã tính sẵn. Tôi parse `order_delivered_customer_date`/`order_estimated_delivery_date` bằng `pandas.to_datetime(..., errors="coerce")`, so trực tiếp giá trị (không đổi múi giờ, đúng lưu ý README mục 2) để có `late_delivery`. Nếu `late_delivery=True`, tôi không tự quyết seller/logistics chịu trách nhiệm mà chỉ nhìn `seller_violations`: có phần tử → `late_delivery_seller`, rỗng → `late_delivery_logistics`. Việc gán `cause_code` cụ thể (`SELLER_HANDOFF_AFTER_LIMIT`/`CARRIER_DELIVERED_AFTER_ESTIMATE`) và thứ tự ưu tiên so với `canceled_order_paid`/`unavailable_order_paid` để Policy Agent (Nhi) làm, vì cần biết cả `order_status`/payment mà tôi không có.

### Input, output và contract

| Thành phần | Mô tả |
| ------------ | ------- |
| Input | `order_id` (từ Order & Seller Agent), timestamp từ `olist_orders_dataset.csv` (`order_delivered_customer_date`, `order_estimated_delivery_date`, `order_delivered_carrier_date`), `shipping_limit_date` từ `olist_order_items_dataset.csv` |
| Output | Cờ `late_delivery`, root-cause candidate (`late_delivery_seller` / `late_delivery_logistics` / không có) |
| Module phụ thuộc | Order & Seller Agent (cung cấp item/seller/`shipping_limit_date` theo seller) |
| Module sử dụng output | Policy Agent (chọn `primary_issue`, `responsible_parties`), Verifier Agent |
| Điều kiện lỗi cần xử lý | Thiếu `order_delivered_customer_date` (đơn chưa giao); order nhiều seller với mốc `shipping_limit_date` khác nhau |

### Cách xác minh

```bash
python -m src.run_pipeline
```

- **Kết quả mong đợi:** Case giao trễ có seller vi phạm phải ra `late_delivery_seller`; case giao trễ nhưng seller đúng hạn phải ra `late_delivery_logistics`; case giao đúng/sớm hạn không được gắn cờ trễ.
- **Kết quả thực tế:** 50/50 case chạy xong; 8 case ra `late_delivery_seller`, 8 case (`EC_009, EC_010, EC_012, EC_016, EC_017, EC_031, EC_049, EC_050`) ra `late_delivery_logistics`, không case nào bị gắn `late_delivery=true` sai khi tôi đối chiếu tay timestamp của `EC_009` (`3aaee056441dcae251f360b1c71a7279`).
- **Artifact/log:** `output/EC_009.json`, dòng `agent: "delivery_agent"` trong `logging/trace.jsonl`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** `order_delivered_customer_date` có thể rỗng/`NaN` khi đơn chưa giao (chưa có timestamp thực tế) hoặc khi Order & Seller Agent không tìm thấy order (`order = {}`); so sánh trực tiếp giá trị rỗng với `order_estimated_delivery_date` dễ gây lỗi hoặc kết luận sai.
- **Các phương án đã cân nhắc:** (1) So sánh chuỗi trực tiếp, coi rỗng là "chưa trễ" bằng try/except bao quanh; (2) Parse bằng `pandas.to_datetime(errors="coerce")` rồi guard bằng `pd.notna()` trước khi so sánh.
- **Phương án đã chọn:** Phương án (2) — chỉ kết luận `late_delivery=True` khi cả `delivered_customer` và `estimated` đều `pd.notna()`.
- **Lý do:** try/except nuốt lỗi âm thầm, khó phân biệt "code sai" với "dữ liệu thiếu hợp lệ"; dùng `pd.notna()` tường minh, đơn chưa giao hoặc order không tồn tại tự động rơi về `late_delivery=False` (không bị coi là bằng chứng giao trễ giả) mà không cần try/except.
- **Bằng chứng quyết định phù hợp:** Test case giả `claimed_order_id` không tồn tại (`order={}` được coordinator truyền xuống) chạy qua `delivery_agent.analyze()` không crash, trả đúng `late_delivery: false, late_cause_candidate: null` — xác nhận guard hoạt động đúng với input rỗng thực tế chứ không chỉ trên giấy.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Câu hỏi thiết kế trước khi viết code: nếu Order & Seller Agent trả `order=None` (không tìm thấy `claimed_order_id`), `delivery_agent.analyze(order, ...)` gọi `order.get("order_delivered_customer_date")` trên `None` sẽ crash `AttributeError: 'NoneType' object has no attribute 'get'`.
- **Lệnh hoặc bước tái hiện:** Gọi thử `delivery_agent.analyze(case_id, order_id, None, [])` trực tiếp với `order=None`.
- **Nguyên nhân gốc:** Hàm của tôi giả định luôn nhận được `order` là dict, nhưng Order & Seller Agent có thể trả `None` khi không tìm thấy order trong CSV.
- **Cách xử lý:** Thống nhất với Coordinator (Phong): coordinator luôn chuẩn hoá `order = order_seller["order"] or {}` trước khi gọi `delivery_agent.analyze()`, nên phía tôi chỉ cần nhận `dict` (có thể rỗng), không cần tự xử `None` bên trong `delivery_agent.py`.
- **Cách xác minh sau khi sửa:** Chạy case giả `claimed_order_id="ORDER_ID_KHONG_TON_TAI"` qua `coordinator_agent.process_case()` — không crash, `delivery_agent` log `late_delivery: false, late_cause_candidate: null` với `order={}` được truyền vào.
- **Điều học được:** Contract giữa các agent (agent sau nhận `dict` gì, có thể rỗng nhưng không phải `None`) cần thống nhất ở tầng Coordinator, không nên để mỗi agent tự đoán và tự viết guard `None` rải rác — dễ thiếu sót.

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

1. Tôi là bước thứ 3 trong chuỗi: nhận `order` (từ Order & Seller Agent) và `seller_violations`, so timestamp để ra `late_delivery`/`late_cause_candidate`, đưa cho Policy Agent gộp với kết quả Payment Agent để chọn `primary_issue` cuối, rồi Verifier build JSON và Coordinator ghi `output/EC_xxx.json`.
2. Root-cause code của tôi (`SELLER_HANDOFF_AFTER_LIMIT` hay `CARRIER_DELIVERED_AFTER_ESTIMATE`) phải khớp đúng điều kiện timestamp thật — nếu tôi báo `late_delivery_seller` nhưng thực ra seller giao đúng hạn, evidence `seller:<id>` và `policy:SELLER_HANDOFF_AFTER_LIMIT` sẽ sai theo dữ liệu gốc, bị tính sai ở cả root cause (15%) lẫn evidence (15%).
3. Verifier kiểm confidence, giới hạn số lượng, và quan trọng với phần tôi: đối chiếu `cause_code` tôi/Policy Agent chọn có thật sự tồn tại trong tập 6 mã hợp lệ (`VALID_ROOT_CAUSE_CODES`), không tự bịa mã mới.
4. Dùng chung 50 case + `EC_POLICY_V1` để "trễ" được định nghĩa nhất quán (cùng công thức so `estimated_delivery_date`) cho mọi case, tránh tình trạng case này tính trễ theo cách khác case kia.
5. Case thuộc phần giao hàng (`late_delivery_seller`/`late_delivery_logistics`) đúng khi `late_delivery` khớp thật với 2 mốc thời gian trong CSV và bên chịu trách nhiệm khớp với `seller_violations` — tôi đã đối chiếu tay `EC_009`: giao trễ thật, nhưng seller không vi phạm `shipping_limit_date` nên đúng là lỗi logistics, không phải seller.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Vũ Huy Hoàng
**Ngày xác nhận:** 2026-08-05
