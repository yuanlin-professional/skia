# GrStrokeTessellationShader

> 源文件: `src/gpu/ganesh/tessellate/GrStrokeTessellationShader.h`, `src/gpu/ganesh/tessellate/GrStrokeTessellationShader.cpp`

## 概述

`GrStrokeTessellationShader` 是 Ganesh 中用于 GPU 描边细分的着色器。它将描边补丁（stroke patches）直接在顶点着色器中细分为三角形条带，通过在曲线沿线的特定位置生成描边宽度的正交边，并按参数化和径向边的排序组合来精确描绘任意曲率的描边曲线。支持动态描边参数、动态颜色、所有接缝类型（miter、bevel、round）以及发线描边。

## 架构位置

位于 Ganesh 细分子系统中，继承自 `GrTessellationShader`。它与 `GrStrokeTessellator` 配合使用，是 GPU 描边渲染的核心着色器。使用固定数量的边（通过预分配顶点缓冲区）和实例化绘制实现。

## 主要类与结构体

### `GrStrokeTessellationShader`
- 继承自 `GrTessellationShader`
- 使用 `GrPrimitiveType::kTriangleStrip` 作为图元类型
- 持有 `PatchAttribs fPatchAttribs`（接缝控制点、描边参数、颜色、曲线类型）
- 持有 `SkStrokeRec fStroke`（描边宽度、cap、join 类型）
- 实例属性：pts01(float4)、pts23(float4)、args(float2)、可选的 dynamicStroke/color/curveType

## 公共 API 函数

### 构造函数
```cpp
GrStrokeTessellationShader(const GrShaderCaps&, PatchAttribs, const SkMatrix& viewMatrix,
                           const SkStrokeRec&, SkPMColor4f);
```

### 属性查询
- `attribs()` - 补丁属性标志
- `hasDynamicStroke()` / `hasDynamicColor()` / `hasExplicitCurveType()` - 动态属性检查
- `stroke()` - 描边参数

## 内部实现细节

### 细分算法核心思想
1. **参数化边**: 沿曲线参数 T 均匀分布，由 Wang 公式确定数量
2. **径向边**: 沿曲线旋转角均匀分布，由每弧度径向段数确定
3. **组合排序**: 使用二分搜索确定每个 `combinedEdgeID` 对应的最大参数化边
4. **最终 T 值**: 取参数化 T 和径向 T 中的较大值

### 接缝（Join）处理
- 接缝区域占用条带开头的边
- Round 接缝：按旋转角均匀细分 + 2 条重复边（首尾各一条，确保无缝拼接）
- Miter 接缝：扩展第 2 条边到 miter 点（当 miter limit 允许时）
- Bevel 接缝：1 段 + 2 条重复边
- 接缝单侧化：避免翻转法线产生不正确的覆盖

### 切线与正交向量计算
- `robust_normalize_diff()` - 处理大坐标差值的归一化
- `cosine_between_unit_vectors()` - 安全的余弦计算（clamp 到 [-1,1]）
- 起始/结束切线通过控制点差值计算，处理重合控制点的退化情况

### 发线描边
- 发线在细分前先变换到设备空间（`AFFINE_MATRIX * point`）
- 描边半径固定为 0.5 设备像素
- 最终坐标通过逆矩阵转换回局部空间

### 动态描边参数
- `dynamicStrokeAttr.x` = 描边半径
- `dynamicStrokeAttr.y` = 接缝类型
- `NUM_RADIAL_SEGMENTS_PER_RADIAN` 根据实例的描边半径动态计算

### 顶点 ID 与回退
- 有 `sk_VertexID` 支持时，最大边数 = `kMaxEdges`（uint16 限制）
- 无 `sk_VertexID` 时，使用 `edgeID` 顶点属性和更小的回退缓冲区

## 依赖关系

- **GrTessellationShader** - 基类
- **skgpu::tess::PatchAttribs** - 补丁属性标志
- **skgpu::tess::FixedCountStrokes** - 固定数量缓冲区常量
- **skgpu::tess::CalcNumRadialSegmentsPerRadian** - 径向段数计算
- **SkStrokeRec** - 描边参数

## 设计模式与设计决策

1. **参数化+径向组合**: 创新的描边细分方法，能处理任意曲率而不需要预分割曲线
2. **固定顶点计数**: 每个实例使用固定数量的顶点，多余的产生退化三角形，简化了缓冲区管理
3. **二分搜索**: 在顶点着色器中使用 `kMaxResolveLevel` 次迭代的二分搜索，确定参数化边位置
4. **接缝集成**: 接缝作为条带的一部分，避免了单独的接缝绘制
5. **重复首尾边**: 确保接缝与相邻描边段的顶点精确匹配

## 性能考量

- 固定顶点计数允许实例化绘制，减少绘制调用
- Wang 公式和径向段数确保不过度细分
- 发线描边在变换后细分，避免非均匀缩放问题
- 顶点着色器中的二分搜索循环次数固定（`kMaxResolveLevel`），可预测性好
- 动态描边/颜色通过实例属性传递，支持异构描边的批量渲染

## 相关文件

- `src/gpu/ganesh/tessellate/GrTessellationShader.h` - 细分着色器基类
- `src/gpu/ganesh/tessellate/GrPathTessellationShader.h` - 路径细分着色器
- `src/gpu/tessellate/Tessellation.h` - 细分常量和 Wang 公式
- `src/gpu/tessellate/FixedCountBufferUtils.h` - 固定计数缓冲区工具
