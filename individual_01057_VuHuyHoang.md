# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung             |
| --------------- | --------------------- |
| Họ và tên       | Vũ Huy Hoàng            |
| MSSV            | 2A202601057            |
| Khóa/Lớp        | K3                     |
| Vai trò chính   | Delivery Agent          |
| Ngày hoàn thành | [YYYY-MM-DD]           |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------- | -------------------- | ---------------- | ------------------ | ------------ |
| Delivery Agent — so sánh `order_delivered_customer_date` với `order_estimated_delivery_date`, so sánh `order_delivered_carrier_date` với `shipping_limit_date` | `src/agents/delivery_agent.py` | `order_id` + timestamp từ `data/olist_orders_dataset.csv`, `shipping_limit_date` từ `olist_order_items_dataset.csv` | Cờ giao trễ (`late_delivery`), phân loại nguyên nhân ứng viên: `late_delivery_seller` vs `late_delivery_logistics` | Chưa hoàn thành |
| Sinh root-cause code liên quan giao hàng (`SELLER_HANDOFF_AFTER_LIMIT`, `CARRIER_DELIVERED_AFTER_ESTIMATE`, `DELIVERY_WITHIN_ESTIMATE`) | Hàm phân loại trong `delivery_agent.py` | Kết quả so sánh timestamp | Root-cause candidate chuyển cho Policy Agent | Chưa hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ---------- | ------------------------------- | --------- |
| [Debug/tích hợp/tài liệu] | [Tên hoặc module] | [Kết quả và bằng chứng] |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| ----------------------- | ------------------------------ | ------------------- | --------------- |
| [Mô tả cụ thể] | [Đường dẫn file] | [Artifact/metrics/report] | [Lệnh/artifact] |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

[Mô tả artifact, metric, report hoặc kết quả tích hợp — ví dụ: phân biệt giao trễ do seller vs logistics cho case EC_014.]

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Cùng một phản ánh "giao trễ" nhưng trách nhiệm khác nhau tùy timestamp thực tế: nếu carrier nhận hàng sau `shipping_limit_date` thì seller chịu trách nhiệm; nếu carrier nhận đúng hạn nhưng giao khách vẫn trễ so với `order_estimated_delivery_date` thì logistics chịu trách nhiệm; nếu giao không muộn hơn ước tính thì claim có thể bị bác bỏ (`unsupported_late_claim`).

### Cách triển khai

[Mô tả cách so sánh timestamp CSV không đổi múi giờ, cách xử lý order nhiều item/nhiều seller khi xác định carrier nhận hàng muộn theo seller nào, cách trả kết quả về root-cause candidate đúng thứ tự ưu tiên trong bảng quy tắc README mục 4.]

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
[Ghi lệnh thực tế đã chạy]
```

- **Kết quả mong đợi:** [Mô tả.]
- **Kết quả thực tế:** [Mô tả.]
- **Artifact/log:** [Đường dẫn; không chứa secret.]

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** [Ví dụ: cách phân định seller vs logistics khi cả hai điều kiện gần ranh giới thời gian.]
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

**Họ và tên:** Vũ Huy Hoàng
**Ngày xác nhận:** [YYYY-MM-DD]
