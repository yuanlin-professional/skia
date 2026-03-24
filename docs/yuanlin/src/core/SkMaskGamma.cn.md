# SkMaskGamma

> 源文件: src/core/SkMaskGamma.h, src/core/SkMaskGamma.cpp

## 概述

`SkMaskGamma` 是 Skia 图形库中用于伽玛校正的核心组件，专门处理文本渲染中的抗锯齿掩码（mask）的伽玛校正问题。在线性混合环境下，直接使用线性 alpha 值会导致文本显示过亮或过暗，`SkMaskGamma` 通过创建并维护查找表（LUT），将线性 alpha 值转换为伽玛校正后的 alpha 值，从而在伽玛不正确的混合环境中实现视觉上正确的文本渲染。

该模块包含三个主要组件：`SkColorSpaceLuminance`（色彩空间亮度转换抽象）、`SkTMaskGamma`（伽玛校正表生成器）和 `SkTMaskPreBlend`（预混合查找表访问器）。通过模板参数化 RGB 通道的亮度位数，系统可以灵活适应不同的性能和精度需求。

## 架构位置

`SkMaskGamma` 位于 Skia 核心层（`src/core`）的文本渲染管线中，处于以下架构位置：

- **上层依赖**：字体光栅化器（Font Rasterizer）生成原始抗锯齿掩码
- **本模块**：执行伽玛校正转换，生成校正后的掩码
- **下层使用**：Blitter（混合器）使用校正后的掩码进行像素混合
- **协作模块**：与 `SkMaskFilter`、`SkDraw` 等文本渲染组件协作

该模块是文本渲染质量优化的关键环节，特别是在 LCD 子像素渲染和高质量字体显示场景中至关重要。

## 主要类与结构体

### SkColorSpaceLuminance 抽象类

**继承关系**：
- 基类：`SkNoncopyable`（不可复制）
- 派生类：
  - `SkLinearColorSpaceLuminance`（线性色彩空间，gamma=1.0）
  - `SkGammaColorSpaceLuminance`（标准伽玛色彩空间）
  - `SkSRGBColorSpaceLuminance`（sRGB 色彩空间，gamma=0）

**关键成员变量**：无成员变量，纯虚接口

**核心方法**：
- `toLuma()`：将色彩空间亮度转换为线性亮度
- `fromLuma()`：将线性亮度转换为色彩空间亮度
- `computeLuminance()`：静态方法，计算颜色的感知亮度值
- `Fetch()`：静态工厂方法，根据 gamma 值返回对应的转换器实例

### SkTMaskGamma 模板类

**模板参数**：
- `R_LUM_BITS`：红色通道亮度位数（1-8）
- `G_LUM_BITS`：绿色通道亮度位数（1-8）
- `B_LUM_BITS`：蓝色通道亮度位数（1-8）

**继承关系**：继承自 `SkRefCnt`（引用计数）

**关键成员变量**：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fGammaTables` | `std::unique_ptr<uint8_t[]>` | 伽玛校正查找表（二维展平数组） |
| `kNumTables` | `static constexpr size_t` | 表的数量（2^kMaxLumBits） |
| `kTableWidth` | `static constexpr size_t` | 每个表的宽度（256） |
| `kTableNumElements` | `static constexpr size_t` | 总元素数（kNumTables * kTableWidth） |

### SkTMaskPreBlend 模板类

**继承关系**：无基类

**关键成员变量**：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fParent` | `sk_sp<const SkTMaskGamma<...>>` | 父 MaskGamma 对象的智能指针 |
| `fR` | `const uint8_t*` | 红色通道查找表指针 |
| `fG` | `const uint8_t*` | 绿色通道查找表指针 |
| `fB` | `const uint8_t*` | 蓝色通道查找表指针 |

## 公共 API 函数

### SkColorSpaceLuminance 接口

```cpp
virtual SkScalar toLuma(SkScalar gamma, SkScalar luminance) const = 0;
```
将给定色彩空间的亮度值转换为线性亮度（luma）。对于 sRGB，应用反伽玛曲线；对于标准 gamma，应用幂函数。

```cpp
virtual SkScalar fromLuma(SkScalar gamma, SkScalar luma) const = 0;
```
将线性亮度（luma）转换回色彩空间的亮度值。执行 `toLuma()` 的逆运算。

```cpp
static U8CPU computeLuminance(SkScalar gamma, SkColor c);
```
计算给定颜色的感知亮度值（0-255）。使用标准亮度系数（R: 0.2126, G: 0.7152, B: 0.0722）加权计算。

```cpp
static const SkColorSpaceLuminance& Fetch(SkScalar gamma);
```
根据 gamma 值返回相应的色彩空间转换器单例：
- `gamma == 0`：sRGB 转换器
- `gamma == 1.0`：线性转换器
- 其他值：标准 gamma 转换器

### SkTMaskGamma 方法

```cpp
constexpr SkTMaskGamma();
```
默认构造函数，创建线性（无校正）的 MaskGamma 对象。

```cpp
SkTMaskGamma(SkScalar contrast, SkScalar deviceGamma);
```
创建包含伽玛校正表的 MaskGamma 对象。`contrast` 参数（0.0-1.0）控制人工对比度，`deviceGamma` 指定目标设备的伽玛值。

```cpp
static SkColor CanonicalColor(SkColor color);
```
将颜色规范化为最接近的可表示颜色，基于模板指定的位深度。用于颜色量化。

```cpp
PreBlend preBlend(SkColor color) const;
```
返回针对给定颜色的预混合查找表。根据颜色的 RGB 分量选择对应的表行。

```cpp
const uint8_t* getGammaTables() const;
```
返回完整查找表的原始指针，用于上传到纹理或其他分析用途。

### SkTMaskPreBlend 方法

```cpp
bool isApplicable() const;
```
检查是否应应用预混合。当 `fG` 为 `nullptr` 时返回 `false`，表示线性模式。

## 内部实现细节

### 伽玛校正表构建算法

`SkTMaskGamma_build_correcting_lut()` 函数实现核心校正逻辑：

1. **源亮度计算**：将源颜色强度（srcI）转换为线性亮度 `linSrc`
2. **目标亮度估算**：使用感知逆（`1.0 - src`）作为目标亮度
3. **对比度调整**：根据目标亮度调整对比度系数：`adjustedContrast = contrast * linDst`
4. **应用对比度**：`srca = apply_contrast(rawSrca, adjustedContrast)`，公式为 `srca + (1-srca) * contrast * srca`
5. **线性混合模拟**：计算期望的线性输出 `linOut = linSrc * srca + linDst * dsta`
6. **逆向求解**：从期望输出反推所需的混合因子 `result = (out - dst) / (src - dst)`
7. **量化到 8 位**：将结果缩放到 0-255 并存入表中

### 不连续性处理

当源颜色和目标颜色非常接近时（差值 < 1/256），算法切换到简化模式，仅应用对比度调整，避免除零和数值不稳定性。

### 色彩空间转换实现

三种色彩空间实现的差异：

- **线性**（`gamma=1.0`）：直接返回输入值，无转换
- **标准 gamma**：使用 `pow(x, gamma)` 和 `pow(x, 1/gamma)`
- **sRGB**：应用分段函数
  - `toLuma`：`x <= 0.04045 ? x/12.92 : pow((x+0.055)/1.055, 2.4)`
  - `fromLuma`：`x <= 0.0031308 ? x*12.92 : 1.055*pow(x, 1/2.4) - 0.055`

### 查找表索引计算

`preBlend()` 方法计算表索引：

```cpp
const size_t r_index = (SkColorGetR(color) >> lum_shift) * kTableWidth;
```

- `lum_shift = 8 - kMaxLumBits`：将 8 位颜色分量缩减到指定位深度
- 乘以 `kTableWidth`（256）定位到对应表行
- 返回该行的起始指针供查找使用

### 模板特化优化

`sk_t_scale255` 函数提供模板特化优化常见位深度：

- 1 位：乘以 0xFF
- 2 位：乘以 0x55
- 4 位：乘以 0x11
- 8 位：直接返回
- 通用版本：使用位移和或运算扩展

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkColor.h` | 颜色类型和操作 |
| `include/core/SkRefCnt.h` | 引用计数智能指针 |
| `include/core/SkScalar.h` | 标量类型定义 |
| `include/private/base/SkFloatingPoint.h` | 浮点数工具（pow, round 等） |
| `src/core/SkColorData.h` | 亮度系数宏定义 |
| `<cmath>` | 标准数学函数 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `SkBlitter` 及子类 | 使用校正后的 alpha 值进行像素混合 |
| `SkDraw` | 文本绘制流程中应用伽玛校正 |
| `SkScalerContext` | 字形光栅化时考虑伽玛校正 |
| LCD 渲染器 | 子像素渲染需要精确的伽玛校正 |

## 设计模式与设计决策

### 策略模式（色彩空间转换）

`SkColorSpaceLuminance` 使用策略模式封装不同的伽玛转换算法，通过 `Fetch()` 工厂方法返回单例实例，避免运行时类型判断和虚函数开销。

### 模板元编程

使用模板参数化 RGB 位深度，允许编译期优化：

- **常量折叠**：`kNumTables`、`kTableWidth` 等都是编译期常量
- **循环展开**：编译器可以针对具体位深度优化循环
- **特化优化**：为常见配置（如 5-6-5）提供专门优化

### 查找表（LUT）优化

空间换时间策略，避免运行时的复杂浮点运算：

- **预计算**：构造时一次性计算所有可能的转换结果
- **O(1) 查找**：运行时仅需数组索引操作
- **缓存友好**：连续内存布局提升缓存命中率

### 引用计数管理

`SkTMaskGamma` 继承 `SkRefCnt`，使用 `sk_sp` 智能指针自动管理生命周期。`SkTMaskPreBlend` 持有父对象的强引用，确保查找表指针始终有效。

### 不可复制语义

`SkColorSpaceLuminance` 继承 `SkNoncopyable`，强制单例模式，避免重复的全局对象。

### Constexpr 构造

默认构造函数使用 `constexpr`，允许编译期创建线性 MaskGamma 对象，减少运行时初始化开销。

## 性能考量

### 查找表的内存布局

二维表展平为一维数组，访问模式：`fGammaTables[row_index * kTableWidth + column_index]`

- **优势**：单次内存分配，连续存储利于 CPU 缓存预取
- **大小**：对于 3-3-3 配置，`8 * 256 = 2KB`；对于 5-6-5 配置，`64 * 256 = 16KB`

### 浮点运算优化

在表构建过程中：

- 使用 `ii += 1.0f` 而非 `i * (1.0f / 255.0f)` 避免累积误差
- 避免整数到浮点转换的隐式开销
- 使用 `sk_float_round2int` 进行高效的舍入转换

### 分支预测优化

`sk_apply_lut_if` 使用模板参数 `APPLY_LUT` 消除运行时分支：

```cpp
template<bool APPLY_LUT> static inline U8CPU sk_apply_lut_if(...) {
    return component;  // 线性模式，编译器优化掉整个函数
}
template<> inline U8CPU sk_apply_lut_if<true>(...) {
    return lut[component];  // 应用查找表
}
```

### 单例模式的性能

`Fetch()` 返回静态局部变量的引用，无构造和析构开销，且线程安全（C++11 保证）。

### 缓存行对齐考量

虽然代码中未显式对齐，但 256 字节的表宽度恰好是常见缓存行大小（64 字节）的倍数，有利于缓存效率。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/core/SkDraw.cpp` | 使用者 | 文本绘制流程中应用伽玛校正 |
| `src/core/SkBlitter.cpp` | 使用者 | Blitter 使用校正后的掩码进行混合 |
| `src/core/SkScalerContext.cpp` | 使用者 | 字形光栅化上下文中考虑伽玛 |
| `src/core/SkColorData.h` | 依赖 | 提供亮度系数定义（SK_LUM_COEFF_*） |
| `include/core/SkColor.h` | 依赖 | 颜色类型和操作函数 |
| `include/private/base/SkFloatingPoint.h` | 依赖 | 浮点数工具函数 |
| `tests/MaskGammaTest.cpp` | 测试 | 单元测试验证伽玛校正逻辑 |

---

**总结**：`SkMaskGamma` 是 Skia 文本渲染质量优化的核心组件，通过精密的伽玛校正算法和高效的查找表机制，在性能和质量之间取得了优异的平衡。其模板化设计、策略模式和查找表优化体现了现代 C++ 高性能编程的最佳实践，为 Skia 在各种显示设备上提供一致的文本渲染效果奠定了基础。
