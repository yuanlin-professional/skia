# SkSurfaceProps

> 源文件: `include/core/SkSurfaceProps.h`

## 概述
SkSurfaceProps 描述了 SkSurface(渲染表面)的属性和约束条件,包括像素几何布局、文本渲染参数和渲染标志。渲染引擎在绘制时可以解析这些属性,优化性能或改善渲染质量,特别是在文本渲染和抗锯齿方面。

## 架构位置
SkSurfaceProps 位于 Skia 核心(core)模块的表面管理层,是 SkSurface 创建和配置的关键组件。它连接了操作系统的显示特性(如 LCD 子像素布局)和 Skia 的渲染优化,影响文本渲染、抗锯齿策略和 GPU 渲染模式。

## 主要类与结构体

### SkPixelGeometry 枚举
描述 LCD 子像素的排列方式。

**枚举值**:
| 枚举值 | 说明 |
|--------|------|
| kUnknown_SkPixelGeometry | 未知布局(用于可移植或需要变换的像素) |
| kRGB_H_SkPixelGeometry | RGB 水平排列(红-绿-蓝) |
| kBGR_H_SkPixelGeometry | BGR 水平排列(蓝-绿-红) |
| kRGB_V_SkPixelGeometry | RGB 垂直排列 |
| kBGR_V_SkPixelGeometry | BGR 垂直排列 |

**辅助函数**:
```cpp
static inline bool SkPixelGeometryIsRGB(SkPixelGeometry geo);  // 是否 RGB 顺序
static inline bool SkPixelGeometryIsBGR(SkPixelGeometry geo);  // 是否 BGR 顺序
static inline bool SkPixelGeometryIsH(SkPixelGeometry geo);    // 是否水平排列
static inline bool SkPixelGeometryIsV(SkPixelGeometry geo);    // 是否垂直排列
```

### SkSurfaceProps 类
描述 SkSurface 的属性和约束。

**继承关系**: 无(值类型)

#### Flags 枚举
控制渲染行为的标志位。

| 标志 | 值 | 说明 |
|------|-----|------|
| kDefault_Flag | 0 | 默认设置,无特殊标志 |
| kUseDeviceIndependentFonts_Flag | 1 << 0 | 使用设备无关字体(用于测试/比较) |
| kDynamicMSAA_Flag | 1 << 1 | 使用内部 MSAA 渲染非 MSAA 的 GPU surface |
| kAlwaysDither_Flag | 1 << 2 | 始终启用抖动(仅影响 GPU 后端) |
| kPreservesTransparentDraws_Flag | 1 << 3 | 保留透明绘制(不跳过它们) |

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fFlags | uint32_t | 标志位组合 |
| fPixelGeometry | SkPixelGeometry | 像素几何布局 |
| fTextContrast | SkScalar | 文本对比度(用于掩码混合) |
| fTextGamma | SkScalar | 文本 Gamma 值 |

## 公共 API 函数

### 构造函数

#### 默认构造函数
```cpp
SkSurfaceProps();
```
- **功能**: 创建默认属性(无标志,未知像素几何,平台默认对比度/gamma)
- **返回值**: SkSurfaceProps 对象

#### 标志和像素几何构造函数
```cpp
SkSurfaceProps(uint32_t flags, SkPixelGeometry);
```
- **功能**: 指定标志和像素几何
- **参数**:
  - `flags`: 标志位组合
  - `pixelGeometry`: 像素几何布局
- **说明**: 使用平台默认的对比度和 gamma

#### 完整构造函数
```cpp
SkSurfaceProps(uint32_t flags, SkPixelGeometry,
               SkScalar textContrast, SkScalar textGamma);
```
- **功能**: 指定所有参数
- **参数**:
  - `flags`: 标志位组合
  - `pixelGeometry`: 像素几何布局
  - `textContrast`: 文本对比度(0.0 到 1.0)
  - `textGamma`: 文本 Gamma 值(0.0 到 4.0,不含 4.0)

### 成员函数

#### `cloneWithPixelGeometry()`
```cpp
SkSurfaceProps cloneWithPixelGeometry(SkPixelGeometry newPixelGeometry) const;
```
- **功能**: 创建副本,但使用新的像素几何
- **参数**: `newPixelGeometry` - 新的像素几何布局
- **返回值**: 修改后的 SkSurfaceProps 副本

#### 访问器函数
```cpp
uint32_t flags() const;                    // 获取标志位
SkPixelGeometry pixelGeometry() const;     // 获取像素几何
SkScalar textContrast() const;             // 获取文本对比度
SkScalar textGamma() const;                // 获取文本 Gamma
```

#### 标志查询函数
```cpp
bool isUseDeviceIndependentFonts() const;  // 是否使用设备无关字体
bool isAlwaysDither() const;               // 是否始终抖动
bool preservesTransparentDraws() const;    // 是否保留透明绘制
```

#### 比较运算符
```cpp
bool operator==(const SkSurfaceProps& that) const;
bool operator!=(const SkSurfaceProps& that) const;
```

### 常量定义
```cpp
static constexpr SkScalar kMaxContrastInclusive = 1;   // 最大对比度
static constexpr SkScalar kMinContrastInclusive = 0;   // 最小对比度
static constexpr SkScalar kMaxGammaExclusive = 4;      // 最大 Gamma(不含)
static constexpr SkScalar kMinGammaInclusive = 0;      // 最小 Gamma
```

## 内部实现细节

### 像素几何与子像素渲染
LCD 显示器的每个像素由红、绿、蓝三个子像素组成。Skia 可以利用这一特性进行子像素抗锯齿(LCD 文本渲染):
- **RGB_H**: 标准横屏显示器(子像素横向排列 R-G-B)
- **BGR_H**: 某些显示器的反向排列
- **RGB_V/BGR_V**: 竖屏或旋转显示器

错误的几何设置会导致文本出现彩色边缘。

### 文本对比度和 Gamma
- **fTextContrast**: 控制掩码混合的对比度,值 0.5 在清晰度和平滑度之间取得平衡
  - 低值(< 0.5): 小字体可能显得模糊
  - 高值(> 0.5): LCD 边缘可能出现彩色条纹
- **fTextGamma**: 用于掩码覆盖的 Gamma 混合,独立于颜色空间的 Gamma

注释特别说明:此 Gamma 专用于掩码覆盖混合,与表面的颜色空间无关。

### Dynamic MSAA
`kDynamicMSAA_Flag` 允许 GPU 后端在内部使用多重采样抗锯齿(MSAA)渲染到非 MSAA 表面:
- 在渲染时使用 MSAA 缓冲区
- 最终 resolve 到非 MSAA 目标
- 提升质量但增加内存和性能开销

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/core/SkScalar.h | 浮点类型定义 |
| include/core/SkTypes.h | 基础类型和 SK_API 宏 |
| include/private/base/SkTo.h | SkToBool 等转换工具 |

### 被依赖的模块
| 模块 | 用途 |
|------|------|
| include/core/SkSurface.h | Surface 创建时指定属性 |
| include/gpu/GrBackendSurface.h | GPU 后端表面配置 |
| src/core/SkDevice.h | 设备创建时传递属性 |
| src/gpu/ganesh/GrRenderTargetContext.h | GPU 渲染目标配置 |
| src/text/gpu/TextBlob.cpp | 文本渲染使用像素几何信息 |

## 设计模式与设计决策

### 值语义
SkSurfaceProps 使用值语义而非引用语义:
- 可以安全复制和传递
- 无生命周期管理问题
- 支持默认拷贝构造和赋值

### 不可变性的例外
虽然是值类型,但提供了 `cloneWithPixelGeometry()` 而非 setter,体现了倾向不可变设计的理念。

### 平台适配模式
通过像素几何枚举抽象不同平台的显示特性,使上层代码无需关心平台差异。

## 性能考量

### 子像素渲染开销
启用子像素渲染(通过正确设置像素几何)会:
- **提升**: 文本渲染清晰度(尤其是小字体)
- **增加**: 内存占用(3 倍子像素数据)和计算复杂度

### 设备无关字体
`kUseDeviceIndependentFonts_Flag` 禁用子像素渲染优化:
- **优点**: 跨设备一致性(用于测试)
- **缺点**: 文本可能不如设备优化版清晰

### Dynamic MSAA 权衡
`kDynamicMSAA_Flag`:
- **优点**: 高质量抗锯齿
- **缺点**: 2-4 倍内存占用,resolve 操作开销

### 抖动标志
`kAlwaysDither_Flag`:
- **优点**: 减少色阶(banding),改善渐变质量
- **缺点**: 轻微性能开销,在高色深显示器上收益有限

## 平台相关说明

### Windows
通常使用 `kBGR_H_SkPixelGeometry`(ClearType 默认配置)。

### macOS
通常使用 `kRGB_H_SkPixelGeometry`,但 Retina 显示器可能使用 `kUnknown_SkPixelGeometry`(高 DPI 下子像素渲染收益较小)。

### Android
需要查询系统配置确定像素几何,不同设备差异大。

### Linux
通常使用 `kRGB_H_SkPixelGeometry`,但用户可通过 fontconfig 配置。

## 使用场景

### 创建 Surface
```cpp
SkSurfaceProps props(SkSurfaceProps::kAlwaysDither_Flag,
                     kRGB_H_SkPixelGeometry);
auto surface = SkSurfaces::Raster(imageInfo, &props);
```

### GPU Surface 配置
```cpp
SkSurfaceProps props(SkSurfaceProps::kDynamicMSAA_Flag,
                     kUnknown_SkPixelGeometry);
auto gpuSurface = SkSurfaces::RenderTarget(context, skgpu::Budgeted::kYes,
                                            imageInfo, sampleCount, &props);
```

### 测试场景
```cpp
SkSurfaceProps props(SkSurfaceProps::kUseDeviceIndependentFonts_Flag,
                     kUnknown_SkPixelGeometry);
// 确保跨平台测试结果一致
```

## 相关文件
| 文件 | 关系 |
|------|------|
| include/core/SkSurface.h | 使用 SkSurfaceProps 创建 Surface |
| src/core/SkDevice.h | Device 使用这些属性配置渲染 |
| src/gpu/ganesh/GrRenderTargetProxy.h | GPU 渲染目标使用这些属性 |
| src/core/SkStrike.h | 字体缓存使用像素几何信息 |
| include/core/SkCanvas.h | Canvas 从 Surface 继承这些属性 |
