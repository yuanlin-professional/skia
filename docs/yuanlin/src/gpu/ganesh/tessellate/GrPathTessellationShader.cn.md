# GrPathTessellationShader

> 源文件: `src/gpu/ganesh/tessellate/GrPathTessellationShader.h`, `src/gpu/ganesh/tessellate/GrPathTessellationShader.cpp`

## 概述

`GrPathTessellationShader` 是 Ganesh GPU 细分填充路径的基类着色器。它提供两种实现：`SimpleTriangleShader`（简单三角形数组）和 `MiddleOutShader`（中间向外细分曲线）。后者使用 Wang 公式确定每条曲线所需的细分段数，支持二次曲线、三次曲线和圆锥曲线。还提供 Redbook 模板测试的标准设置。

## 架构位置

位于 Ganesh 细分（tessellation）子系统中，继承自 `GrTessellationShader`。它是 GPU 侧路径填充的核心着色器组件，与 `GrPathTessellator` 操作配合使用。该着色器不使用硬件细分阶段，而是通过实例化绘制和顶点着色器中的参数化求值实现软件细分。

## 主要类与结构体

### `GrPathTessellationShader`
- 继承自 `GrTessellationShader`
- 持有 `PatchAttribs fAttribs`（扇形点、颜色、显式曲线类型等）
- 定义 `Impl` 基类处理 uniform 矩阵和颜色

### `SimpleTriangleShader`（内部）
- 直接渲染三角形数组（float2 顶点）
- 用于简单的三角形扇形填充

### `MiddleOutShader`（内部）
- 使用中间向外拓扑细分曲线
- 实例属性：p01(float4), p23(float4), 可选的 fanPoint/color/curveType
- 顶点属性：resolveLevel_and_idx(float2)
- 在顶点着色器中求值 De Casteljau 算法

## 公共 API 函数

### 工厂方法
- `Make()` - 创建 `MiddleOutShader`（需要 GPU 支持 infinity 或提供显式曲线类型）
- `MakeSimpleTriangleShader()` - 创建 `SimpleTriangleShader`

### 模板设置
- `StencilPathSettings()` - 返回 Redbook "stencil" 通道的模板设置（winding 用 incr/decr，even-odd 用 invert）
- `TestAndResetStencilSettings()` - 返回 "fill" 通道的模板设置（非零测试并重置）

### 管线工具
- `MakeStencilOnlyPipeline()` - 创建不写颜色缓冲区的模板专用管线

## 内部实现细节

### 中间向外细分算法
1. 每个实例是一条曲线（4 个控制点 + 可选属性）
2. 每个顶点携带 `(resolveLevel, idxInResolveLevel)` 用于确定参数 T 值
3. 着色器使用 Wang 公式计算最大所需 resolveLevel
4. 超出所需级别的顶点通过降级产生退化三角形
5. 固定顶点 ID 被提升到最大分辨率级别以确保共位点精确匹配

### De Casteljau 求值
- 三次曲线：标准三级线性插值
- 圆锥曲线：带权重的有理求值 `abc/uv`
- 三角形圆锥曲线（退化）：直接选择控制点

### 曲线类型检测
- 有 infinity 支持时：`p23.w == Infinity` 表示圆锥曲线
- 无 infinity 支持时：使用额外的 `curveType` 属性

### Impl 基类
- 管理 `affineMatrix`（float4 uniform，包含 2x2 仿射矩阵）和 `translate`（float2 uniform）
- 可选的 `color` uniform（当颜色不在属性中时）
- `kEvalRationalCubicFn` 提供数值稳定的有理三次曲线求值

## 依赖关系

- **GrTessellationShader** - 基类
- **skgpu::tess::PatchAttribs** - 补丁属性标志
- **skgpu::tess::kPrecision / kMaxResolveLevel** - 细分精度常量
- **GrUserStencilSettings** - 模板测试设置
- **GrDisableColorXPFactory** - 模板专用管线的颜色处理

## 设计模式与设计决策

1. **软件细分**: 不依赖硬件细分阶段，通过实例化+顶点着色器实现，更广泛的硬件兼容性
2. **Wang 公式**: 运行时确定每条曲线的精确细分需求，避免过度或不足细分
3. **固定顶点 ID 对齐**: 确保不同 resolveLevel 的共位点产生完全相同的坐标，避免接缝
4. **Redbook 模板**: 使用经典的两步模板填充算法（stencil + fill）

## 性能考量

- 中间向外拓扑利用 GPU 并行性，广度优先递归避免了深度优先的数据依赖
- Wang 公式避免了过度细分，退化三角形被 GPU 自动丢弃
- 简单三角形着色器用于已三角化的数据，开销最小
- 仿射矩阵通过 uniform 传递，避免了逐顶点矩阵乘法

## 相关文件

- `src/gpu/ganesh/tessellate/GrTessellationShader.h` - 细分着色器基类
- `src/gpu/ganesh/tessellate/GrStrokeTessellationShader.h` - 描边细分着色器
- `src/gpu/tessellate/Tessellation.h` - 细分常量和工具
- `src/gpu/ganesh/GrUserStencilSettings.h` - 模板设置
