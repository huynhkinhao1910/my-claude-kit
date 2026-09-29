# Continuous Learning — Claude tự rút kinh nghiệm theo project

Tài liệu này giải thích cơ chế "tự học" trong kit: nó làm gì, dữ liệu nằm ở đâu, cách bật/tắt, cách dùng hằng ngày và cách xử lý sự cố.

> **Tóm tắt một câu:** hook ghi lại cách bạn làm việc, một agent Haiku chạy nền (tắt mặc định) rút ra các "instinct" có điểm tin cậy, rồi đầu mỗi session các instinct mạnh nhất được nạp vào context để Claude làm theo.

---

## 1. Nó KHÔNG phải là gì

- **Không** train lại model. Trọng số Claude không đổi.
- **Không** gửi dữ liệu lên server riêng nào. Mọi thứ nằm trên máy bạn, ngoại trừ phần observer gọi `claude` CLI (Haiku) để phân tích. Phần này dùng đúng tài khoản Claude của bạn.
- **Không** tự sửa code hay config của bạn.

Bản chất là một hệ thống **ghi chú tự động có chấm điểm**, được inject vào prompt.

---

## 2. Kiến trúc

```
 Bạn làm việc trong Claude Code (trong một git repo)
        │
        │  PreToolUse / PostToolUse
        ▼
 ┌──────────────────────────────────────────────┐
 │ observe.sh                                   │  luôn chạy khi hook được đăng ký
 │  - nhận diện project (hash git remote)       │  không tốn token
 │  - scrub secret, cắt input/output 5000 ký tự │
 │  - ghi 1 dòng JSON / tool call               │
 └──────────────────────────────────────────────┘
        │
        ▼
 ~/.local/share/ecc-homunculus/projects/<hash>/observations.jsonl
        │
        │  chỉ khi observer.enabled = true
        ▼
 ┌──────────────────────────────────────────────┐
 │ Observer (Haiku, chạy nền)                   │  mỗi 5 phút, khi ≥ 20 observation
 │  - tìm: bạn sửa Claude, lỗi được fix,        │  TỐN TOKEN (ít)
 │    workflow lặp lại                          │
 │  - tạo / cập nhật instinct + confidence      │
 └──────────────────────────────────────────────┘
        │
        ▼
 projects/<hash>/instincts/personal/*.yaml   (instinct của project)
 instincts/personal/*.yaml                   (instinct global)
        │
        │  SessionStart
        ▼
 ┌──────────────────────────────────────────────┐
 │ inject-instincts.py  (viết riêng cho kit)    │
 │  - lọc confidence ≥ 0.5, tối đa 10           │
 │  - project được ưu tiên (+0.25 khi xếp hạng) │
 │  - trả về additionalContext                  │
 └──────────────────────────────────────────────┘
        │
        ▼
 Claude thấy ở đầu session:
   Active instincts (learned from past sessions):
   - [project 80%] Validate input with FormRequest classes.
   - [global 70%] Grep for usages before renaming a symbol.
```

### Thành phần trong kit

| File | Vai trò | Nguồn |
|------|---------|-------|
| `skills/continuous-learning-v2/` | Skill gốc: `observe.sh`, observer, `instinct-cli.py` | ECC, giữ nguyên |
| `hooks/inject-instincts.py` | Hook SessionStart nạp instinct vào session | Tự viết (thay cho `session-start.js` 840 dòng của ECC) |
| `scripts/merge-settings.py` | Đăng ký / gỡ hook trong `settings.json` | Tự viết |
| `commands/instinct-*.md`, `evolve`, `promote`, `projects`, `prune` | Slash command quản lý instinct | ECC / `~/.claude`, đã sửa đường dẫn |

`inject-instincts.py` **import thẳng** `detect_project()` và `load_all_instincts()` từ `instinct-cli.py`. Nhờ vậy hash project luôn khớp với thứ `observe.sh` ghi ra, và kit không phải tự viết lại thuật toán này.

---

## 3. Instinct là gì

Mỗi instinct là một file YAML nhỏ, gồm **một trigger và một hành động**:

```yaml
---
id: use-form-request
trigger: "when adding validation to a Laravel endpoint"
confidence: 0.7
domain: laravel
scope: project
---

# Use FormRequest

## Action
Validate input with FormRequest classes, never inline in controllers.

## Evidence
- User corrected inline $request->validate() on 2026-09-12
- Observed 4 times in shop-api
```

Hook chỉ inject **dòng đầu tiên của mục `## Action`**. Vì vậy dòng này cần ngắn, rõ, và là mệnh lệnh.

### Điểm tin cậy (confidence)

| Điểm | Ý nghĩa | Trong kit |
|------|---------|-----------|
| 0.3 | Mới phỏng đoán | Không inject |
| 0.5 | Vừa phải | **Bắt đầu được inject** (ngưỡng mặc định) |
| 0.7 | Mạnh | Inject, xếp hạng cao |
| 0.9 | Gần như chắc chắn | Hành vi cốt lõi |

Điểm **tăng** khi pattern lặp lại mà bạn không sửa. Điểm **giảm** khi bạn sửa ngược lại, khi lâu không thấy pattern, hoặc khi có bằng chứng mâu thuẫn.

### Scope: project và global

- **project** (mặc định): chỉ áp dụng trong repo đó. Quy tắc của project Laravel không lây sang project Go.
- **global**: áp dụng mọi nơi. Instinct được nâng lên global bằng `/promote`. Điều kiện gợi ý: xuất hiện ở ≥ 2 project với confidence trung bình ≥ 0.8.
- Khi instinct project và global trùng `id`, bản **project thắng**.

### Nhận diện project

1. Biến `CLAUDE_PROJECT_DIR`, nếu có.
2. `git remote get-url origin`: URL được chuẩn hóa (bỏ credential, bỏ `.git`, viết thường), rồi lấy 12 ký tự đầu của SHA-256. **Cùng repo trên máy nhà và máy công ty cho ra cùng ID.**
3. Nếu không có remote: dùng đường dẫn repo. ID này chỉ đúng trên một máy.
4. Nếu không nằm trong git repo: rơi vào global.

---

## 4. Dữ liệu nằm ở đâu

Thư mục gốc (gọi là **data dir**) được chọn theo thứ tự:
1. `CLV2_HOMUNCULUS_DIR` (đường dẫn tuyệt đối)
2. `$XDG_DATA_HOME/ecc-homunculus`
3. `~/.local/share/ecc-homunculus` ← mặc định trên macOS/Linux

```
~/.local/share/ecc-homunculus/
├── config.json              # config CỦA BẠN (ưu tiên hơn config trong skill)
├── disabled                 # tạo file này = tắt toàn bộ (observe + inject)
├── projects.json            # registry: hash → tên, đường dẫn, remote
├── instincts/
│   ├── personal/            # instinct global do observer tạo
│   └── inherited/           # instinct global import từ nơi khác
├── evolved/                 # skill/command/agent sinh bởi /evolve (global)
└── projects/<hash>/
    ├── observations.jsonl   # log tool call (tự archive khi > 10 MB)
    ├── observations.archive/
    ├── instincts/personal/  # instinct của project
    ├── instincts/inherited/
    ├── evolved/
    ├── observer.log         # log của observer
    └── .observer.pid
```

Data dir nằm **ngoài** `~/.claude` và ngoài kit. Cài lại kit không làm mất instinct hay config.

> ⚠️ Observer tạo file `.observer.lock` ở **gốc repo** của project. Nên thêm `.observer.lock` vào `.gitignore` global:
> ```bash
> echo ".observer.lock" >> ~/.gitignore_global && git config --global core.excludesfile ~/.gitignore_global
> ```

---

## 5. Cài đặt

```bash
cd ~/my-claude-kit
./install.sh --dry-run    # xem trước: file nào được copy, hook nào được thêm
./install.sh              # cài thật
```

`install.sh` làm các việc sau:
1. Copy agents, commands, skills, rules và `hooks/` → `~/.claude/hooks/my-claude-kit/`. File cũ được backup vào `~/.claude/.backup/my-claude-kit-<thời gian>/`.
2. Chạy `scripts/merge-settings.py`:
   - backup `settings.json` → `settings.json.bak-<thời gian>`, chỉ khi có thay đổi
   - thêm 3 hook: `observe.sh pre` (PreToolUse), `observe.sh post` (PostToolUse), `inject-instincts.py` (SessionStart)
   - **giữ nguyên** hook riêng của bạn (`guard.sh`, `post-edit-format.sh`, …) và mọi key khác
   - idempotent: chạy lại không nhân đôi, và tự dọn entry `observe.sh` cũ nếu trước đây bạn thêm tay
   - nếu `settings.json` là symlink (dotfiles), ghi xuyên qua link, link vẫn giữ nguyên

Tùy chọn:

| Lệnh | Tác dụng |
|------|----------|
| `./install.sh --no-hooks` | Chỉ copy file, không đụng `settings.json` |
| `python3 scripts/merge-settings.py --remove` | Gỡ **chỉ** hook của kit khỏi `settings.json` |
| `python3 scripts/merge-settings.py --dry-run` | In ra hooks sau khi merge, không ghi |

Yêu cầu: `bash`, `python3`, `git`. Observer cần thêm `claude` CLI. Sau khi cài, **khởi động lại Claude Code**.

---

## 6. Các chế độ hoạt động

Có 3 mức, chọn theo máy:

| Mức | Cách đặt | Ghi observation | Sinh instinct | Inject | Tốn token |
|-----|----------|:---:|:---:|:---:|:---:|
| **Tắt hẳn** | `touch ~/.local/share/ecc-homunculus/disabled` hoặc `./install.sh --no-hooks` | ✗ | ✗ | ✗ | ✗ |
| **Chỉ ghi** (mặc định sau khi cài) | observer.enabled = false | ✓ | ✗ (chỉ instinct bạn viết tay hoặc import) | ✓ instinct có sẵn | ✗ |
| **Học tự động** | observer.enabled = true | ✓ | ✓ mỗi 5 phút | ✓ | ít (Haiku) |

### Bật observer (học tự động)

Tạo config **của bạn** trong data dir. Không sửa `config.json` trong skill, vì cài lại kit sẽ ghi đè file đó.

```bash
mkdir -p ~/.local/share/ecc-homunculus
cat > ~/.local/share/ecc-homunculus/config.json <<'EOF'
{
  "version": "2.1",
  "observer": {
    "enabled": true,
    "run_interval_minutes": 5,
    "min_observations_to_analyze": 20
  }
}
EOF
```

Observer **tự khởi động (lazy-start)** ở lần tool call kế tiếp trong một git repo. Không cần chạy lệnh nào.

Điều khiển tay:

```bash
OBS=~/.claude/skills/continuous-learning-v2/agents/start-observer.sh
bash $OBS status    # đang chạy không
bash $OBS stop      # dừng
bash $OBS --reset   # xóa lock và khởi động lại (khi observer bị "paused")
```

Chạy các lệnh này **trong thư mục repo**, vì observer chạy riêng theo từng project.

### Tắt observer

Sửa `"enabled": false` trong `~/.local/share/ecc-homunculus/config.json`, rồi `bash $OBS stop`.

### Gợi ý theo máy

- **Máy nhà:** học tự động.
- **Máy công ty:** "chỉ ghi" hoặc "tắt hẳn", tùy chính sách công ty (xem mục 9). Instinct học ở nhà vẫn mang sang được bằng export/import (mục 7).

---

## 7. Dùng hằng ngày

| Command | Việc |
|---------|------|
| `/instinct-status` | Xem instinct của project hiện tại và global, kèm confidence |
| `/projects` | Danh sách project đã ghi nhận, số instinct và observation |
| `/evolve` | Gom instinct liên quan thành skill/command/agent (`--generate` để ghi file) |
| `/promote [id]` | Nâng instinct project lên global (`--dry-run` để xem trước) |
| `/prune` | Xóa instinct pending > 30 ngày chưa được promote |
| `/instinct-export` | Xuất instinct ra file YAML |
| `/instinct-import <file\|url>` | Nhập instinct (`--scope project\|global`, `--min-confidence`) |

### Vòng làm việc gợi ý

1. **Làm việc bình thường.** Khi Claude làm sai, **sửa rõ ràng bằng lời**, ví dụ "Không, dùng FormRequest". Câu sửa là tín hiệu mạnh nhất cho observer.
2. **Hằng tuần:** chạy `/instinct-status` và đọc lại. Instinct sai thì xóa file YAML tương ứng hoặc hạ `confidence`.
3. **Khi một nhóm instinct đã ổn định:** chạy `/evolve`, rồi đưa skill/agent đáng giữ **vào repo kit**, commit. Đây là cách tài sản cá nhân của bạn lớn dần.
4. **Instinct đúng ở mọi project:** chạy `/promote`.

### Tự viết instinct bằng tay

Không cần observer. Tạo file thẳng vào thư mục instinct:

```bash
# Lấy hash của project hiện tại (chạy trong thư mục repo).
# Khi project chưa có instinct nào, status in luôn đường dẫn "Project instincts:".
python3 ~/.claude/skills/continuous-learning-v2/scripts/instinct-cli.py status
# Khi đã có instinct: xem cột ID ở đây
python3 ~/.claude/skills/continuous-learning-v2/scripts/instinct-cli.py projects
```

```yaml
# ~/.local/share/ecc-homunculus/projects/<hash>/instincts/personal/no-raw-sql.yaml
---
id: no-raw-sql
trigger: "when querying the database in this project"
confidence: 0.9
domain: laravel
scope: project
---

## Action
Use Eloquent or the query builder; raw SQL only inside repositories.
```

Mở session mới là thấy instinct này được inject.

### Mang instinct sang máy khác

```bash
# máy nhà
/instinct-export --output ~/my-claude-kit/instincts/shop-api.yaml
# commit vào kit, push

# máy công ty (sau git pull)
/instinct-import ~/my-claude-kit/instincts/shop-api.yaml --scope project
```

Vì project ID tính từ git remote, instinct import trong cùng repo sẽ khớp đúng project.

---

## 8. Tùy chỉnh việc inject

Đặt trong phần `env` của `~/.claude/settings.json`, hoặc export trong shell:

| Biến | Mặc định | Ý nghĩa |
|------|----------|---------|
| `ECC_INSTINCT_CONFIDENCE_THRESHOLD` | `0.5` | Confidence tối thiểu để inject (số thập phân 0–1) |
| `ECC_MAX_INJECTED_INSTINCTS` | `10` | Số instinct tối đa mỗi session (số nguyên dương) |
| `CLV2_HOMUNCULUS_DIR` | `~/.local/share/ecc-homunculus` | Đổi data dir |
| `CLV2_INSTINCT_CLI` | tự tìm | Đường dẫn `instinct-cli.py` nếu cài ở chỗ lạ |
| `ECC_SKIP_OBSERVE` | `0` | `1` = bỏ qua ghi observation cho session này |

Giá trị sai định dạng (vd. `0x1`, `abc`) bị bỏ qua và dùng mặc định.

Xếp hạng: `score = confidence + 0.25` nếu là instinct project. Nhờ vậy một instinct project 0.7 (score 0.95) đứng trên một instinct global 0.9.

---

## 9. Riêng tư và bảo mật

- `observations.jsonl` chứa **prompt, input và output của tool** (mỗi trường cắt còn 5000 ký tự). Nội dung đó có thể gồm đoạn code và đường dẫn nội bộ.
- `observe.sh` tự thay giá trị sau các từ khóa như `api_key`, `token`, `secret`, `password`, `authorization` bằng `[REDACTED]`. Đây là **best-effort**, không phải bảo đảm.
- `observations.jsonl` lớn hơn 10 MB tự được chuyển vào `observations.archive/`. File archive cũ hơn 30 ngày tự bị xóa. File đang ghi **không** tự xóa theo thời gian.
- Observer gửi nội dung observation cho Haiku qua `claude` CLI của bạn.
- **Máy công ty:** kiểm tra chính sách trước khi bật observer. An toàn nhất là `./install.sh --no-hooks` hoặc tạo file `disabled`, rồi chỉ import instinct đã review từ máy nhà.
- Đừng commit `observations.jsonl` vào kit. Chỉ commit instinct đã export và đã đọc lại.

---

## 10. Xử lý sự cố

| Triệu chứng | Kiểm tra |
|-------------|----------|
| Không thấy "Active instincts" đầu session | Có instinct ≥ ngưỡng chưa (`/instinct-status`)? Có file `disabled` không? Đã khởi động lại Claude Code chưa? |
| Chạy hook tay để xem lỗi | `echo '{"cwd":"'$PWD'"}' \| python3 ~/.claude/hooks/my-claude-kit/inject-instincts.py`. Lỗi in ra stderr với tiền tố `[inject-instincts]` |
| Không có `observations.jsonl` | Hook đã đăng ký chưa (`grep observe ~/.claude/settings.json`)? Có `python3` không? Đang ở trong git repo chưa? |
| Observer không sinh instinct | `enabled: true` trong config **của data dir** chưa? Đã đủ 20 observation chưa? Xem `projects/<hash>/observer.log` |
| Observer "paused" | Nó gặp prompt xin quyền. Đọc `observer.log`, rồi chạy `start-observer.sh --reset` |
| Instinct của project A xuất hiện ở project B | Instinct đó có `scope: global`. Sửa lại thành `project` hoặc xóa |
| Muốn gỡ sạch | `python3 scripts/merge-settings.py --remove`, rồi xóa `~/.claude/hooks/my-claude-kit`. Data dir giữ lại hay xóa tùy bạn |

Hook inject **không bao giờ chặn session**: mọi lỗi đều exit 0 và chỉ log ra stderr.

---

## 11. Test

```bash
python3 -m unittest discover -s tests
```

- `tests/test_inject_instincts.py` (11 test): ngưỡng, giới hạn số lượng, project thắng global, xếp hạng, env sai định dạng, file `disabled`, thiếu CLI, stdin hỏng.
- `tests/test_merge_settings.py` (11 test): tạo mới, giữ hook người dùng, idempotent, dọn entry cũ, backup, `--remove`, JSON hỏng, symlink, `--dry-run`.

Test dùng chính `instinct-cli.py` thật để tính hash project, nên nếu ECC đổi thuật toán hash thì test sẽ bắt được.
