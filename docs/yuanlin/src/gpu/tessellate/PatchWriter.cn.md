# PatchWriter - GPU 曲线细分补丁写入器

> 源文件: `src/gpu/tessellate/PatchWriter.h`

## 概述

PatchWriter 是 Skia GPU 曲线细分系统的核心模板类，负责将曲线几何（三次贝塞尔、二次贝塞尔、圆锥曲线、直线、三角形）格式化为 GPU 可消费的"补丁"（patch）数据，并写入 GPU 缓冲区。

PatchWriter 使用模板特性（Traits）系统来配置编译时和运行时的行为差异。这种设计使得不同的细分渲染算法和 GPU 后端（Graphite 和 Ganesh）可以共享核心算法代码，同时通过模板特化获得最优性能。在内循环中，属性写入操作和数学计算都需要大量内联以获得可接受的性能，而算法变体之间的差异通常很小且发生在最内层循环中。

## 架构位置

```
Skia GPU 曲线细分系统
  -> PatchWriter<PatchAllocator, Traits...> (补丁写入器)
    -> WangsFormula (计算线段数)
    -> LinearTolerances (线性容差)
    -> PatchAllocator (GPU 缓冲区分配)
    -> MiddleOutPolygonTriangulator (三角形填充)
```

PatchWriter 是细分系统的数据输出层，将数学计算结果转化为 GPU 实例数据。它被路径渲染的各个阶段使用。

## 主要类与结构体

### `PatchWriter<PatchAllocator, Traits...>`
- **模板参数**:
  - `PatchAllocator`: GPU 缓冲区分配器类型，需提供 `append(LinearTolerances&)` 方法
  - `Traits...`: 可变参数特性包，配置属性和行为

### 特性类型（Traits）

#### 属性配置特性
| 特性 | 说明 |
|------|------|
| `Required<PatchAttribs::X>` | 编译时强制启用属性 X |
| `Optional<PatchAttribs::X>` | 属性 X 可在运行时启用/禁用 |

#### 行为配置特性
| 特性 | 说明 |
|------|------|
| `TrackJoinControlPoints` | 跟踪连接点，支持笔画的延迟补丁写入 |
| `AddTrianglesWhenChopping` | 在曲线切分时自动添加三角形填充空隙 |
| `DiscardFlatCurves` | 自动忽略只需一个线段的平坦曲线 |
| `ReplicateLineEndPoints` | 用 {a,a,b,b} 代替真正的线性三次方表示直线 |

### 辅助类型

#### `AttribValue<A, T, Required, Optional>`
- **职责**: 编译时/运行时属性值的统一存储和写入抽象
- **三种状态**: Required（始终写入）、Optional（条件写入）、Disabled（从不写入）
- **使用 `std::monostate`** 作为禁用状态的占位类型

#### `PatchStorage<Stride>`
- **职责**: 存储延迟写入的补丁数据（用于 `TrackJoinControlPoints`）
- **成员**: 首尾控制点、曲线类型、参数段数、补丁原始数据
- **状态机**: 通过 `fCurveType` 和 `fN_p4` 的符号编码多种状态

#### `NullTriangulator`
- **职责**: `AddTrianglesWhenChopping` 禁用时的空操作替代

## 公共 API 函数

### 构造和配置
| 函数 | 说明 |
|------|------|
| `PatchWriter(PatchAttribs, allocArgs...)` | 构造函数，传入属性掩码和分配器参数 |
| `attribs()` | 返回当前属性掩码 |
| `setShaderTransform(VectorXform, maxScale)` | 设置近似变换矩阵 |

### 属性更新
| 函数 | 启用条件 | 说明 |
|------|----------|------|
| `updateFanPointAttrib(SkPoint)` | FanPointAttrib 启用 | 更新扇形中心点 |
| `updateStrokeParamsAttrib(StrokeParams)` | StrokeAttrib 启用 | 更新笔画参数 |
| `updateUniformStrokeParams(StrokeParams)` | StrokeAttrib 启用 | 更新 uniform 笔画参数 |
| `updateColorAttrib(SkPMColor4f)` | ColorAttrib 启用 | 更新颜色 |
| `updatePaintDepthAttrib(float)` | DepthAttrib 启用 | 更新绘制深度 |
| `updateSsboIndexAttrib(uint32_t)` | SsboIndexAttrib 启用 | 更新 SSBO 索引 |
| `updateJoinControlPointAttrib(SkPoint)` | JoinAttrib 启用 | 更新连接控制点（已弃用） |

### 笔画延迟写入
| 函数 | 启用条件 | 说明 |
|------|----------|------|
| `writeDeferredStrokePatch(moveTo, cap)` | TrackJoinControlPoints | 完成延迟补丁，处理连接/端帽 |
| `closeDeferredStrokePatch(cap)` | TrackJoinControlPoints | 关闭轮廓的延迟补丁 |
| `writeDeferredStrokePatch()` | JoinAttrib（已弃用） | Ganesh 兼容接口 |

### 几何写入
| 函数 | 说明 |
|------|------|
| `writeCubic(p0, p1, p2, p3)` | 写入三次贝塞尔曲线 |
| `writeCubic(pts[4])` | 写入三次贝塞尔曲线（数组版本） |
| `writeConic(p0, p1, p2, w)` | 写入圆锥曲线 |
| `writeQuadratic(p0, p1, p2)` | 写入二次贝塞尔（自动转换为三次） |
| `writeLine(p0, p1)` | 写入直线（自动转换为三次） |
| `writeTriangle(p0, p1, p2)` | 写入三角形（编码为圆锥 w=inf） |
| `writeCircle(SkPoint)` | 写入圆形端帽（四个相同控制点的三次） |
| `writeSquare(SkPoint, joinTo)` | 写入方形端帽（三个相同控制点的圆锥） |

## 内部实现细节

### 补丁数据布局
每个补丁的数据布局为：
1. **4 个控制点**（8 floats）: 定义曲线几何
   - 二次贝塞尔转换为等价三次
   - 圆锥曲线在最后一个控制点存储 `{w, inf}`
   - 三角形在最后一个控制点存储 `{inf, inf}`
2. **启用的属性值**: 按 PatchAttribs 定义顺序排列，跳过禁用属性

### 曲线切分（Chopping）
当 Wang 公式计算出的所需段数超过 GPU 支持的最大值时：
1. `accountForCurve(n4)` 计算需要的切分次数
2. `chopAndWriteCubics/Quads/Conics` 将曲线参数化均匀切分
3. 切分使用 de Casteljau 算法的 SIMD 优化版本
4. 每次迭代从一端切分，批量处理 3 段或 2 段

### 切分时的三角形填充
当 `AddTrianglesWhenChopping` 启用时，切分后原始闭合边与新闭合边之间的空白区域会被自动填充三角形。使用 `MiddleOutPolygonTriangulator` 生成这些三角形。

### 延迟补丁机制（TrackJoinControlPoints）
笔画渲染中，每个补丁需要知道前一个补丁的最后控制点来确定连接方向。但第一个补丁在写入时没有前驱信息。解决方案：
1. 第一个补丁写入临时 CPU 缓冲区（`PatchStorage`）而非 GPU 缓冲区
2. 当轮廓关闭时，回填连接控制点信息
3. 通过 `writeDeferredStrokePatch` 将完整补丁刷写到 GPU

### mix 函数的数值稳定性
```cpp
static float4 mix(float4 a, float4 b, float4 T) {
    return (b - a)*T + a;  // 而非 a*(1-t) + b*t
}
```
使用 `(b-a)*T + a` 形式在 t=0 时精确返回 a，对于在精确尖点处切分的场景更加数值稳定。注意 t=1 时不保证精确返回 b，调用者需确保 t < 1。

### 退化曲线处理
`writePatch` 检测所有控制点相等的退化情况并跳过写入。对于笔画，退化曲线仍会设置 `fCurveType` 标记以便后续可能的端帽生成。

### 直线的两种编码方式
- `ReplicateLineEndPoints`: 编码为 `{a,a,b,b}`，着色器可轻松检测并假设只需一个段
- 默认: 编码为真正的线性三次方 `{a, 2/3a+1/3b, 1/3a+2/3b, b}`，Wang 公式理论返回 0

### MSVC 兼容性
由于 MSVC 19.24 不支持模板中的 constexpr 折叠表达式，使用 `DEF_ATTRIB_TYPE` 宏将模板参数提取为独立的 constexpr bool 常量。

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `src/gpu/tessellate/WangsFormula.h` | 计算曲线所需线段数 |
| `src/gpu/tessellate/LinearTolerances.h` | 管理线性容差 |
| `src/gpu/tessellate/Tessellation.h` | 细分常量（kMaxParametricSegments 等） |
| `src/gpu/tessellate/MiddleOutPolygonTriangulator.h` | 切分时的三角形填充 |
| `src/gpu/BufferWriter.h` | VertexWriter GPU 缓冲区写入 |
| `src/base/SkVx.h` | SIMD 向量类型 |
| `src/core/SkColorData.h` | VertexColor 类型 |

## 设计模式与设计决策

1. **编译时多态**: 通过模板特性包实现零开销的行为配置。不同的渲染策略和后端在编译时确定，内循环中无运行时分支。

2. **三态属性模型**: Required/Optional/Disabled 三种状态通过 `AttribValue` 模板抽象，在编译时消除禁用属性的所有代码（包括存储和写入）。

3. **延迟写入模式**: `TrackJoinControlPoints` 解决了笔画渲染中前驱信息不可用的经典问题，通过将第一个补丁暂存到 CPU 缓冲区实现。

4. **RAII 三角形栈**: `MiddleOutPolygonTriangulator::PoppedTriangleStack` 使用 RAII 模式，遍历三角形后自动更新内部栈状态。

5. **ENABLE_IF 条件方法**: 使用 SFINAE 根据特性启用/禁用方法，确保调用不支持的功能时产生编译错误而非运行时错误。

## 性能考量

1. **全内联**: 所有 `writeX` 方法和内部辅助方法标记 `SK_ALWAYS_INLINE`，确保热路径无函数调用开销。

2. **SIMD 切分**: `chopAndWriteCubics` 等方法使用 `float4` 进行 de Casteljau 计算，一次处理多个中间点。

3. **避免开方**: 使用 Wang 公式的 `_p4` 变体和 `nextlog16` 进行段数计算，避免 `sqrtf` 开销。

4. **状态跟踪最小化**: `fApproxTransform` 和属性值存储在 PatchWriter 中，避免每条曲线重复传递。

5. **批量切分**: `chopAndWriteCubics/Quads` 每次迭代处理 3 段（而非递归二分），减少了循环迭代次数和中间结果存储。

6. **kMaxStride 编译时常量**: 补丁最大步幅在编译时计算，用于 `PatchStorage` 的固定大小缓冲区，避免动态分配。

7. **VertexWriter 零拷贝**: 直接写入 GPU 映射内存，无中间缓冲区拷贝。

## 相关文件

- `src/gpu/tessellate/WangsFormula.h` - Wang 公式实现
- `src/gpu/tessellate/LinearTolerances.h` - 线性容差管理
- `src/gpu/tessellate/Tessellation.h` - 细分常量和类型定义
- `src/gpu/tessellate/MiddleOutPolygonTriangulator.h` - 多边形三角化
- `src/gpu/tessellate/StrokeIterator.h` - 笔画迭代器
- `src/gpu/BufferWriter.h` - GPU 缓冲区写入器
- `src/gpu/graphite/render/TessellateCurvesRenderStep.cpp` - Graphite 曲线渲染步骤
- `src/gpu/graphite/render/TessellateStrokesRenderStep.cpp` - Graphite 笔画渲染步骤

## 附录：补丁数据格式详解

### 曲线类型编码约定

PatchWriter 使用控制点的特殊值来区分不同的曲线类型：

| 曲线类型 | p3 编码 | 说明 |
|----------|---------|------|
| 三次贝塞尔 | 正常坐标 | 4 个控制点完整定义曲线 |
| 圆锥曲线 | `{w, inf}` | p0-p2 为 3 个控制点，w 为权重 |
| 三角形 | `{inf, inf}` | p0-p2 为 3 个顶点 |
| 直线 | 三次等价 | 转换为等价三次或端点复制形式 |

### 显式曲线类型（kExplicitCurveType）

当 `PatchAttribs::kExplicitCurveType` 启用时，每个补丁额外携带一个 float 标识曲线类型。这用于不支持 infinity 的着色器环境中替代上述隐式编码。

### 属性写入顺序

补丁属性在控制点之后按以下顺序写入（仅写入已启用的属性）：
1. JoinControlPoint (SkPoint)
2. FanPoint (SkPoint)
3. StrokeParams
4. Color (uint32/VertexColor/SkPMColor4f)
5. PaintDepth (float)
6. ExplicitCurveType (float)
7. SsboIndex (uint32)
