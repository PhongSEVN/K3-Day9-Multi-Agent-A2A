# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung             |
| --------------- | --------------------- |
| Họ và tên       | Nguyễn Văn Phong       |
| MSSV            | 2A202601241            |
| Khóa/Lớp        | K3                     |
| Vai trò chính   | Coordinator Agent       |
| Ngày hoàn thành | [YYYY-MM-DD]           |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------- | -------------------- | ---------------- | ------------------ | ------------ |
| Coordinator Agent — nhận case, điều phối handoff giữa Order&Seller / Payment / Delivery / Policy / Verifier Agent, tổng hợp kết quả cuối | `src/agents/coordinator_agent.py` | 1 file `input/EC_xxx.json` + kết quả trung gian từ các agent con | Bản ghép JSON theo schema output (trước khi Verifier ký duyệt) | Chưa hoàn thành |
| Orchestration pipeline chạy toàn bộ 50 case, quản lý logging/trace | `src/main.py`, `logging/trace.jsonl` | 50 file `input/EC_001.json` → `EC_050.json` | 50 file `output/EC_xxx.json`, `trace.jsonl` đầy đủ | Chưa hoàn thành |
| Quản lý repo chung, `metadata.json`, đảm bảo `.env`/source code tách khỏi zip nộp | `metadata.json`, `.gitignore` | Cấu hình model, framework, runtime | `metadata.json` khai đúng tên model, param size | Chưa hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ---------- | ------------------------------- | --------- |
| [Debug/tích hợp/tài liệu] | [Tên hoặc module] | [Kết quả và bằng chứng] |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| ----------------------- | ------------------------------ | ------------------- | --------------- |
| [Mô tả cụ thể] | [Đường dẫn file] | [Artifact/metrics/report] | [Lệnh/artifact] |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

[Mô tả artifact, metric, report hoặc kết quả tích hợp — ví dụ: log điều phối handoff giữa các agent cho case EC_001.]

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Coordinator Agent chịu trách nhiệm nhận từng case input, gọi lần lượt (hoặc song song) các agent chuyên trách domain (order/seller, payment, delivery), thu thập bằng chứng (evidence) họ trả về, chuyển cho Policy Agent áp `EC_POLICY_V1`, rồi chuyển kết quả cho Verifier Agent kiểm tra trước khi ghi ra `output/EC_xxx.json`. Vấn đề cốt lõi: đảm bảo luồng handoff có thứ tự, không để một agent tự suy diễn toàn bộ kết luận.

### Cách triển khai

[Mô tả cách điều phối: tuần tự hay có state machine, cách truyền evidence giữa agent, cách xử lý lỗi/agent trả kết quả thiếu.]

### Input, output và contract

| Thành phần | Mô tả |
| ------------ | ------- |
| Input | `input/EC_xxx.json` theo schema: `case_id`, `opened_at`, `customer_request.claimed_order_id`, `policy_version` |
| Output | `output/EC_xxx.json` theo schema mục 6 README (assessment, affected_entities, root_cause_analysis, evidence_ids, financial_resolution, resolution_actions) |
| Module phụ thuộc | Order & Seller Agent, Payment Agent, Delivery Agent, Policy Agent, Verifier Agent |
| Module sử dụng output | Verifier Agent (kiểm tra cuối), quy trình nộp bài (zip `output/`) |
| Điều kiện lỗi cần xử lý | `claimed_order_id` không tồn tại trong `orders.csv`; agent con timeout hoặc trả evidence sai định dạng |

### Cách xác minh

```bash
[Ghi lệnh thực tế đã chạy]
```

- **Kết quả mong đợi:** [Mô tả.]
- **Kết quả thực tế:** [Mô tả.]
- **Artifact/log:** [Đường dẫn; không chứa secret.]

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** [Vấn đề hoặc lựa chọn cần quyết định — ví dụ: điều phối tuần tự vs song song giữa các agent con.]
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

**Họ và tên:** Nguyễn Văn Phong
**Ngày xác nhận:** [YYYY-MM-DD]
