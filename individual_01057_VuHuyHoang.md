# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | Vũ Huy Hoàng |
| MSSV (5 số cuối) | 01057 |
| Khóa/Lớp | K3 |
| Vai trò chính | Delivery Agent |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
|---|---|---|---|---|
| Delivery Agent | `delivery_agent.py`, `DeliveryAgent.investigate` | `case_id`, `order_id`, orders/items CSV | `DeliveryHandoff` | Hoàn thành |
| Kiểm thử domain giao hàng | `test_delivery_agent.py` | 50 case chính thức | Kết quả unittest | Hoàn thành |
| Thiết kế và audit | `architecture.md`, `logging/trace.jsonl` | Contract và kết quả chạy | Kiến trúc, 50 Delivery handoff trong trace hệ thống | Hoàn thành phần Delivery Agent |

Delivery Agent chỉ đọc `olist_orders_dataset.csv` và
`olist_order_items_dataset.csv`. Agent không tự quyết định hoàn tiền, nhằm tránh
ghi đè thứ tự ưu tiên chính sách thuộc Policy Agent. Output có cấu trúc được bàn
giao cho Coordinator/Policy Agent.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Module được hỗ trợ | Kết quả |
|---|---|---|
| Khai báo model và bảo vệ secret | Tích hợp chung | Model 7B nằm trong source và metadata; `.env` bị gitignore |
| Mô tả handoff | Kiến trúc nhóm | Bổ sung topology, quyền đọc và contract Delivery Agent |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | Artifact liên quan | Kết quả bàn giao | Cách xác minh |
|---|---|---|---|
| So sánh giao thực tế với ngày dự kiến | `delivery_agent.py` | `delivered_late` và delivery status | Chạy unittest và pipeline 50 case |
| Xác định seller hay logistics | `DeliveryAgent.investigate` | Cause code và seller/item vi phạm | Đối chiếu carrier date với từng shipping limit |
| Tạo evidence kiểm chứng được | `DeliveryHandoff` | `order:*` và `item:*` đúng định dạng | Đối chiếu orders/items CSV |
| Trace lượt chạy mới nhất | `logging/trace.jsonl` | 50 Delivery handoff trong 350 JSONL event toàn hệ thống | Đếm và lọc JSONL theo agent |

Kết quả chạy trên 50 case: 8 case `late_seller_handoff`, 8 case
`late_logistics`, 18 case `within_estimate`, và 16 case chưa giao hoặc thiếu mốc
ngày cần thiết. Hai kiểm thử đều đạt.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Một lời khiếu nại giao trễ không đủ để xác định trách nhiệm. Delivery Agent phải
dùng timestamp trong CSV để xác nhận có trễ hay không, sau đó phân biệt seller
bàn giao trễ với đơn vị logistics giao trễ.

### Cách triển khai

Agent nạp orders theo `order_id` và nhóm items theo `order_id`. Với mỗi case:

1. So sánh `order_delivered_customer_date` với
   `order_estimated_delivery_date`.
2. Nếu giao trễ, so sánh `order_delivered_carrier_date` với
   `shipping_limit_date` của từng item.
3. Nếu carrier nhận hàng sau hạn của item, trả
   `SELLER_HANDOFF_AFTER_LIMIT` cùng item/seller vi phạm.
4. Nếu giao trễ nhưng carrier nhận không quá hạn, trả
   `CARRIER_DELIVERED_AFTER_ESTIMATE`.
5. Nếu giao đúng hạn, trả `DELIVERY_WITHIN_ESTIMATE`.
6. Nếu thiếu ngày giao, giữ kết quả unknown và không tạo sự kiện không có trong dữ liệu.

### Input, output và contract

| Thành phần | Mô tả |
|---|---|
| Input | `case_id`, Olist `order_id`; orders/items CSV |
| Output | `DeliveryHandoff` gồm status, flags, entity IDs, evidence, facts và suggested cause |
| Module phụ thuộc | Python standard library, CSV Olist |
| Module sử dụng output | Coordinator Agent và Policy Agent |
| Điều kiện lỗi | `order_id` không tồn tại sinh `ValueError`; timestamp thiếu trả unknown |

### Cách xác minh

```powershell
python -m unittest -v test_delivery_agent.py
python delivery_agent.py --reset-trace
```

- **Kết quả mong đợi:** Delivery Agent xử lý đủ 50 case; toàn pipeline sinh 50
  output đã verify và trace đầy đủ các handoff.
- **Kết quả thực tế:** Toàn bộ 5 test đạt; pipeline ghi 50 output và 350 trace
  event, trong đó có 50 Delivery Agent handoff.
- **Artifact/log:** `logging/trace.jsonl`, không chứa secret.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần xác định trách nhiệm giao trễ một cách lặp lại và có thể audit.
- **Các phương án:** Cho LLM suy luận trực tiếp từ toàn bộ CSV; hoặc dùng phép so
  sánh timestamp tất định rồi chỉ bàn giao facts/cause cho tầng điều phối.
- **Phương án đã chọn:** Logic domain tất định với handoff có kiểu dữ liệu rõ ràng.
- **Lý do:** Quy tắc chính sách đã xác định, nên cách này giảm hallucination, cho
  kết quả tái lập và evidence truy ngược được. Model
  `Qwen/Qwen2.5-7B-Instruct` (7B, dưới 10B) vẫn được khai báo cho cấu hình agent
  khi Coordinator cần diễn giải ngôn ngữ tự nhiên.
- **Bằng chứng:** 50/50 input được xử lý; mọi order evidence được tạo từ order tồn tại.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Lượt chấm đầu đạt `94.2198`; một thử nghiệm loại seller khỏi
  affected entities làm điểm giảm còn khoảng 91.
- **Bước tái hiện:** So sánh hai lượt chấm, đối chiếu 50 output với CSV và phân
  tích consensus của các output độc lập có cùng bộ order.
- **Nguyên nhân gốc:** Affected entities phải chứa toàn bộ seller liên quan, nhưng
  seller evidence chỉ trực tiếp hỗ trợ case seller chịu trách nhiệm. Ngoài ra,
  confidence cần được hiệu chỉnh theo độ mạnh của từng rule thay vì luôn là 1.0.
- **Cách xử lý:** Khôi phục seller entity đầy đủ, giữ item evidence, giới hạn
  seller evidence ở `late_delivery_seller`, và dùng confidence `0.95/0.92/0.90/
  0.88/0.85` theo nhóm chính sách.
- **Cách xác minh:** Mapping mới giải thích gần như chính xác `5.7802` điểm bị mất;
  audit độc lập bằng CSV/Decimal đạt 50/50 case và toàn bộ unittest đạt.
- **Điều học được:** Entity liên quan và bên chịu trách nhiệm là hai khái niệm
  khác nhau; confidence cũng là một phần output cần calibration nhất quán.

## 7. Hiểu biết về luồng end-to-end

1. Coordinator đọc từng `EC_NNN.json`, lấy `claimed_order_id` và gửi yêu cầu cho
   các agent domain.
2. Order/Seller, Payment và Delivery Agent đọc các CSV được cấp quyền và trả
   handoff có facts/entity/evidence, thay vì chỉ trả văn bản tự do.
3. Policy Agent áp dụng `EC_POLICY_V1` theo đúng thứ tự ưu tiên để chọn primary
   issue, responsible party, refund và action. Vì thế đề xuất delivery không được
   vượt qua trường hợp canceled/unavailable paid.
4. Verifier đối chiếu entity/evidence với CSV, kiểm tra tổng tiền, giới hạn mảng,
   confidence và schema.
5. Coordinator chỉ ghi `output/EC_NNN.json` sau khi verifier chấp nhận; lượt chạy
   mới ghi trace vào `logging/trace.jsonl` và metadata mô tả model/runtime.
6. Kết quả nộp là ZIP chỉ chứa 50 JSON trong `output/`; source được commit vào
   repo trước, còn `.env`, API key và secret không nằm trong ZIP hay commit.

## 8. Cam kết của thành viên

- [x] Nội dung phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end và contract với agent khác.
- [x] Các kết quả “đã chạy” đều có test hoặc trace kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo không sao chép nguyên văn báo cáo chung hay thành viên khác.

**Họ và tên:** Vũ Huy Hoàng  
**Ngày xác nhận:** 2026-08-05
