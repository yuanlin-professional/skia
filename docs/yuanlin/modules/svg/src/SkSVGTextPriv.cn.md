# SkSVGTextPriv - SVG 文本上下文内部定义

> 源文件: [`modules/svg/src/SkSVGTextPriv.h`](../../../modules/svg/src/SkSVGTextPriv.h)

## 概述

SkSVGTextPriv.h 定义了 SVG 文本渲染的核心内部类 `SkSVGTextContext`，它实现了 SVG 文本布局算法（SVG 1.1 规范第 10 章）。该类负责将输入文本字符序列化为"块"（chunk），管理文本整形、位置属性解析、路径跟随以及最终的文本块对齐和渲染。

SkSVGTextContext 同时实现了 `SkShaper::RunHandler` 接口，直接接收文本整形结果。

## 架构位置

位于 SVG 模块的内部实现层（私有头文件）：

- **调用者**: SkSVGText.cpp 中的文本渲染逻辑
- **实现接口**: SkShaper::RunHandler（接收整形回调）
- **输出**: 通过 ShapedTextCallback 回调输出 SkTextBlob

## 主要类与结构体

### `SkSVGTextContext` 类
文本上下文主类，继承自 `SkShaper::RunHandler`。

```cpp
class SkSVGTextContext final : SkShaper::RunHandler {
public:
    using ShapedTextCallback = std::function<void(const SkSVGRenderContext&,
                                                  const sk_sp<SkTextBlob>&,
                                                  const SkPaint*, const SkPaint*)>;
    void shapeFragment(const SkString&, const SkSVGRenderContext&, SkSVGXmlSpace);
    void flushChunk(const SkSVGRenderContext& ctx);
};
```

### `PosAttrs` 辅助类
位置属性编码器，使用 5 个 float 值存储 x, y, dx, dy, rotate。使用 infinity 作为"未设置"标记。区分显式旋转和隐式旋转（最后一个指定值的延续）。

```cpp
class PosAttrs {
    enum Attr { kX, kY, kDx, kDy, kRotate };
    float fStorage[5] = { kNone, kNone, kNone, kNone, kNone };
    bool  fImplicitRotate = false;
};
```

### `ScopedPosResolver` 类
级联位置属性解析器，实现 SVG 文本位置属性的层级查找：
- 每个文本容器元素（text/tspan）可指定任意长度的 x/y/dx/dy/rotate 数组
- 对每个字符，首先在本地数组中查找，找不到则沿祖先链回退
- 查找基于相对于文本子树的字符索引（跨块边界）

### `ShapeBuffer` 结构体
整形缓冲区，使用 STArray<128> 提供栈上快速存储。积累 UTF-8 字符和每字符的累积位置调整。

### `RunRec` 结构体
整形运行记录，包含字体、填充/描边画笔、字形 ID 数组、字形位置数组、位置调整数组、字形数量和前进量。

### `PathData` 类
文本路径数据缓存，存储路径的轮廓测量结果（SkContourMeasure 向量）和总长度，用于沿路径排列文本。

### `PositionAdjustment` 结构体
每字符的位置调整，包含偏移向量和旋转角度。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `shapeFragment(text, ctx, xmlSpace)` | 整形并排队一段文本 |
| `flushChunk(ctx)` | 执行最终对齐并将文本块推送到回调 |
| `getCallback()` | 获取整形文本回调 |

## 内部实现细节

### 文本块（Chunk）概念
根据 SVG 规范，新的文本块在以下情况下开始：
1. 每个顶级文本元素（`<text>`、`<textPath>`）
2. 遇到具有显式绝对位置属性的字符

文本块是对齐（text-anchor）的基本单位。

### SkShaper::RunHandler 实现
SkSVGTextContext 实现了 SkShaper 的回调接口：
- `beginLine()` / `commitLine()`: 空操作（SVG 文本不使用 SkShaper 的行概念）
- `runBuffer()`: 分配字形缓冲区
- `commitRunBuffer()`: 收集整形结果到 RunRec

### 位置调整累积
ShapeBuffer::append 中位置调整是累积的：每个字符的偏移量是前面所有字符调整之和。这简化了后续的定位计算。

### 字形变换计算
`computeGlyphXform` 根据位置调整和可选的路径数据计算每个字形的 RSXform（旋转+缩放+平移）。

### 路径文本
PathData 缓存多轮廓路径的测量数据，`getMatrixAt` 根据路径距离返回变换矩阵。

## 依赖关系

- `modules/skshaper/include/SkShaper.h` - 文本整形引擎和 RunHandler 接口
- `include/core/SkContourMeasure.h` - 路径测量
- `include/core/SkFont.h` / `SkPaint.h` - 字体和画笔
- `include/core/SkTextBlob.h` - 文本块输出

## 设计模式与设计决策

### RunHandler 直接集成
SkSVGTextContext 直接实现 SkShaper::RunHandler，避免了中间数据结构的开销。

### 链式位置解析器
ScopedPosResolver 使用链表式的父指针实现祖先链遍历，RAII 管理生命周期。

### 回调输出
使用 `ShapedTextCallback` 函数回调而非直接渲染，允许调用方灵活处理整形结果（如缓存、转发等）。

### 栈优化
ShapeBuffer 使用 STArray<128> 为典型的短文本提供栈上分配，避免堆分配开销。

## 性能考量

- STArray<128> 栈缓冲减少短文本的内存分配
- ScopedPosResolver 的 `fLastPosIndex` 缓存避免对高索引的无效查找
- 累积位置调整简化了最终定位计算（单次加法而非遍历）
- PathData 缓存路径测量，避免重复测量

## 相关文件

- `modules/svg/src/SkSVGText.cpp` - 文本渲染实现
- `modules/svg/include/SkSVGText.h` - 文本节点类声明
- `modules/svg/include/SkSVGRenderContext.h` - 渲染上下文
- `modules/skshaper/include/SkShaper.h` - 文本整形接口
