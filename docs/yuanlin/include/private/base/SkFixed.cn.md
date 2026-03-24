# SkFixed 定点数运算模块

> 源文件: `include/private/base/SkFixed.h`

## 概述
SkFixed 提供 Skia 的定点数 (Fixed-Point) 运算支持,定义了 16.16 格式的定点数类型及其运算函数。定点数在需要精确小数表示且避免浮点运算开销的场景中非常有用,特别是在早期移动设备和嵌入式系统中。

## 架构位置
位于 Skia 基础数学层 (private/base),为路径光栅化、文本渲染、几何变换等模块提供定点数运算支持。虽然现代 Skia 主要使用浮点数,但定点数在某些遗留接口和优化路径中仍在使用。

## 定点数格式

### SkFixed - 16.16 定点数
```cpp
typedef int32_t SkFixed;
```
- **格式**: 32 位有符号整数,高 16 位为整数部分,低 16 位为小数部分
- **范围**: -32768.0 ~ 32767.99998...
- **精度**: 1/65536 ≈ 0.000015
- **示例**:
  - `SK_Fixed1` (65536) 表示 1.0
  - `SK_FixedHalf` (32768) 表示 0.5
  - `0x00010000` 表示 1.0
  - `0x00018000` 表示 1.5

### SkFixed3232 - 32.32 定点数
```cpp
typedef int64_t SkFixed3232;
```
- **格式**: 64 位有符号整数,高 32 位为整数部分,低 32 位为小数部分
- **范围**: 更大的整数范围和更高精度
- **用途**: 需要更高精度的中间计算

## 常量定义

### 16.16 定点常量
| 常量名 | 值 (十六进制) | 十进制值 | 含义 |
|--------|--------------|----------|------|
| `SK_Fixed1` | 0x10000 | 65536 | 1.0 |
| `SK_FixedHalf` | 0x8000 | 32768 | 0.5 |
| `SK_FixedQuarter` | 0x4000 | 16384 | 0.25 |
| `SK_FixedMax` | 0x7FFFFFFF | 2147483647 | 最大值 (~32767.99998) |
| `SK_FixedMin` | -0x7FFFFFFF | -2147483647 | 最小值 (~-32767.99998) |
| `SK_FixedPI` | 0x3243F | 205887 | π ≈ 3.14159 |
| `SK_FixedSqrt2` | 92682 | 92682 | √2 ≈ 1.41421 |
| `SK_FixedTanPIOver8` | 0x6A0A | 27146 | tan(π/8) ≈ 0.41421 |
| `SK_FixedRoot2Over2` | 0xB505 | 46341 | √2/2 ≈ 0.70711 |

### 32.32 定点常量
```cpp
#define SkFixed3232Max            SK_MaxS64
#define SkFixed3232Min            (-SkFixed3232Max)
```

## 类型转换函数

### SkFixed ↔ Float

#### 定点数转浮点数
```cpp
#define SkFixedToFloat(x)   ((x) * 1.52587890625e-5f)
```
- **公式**: `x / 65536.0`
- **精度**: 精确转换
- **示例**: `SkFixedToFloat(SK_Fixed1)` → `1.0f`

#### 浮点数转定点数
```cpp
#define SkFloatToFixed(x)   sk_float_saturate2int((x) * SK_Fixed1)
```
- **公式**: `x * 65536`,然后饱和到 int32 范围
- **精度**: 可能损失精度 (float 23 位尾数 vs 定点数 16 位小数)
- **安全性**: 使用饱和运算防止溢出
- **注意**: 注释中提到此实现缺少舍入步骤

#### Debug 检查版本
```cpp
#ifdef SK_DEBUG
    static inline SkFixed SkFloatToFixed_Check(float x);
#else
    #define SkFloatToFixed_Check(x) SkFloatToFixed(x)
#endif
```
- **功能**: Debug 模式下检查转换是否溢出
- **实现**: 先转为 int64_t,再检查是否能放入 int32_t

### SkFixed ↔ Double

#### 定点数转双精度
```cpp
#define SkFixedToDouble(x)  ((x) * 1.52587890625e-5)
```
精度更高的转换版本。

#### 双精度转定点数
```cpp
#define SkDoubleToFixed(x)  ((SkFixed)((x) * SK_Fixed1))
```
无饱和保护,假设值在有效范围内。

### SkFixed ↔ Int

#### 整数转定点数
```cpp
#ifdef SK_DEBUG
    inline SkFixed SkIntToFixed(int n) {
        SkASSERT(n >= -32768 && n <= 32767);
        return (SkFixed)((unsigned)n << 16);
    }
#else
    #define SkIntToFixed(n)  (SkFixed)((unsigned)(n) << 16)
#endif
```
- **范围**: 仅 -32768 ~ 32767 安全
- **实现**: 先转为无符号数,避免左移负数的未定义行为
- **Debug**: 断言检查范围

#### 定点数转整数 (舍入方式)

##### 四舍五入
```cpp
#define SkFixedRoundToInt(x)    (((x) + SK_FixedHalf) >> 16)
```
加 0.5 后右移,实现四舍五入。

##### 向上取整
```cpp
#define SkFixedCeilToInt(x)     (((x) + SK_Fixed1 - 1) >> 16)
```
加 0.999... 后右移。

##### 向下取整
```cpp
#define SkFixedFloorToInt(x)    ((x) >> 16)
```
直接丢弃小数部分。

### SkFixed ↔ SkFixed (对齐操作)

#### 舍入到整数定点数
```cpp
static inline SkFixed SkFixedRoundToFixed(SkFixed x) {
    return (SkFixed)((uint32_t)(x + SK_FixedHalf) & 0xFFFF0000);
}
```
清除小数部分,保留整数部分。

#### 向上/向下对齐
```cpp
static inline SkFixed SkFixedCeilToFixed(SkFixed x);
static inline SkFixed SkFixedFloorToFixed(SkFixed x);
```
类似的对齐操作。

## 定点数运算

### 平均值
```cpp
#define SkFixedAve(a, b)    (((a) + (b)) >> 1)
```
计算两个定点数的平均值。

### 乘法
```cpp
static inline SkFixed SkFixedMul(SkFixed a, SkFixed b) {
    return (SkFixed)((int64_t)a * b >> 16);
}
```
- **实现**: 先转为 64 位防止溢出,乘积右移 16 位
- **原理**: (a/2^16) * (b/2^16) = (a*b)/2^32,需右移 16 位得到结果

### 除法
```cpp
#define SkFixedDiv(numer, denom) \
    SkToS32(SkTPin<int64_t>((SkLeftShift((int64_t)(numer), 16) / (denom)), \
                             SK_MinS32, SK_MaxS32))
```
- **实现**: 分子左移 16 位后除以分母
- **原理**: (a/2^16) / (b/2^16) = a/b,但需先左移保持精度
- **安全性**: 使用 64 位中间值,结果限制在 int32 范围
- **示例**: `SkFixedDiv(SK_Fixed1, 2)` → `SK_FixedHalf` (1.0 / 2 = 0.5)

## SkFixed3232 转换

### 与 SkFixed 的转换
```cpp
#define SkFixedToFixed3232(x)     (SkLeftShift((SkFixed3232)(x), 16))
#define SkFixed3232ToFixed(x)     ((SkFixed)((x) >> 16))
```
仅需移位,无精度损失或增加。

### 与整数的转换
```cpp
#define SkIntToFixed3232(x)       (SkLeftShift((SkFixed3232)(x), 32))
#define SkFixed3232ToInt(x)       ((int)((x) >> 32))
```

### 与浮点数的转换
```cpp
#define SkFloatToFixed3232(x)     sk_float_saturate2int64((x) * (65536.0f * 65536.0f))
#define SkFixed3232ToFloat(x)     (x * (1 / (65536.0f * 65536.0f)))
```

### 与 Scalar 的转换
```cpp
#define SkScalarToFixed3232(x)    SkFloatToFixed3232(x)
```
Scalar 通常定义为 float。

## 平台优化

### ARM VFPv3 优化
```cpp
#if defined(__ARM_VFPV3__)
    #include <cstring>
    SK_ALWAYS_INLINE SkFixed SkFloatToFixed_arm(float x) {
        int32_t y;
        asm("vcvt.s32.f32 %0, %0, #16": "+w"(x));
        std::memcpy(&y, &x, sizeof(y));
        return y;
    }
    #undef SkFloatToFixed
    #define SkFloatToFixed(x)  SkFloatToFixed_arm(x)
#endif
```
- **优化**: 使用 ARM NEON 指令 `vcvt` 直接转换
- **性能**: 比乘法后转整数快得多
- **要求**: ARM VFPv3 或更高版本
- **注意**: 不处理 NaN 等特殊值

## Scalar 互操作

```cpp
#define SkFixedToScalar(x)          SkFixedToFloat(x)
#define SkScalarToFixed(x)          SkFloatToFixed(x)
```
在现代 Skia 中,Scalar 即 float,所以直接映射。

## 内部实现细节

### 转换的精度问题
注释中明确指出:
```
SkFixedToFloat is exact.
SkFloatToFixed seems to lack a rounding step.
```
- `SkFixedToFloat`: 精确,因为 float 可以表示所有 16.16 定点数
- `SkFloatToFixed`: 缺少舍入,直接截断可能损失精度

### 为何不舍入?
```
For all fixed-point values, this version is as accurate as possible for
(fixed -> float -> fixed). Rounding reduces accuracy if the intermediate
floats are in the range that only holds integers (adding 0.5f to an odd
integer then snaps to nearest even).
```
当浮点数在只能表示整数的范围内时,舍入会导致精度下降。

### 安全的左移实现
```cpp
return (SkFixed)((unsigned)n << 16);
```
左移前先转为无符号类型,避免对负数左移的未定义行为。

### 64 位中间值
乘法和除法使用 int64_t 中间类型防止溢出:
```cpp
(int64_t)a * b >> 16
```

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| `SkAssert.h` | 提供 SkASSERT 断言 |
| `SkDebug.h` | Debug 模式支持 |
| `SkMath.h` | 基础数学常量和函数 |
| `SkTPin.h` | 提供 SkTPin 范围限制 |
| `<cstdint>` | 固定宽度整数类型 |
| `<cstring>` | ARM 优化中的 memcpy |

### 被依赖的模块
- 文本渲染 (字形位置)
- 路径光栅化 (亚像素精度)
- 旧版矩阵运算
- 某些图像处理算法

## 设计模式与设计决策

### 16.16 格式的选择
- **平衡**: 整数范围 ±32K 和精度 1/65536
- **历史**: 在浮点运算昂贵时代广泛使用
- **适用**: 屏幕坐标、文本排版等场景

### 宏而非内联函数
大多数转换使用宏实现:
- 编译期常量折叠
- 避免函数调用开销
- 某些场景允许编译器更好优化

### 平台特定优化
通过条件编译选择最优实现:
- ARM: 使用 NEON 指令
- 其他: 标准 C 实现

### 饱和转换
浮点转定点使用饱和运算,防止溢出导致的错误结果。

## 性能考量

### 定点数 vs 浮点数
**定点数优势** (历史):
- 整数运算,无浮点单元也能快速计算
- 精确表示小数,无舍入误差累积
- 比较和排序是整数操作

**浮点数优势** (现代):
- 硬件浮点单元已普及
- 动态范围更大
- 标准数学库支持丰富

### 现代 Skia 的使用
定点数主要在遗留接口和特定优化路径中使用,新代码倾向于浮点数。

### ARM NEON 优化
在支持的平台上,NEON 指令将浮点转定点加速数倍。

## 使用示例

### 基本转换
```cpp
// 整数转定点数
SkFixed one = SkIntToFixed(1);      // 65536
SkFixed ten = SkIntToFixed(10);     // 655360

// 浮点数转定点数
SkFixed half = SkFloatToFixed(0.5f);  // 32768
SkFixed pi = SkFloatToFixed(3.14f);   // 205209

// 定点数转浮点数
float f1 = SkFixedToFloat(SK_Fixed1);     // 1.0f
float f2 = SkFixedToFloat(SK_FixedHalf);  // 0.5f
```

### 定点数运算
```cpp
SkFixed a = SkIntToFixed(3);
SkFixed b = SkIntToFixed(4);

// 乘法: 3 * 4 = 12
SkFixed product = SkFixedMul(a, b);
int result = SkFixedRoundToInt(product);  // 12

// 除法: 3 / 4 = 0.75
SkFixed quotient = SkFixedDiv(a, b);
float f = SkFixedToFloat(quotient);  // 0.75f

// 平均值: (3 + 4) / 2 = 3.5
SkFixed avg = SkFixedAve(a, b);
float favg = SkFixedToFloat(avg);  // 3.5f
```

### 亚像素定位
```cpp
// 文本排版中的亚像素位置
SkFixed xPos = SkFloatToFixed(10.25f);  // x = 10.25 像素
SkFixed yPos = SkFloatToFixed(20.75f);  // y = 20.75 像素

// 提取整数和小数部分
int xPixel = SkFixedFloorToInt(xPos);   // 10
int yPixel = SkFixedFloorToInt(yPos);   // 20

SkFixed xFrac = xPos & 0xFFFF;  // 0.25 的定点表示
SkFixed yFrac = yPos & 0xFFFF;  // 0.75 的定点表示
```

### 定点数舍入
```cpp
SkFixed value = SkFloatToFixed(2.7f);

int floor = SkFixedFloorToInt(value);   // 2
int ceil = SkFixedCeilToInt(value);     // 3
int round = SkFixedRoundToInt(value);   // 3
```

### 高精度中间计算
```cpp
// 使用 SkFixed3232 避免精度损失
SkFixed a = SkIntToFixed(1000);
SkFixed b = SkIntToFixed(2000);

// 直接用 SkFixed 乘法可能溢出
// SkFixed product = SkFixedMul(a, b);  // 可能不准确

// 使用 32.32 格式
SkFixed3232 a32 = SkFixedToFixed3232(a);
SkFixed3232 b32 = SkFixedToFixed3232(b);
SkFixed3232 product32 = (a32 * b32) >> 32;
SkFixed product = SkFixed3232ToFixed(product32);
```

## 局限性与注意事项

### 范围限制
SkFixed 仅能表示 -32768 ~ 32767 的数值,超出会溢出。

### 精度限制
小数部分仅 16 位,精度约 0.000015,某些场景不够。

### 乘法累积误差
连续乘法会累积舍入误差:
```cpp
SkFixed x = SkFloatToFixed(0.1f);
for (int i = 0; i < 1000; i++) {
    x = SkFixedMul(x, SK_Fixed1);  // 每次乘法都舍入
}
// x 可能不再精确等于 0.1
```

### 现代硬件不适用
在现代设备上,浮点数性能通常优于定点数。

## 相关文件
| 文件 | 关系 |
|------|------|
| `SkMath.h` | 整数数学工具 |
| `SkFloatingPoint.h` | 浮点数工具 |
| `SkScalar.h` | Scalar 类型定义 |
| 文本渲染模块 | 使用定点数表示字形位置 |

## 历史与演进
- 文件历史可追溯到 2006 年 (Android Open Source Project)
- 早期 Android 设备无浮点单元,定点数至关重要
- 随着硬件进步,定点数使用逐渐减少
- 保留主要用于向后兼容和特定优化场景
- ARM NEON 优化体现了平台特定性能调优
