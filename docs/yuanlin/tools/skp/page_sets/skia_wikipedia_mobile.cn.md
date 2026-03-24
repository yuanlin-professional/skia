# skia_wikipedia_mobile

> 源文件: tools/skp/page_sets/skia_wikipedia_mobile.py

## 概述

`skia_wikipedia_mobile.py` 是 Skia 的移动端页面集定义文件,用于捕获 Wikipedia 移动版首页的 SKP 文件。该页面集专门测试移动设备上的文本密集型网页渲染,包括复杂的排版、多语言支持和响应式布局。Wikipedia 作为全球最大的在线百科全书,其移动版代表了信息类网站的典型渲染场景,是测试 Skia 文本渲染引擎和移动优化的重要基准。

## 架构位置

该文件位于 Skia 的移动端页面集目录,与其他移动测试页面集并列:

```
skia/tools/skp/page_sets/
  skia_wikipedia_mobile.py           # 本文件
  skia_wikipedia_desktop.py          # 桌面版对照
  skia_youtube_mobile.py             # 其他移动页面集
  data/
    skia_wikipedia_mobile.json       # WPR 配置
    skia_wikipedia_mobile_*.wprgo    # 移动流量档案
```

生成的 SKP 文件名为 `mobi_wikipedia.skp`,用于移动端性能回归测试。

## 主要类与结构体

### SkiaMobilePage 类

移动页面基类,配置移动浏览器环境:

**关键配置:**
- `shared_page_state_class`: 使用 `SharedMobilePageState` 模拟移动设备
- `archive_data_file`: `'data/skia_wikipedia_mobile.json'`

**移动环境特性:**
- 移动视口尺寸(通常 360x640 或 375x667)
- 移动 User-Agent
- 触摸事件支持
- 移动特定的浏览器标志

**`RunNavigateSteps(action_runner)` 方法:**
```python
action_runner.Navigate(self.url, timeout_in_seconds=120)
```

关键差异:
- **超时时间**: 120 秒(桌面版通常 15 秒)
- **原因**: 移动网络模拟较慢,Wikipedia 首页内容丰富
- **行为**: 导航后不显式等待,依赖导航超时机制

### SkiaWikipediaMobilePageSet 类

移动 Wikipedia 页面集定义:

**测试 URL:**
```python
urls_list = ['https://en.wikipedia.org/wiki/Wikipedia']
```

选择 Wikipedia 首页的原因:
- **文本密集**: 大量段落文本测试字体渲染
- **多语言链接**: 测试国际化文本处理
- **复杂排版**: 侧边栏、信息框、表格等布局
- **响应式设计**: 移动版使用不同的 CSS 和布局
- **图片优化**: 测试移动端图片缩放和懒加载

## 公共 API 函数

### Telemetry 接口

与 Telemetry 框架的集成点:

1. **页面集注册**: 通过文件名 `skia_wikipedia_mobile.py` 被发现
2. **移动模拟**: 使用 `SharedMobilePageState` 配置移动环境
3. **导航执行**: 调用 `RunNavigateSteps` 加载页面
4. **SKP 生成**: 在页面加载完成后捕获 `mobi_wikipedia.skp`

### 命名约定

- 输入文件: `skia_wikipedia_mobile.py`
- 解析规则: `skia` + `wikipedia` + `mobile`
- 输出文件: `mobi_wikipedia.skp` (mobile → mobi 前缀)

## 内部实现细节

### 超时策略

使用 120 秒超时而非固定等待时间:
- **优点**: 页面加载完成后立即继续,不浪费时间
- **缺点**: 如果页面有延迟内容,可能在超时前就返回
- **适用场景**: Wikipedia 的移动版优化良好,通常能快速加载完成

### SharedMobilePageState 配置

移动状态包含的配置:
- **设备仿真**: 模拟具体移动设备(如 Nexus 5、Pixel 3)
- **网络条件**: 可选模拟 3G/4G 网络延迟
- **屏幕旋转**: 支持竖屏/横屏测试
- **触摸输入**: 启用触摸事件而非鼠标事件

### pylint 配置

```python
# pylint: disable=W0401,W0614
```
与其他页面集相同,禁用通配符导入警告以适应 Telemetry 框架的约定。

## 依赖关系

### Chromium Telemetry 组件

- `telemetry.page.shared_page_state.SharedMobilePageState`: 移动环境模拟
- `telemetry.story.StorySet`: 故事集基类
- `telemetry.page.page_module.Page`: 页面基类

### 设备配置

移动测试可能依赖:
- Chrome 的移动设备仿真
- 特定的设备配置文件(device metrics)
- 移动 User-Agent 字符串

### WPR 档案

- `skia_wikipedia_mobile.json`: 移动版的 WPR 配置
- `skia_wikipedia_mobile_*.wprgo`: 移动流量档案(可能包含移动特定的 API 调用)

## 设计模式与设计决策

### 平台特化

通过独立的移动页面集文件实现平台特化:
- 独立的类定义(`SkiaMobilePage` vs `SkiaDesktopPage`)
- 不同的页面状态(`SharedMobilePageState` vs `SharedDesktopPageState`)
- 不同的超时和等待策略

### 超时优于等待

选择使用超时参数而非固定等待:
```python
# 移动版
action_runner.Navigate(self.url, timeout_in_seconds=120)

# vs 桌面版
action_runner.Navigate(self.url)
action_runner.Wait(15)
```

移动版策略更灵活:
- 快速加载时不浪费时间
- 慢速加载时有足够缓冲
- 避免在页面完全加载前就开始等待

### 真实 URL 测试

使用真实的 Wikipedia URL 而非测试页面:
- 测试真实世界的复杂性
- 包含 CDN、动态内容、第三方脚本
- 验证 Skia 在实际部署中的表现

## 性能考量

### 移动网络模拟

移动环境可能模拟网络限制:
- **带宽限制**: 模拟 3G/4G 速度
- **延迟增加**: 模拟移动网络往返时间
- **数据包丢失**: 模拟不稳定的移动连接

这导致需要更长的超时时间(120 秒)。

### 移动优化测试

Wikipedia 移动版的特点:
- **响应式图片**: 使用 `srcset` 提供不同尺寸
- **延迟加载**: 折叠下方内容延迟加载
- **精简 CSS**: 移动版使用更小的样式表
- **触摸优化**: 更大的点击区域和间距

### 文本渲染压力

Wikipedia 页面文本密集,测试以下渲染场景:
- **大量字形**: 数千个字符的排版
- **多语言**: 页面包含多种语言的链接
- **复杂布局**: 多列、浮动元素、表格
- **字体回退**: 测试缺失字形的回退机制

### SKP 文件大小

文本密集型页面可能产生较大的 SKP:
- 每个字形都记录在 SKP 中
- 复杂路径和蒙版操作
- 但相比图像密集型页面,仍然相对紧凑

## 相关文件

### 对照页面集

- `skia_wikipedia_desktop.py`: 桌面版 Wikipedia,用于对比桌面/移动差异
- `skia_wikipedia_*.py`: 其他 Wikipedia 相关测试

### 类似的移动页面集

- `skia_youtube_mobile.py`: 移动视频网站测试
- `skia_twitter_mobile.py`: 移动社交媒体测试(如存在)
- 其他 `*_mobile.py` 页面集

### 数据和输出

- `data/skia_wikipedia_mobile.json`: WPR 回放配置
- `data/skia_wikipedia_mobile_001.wprgo`: 移动流量档案
- `mobi_wikipedia.skp`: 生成的移动 SKP 文件
- `mobi_wikipedia.pdf`: 可选的 PDF 输出

### 框架和工具

- `webpages_playback.py`: 执行脚本
- Chromium 移动设备仿真器
- Chrome DevTools Protocol: 用于移动调试
