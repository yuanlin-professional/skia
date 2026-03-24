# ContextOptionsPriv - Graphite 上下文私有选项

> 源文件: `src/gpu/graphite/ContextOptionsPriv.h`

## 概述

`ContextOptionsPriv` 是 Skia Graphite 中仅供内部测试使用的上下文配置选项结构体。与公共的 `ContextOptions` 不同，该结构体中的选项专门用于 Skia 工具和测试环境，不应在生产代码中使用。这些选项提供了纹理大小覆盖、Recorder 反向引用、图层排序以及路径渲染器策略等调试/测试功能。

## 架构位置

```
Context 配置体系
  ├── ContextOptions (公共配置)
  │     └── ContextOptionsPriv* fOptionsPriv (可选的私有配置指针)
  └── ContextOptionsPriv (本文件 - 测试专用配置)
        ├── 纹理大小覆盖
        ├── Recorder-Context 反向引用
        ├── 图层排序开关
        └── 路径渲染策略覆盖
```

## 主要类与结构体

### `ContextOptionsPriv`

测试专用上下文选项结构体，包含以下字段：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fMaxTextureSizeOverride` | `int` | `SK_MaxS32` | 覆盖 Caps 报告的最大纹理尺寸 |
| `fStoreContextRefInRecorder` | `bool` | `false` | 在 Recorder 中存储指向 Context 的反向指针 |
| `fDrawListLayer` | `bool` | `false` | 启用基于图层的绘制排序 |
| `fPathRendererStrategy` | `optional<PathRendererStrategy>` | 空 | 覆盖 Caps 的路径渲染器策略 |

## 公共 API 函数

该结构体为纯数据类型（POD-like），没有方法。所有字段直接访问。

## 内部实现细节

### fMaxTextureSizeOverride

默认值 `SK_MaxS32` 意味着不覆盖 Caps 的实际报告值。设置较小的值可以在测试中模拟资源受限设备，验证纹理分块和降级路径。

### fStoreContextRefInRecorder

当设为 `true` 时，Recorder 会持有创建它的 Context 的指针。这使得 `readPixels()` 等通常需要 Context 参与的操作可以从 Recorder 直接执行，简化了测试代码。注意这在生产环境中不安全，因为 Context 的生命周期可能短于 Recorder。

### fDrawListLayer

启用实验性的图层排序优化。当为 `true` 时，绘制命令按图层组织而非严格的提交顺序，可能改善渲染效率。

### fPathRendererStrategy

`std::optional` 包装允许区分"未设置"和"设置为某个值"。仅当设置了值且该策略被后端支持时才生效，否则使用 Caps 的默认启发式选择。

## 依赖关系

- **include/private/base/SkMath.h**: `SK_MaxS32` 常量
- **\<optional\>**: `std::optional` 类型
- 前向声明: `PathRendererStrategy` 枚举

## 设计模式与设计决策

### 测试配置隔离

将测试选项从公共 `ContextOptions` 中分离出来是有意的设计决策。公共 API 保持简洁，测试特定的选项通过指针间接引用，避免暴露内部概念。

### Optional 语义

`fPathRendererStrategy` 使用 `std::optional` 而非哨兵值，提供了更清晰的"未设置/已设置"语义，避免了与合法枚举值冲突的风险。

## 性能考量

- 该结构体仅在 Context 创建时读取一次，对运行时性能没有直接影响
- `fMaxTextureSizeOverride` 影响资源分配策略，间接影响性能
- `fDrawListLayer` 可能改变绘制命令的排序和批处理方式

## 相关文件

- `include/gpu/graphite/ContextOptions.h` - 公共上下文选项
- `src/gpu/graphite/ContextPriv.h` - Context 内部访问接口
- `src/gpu/graphite/Caps.h` - GPU 能力查询（PathRendererStrategy）
- `src/gpu/graphite/RecorderPriv.h` - Recorder 内部访问（使用 Context 反向引用）
