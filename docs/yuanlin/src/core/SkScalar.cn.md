# SkScalar

> 源文件: include/core/SkScalar.h, src/core/SkScalar.cpp

## 概述

`SkScalar` 是 Skia 图形库的核心浮点数类型定义,目前定义为 `float` 类型。该模块提供了一整套数学运算宏和内联函数,包括三角函数、取整、插值等常用操作。这是一个历史遗留的抽象层,最初用于在不同平台间切换定点数和浮点数实现,现在统一使用 32 位浮点数,但保留了 API 以维护兼容性。

## 架构位置

`SkScalar` 位于 Skia 的 `include/core` 公共接口层:

- **基础层**: 最底层的数学类型定义,被所有模块使用
- **上层**: `SkPoint`、`SkRect`、`SkMatrix` 等几何类型基于 `SkScalar` 构建
- **全局影响**: 整个 Skia API 表面使用 `SkScalar` 作为浮点数参数类型
- **平台适配**: 通过宏封装标准 C++ 数学函数,提供统一接口

## 主要类与结构体

### SkScalar 类型别名

| 属性 | 说明 |
|------|------|
| **类型定义** | `typedef float SkScalar;` |
| **常量** | `SK_Scalar1`: 1.0f<br>`SK_ScalarHalf`: 0.5f<br>`SK_ScalarPI`: π<br>`SK_ScalarMax/Min`: 浮点数范围<br>`SK_ScalarInfinity/NaN`: 特殊值<br>`SK_ScalarNearlyZero`: 近似零阈值(1/4096) |

核心类型定义和常用常量。

## 公共 API 函数

### 类型转换宏

```cpp
#define SkIntToScalar(x)        static_cast<SkScalar>(x)
#define SkIntToFloat(x)         static_cast<float>(x)
#define SkScalarToFloat(x)      static_cast<float>(x)
#define SkFloatToScalar(x)      static_cast<SkScalar>(x)
#define SkScalarToDouble(x)     static_cast<double>(x)
#define SkDoubleToScalar(x)     sk_double_to_float(x)
```

### 取整函数宏

```cpp
// 向下取整
#define SkScalarFloorToScalar(x)    std::floor(x)
#define SkScalarFloorToInt(x)       sk_float_floor2int(x)

// 向上取整
#define SkScalarCeilToScalar(x)     std::ceil(x)
#define SkScalarCeilToInt(x)        sk_float_ceil2int(x)

// 四舍五入
#define SkScalarRoundToScalar(x)    sk_float_round(x)
#define SkScalarRoundToInt(x)       sk_float_round2int(x)

// 截断
#define SkScalarTruncToScalar(x)    std::trunc(x)
#define SkScalarTruncToInt(x)       sk_float_saturate2int(x)
```

### 数学运算宏

```cpp
// 基本运算
#define SkScalarAbs(x)              std::fabs(x)
#define SkScalarSqrt(x)             std::sqrt(x)
#define SkScalarPow(b, e)           std::pow(b, e)
#define SkScalarMod(x, y)           std::fmod(x,y)
#define SkScalarCopySign(x, y)      std::copysign(x, y)

// 三角函数
#define SkScalarSin(radians)        ((float)std::sin(radians))
#define SkScalarCos(radians)        ((float)std::cos(radians))
#define SkScalarTan(radians)        ((float)std::tan(radians))
#define SkScalarASin(val)           ((float)std::asin(val))
#define SkScalarACos(val)           ((float)std::acos(val))
#define SkScalarATan2(y, x)         ((float)std::atan2(y,x))

// 指数和对数
#define SkScalarExp(x)              ((float)std::exp(x))
#define SkScalarLog(x)              ((float)std::log(x))
#define SkScalarLog2(x)             ((float)std::log2(x))
```

### 内联辅助函数

```cpp
// 获取小数部分
static inline SkScalar SkScalarFraction(SkScalar x);

// 平方运算
static inline SkScalar SkScalarSquare(SkScalar x);

// 倒数
#define SkScalarInvert(x)           (SK_Scalar1 / (x))

// 取半
#define SkScalarHalf(a)             ((a) * SK_ScalarHalf)

// 平均值
#define SkScalarAve(a, b)           sk_float_midpoint(a, b)

// 角度转换
#define SkDegreesToRadians(degrees) ((degrees) * (SK_ScalarPI / 180))
#define SkRadiansToDegrees(radians) ((radians) * (180 / SK_ScalarPI))

// 判断是否为整数
static inline bool SkScalarIsInt(SkScalar x);

// 符号函数
static inline int SkScalarSignAsInt(SkScalar x);
static inline SkScalar SkScalarSignAsScalar(SkScalar x);

// 近似相等判断
static inline bool SkScalarNearlyZero(SkScalar x,
                                      SkScalar tolerance = SK_ScalarNearlyZero);
static inline bool SkScalarNearlyEqual(SkScalar x, SkScalar y,
                                       SkScalar tolerance = SK_ScalarNearlyZero);

// 三角函数零值捕捉
static inline float SkScalarSinSnapToZero(SkScalar radians);
static inline float SkScalarCosSnapToZero(SkScalar radians);

// 线性插值
static inline SkScalar SkScalarInterp(SkScalar A, SkScalar B, SkScalar t);

// 数组比较
static inline bool SkScalarsEqual(const SkScalar a[], const SkScalar b[], int n);
```

### 实现函数

```cpp
// 分段线性插值(在 SkScalar.cpp 中实现)
float SkFloatInterpFunc(float searchKey,
                        const float keys[],
                        const float values[],
                        int length);
```

## 内部实现细节

### SkFloatInterpFunc 实现

分段线性插值函数用于在键值对数组中查找和插值:

1. **输入验证**: 断言 keys 数组是升序排列
2. **二分查找**: 线性扫描找到 searchKey 所在区间
3. **边界处理**:
   - 如果超出右边界,返回最后一个值
   - 如果低于左边界,返回第一个值
4. **插值计算**: 使用 `SkScalarInterp` 在两个端点间插值

用途示例: 计算假粗体的描边宽度(根据字体大小插值)

### 近似零判定

`SkScalarNearlyZero` 使用阈值比较:
- 默认阈值 `SK_ScalarNearlyZero` = 1/4096 ≈ 0.000244
- 用于避免浮点误差导致的判断错误
- 在矩阵可逆性判断、边界检测等场景广泛使用

### 三角函数零值捕捉

`SkScalarSinSnapToZero` 和 `SkScalarCosSnapToZero`:
- 对于非常接近零的结果(< `SK_ScalarSinCosNearlyZero` = 1/65536),强制返回 0.0f
- 避免浮点误差导致的渲染瑕疵
- 特别用于整数度数(如 90°, 180°)的情况

### 线性插值实现

`SkScalarInterp(A, B, t)` 计算 `A + (B - A) * t`:
- 要求 `t ∈ [0, 1]`
- 避免直接使用 `A * (1 - t) + B * t` 以减少舍入误差
- 广泛用于动画、渐变、贝塞尔曲线等

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| include/private/base/SkAssert.h | 断言宏 |
| include/private/base/SkFloatingPoint.h | 浮点数辅助函数(floor2int, round2int 等) |
| include/private/base/SkDebug.h | 调试支持 |
| &lt;cmath&gt; | 标准数学函数 |

### 被依赖的模块

| 模块 | 依赖方式 |
|------|----------|
| 所有几何类型 | SkPoint, SkRect, SkMatrix, SkPath 等 |
| 所有渲染代码 | 颜色计算、变换、光栅化等 |
| 公共 API | SkCanvas, SkPaint, SkShader 等 |
| 布局系统 | 文本排版、度量计算 |

## 设计模式与设计决策

### 宏而非内联函数

大量使用宏定义而非内联函数:
- **历史原因**: 早期 C++ 编译器内联支持有限
- **兼容性**: 保持与旧代码的 ABI 兼容
- **类型灵活性**: 宏可用于 constexpr 上下文
- **零开销**: 保证没有函数调用

### 统一类型抽象

使用 `SkScalar` 而非直接使用 `float`:
- 提供未来切换到 double 的可能性(虽然不太可能)
- 统一 API 风格,提高可读性
- 历史上曾支持定点数(16.16 格式),现已废弃

### 常量前缀约定

所有常量使用 `SK_Scalar` 前缀:
- 避免命名冲突(如 `PI` 在某些系统中已定义)
- 明确来源和用途
- 与 Skia 的整体命名规范一致

### 近似比较策略

提供多个阈值常量:
- `SK_ScalarNearlyZero`: 通用近似零判断
- `SK_ScalarSinCosNearlyZero`: 三角函数特化阈值
- 允许根据上下文调整容差

## 性能考量

### 宏展开优化

所有数学运算宏直接展开为 C++ 标准库调用:
- 编译器可内联和优化
- 避免 Skia 层额外的函数调用开销
- 利用编译器的数学优化(如快速数学模式)

### 浮点数选择

使用 32 位 `float` 而非 `double`:
- GPU 原生支持单精度浮点
- 减少内存占用和缓存压力
- 对于图形渲染精度已足够
- SIMD 指令集可并行处理更多 float

### 避免分支

`SkScalarSignAsInt` 使用算术运算而非 if-else:
```cpp
return x < 0 ? -1 : (x > 0);
```
现代编译器可将其优化为无分支代码。

### 内联函数强制

小型辅助函数声明为 `static inline`:
- 保证编译器内联
- 避免链接器符号开销
- 跨编译单元优化

## 相关文件

| 文件 | 关系 |
|------|------|
| include/core/SkPoint.h | 使用 SkScalar 表示坐标 |
| include/core/SkRect.h | 使用 SkScalar 表示边界 |
| include/core/SkMatrix.h | 使用 SkScalar 表示变换矩阵 |
| include/core/SkPath.h | 使用 SkScalar 表示路径点 |
| include/private/base/SkFloatingPoint.h | 提供底层浮点工具函数 |
| include/private/base/SkFixed.h | 定点数类型(已废弃) |
| src/core/SkTextFormatParams.h | 使用 SkFloatInterpFunc |
