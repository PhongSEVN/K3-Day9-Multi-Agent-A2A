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
| Order & Seller Agent — tra `orders`/`order_items`/`sellers` qua `DataStore`, tính `order_status`, `item_total`, `freight_total`, `seller_ids`, seller nào bàn giao trễ | `src/agents/order_seller_agent.py` (`OrderSellerAgent.run()`) | `order_id` (từ Coordinator) | `OrderSellerFacts` (dataclass trong `src/policy_rules.py`) chuyển cho Payment Agent và Policy Agent | Hoàn thành |
| Quy tắc xác định seller vi phạm mốc bàn giao khi order có nhiều item | So `order_delivered_carrier_date` (order-level) với `shipping_limit_date` (item-level) trong `OrderSellerAgent.run()` | Từng dòng `order_items` của order | `late_seller_ids` — danh sách seller vi phạm, dùng để Policy Agent chọn `late_delivery_seller` vs `late_delivery_logistics` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ---------- | ------------------------------- | --------- |
| Đối chiếu evidence/entity logic với nhánh git của Hoàng | Toàn nhóm | Xác nhận `seller_ids` trong entity phải không điều kiện, chỉ evidence mới lọc theo seller vi phạm — cùng kết luận độc lập, giúp nhóm tự tin chọn thiết kế cuối |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| ----------------------- | ------------------------------ | ------------------- | --------------- |
| Tra order EC_001 (`e2a03ccf5ea816036608b2d8c3ab8e60`), phát hiện seller bàn giao muộn | `src/agents/order_seller_agent.py` | `late_seller_ids = ["f7496d659ca9fdaf323c0aae84176632"]` | `python run_pipeline.py` rồi mở `output/EC_001.json` |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Case `EC_001.json` (khách báo "giao trễ"): item duy nhất trong đơn có `carrier_after_limit = True` (carrier nhận hàng sau `shipping_limit_date` của chính item đó) → seller `f7496d659ca9fdaf323c0aae84176632` vào `late_seller_ids`. Policy Agent dùng danh sách này để kết luận `primary_issue = "late_delivery_seller"` thay vì đổ lỗi logistics, `responsible_parties = [("seller", "f7496d659ca9fdaf323c0aae84176632")]` — khớp `output/EC_001.json` thực tế (đã tự chạy lại xác nhận).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Không thể kết luận trách nhiệm chỉ từ nội dung khiếu nại của khách. Order & Seller Agent phải xác định trạng thái đơn thực tế (`canceled`/`unavailable`/`delivered`...), tổng tiền item + freight, và **từng seller** có bàn giao đúng hạn `shipping_limit_date` của chính item họ bán hay không — đây là fact then chốt để Policy Agent phân biệt lỗi seller vs lỗi logistics ở bước sau.

### Cách triển khai

`OrderSellerAgent.run(case_id, store, order_id)`: `store.get_order(order_id)` trả `None` nếu không có → set `order_found=False`, dừng sớm, không tính gì thêm (không crash). Nếu có order: lấy `order_delivered_carrier_date` (1 giá trị chung cho cả đơn), rồi lặp từng dòng `store.get_items(order_id)` — với mỗi item, `carrier_after_limit = pd.notna(carrier_date) and pd.notna(shipping_limit_date) and carrier_date > shipping_limit_date` (guard `pd.notna` để tránh so sánh với giá trị rỗng khi đơn chưa giao). `seller_ids` gom theo thứ tự xuất hiện (không trùng lặp), `late_seller_ids` chỉ thêm seller có ít nhất 1 item vi phạm. Kết quả trả về là dataclass `OrderSellerFacts` (không phải dict) — dùng type an toàn hơn, các agent sau truy cập qua thuộc tính (`order_facts.item_total`) thay vì tra key dict dễ gõ sai.

### Input, output và contract

| Thành phần | Mô tả |
| ------------ | ------- |
| Input | `order_id` (từ Coordinator), đọc `orders`/`order_items` qua `DataStore` (`src/data_store.py`) |
| Output | `OrderSellerFacts(order_found, order_status, items, seller_ids, late_seller_ids, item_total, freight_total)` |
| Module phụ thuộc | `src/data_store.py` (đọc CSV), `src/coordinator.py` (gọi vào) |
| Module sử dụng output | Payment Agent (cần `item_total`/`freight_total`), Policy Agent (cần cả 7 field), `output_builder.py` (build `affected_entities`) |
| Điều kiện lỗi cần xử lý | `order_id` không có trong `orders.csv` → `order_found=False`, mọi field khác về mặc định rỗng; order không có item row → `items=[]`, `item_total=freight_total=0.0` (đúng README mục 6, không coi là lỗi) |

### Cách xác minh

```bash
python run_pipeline.py
```

- **Kết quả mong đợi:** Case có `order_id` hợp lệ trả đúng `order_status`, `seller_ids` không rỗng khi order có item, `late_seller_ids` chỉ chứa seller thực sự vi phạm.
- **Kết quả thực tế:** Tự chạy lại 50/50 case không lỗi; 8 case ra `late_delivery_seller` đều có đúng 1 seller trong `late_seller_ids`, khớp thủ công khi tra `order_items.csv` theo `order_id` của `EC_001`.
- **Artifact/log:** `output/EC_001.json`, dòng `agent: "order_seller_agent"` trong `logging/trace.jsonl` (event `tool_result` + `llm_note`).

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** `affected_entities.seller_ids` (mô tả mọi seller thuộc order) và evidence `seller:<id>` (chứng minh cho kết luận) — ban đầu định dùng chung 1 danh sách `late_seller_ids` cho cả hai.
- **Các phương án đã cân nhắc:** (1) Dùng `late_seller_ids` (seller vi phạm) cho cả `affected_entities.seller_ids` lẫn evidence; (2) Tách 2 khái niệm: `affected_entities.seller_ids` luôn là toàn bộ `seller_ids` của order (không điều kiện), còn evidence `seller:` chỉ lấy từ `late_seller_ids` khi `primary_issue == "late_delivery_seller"`.
- **Phương án đã chọn:** (2).
- **Lý do:** Test thật cho thấy scope `seller_ids` theo lỗi ở **cả** entities lẫn evidence làm điểm Entity rớt mạnh (94.43 → 77.93, theo log trong `architecture.md`) — vì `affected_entities` mô tả "đơn hàng có seller nào", không phải "ai có lỗi", nên phải giữ đầy đủ không điều kiện; chỉ evidence (chứng minh quyết định cụ thể) mới nên lọc theo lỗi.
- **Bằng chứng quyết định phù hợp:** Sau khi tách đúng 2 khái niệm, điểm Entity phục hồi 94.43 và tổng điểm cuối đạt 100.00/100 (nộp thật, ghi trong `architecture.md` mục 2.2).

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Không phải crash — là câu hỏi thiết kế: nếu `claimed_order_id` không có trong `orders.csv`, agent phải trả gì để không làm Payment/Policy Agent phía sau lỗi khi truy cập thuộc tính?
- **Lệnh hoặc bước tái hiện:** Gọi thử `OrderSellerAgent().run(case_id, store, "ORDER_ID_KHONG_TON_TAI")`.
- **Nguyên nhân gốc:** `store.get_order()` trả `None` khi không tìm thấy; nếu để các agent sau tự `.get(...)` trên `None` sẽ crash `AttributeError`.
- **Cách xử lý:** `OrderSellerFacts` là dataclass có default rỗng cho mọi field (`items=[]`, `seller_ids=[]`...) nhờ `field(default_factory=list)`; khi `order is None`, trả thẳng `OrderSellerFacts(order_found=False, order_status=None)` — các field còn lại tự nhận default, agent sau luôn nhận được object hợp lệ (không phải `None`), chỉ cần kiểm `order_found` khi cần phân biệt.
- **Cách xác minh sau khi sửa:** Test case giả `claimed_order_id` không tồn tại chạy hết pipeline không crash, `output` vẫn ghi ra với `order_ids=[]` (vì `order_facts.order_found=False`).
- **Điều học được:** Dùng `dataclass` với default rõ ràng cho contract giữa các agent an toàn hơn dict tự do — agent sau không cần đoán key nào có/không có, tất cả field luôn tồn tại với giá trị mặc định hợp lý.

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

1. Coordinator lấy `claimed_order_id` đưa cho tôi tra ra `OrderSellerFacts`; Payment Agent dùng `item_total`/`freight_total` của tôi để đối soát; Delivery Agent tự đọc `orders` độc lập, không cần fact của tôi. Policy Agent gộp cả 3 nguồn (facts của tôi quan trọng nhất để phân biệt seller vs logistics), `output_builder.py` build entity/evidence, Verifier kiểm tra rồi Coordinator mới ghi `output/EC_xxx.json`.
2. Evidence `seller:<id>` chỉ hợp lệ khi seller đó thật sự nằm trong `late_seller_ids` tôi tính VÀ case đang là `late_delivery_seller` — nếu tôi tính sai (seller không vi phạm vẫn bị đưa vào `late_seller_ids`), root-cause code `SELLER_HANDOFF_AFTER_LIMIT` và evidence sẽ sai theo, mất điểm cả 2 tiêu chí (30% tổng trọng số).
3. Verifier tra ngược từng evidence ID vào `DataStore` (không chỉ đúng regex `seller:<id>`) — và quan trọng: nếu phát hiện vấn đề, Verifier **raise lỗi khiến case bị loại khỏi `output/`** hoàn toàn, không phải chỉ log cảnh báo rồi vẫn ghi file.
4. Dùng chung 50 case + `EC_POLICY_V1` để mốc "bàn giao trễ" được tính nhất quán (cùng phép so `carrier_date > shipping_limit_date`) cho toàn bộ case, không lệch chuẩn giữa các lần chạy hay giữa các nhánh code khác nhau của nhóm.
5. Case thuộc phần tôi (`late_delivery_seller`) đúng khi `order_status`, `seller_ids`, `late_seller_ids` khớp thật với CSV — tự đối chiếu tay `EC_001` xác nhận seller `f7496d659ca9fdaf323c0aae84176632` đúng có `shipping_limit_date` bị vượt; nhóm đã nộp thật và đạt **100.00/100** trên nhánh `main`.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phạm Khánh Linh
**Ngày xác nhận:** 2026-08-05
