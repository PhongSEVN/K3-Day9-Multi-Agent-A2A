# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung             |
| --------------- | --------------------- |
| Họ và tên       | Nguyễn Văn Phong       |
| MSSV            | 2A202601241            |
| Khóa/Lớp        | K3                     |
| Vai trò chính   | Coordinator Agent       |
| Ngày hoàn thành | 2026-08-05           |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------- | -------------------- | ---------------- | ------------------ | ------------ |
| Coordinator Agent — nhận case, điều phối handoff giữa Order&Seller / Payment / Delivery / Policy / Verifier Agent, tổng hợp kết quả cuối | `src/agents/coordinator_agent.py` | 1 file `input/EC_xxx.json` + kết quả trung gian từ các agent con | JSON cuối theo schema output (sau khi Verifier ký duyệt) | Hoàn thành |
| Orchestration pipeline chạy toàn bộ 50 case, quản lý logging/trace | `src/run_pipeline.py`, `src/trace_logger.py` | 50 file `input/EC_001.json` → `EC_050.json` | 50 file `output/EC_xxx.json`, `logging/trace.jsonl` đầy đủ | Hoàn thành |
| Quản lý repo chung, `logging/metadata.json`, đảm bảo `.env`/source code tách khỏi zip nộp | `logging/metadata.json`, `.gitignore`, `.env.example` | Cấu hình model, framework, runtime | `metadata.json` khai đúng tên model (`gpt-4o-mini`), ghi chú param size | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ---------- | ------------------------------- | --------- |
| [Debug/tích hợp/tài liệu] | [Tên hoặc module] | [Kết quả và bằng chứng] |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| ----------------------- | ------------------------------ | ------------------- | --------------- |
| Chạy pipeline điều phối 5 agent cho toàn bộ 50 case, ghi output + trace | `src/run_pipeline.py` | `python -m src.run_pipeline` | 50/50 file `output/EC_xxx.json`, `logging/trace.jsonl` 550 dòng | `python -c "import json,glob; [json.load(open(f,encoding='utf-8')) for f in glob.glob('output/EC_*.json')]"` — không lỗi |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

`logging/trace.jsonl` dòng `case_id=EC_001` ghi đủ chuỗi handoff: `coordinator_agent.case_start` → `order_seller_agent.lookup` → `payment_agent.reconcile` → `delivery_agent.compare_timing` → `policy_agent.rule_decision` → `verifier_agent.validate` → `coordinator_agent.case_end`, kết quả cuối `output/EC_001.json` có `primary_issue: "late_delivery_seller"`, `recommended_refund_brl: 12.04`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Coordinator Agent chịu trách nhiệm nhận từng case input, gọi lần lượt (hoặc song song) các agent chuyên trách domain (order/seller, payment, delivery), thu thập bằng chứng (evidence) họ trả về, chuyển cho Policy Agent áp `EC_POLICY_V1`, rồi chuyển kết quả cho Verifier Agent kiểm tra trước khi ghi ra `output/EC_xxx.json`. Vấn đề cốt lõi: đảm bảo luồng handoff có thứ tự, không để một agent tự suy diễn toàn bộ kết luận.

### Cách triển khai

`coordinator_agent.process_case()` gọi tuần tự (không song song) 5 hàm: `order_seller_agent.analyze()` → `payment_agent.analyze()` → `delivery_agent.analyze()` → `policy_agent.decide()` → `verifier_agent.build()`. Mỗi hàm nhận dict kết quả của bước trước làm tham số (không agent nào tự đọc lại CSV mà agent trước đã đọc), và tự ghi 1-2 dòng vào `trace_logger` (raw lookup/reconcile + `llm_finding`). Nếu `order_seller_agent` không tìm thấy `claimed_order_id` trong `orders.csv`, coordinator vẫn truyền `order = {}` xuống các agent sau thay vì dừng pipeline, để không bao giờ thiếu file output cho 1 case.

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
python -m src.run_pipeline
python -c "import json,glob; n=[json.load(open(f,encoding='utf-8')) for f in sorted(glob.glob('output/EC_*.json'))]; print(len(n))"
```

- **Kết quả mong đợi:** Đúng 50 file `output/EC_001.json`..`EC_050.json`, mỗi file parse JSON không lỗi, `logging/trace.jsonl` có log cho cả 50 case.
- **Kết quả thực tế:** Console in `Done: 50/50 cases written to .../output`; script parse 50 file không lỗi (in ra `50`); `logging/trace.jsonl` 550 dòng (50 case × 11 sự kiện/case), 0 dòng `"level": "warning"`, 0 dòng `"level": "error"`.
- **Artifact/log:** `output/EC_001.json`..`EC_050.json`, `logging/trace.jsonl`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Chọn cách điều phối giữa các agent domain (Order & Seller, Payment, Delivery) — chạy tuần tự hay song song trước khi vào Policy Agent.
- **Các phương án đã cân nhắc:** (1) Chạy song song 3 agent domain rồi gộp kết quả (giảm latency vì có gọi LLM); (2) Chạy tuần tự, mỗi agent nhận thẳng output của agent trước làm input.
- **Phương án đã chọn:** Tuần tự (Order & Seller → Payment → Delivery → Policy → Verifier).
- **Lý do:** Delivery Agent cần `seller_violations` do Order & Seller Agent tính (để phân biệt `late_delivery_seller` vs `late_delivery_logistics`), nên có phụ thuộc dữ liệu thật, không độc lập hoàn toàn. Tuần tự cũng cho `trace.jsonl` thứ tự sự kiện rõ ràng, dễ debug trong khung thời gian thi giới hạn hơn là quản lý state đồng bộ giữa các luồng song song.
- **Bằng chứng quyết định phù hợp:** Chạy thật 50 case không có case nào bị thiếu field do race condition; `trace.jsonl` mỗi case có đúng 1 khối 11 sự kiện liên tục theo đúng thứ tự agent.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**

  ```text
  Traceback (most recent call last):
    File "...\src\run_pipeline.py", line 11, in <module>
      from . import trace_logger
  ImportError: attempted relative import with no known parent package
  ```

- **Lệnh hoặc bước tái hiện:** `python src/run_pipeline.py` (chạy trực tiếp file, từ thư mục gốc repo).
- **Nguyên nhân gốc:** Toàn bộ module trong `src/` dùng relative import (`from . import ...`, `from .. import ...`) để dùng chung `data_loader`/`llm_client`/`trace_logger` giữa `src/` và `src/agents/`. Khi chạy `python src/run_pipeline.py` như 1 script rời, Python không coi `src` là package nên relative import thất bại.
- **Cách xử lý:** Thêm `src/__init__.py` và `src/agents/__init__.py`, quy định chạy pipeline bằng `python -m src.run_pipeline` từ thư mục gốc repo (đã ghi trong docstring đầu file `run_pipeline.py`).
- **Cách xác minh sau khi sửa:** Chạy `python -m src.run_pipeline` → in đủ 50 dòng `EC_xxx.json -> <primary_issue> (confidence=...)` và dòng cuối `Done: 50/50 cases written to .../output`.
- **Điều học được:** Package Python dùng relative import bắt buộc phải chạy bằng `-m` từ thư mục cha, không thể chạy trực tiếp file con — cần ghi rõ trong docstring/README nội bộ để đồng đội không gặp lại lỗi này.

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

1. `run_pipeline.py` đọc lần lượt 50 file trong `input/`, mỗi file gọi `coordinator_agent.process_case()`. Coordinator lấy `claimed_order_id` đưa cho Order & Seller Agent (tra `orders`/`order_items`/`sellers`), đưa `items` cho Payment Agent (tra `order_payments`, đối soát tổng), đưa `order` + `seller_violations` cho Delivery Agent (so sánh timestamp), rồi đưa toàn bộ facts cho Policy Agent (áp bảng quy tắc `EC_POLICY_V1`) và cuối cùng Verifier Agent (build JSON, cắt giới hạn, lọc evidence không grounded) trước khi tôi ghi ra `output/EC_xxx.json`.
2. Evidence ID (`order:`, `item:`, `payment:`, `seller:`, `policy:`) phải trỏ đúng về dòng dữ liệu thật trong CSV — Verifier Agent dùng `schemas.evidence_id_is_grounded()` để loại bỏ id sai định dạng hoặc không tồn tại (false positive) trước khi ghi file, nên khi chấm điểm có thể đối chiếu ngược từng evidence với CSV gốc để biết tôi có "bịa" hay không.
3. Ngoài parse đúng schema, Verifier còn cắt số lượng theo giới hạn (tối đa 5 entity/set, 10 evidence, 3 root cause, 3 responsible party, 5 action), ép `confidence` về `[0,1]`, kiểm số tiền không âm — và quan trọng nhất là gọi lại `data_loader` để xác nhận từng evidence ID tồn tại thật, không chỉ đúng regex.
4. Dùng chung 50 case và `policy_version = EC_POLICY_V1` để mọi thành viên/agent áp cùng 1 bảng luật, kết quả có thể so sánh và tổng hợp được giữa các lần chạy — nếu mỗi lần chạy dùng policy khác nhau thì không thể đối chiếu tay hay chấm điểm nhất quán.
5. Case được coi là xử lý đúng khi: JSON hợp lệ theo schema, `primary_issue`/`confidence` đúng bảng quy tắc, `affected_entities` đầy đủ và đúng giới hạn, `root_cause`/`responsible_parties` khớp cause code, `evidence_ids` grounded, và `financial_resolution`/`resolution_actions` khớp số tiền tính từ CSV — đúng 6 tiêu chí trọng số ở README mục 8. Với 50 case đã chạy, tôi xác minh tầng hệ thống (đủ 50 file, JSON hợp lệ, trace sạch); độ đúng nghiệp vụ chi tiết từng case do các bạn giữ agent domain tương ứng tự đối chiếu tay.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Văn Phong
**Ngày xác nhận:** 2026-08-05
