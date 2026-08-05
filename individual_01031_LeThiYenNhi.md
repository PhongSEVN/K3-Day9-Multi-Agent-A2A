# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung             |
| --------------- | --------------------- |
| Họ và tên       | Lê Thị Yến Nhi          |
| MSSV            | 2A202601031            |
| Khóa/Lớp        | K3                     |
| Vai trò chính   | Policy Agent + Verifier Agent |
| Ngày hoàn thành | [YYYY-MM-DD]           |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------- | -------------------- | ---------------- | ------------------ | ------------ |
| Policy Agent — áp bảng quy tắc `EC_POLICY_V1` (mục 4 README) theo thứ tự ưu tiên để chọn `primary_issue`, `responsible_parties`, `refund`, `resolution_actions` | `src/agents/policy_agent.py` | Evidence tổng hợp từ Order & Seller Agent, Payment Agent, Delivery Agent | `assessment`, `root_cause_analysis`, `financial_resolution.recommended_refund_brl`, `resolution_actions` | Chưa hoàn thành |
| Verifier Agent — kiểm tra evidence ID đúng định dạng và tồn tại trong CSV, số tiền làm tròn 2 chữ số, giới hạn số lượng ID/evidence/root cause/action theo mục 6 README, trước khi ghi `output/EC_xxx.json` | `src/agents/verifier_agent.py` | Bản nháp output từ Policy Agent | File `output/EC_xxx.json` đã qua kiểm chứng, hoặc lỗi trả về Coordinator | Chưa hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ---------- | ------------------------------- | --------- |
| [Debug/tích hợp/tài liệu] | [Tên hoặc module] | [Kết quả và bằng chứng] |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| ----------------------- | ------------------------------ | ------------------- | --------------- |
| [Mô tả cụ thể] | [Đường dẫn file] | [Artifact/metrics/report] | [Lệnh/artifact] |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

[Mô tả artifact, metric, report hoặc kết quả tích hợp — ví dụ: phát hiện evidence ID sai định dạng bị Verifier chặn trước khi ghi file.]

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Hệ thống phải ưu tiên dữ liệu có thể kiểm chứng thay vì tin hoàn toàn lời khiếu nại hoặc tự suy diễn sự kiện không tồn tại (Olist không có refund ledger, tracking checkpoint theo item...). Policy Agent áp đúng thứ tự ưu tiên 6 loại `primary_issue` trong README; Verifier Agent là chốt chặn cuối để evidence ID không hợp lệ / vượt giới hạn số lượng / sai số tiền không lọt ra file output (tránh hard gate 0 điểm).

### Cách triển khai

[Mô tả cách Policy Agent duyệt bảng quy tắc theo đúng thứ tự ưu tiên (canceled/unavailable trước, rồi late_delivery_seller, late_delivery_logistics, valid_split_payment, unsupported_late_claim), cách Verifier đối chiếu từng evidence ID ngược lại CSV gốc và áp giới hạn tối đa 5 ID/entity, 10 evidence, 3 root cause, 3 responsible parties, 5 actions.]

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
[Ghi lệnh thực tế đã chạy]
```

- **Kết quả mong đợi:** [Mô tả.]
- **Kết quả thực tế:** [Mô tả.]
- **Artifact/log:** [Đường dẫn; không chứa secret.]

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** [Ví dụ: cách xử lý khi Verifier phát hiện evidence không hợp lệ — reject toàn case hay tự sửa lại.]
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

**Họ và tên:** Lê Thị Yến Nhi
**Ngày xác nhận:** [YYYY-MM-DD]
