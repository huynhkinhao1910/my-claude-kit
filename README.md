# My Claude Kit

Bộ agent, skill, command, rules và hook cá nhân cho **Claude Code**, được thiết kế và tuỳ biến theo đúng stack và cách làm việc của mình:

- **Backend:** PHP/Laravel, Go, TypeScript/NestJS, trên MySQL, Redis và RabbitMQ
- **Frontend:** Vue 3 / Nuxt, React / Next.js
- **Quy trình:** pipeline `/feature` (spec → plan → TDD → verify → review → ship qua GitLab MR), đường nhanh `/quick` và `/debug` cho việc nhỏ
- **Chất lượng:** Laravel house style, một API contract thống nhất, scalability, lớp an toàn (chặn secret và lệnh phá hoại), tự học theo project (instincts)

---

## Mục lục

1. [Cài đặt](#1-cài-đặt)
2. [Dùng hằng ngày: gặp việc gì thì gọi gì](#2-dùng-hằng-ngày-gặp-việc-gì-thì-gọi-gì)
3. [Pipeline `/feature`](#3-pipeline-feature)
4. [Đường nhanh: `/quick`, `/debug`, `/code-review`](#4-đường-nhanh-quick-debug-code-review)
5. [Danh mục command](#5-danh-mục-command-28)
6. [Danh mục agent](#6-danh-mục-agent-25)
7. [Danh mục skill](#7-danh-mục-skill-39)
8. [Rules](#8-rules)
9. [House style và API contract](#9-house-style-và-api-contract)
10. [Scalability](#10-scalability)
11. [Continuous learning](#11-continuous-learning)
12. [Lớp an toàn](#12-lớp-an-toàn)
13. [Cấu trúc repo](#13-cấu-trúc-repo)
14. [Tự custom kit](#14-tự-custom-kit)
15. [Xử lý sự cố](#15-xử-lý-sự-cố)
16. [Giấy phép và ghi nhận](#16-giấy-phép-và-ghi-nhận)

---

## 1. Cài đặt

### Yêu cầu

| Công cụ | Bắt buộc | Dùng cho |
|---------|----------|----------|
| `bash`, `git`, `python3` | ✅ | installer, hooks, continuous learning |
| `jq` | ✅ | `guard.sh` và `post-edit-format.sh`. **Thiếu `jq` thì guard không chặn được gì**, installer sẽ cảnh báo |
| `glab` (đã chạy `glab auth login`) | cho `/ship` | mở GitLab MR. Thiếu thì `/ship` chỉ in MR description ra |
| `claude` CLI | cho observer | observer tự học chạy bằng Haiku (mặc định tắt) |
| `composer`/`pint`, `node`/`tsc`, `go`/`golangci-lint` | theo project | để `/verify`, `/quick`, `/build-fix` chạy được bước kiểm tra |

```bash
brew install jq glab golangci-lint    # macOS
glab auth login
```

### Máy mới (nhà hoặc công ty)

```bash
git clone https://github.com/huynhkinhao1910/my-claude-kit.git ~/my-claude-kit
cd ~/my-claude-kit
./install.sh --dry-run      # xem trước: file nào được cài, rules nào bị dọn, hooks/deny sẽ thành gì
./install.sh                # cài thật
```

Cài xong thì **khởi động lại Claude Code**.

| Lệnh | Khi nào dùng |
|------|--------------|
| `./install.sh` | Cài đầy đủ: file, hooks, rule deny, `CLAUDE.md` global |
| `./install.sh --no-hooks` | Chỉ copy file, không đụng `settings.json`. Hợp với máy công ty có chính sách chặt |
| `./install.sh --no-claude-md` | Giữ `~/.claude/CLAUDE.md` riêng của máy đó |
| `./install.sh --dry-run` | Xem trước, không ghi gì |

**Installer làm gì:**
- **Backup trước khi ghi:** mọi file bị ghi đè được chuyển vào `~/.claude/.backup/my-claude-kit-<thời gian>/`. `settings.json` được backup thành `settings.json.bak-<thời gian>` mỗi khi có thay đổi.
- **Rules:** cài vào `~/.claude/rules/my-claude-kit/`. Bản cũ của cùng rules nằm ở `rules/ecc/` hoặc `rules/` phẳng, cùng với `zh/` và các file `README.md` hướng dẫn của ECC, được chuyển vào backup để không bị nạp 2 lần. Rules không thuộc kit (`angular`, `python`…) được giữ nguyên.
- **Hooks:** `guard.sh`, `post-edit-format.sh`, `observe.sh`, `inject-instincts.py` được đăng ký vào `settings.json`. Entry cũ trỏ tới `~/.claude/hooks/guard.sh` được thay thế. Hook riêng của bạn được giữ nguyên.
- **Permissions:** rule deny của kit được gộp vào `permissions.deny`. Rule `allow`/`deny` riêng của bạn được giữ nguyên.

| Biến môi trường | Mặc định | Ý nghĩa |
|-----------------|----------|---------|
| `CLAUDE_DIR` | `~/.claude` | Thư mục cài |
| `RULES_NS` | `my-claude-kit` | Thư mục con của rules |
| `LEGACY_RULES_NS` | `ecc .` | Các namespace cũ cần dọn (`.` là thư mục `rules/` gốc) |
| `RETIRE_DUPLICATES` | `zh README.md` | Mục trùng lặp cần dọn thêm. Đặt `""` để giữ lại |

### Cập nhật

```bash
cd ~/my-claude-kit && git pull && ./install.sh
```

Sửa kit **trong repo này**, đừng sửa thẳng `~/.claude`, vì lần cài sau sẽ ghi đè. Sửa ở máy nào thì commit và push từ máy đó, máy kia `git pull` rồi cài lại.

### Gỡ bỏ

```bash
python3 scripts/merge-settings.py --remove   # gỡ hook của kit, giữ permissions
rm -rf ~/.claude/hooks/my-claude-kit ~/.claude/rules/my-claude-kit
# khôi phục file cũ nếu cần: ~/.claude/.backup/my-claude-kit-<thời gian>/
```

---

## 2. Dùng hằng ngày: gặp việc gì thì gọi gì

| Tình huống | Gọi | Ghi chú |
|------------|-----|---------|
| Tính năng mới, thay đổi lớn, có endpoint/bảng/migration mới | `/feature <slug> <yêu cầu>` | 4 cổng duyệt, toàn bộ tài liệu nằm trong `docs/features/<slug>/` |
| Fix bug hoặc sửa nhỏ (≤ ~3 file, không đổi contract, không đụng auth/payment) | `/quick <mô tả>` | 1 cổng duyệt trước khi commit, tự đề nghị lên `/feature` nếu việc lớn hơn |
| Có lỗi nhưng chưa rõ nguyên nhân (500, timeout, flaky, sai dữ liệu) | `/debug <triệu chứng>` | Chứng minh nguyên nhân gốc trước, sau đó mới sửa qua `/quick` |
| Muốn review thay đổi đang làm trước khi commit | `/code-review` hoặc `/code-review main` | Chỉ đọc, in kết quả ngay trong chat |
| Build, type hoặc lint đỏ | `/build-fix` | Tự chọn resolver đúng stack |
| Chạy toàn bộ cổng chất lượng | `/verify` | format → static analysis → test → lint |
| Dọn dead code sau khi ship | `/refactor-clean` | Xóa theo từng đợt đã duyệt, test xanh sau mỗi đợt |
| Hết giờ, việc còn dở | `/save-session`, rồi mai `/resume-session` | Lưu vào `~/.claude/session-data/` |
| Quyết định kiến trúc ảnh hưởng nhiều module | nhờ agent `architect` | Ghi ADR vào `docs/adr/` |
| Endpoint hoặc job sẽ chịu tải | nhắc tới "scale" hoặc "chịu tải", hay dùng agent `scalability-reviewer` | Skill `scalability` |
| Xem Claude đã học được gì ở project này | `/instinct-status` | Xem [mục 11](#11-continuous-learning) |

Không cần gọi skill bằng tay. Claude tự nạp skill theo ngữ cảnh: sửa file `.php` thì nạp `laravel-patterns`, nói "viết test" thì nạp `laravel-tdd`, nói "lỗi" thì nạp `debugging`.

---

## 3. Pipeline `/feature`

```
/feature order-refund "Cho phép khách hoàn tiền đơn trong 7 ngày"

 1 Spec ──▶ Gate 1 ──▶ 2 Plan ──▶ Gate 2 ──▶ 3 Implement ──▶ 4 Verify ──▶ 5 Review ──▶ Gate 3 ──▶ 6 Ship ──▶ Final gate
 requirement-          code-explorer          test-writer →      /verify      reviewers theo         doc-writer
 analyst               + planner              implementer        (phải xanh)  loại file, chạy        + glab MR draft
                                              (1 commit/task)                 song song
```

| Phase | Command | Agent | File tạo ra | Cổng |
|-------|---------|-------|-------------|------|
| 1 Spec | `/spec <slug> <yêu cầu>` | requirement-analyst | `spec.md` (user story, AC Gherkin có ID, edge case, câu hỏi mở) | **Gate 1:** bạn trả lời câu hỏi / "approve spec" |
| 2 Plan | `/plan <slug>` | code-explorer, planner | `plan.md` (cách làm, data model, API contract, task T1..Tn gắn với AC) | **Gate 2:** "approve plan", sau đó tạo nhánh `feature/<slug>` |
| 3 Implement | `/implement <slug>` | test-writer → implementer, commit-message-writer | test + code, mỗi task 1 commit | dừng lại khi lệch plan |
| 4 Verify | `/verify <slug>` | build-error-resolver / implementer nếu đỏ | — | phải xanh |
| 5 Review | `/review <slug>` | các reviewer theo loại file (bảng dưới) + spec-verifier | `review.md` (bảng finding + verdict) | **Gate 3:** "fix all" / "fix #1,#3" / "approve" |
| 6 Ship | `/ship <slug>` | doc-writer | `feature-doc.md` (tiếng Việt), `mr-description.md` (tiếng Anh) | **Final gate:** "ship", sau đó push và mở MR draft |

- **Tiếp tục khi bị gián đoạn:** chạy lại `/feature <slug>`. Command đọc `docs/features/<slug>/STATUS.md` và tiếp tục từ phase đang dở.
- **Không bao giờ bỏ qua cổng**, kể cả khi bạn không trả lời.
- **`/plan` không có slug** (ad-hoc): lập kế hoạch cho một việc lẻ, không ghi file, và chờ bạn xác nhận.

**`/review` chọn reviewer theo file thay đổi:**

| File thay đổi | Reviewer |
|---------------|----------|
| `*.php` | laravel-reviewer |
| `*.vue`, pages/composables/stores của Nuxt | vue-reviewer |
| `*.tsx`, `*.jsx`, Next.js | react-reviewer |
| `*.ts`, `*.js` (NestJS, Node) | typescript-reviewer |
| `*.go` | go-reviewer |
| `*.py` | python-reviewer |
| migration, raw SQL, query mới | database-reviewer |
| routes, auth, FormRequest, upload, webhook, payment, config | security-reviewer |
| repository/query, job/queue, endpoint list/export, HTTP client, scheduler, config session/cache/queue/database | scalability-reviewer |
| còn lại (CI, Docker, shell) | code-reviewer |
| luôn chạy | silent-failure-hunter; spec-verifier nếu có `spec.md` |

Mức độ theo `review-checklist`: **BLOCKER** (sai hành vi, mất dữ liệu, lỗ hổng bảo mật) · **MAJOR** (bug khả năng cao, thiếu test, vỡ ở tải 10×) · **MINOR** · **NIT**. Verdict `CHANGES REQUIRED` khi còn BLOCKER hoặc MAJOR chưa được giải trình.

---

## 4. Đường nhanh: `/quick`, `/debug`, `/code-review`

### `/quick <việc>`

```
0 Kiểm tra độ lớn ─▶ 1 Tái hiện (test fail) ─▶ 2 Sửa ─▶ 3 Verify phần bị đụng ─▶ 4 Review nhẹ ─▶ 5 STOP: commit | fix #n | lên /feature
```

- **Tự đề nghị chuyển sang `/feature`** khi: quá ~3 file hoặc ~150 dòng; có endpoint, bảng, migration, queue hoặc contract mới; đụng auth, payment, phân quyền hay xóa dữ liệu; yêu cầu còn mơ hồ.
- **Chỉ có 1 cổng**, nằm ngay trước khi commit. Không bao giờ push. Không commit thẳng lên `main`: nếu đang ở `main` thì tạo `fix/<slug>` trước.

### `/debug <triệu chứng>`

Làm theo skill `debugging`: tái hiện → đọc bằng chứng → thu hẹp → mỗi lần 1 giả thuyết → chứng minh. Sau đó **dừng lại, chưa sửa code**, và báo cáo:

```
Symptom:     POST /api/v1/orders trả 500 ~2% lúc cao điểm
Evidence:    log request_id=... "Deadlock found"; INNODB STATUS: orders và products bị khóa ngược thứ tự
Root cause:  OrderService khóa orders trước products, RefundService khóa ngược lại
Fix:         khóa theo cùng thứ tự (products → orders) ở cả 2 service
Regression:  test chạy place() và refund() song song, cả hai đều thành công
```

Bạn chọn `fix` (chạy `/quick` với báo cáo này), `dig deeper`, hoặc `stop`. Các thao tác thay đổi trạng thái (xóa cache, retry job, purge queue, kill query, sửa dữ liệu) đều phải được bạn đồng ý.

### `/code-review [base]`

Không truyền base thì review thay đổi chưa commit. Có base thì review `base...HEAD`. Reviewer được chọn giống `/review`, kết quả gộp thành một bảng, in ngay trong chat. **Chỉ đọc**: muốn sửa thì dùng `/quick fix #n …`.

---

## 5. Danh mục command (28)

### Pipeline

| Command | Tham số | Việc |
|---------|---------|------|
| `/feature` | `<slug> <yêu cầu \| file \| URL>` | Điều phối toàn bộ pipeline, có resume |
| `/spec` | `<slug> <yêu cầu>` | Phase 1: `spec.md` + Gate 1 |
| `/plan` | `<slug>` hoặc `<việc lẻ>` | Phase 2: `plan.md` + Gate 2; không có slug thì là kế hoạch ad-hoc |
| `/implement` | `<slug> [T1,T2 \| all]` | Phase 3: TDD từng task, mỗi task 1 commit |
| `/verify` | `[slug]` | Cổng chất lượng theo stack |
| `/review` | `<slug> [base=main]` | Phase 4: review song song → `review.md` + Gate 3 |
| `/ship` | `<slug>` | Phase 5: tài liệu + MR description, push, mở MR draft |

### Hằng ngày

| Command | Tham số | Việc |
|---------|---------|------|
| `/quick` | `<việc>` | Sửa nhỏ, 1 cổng duyệt |
| `/debug` | `<triệu chứng \| lỗi \| request_id>` | Tìm nguyên nhân gốc, dừng lại báo cáo |
| `/code-review` | `[base]` | Review local, chỉ đọc |
| `/build-fix` | `[path \| lỗi]` | Sửa build/type/lint bằng resolver đúng stack |
| `/refactor-clean` | `[path]` | Xóa dead code theo đợt an toàn |
| `/save-session` | — | Lưu trạng thái phiên làm việc |
| `/resume-session` | `[file]` | Mở lại phiên đã lưu gần nhất |

### Theo ngôn ngữ

| Command | Việc |
|---------|------|
| `/go-build` | Sửa lỗi `go build`/`go vet`/lint (go-build-resolver) |
| `/go-test` | TDD cho Go, table-driven test, coverage |
| `/go-review` | Review Go (go-reviewer) |
| `/vue-review` | Review Vue (vue-reviewer + typescript-reviewer) |
| `/react-review` | Review React (react-reviewer + typescript-reviewer) |
| `/react-build` | Sửa build React/Next (react-build-resolver) |
| `/react-test` | TDD cho React bằng Testing Library |

### Continuous learning

| Command | Việc |
|---------|------|
| `/instinct-status` | Xem instinct của project và global, kèm confidence |
| `/projects` | Danh sách project đã ghi nhận |
| `/evolve` | Gom instinct thành skill/command/agent |
| `/promote` | Nâng instinct của project lên global |
| `/prune` | Xóa instinct pending quá 30 ngày |
| `/instinct-export` | Xuất instinct ra file |
| `/instinct-import` | Nhập instinct từ file hoặc URL |

---

## 6. Danh mục agent (25)

Cột **Ghi code**: ✍️ = được sửa code · 📄 = chỉ ghi tài liệu của mình · 👁 = chỉ đọc. Model theo `AGENT_STANDARD.md`: `opus` cho việc cần phán đoán, `sonnet` cho việc làm theo pattern, `haiku` cho việc máy móc.

### Pipeline

| Agent | Model | Ghi code | Vai trò |
|-------|-------|----------|---------|
| requirement-analyst | opus | 📄 | Yêu cầu thô → `spec.md` testable (AC có ID, edge case, câu hỏi mở) |
| code-explorer | sonnet | 👁 | Vẽ bản đồ một tính năng đang có (entry point, luồng, tầng, file:line) |
| planner | opus | 📄 | Spec đã duyệt → `plan.md` với task T1..Tn gắn với AC |
| architect | opus | 📄 | Quyết định kiến trúc xuyên module → ADR trong `docs/adr/` |
| test-writer | sonnet | ✍️ | Viết test FAIL trước (TDD red), xác nhận fail đúng lý do |
| implementer | sonnet | ✍️ | Làm đúng 1 task tới khi test xanh, rồi format và static analysis |
| spec-verifier | sonnet | 👁 | Bảng truy vết AC → test, chấm chất lượng test |
| doc-writer | sonnet | 📄 | Tài liệu tính năng (tiếng Việt) + MR description (tiếng Anh) từ diff thật |
| commit-message-writer | haiku | 👁 | Viết Conventional Commit từ `git diff --staged` |

### Review (đều read-only)

| Agent | Model | Phạm vi |
|-------|-------|---------|
| laravel-reviewer | opus | Laravel theo house style: tầng, API format, exception, Sanctum, RabbitMQ, transaction, test PHPUnit. Vi phạm `[layers]`/`[api]` là **MAJOR** |
| security-reviewer | opus | OWASP: IDOR, mass assignment, injection, XSS, secret, upload, SSRF, webhook, race trên tiền/tồn kho |
| scalability-reviewer | opus | Tải ở 10× và chạy nhiều node. Mỗi finding phải nêu mức tải sẽ vỡ và tài nguyên bị cạn |
| database-reviewer | sonnet | MySQL/InnoDB + Eloquent: index, query plan, N+1, migration bảng lớn, lock |
| typescript-reviewer | sonnet | TS/JS/NestJS/Node: type, async, boundary |
| vue-reviewer | sonnet | Vue 3/Nuxt: Composition API, reactivity, Pinia/Router |
| react-reviewer | sonnet | React/Next: hook, render, server/client boundary, a11y |
| go-reviewer | sonnet | Go: idiom, error, context, concurrency, rò rỉ tài nguyên |
| python-reviewer | sonnet | Python: typing, error handling, async |
| silent-failure-hunter | sonnet | Exception bị nuốt, catch rỗng, fallback che lỗi, thiếu timeout/rollback |
| code-reviewer | sonnet | Dự phòng cho shell, SQL script, YAML/CI, Dockerfile, config |

### Sửa lỗi build và bảo trì

| Agent | Model | Ghi code | Vai trò |
|-------|-------|----------|---------|
| build-error-resolver | sonnet | ✍️ | Build/type/lint PHP, TS/Vue, Python |
| react-build-resolver | sonnet | ✍️ | Build React/Next (Vite, webpack, hydration) |
| go-build-resolver | sonnet | ✍️ | `go build`/`go vet`/golangci-lint |
| refactor-cleaner | sonnet | ✍️ | Xóa dead code, test xanh sau mỗi đợt |
| e2e-runner | sonnet | ✍️ (test) | E2E Playwright, cách ly test flaky, thu trace |

---

## 7. Danh mục skill (39)

Skill là kiến thức được nạp khi cần. Chỉ phần **description** (1-2 câu) luôn nằm trong context. Nội dung đầy đủ chỉ được đọc khi skill liên quan tới việc đang làm.

### Backend: Laravel

| Skill | Nội dung |
|-------|----------|
| `laravel-patterns` | **House style:** FormRequest → Controller → Service → Repository → Model, response theo `api-design`, `BusinessException` + Handler tập trung, `/api/v1`, Sanctum, RabbitMQ, Redis. `references/`: exception handler (Laravel 10 và 11+), RabbitMQ queues |
| `laravel-tdd` | PHPUnit trên MySQL test DB, trait kiểm tra response, các case 401/403/404/422, test idempotency cho job |
| `laravel-verification` | Kiểm tra trước PR/deploy: Pint, test + coverage, `composer audit`, migration, `queue:restart` |
| `laravel-security` | Sanctum cookie hoặc token, policy, validation, upload, rate limit, secret |
| `laravel-plugin-discovery` | Tìm và đánh giá package Laravel (cần MCP LaraPlugins.io) |

### Backend: API, dữ liệu, Go, NestJS

| Skill | Nội dung |
|-------|----------|
| `api-design` | **API contract:** project có sẵn thì phát hiện format và làm theo; project mới dùng `data` + `paging` + `meta`. Bảng mã lỗi, pagination, versioning, helper mẫu cho Laravel/NestJS/Go |
| `mysql-patterns` | Schema, index, transaction, replication, connection pool |
| `redis-patterns` | Cấu trúc dữ liệu, cache, lock, rate limit, pub/sub |
| `database-migrations` | Migration an toàn, zero-downtime |
| `golang-patterns` | Go idiomatic: error, interface, concurrency, package |
| `golang-testing` | Table-driven test, fuzz, benchmark, coverage |
| `nestjs-patterns` | Module, provider, DTO, guard, interceptor, config |

### Chất lượng, quy trình, vận hành

| Skill | Nội dung |
|-------|----------|
| `scalability` | Bậc thang L1→L3 (1 VPS → nhiều node). `references/`: code-level, scale ngang, resilience, đo lường + k6 |
| `debugging` | Quy trình tìm nguyên nhân gốc. `references/stack-tools.md`: Laravel, NestJS, Go, MySQL, Redis, RabbitMQ, browser, Docker |
| `review-checklist` | Luật chung cho mọi reviewer: thang mức độ, bằng chứng, bảng output, cách gộp kết quả |
| `feature-spec` | Template `spec.md` + `STATUS.md` |
| `feature-docs` | Template tài liệu tính năng (tiếng Việt) |
| `gitlab-mr` | Đặt tên nhánh, Conventional Commits, template MR, lệnh `glab` |
| `tdd-workflow` | TDD chung, coverage 80% |
| `verification-loop` | Kiểm tra 6 phase, báo cáo PASS/FAIL |
| `e2e-testing` | Playwright, Page Object, CI, test flaky |
| `continuous-learning-v2` | Hệ thống instinct tự học (xem [mục 11](#11-continuous-learning)) |

### Frontend

| Skill | Nội dung |
|-------|----------|
| `vue-patterns` | Vue 3 Composition API, Pinia, Router |
| `nuxt4-patterns` | Nuxt 4: hydration, route rules, `useFetch` |
| `ui-to-vue` | Chuyển screenshot/design thành component Vue |
| `react-patterns` | React 18/19: hook, server/client component, Suspense |
| `react-performance` | Hơn 70 rule hiệu năng React/Next |
| `react-testing` | Testing Library, Vitest/Jest, MSW, axe |
| `nextjs-turbopack` | Next.js 16+, Turbopack |
| `vite-patterns` | Config, plugin, env, proxy, build |
| `frontend-patterns` | Pattern frontend chung |
| `frontend-a11y`, `accessibility` | A11y theo WCAG 2.2 AA |
| `frontend-design-direction`, `design-system` | Định hướng thiết kế, token, audit UI |
| `motion-foundations`, `motion-patterns`, `motion-advanced` | Animation với `motion/react` |
| `browser-qa` | Kiểm tra UI sau deploy bằng browser MCP |

> Các skill frontend hiện vẫn là bản chung, chưa có house style riêng như Laravel.

---

## 8. Rules

Rules là các chỉ dẫn "luôn tuân theo". Rules nằm trong `~/.claude/rules/my-claude-kit/`:

| Thư mục | Nạp khi | Nội dung |
|---------|---------|----------|
| `common/` | **mọi session** (~17k ký tự) | coding style, testing, security, git workflow, roster agent, chọn model, code review |
| `php/` | khi làm file PHP | style, pattern, security, testing PHP |
| `golang/` | khi làm file Go | idiom Go |
| `typescript/` | khi làm file TS/JS | type, response type theo `api-design` |
| `web/` | khi làm file `.vue`, `.tsx`, `.css`, Blade, `resources/js`… | design quality, performance, security web |
| `vue/`, `nuxt/`, `react/` | khi làm file tương ứng | luật riêng từng framework |

Mọi rule ngoài `common/` đều có frontmatter `paths:`, nên chỉ được nạp khi đụng tới file khớp.

---

## 9. House style và API contract

### Laravel

| Chủ đề | Quy ước |
|--------|---------|
| Kiểu app | REST API cho SPA/mobile |
| Tầng | FormRequest → Controller → Service → Repository (class cụ thể, không interface) → Model |
| Input vào Service | `$request->validated()` dạng array |
| Query | Chỉ nằm trong Repository (ngoại lệ duy nhất: route model binding) |
| Transaction | Nằm ở Service; job/event dispatch bằng `afterCommit()` |
| Lỗi | `BusinessException(message, status, code, errors)` + Handler tập trung; không `try/catch` trong controller |
| Route | `/api/v1`, controller trong `Api\V1` |
| Auth | Sanctum: SPA cookie hoặc personal access token |
| Queue / cache | RabbitMQ (`vladimir-yuldashev/laravel-queue-rabbitmq`) / Redis |
| Test | PHPUnit, MySQL test DB riêng, repository thật |
| Format | Pint |
| Git | `main` only, nhánh `feature/*` / `fix/*`, merge qua MR |

Project nào muốn khác một luật thì ghi rõ trong `CLAUDE.md` của project đó. Luật của project thắng luật của kit.

### API contract (`api-design`)

1. **Project đã có API:** phát hiện format đang dùng (grep helper, đọc 2-3 endpoint và test), rồi **làm theo đúng format đó**. Không thêm format thứ hai. Muốn đổi format thì phải lên version mới (`/api/v2`).
2. **Project mới:**

```json
// list
{ "data": [ ... ], "paging": { "current_page": 1, "per_page": 20, "total": 42, "last_page": 3 }, "meta": { "message": "OK", "request_id": "01J9..." } }
// detail / create (không có paging)
{ "data": { "id": 12 }, "meta": { "message": "Order created", "request_id": "01J9..." } }
// lỗi
{ "data": null, "meta": { "message": "Validation failed", "code": "validation_failed", "errors": { "quantity": ["..."] }, "request_id": "01J9..." } }
```

Key dùng `snake_case`. `meta.code` là chuỗi ổn định cho client dựa vào. Ngày giờ theo ISO-8601. Tiền tính bằng số nguyên theo đơn vị nhỏ nhất. Bảng mã lỗi chuẩn nằm trong `skills/api-design/SKILL.md`.

---

## 10. Scalability

Skill `scalability` đi theo 3 bậc:

| Level | Hình dạng | Lên level khi |
|-------|-----------|---------------|
| **L1** | 1 VPS, Docker Compose: app, worker, MySQL, Redis, RabbitMQ | CPU > 70% kéo dài, swap, p95 vượt SLO |
| **L2** | Tách MySQL, rồi Redis/RabbitMQ ra host riêng | App là nút cổ chai, worker giành tài nguyên với app |
| **L3** | Nhiều app node stateless sau load balancer, MySQL read replica, worker riêng | Đọc quá nhiều so với ghi, deploy không được rớt request |

| Reference | Nội dung |
|-----------|----------|
| `code-level.md` | Keyset pagination, N+1, streaming, bulk write, transaction ngắn, count rẻ, cache, đẩy việc sang queue |
| `horizontal.md` | Stateless, load balancer, ngân sách connection MySQL, read replica, worker, scheduler chạy 1 lần, deploy không downtime |
| `resilience.md` | Timeout, retry + jitter, circuit breaker, rate limit, idempotency key, backpressure, graceful shutdown |
| `observability-load-test.md` | SLO, golden signals, slow query log, script k6, tính capacity |

---

## 11. Continuous learning

Claude ghi lại cách bạn làm việc theo từng project. Từ đó rút ra các **instinct**, là các ghi chú nhỏ có điểm tin cậy 0.3–0.9. Đầu mỗi session, những instinct mạnh nhất được nạp vào context. **Model không thay đổi**, đây là ghi chú tự động được chèn vào prompt.

| Thành phần | Việc |
|------------|------|
| `observe.sh` (PreToolUse/PostToolUse) | Ghi tool call vào `~/.local/share/ecc-homunculus/projects/<hash>/observations.jsonl` |
| Observer (Haiku, **mặc định tắt**) | Phân tích observation thành instinct, 5 phút một lần |
| `hooks/inject-instincts.py` (SessionStart) | Nạp instinct có confidence ≥ 0.5, tối đa 10, instinct của project xếp trước |

- **Bật observer:** đặt `"observer": {"enabled": true}` trong `~/.local/share/ecc-homunculus/config.json`. Đừng sửa file config trong skill, vì cài lại sẽ bị ghi đè.
- **Tắt hẳn:** `touch ~/.local/share/ecc-homunculus/disabled`.
- **Mang sang máy khác:** `/instinct-export`, rồi `/instinct-import`. Project ID tính từ git remote nên khớp giữa các máy.

Hướng dẫn chi tiết: [docs/continuous-learning.md](docs/continuous-learning.md).

---

## 12. Lớp an toàn

| Thành phần | Cài vào | Việc |
|------------|---------|------|
| `hooks/guard.sh` | `~/.claude/hooks/my-claude-kit/` (PreToolUse) | **Chặn** đọc/sửa `.env*` và file credential (kể cả qua shell); lệnh DB phá hoại (trừ khi có `--env=testing`); force push; push thẳng lên `main`/`master`/`develop`; `reset --hard` về các nhánh đó; `rm -rf` ở root, home, cwd |
| `hooks/post-edit-format.sh` | như trên (PostToolUse) | Format file vừa sửa bằng Pint, ESLint, gofmt hoặc ruff của project. Không bao giờ chặn |
| `settings/permissions.json` | gộp vào `permissions.deny` | Chặn `Read`/`Edit` trên `.env`, `.env.local`, `.env.production`, `.env.staging`, và `php artisan db:wipe` |
| `claude/CLAUDE.md` | `~/.claude/CLAUDE.md` | Chỉ dẫn global: style trả lời ngắn gọn, và khi nào viết đầy đủ |

- `.env.example`, `.env.testing` và `migrate:fresh --env=testing` được cho qua.
- **Guard chặn push thẳng lên `main`**, nên Claude không push hộ repo kit này được. Tự push bằng `! git push`.
- `claude/CLAUDE.md` có nhắc skill `graphify`, là skill không nằm trong kit. Máy nào không có thì bỏ đoạn đó đi.

---

## 13. Cấu trúc repo

```
my-claude-kit/
├── agents/            25 agent (.md, frontmatter: name, description, tools, model, skills)
├── commands/          28 slash command
├── skills/            39 skill (SKILL.md + references/)
├── rules/             common + php, golang, typescript, web, vue, nuxt, react
├── hooks/             guard.sh, post-edit-format.sh, inject-instincts.py
├── settings/          permissions.json (deny rules)
├── claude/            CLAUDE.md global
├── scripts/           merge-settings.py (hooks + deny ↔ settings.json)
├── docs/              continuous-learning.md
├── tests/             unittest: guard, inject, merge-settings, install, lint
├── upstream/          bản gốc của các file dựa trên mã nguồn mở, để đối chiếu (không cài)
├── LICENSE            MIT, © 2026 huynhkinhao1910
├── THIRD_PARTY_NOTICES.md  giấy phép và ghi nhận mã nguồn mở
├── AGENT_STANDARD.md  chuẩn viết agent/skill/command
├── lint.py            kiểm tra theo chuẩn
└── install.sh
```

---

## 14. Tự custom kit

### Thêm hoặc sửa một skill

1. Tạo `skills/<tên>/SKILL.md`. Frontmatter gồm `name` (trùng tên thư mục), `description` (≤ 1024 ký tự, nói rõ **khi nào dùng** và **khi nào không**; dùng `>-` nếu có dấu `: `), và `origin: My Claude Kit`.
2. Phần thân gồm các mục **When to Use → How It Works → Examples**, tối đa 500 dòng. Chi tiết dài tách ra `references/*.md`.
3. Chỉ ghi kiến thức và quy trình, không đặt persona. Persona thuộc về agent.

### Thêm một agent

- Frontmatter: `name`, `description` (≤ 400 ký tự, có "Use when…" và "Do NOT use for…"), `tools` (**luôn ghi rõ**, nếu bỏ trống sẽ có mọi quyền), `model`, `skills`.
- Reviewer, verifier, explorer **không** có `Write`/`Edit`.
- Thân theo thứ tự: Role → Inputs → Process → Output (format cố định) → Never.
- Thêm agent vào roster trong `AGENT_STANDARD.md` và `rules/common/agents.md` trong cùng một thay đổi.

### Kiểm tra trước khi commit

```bash
python3 lint.py .                          # 0 ERROR là bắt buộc
python3 -m unittest discover -s tests      # toàn bộ test phải xanh
./install.sh --dry-run
```

`lint.py` báo lỗi khi frontmatter YAML hỏng, tham chiếu tới skill hoặc agent không tồn tại, hay agent read-only có quyền ghi. Test `test_lint.py` chạy lint trên kit, nên lỗi này không lọt được vào commit.

### Đối chiếu với bản gốc (`upstream/`)

```bash
diff upstream/agents/go-reviewer.md agents/go-reviewer.md
diff -r upstream/skills/laravel-patterns skills/laravel-patterns
```

Khi dự án gốc có bản vá đáng lấy: so bản mới với `upstream/`, gộp phần đáng giá vào kit, rồi cập nhật `upstream/`.

### Tên kỹ thuật cần giữ nguyên

- Biến `ECC_*` (`ECC_INSTINCT_CONFIDENCE_THRESHOLD`, `ECC_SKIP_OBSERVE`…) và thư mục `~/.local/share/ecc-homunculus` là tên mà engine continuous-learning đọc. Đổi tên sẽ làm hỏng tính năng tự học và mất các instinct đã lưu.
- `LEGACY_RULES_NS=ecc` chỉ để installer dọn namespace rules cũ trên máy.

---

## 15. Xử lý sự cố

| Triệu chứng | Kiểm tra / sửa |
|-------------|----------------|
| Skill, agent hoặc command mới không xuất hiện | Khởi động lại Claude Code; `python3 lint.py ~/.claude` phải ra 0 ERROR |
| `guard.sh` không chặn gì | Máy chưa có `jq` → `brew install jq` |
| Claude báo "BLOCKED by My Claude Kit guard" | Đó là guard đang hoạt động. Push `main` thì tự push bằng `! git push`; đụng DB test thì thêm `--env=testing` |
| `/ship` không mở được MR | Chưa có `glab` hoặc chưa `glab auth login` |
| Rules bị nạp 2 lần | Chạy `./install.sh` để dọn namespace cũ; kiểm tra `ls ~/.claude/rules` |
| Không thấy "Active instincts" đầu session | Chưa có instinct ≥ 0.5 (`/instinct-status`), hoặc đang có file `disabled` |
| Muốn quay về trạng thái trước khi cài | Khôi phục `~/.claude/settings.json.bak-<thời gian>` và `~/.claude/.backup/my-claude-kit-<thời gian>/` |
| Máy công ty không muốn đụng `settings.json` | `./install.sh --no-hooks --no-claude-md` |

---

## 16. Giấy phép và ghi nhận

My Claude Kit được phát hành theo giấy phép [MIT](LICENSE), © 2026 huynhkinhao1910.

Một số skill, agent và command trong kit được xây dựng dựa trên các dự án mã nguồn mở theo giấy phép MIT. Thông báo giấy phép đầy đủ nằm trong [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), và bản gốc được giữ trong `upstream/`.
