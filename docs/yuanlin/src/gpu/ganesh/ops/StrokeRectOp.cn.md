# StrokeRectOp

> 源文件: `src/gpu/ganesh/ops/StrokeRectOp.h`, `src/gpu/ganesh/ops/StrokeRectOp.cpp`

## 概述

`StrokeRectOp` 命名空间提供了一组工厂函数，用于创建描边矩形的绘制操作。它包含两种实现：`NonAAStrokeRectOp`（非抗锯齿描边，使用三角形条带或线条条带）和 `AAStrokeRectOp`（Coverage AA 描边，使用精心构建的多层矩形几何体实现覆盖率渐变）。还提供 `MakeNested` 用于绘制两个矩形之间的区域。

## 架构位置

位于 Ganesh 操作（ops）层，属于特化的矩形绘制操作。它在 `SurfaceDrawContext` 中被直接调用来处理矩形描边请求。对于可以表示为轴对齐矩形的描边，该操作比通用路径渲染器更高效。

## 主要类与结构体

### `NonAAStrokeRectOp`
- 使用三角形条带（有宽度描边）或线条条带（发线描边）
- 10 个顶点的三角形条带围绕矩形形成描边
- 支持 MSAA 但不支持 Coverage AA

### `AAStrokeRectOp`
- 使用四层嵌套矩形创建覆盖率渐变
- 支持 miter 和 bevel 接缝
- 使用索引缓冲区模式（miter: 16 顶点/72 索引，bevel: 24 顶点/108 索引）
- 支持操作合并和宽色域

### `RectInfo`（AAStrokeRectOp 内部）
- 包含颜色、设备空间外矩形、内矩形、半描边尺寸和退化标志

## 公共 API 函数

### `Make()`
根据 AA 类型选择创建 `AAStrokeRectOp` 或 `NonAAStrokeRectOp`。

### `MakeNested()`
创建绘制两个嵌套矩形之间区域的操作。当内矩形为空或退化时，回退到 `FillRectOp`。

## 内部实现细节

### 非 AA 描边
- `init_nonaa_stroke_rect_strip()` 生成内外偏移的 10 顶点条带
- 发线描边使用 5 顶点的线条条带
- 当描边宽度超过矩形宽度/高度时，中间顶点坍缩到中心

### AA 描边几何生成
- 四层矩形：外 AA 边缘（outerCoverage=0）-> 外描边边缘（innerCoverage）-> 内描边边缘（innerCoverage）-> 内 AA 边缘（interiorCoverage）
- 亚像素描边：当描边宽度小于 1 像素时，通过调整 inset/coverage 模拟更窄的描边
- MSAA 支持：扩展 AA bloat 确保部分覆盖的像素有完整采样掩码
- Bevel 描边使用两个重叠矩形的八边形外轮廓
- 退化描边（内矩形坍缩）使用特殊处理避免双重覆盖

### 索引缓冲区缓存
- Miter 和 Bevel 使用不同的索引模式，各缓存 256 个矩形的索引缓冲区
- `PatternHelper` 处理实例化的索引绘制

### 接缝类型支持
- `allowed_stroke()` 检查支持的接缝类型：miter、bevel（仅 AA）、发线
- Round 接缝不支持
- 当 miter 限制使 miter 实际变为 bevel 时，非 AA 模式下拒绝

## 依赖关系

- **GrMeshDrawOp** - 操作基类
- **GrDefaultGeoProcFactory** - 创建几何处理器（支持颜色/覆盖率属性）
- **GrSimpleMeshDrawOpHelper** - 管线和处理器设置辅助
- **FillRectOp** - `MakeNested` 中内矩形退化时的回退方案
- **GrQuad** - `MakeNested` 中创建四边形描述

## 设计模式与设计决策

1. **AA/非 AA 分离**: 两种完全不同的实现针对不同的 AA 需求进行优化
2. **操作合并**: `AAStrokeRectOp` 支持合并兼容的描边操作，减少绘制调用
3. **视口裁剪**: 大坐标矩形会被裁剪到视口加上描边宽度的范围，避免浮点精度问题
4. **覆盖率作为 alpha**: 在非 MSAA 场景下尝试将覆盖率折叠到 alpha 通道，减少混合操作

## 性能考量

- 非 AA 描边仅需 10 个顶点的简单条带，极其高效
- AA 描边通过索引缓冲区缓存和实例化绘制支持高效的批量处理
- 亚像素描边不退化为不可见，而是通过覆盖率调整保持可见性
- MSAA 额外 bloat 确保正确性但增加了少量过度绘制

## 相关文件

- `src/gpu/ganesh/ops/GrMeshDrawOp.h` - 网格绘制操作基类
- `src/gpu/ganesh/ops/FillRectOp.h` - 填充矩形操作
- `src/gpu/ganesh/GrDefaultGeoProcFactory.h` - 默认几何处理器工厂
- `src/gpu/ganesh/SurfaceDrawContext.h` - 表面绘制上下文
