# SkHighContrastFilter

> 源文件
> - include/effects/SkHighContrastFilter.h
> - src/effects/SkHighContrastFilter.cpp

## 概述

`SkHighContrastFilter` 是 Skia 图形库中专为低视力用户设计的颜色滤镜,通过一系列可配置的变换来提升图像对比度和可读性。该滤镜支持灰度转换、亮度/明度反转以及对比度调整三种变换,可按顺序组合应用,满足不同视觉辅助需求。

该滤镜是无障碍功能的重要组成部分,广泛应用于操作系统级别的辅助功能设置、浏览器的高对比度模式、以及各种需要增强可视性的应用场景。通过灵活的配置选项,可以为不同类型的视觉障碍(如色盲、弱视等)提供针对性的视觉增强。

## 架构位置

`SkHighContrastFilter` 位于 Skia 特效模块的颜色处理层:

- 位于 `include/effects/` 公共接口目录
- 实现为 `SkColorFilter` 的特殊类型
- 基于 `SkRuntimeEffect` 实现,使用着色器进行颜色变换
- 使用 `SkColorFilterPriv::WithWorkingFormat` 包装,确保在线性色彩空间中处理
- 与 `SkKnownRuntimeEffects` 系统集成,使用预编译的运行时特效
- 作为系统无障碍功能的底层实现

## 主要类与结构体

### SkHighContrastConfig

配置结构体,定义高对比度变换的参数:

**枚举类型 InvertStyle:**

| 枚举值 | 说明 |
|--------|------|
| `kNoInvert` | 不反转颜色 |
| `kInvertBrightness` | 在 RGB 空间反转亮度(1 - color) |
| `kInvertLightness` | 在 HSL 空间反转明度 |

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fGrayscale` | `bool` | 是否转换为灰度,true 时移除所有颜色信息 |
| `fInvertStyle` | `InvertStyle` | 反转模式,定义如何反转颜色 |
| `fContrast` | `SkScalar` | 对比度调整值,范围 [-1.0, 1.0],0.0 表示不调整 |

**成员函数:**

```cpp
bool isValid() const;
```

验证配置参数是否在有效范围内:
- `fInvertStyle` 在枚举范围内
- `fContrast` 在 [-1.0, 1.0] 范围内

### SkHighContrastFilter

**继承关系:**
- 这是一个工厂结构体,不包含状态
- 返回的实际是 `SkColorFilter` 对象

## 公共 API 函数

### Make

```cpp
static sk_sp<SkColorFilter> Make(const SkHighContrastConfig& config);
```

创建高对比度颜色滤镜:

- **参数:**配置结构体,定义所有变换参数
- **返回:**颜色滤镜智能指针,配置无效时返回 `nullptr`
- **验证:**自动调用 `config.isValid()` 验证参数

**使用示例:**
```cpp
// 简单灰度滤镜
SkHighContrastConfig config;
config.fGrayscale = true;
auto filter = SkHighContrastFilter::Make(config);

// 反转亮度并增强对比度
SkHighContrastConfig config2;
config2.fInvertStyle = SkHighContrastConfig::InvertStyle::kInvertBrightness;
config2.fContrast = 0.5f;  // 增加 50% 对比度
auto filter2 = SkHighContrastFilter::Make(config2);

// 完整变换:灰度 + 反转明度 + 高对比度
SkHighContrastConfig config3(true, InvertStyle::kInvertLightness, 0.8f);
auto filter3 = SkHighContrastFilter::Make(config3);
```

## 内部实现细节

### 变换顺序

滤镜按以下顺序应用变换:
1. **灰度转换:**如果 `fGrayscale = true`
2. **颜色反转:**根据 `fInvertStyle`
3. **对比度调整:**根据 `fContrast`

### 运行时特效实现

滤镜使用 SkRuntimeEffect(SkSL 着色器)实现:

```cpp
const SkRuntimeEffect* highContrastEffect =
    GetKnownRuntimeEffect(SkKnownRuntimeEffects::StableKey::kHighContrast);
```

- 预编译的 SkSL 着色器存储在 `SkKnownRuntimeEffects` 中
- 着色器接收 uniforms:grayscale, invertStyle, contrast
- GPU 加速处理,逐像素并行计算

### Uniforms 结构

```cpp
struct Uniforms {
    float grayscale;     // 0.0(关闭)或 1.0(开启)
    float invertStyle;   // 0.0(无)、1.0(亮度)、2.0(明度)
    float contrast;      // 对比度增益因子
};
```

### 对比度计算

对比度调整使用非线性映射:

```cpp
float c = SkTPin(config.fContrast, -1.0f + FLT_EPSILON, +1.0f - FLT_EPSILON);
float contrastGain = (1 + c) / (1 - c);
```

**映射关系:**
- `c = -1.0`:  `gain ≈ 0` (完全灰色)
- `c = 0.0`:   `gain = 1` (无变化)
- `c = +1.0`:  `gain → ∞` (最大对比度)

**边界处理:**
- 钳制到 `[-1 + ε, 1 - ε]` 避免除零
- 使用 `FLT_EPSILON` 保持对称性

### 工作色彩空间

使用 `SkColorFilterPriv::WithWorkingFormat` 包装:

```cpp
return SkColorFilterPriv::WithWorkingFormat(
    highContrastEffect->makeColorFilter(...),
    &SkNamedTransferFn::kLinear,  // 线性传递函数
    nullptr,                       // 使用目标色域
    &kUnpremul);                  // 非预乘 Alpha
```

**作用:**
- 在线性色彩空间中进行变换,确保数学正确性
- 自动处理色彩空间转换和 Alpha 预乘
- 非预乘 Alpha 避免颜色泄漏

### 灰度转换

在着色器中实现标准亮度公式:
```
Y = 0.2126 * R + 0.7152 * G + 0.0722 * B
```

这是 Rec.709(sRGB)的亮度系数,符合人眼对不同颜色的感知灵敏度。

### 亮度反转 vs 明度反转

**亮度反转(RGB 空间):**
```
R' = 1 - R
G' = 1 - G
B' = 1 - B
```
- 简单、快速
- 直接反转每个颜色通道
- 可能导致色相变化

**明度反转(HSL 空间):**
```
HSL = RGBtoHSL(color)
L' = 1 - L
color' = HSLtoRGB(H, S, L')
```
- 更复杂,需要色彩空间转换
- 保持色相和饱和度,只反转明度
- 视觉上更自然,适合保留颜色信息

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| `SkColorFilter` | 颜色滤镜基类 |
| `SkRuntimeEffect` | 运行时着色器系统 |
| `SkKnownRuntimeEffects` | 预编译着色器管理 |
| `SkColorFilterPriv` | 颜色滤镜内部工具 |
| `SkTPin` | 数值钳制工具 |
| `SkData` | uniforms 数据容器 |
| `SkNamedTransferFn` | 命名传递函数 |

**被依赖的模块:**

| 模块 | 关系 |
|------|------|
| 操作系统无障碍服务 | 系统级高对比度模式 |
| 浏览器渲染引擎 | 网页高对比度显示 |
| 应用辅助功能 | 提升 UI 可读性 |
| 阅读器应用 | 文本对比度增强 |
| 图像查看器 | 图像增强工具 |

## 设计模式与设计决策

### 配置对象模式

使用独立的配置结构体:
- 参数组织清晰,易于理解
- 支持默认值构造
- 便于验证和传递
- 未来扩展不影响 API

### 工厂方法模式

通过静态 `Make` 方法创建:
- 封装创建逻辑
- 支持创建失败(返回 `nullptr`)
- 隐藏内部实现细节

### 管道式变换

三个变换按固定顺序应用:
- 灰度化去除颜色信息
- 反转改变明暗关系
- 对比度增强突出差异
- 顺序经过无障碍专家设计,效果最优

### GPU 加速

使用 SkRuntimeEffect 实现:
- GPU 并行处理,性能优异
- 支持复杂的颜色空间转换
- 统一的着色器管线
- 可在不同平台复用

### 预编译着色器

使用 `SkKnownRuntimeEffects`:
- 避免运行时编译开销
- 减少首次使用延迟
- 便于着色器优化和测试

### 线性色彩空间处理

使用 `WithWorkingFormat`:
- 在物理上正确的线性空间计算
- 自动处理伽马校正
- 避免伽马空间计算错误

## 性能考量

### GPU 加速

- 着色器在 GPU 上逐像素并行执行
- 对大图像性能优势明显
- 小图像可能受 GPU 启动开销影响

### 着色器复杂度

- **灰度转换:**简单加权和,1 次乘加
- **亮度反转:**简单减法,3 次操作
- **明度反转:**RGB↔HSL 转换,涉及三角函数和条件分支
- **对比度调整:**乘法和加法

### 预编译优势

- 避免运行时着色器编译
- 减少首帧延迟
- 可预先进行优化

### 色彩空间转换开销

`WithWorkingFormat` 引入额外转换:
- 输入:源色彩空间 → 线性色彩空间
- 输出:线性色彩空间 → 目标色彩空间
- 对于已经是线性的数据,开销较小

### 内存占用

- uniforms 结构仅 12 字节
- 着色器代码已预编译共享
- 每个滤镜实例开销极小

### 优化建议

- 对于静态配置,复用滤镜实例
- 批量应用滤镜减少状态切换
- 对于 CPU 渲染,考虑自定义实现避免 GPU 同步

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/effects/SkHighContrastFilter.h` | 公共接口头文件 |
| `src/effects/SkHighContrastFilter.cpp` | 实现文件 |
| `include/core/SkColorFilter.h` | 颜色滤镜基类 |
| `include/effects/SkRuntimeEffect.h` | 运行时特效系统 |
| `src/core/SkKnownRuntimeEffects.h` | 预编译着色器管理 |
| `src/core/SkColorFilterPriv.h` | 颜色滤镜内部工具 |
| `include/private/base/SkTPin.h` | 数值钳制工具 |
| `src/sksl/` | SkSL 着色器实现目录 |
