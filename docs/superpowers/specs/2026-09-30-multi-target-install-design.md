# Multi-target install: Claude, Codex, Copilot

Ngày: 2026-09-30 · Trạng thái: chờ duyệt

## Mục tiêu

Ở công ty không dùng Claude Code, chạy `./install.sh --target codex` hoặc `--target copilot` để có cùng bộ agent/skill/command/rule trên OpenAI Codex CLI, GitHub Copilot CLI và Copilot trong VS Code.

Thành công khi:
- `./install.sh` (không cờ) cho kết quả y hệt hiện tại.
- `--target codex` / `--target copilot` cài vào thư mục user-level, có backup, có `--dry-run`, không xóa file không thuộc kit.
- Toàn bộ test hiện có và test mới đều pass.

## Quyết định

- **Không có converter.** Mỗi target có thư mục riêng trong repo, chứa file đúng định dạng của AI đó. Installer chỉ copy.
- **Chỉ user-level.** Không ghi vào repo công ty (`.github/`, `AGENTS.md` của repo).
- **Tên thư mục không có dấu chấm** (`codex/`, không phải `.codex/`), để Claude Code không nạp nhầm chúng như cấu hình project khi mở chính repo kit.
- **Skills dùng chung.** Codex, Copilot CLI và Copilot VS Code đều đọc `~/.agents/skills/<name>/SKILL.md` theo cùng chuẩn với Claude, nên `skills/` chỉ có một bản.
- **Chấp nhận trùng lặp nội dung** giữa 3 target. Sửa một agent phải sửa ở 3 nơi. Test chỉ kiểm tra đủ file, không kiểm tra nội dung giống nhau.

## Cấu trúc repo

```
skills/                      dùng chung (đã có)
agents/ commands/ rules/ claude/ hooks/   Claude (giữ nguyên)
dotagents/skills/<cmd>/SKILL.md           command dạng skill cho Codex + Copilot → ~/.agents/skills/
codex/                       mirror của ~/.codex
├── AGENTS.md                CLAUDE.md + mục lục rules (≤ 32 KiB)
├── agents/<name>.toml
└── my-claude-kit/rules/<ns>/*.md
copilot/                     mirror của ~/.copilot
├── copilot-instructions.md
├── agents/<name>.agent.md
└── instructions/<ns>-<file>.instructions.md
```

## Định dạng từng target

**Codex** (`CODEX_HOME`, mặc định `~/.codex`)
- `agents/<name>.toml`: `name`, `description`, `developer_instructions` (body của agent Claude). Agent chỉ có quyền Read/Grep/Glob/Bash thì thêm `sandbox_mode = "read-only"`. Bỏ `model`.
- `AGENTS.md`: nội dung `claude/CLAUDE.md` + mục lục kiểu "khi sửa `*.php`, đọc `~/.codex/my-claude-kit/rules/php/`". Giới hạn 32 KiB của Codex không chứa nổi 216 KB rules, nên rules nằm ở file riêng.

**Copilot** (`COPILOT_HOME`, mặc định `~/.copilot`; VS Code cũng đọc `~/.copilot/agents`)
- `agents/<name>.agent.md`: frontmatter `name`, `description`, `tools`. Đổi tool: Read/Grep/Glob → `read`, `search`; Write/Edit → `edit`; Bash → `execute`. Bỏ `model`.
- `copilot-instructions.md`: nội dung `claude/CLAUDE.md`.
- `instructions/*.instructions.md`: mỗi rule một file, `paths:` đổi thành `applyTo:` (glob nối bằng dấu phẩy). Rule không có `paths` thì `applyTo: "**"`.

**Chung cho cả hai** (`AGENTS_HOME`, mặc định `~/.agents`)
- `skills/`: copy `skills/*` và `dotagents/skills/*`.
- Command → skill: `name` = tên command, `description` giữ nguyên, `$ARGUMENTS` thay bằng "the user's request", `argument-hint` thành một dòng "Input: …" trong body.
- Frontmatter `skills:` của agent Claude chuyển thành dòng "Load these skills first: X, Y" ở đầu body.

## Installer

`install.sh --target <list>`, list là `claude`, `codex`, `copilot` cách nhau bằng dấu phẩy, mặc định `claude`.
- Dùng lại `install_item` (backup vào `<home>/.backup/my-claude-kit-<thời gian>/`, `--dry-run`).
- Mỗi file/thư mục trong `codex/` được cài vào đúng đường dẫn tương ứng dưới `CODEX_HOME`; tương tự `copilot/` và `dotagents/`. Chỉ ghi đè mục do kit sở hữu.
- `skills/` vào `AGENTS_HOME` chỉ một lần, kể cả khi chọn cả codex và copilot.
- `--no-hooks`, `--no-claude-md` chỉ có tác dụng với target claude. `--no-claude-md` cũng bỏ qua `AGENTS.md` và `copilot-instructions.md` (giữ file instructions riêng của máy).
- Target không hợp lệ → thoát mã 2, không ghi gì.

## Khởi tạo nội dung

Một script chạy **một lần** sinh `codex/`, `copilot/`, `dotagents/` từ file Claude hiện có theo quy tắc ở trên. Script không được commit. Sau đó file trong 3 thư mục được sửa tay.

## Test

- `tests/test_targets.py`:
  - Mỗi `agents/*.md` có đủ `codex/agents/<name>.toml` và `copilot/agents/<name>.agent.md`. Mỗi command (trừ các command ngoài phạm vi) có `dotagents/skills/<name>/SKILL.md`.
  - Mọi `.toml` parse được bằng `tomllib`, có `name`, `description`, `developer_instructions`.
  - Mọi `.agent.md` và `SKILL.md` có `name` và `description`. Tên skill không trùng giữa `skills/` và `dotagents/skills/`.
  - `codex/AGENTS.md` ≤ 32 KiB.
  - Agent read-only: TOML có `sandbox_mode = "read-only"`, Copilot không có tool `edit`.
- `tests/test_install.py` thêm: `--target codex,copilot` với HOME tạm cài đúng chỗ; skill riêng của người dùng trong `~/.agents/skills` còn nguyên; target lạ thoát mã 2.

## Ngoài phạm vi (giai đoạn 2)

- Hooks: port `guard.sh` và continuous learning sang Codex `hooks.json` và Copilot `hooks/*.json`. Cần test trên máy có Codex/Copilot thật.
- 9 command phụ thuộc đường dẫn `~/.claude`: `instinct-status`, `instinct-export`, `instinct-import`, `evolve`, `promote`, `projects`, `prune`, `save-session`, `resume-session`.
- Prompt files của VS Code (`*.prompt.md`): skills đã phủ.
- Cài theo repo.
