# skia_googledocs_desktop.py - Google Docs 桌面端页面集定义

> 源文件: [tools/skp/page_sets/skia_googledocs_desktop.py](../../../tools/skp/page_sets/skia_googledocs_desktop.py)

## 概述

此文件定义了一个 Chromium Telemetry 页面集，用于从 Google Docs 文档查看页面录制 Skia Picture（SKP）文件。这是所有页面集中最复杂的之一，因为它需要处理 Google 账户登录认证。在非 Web Page Replay 回放模式下，脚本会先执行 Google 登录流程，然后导航到指定的文档 URL。Google Docs 大量使用 HTML5 Canvas 进行文档渲染，这使得录制的 SKP 对测试 Skia 的 Canvas 2D 渲染路径具有特殊价值。

## 架构位置

该文件属于 Skia SKP 页面集合（`tools/skp/page_sets/`），是需要身份验证的页面集类别中的唯一成员。它额外依赖 Telemetry 的登录辅助模块和凭据文件，增加了与其他简单页面集截然不同的复杂性。在页面集的认证需求分类中：
- **无需认证**：大多数页面集（ESPN、CNN、Amazon 等）
- **需要认证**：仅 Google Docs（本文件）

## 主要类与结构体

### `SkiaDesktopPage(page_module.Page)`
桌面端页面定义类，包含条件登录逻辑。

**属性**：
- `shared_page_state_class`：`SharedDesktopPageState`
- `archive_data_file`：`'data/skia_googledocs_desktop.json'`

**方法**：
- `RunNavigateSteps(action_runner)`：条件登录 + 导航 + 等待

### `SkiaGoogledocsDesktopPageSet(story.StorySet)`
页面集合定义。

**URL**：`https://docs.google.com/document/d/1X-IKNjtEnx-WW5JIKRLsyhz5sbsat3mfTpAPUSX3_s4/view`
**来源**：`go/skia-skps-3-2019`

## 公共 API 函数

| 方法 | 所属类 | 参数 | 描述 |
|------|--------|------|------|
| `__init__(url, page_set)` | SkiaDesktopPage | URL 和父页面集 | 初始化页面 |
| `RunNavigateSteps(action_runner)` | SkiaDesktopPage | Telemetry action_runner | 条件登录、导航、等待 |
| `__init__()` | SkiaGoogledocsDesktopPageSet | 无 | 初始化页面集 |

## 内部实现细节

1. **条件登录逻辑**：
   - 检查 `self.wpr_mode != wpr_modes.WPR_REPLAY`
   - 仅在录制模式（非回放模式）下执行 Google 登录
   - 回放模式跳过登录，因为 WPR 存档包含认证后的完整响应
2. **登录流程**：
   - 从 `data/credentials.json` 文件加载凭据
   - 调用 `google_login.BaseLoginGoogle(action_runner, 'google', credentials_path)` 执行登录
   - 登录后等待 15 秒确保认证完成
3. **页面导航**：导航到 Google Docs 文档 `/view` 模式 URL
4. **总等待时间**：最长可达 30 秒（登录后 15 秒 + 导航后 15 秒）
5. **额外导入**：除标准 Telemetry 导入外，还需要 `os`、`google_login` 和 `wpr_modes`

## 依赖关系

- **Telemetry 框架**：
  - `telemetry.story.StorySet`
  - `telemetry.page.page.Page`
  - `telemetry.page.shared_page_state.SharedDesktopPageState`
  - `telemetry.util.wpr_modes`
- **登录辅助**：`page_sets.login_helpers.google_login`
- **凭据文件**：`data/credentials.json`（包含 Google 账户认证信息）
- **Python 标准库**：`os`（用于构建凭据文件路径）
- **存档数据**：`data/skia_googledocs_desktop.json`

## 设计模式与设计决策

- **条件认证模式**：通过检查 WPR 模式智能决定是否执行登录。录制时需要真实登录以获取认证后的页面内容；回放时 WPR 存档已包含完整响应，无需登录。
- **凭据外部化**：登录凭据存储在独立 JSON 文件中，避免硬编码敏感信息。
- **文档查看模式**：使用 `/view` URL 而非编辑模式，因为查看模式不需要编辑权限且渲染行为更稳定可预测。
- **Canvas 渲染测试**：Google Docs 使用 Canvas 2D API 进行文档渲染，这与普通 DOM 渲染有本质不同，对 Skia 的 Canvas 实现是独特的测试。

## 性能考量

- 总等待时间最长可达 30 秒，是运行时间最长的页面集之一。
- Google Docs 的 Canvas 渲染生成大量低级绘图命令（文本、线条、矩形），SKP 文件可能很大。
- 文档的 Canvas 渲染对 Skia 的文本度量和文本绘制路径是密集测试。
- 登录流程中的网络请求增加了录制模式的耗时。

## 相关文件

- `tools/skp/page_sets/data/credentials.json`：Google 登录凭据
- `tools/skp/page_sets/data/skia_googledocs_desktop.json`：WPR 存档
- `page_sets/login_helpers/google_login.py`：Google 登录辅助模块
- `tools/skp/page_sets/skia_googlespreadsheet_desktop.py`：类似的 Google 产品页面集
