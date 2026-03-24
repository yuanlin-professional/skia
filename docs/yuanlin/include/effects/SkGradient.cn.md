# SkGradient

> 源文件: `include/effects/SkGradient.h`

## 概述
SkGradient 提供了创建各种渐变 shader 的工厂函数和配置类,包括线性渐变、径向渐变、圆锥渐变和扫描渐变。该模块支持高级颜色插值选项,包括多种颜色空间(如 OKLab、LCH)和色相插值方法,是 Skia 渐变效果系统的核心接口。

## 架构位置
SkGradient 位于 Skia 的效果(effects)模块,是着色器(SkShader)子系统的重要组成部分。它为上层绘图 API 提供丰富的渐变填充能力,底层依赖于 GPU 或光栅管道实现高性能的渐变渲染。

## 主要类与结构体

### SkGradient::Interpolation
定义渐变颜色插值的方式。

**成员枚举**:

#### InPremul
```cpp
enum class InPremul : bool { kNo = false, kYes = true };
```
- **说明**: 是否在预乘 alpha 空间中插值
- **kNo**: 在非预乘空间插值(默认)
- **kYes**: 在预乘 alpha 空间插值

#### ColorSpace
定义插值使用的颜色空间。

| 枚举值 | 说明 |
|--------|------|
| kDestination | 默认行为,在目标表面的颜色空间中插值 |
| kSRGBLinear | 线性 sRGB 空间 |
| kLab | CIE Lab 颜色空间 |
| kOKLab | OKLab 颜色空间(改进的感知均匀性) |
| kOKLabGamutMap | OKLab + 色域映射到 Rec2020(实验性) |
| kLCH | CIE LCH(柱坐标 Lab) |
| kOKLCH | OKLCH(柱坐标 OKLab) |
| kOKLCHGamutMap | OKLCH + 色域映射(实验性) |
| kSRGB | sRGB 颜色空间 |
| kHSL | HSL(色相-饱和度-明度) |
| kHWB | HWB(色相-白度-黑度) |
| kDisplayP3 | Display P3 宽色域空间 |
| kRec2020 | Rec.2020 宽色域空间 |
| kProphotoRGB | ProPhoto RGB 宽色域空间 |
| kA98RGB | Adobe RGB 1998 |

**常量**:
```cpp
static constexpr int kColorSpaceCount =
    static_cast<int>(ColorSpace::kLastColorSpace) + 1;  // 14
```

#### HueMethod
定义色相插值方法(仅适用于 LCH、OKLCH、HSL、HWB)。

| 枚举值 | 说明 |
|--------|------|
| kShorter | 选择较短的圆周路径(默认) |
| kLonger | 选择较长的圆周路径 |
| kIncreasing | 始终增加色相值 |
| kDecreasing | 始终减少色相值 |

**常量**:
```cpp
static constexpr int kHueMethodCount =
    static_cast<int>(HueMethod::kLastHueMethod) + 1;  // 4
```

**成员变量**:
| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| fInPremul | InPremul | kNo | 是否预乘插值 |
| fColorSpace | ColorSpace | kDestination | 插值颜色空间 |
| fHueMethod | HueMethod | kShorter | 色相插值方法 |

**静态工厂方法**:
```cpp
static Interpolation FromFlags(uint32_t flags);
```
- **功能**: 从旧版标志创建 Interpolation(向后兼容)
- **参数**: `flags` - bit 0 控制是否预乘
- **返回值**: Interpolation 对象

### SkGradient::Colors
封装渐变颜色数据的容器类。

**构造函数**:
```cpp
Colors();  // 默认构造
Colors(SkSpan<const SkColor4f> colors,
       SkSpan<const float> pos,
       SkTileMode mode,
       sk_sp<SkColorSpace> cs = nullptr);

Colors(SkSpan<const SkColor4f> colors,
       SkTileMode tm,
       sk_sp<SkColorSpace> cs = nullptr);  // 均匀分布
```

**参数说明**:
- **colors**: 颜色数组
- **pos**: 颜色位置数组(0.0 到 1.0),可为空(均匀分布)
  - 必须严格递增
  - 如果首个值不是 0.0,会自动添加位置 0.0 的色标
  - 如果末个值不是 1.0,会自动添加位置 1.0 的色标
- **mode**: 平铺模式(SkTileMode)
- **cs**: 颜色空间(null 则为 sRGB)

**访问器**:
```cpp
SkSpan<const SkColor4f> colors() const;
SkSpan<const float> positions() const;
const sk_sp<SkColorSpace>& colorSpace() const;
SkTileMode tileMode() const;
```

**成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fColors | SkSpan<const SkColor4f> | 颜色数组 |
| fPos | SkSpan<const float> | 位置数组 |
| fColorSpace | sk_sp<SkColorSpace> | 颜色空间 |
| fTileMode | SkTileMode | 平铺模式 |

### SkGradient 主类
渐变配置容器。

**构造函数**:
```cpp
SkGradient();
SkGradient(const Colors& colors, const Interpolation& interp);
```

**访问器**:
```cpp
const Colors& colors() const;
const Interpolation& interpolation() const;
```

## 渐变工厂函数(SkShaders 命名空间)

### `LinearGradient()`
```cpp
SK_API sk_sp<SkShader> LinearGradient(const SkPoint pts[2],
                                      const SkGradient&,
                                      const SkMatrix* lm = nullptr);
```
- **功能**: 创建线性渐变 shader
- **参数**:
  - `pts`: 长度为 2 的点数组,定义渐变线段的端点
  - `grad`: 渐变配置(颜色和插值)
  - `lm`: 可选的局部矩阵
- **返回值**: SkShader 智能指针,输入无效时返回 nullptr
- **说明**: 沿着从 pts[0] 到 pts[1] 的线段进行颜色插值

### `RadialGradient()`
```cpp
SK_API sk_sp<SkShader> RadialGradient(SkPoint center,
                                      float radius,
                                      const SkGradient& grad,
                                      const SkMatrix* lm = nullptr);
```
- **功能**: 创建径向渐变 shader
- **参数**:
  - `center`: 圆心
  - `radius`: 半径(必须为正)
  - `grad`: 渐变配置
  - `lm`: 可选的局部矩阵
- **返回值**: SkShader 智能指针
- **说明**: 从圆心向外径向插值颜色

### `TwoPointConicalGradient()`
```cpp
SK_API sk_sp<SkShader> TwoPointConicalGradient(SkPoint start,
                                               float startRadius,
                                               SkPoint end,
                                               float endRadius,
                                               const SkGradient& grad,
                                               const SkMatrix* lm = nullptr);
```
- **功能**: 创建双点圆锥渐变 shader
- **参数**:
  - `start`: 起始圆的圆心
  - `startRadius`: 起始圆半径(必须为正)
  - `end`: 结束圆的圆心
  - `endRadius`: 结束圆半径(必须为正)
  - `grad`: 渐变配置
  - `lm`: 可选的局部矩阵
- **返回值**: SkShader 智能指针,输入无效时返回 nullptr
- **说明**: 遵循 HTML5 Canvas 的 createRadialGradient 规范

### `SweepGradient()`
```cpp
SK_API sk_sp<SkShader> SweepGradient(SkPoint center,
                                     float startAngle,
                                     float endAngle,
                                     const SkGradient&,
                                     const SkMatrix* lm = nullptr);

// 便利重载(默认 0-360 度)
static inline sk_sp<SkShader> SweepGradient(SkPoint center,
                                     const SkGradient& grad,
                                     const SkMatrix* lm = nullptr);
```
- **功能**: 创建扫描渐变 shader
- **参数**:
  - `center`: 扫描中心
  - `startAngle`: 起始角度(0 度为水平正 x 轴)
  - `endAngle`: 结束角度(必须大于 startAngle)
  - `grad`: 渐变配置
  - `lm`: 可选的局部矩阵
- **返回值**: SkShader 智能指针
- **说明**:
  - 支持负角度和大于 360 的角度
  - 绘制范围限制在 0-360 度
  - 类似 CSS conic-gradient 语义
  - 如果色标不包含 0 和 1 但在此范围内,外侧色标会自动重复

## 内部实现细节

### 颜色空间插值
不同颜色空间的插值会产生不同的视觉效果:
- **kDestination**: 最快,但可能不是感知均匀的
- **kSRGBLinear**: 物理上正确的光学混合
- **kLab/kOKLab**: 感知均匀,避免中间灰暗区域
- **kLCH/kOKLCH**: 保持色相一致,适合彩虹渐变
- **kHSL**: 传统图形学方法,可能产生意外的饱和度变化

### 色相插值策略
在柱坐标颜色空间(LCH、OKLCH、HSL、HWB)中,色相是圆周值:
- **kShorter**: 红(0°) → 黄(60°) 直接过渡
- **kLonger**: 红(0°) → 黄(60°) 绕过蓝/紫
- **kIncreasing**: 确保色相单调增加(可能绕圈)
- **kDecreasing**: 确保色相单调减少

### 色域映射(实验性)
OKLabGamutMap 和 OKLCHGamutMap 尝试将超出 Rec2020 色域的颜色映射回可显示范围,参考 CSS Color 4 草案。标记为实验性,不建议生产环境使用。

### 位置数组处理
位置数组的特殊处理逻辑:
1. 如果 pos 为空,颜色均匀分布
2. 如果 pos[0] != 0.0,自动添加 {0.0, colors[0]}
3. 如果 pos[n-1] != 1.0,自动添加 {1.0, colors[n-1]}
4. 位置必须严格递增,否则行为未定义

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/core/SkColor.h | SkColor4f 颜色定义 |
| include/core/SkColorSpace.h | 颜色空间管理 |
| include/core/SkPoint.h | 几何点定义 |
| include/core/SkShader.h | Shader 基类 |
| include/core/SkSpan.h | 数组视图 |
| include/core/SkTileMode.h | 平铺模式枚举 |

### 被依赖的模块
| 模块 | 用途 |
|------|------|
| src/shaders/gradients/ | 渐变 shader 的具体实现 |
| src/gpu/ganesh/effects/GrGradientShader.cpp | GPU 渐变渲染 |
| include/core/SkPaint.h | 通过 setShader 使用渐变 |
| examples/ 和 tests/ | 示例和测试代码 |

## 设计模式与设计决策

### 建造者模式变体
SkGradient::Colors 和 SkGradient::Interpolation 组合成完整的渐变配置,分离了"数据"和"算法"。

### 工厂模式
SkShaders 命名空间提供静态工厂函数,而非直接暴露实现类。

### 值语义
Colors 和 Interpolation 都是值类型,便于复制和传递,无生命周期问题。

### CSS 对齐
颜色空间和色相插值方法与 CSS Color Level 4 规范对齐,降低 Web 开发者的学习成本。

## 性能考量

### 颜色空间性能差异
| 颜色空间 | 性能 | 质量 |
|----------|------|------|
| kDestination | 最快 | 一般 |
| kSRGBLinear | 快 | 较好 |
| kOKLab/kOKLCH | 中等 | 优秀(感知均匀) |
| kLab/kLCH | 中等 | 好 |
| kHSL/kHWB | 快 | 一般(可能有色偏) |
| *GamutMap 变体 | 慢 | 实验性 |

### GPU 加速
所有渐变类型都在 GPU 上高度优化,通过 fragment shader 实现。

### 位置数组优化
均匀分布的渐变(pos 为空)可以使用更简单的插值公式,性能更好。

## 使用场景

### 基础线性渐变
```cpp
SkColor4f colors[] = {SkColors::kRed, SkColors::kBlue};
SkGradient::Colors gradColors(colors, SkTileMode::kClamp);
SkGradient grad(gradColors, {});
SkPoint pts[] = {{0, 0}, {100, 100}};
auto shader = SkShaders::LinearGradient(pts, grad);
```

### 感知均匀渐变
```cpp
SkGradient::Interpolation interp;
interp.fColorSpace = SkGradient::Interpolation::ColorSpace::kOKLab;
SkGradient grad(gradColors, interp);
auto shader = SkShaders::RadialGradient({50, 50}, 50, grad);
```

### 彩虹渐变
```cpp
SkGradient::Interpolation interp;
interp.fColorSpace = SkGradient::Interpolation::ColorSpace::kOKLCH;
interp.fHueMethod = SkGradient::Interpolation::HueMethod::kLonger;
// 创建平滑的彩虹效果
```

## 相关文件
| 文件 | 关系 |
|------|------|
| src/shaders/gradients/SkGradientShader.cpp | 渐变 shader 基类实现 |
| src/shaders/gradients/SkLinearGradient.cpp | 线性渐变实现 |
| src/shaders/gradients/SkRadialGradient.cpp | 径向渐变实现 |
| src/shaders/gradients/SkSweepGradient.cpp | 扫描渐变实现 |
| src/gpu/ganesh/effects/GrGradientEffect.h | GPU 渐变效果 |
| include/core/SkShader.h | Shader 基类 |
| include/core/SkTileMode.h | 平铺模式定义 |
