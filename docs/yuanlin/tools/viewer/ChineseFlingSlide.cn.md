# ChineseFlingSlide - 中文文本滚动性能测试幻灯片

> 源文件: `tools/viewer/ChineseFlingSlide.cpp`

## 概述

ChineseFlingSlide.cpp 实现了三个用于测试中文文本渲染性能的 Viewer 幻灯片：ChineseFlingSlide（快速滑动）、ChineseZoomSlide（缩放）和 ChineseScrollSlide（平滑滚动）。这些幻灯片通过大量唯一的 CJK 字符（Unicode 0x4F00-0x9FA0 范围）对字体图集（font atlas）缓存系统进行压力测试。

## 架构位置

位于 `tools/viewer/` 目录，属于 Skia Viewer 应用程序的演示幻灯片集。

## 主要类与结构体

### `ChineseFlingSlide` - 快速滑动模拟
- 200 个预生成的 TextBlob（每个 16 字符）
- 每帧随机跳过 5-20 个 blob，模拟快速滑动

### `ChineseZoomSlide` - 缩放测试
- 8 个段落 blob（每段 175 字符）
- 支持 `>/<` 键调整缩放比例
- 在 GPU 模式下可视化字体图集纹理

### `ChineseScrollSlide` - 平滑滚动
- 50 个 blob（每个 6 行 x 45 字符）
- 确保所有字形唯一，加速缓存淘汰
- 支持 `,/.` 键调整滚动速度（2^n 形式）

## 公共 API 函数

所有类继承 Slide 接口：`load()`, `draw()`, `animate()`, `onChar()`

## 内部实现细节

- `chinese_typeface()` 根据平台选择合适的中文字体（如 macOS 用 "Hiragino Sans GB W3"）
- ChineseScrollSlide 使用 `THashSet` 确保字形不重复，迫使字体图集不断增长和淘汰
- 滚动使用周期函数实现无缝重复

## 依赖关系

- `include/core/SkTextBlob.h`, `SkFontMgr.h` - 文本渲染
- `src/gpu/MaskFormat.h` - 字体图集 mask 格式
- Ganesh GPU 后端（可选，用于图集可视化）

## 设计模式与设计决策

- **压力测试设计**: 大量唯一字形迫使字体缓存持续工作
- **平台适配**: 根据构建目标自动选择中文字体

## 性能考量

- 专门设计用于暴露字体图集管理的性能瓶颈
- ChineseScrollSlide 的唯一字形策略可测试缓存淘汰效率

## 相关文件

- `tools/viewer/Slide.h` - Slide 基类
- `tools/viewer/AnimatedTextSlide.cpp` - 另一个文本性能测试
