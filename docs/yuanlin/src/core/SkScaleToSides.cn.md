# SkScaleToSides

> 源文件: src/core/SkScaleToSides.h

## 概述

`SkScaleToSides` 是一个专门处理浮点数精度问题的工具类,用于在缩放两个半径值时确保它们的和不超过指定的限制。该类主要服务于圆角矩形(RRect)的绘制,当圆角半径过大时需要等比例缩小,同时必须精确处理浮点舍入误差以避免渲染瑕疵。它使用 `nextafterf` 函数逐步调整值,确保最终结果在浮点精度范围内满足约束。

## 架构位置

`SkScaleToSides` 位于 `src/core` 模块,作为底层数学工具类:

- **基础层**: 处理浮点数精度问题的底层工具
- **上层**: 被 `SkRRect`(圆角矩形)等几何类使用
- **相关系统**: 与浮点数运算、几何计算、渲染精度控制相关
- **使用场景**: 圆角矩形绘制、边界框计算、缩放操作

## 主要类与结构体

### SkScaleToSides

| 属性 | 说明 |
|------|------|
| **继承关系** | 无继承关系,静态工具类 |
| **核心方法** | `AdjustRadii`: 调整两个半径值使其和不超过限制 |

纯静态类,仅提供一个核心方法。

## 公共 API 函数

### AdjustRadii 方法

```cpp
// 调整 a 和 b 使得 a + b <= limit
// 参数:
//   limit: 两个半径和的上限(double 精度)
//   scale: 缩放因子,必须在 (0.0, 1.0) 范围内
//   a, b: 指向两个半径值的指针(将被修改)
static void AdjustRadii(double limit, double scale,
                        SkScalar* a, SkScalar* b);
```

## 内部实现细节

### 算法流程

1. **初始缩放**:
   ```cpp
   *a = (float)((double)*a * scale);
   *b = (float)((double)*b * scale);
   ```
   使用 double 精度进行计算,然后转换回 float。

2. **检查是否超限**:
   ```cpp
   if (*a + *b > limit) {
       // 需要进一步调整
   }
   ```

3. **确定较小值**:
   使用 `std::swap` 确保 `minRadius` 指向较小的值,`maxRadius` 指向较大的值。

4. **计算新的最大半径**:
   ```cpp
   float newMinRadius = *minRadius;  // 保持较小值不变
   float newMaxRadius = (float)(limit - newMinRadius);
   ```

5. **ULP 调整循环**:
   ```cpp
   while (newMaxRadius + newMinRadius > limit) {
       newMaxRadius = nextafterf(newMaxRadius, 0.0f);
   }
   ```
   使用 `nextafterf` 逐步减小 `newMaxRadius`,直到和不超过 `limit`。

6. **应用结果**:
   ```cpp
   *maxRadius = newMaxRadius;
   ```

### 浮点精度处理

**为什么需要 ULP 调整**:
- 浮点数加法不精确: `(float)(limit - minRadius) + minRadius` 可能略大于 `limit`
- 由于舍入误差,简单的减法不能保证和在限制内
- 必须逐步调整到下一个可表示的浮点数

**nextafterf 函数**:
- C 标准库函数,返回向指定方向的下一个可表示浮点数
- `nextafterf(x, 0.0f)` 返回比 x 小的下一个浮点数
- 每次调整一个 ULP(Unit in the Last Place)

**迭代次数**:
- 通常 0-2 次(注释中提到)
- 病态情况下可能更多(观察到的最大值为 17 次)
- 仍然是常数级开销

### 前置条件和断言

输入断言:
```cpp
SkASSERTF(scale < 1.0 && scale > 0.0, "scale: %g", scale);
```
- 缩放因子必须在 (0, 1) 之间(不包括端点)
- 这是因为 `limit / (a + b)` 小于 1 才需要缩放

输出断言:
```cpp
SkASSERTF(*a >= 0.0f && *b >= 0.0f, ...);
SkASSERTF(*a + *b <= limit, ...);
```
- 保证半径非负
- 保证和不超过限制(精确满足浮点约束)

### 特殊设计考虑

**保持较小值不变**:
- 较小的半径更接近限制的一半
- 调整较大值可减少舍入误差影响
- 注释说明: "newMinRadius 最大为 1/2 limit + ULP"

**双精度中间计算**:
- 输入缩放使用 double 减少累积误差
- 最终结果转换为 float(与 SkScalar 一致)

**病态情况处理**:
- 极端缩放比例(接近 0 或 1)
- 极小的限制值
- 半径值差异巨大

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| include/core/SkScalar.h | SkScalar 类型定义 |
| include/core/SkTypes.h | 断言宏和基础类型 |
| &lt;cmath&gt; | nextafterf 函数 |
| &lt;utility&gt; | std::swap |

### 被依赖的模块

| 模块 | 依赖方式 |
|------|----------|
| SkRRect | 圆角矩形半径调整 |
| SkPath | 路径构建时的圆角处理 |
| SkCanvas | 绘制圆角矩形 |

## 设计模式与设计决策

### 静态工具类模式

仅包含静态方法,无状态:
- 简化使用(无需实例化)
- 明确表示这是纯函数
- 避免不必要的对象创建

### 就地修改参数

通过指针参数直接修改输入:
- 避免返回复杂类型(如 pair)
- 调用者可选择性使用原变量
- 与 C 风格 API 一致(Skia 的历史风格)

### 防御性编程

多层断言确保正确性:
- 输入验证(缩放因子范围)
- 输出验证(半径非负、和不超限)
- 调试版本捕获违规,发布版本忽略

### ULP 级精度控制

使用 `nextafterf` 而非固定 epsilon:
- 适应不同数量级的值
- 精确控制浮点表示
- 避免过度或不足的调整

## 性能考量

### 快速路径优化

如果初始缩放后已满足条件,直接返回:
```cpp
if (*a + *b > limit) {
    // 仅在需要时执行 ULP 调整
}
```
大多数情况下无需进入调整循环。

### 常数时间复杂度

ULP 调整循环:
- 通常 0-2 次迭代(最常见)
- 最坏情况下迭代次数有界
- 总体仍为 O(1) 复杂度

### 内联优化

定义在头文件中,鼓励编译器内联:
- 消除函数调用开销
- 允许跨编译单元优化
- 在圆角矩形绘制热路径中关键

### 避免分支预测失败

代码结构简单,分支少:
- 主要逻辑为顺序执行
- 循环次数少,分支预测器友好

## 相关文件

| 文件 | 关系 |
|------|------|
| include/core/SkRRect.h | 圆角矩形使用该工具调整半径 |
| src/core/SkRRect.cpp | 具体调用 AdjustRadii |
| include/core/SkPath.h | 路径构建中的圆角处理 |
| src/core/SkDraw.cpp | 绘制圆角图形 |

## 使用场景示例

### 圆角矩形缩放

```cpp
// RRect 的四个角半径可能过大
float topLeft = 50.0f, topRight = 50.0f;
float width = 80.0f;  // 宽度不足以容纳两个半径

// 计算缩放因子
float scale = width / (topLeft + topRight);  // 0.8

// 调整半径
SkScaleToSides::AdjustRadii(width, scale, &topLeft, &topRight);

// 现在保证: topLeft + topRight <= width (精确满足浮点约束)
```

### 为什么不能直接乘以 scale

```cpp
// 错误做法:
float a = 50.0f * 0.8f;
float b = 50.0f * 0.8f;
// a + b 可能因浮点误差略大于 width

// 正确做法:
SkScaleToSides::AdjustRadii(width, 0.8, &a, &b);
// 保证 a + b <= width (在浮点表示精度内)
```
