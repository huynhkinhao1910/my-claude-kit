---
name: feature-docs
description: Template for per-feature technical documentation written after a feature ships — Vietnamese body, English technical terms kept verbatim, describes the shipped diff. Use when writing docs/features/<slug>/feature-doc.md. Do NOT use for specs, ADRs or MR descriptions.
---

# Feature Docs

Viết tiếng Việt, giữ nguyên thuật ngữ kỹ thuật tiếng Anh (controller, queue, job, migration, endpoint, index, cache, AC…). Mô tả cái đã ship theo diff, không phải plan.

## Template
````markdown
# <Tên tính năng>
- Slug · MR · Ngày release · Owner

## 1. Tóm tắt
<2–3 câu: làm gì, cho ai, giá trị>

## 2. Luồng nghiệp vụ
```mermaid
sequenceDiagram
```

## 3. Thay đổi kỹ thuật
| Layer | File | Thay đổi |
|-------|------|----------|
### Database — migration, index (phục vụ query nào), backfill
### API
| Method | Endpoint | Request | Response | Error codes |
### Jobs / Events / Config / Env mới

## 4. Acceptance criteria → Test
| AC | Test |

## 5. Vận hành
- Deploy steps, feature flag, rollback
- Monitoring / log keys

## 6. Khác với plan ban đầu
## 7. Known limitations / Tech debt
````
