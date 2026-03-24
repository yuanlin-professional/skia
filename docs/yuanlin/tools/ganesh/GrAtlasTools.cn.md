# GrAtlasTools

> 源文件: `tools/ganesh/GrAtlasTools.h`, `tools/ganesh/GrAtlasTools.cpp`

## 概述

GrAtlasTools 提供了一组工具函数用于在测试中操作和调试 Ganesh 的纹理图集（Atlas）系统。纹理图集是 Skia GPU 渲染中管理字形、路径覆盖等小纹理的关键组件。这些工具允许转储图集内容为 PNG 文件、设置图集尺寸为最小值以及控制最大页面数，主要用于单元测试和调试。

## 架构位置

```
Ganesh 纹理图集系统
  +-- GrAtlasManager      (图集管理器)
  +-- GrDrawOpAtlas        (底层图集实现)
  +-- GrAtlasManagerTools  (测试工具) <-- 本文件
  +-- GrDrawOpAtlasTools   (底层图集测试工具) <-- 本文件
```

这些工具类通过直接访问 GrAtlasManager 和 GrDrawOpAtlas 的私有成员来实现功能（可能通过 friend 声明）。

## 主要类与结构体

### `GrAtlasManagerTools`
针对 `GrAtlasManager` 的静态工具方法

### `GrDrawOpAtlasTools`
针对 `GrDrawOpAtlas` 的静态工具方法

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `GrAtlasManagerTools::Dump(am, ctx)` | 将所有图集页面转储为 PNG 文件 |
| `GrAtlasManagerTools::SetAtlasDimensionsToMinimum(am)` | 重置图集为最小 1x1 plot 配置 |
| `GrAtlasManagerTools::SetMaxPages(am, maxPages)` | 设置所有图集的最大页面数 |
| `GrDrawOpAtlasTools::NumAllocated(doa)` | 查询已实例化的页面数 |
| `GrDrawOpAtlasTools::SetMaxPages(doa, maxPages)` | 设置底层图集最大页面数 |

## 内部实现细节

### Dump 实现
遍历所有掩码格式（`kMaskFormatCount`）的图集，读取每个活动页面的 SurfaceProxy 内容并编码为 PNG 文件。Android 上输出到 `/sdcard/fontcache_*.png`，其他平台输出到当前目录。使用全局计数器 `gDumpCount` 区分多次转储。

### save_pixels 辅助函数
1. 通过 `GrDirectContextPriv::makeSC` 创建 SurfaceContext
2. 读取像素到 RGBA8888 格式的 SkBitmap
3. 使用 SkPngEncoder 编码输出

### SetAtlasDimensionsToMinimum
删除所有现有图集（要求不在 flush 中间调用），然后使用默认构造的 `GrDrawOpAtlasConfig` 重置配置，使每个图集仅有 1x1 plot。

### SetMaxPages
要求在页面尚未分配时调用（`!fNumActivePages`），直接修改 `fMaxPages`。

## 依赖关系

- **Ganesh 内部**: `GrAtlasManager`, `GrDrawOpAtlas`, `GrDirectContextPriv`, `GrSurfaceProxy`
- **Skia 核心**: `SkBitmap`, `SkPngEncoder`, `SkStream`

## 设计模式与设计决策

1. **友元工具类**: 通过 friend 声明访问管理器私有成员，将测试/调试代码与生产代码分离
2. **静态方法**: 所有方法均为静态，无实例状态，作为纯工具函数使用
3. **仅测试用途**: 这些操作在生产环境中不安全（如 SetAtlasDimensionsToMinimum 删除所有图集）

## 性能考量

- Dump 操作涉及 GPU readback 和 PNG 编码，开销较大，仅用于调试
- SetAtlasDimensionsToMinimum 用于测试图集溢出和页面分配逻辑

## 相关文件

- `src/gpu/ganesh/text/GrAtlasManager.h` - 图集管理器
- `src/gpu/ganesh/GrDrawOpAtlas.h` - 底层图集实现
- `src/gpu/ganesh/SurfaceContext.h` - GPU 表面上下文
