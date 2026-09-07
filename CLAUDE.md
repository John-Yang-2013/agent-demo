# CLAUDE.md — Agent Demo 项目规则与改进蓝图

> 本文件是 AI 助手（Claude / Copilot 等）在本仓库工作时的规则与上下文文件。
> 包含：项目速览、代码规约、已知问题 Review、改进路线图。

---

## 1. 项目速览

**定位**：一个本地运行的 ReAct 多工具 AI Agent 演示。

**技术栈**：
- LLM：Ollama 本地推理（默认 `qwen3.5`）
- 框架：LangChain + LangGraph（`langchain.agents.create_agent`，ReAct 循环）
- UI：`rich`（终端面板 / Markdown 渲染 / 表格）
- 运行时：Python 3.12，`pyenv-virtualenv`（环境名 `agent`）

**5 个工具**：
| 工具 | 职责 | 实现要点 |
|---|---|---|
| `calculator` | 安全算术求值 | 基于 AST 白名单的 `_safe_eval_node`，禁用任意属性访问 |
| `get_current_datetime` | 时区日期时间 | `zoneinfo.ZoneInfo`，含星期、周数、年内剩余天数 |
| `get_weather` | 实时天气 | `wttr.in` JSON API（免 key） |
| `wikipedia_search` | 知识摘要 | `wikipedia` 库，含消歧义回退 |
| `unit_converter` | 单位换算 | 7 类线性换算表 + 温度非线性特例 |

**三种运行模式**：交互式 REPL / 单次查询（`-q`）/ 自动演示（`--demo`，7 个场景）

---

## 2. 代码规约（给所有贡献者 / AI 助手）

### 通用
- 遵循现有风格：模块级常量大写下划线、函数小写下划线、详细 docstring。
- 新增工具只需：`@tool` 装饰器（`agent/tools.py` 内定义即自动注册）+ 详细 docstring（含 args/examples，首行会作为工具摘要）。
- system prompt 与 CLI banner 由工具注册表动态生成，无需手动同步清单。
- 所有新函数加类型注解，保持小而单一职责。
- 不要改动无关文件或大规模重排格式。

### 提交信息（Conventional Commits）
```
<type>(<scope>): <summary ≤50 字符，现在时>
```
- type: `feat|fix|docs|style|refactor|perf|test|chore`
- scope: `tools|core|config|main|deps|docs|ci`

### 环境约定
- 不使用 `.venv`，使用 `pyenv activate agent`。
- 缺包时先确认处于 `agent` 环境，再 `pip install`。

---

## 3. 代码 Review — 已发现的问题

### 🔴 严重 / 架构级

**R1. `main.py` 过度臃肿（405 行，混合 4 层职责）**
- CLI 解析、Rich UI 渲染、agent 调用编排、demo 场景数据，全挤在一个文件。
- 违反单一职责；难以测试、难以复用（例如想加 web 前端就要重写）。
- **建议**：拆分为 `cli.py`（argparse 入口）、`ui.py`（Rich 渲染）、`runner.py`（agent 调用编排）、`scenarios.py`（demo 数据）。

**R2. 交互模式无对话历史** ✅ 已修复（阶段二：`agent/memory.py` 滑动窗口记忆）
- `run_interactive_mode` 每轮调用 `run_query` 都新建 `messages=[HumanMessage(...)]`，agent 完全无状态。
- 用户问"刚才那个再说一遍"会失败，无法多轮追问。
- **建议**：维护 `chat_history: list[BaseMessage]`，每轮 append 后传入。

**R3. 完全没有测试**
- 5 个工具（含 AST 求值器、单位换算表）都是纯逻辑、极易单测，却 0 测试。
- 计算器安全沙箱尤其需要"恶意输入回归测试"。
- **建议**：用 `pytest` 补 `tests/test_tools.py`、`tests/test_calculator_security.py`。

**R4. 无 lint / type-check / 格式化配置**
- 无 `pyproject.toml`、无 ruff、无 mypy、无 black。
- **建议**：加 `pyproject.toml` + `ruff` + `mypy`（即使只跑 `--ignore-missing-imports`）。

### 🟠 中等

**R5. System Prompt 硬编码工具清单，易与 `TOOLS` 失同步**
- `core.py` 里手写 5 条 bullet；新增工具忘改 → 模型不知道有该工具。
- **建议**：从 `TOOLS` 动态生成工具说明注入 prompt。

**R6. `wikipedia_search` 在函数内 `import wikipedia`**
- 每次调用重复 import 开销；若包未装，第一次调用才发现。
- **建议**：模块顶层 import，失败则在 `TOOLS` 构建时跳过并告警（graceful degradation）。

**R7. 温度换算用 `fu[0]` 取首字母判单位 — 脆弱 hack**
- `"celsius"[0]=="c"`、`"kelvin"[0]=="k"` 恰好成立，但语义脆弱、不可读。
- **建议**：显式别名映射 `{"celsius":"c","c":"c","fahrenheit":"f",...}`。

**R8. `get_weather` 用裸 `requests.get`，无连接复用 / 无缓存** ✅ 已修复（`_HTTP_SESSION` + `agent/cache.py` TTLCache）
- 每次新建连接；同一城市连问两次都打 API。
- **建议**：用 `requests.Session`（模块级）+ 短 TTL 内存缓存（`functools.lru_cache` 或显式 dict + 过期时间）。

**R9. `RECURSION_LIMIT = MAX_ITERATIONS * 2 + 1` 是魔法公式**
- 无注释说明为何 ×2 +1。LangGraph 每个工具调用产生 2 个递归步（agent 节点 + tool 节点），+1 余量。但读者不知。
- **建议**：加注释解释，或直接暴露 `RECURSION_LIMIT` 为独立 env 变量。

**R10. `num_predict=4096` 硬编码在 `core.py`** ✅ 已修复（`NUM_PREDICT` / `NUM_CTX` 纳入 config，env 可调）
- 不可通过 env 调整，`num_ctx` 也未设置。
- **建议**：纳入 `config.py`（`NUM_PREDICT`、`NUM_CTX`）。

### 🟡 轻微 / 打磨

**R11. `calculator` 的 `cbrt` 用 `lambda x: x**(1/3)`，其余用 `math.*`**
- 不一致；负数立方根会得复数路径。
- **建议**：Python 3.11+ 有 `math.cbrt`，直接用。

**R12. `_format_number` 对 0 直接返回 "0" 但不处理 -0.0**
- `unit_converter` 输出可能出现 `-0`。

**R13. `strip_thinking` 正则 `<think>…</think>` 是 qwen3 推理模型特有**
- 写死在通用 `main.py`；换模型无此标记则空转。
- **建议**：注释说明适用模型，或做成可配置的 post-processor 链。

**R14. requirements.txt 只写下限无上限**
- `langchain>=0.3.0` 可能被未来的不兼容大版本破坏。
- **建议**：用 `~=` 兼容版本范围，或 lock 文件（`pip-compile`）。

**R15. 无 CI**
- `.github/` 只有文档，没有 workflow。
- **建议**：加 `.github/workflows/ci.yml`（ruff + pytest）。

**R16. demo 场景里 `input()` 阻塞，非交互环境（CI/容器）会卡死**
- **建议**：加 `--no-pause` 标志或检测 `sys.stdin.isatty()`。

**R17. `main.py` 错误处理只靠字符串匹配 "connection refused"**
- 脆弱；应捕获具体异常类型（`requests.ConnectionError` / `httpx.ConnectError`）。

---

## 4. 改进路线图（打造成更好的 Agent）

### 阶段一：夯实基础（工程化）
1. 加 `pyproject.toml`：ruff + mypy + black 配置，统一工具链。
2. 拆分 `main.py` → `cli.py` / `ui.py` / `runner.py` / `scenarios.py`。
3. 补 `pytest` 测试：calculator 安全性、unit_converter 各类、datetime 边界。
4. 加 GitHub Actions CI（lint + test）。
5. requirements 改用版本约束 + `requirements-dev.txt`。

### 阶段二：Agent 能力增强
6. ✅ **对话记忆**：`agent/memory.py` 滑动窗口（`HISTORY_MAX_MESSAGES`），交互模式多轮追问，`clear` 命令重置。
7. ✅ **工具动态注册**：`@tool` 装饰器自动注册到 `_TOOL_REGISTRY`，system prompt / banner 动态生成。
8. ✅ **工具结果缓存**：`agent/cache.py` TTLCache（weather 10 分钟 / wikipedia 1 小时，env 可调）。
9. 🟡 **重试与超时**：工具 HTTP 层已完成（`requests.Session` + urllib3 `Retry` 指数退避）；LLM 调用层重试待做。
10. ⏳ **流式 token 输出**：`stream_mode="values"` 或 `astream` 实现 token 级打字机效果。

### 阶段三：能力扩展（更"Agent"）
11. **新工具**：web 搜索（DuckDuckGo/SerpAPI）、文件读写、代码执行（沙箱）、RAG 文档检索。
12. **结构化输出**：对计算/换算类调用用 `with_structured_output` 保证返回 schema。
13. **多 Agent / 路由**：LangGraph 多节点，按问题类型路由到子 agent。
14. **人机协作（Human-in-the-loop）**：危险工具调用前打断确认。
15. **可观测性**：接入 LangSmith / 本地日志，记录每次工具调用链。
16. **MCP 协议支持**：让 Agent 能消费外部 MCP server 的工具，成为开放生态。

### 阶段四：产品化
17. **配置体系升级**：`pydantic-settings` 替代裸 `os.getenv`，带校验与类型。
18. **多后端支持**：不只 Ollama，支持 OpenAI / Anthropic / vLLM 通过 `init_chat_model`。
19. **Web UI**：FastAPI + 前端，复用 `runner.py`。
20. **插件机制**：第三方按约定放一个 `@tool` 文件即被加载。

---

## 5. 快速命令

```bash
pyenv activate agent              # 激活环境
pip install -r requirements.txt   # 装依赖
ollama serve &                    # 启动 LLM
ollama pull qwen3.5               # 拉模型
python main.py                    # 交互
python main.py --demo             # 演示
python main.py -q "Convert 5 mi to km"
```

---

## 6. 已知假设 / 限制

- 当前仅支持单用户、单进程、终端交互。
- 对话记忆为进程内滑动窗口（`HISTORY_MAX_MESSAGES`，默认 12 条），重启即失；跨会话持久化待做。
- 工具缓存为进程内 TTL 缓存（weather 10 分钟 / wikipedia 1 小时），同样不跨进程。
- 工具调用无并发（LangGraph ReAct 串行）。
- weather/wikipedia 依赖外网，离线不可用。
