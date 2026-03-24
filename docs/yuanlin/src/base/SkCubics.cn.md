# SkCubics - 三次方程求解器
> 源文件: `src/base/SkCubics.h`, `src/base/SkCubics.cpp`

## 概述
SkCubics 是一个专门用于求解三次方程（形如 f(t) = A*t³ + B*t² + C*t + D = 0）的工具类。该类提供了多种求根算法，包括标准的代数求解方法和二分搜索方法，并针对浮点精度问题进行了优化处理。它在 Skia 图形库中主要用于路径计算、曲线求交等几何运算场景。

## 架构位置
SkCubics 位于 Skia 的基础数学模块（src/base）中，属于底层数学工具集。它与二次方程求解器 SkQuads 协同工作，为上层的路径操作、贝塞尔曲线处理等模块提供核心的数学计算支持。

## 主要类与结构体

### SkCubics
纯静态工具类，提供三次方程的各种求解方法。

**继承关系**: 无继承关系，纯静态工具类

**关键成员函数**:
| 函数名 | 功能 | 特点 |
|--------|------|------|
| RootsReal | 求解所有实根 | 最多返回3个实根 |
| RootsValidT | 求解[0,1]范围内的实根 | 用于参数化曲线 |
| BinarySearchRootsValidT | 二分搜索求根 | 精度更高但速度较慢 |
| EvalAt | 计算函数值 | 使用 FMA 优化 |

## 公共 API 函数

### `static int RootsReal(double A, double B, double C, double D, double solution[3])`
- **功能**: 求解三次方程 A*t³ + B*t² + C*t + D = 0 的所有实数根
- **参数**:
  - A, B, C, D: 三次方程的系数
  - solution[3]: 输出数组，存储找到的实根
- **返回值**: 找到的实根数量（0-3个）
- **实现细节**:
  - 使用 Cardano 公式求解
  - 特殊处理 A 接近 0 的退化情况（降为二次方程）
  - 特殊处理 0 和 1 作为根的情况
  - 根据判别式 R²-Q³ 判断根的数量

### `static int RootsValidT(double A, double B, double C, double D, double solution[3])`
- **功能**: 求解三次方程在参数范围 [0, 1] 内的实根
- **参数**: 同 RootsReal
- **返回值**: 在 [0, 1] 范围内的根数量
- **实现细节**:
  - 先调用 RootsReal 获取所有实根
  - 过滤出 [0, 1] 范围内的根
  - 对边界附近的根进行容差处理（±0.00005）
  - 去重处理，避免重复的根

### `static int BinarySearchRootsValidT(double A, double B, double C, double D, double solution[3])`
- **功能**: 使用二分搜索方法求解 [0, 1] 范围内的根，精度更高
- **参数**: 同 RootsReal
- **返回值**: 找到的根数量
- **实现细节**:
  - 先找到三次函数的极值点（通过求导得到二次方程）
  - 将 [0, 1] 区间分段（根据极值点）
  - 在每个单调区间内使用二分搜索
  - 最多迭代 1000 次，精度为 1e-8

### `static double EvalAt(double A, double B, double C, double D, double t)`
- **功能**: 计算三次函数在给定 t 值处的函数值
- **参数**:
  - A, B, C, D: 函数系数
  - t: 自变量值
- **返回值**: 函数值 f(t)
- **实现细节**: 使用嵌套的 std::fma (fused multiply-add) 优化计算，减少浮点误差

## 内部实现细节

### 数值稳定性处理
1. **退化情况检测**: 当 A 系数接近 0 或相对于 B 很小（比值 < 1e-7）时，退化为二次方程求解
2. **特殊根优化**: 显式检查 0 和 1 是否为根，避免精度损失
3. **精度比较**: 使用 `nearly_equal` 函数进行浮点数比较，结合绝对误差和 ULP（Unit in the Last Place）误差

### Cardano 公式实现
```
变量替换: t = x - a/3
化简为: x³ + px + q = 0
判别式: Δ = R² - Q³
- 若 Δ < 0: 三个实根（使用三角函数求解）
- 若 Δ ≥ 0: 一个实根（或重根）
```

### 二分搜索算法流程
1. 求导得到 3A*t² + 2B*t + C = 0，找到极值点
2. 根据极值点将 [0, 1] 分为最多 3 个单调区间
3. 对每个区间：
   - 检查端点函数值符号是否相反
   - 若符号相反，则该区间内存在根
   - 使用二分法迭代求根
4. 去重并返回所有找到的根

### 浮点精度保护
- 使用 `sk_ieee_double_divide` 处理除零情况
- 使用 `SkIsFinite` 检查计算结果有效性
- 使用 `SkTPin` 将反余弦函数的参数钳制到有效范围 [-1, 1]
- 使用 `sk_doubles_nearly_equal_ulps` 进行 ULP 级别的相等性判断

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| SkQuads | 求解二次方程（退化情况） |
| SkFloatingPoint | 浮点数精度比较工具 |
| SkTPin | 数值范围钳制 |
| SkAssert | 断言检查 |
| std::fma | 融合乘加运算 |
| std::cbrt | 立方根计算 |
| std::acos | 反余弦函数 |

### 被依赖的模块
- 路径操作模块（PathOps）
- 贝塞尔曲线处理
- 曲线求交算法
- 图形渲染管线

## 设计模式与设计决策

### 纯静态工具类模式
所有方法都是静态方法，无需实例化对象，降低了使用复杂度和内存开销。这是典型的工具类（Utility Class）模式。

### 双策略模式
提供两种求根策略：
1. **RootsValidT**: 快速但精度一般，适合大多数场景
2. **BinarySearchRootsValidT**: 慢但精度高，用于对精度要求极高的场景

这种设计允许用户根据性能和精度需求进行权衡。

### 防御性编程
大量的边界情况处理和数值稳定性检查：
- NaN/Infinity 检测
- 退化情况特判
- 重根去重
- 边界容差处理

## 性能考量

### 优化技术
1. **FMA 指令**: EvalAt 使用融合乘加指令，减少中间舍入误差，提升性能
2. **早期返回**: 优先检测特殊情况（0 和 1 作为根），避免完整的 Cardano 求解
3. **退化检测**: 及时将三次方程降为二次方程，减少计算量

### 性能权衡
- **RootsValidT**: O(1) 时间复杂度，但可能因浮点误差损失精度
- **BinarySearchRootsValidT**: O(n*log(1/ε)) 时间复杂度（n 为区间数，ε 为精度），但数值稳定性更好

### 精度阈值选择
- `close_to_a_quadratic`: 比值阈值 1e-7
- `approximately_zero`: 绝对阈值 1e-8
- 边界容差: ±0.00005
这些阈值是根据 Skia 实际应用场景的数值范围和精度需求经验调整得出。

## 相关文件
| 文件 | 关系 |
|------|------|
| src/base/SkQuads.h | 二次方程求解器，处理退化情况 |
| include/private/base/SkFloatingPoint.h | 提供浮点数比较和精度工具 |
| include/private/base/SkTPin.h | 提供数值钳制功能 |
| src/pathops/*.cpp | 路径操作模块，主要使用方 |
| src/core/SkGeometry.cpp | 几何计算模块，使用三次曲线求解 |
