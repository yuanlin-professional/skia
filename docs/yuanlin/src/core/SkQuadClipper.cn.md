# SkQuadClipper

> 源文件
> - src/core/SkQuadClipper.h
> - src/core/SkQuadClipper.cpp

## 概述

`SkQuadClipper` 是 Skia 中用于裁剪二次贝塞尔曲线（quad）的工具类。该类负责将二次贝塞尔曲线与矩形裁剪区域相交，返回裁剪后在裁剪区域内的部分。主要用于路径渲染中的曲线裁剪操作，确保曲线段在指定的 Y 轴范围内单调递增。

该模块提供两个主要类：
- `SkQuadClipper`: 基础裁剪器，处理单个二次贝塞尔曲线的裁剪
- `SkQuadClipper2`: 高级迭代器，将裁剪后的曲线分解为线段或二次曲线段

## 架构位置

`SkQuadClipper` 位于 Skia 核心图形模块（`src/core`）中，是几何处理系统的一部分。它与路径渲染、几何变换和裁剪系统紧密配合。

在 Skia 渲染管线中的位置：
```
路径构建 → 几何处理 → SkQuadClipper（曲线裁剪） → 光栅化 → 像素输出
```

## 主要类与结构体

### SkQuadClipper

基础的二次贝塞尔曲线裁剪器。

**继承关系**
- 无继承关系（独立类）

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fClip` | `SkRect` | 裁剪矩形区域 |

### SkQuadClipper2

迭代器风格的裁剪器，支持曲线和立方曲线的裁剪。

**继承关系**
- 无继承关系（独立类）

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fCurrPoint` | `SkPoint*` | 当前点指针 |
| `fCurrVerb` | `SkPath::Verb*` | 当前动词指针 |
| `fPoints` | `SkPoint[32]` | 点缓冲区 |
| `fVerbs` | `SkPath::Verb[13]` | 动词缓冲区 |
| `kMaxVerbs` | `enum` | 最大动词数量（13） |
| `kMaxPoints` | `enum` | 最大点数量（32） |

## 公共 API 函数

### SkQuadClipper

**构造与配置**
```cpp
SkQuadClipper();  // 构造函数，初始化空裁剪区域
void setClip(const SkIRect& clip);  // 设置裁剪矩形
```

**裁剪操作**
```cpp
bool clipQuad(const SkPoint src[3], SkPoint dst[3]);
```
- 裁剪二次贝塞尔曲线到裁剪区域
- `src`: 输入的 3 个控制点（必须在 Y 轴上单调）
- `dst`: 输出裁剪后的 3 个控制点
- 返回：裁剪成功返回 `true`，完全在裁剪区域外返回 `false`

### SkQuadClipper2

**裁剪入口**
```cpp
bool clipQuad(const SkPoint pts[3], const SkRect& clip);
bool clipCubic(const SkPoint pts[4], const SkRect& clip);
```
- 裁剪二次曲线或三次曲线
- 返回值指示是否有可见部分

**迭代访问**
```cpp
SkPath::Verb next(SkPoint pts[]);
```
- 获取下一个裁剪后的线段或曲线段
- 返回 `kMove_Verb`, `kLine_Verb`, `kQuad_Verb` 或 `kDone_Verb`

## 内部实现细节

### 裁剪算法

**单调性保证**
- 输入的二次贝塞尔曲线必须在 Y 轴上单调递增或递减
- 如果 `src[0].fY > src[2].fY`，算法会自动翻转点顺序

**裁剪步骤**
1. **边界检查**：快速排除完全在裁剪区域上方或下方的曲线
2. **顶部裁剪**：如果曲线起点在裁剪区域上方，使用 `chopMonoQuadAtY` 在顶部边界处分割曲线
3. **底部裁剪**：如果曲线终点在裁剪区域下方，在底部边界处分割曲线
4. **数值稳定性**：如果分割失败（数值精度问题），直接将点夹紧到边界

**chopMonoQuadAt 函数**
```cpp
static bool chopMonoQuadAt(SkScalar c0, SkScalar c1, SkScalar c2,
                           SkScalar target, SkScalar* t);
```
- 求解二次贝塞尔方程 `F(t) = c0(1-t)^2 + 2c1*t(1-t) + c2*t^2 = target`
- 使用一元二次方程求根：`At^2 + Bt + C = 0`
  - `A = c0 - 2c1 + c2`
  - `B = 2(c1 - c0)`
  - `C = c0 - target`

### SkQuadClipper2 实现

该类将裁剪操作分解为多个子步骤：
1. 调用 `clipQuad` 或 `clipCubic` 初始化裁剪
2. 内部调用 `clipMonoQuad` 或 `clipMonoCubic` 处理单调曲线
3. 使用 `appendVLine`, `appendQuad`, `appendCubic` 添加裁剪结果
4. 通过 `next()` 迭代返回裁剪后的线段和曲线段

### 调试支持

提供断言宏用于调试单调性：
```cpp
#ifdef SK_DEBUG
void sk_assert_monotonic_x(const SkPoint pts[], int count);
void sk_assert_monotonic_y(const SkPoint pts[], int count);
#endif
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkPath` | 路径动词类型定义 |
| `SkPoint` | 二维点表示 |
| `SkRect` / `SkIRect` | 矩形表示 |
| `SkGeometry` | 几何计算函数（曲线分割） |
| `SkScalar` | 标量类型定义 |

### 被依赖的模块

`SkQuadClipper` 被以下模块使用：
- **路径渲染器**：在绘制路径时裁剪曲线
- **边缘抗锯齿（Edge AA）**：处理边缘曲线的可见部分
- **扫描转换器**：将曲线转换为扫描线前的预处理

## 设计模式与设计决策

### 设计模式

1. **迭代器模式**（`SkQuadClipper2`）
   - 提供顺序访问裁剪结果的接口
   - 避免一次性分配大量内存

2. **状态封装**
   - 裁剪区域作为成员变量保存，支持多次裁剪操作

### 设计决策

**为何要求单调性**
- 单调曲线简化裁剪逻辑，只需在两个边界处最多分割一次
- 非单调曲线需要先分割为单调段

**为何支持原地翻转**
- 避免额外内存分配
- 通过翻转输入点顺序统一处理递增和递减情况

**为何提供两个类**
- `SkQuadClipper`：简单场景，单次裁剪
- `SkQuadClipper2`：复杂场景，需要迭代多个裁剪段

**数值健壮性考虑**
- 当求根失败时使用夹紧策略，避免完全失败
- 通过 `SkFindUnitQuadRoots` 处理边界情况

## 性能考量

### 优化策略

1. **快速路径判断**
   - 先检查曲线是否完全在裁剪区域外，避免不必要的计算

2. **最小化内存分配**
   - `SkQuadClipper2` 使用固定大小的数组缓冲区
   - 最大支持 13 个动词和 32 个点

3. **原地操作**
   - 支持 `dst == src`，减少数据拷贝

4. **数学优化**
   - 使用一元二次方程求根，比迭代法更快

### 性能瓶颈

- **曲线分割**：`SkChopQuadAt` 需要多次浮点运算
- **根查找**：二次方程求根可能涉及平方根计算

### 使用建议

- 对于已知在裁剪区域内的曲线，跳过裁剪
- 批量处理时重用 `SkQuadClipper` 实例
- 优先使用 `SkQuadClipper` 处理简单情况

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/core/SkGeometry.h` / `.cpp` | 依赖 | 提供 `SkChopQuadAt` 和 `SkFindUnitQuadRoots` |
| `include/core/SkPath.h` | 依赖 | 定义 `SkPath::Verb` 枚举 |
| `include/core/SkPoint.h` | 依赖 | 定义 `SkPoint` 结构体 |
| `include/core/SkRect.h` | 依赖 | 定义 `SkRect` 和 `SkIRect` |
| `src/core/SkEdgeClipper.h` | 相关 | 更高级的边缘裁剪器 |
| `src/core/SkScan.cpp` | 使用者 | 扫描转换中使用曲线裁剪 |
| `src/core/SkAAClip.cpp` | 使用者 | 抗锯齿裁剪中使用 |
