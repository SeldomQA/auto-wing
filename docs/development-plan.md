# auto-wing 项目优化 & 改进计划

> 版本：0.7.0 → 1.0.0 演进路线
> 制定日期：2026-08
> 维护者：seldomQA

---

## 一、背景与目标

auto-wing 是一个利用 LLM 辅助自动化测试的工具，支持 `playwright` / `selenium` / `appium`
三大驱动，提供 `ai_action`、`ai_query`、`ai_assert`、`ai_function_cases` 四类 AI 操作。

当前版本（0.7.0）已具备元素标记注入、智能缓存等核心能力，但在 **工程整洁度、执行稳定性、
测试覆盖、功能完整性** 方面仍有明显改进空间。本计划目标：

1. 清理仓库工程卫生问题，降低新贡献者的理解成本。
2. 修复已知缺陷，提升 AI 操作的稳定性与可靠性。
3. 补齐视觉（Vision）能力与失败自愈能力，向 1.0 版本演进。
4. 建立测试与 CI 体系，保障后续迭代质量。

---

## 二、现状问题清单

### 2.1 工程卫生问题

| # | 问题 | 位置 | 严重度 |
|---|------|------|--------|
| H1 | 根目录存在大量调试/临时脚本，未纳入 `.gitignore` | `abc.json.py`、`zz.json`、`deep_debug.py`、`analyze_elements.py`、`debug_cache.py`、`demo.py` 及十余个 `test_*.py` 调试文件 | 中 |
| H2 | 存在疑似环境变量未展开而误创建的目录 | `%allure_result_folder%/` | 低 |
| H3 | README 提到 `configfile: pyproject.toml`，但 `pyproject.toml` 中缺少 `[tool.pytest.ini_options]` 配置 | `pyproject.toml` | 低 |
| H4 | `.env` 示例配置分散，缺少 `.env.example` 模板 | 根目录 / `examples/` | 低 |
| H5 | `docs/README-bak.md` 等备份文件残留 | `docs/` | 低 |

### 2.2 代码质量问题

| # | 问题 | 位置 | 严重度 |
|---|------|------|--------|
| Q1 | 死代码：`AiContext` 类定义后从未被引用 | `autowing/core/ai_context.py` | 低 |
| Q2 | `complete_with_vision()` 在 5 个 LLM 客户端中均已实现，但主流程从未调用，属于"半成品"能力 | `autowing/core/llm/base.py` 及 `client/*` | 中 |
| Q3 | Playwright/Selenium 的 `ai_assert` 只把 URL/Title 传给 LLM，未传入页面元素上下文，断言依据薄弱（Appium 版则传了 `elements`，三者行为不一致） | `autowing/playwright/fixture.py`、`autowing/selenium/fixture.py` | 高 |
| Q4 | 异常处理中引用可能未定义的局部变量（如 `ai_query`/`ai_function_cases` 的 except 分支引用 `cleaned_response`，若在清洗前抛异常会引发 `NameError` 掩盖原始错误） | `autowing/playwright/fixture.py` | 中 |
| Q5 | 三份驱动实现（playwright / selenium / appium）的 `ai_query`、`ai_assert` 逻辑大量重复，可进一步上提到 `AiFixtureBase` | `autowing/*/fixture.py` | 中 |
| Q6 | 自实现的 TF-IDF 向量化器缺少单元测试保护，且每次实例化 `AiFixtureBase` 都新建 `IntelligentCacheManager`，无法跨用例共享缓存 | `autowing/core/cache/cache_manager.py` | 中 |

### 2.3 功能与稳定性问题

| # | 问题 | 位置 | 严重度 |
|---|------|------|--------|
| F1 | **缓存失效风险**：`ai_action` 缓存的是 LLM 返回的 selector 指令，页面改版后缓存命中可能指向失效定位器，无失效回退机制 | `autowing/core/ai_fixture_base.py` `_get_cached_or_compute` | 高 |
| F2 | `ai_action` 仅支持 `click` / `fill` / `press` 三种动作，缺少 `select`（下拉框）、`hover`、`check`、`scroll`、`upload` 等 | `autowing/playwright/fixture.py` | 中 |
| F3 | LLM 返回非法 JSON / 动作执行失败时无重试与重规划机制（README 宣称的"自动重规划能力"尚未实现） | 各 `ai_action` | 高 |
| F4 | 无显式等待机制：动作执行依赖元素立即可交互，动态页面易出现超时/定位失败 | 各驱动实现 | 中 |
| F5 | iframe / Shadow DOM 场景下标记注入脚本与元素采集脚本的覆盖度待验证（`examples/` 已有 iframes 示例文件，但核心脚本未做跨 frame 处理） | `autowing/core/ai_fixture_web.py` | 中 |
| F6 | 缺少操作超时、失败截图、执行轨迹等调试辅助能力 | 全局 | 中 |

### 2.4 测试与质量保障缺失

| # | 问题 | 说明 |
|---|------|------|
| T1 | 无单元测试 / 集成测试套件，根目录的 `test_*.py` 均为手工调试脚本 | 核心逻辑（响应清洗、格式校验、缓存匹配）零测试保护 |
| T2 | 无 CI 流水线 | 无自动化构建 / 测试 / 发布校验 |
| T3 | 无类型检查与 Lint 约束 | 未配置 `mypy` / `ruff` |
| T4 | LLM 调用无 Mock 测试手段 | 测试必须真实调用模型，成本高且不稳定 |

---

## 三、改进计划（分三阶段）

### 阶段一：工程治理与缺陷修复（目标版本 0.7.1，约 1~2 周）

> 目标：清障 + 止损，不引入新功能。

**1. 仓库清理**
- 删除或迁移根目录调试脚本（`abc.json.py`、`zz.json`、`deep_debug.py`、`demo.py` 等）：
  有价值的移入 `examples/` 或 `tests/manual/`，无价值的直接删除。
- 删除 `%allure_result_folder%/` 目录，并在 `.gitignore` 中补充
  `%allure_result_folder%/`、`*.bak`、`allure-results/` 等规则。
- 删除 `docs/README-bak.md` 等备份残留。
- 新增 `.env.example` 模板，统一 5 个模型的示例配置；`examples/.env` 与根目录 `.env` 保留一个并在文档中说明。

**2. 构建配置完善**
- `pyproject.toml` 补充 `[tool.pytest.ini_options]`（`testpaths = ["tests"]`、
  `addopts` 等），与 README 描述对齐。
- 补充 `[project.optional-dependencies]`，显式声明 `playwright` / `selenium` / `appium`
  可选依赖组（当前仅靠文档口头说明）。
- 新增 `ruff` 配置（`[tool.ruff]`），先以修复明显问题为目标，不强制全量风格统一。

**3. 缺陷修复（对应问题清单）**
- **[Q3] 修复 `ai_assert` 上下文缺失**：将 `elements`（经 `_remove_empty_keys` 精简后）
  加入 playwright / selenium 的断言 prompt，并对齐三个驱动的 prompt 结构。
- **[Q4] 修复异常处理中的变量作用域问题**：`ai_query`、`ai_function_cases` 的 except
  分支中对 `cleaned_response` 做存在性防护。
- **[F1] 缓存失效回退**：`ai_action` 执行缓存指令时，若定位器找不到元素，自动淘汰该
  缓存条目并重新调用 LLM 计算（在 `cache_manager` 中增加 `invalidate(prompt, context)` 接口）。
- **[F4] 基础等待机制**：动作执行前使用框架自带的自动等待（Playwright locator 默认等待已具备，
  需显式传入合理 `timeout`；Selenium 使用已有的 `WebDriverWait` 补齐）。
- **[Q1] 清理死代码**：移除 `ai_context.py` 或将其真正接入上下文传递链路（二选一，
  倾向直接移除）。

**4. 测试基线**
- 建立 `tests/` 目录，先为纯逻辑模块补单元测试（无需真实浏览器/模型）：
  - `_clean_response()`：markdown 代码块、```json、异常输入。
  - `_validate_result_format()`：`string[]` / `number[]` 转换。
  - `IntelligentCacheManager`：命中/未命中、相似度阈值、持久化读写。
  - `selector_to_locator()`：CSS / XPath 转换。
- 引入 `pytest-mock`，为 LLM 客户端调用提供 Mock 测试手段。

### 阶段二：能力增强（目标版本 0.8.0，约 3~4 周）

> 目标：补齐宣称能力，提升成功率。

**1. 失败重试与重规划（对应 F3）**
- `ai_action` 增加执行闭环：定位失败 / 操作异常 → 采集错误上下文 → 携带错误信息重新
  请求 LLM（最多重试 N 次，可配置，默认 2 次）。
- 重试产生的新指令成功后，更新（而非叠加）缓存。

**2. 视觉能力落地（对应 Q2）**
- 主流程接入 `complete_with_vision()`：`ai_action` 支持"截图 + 元素坐标"双模输入，
  截图以 base64 传入，供视觉模型（qwen-vl / gemini / doubao-vision）定位元素。
- 提供 `vision: bool` 开关（按模型能力自动降级为纯文本模式）。
- 与 README 中"所有传递给 LLM 的数据都是截图和元素坐标"的描述对齐。

**3. 动作集扩展（对应 F2）**
- 新增动作：`select`（下拉选择）、`hover`、`check`/`uncheck`、`scroll`、`upload`。
- prompt 中的 `action` 枚举与动作执行分支同步扩展，三个驱动保持对齐。

**4. 缓存体系完善（对应 Q6）**
- `IntelligentCacheManager` 支持单例/共享模式（进程级），避免每个 fixture 实例独立缓存。
- 为缓存增加 `domain`/`url-pattern` 维度，降低跨页面误命中。
- 新增缓存统计命令行的正式入口（整合 `cache_manager_cli.py` 的能力，作为
  `python -m autowing.cache` 子模块暴露）。

**5. 调试辅助（对应 F6）**
- 动作失败时自动截图保存到 `.auto-wing/screenshots/`，并在日志中输出路径。
- 增加 `AUTOWING_DEBUG=true` 环境变量，打印完整 prompt / LLM 原始响应。

**6. 文档更新**
- `docs/how_to_work.md` 补充重试、视觉、缓存失效回退的机制说明。
- 更新 `README.md` 的 Prompting Tips 与 Examples。

### 阶段三：架构打磨与 1.0 冲刺（目标版本 0.9.0 → 1.0.0，约 4~6 周）

> 目标：收敛重复实现，建立质量门禁，发布稳定版。

**1. 三端逻辑收敛（对应 Q5）**
- 将 `ai_query` / `ai_assert` / `ai_function_cases` 的 prompt 构造、响应解析、缓存读写
  上提至 `AiFixtureBase`（或新建 `autowing/core/actions_mixin.py`），
  三个驱动只保留"采集上下文 + 执行原子动作"的差异实现。
- 统一三端的动作枚举、错误类型、日志格式。

**2. iframe / Shadow DOM 支持完善（对应 F5）**
- 标记注入脚本递归进入同源 iframe；Playwright 侧利用 `frame_locator` 打通定位链路。
- 在 `examples/test_*_iframes.py` 基础上沉淀为回归用例。

**3. 质量门禁**
- 引入 GitHub Actions CI：`ruff` 检查 + `pytest`（单元部分）+ 构建校验。
- 引入 `mypy`（先对 `autowing/core` 开启严格模式）。
- 关键指标纳入 CI 报告：测试覆盖率 ≥ 70%（核心模块）。

**4. 1.0 发布准备**
- API 冻结与兼容性承诺声明（`ai_action` / `ai_query` / `ai_assert` / `ai_function_cases`
  签名稳定化）。
- 完善 `CHANGES.md` 与迁移指南（0.7 → 1.0 破坏性变更清单）。
- 评估并移除未完成/实验性入口（如 `PrefetchManager` 预取、`pattern_analyzer` 若未成熟，
  标注为 `experimental` 或移入独立模块）。

---

## 四、里程碑与版本规划

| 版本 | 内容 | 预计周期 |
|------|------|----------|
| **0.7.1** | 阶段一：仓库清理 + 缺陷修复 + 测试基线 | 1~2 周 |
| **0.8.0** | 阶段二：重试重规划 + 视觉能力 + 动作扩展 + 缓存共享 | 3~4 周 |
| **0.9.0** | 阶段三前半：三端收敛 + iframe 支持 + CI 门禁 | 2~3 周 |
| **1.0.0** | 阶段三后半：API 稳定化 + 文档完善 + 正式发布 | 1~2 周 |

---

## 五、风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| 视觉模型成本高于纯文本模型 | 用户使用成本上升 | `vision` 默认关闭，按模型自动降级；文档明确成本差异 |
| 缓存失效回退可能降低缓存命中率统计表现 | 指标回退引发误判 | 统计面板区分"命中后回退"与"真命中"两类指标 |
| 三端逻辑收敛属破坏性重构 | 可能引入行为回归 | 在阶段一单元测试充分覆盖后再动；收敛过程小步提交 |
| 真实浏览器/设备集成测试不稳定 | CI 失败率高 | 集成测试标记 `@pytest.mark.integration`，CI 中单独调度，不阻塞主干 |
| LLM 输出格式漂移（模型升级） | 解析失败率上升 | 响应解析保持宽松兜底；关键格式用 few-shot 示例锚定 |

---

## 六、优先级速览（可立即执行清单）

按投入产出比排序：

1. ✅ 删除根目录调试残留与 `%allure_result_folder%/`（半天）
2. ✅ 修复 `ai_assert` 缺失元素上下文（0.5 天）
3. ✅ 实现缓存失效回退机制（1~2 天）
4. ✅ 补充 `.env.example` 与 `pyproject.toml` pytest 配置（0.5 天）
5. ✅ 为核心纯逻辑模块补单元测试（2~3 天）
6. ✅ 实现 `ai_action` 失败重试/重规划（2~3 天）
7. 🔜 主流程接入 `complete_with_vision`（3~5 天）
8. 🔜 三端公共逻辑收敛重构（3~5 天）
9. 🔜 CI 流水线 + 质量门禁（2~3 天）
