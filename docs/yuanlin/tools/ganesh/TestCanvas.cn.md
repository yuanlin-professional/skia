# TestCanvas

> 源文件: `tools/ganesh/TestCanvas.h`, `tools/ganesh/TestCanvas.cpp`

## 概述

TestCanvas 是 Skia 测试框架中用于测试 Slug 渲染路径的专用 Canvas 模板类系列。Slug 是 Skia Chromium 集成中文本渲染的中间表示形式，TestCanvas 通过拦截文本绘制调用并将其重定向到 Slug 管线，使得测试能够验证 Slug 渲染与传统 TextBlob 渲染的一致性。

该模块提供三种测试模式：直接 Slug 渲染、序列化/反序列化 Slug 渲染、远程 Strike Server/Client Slug 渲染。

## 架构位置

```
SkCanvas (基类)
  +-- TestCanvas<SkSlugTestKey>          (Slug 直接渲染)
  +-- TestCanvas<SkSerializeSlugTestKey> (Slug 序列化/反序列化)
  +-- TestCanvas<SkRemoteSlugTestKey>    (远程 Slug 渲染)
```

## 主要类与结构体

### `TestCanvas<SkSlugTestKey>`
将 GlyphRunList 转换为 Slug 后直接绘制

### `TestCanvas<SkSerializeSlugTestKey>`
将 GlyphRunList 转换为 Slug，序列化为字节，反序列化后绘制。验证序列化往返的正确性。

### `TestCanvas<SkRemoteSlugTestKey>`
模拟 Chrome 远程文本渲染流程：
- **ServerHandleManager**: 服务端的空操作句柄管理器
- **ClientHandleManager**: 客户端句柄管理器，在测试期间锁定 Strike 缓存
- 使用 `SkStrikeServer` 和 `SkStrikeClient` 模拟完整的远程字体渲染管线

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `TestCanvas(canvas)` | 构造函数，从目标 Canvas 的 rootDevice 初始化 |
| `onDrawGlyphRunList(glyphRunList, paint)` | 拦截文本绘制并重定向到 Slug 管线 |

## 内部实现细节

### Slug 直接渲染
1. 检查 quickReject 以跳过不可见文本
2. 设置 aboutToDraw 层
3. 如果 GlyphRunList 包含 RSXForm（旋转/缩放变换），回退到标准渲染
4. 否则转换为 Slug 并绘制

### 序列化渲染
在 Slug 直接渲染基础上增加序列化/反序列化步骤：Slug -> bytes -> Slug -> draw

### 远程渲染
模拟 Chrome 的 GPU 进程文本渲染：
1. 在 `SkStrikeServer` 的分析 Canvas 上创建 Slug
2. 序列化 Slug 和 Strike 数据
3. 在 `SkStrikeClient` 端反序列化 Strike 数据和 Slug
4. 绘制反序列化后的 Slug

### ClientHandleManager 的锁定机制
测试期间 `fIsLocked = false`（不删除句柄），析构时通过 `unlock()` 设为 `true`，允许 Strike 缓存释放。

## 依赖关系

- **Skia 核心**: `SkCanvas`, `SkDevice`
- **Chrome 远程字体**: `SkChromeRemoteGlyphCache` (SkStrikeServer, SkStrikeClient)
- **Slug**: `sktext::gpu::Slug`
- **文本**: `sktext::GlyphRun`, `GlyphRunList`

## 设计模式与设计决策

1. **模板特化**: 使用 Key 类型的模板特化而非继承来创建不同测试 Canvas，避免修改 SkCanvas 的 friend 列表
2. **RSXForm 回退**: 当文本包含旋转/缩放变换时回退到标准路径，因为 Slug 不支持此场景
3. **Strike 缓存生命周期**: 通过 ClientHandleManager 在测试期间锁定缓存，确保 Slug 渲染所需的字形数据不被驱逐

## 性能考量

- 远程模式的序列化/反序列化引入额外开销，仅用于测试验证
- `aboutToDraw` 确保正确的 Paint 层处理
- 分析 Canvas 使用 `DFTSupport=true` 启用距离场文本支持

## 相关文件

- `include/private/chromium/SkChromeRemoteGlyphCache.h` - 远程字形缓存
- `include/private/chromium/Slug.h` - Slug 定义
- `src/text/GlyphRun.h` - GlyphRunList 定义
