# SkRRectPriv

> 源文件: src/core/SkRRectPriv.h

## 概述

`SkRRectPriv` 是一个提供 `SkRRect`（圆角矩形）私有功能和工具方法的静态辅助类。它封装了一系列用于检测、查询和操作圆角矩形的内部 API，这些 API 不适合暴露在公共头文件中，但对 Skia 内部实现非常有用。

该类主要提供圆角矩形的特殊属性检测（如是否为圆形、是否所有角都是圆角等）、序列化支持、点包含测试、内接矩形计算以及圆角矩形交集的保守估算等功能。所有方法都是静态的，类本身不包含任何状态。

## 架构位置

`SkRRectPriv` 位于 Skia 核心几何模块的辅助层，为 `SkRRect` 提供扩展功能：

- **公共接口**：`SkRRect`（`include/core/SkRRect.h`）提供标准的圆角矩形 API
- **私有扩展**：`SkRRectPriv`（`src/core/SkRRectPriv.h`）提供内部优化和特殊查询
- **使用场景**：渲染后端、路径操作、碰撞检测、GPU 优化等

作为私有辅助类，它不是公共 API 的一部分，仅供 Skia 内部模块使用。

## 主要类与结构体

### SkRRectPriv 类

**继承关系：**
- 无继承关系（纯静态工具类）

**特点：**
- 所有方法都是 `public static`
- 不包含成员变量
- 不可实例化（没有公共构造函数）

## 公共 API 函数

### 圆形检测

```cpp
static bool IsCircle(const SkRRect& rr);
```
判断圆角矩形是否为圆形。条件：必须是椭圆（`isOval()`）且宽度半径近似等于高度半径。

```cpp
static bool IsSimpleCircular(const SkRRect& rr);
```
判断是否为简单圆形（simple 类型且四个角的 X、Y 半径近似相等）。

```cpp
static bool IsNearlySimpleCircular(const SkRRect& rr, float tolerance = SK_ScalarNearlyZero);
```
宽松版本的 `IsSimpleCircular`，使用可配置的容差参数。

### 半径查询

```cpp
static SkVector GetSimpleRadii(const SkRRect& rr);
```
获取简单（非复杂）圆角矩形的半径。断言传入的 `SkRRect` 不是复杂类型（`!isComplex()`）。

```cpp
static const SkVector* GetRadiiArray(const SkRRect& rr);
```
获取内部半径数组的指针，直接访问 `SkRRect::fRadii` 成员。

### 等半径判断

```cpp
static bool EqualRadii(const SkRRect& rr);
```
判断所有角的半径是否相等。对于矩形、圆形或简单圆形返回 `true`。

### 圆角检测

```cpp
static bool AllCornersCircular(const SkRRect& rr, float tolerance = SK_ScalarNearlyZero);
```
检查所有四个角是否为圆角（X 半径 ≈ Y 半径，使用绝对差值比较）。

```cpp
static bool AllCornersRelativelyCircular(const SkRRect& rr, float tolerance = SK_ScalarNearlyZero);
static bool IsRelativelyCircular(float rx, float ry, float tolerance = SK_ScalarNearlyZero);
```
相对圆角检测，使用相对误差而非绝对差值。更稳定，推荐优先使用。

### 序列化

```cpp
static bool ReadFromBuffer(SkRBuffer* buffer, SkRRect* rr);
static void WriteToBuffer(const SkRRect& rr, SkWBuffer* buffer);
```
从缓冲区读取/写入圆角矩形数据，用于序列化和反序列化（如 `SkPicture` 记录）。

### 几何计算

```cpp
static bool ContainsPoint(const SkRRect& rr, const SkPoint& p);
```
测试点是否在圆角矩形内部（将其视为闭合集合）。结合边界矩形包含测试和角落包含测试（`checkCornerContainment`）。

```cpp
static SkRect InnerBounds(const SkRRect& rr);
```
计算圆角矩形的近似最大内接矩形。对于空、矩形、椭圆和简单类型返回最大内接矩形；对于复杂类型返回近似解（保证非空、至少接触一条边且包含在圆角矩形内）。

```cpp
static SkRRect ConservativeIntersect(const SkRRect& a, const SkRRect& b);
```
尝试计算两个圆角矩形的交集。只在交集可以表示为新的圆角矩形（或矩形）时返回有效结果，否则返回空。这是保守的算法，可能无法检测所有可表示的交集，但返回的结果一定是精确的（非子集近似）。

## 内部实现细节

### 圆形检测逻辑

`IsCircle()` 的判断条件：
1. `rr.isOval()`：必须是椭圆类型
2. `SkScalarNearlyEqual(rr.fRadii[0].fX, rr.fRadii[0].fY)`：宽度和高度半径近似相等

这比简单检查边界矩形宽高更精确，因为它直接检查内部半径值。

### 相对 vs. 绝对圆角检测

`AllCornersCircular()` 使用绝对差值：
```cpp
|rx - ry| < tolerance
```

`AllCornersRelativelyCircular()` 使用相对误差：
```cpp
|rx - ry| / max(rx, ry) < tolerance
```

相对误差在不同缩放级别下更稳定，文档建议优先使用。

### 内接矩形计算策略

`InnerBounds()` 对不同类型采用不同策略：
- **Empty/Rect**：返回原始边界
- **Oval**：返回内接矩形（宽度和高度缩小 `radius * √2`）
- **Simple**：考虑单一半径的影响
- **Complex**：启发式算法，可能不是全局最优但保证有效性

### 保守交集的局限性

`ConservativeIntersect()` 的注释明确说明：
- 交集不一定是圆角矩形
- 只返回可以表示为圆角矩形的交集
- 保守策略：宁可返回空也不返回不精确的近似
- 未来可能改进检测算法

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `SkRRect` | 圆角矩形公共接口 |
| `SkRBuffer` / `SkWBuffer` | 序列化缓冲区 |
| `SkScalar` | 标量类型和数学函数 |
| `SkPoint` | 点坐标 |
| `SkRect` | 矩形 |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| `SkPath` | 路径操作可能使用圆角矩形检测 |
| GPU 后端 | 使用圆形检测优化渲染 |
| `SkCanvas` | 绘制优化（如检测简单情况） |
| `SkPicture` | 序列化圆角矩形数据 |
| 碰撞检测系统 | 使用 `ContainsPoint` 和交集计算 |

## 设计模式与设计决策

### 静态工具类模式

`SkRRectPriv` 采用纯静态方法的设计：
- **无状态**：不维护任何成员变量
- **命名空间替代**：类名作为逻辑命名空间
- **私有扩展**：将内部 API 与公共 API 分离

### 私有实现模式

通过单独的 `*Priv.h` 头文件隔离内部 API：
- 公共 API（`SkRRect.h`）保持稳定和简洁
- 私有 API（`SkRRectPriv.h`）可以自由演化
- 避免暴露内部实现细节（如 `fRadii` 数组访问）

### 容差参数化

多个函数接受 `tolerance` 参数（默认 `SK_ScalarNearlyZero`）：
- **灵活性**：调用者可以根据场景调整精度
- **默认合理**：默认值适用于大多数情况
- **精度权衡**：允许在性能和精度之间平衡

### 保守策略

`ConservativeIntersect()` 采用保守算法：
- **正确性优先**：宁可失败也不返回错误结果
- **渐进增强**：未来可以改进检测能力而不破坏语义
- **文档透明**：注释明确说明局限性

## 性能考量

### 内联候选

所有方法都是静态的短函数，编译器很可能内联它们，消除函数调用开销。

### 直接成员访问

`GetRadiiArray()` 直接返回内部数组指针，避免复制：
```cpp
return rr.fRadii;
```

这在需要遍历所有角的场景中非常高效。

### 早期退出优化

`EqualRadii()` 使用短路逻辑：
```cpp
return rr.isRect() || IsCircle(rr) || IsSimpleCircular(rr);
```

按从简单到复杂的顺序检查，尽早返回。

### 相对圆角检测的稳定性

相对误差检测在不同缩放级别下更稳定，避免了绝对误差在大尺寸或小尺寸时的问题。文档特别推荐这种方法。

### 内接矩形的近似

对于复杂类型的 `InnerBounds()`，使用启发式算法而非精确计算：
- **避免昂贵的数学运算**：精确解需要优化算法
- **实用性**：近似解在实际应用中足够好
- **保证性质**：结果保证非空且被包含

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/core/SkRRect.h` | 圆角矩形公共接口 |
| `include/core/SkRect.h` | 矩形定义 |
| `include/core/SkPoint.h` | 点坐标 |
| `include/core/SkScalar.h` | 标量类型和数学函数 |
| `src/core/SkRBuffer.h` | 读取缓冲区 |
| `src/core/SkWBuffer.h` | 写入缓冲区 |
| `include/private/base/SkAssert.h` | 断言宏 |
