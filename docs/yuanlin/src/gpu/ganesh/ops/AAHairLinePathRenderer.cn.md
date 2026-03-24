# AAHairLinePathRenderer

> 源文件
> - src/gpu/ganesh/ops/AAHairLinePathRenderer.h
> - src/gpu/ganesh/ops/AAHairLinePathRenderer.cpp

## 概述

`AAHairLinePathRenderer` 是 Skia Ganesh GPU 后端的专用路径渲染器，用于渲染具有抗锯齿效果的细线（hairline）路径。Hairline 是宽度为 0 或接近 0 的描边，在任何缩放下都保持 1 像素宽度。该渲染器通过精心设计的几何体膨胀和覆盖率计算，在 GPU 上实现高质量的抗锯齿细线渲染。

该渲染器将路径分解为直线段、二次曲线和圆锥曲线，为每种图元类型生成专门的几何体和着色器。支持透视变换、局部坐标、模板测试等高级特性，能够处理复杂的路径渲染场景。

## 架构位置

```
Skia GPU 渲染架构:
├── PathRenderer 系统
│   ├── AALinearizingConvexPathRenderer
│   ├── AAHairLinePathRenderer ← 本类
│   ├── AtlasPathRenderer
│   └── DefaultPathRenderer
├── GrOp 操作层
│   └── AAHairlineOp (内部实现)
├── 几何处理器
│   ├── GrDefaultGeoProcFactory (直线)
│   ├── GrQuadEffect (二次曲线)
│   └── GrConicEffect (圆锥曲线)
└── 几何工具
    └── GrPathUtils
```

## 主要类与结构体

### AAHairLinePathRenderer 类

继承自 `PathRenderer`，提供细线路径渲染能力。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| 无公共成员变量 | - | 无状态渲染器，所有状态在生成的 Op 中 |

### AAHairlineOp 类（内部实现）

继承自 `GrMeshDrawOp`，封装实际的细线绘制操作。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fPaths` | `STArray<1, PathData, true>` | 待渲染的路径数据数组 |
| `fHelper` | `GrSimpleMeshDrawOpHelperWithStencil` | 操作辅助工具 |
| `fColor` | `SkPMColor4f` | 预乘 alpha 颜色 |
| `fCoverage` | `uint8_t` | 覆盖率值（0-255） |
| `fCharacterization` | `Program` | 所需的程序类型掩码 |
| `fMeshes[3]` | `GrSimpleMesh*[3]` | 三种图元类型的网格 |
| `fProgramInfos[3]` | `GrProgramInfo*[3]` | 三种图元类型的程序信息 |

### PathData 结构体

存储单个路径的渲染参数：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fViewMatrix` | `SkMatrix` | 视图变换矩阵 |
| `fPath` | `SkPath` | 待渲染的路径对象 |
| `fDevClipBounds` | `SkIRect` | 设备空间裁剪边界 |
| `fCapLength` | `SkScalar` | 端点帽长度（用于零长度线段） |

### LineVertex 结构体

直线段顶点数据：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fPos` | `SkPoint` | 顶点位置 |
| `fCoverage` | `float` | 抗锯齿覆盖率 |

### BezierVertex 结构体

贝塞尔曲线顶点数据（联合体支持二次曲线和圆锥曲线）：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fPos` | `SkPoint` | 顶点位置 |
| `fConic.fKLM[3]` | `SkScalar[3]` | 圆锥曲线隐式方程系数 |
| `fQuadCoord` | `SkVector` | 二次曲线 UV 坐标 |

### Program 枚举

表示所需的程序类型：

| 标志位 | 值 | 说明 |
|-------|-----|------|
| `kNone` | 0x0 | 无程序 |
| `kLine` | 0x1 | 直线程序 |
| `kQuad` | 0x2 | 二次曲线程序 |
| `kConic` | 0x4 | 圆锥曲线程序 |

## 公共 API 函数

### PathRenderer 接口

```cpp
const char* name() const override
```
返回渲染器名称 "AAHairline"。

```cpp
CanDrawPath onCanDrawPath(const CanDrawPathArgs&) const override
```
判断是否可以渲染给定路径。支持条件：
- 覆盖率抗锯齿（`GrAAType::kCoverage`）
- Hairline 或等效描边
- 无 path effect（不处理虚线等效果）
- 路径只有直线段，或硬件支持着色器导数

```cpp
bool onDrawPath(const DrawPathArgs&) override
```
执行路径渲染，创建 `AAHairlineOp` 并添加到绘制上下文。

## 内部实现细节

### 几何体生成流程

`gather_lines_and_quads` 函数遍历路径并生成几何数据：

1. **直线（kLine）**：直接映射到设备空间
2. **二次曲线（kQuad）**：在最大曲率处分割，转换为设备/源空间
3. **三次曲线（kCubic）**：转换为多个二次曲线
4. **圆锥曲线（kConic）**：根据硬件能力转换为二次曲线或保留
5. **零长度线段**：使用 `capLength` 生成微小线段以渲染端点帽

### 直线几何体膨胀

`add_line` 函数为每条线段生成 6 个顶点：

```
p4                  p5
     p0         p1
p2                  p3
```

- **p0/p1**：中心线顶点，覆盖率 = 1.0（或长度调制）
- **p2-p5**：外围顶点，覆盖率 = 0.0，距离中心 1 像素
- **短线段优化**：长度 < 1 像素时，覆盖率按长度调制

顶点位置计算：
- 计算线段方向向量和正交向量
- 内顶点向内偏移半像素
- 外顶点向外偏移 1.5 像素

### 二次曲线几何体膨胀

`bloat_quad` 函数为每个二次曲线生成 5 个顶点：

```
         b0
    b

a0            c0
 a          c
  a1      c1
```

膨胀策略：
1. 计算边 `ab` 和 `bc` 的正交向量
2. 边缘顶点沿正交方向偏移 1 像素
3. 中间顶点通过两条平行线相交计算
4. 处理退化情况（共线、重合点）

### 二次曲线 UV 坐标

`set_uv_quad` 使用 `GrPathUtils::QuadUVMatrix` 计算 UV 坐标：
- 将二次曲线的标准参数空间映射到顶点
- 片段着色器使用 UV 坐标计算隐式方程
- 根据隐式值判断片段是否在曲线内

### 圆锥曲线隐式方程

`set_conic_coeffs` 计算圆锥曲线的 KLM 系数：
- 使用 `GrPathUtils::getConicKLM` 获取隐式方程参数
- 对每个顶点计算 `K`、`L`、`M` 值
- 片段着色器评估 `K^2 - LM` 判断内外

### 圆锥曲线分割

`chop_conic` 在最大曲率处分割圆锥曲线：
1. 使用 `SkFindQuadMaxCurvature` 找到分割点
2. 可能分割 1、2 或 3 次（原始 + 2 次子分割）
3. 目的：收紧裁剪，隐藏极薄圆锥曲线的误差

### 三次曲线转换

三次曲线通过 `GrPathUtils::convertCubicToQuads` 转换为二次曲线序列：
- **透视变换**：在源空间转换（需调整容差）
- **非透视**：在设备空间转换（容差 = 1 像素）
- 递归细分直到误差满足容差

### 二次曲线细分

`num_quad_subdivs` 决定细分次数：
- 计算曲线与弦的距离平方
- 根据距离阈值（175 像素）决定细分级别
- 最大细分 4 次（16 个子曲线）

`add_quads` 执行递归细分：
- 使用 `SkChopQuadAt` 在分数位置分割
- 逐步输出细分后的二次曲线
- 为每个子曲线计算 UV 坐标和膨胀几何体

### 索引缓冲区

两种预定义索引模式：

**直线段**（18 个索引，6 个三角形）：
```cpp
{ 0,1,3, 0,3,2, 0,4,5, 0,5,1, 0,2,4, 1,5,3 }
```

**二次曲线/圆锥曲线**（9 个索引，3 个三角形）：
```cpp
{ 0,1,2, 2,4,3, 1,4,2 }
```

使用模式化索引缓冲区（`findOrCreatePatternedIndexBuffer`），所有实例共享。

### 三种程序路径

`AAHairlineOp` 根据路径内容创建最多 3 种几何处理器：

1. **Line Program**：使用 `GrDefaultGeoProcFactory`，简单的位置+覆盖率
2. **Quad Program**：使用 `GrQuadEffect`，计算二次曲线隐式方程
3. **Conic Program**：使用 `GrConicEffect`，计算圆锥曲线隐式方程

每种程序有独立的网格和绘制调用。

### 透视处理

透视变换的特殊处理：
- **几何处理器视图矩阵**：使用实际视图矩阵
- **几何处理器局部矩阵**：使用单位矩阵
- **曲线坐标**：在源空间存储（避免透视插值问题）

非透视情况：
- **几何处理器视图矩阵**：单位矩阵
- **几何处理器局部矩阵**：视图矩阵的逆
- **曲线坐标**：在设备空间存储（简化细分）

### 零长度线段处理

当检测到零长度动词时：
- 如果在轮廓开始，标记为零长度
- 轮廓闭合时，如果只有一个动词，生成端点帽
- 端点帽是长度为 `capLength` 的 x 对齐线段

这实现了 SVG Spec 11.4 对零长度子路径的描边要求。

## 依赖关系

### 依赖的模块

| 模块 | 依赖关系 | 说明 |
|------|---------|------|
| `PathRenderer` | 继承 | 路径渲染器基类 |
| `GrMeshDrawOp` | 继承 | 网格绘制操作基类 |
| `GrDefaultGeoProcFactory` | 强依赖 | 创建直线几何处理器 |
| `GrBezierEffect` | 强依赖 | 二次曲线和圆锥曲线效果 |
| `GrPathUtils` | 强依赖 | 路径几何工具（曲率、转换等） |
| `GrSimpleMeshDrawOpHelperWithStencil` | 强依赖 | 操作辅助工具 |

### 被依赖的模块

| 模块 | 依赖类型 | 说明 |
|------|---------|------|
| `SurfaceDrawContext` | 使用 | 通过路径渲染器链选择此渲染器 |
| `PathRendererChain` | 注册 | 作为可选路径渲染器之一 |

## 设计模式与设计决策

### 1. 多程序架构

使用 3 个独立的几何处理器而非单个通用处理器：
- **优点**：每种图元类型优化的着色器
- **缺点**：增加程序数量和状态切换
- **权衡**：性能优于状态切换开销

### 2. 几何体膨胀策略

在 CPU 端生成膨胀几何体：
- **直线**：6 顶点六边形，边缘渐变覆盖率
- **曲线**：5 顶点五边形，边界紧密包围曲线

避免了片段着色器中的距离计算，利用硬件插值实现抗锯齿。

### 3. 隐式曲线评估

二次曲线和圆锥曲线使用隐式方程：
- **优点**：片段着色器高效评估
- **实现**：Loop-Blinn 算法的 GPU 适配
- **精度**：利用导数避免数值不稳定

### 4. 自适应细分

根据曲率和容差动态决定细分级别：
- 小曲率：无细分或少量细分
- 大曲率：最多细分 4 次
- 目的：平衡质量和顶点数量

### 5. 透视空间选择

透视变换时在源空间处理曲线：
- **原因**：透视后的插值不是线性的
- **代价**：几何处理器需要应用透视矩阵
- **效果**：保证曲线评估的正确性

### 6. 圆锥曲线转换选项

根据硬件能力选择圆锥曲线处理：
- **支持 32 位浮点数**：使用专门的圆锥曲线着色器
- **仅 16 位浮点数**：转换为二次曲线（避免精度问题）

### 7. 退化情况处理

全面处理退化路径：
- **共线点**：转换为直线
- **重合点**：生成离屏顶点（避免崩溃）
- **零长度线段**：生成端点帽

### 8. 端点帽实现

通过生成微小线段实现端点帽：
- **Butt Cap**：`capLength = 0`，无额外线段
- **Round/Square Cap**：`capLength = hairlineCoverage * 0.5`
- **优点**：简单、与主渲染路径一致

## 性能考量

### 1. 批处理优化

通过 `onCombineIfPossible` 合并兼容的细线操作：
- 减少绘制调用次数
- 共享几何处理器和管线
- 要求颜色、覆盖率、视图矩阵等匹配

### 2. 索引缓冲区复用

使用全局共享的模式化索引缓冲区：
- 直线和曲线各一个索引缓冲区
- 通过 `SKGPU_DECLARE_STATIC_UNIQUE_KEY` 单例化
- 避免重复分配和传输索引数据

### 3. 预分配数组

使用 `PREALLOC_PTARRAY` 预分配栈空间：
- 小路径无堆分配
- 大路径平滑增长
- 减少内存分配开销

### 4. 早期裁剪

在生成几何体前进行裁剪：
- 使用 `safeIBounds` 计算保守边界
- 与裁剪边界相交测试
- 完全裁剪的图元不生成顶点

### 5. SIMD 边界检查

`safeIBounds` 使用向量化操作：
- SIMD 计算边界框
- 快速相交测试
- 减少分支预测失误

### 6. 覆盖率编码

将覆盖率作为顶点属性：
- 利用硬件插值生成平滑渐变
- 避免片段着色器计算
- 支持子像素抗锯齿

### 7. 程序预测

`predictPrograms` 提前确定所需程序类型：
- 在 DDL 模式下用于程序预编译
- 避免运行时程序切换
- 保守预测（包含可能用不到的程序）

### 8. 短线段优化

长度 < 1 像素的线段使用长度调制覆盖率：
- 正确处理亚像素平移
- 避免过度覆盖
- 精确的亚像素渲染

### 9. 三次曲线转换缓存

使用局部数组存储转换后的二次曲线：
- `PREALLOC_PTARRAY(32)` 栈分配
- 避免逐个分配二次曲线
- 批量处理提高缓存局部性

### 10. 浮点数指数提取

`get_float_exp` 使用位操作提取浮点数指数：
- 比 `logf` 快 178 倍
- 用于计算对数空间的细分级别
- 避免昂贵的超越函数调用

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/PathRenderer.h` | 基类 | 路径渲染器抽象接口 |
| `src/gpu/ganesh/ops/GrMeshDrawOp.h` | 基类 | 网格绘制操作基类 |
| `src/gpu/ganesh/GrDefaultGeoProcFactory.h` | 依赖 | 创建直线几何处理器 |
| `src/gpu/ganesh/effects/GrBezierEffect.h` | 依赖 | 二次曲线和圆锥曲线效果 |
| `src/gpu/ganesh/geometry/GrPathUtils.h` | 依赖 | 路径几何工具 |
| `src/gpu/ganesh/ops/GrSimpleMeshDrawOpHelperWithStencil.h` | 辅助 | 操作创建和管线管理 |
| `src/gpu/ganesh/SurfaceDrawContext.h` | 使用者 | 表面绘制上下文 |
| `src/core/SkGeometry.h` | 依赖 | 几何计算工具（分割、曲率等） |
