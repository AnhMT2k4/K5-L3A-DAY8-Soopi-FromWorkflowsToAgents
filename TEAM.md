# Team

## Thông tin nhóm

- Tên nhóm: Soopi
- Lớp: L3A
- Repo nhóm: `K5-L3A-DAY8-Soopi-FromWorkflowsToAgents` (xem [SUBMISSION.md](SUBMISSION.md))
- URL repo, nhánh nộp, commit chốt: https://github.com/AnhMT2k4/K5-L3A-DAY8-Soopi-FromWorkflowsToAgents, main

## Thành viên

| STT | Họ tên | MSSV | Email | GitHub | Vai trò |
| --: | ------ | ---- | ----- | ------ | ------- |
|   1 | Mai Tuấn Anh | 2A202603574 | maituananh1511@gmail.com | https://github.com/AnhMT2k4 | Workflow + Integration |
|   2 | Nguyễn Đức Đạt | 2A202603544 | nguyenducdat298@gmail.com | https://github.com/nguyenducdat298 | Viết báo cáo (Eval, ADR, Research Card, Group Report) |
|   3 | Nguyễn Hữu Tiến | 2A202603598 | tiennh2026@gmail.com | https://github.com/tiennh2026 | Orchestrator + Sub-agents |

Gợi ý chia vai:

- Nhóm 6 người: integration; workflow; single agent; orchestrator; ledger/policy/crash; eval/report.
- Nhóm 4 người: workflow + integration; single; orchestrator + handoff; ledger + evaluation.

## Bảng đóng góp

`python -m lab8.check_submission` đọc bảng này bằng máy: giữ nguyên tiêu đề `## Bảng đóng góp` và các cột. Mỗi người một dòng: commit có nội dung và ít nhất một test đã thêm hoặc sửa.

| Người | Vai | Commit | Test đã thêm hoặc sửa |
| --- | --- | --- | --- |
| Mai Tuấn Anh | workflow + integration | 38c08ef | src/tests/test_workflow.py |
| Nguyễn Đức Đạt | Viết báo cáo & Đánh giá | e90ae65 | src/tests/test_public_matrix.py, src/tests/test_authorization.py |
| Nguyễn Hữu Tiến | orchestrator | 4d56c70 | src/tests/test_orchestrator.py |

## Cá nhân

Mỗi thành viên đồng thời tạo một báo cáo riêng trong `report/` theo dạng:

```text
report/team/MSSV_HoTen.md
```

Ví dụ: `report/team/20241234_NguyenVanAn.md`.

Sao chép mục dưới đây cho từng thành viên.

## 2A202603544_NguyenDucDat

### Phần việc phụ trách

- Phụ trách nghiên cứu, đánh giá thực nghiệm và viết toàn bộ hệ thống báo cáo (Group Report, ADR, Research Card, Báo cáo cá nhân).
- Phân tích và đối chiếu số đo thực nghiệm từ kết quả benchmark (pass rate, seed variance, cost per success).

### Đóng góp cụ thể

- Viết báo cáo nhóm hoàn chỉnh 8 mục theo chuẩn Rubric: `report/team/group_report.md`.
- Viết tài liệu quyết định kiến trúc: `report/team/decision_adr.md` dựa trên số liệu thực nghiệm benchmark 4 shape x 5 seed.
- Viết phiếu nghiên cứu khoa học: `report/team/research_card.md` giải quyết bài toán R2 (Failure Taxonomy) theo paper NeurIPS 2025.
- Viết báo cáo cá nhân: `report/team/2A202603544_NguyenDucDat.md`.
- Tham gia chạy thử nghiệm, phân tích số liệu benchmark và crash test để đưa vào các tài liệu báo cáo.

### Bằng chứng

- Commit hash: e90ae65
- 248/248 tests passed trong `python -m pytest -q -m student -o addopts=`
- 20/20 crash safety trong `python -m lab8.crash_test --count 20 --out reports/crash.json`
