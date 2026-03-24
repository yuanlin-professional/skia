# VariableWidthStrokerSlide 可变宽度描边器演示

> 源文件: `tools/viewer/VariableWidthStrokerSlide.cpp`

## 概述

此文件实现了一个原型级别的可变宽度路径描边器（Variable Width Stroker）及其交互式演示 Slide。该描边器基于 Elber-Cohen 算法，能够将输入路径按照任意距离函数（而非固定宽度）生成描边填充路径。这是对传统固定宽度描边的重大扩展，支持沿路径变化的笔触宽度。演示 Slide 提供了交互式的控制面板，允许用户调整路径控制点、描边宽度和距离函数参数。

## 架构位置

- 所属模块：`tools/viewer/`（Skia Viewer 工具）
- 角色：研究性原型和交互式演示
- 算法来源：G. Elber, E. Cohen 的曲线偏移算法（1991-1992）

## 主要类与结构体

### `ScalarBezCurve`（标量贝塞尔曲线）
通用的任意阶标量贝塞尔曲线类，用于表示距离函数和误差函数。

**核心字段：**
- `fDegree`：曲线阶数
- `fWeights`：控制点权重向量

**主要功能：**
- 求值（de Casteljau 算法）
- 分裂（Split）
- 升阶（Degree Elevation）
- 乘法（曲线相乘）
- 零集求解（递归二分法）

### `PathVerbMeasure`（路径分段测量器）
辅助类，逐动词（verb）测量路径长度。

**核心字段：**
- `fPath`：被测量的路径
- `fIter`：路径迭代器
- `fMeas`：路径测量器

### `SkVarWidthStroker`（可变宽度描边器）
核心描边器类，实现 Elber-Cohen 偏移曲线算法。

**核心字段：**
- `fRadius`、`fCap`、`fJoin`：描边参数
- `fInner`、`fOuter`：内外轮廓路径构建器
- `fVarWidth`、`fVarWidthInner`：内外距离函数
- `fCurrT`：当前参数值

**内部结构：**
- `PathSegment`：路径段（verb + 控制点）
- `OffsetSegments`：偏移结果（内外路径段集合）
- `LengthMetric`：长度度量枚举（段数/路径长度）

### `VariableWidthStrokerSlide`
交互式演示 Slide，继承自 `ClickHandlerSlide`。

**核心字段：**
- `fPathPts[5]`：5 个可拖动的路径控制点
- `fWidth`：描边宽度
- `fDistFncs`/`fDistFncsInner`：距离函数菜单项
- `fLengthMetric`：插值度量方式
- 多个显示标志和画笔

## 公共 API 函数

### ScalarBezCurve 静态方法
| 方法 | 描述 |
|------|------|
| `Eval(curve, t)` | De Casteljau 求值 |
| `Split(curve, t, left, right)` | 在参数 t 处分裂曲线 |
| `ElevateDegree(curve, newDeg)` | 升阶到指定阶数 |
| `Mul(curve, f)` | 标量乘法 |
| `Mul(a, b)` | 两曲线相乘（阶数为和） |
| `AddSquares(a, b)` | 计算 a^2 + b^2 |
| `Sub(a, b)` | 曲线减法 |
| `ZeroSet(curve)` | 计算零集（过零参数值） |

### SkVarWidthStroker 方法
| 方法 | 描述 |
|------|------|
| `getFillPath(path, paint)` | 使用固定宽度描边 |
| `getFillPath(path, paint, varWidth, varWidthInner, metric)` | 使用可变宽度描边 |

### 辅助函数
| 函数 | 描述 |
|------|------|
| `rotate90(p)` | 向量旋转 90 度 |
| `rotate180(p)` | 向量旋转 180 度 |
| `isClockwise(a, b)` | 判断两向量是否顺时针 |
| `choose(n, k)` | 组合数计算 |

## 内部实现细节

### Elber-Cohen 偏移算法
1. 对路径的每个段（线段/二次/三次贝塞尔）：
   - 使用控制多边形变换生成初始二次近似
   - 计算误差函数 eps(t) = delta_x^2 + delta_y^2 - d(t)^2
   - 如果最大误差超过容差，二分细化
   - 否则接受近似结果
2. 递归细化使用栈而非递归调用，上限为 5000 次迭代

### 距离函数处理
- 距离函数表示为标量贝塞尔曲线，可以是任意阶数
- 在路径遍历过程中，距离函数按当前段的参数区间子集化
- 支持两种插值度量：按段数均分或按路径长度比例分配

### 接合（Join）处理
- 当前仅实现了斜接接合（Miter Join）
- 接合需要分别处理左右两侧，因为可变宽度下两侧可能都需要外接合或内接合
- 使用半角公式计算斜接长度

### 端点（Cap）处理
- 当前仅实现了平头端点（Butt Cap）
- 开放轮廓在末端用直线连接内外轮廓

### 近似策略（Yzerman 方法）
- 使用 F. Yzerman 2019 年的方法进行简单的控制多边形变换
- 在段的起点、中点和终点计算法向偏移
- 生成二次贝塞尔近似

## 依赖关系

- Skia 核心：`SkPath`、`SkPathBuilder`、`SkPathMeasure`、`SkCanvas`
- Skia 内部：`SkGeometry`（`SkEvalCubicAt`）
- ImGui：交互式 UI 面板
- STL：`<stack>`、`<vector>`
- Viewer 框架：`ClickHandlerSlide`

## 设计模式与设计决策

- **研究原型定位**：代码中有大量 TODO 标记和未处理的边界情况，明确定位为原型而非生产代码
- **递归转迭代**：偏移算法使用显式栈（`std::stack`）而非递归，避免深度递归的栈溢出
- **曲线代数基础**：大量使用贝塞尔曲线的代数性质（乘法、升阶、零集），体现了符号-数值混合计算的学术方法
- **可视化调试**：通过 `viz` 命名空间提供调试用的误差曲线和首次近似可视化
- **ImGui 交互**：使用 ImGui 提供实时参数调节界面，适合研究和演示

## 性能考量

- 偏移算法的 5000 次迭代上限可能在复杂路径上成为瓶颈
- 贝塞尔曲线乘法的复杂度为 O(n*m)（n, m 为两曲线的阶数），升阶后阶数会快速增长
- 组合数计算使用循环而非查表，对高阶曲线可能有性能影响
- 每帧重新计算完整描边路径，无增量更新优化
- `ScalarBezCurve` 使用 `std::vector<float>` 存储权重，频繁的堆分配可能影响性能

## 相关文件

- `tools/viewer/ClickHandlerSlide.h` - Slide 基类
- `src/core/SkGeometry.h` - Skia 几何计算工具
- `include/core/SkPathMeasure.h` - 路径测量 API
- `include/core/SkPathUtils.h` - 路径工具
