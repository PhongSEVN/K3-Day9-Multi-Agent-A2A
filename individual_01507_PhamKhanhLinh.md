# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung             |
| --------------- | --------------------- |
| Họ và tên       | Phạm Khánh Linh        |
| MSSV            | 2A202601507            |
| Khóa/Lớp        | K3                     |
| Vai trò chính   | Order & Seller Agent    |
| Ngày hoàn thành | [YYYY-MM-DD]           |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------- | -------------------- | ---------------- | ------------------ | ------------ |
| Order & Seller Agent — tra `orders.csv`, `order_items.csv`, `sellers.csv` theo `claimed_order_id`, xác định `order_status`, danh sách item/seller, mốc `shipping_limit_date` | `src/agents/order_seller_agent.py` | `claimed_order_id` từ Coordinator + `data/olist_orders_dataset.csv`, `olist_order_items_dataset.csv`, `olist_sellers_dataset.csv` | Evidence: order status, item list (`item:<order_id>:<n>`), seller list (`seller:<seller_id>`), cờ seller bàn giao muộn | Chưa hoàn thành |
| Quy tắc xác định seller vi phạm khi order có nhiều item | Hàm kiểm tra `order_delivered_carrier_date > shipping_limit_date` theo từng seller trong `order_seller_agent.py` | Item rows theo order | Danh sách seller vi phạm (nếu có), dùng cho `SELLER_HANDOFF_AFTER_LIMIT` | Chưa hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ---------- | ------------------------------- | --------- |
| [Debug/tích hợp/tài liệu] | [Tên hoặc module] | [Kết quả và bằng chứng] |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| ----------------------- | ------------------------------ | ------------------- | --------------- |
| [Mô tả cụ thể] | [Đường dẫn file] | [Artifact/metrics/report] | [Lệnh/artifact] |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

[Mô tả artifact, metric, report hoặc kết quả tích hợp — ví dụ: evidence order/item/seller cho case EC_003.]

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Không thể kết luận trách nhiệm chỉ từ nội dung khiếu nại của khách. Order & Seller Agent phải xác định trạng thái đơn thực tế (`canceled`/`unavailable`/khác), danh sách item và seller liên quan, và mốc `shipping_limit_date` seller phải bàn giao — làm căn cứ cho Delivery Agent và Policy Agent phân biệt trách nhiệm seller vs logistics.

### Cách triển khai

[Mô tả cách join `orders` → `order_items` → `sellers` theo `claimed_order_id`, cách xử lý order nhiều item/nhiều seller, cách sinh evidence ID đúng định dạng `order:<order_id>`, `item:<order_id>:<order_item_id>`, `seller:<seller_id>`.]

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
[Ghi lệnh thực tế đã chạy]
```

- **Kết quả mong đợi:** [Mô tả.]
- **Kết quả thực tế:** [Mô tả.]
- **Artifact/log:** [Đường dẫn; không chứa secret.]

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** [Ví dụ: xử lý order có nhiều seller — quy định seller bị coi bàn giao muộn dựa trên `shipping_limit_date` của item thuộc seller đó, không phải mốc chung cả đơn.]
- **Các phương án đã cân nhắc:** [Ít nhất hai phương án.]
- **Phương án đã chọn:** [Lựa chọn.]
- **Lý do:** [Trade-off về correctness, data quality, reproducibility, cost hoặc độ phức tạp.]
- **Bằng chứng quyết định phù hợp:** [Metric, artifact hoặc kết quả thử nghiệm.]

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** [Che toàn bộ secret trước khi ghi.]
- **Lệnh hoặc bước tái hiện:** [Lệnh/bước.]
- **Nguyên nhân gốc:** [Root cause, không chỉ mô tả triệu chứng.]
- **Cách xử lý:** [Thay đổi cụ thể.]
- **Cách xác minh sau khi sửa:** [Lệnh và kết quả.]
- **Điều học được:** [Bài học kỹ thuật.]

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

[Viết câu trả lời tại đây.]

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [ ] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [ ] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [ ] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [ ] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [ ] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phạm Khánh Linh
**Ngày xác nhận:** [YYYY-MM-DD]
