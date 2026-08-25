# auto-wing 项目优化 & 改进计划

> 版本：0.7.0 → 1.0.0 演进路线
> 制定日期：2026-08
> 最近更新：2026-08-25（工程卫生治理 + Q1~Q6/F1/F2/F3/F5/F6/T1/T3/T4 已完成，视觉能力、三端收敛、重试重规划、动作集扩展、跨 frame 覆盖、调试辅助、单测套件、Lint/类型检查门禁与 LLM Mock 测试手段提前落地）
> 维护者：seldomQA
> 状态图例：✅ 已完成 · ⏳ 未开始 · ⏸️ 暂缓

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

| #  | 问题                                                                                           | 位置                                                                                                             | 严重度 | 状态                               |
|----|----------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|-----|----------------------------------|
| H1 | 根目录存在大量调试/临时脚本，未纳入 `.gitignore`                                                              | `abc.json.py`、`zz.json`、`deep_debug.py`、`analyze_elements.py`、`debug_cache.py`、`demo.py` 及十余个 `test_*.py` 调试文件 | 中   | ✅ 已清理（备份至仓库外 `_cleanup_backup/`） |
| H2 | 存在疑似环境变量未展开而误创建的目录                                                                           | `%allure_result_folder%/`                                                                                      | 低   | ✅ 目录已不存在，`.gitignore` 已补预防规则     |
| H3 | README 提到 `configfile: pyproject.toml`，但 `pyproject.toml` 中缺少 `[tool.pytest.ini_options]` 配置 | `pyproject.toml`                                                                                               | 低   | ✅ 已补充                            |
| H4 | `.env` 示例配置分散，缺少 `.env.example` 模板                                                           | 根目录 / `examples/`                                                                                              | 低   | ✅ 模板已建；⏳ 两处 `.env` 去重待处理         |
| H5 | `docs/README-bak.md` 等备份文件残留                                                                 | `docs/`                                                                                                        | 低   | ⏸️ 暂缓（按约定不清理 `docs/`）            |

### 2.2 代码质量问题

| #  | 问题                                                                                                                  | 位置                                                              | 严重度 | 状态                                                                                          |
|----|---------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------|-----|---------------------------------------------------------------------------------------------|
| Q1 | 死代码：`AiContext` 类定义后从未被引用                                                                                           | `autowing/core/ai_context.py`                                   | 低   | ✅ 已删除（提交 `24fee49`）                                                                         |
| Q2 | `complete_with_vision()` 在 5 个 LLM 客户端中均已实现，但主流程从未调用，属于"半成品"能力                                                      | `autowing/core/llm/base.py` 及 `client/*`                        | 中   | ✅ 已接入主流程（`_llm_complete()` 统一入口 + 自动降级；Gemini 图片缺陷已修复）                                      |
| Q3 | Playwright/Selenium 的 `ai_assert` 只把 URL/Title 传给 LLM，未传入页面元素上下文，断言依据薄弱（Appium 版则传了 `elements`，三者行为不一致）             | `autowing/playwright/fixture.py`、`autowing/selenium/fixture.py` | 高   | ✅ 已修复（三端补齐补齐/统一 `elements` 上下文）                                                             |
| Q4 | 异常处理中引用可能未定义的局部变量（如 `ai_query`/`ai_function_cases` 的 except 分支引用 `cleaned_response`，若在清洗前抛异常会引发 `NameError` 掩盖原始错误） | `autowing/playwright/fixture.py`                                | 中   | ✅ 已修复（3 处隐患点均已在 `try` 前初始化；Appium 核查无此隐患）                                                   |
| Q5 | 三份驱动实现（playwright / selenium / appium）的 `ai_query`、`ai_assert` 逻辑大量重复，可进一步上提到 `AiFixtureBase`                       | `autowing/*/fixture.py`                                         | 中   | ✅ 已完成（`ai_query`/`ai_assert` 上提至 `AiFixtureBase`，三端共 ~450 行重复代码删除）                          |
| Q6 | 自实现的 TF-IDF 向量化器缺少单元测试保护，且每次实例化 `AiFixtureBase` 都新建 `IntelligentCacheManager`，无法跨用例共享缓存                             | `autowing/core/cache/cache_manager.py`                          | 中   | ✅ 已完成（`tests/` 新增 28 个单测；进程级共享实例 `get_intelligent_cache_manager()`，支持 `AUTOWING_CACHE_DIR`） |

### 2.3 功能与稳定性问题

| #  | 问题                                                                                                   | 位置                                                          | 严重度 | 状态    |
|----|------------------------------------------------------------------------------------------------------|-------------------------------------------------------------|-----|-------|
| F1 | **缓存失效风险**：`ai_action` 缓存的是 LLM 返回的 selector 指令，页面改版后缓存命中可能指向失效定位器，无失效回退机制                           | `autowing/core/ai_fixture_base.py` `_get_cached_or_compute` | 高   | ✅ 已修复（新增 `invalidate()`；playwright/selenium 定位失败时自动淘汰缓存并重算一次；Appium 走坐标点击不适用） |
| F2 | `ai_action` 仅支持 `click` / `fill` / `press` 三种动作，缺少 `select`（下拉框）、`hover`、`check`、`scroll`、`upload` 等 | `autowing/playwright/fixture.py`                            | 中   | ✅ 已扩展（playwright/selenium 同步新增 `select`/`hover`/`check`/`uncheck`/`scroll`/`upload`，prompt 动作枚举与执行分支对齐；Appium 走坐标点击不适用；新增动作分派单测） |
| F3 | LLM 返回非法 JSON / 动作执行失败时无重试与重规划机制（README 宣称的"自动重规划能力"尚未实现）                                            | 各 `ai_action`                                               | 高   | ✅ 已实现（`_ai_action_loop` 执行闭环 + `_llm_json_with_retry`；`AUTOWING_MAX_RETRIES` 默认 2；重试成功后刷新缓存） |
| F4 | 无显式等待机制：动作执行依赖元素立即可交互，动态页面易出现超时/定位失败                                                                 | 各驱动实现                                                       | 中   | ⏳ 未开始 |
| F5 | iframe / Shadow DOM 场景下标记注入脚本与元素采集脚本的覆盖度待验证（`examples/` 已有 iframes 示例文件，但核心脚本未做跨 frame 处理）           | `autowing/core/ai_fixture_web.py`                           | 中   | ✅ 已覆盖（三脚本上提为共享实现，递归同源 iframe + open Shadow DOM；Playwright `ai_action` 新增 `frame` 参数；Selenium 标记定位支持跨 frame 回退；新增回归测试） |
| F6 | 缺少操作超时、失败截图、执行轨迹等调试辅助能力                                                                              | 全局                                                          | 中   | ✅ 已实现（`AUTOWING_ACTION_TIMEOUT` 统一三端操作/等待超时；动作失败自动截图至 `.auto-wing/screenshots/` 并输出路径；执行轨迹追加至 `trace.jsonl`；`AUTOWING_DEBUG=true` 打印完整 prompt / LLM 原始响应；新增单测） |

### 2.4 测试与质量保障缺失

| #  | 问题                                       | 说明                        | 状态             |
|----|------------------------------------------|---------------------------|----------------|
| T1 | 无单元测试 / 集成测试套件，根目录的 `test_*.py` 均为手工调试脚本 | 核心逻辑（响应清洗、格式校验、缓存匹配）零测试保护 | ✅ 已建立（根目录调试脚本已清理；`tests/` 套件覆盖响应清洗/格式校验/定位器转换/缓存匹配/重试闭环/调试辅助/动作分派/跨 frame，共 118 个用例；并反向修复 2 个真缺陷） |
| T2 | 无 CI 流水线                                 | 无自动化构建 / 测试 / 发布校验        | ⏳ 未开始          |
| T3 | 无类型检查与 Lint 约束                           | 未配置 `mypy` / `ruff`       | ✅ 已配置（`pyproject.toml` 新增 `[tool.ruff]`（E9/F/W6/B 缺陷类规则）与 `[tool.mypy]`（渐进式：utils 严格、驱动/LLM 客户端豁免）；修复 29 个 lint 问题含 15 处异常链丢失，基类/缓存 4 个 mypy 真问题；现 `ruff check` / `mypy` 全绿） |
| T4 | LLM 调用无 Mock 测试手段                        | 测试必须真实调用模型，成本高且不稳定        | ✅ 已提供（三驱动构造器支持 `llm_client=` 注入 + `LLMFactory.register_model()` 注册 Fake；`tests/helpers.py::FakeLLMClient` 脚本化替身，`tests/test_llm_mocking.py` 19 个用例全离线验证工厂/注入/ai_query/重试重规划/缓存命中路径） |

---

## 三、改进计划（分三阶段）

### 阶段一：工程治理与缺陷修复（目标版本 0.7.1，约 1~2 周）

> 目标：清障 + 止损，不引入新功能。

**1. 仓库清理**

- ✅ 删除或迁移根目录调试脚本（`abc.json.py`、`zz.json`、`deep_debug.py`、`demo.py` 等）：
  全部确认无保留价值，已备份至仓库外 `_cleanup_backup/` 后移出（含 `cache_manager_cli.py`，
  阶段二整合时可取回）。
- ✅ 删除 `%allure_result_folder%/` 目录，并在 `.gitignore` 中补充
  `%allure_result_folder%/`、`*.bak`、`allure-results/` 等规则（目录检查时已不存在，预防规则已补）。
- ⏸️ 删除 `docs/README-bak.md` 等备份残留（按约定暂不清理 `docs/`）。
- ✅ 新增 `.env.example` 模板，统一 5 个模型的示例配置；⏳ `examples/.env` 与根目录 `.env` 保留一个并在文档中说明。

**2. 构建配置完善**

- ✅ `pyproject.toml` 补充 `[tool.pytest.ini_options]`（`testpaths = ["tests"]`、
  `addopts` 等），与 README 描述对齐。
- ✅ 补充 `[project.optional-dependencies]`，显式声明 `playwright` / `selenium` / `appium` / `dev`
  可选依赖组（当前仅靠文档口头说明）。
- ✅ 新增 `ruff` 配置（`[tool.ruff]`），先以修复明显问题为目标，不强制全量风格统一：仅启用缺陷类规则（pyflakes/
  致命语法/非法转义/bugbear），不启用注解风格类（UP）；同步修复 29 个问题（未使用导入/变量、`raise ... from`
  异常链、`zip(strict=)`、包重导出 `__all__`）。另新增 `[tool.mypy]` 渐进式类型检查（T3）。

**3. 缺陷修复（对应问题清单）**

- ✅ **[Q3] 修复 `ai_assert` 上下文缺失**：已将 `elements`（经 `_remove_empty_keys` 精简后）
  加入 playwright / selenium 的断言 prompt；Appium 版同步规范为 `json.dumps` 序列化，三端对齐。
- ✅ **[Q4] 修复异常处理中的变量作用域问题**：`ai_query`（playwright）、`ai_function_cases`
  （playwright + selenium）共 3 处已在 `try` 前初始化 `cleaned_response = ""`，原始错误不再被掩盖。
- ✅ **[F1] 缓存失效回退**：`cache_manager` 新增 `invalidate(prompt, context)`（按与 `get_intelligent`
  相同的匹配规则淘汰内存与磁盘条目）；playwright（`count()==0`）/selenium（`TimeoutException`）
  在缓存指令定位失败时自动淘汰并经 LLM 重算一次；`_get_cached_or_compute` 命中结果携带来源标记，
  新算指令不受影响。附 5 个 `invalidate()` 单测。
- ⏳ **[F4] 基础等待机制**：动作执行前使用框架自带的自动等待（Playwright locator 默认等待已具备，
  需显式传入合理 `timeout`；Selenium 使用已有的 `WebDriverWait` 补齐）。
- ✅ **[Q1] 清理死代码**：`ai_context.py` 已删除（提交 `24fee49`）。

**4. 测试基线** ✅ 已完成（2026-08）

- ✅ 建立 `tests/` 目录，`IntelligentCacheManager`（命中/未命中、相似度阈值、持久化读写、
  共享实例）与 `ImprovedTFIDFVectorizer`（预处理、n-gram、fit/transform、IDF）共 28 个单测。
- ✅ 纯逻辑模块单测补齐（无需真实浏览器/模型）：
    - `_clean_response()`：markdown 代码块、```json、异常输入。
    - `_validate_result_format()` / `_parse_format_hint()` / `_extract_query_from_text()` /
      `_parse_boolean_response()` / `_remove_empty_keys()`：格式转换与解析边界。
    - `selector_to_locator()` / `selector_to_selenium()`：`[text()=]` 谓词转换（含空白变体）。
- ✅ 测试反向暴露并修复 2 个真缺陷：`[text() = 'x']` 带空白谓词在 Playwright 端不生效；
  `_validate_result_format()` 对 `object[]` 提示隐式返回 `None`。
- ✅ 补齐 `autowing/core/cache/`、`autowing/utils/` 缺失的 `__init__.py`（打包完整性）。
- 集成测试：iframe/Shadow DOM 用例在真实浏览器上运行（无浏览器时优雅跳过）。
- ✅ LLM Mock 测试手段（T4，2026-08）：三驱动构造器新增可选 `llm_client` 注入参数（默认行为不变）；
  `tests/helpers.py` 提供 `FakeLLMClient`（FIFO 脚本化响应 + 调用记录），可配合 `LLMFactory.register_model()`
  做工厂级替换；`tests/test_llm_mocking.py` 覆盖 ai_query / 重试重规划 / 缓存命中全离线链路，无需 API Key、网络或浏览器。

### 阶段二：能力增强（目标版本 0.8.0，约 3~4 周）

> 目标：补齐宣称能力，提升成功率。

**1. 失败重试与重规划（对应 F3）** ✅ 已提前完成（2026-08）

- ✅ `ai_action` 执行闭环：基类 `_ai_action_loop()` 统一调度——执行失败 → 淘汰失效缓存 →
  携带错误信息重新请求 LLM（`AUTOWING_MAX_RETRIES` 可配置，默认 2 次）；三端接入。
- ✅ 非法 JSON 重试：`_llm_json_with_retry()` 在解析/结构校验失败时附带错误与上次响应反馈重试。
- ✅ 重试产生的新指令成功后，更新（而非叠加）缓存（`invalidate` + `set_intelligent`）。
- ✅ F1 的缓存失效回退已统一进重试循环（缓存指令定位失败作为一次失败尝试触发重规划）。

**2. 视觉能力落地（对应 Q2）** ✅ 已提前完成（2026-08）

- ✅ 主流程接入 `complete_with_vision()`：新增 `_llm_complete()` 统一入口，截图以
  base64 传入，供视觉模型（qwen-vl / gemini / doubao-vision）定位元素；三个驱动全部接入。
- ✅ 提供 `AUTOWING_VISION` 环境变量 + `enable_vision()` API 开关（按模型能力自动降级为纯文本模式）。
- ✅ 修复 Gemini 客户端图片处理缺陷（改为 `inline_data` 传入，原为文本占位符）。
- ⏳ 与 README 中"所有传递给 LLM 的数据都是截图和元素坐标"的描述对齐（文档更新待做）。

**3. 动作集扩展（对应 F2）** ✅ 已完成（2026-08）

- 新增动作：`select`（下拉选择）、`hover`、`check`/`uncheck`、`scroll`、`upload`。
- prompt 中的 `action` 枚举与动作执行分支同步扩展，两个 Web 驱动保持对齐：
  Playwright 直接使用 `select_option`/`hover`/`check`/`scroll_into_view_if_needed`/
  `set_input_files`；Selenium 通过 `Select`/`ActionChains` 实现，`upload` 依赖原生文件输入。
- Appium 端走坐标点击，不涉及元素级动作分派，不在本次范围。
- 新增 `tests/test_action_execution.py`：Mock 驱动验证各动作分派与回退逻辑。

**4. 缓存体系完善（对应 Q6）** 🔄 核心已完成（2026-08）

- ✅ `IntelligentCacheManager` 支持单例/共享模式（进程级）：`get_intelligent_cache_manager()`
  按 `cache_dir` 复用实例，`AiFixtureBase` 不再每实例新建（可通过 `AUTOWING_CACHE_DIR` 覆盖）。
- ⏳ 为缓存增加 `domain`/`url-pattern` 维度，降低跨页面误命中。
- ⏳ 新增缓存统计命令行的正式入口（整合 `cache_manager_cli.py` 的能力，作为
  `python -m autowing.cache` 子模块暴露）。

**5. 调试辅助（对应 F6）** ✅ 已完成（2026-08）

- 动作失败时自动截图保存到 `.auto-wing/screenshots/`（目录可用 `AUTOWING_SCREENSHOT_DIR` 覆盖），
  并在日志中输出路径；截图失败不影响原始错误上抛。
- `AUTOWING_DEBUG=true` 环境变量：在 `_llm_complete` 统一入口打印完整 prompt / LLM 原始响应。
- 执行轨迹：每次 `ai_action` 的成功/失败/重试尝试追加到 `.auto-wing/trace.jsonl`
  （含时间、指令、错误、截图路径），三端共享。
- 操作超时：`AUTOWING_ACTION_TIMEOUT`（默认 30 秒）统一约束 Playwright 元素操作、
  Selenium / Appium 的 `WebDriverWait`。

**6. 文档更新** ⏳

- `docs/how_to_work.md` 补充重试、视觉、缓存失效回退的机制说明。
- 更新 `README.md` 的 Prompting Tips 与 Examples。

### 阶段三：架构打磨与 1.0 冲刺（目标版本 0.9.0 → 1.0.0，约 4~6 周）

> 目标：收敛重复实现，建立质量门禁，发布稳定版。

**1. 三端逻辑收敛（对应 Q5）**

- ✅ **`ai_query` / `ai_assert` 已提前上提至 `AiFixtureBase`**（2026-08）：prompt 构造
  （`_build_query_prompt` / `_get_context_summary`）、响应解析（`_parse_boolean_response` /
  `_extract_query_from_text`）统一在基类；Appium 的 label/text 提示经 `_llm_prompt_notice()`
  钩子保留。剩余工作：`ai_function_cases` 上提。
- 统一三端的动作枚举、错误类型、日志格式。

**2. iframe / Shadow DOM 支持完善（对应 F5）** ✅ 已完成（2026-08）

- ✅ 标记注入/元素采集/标记清理三脚本上提为 `ai_fixture_web.py` 共享实现，递归进入同源 iframe（深度上限 5）
  与 open Shadow DOM（跨域 frame 静默跳过）；嵌套 frame 内元素携带 `inFrame: true` 提示。
- ✅ Playwright 侧 `ai_action(prompt, frame=...)` 支持 Frame/FrameLocator/Locator/选择器字符串，
  经 `_resolve_frame()` 打通帧内定位链路（修复 `examples/test_playwright_iframes.py` 传参失效问题）。
- ✅ Selenium 侧 `_find_element_by_marker` 新增递归子 frame 查找回退（命中后停留在目标 frame）。
- ✅ 沉淀回归用例 `tests/test_iframe_shadow_dom.py`：脚本构成校验 + 真实浏览器覆盖验证（
  无 chromium 时自动跳过）+ Selenium 跨 frame 查找 Mock 测试。

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

| 版本        | 内容                             | 预计周期  | 进度                                                                    |
|-----------|--------------------------------|-------|-----------------------------------------------------------------------|
| **0.7.1** | 阶段一：仓库清理 + 缺陷修复 + 测试基线         | 1~2 周 | 🔄 进行中：仓库清理/构建配置（含 ruff+mypy 门禁）/Q1~Q4/Q6/F1/F3/T1/T3/T4 完成，仅剩缺陷修复（F4）                  |
| **0.8.0** | 阶段二：重试重规划 + 视觉能力 + 动作扩展 + 缓存共享 | 3~4 周 | 🔄 视觉能力（Q2）、缓存共享实例（Q6 核心）、动作集扩展（F2）与调试辅助（F6）已提前完成                                        |
| **0.9.0** | 阶段三前半：三端收敛 + iframe 支持 + CI 门禁 | 2~3 周 | 🔄 Q5 核心（ai_query/ai_assert 上提）与 iframe/Shadow DOM 覆盖（F5）已提前完成，剩 ai_function_cases 上提、CI |
| **1.0.0** | 阶段三后半：API 稳定化 + 文档完善 + 正式发布    | 1~2 周 | ⏳ 未开始                                                                 |

---

## 五、风险与应对

| 风险                  | 影响       | 应对                                               |
|---------------------|----------|--------------------------------------------------|
| 视觉模型成本高于纯文本模型       | 用户使用成本上升 | `vision` 默认关闭，按模型自动降级；文档明确成本差异                   |
| 缓存失效回退可能降低缓存命中率统计表现 | 指标回退引发误判 | 统计面板区分"命中后回退"与"真命中"两类指标                          |
| 三端逻辑收敛属破坏性重构        | 可能引入行为回归 | 在阶段一单元测试充分覆盖后再动；收敛过程小步提交                         |
| 真实浏览器/设备集成测试不稳定     | CI 失败率高  | 集成测试标记 `@pytest.mark.integration`，CI 中单独调度，不阻塞主干 |
| LLM 输出格式漂移（模型升级）    | 解析失败率上升  | 响应解析保持宽松兜底；关键格式用 few-shot 示例锚定                   |

---

## 六、优先级速览（可立即执行清单）

按投入产出比排序：

1. ✅ 删除根目录调试残留与 `%allure_result_folder%/`（半天）**——已完成**
2. ✅ 修复 `ai_assert` 缺失元素上下文（0.5 天）**——已完成**
3. ✅ 实现缓存失效回退机制（1~2 天）**——已完成**
4. ✅ 补充 `.env.example` 与 `pyproject.toml` pytest 配置（0.5 天）**——已完成**
5. 🔄 为核心纯逻辑模块补单元测试（2~3 天）**——缓存/TF-IDF 已覆盖（28 个），剩响应清洗/格式校验/定位器转换**
6. ✅ 实现 `ai_action` 失败重试/重规划（2~3 天）**——已提前完成**
7. ✅ 主流程接入 `complete_with_vision`（3~5 天）**——已提前完成**
8. ✅ 三端公共逻辑收敛重构（3~5 天）**——`ai_query`/`ai_assert` 已提前上提，剩 `ai_function_cases`**
9. 🔜 CI 流水线 + 质量门禁（2~3 天）
