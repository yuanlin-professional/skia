# SkBlurMask

> 源文件：src/core/SkBlurMask.h, src/core/SkBlurMask.cpp

## 概述

`SkBlurMask` 是 Skia 中负责模糊遮罩（mask）处理的核心工具类。它提供了多种模糊算法的静态方法，用于将矩形和圆角矩形进行高斯模糊处理。该类实现了从 sigma（标准差）到像素半径的转换，以及基于盒式滤波器（box filter）近似和精确高斯卷积的模糊算法。

主要功能包括：
- 矩形和圆角矩形的快速模糊
- 基于盒式滤波器的近似高斯模糊（BoxBlur）
- 精确的高斯模糊卷积（BlurGroundTruth）
- Sigma 与像素半径的双向转换
- 解析式模糊轮廓生成（用于矩形边缘）

## 架构位置

`SkBlurMask` 位于 Skia 核心图形库的遮罩处理层：

```
src/core/
├── SkBlurMask.h/cpp          # 模糊遮罩算法实现
├── SkBlurMaskFilterImpl      # 模糊遮罩滤镜实现
├── SkBlurEngine              # 后端无关的模糊引擎
├── SkMask.h                  # 遮罩基础数据结构
└── SkMaskBlurFilter          # 遮罩模糊滤波器
```

该类是遮罩模糊功能的底层实现，被 `SkBlurMaskFilterImpl` 等上层模糊滤镜调用。

## 主要类与结构体

### SkBlurMask

纯静态工具类，不可实例化。

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| kBLUR_SIGMA_SCALE | constexpr SkScalar (0.57735f) | Sigma 缩放常数，用于与 CSS 规范匹配 |

**关键静态方法：**

| 方法名 | 说明 |
|-------|------|
| `ConvertRadiusToSigma()` | 将像素半径转换为高斯标准差 |
| `ConvertSigmaToRadius()` | 将高斯标准差转换为像素半径 |
| `BoxBlur()` | 使用盒式滤波器近似的快速模糊 |
| `BlurRect()` | 矩形的解析式模糊 |
| `BlurRRect()` | 圆角矩形的模糊 |
| `BlurGroundTruth()` | 精确的高斯卷积模糊（参考实现） |

## 公共 API 函数

### 1. 半径与 Sigma 转换

```cpp
static SkScalar ConvertRadiusToSigma(SkScalar radius)
static SkScalar ConvertSigmaToRadius(SkScalar sigma)
```

**功能：**在模糊半径和高斯标准差之间转换。使用缩放因子 `kBLUR_SIGMA_SCALE (0.57735 ≈ 1/√3)` 以匹配 CSS 规范。

**使用场景：**UI 框架通常以像素半径指定模糊强度，而高斯模糊算法需要标准差参数。

### 2. 盒式模糊（Box Blur）

```cpp
[[nodiscard]] static bool BoxBlur(SkMaskBuilder* dst,
                                   const SkMask& src,
                                   SkScalar sigma,
                                   SkBlurStyle style,
                                   SkIVector* margin = nullptr)
```

**功能：**使用三次盒式滤波器近似高斯模糊，速度快但精度略低。

**参数：**
- `dst`: 输出遮罩构建器
- `src`: 输入遮罩（支持 kBW、kA8、kARGB32、kLCD16 格式）
- `sigma`: 高斯标准差
- `style`: 模糊样式（kNormal、kSolid、kOuter、kInner）
- `margin`: 返回模糊边缘扩展量（可选）

**返回值：**成功返回 `true`，失败（如溢出）返回 `false`。

### 3. 矩形解析式模糊

```cpp
[[nodiscard]] static bool BlurRect(SkScalar sigma,
                                    SkMaskBuilder* dst,
                                    const SkRect& src,
                                    SkBlurStyle style,
                                    SkIVector* margin = nullptr,
                                    SkMaskBuilder::CreateMode createMode)
```

**功能：**使用解析方法快速计算矩形模糊，无需完整卷积。基于模糊阶跃函数的闭式解。

**优势：**比通用模糊算法快得多，特别适合 UI 矩形阴影。

### 4. 精确高斯模糊

```cpp
[[nodiscard]] static bool BlurGroundTruth(SkScalar sigma,
                                           SkMaskBuilder* dst,
                                           const SkMask& src,
                                           SkBlurStyle style,
                                           SkIVector* margin = nullptr)
```

**功能：**使用真实的高斯卷积核进行精确模糊，主要用于测试和验证。速度慢，不推荐在生产环境使用。

### 5. 解析式轮廓工具

```cpp
static uint8_t ProfileLookup(const uint8_t* profile, int loc,
                              int blurredWidth, int sharpWidth)

static void ComputeBlurProfile(uint8_t* profile, int size, SkScalar sigma)

static void ComputeBlurredScanline(uint8_t* pixels, const uint8_t* profile,
                                   unsigned int width, SkScalar sigma)
```

**功能：**生成和查询一维模糊轮廓，用于矩形模糊的快速计算。基于 Michael Herf 的阴影矩形算法。

## 内部实现细节

### 1. Sigma 缩放常数

```cpp
static const SkScalar kBLUR_SIGMA_SCALE = 0.57735f;  // ≈ 1/√3
```

该常数用于将"高质量"模糊与 CSS/Canvas 规范对齐。历史原因导致 Safari 使用此缩放因子，Skia 为保持兼容性也采用相同值。

### 2. 盒式滤波器近似

`BoxBlur()` 使用 `SkMaskBlurFilter` 实现三次盒式卷积，根据 SVG 规范近似高斯模糊：

```
window = floor(sigma * 3 * sqrt(2*π) / 4 + 0.5)
```

对于极小的 sigma（< 2），会退化为精度不足，此时应使用其他方法。

### 3. 模糊样式处理

四种模糊样式通过后处理实现：
- **kNormal**: 直接输出模糊结果
- **kSolid**: 模糊结果与原始遮罩叠加（屏幕混合）
- **kOuter**: 从模糊结果中减去原始遮罩（外发光）
- **kInner**: 模糊结果与原始遮罩相乘（内发光）

### 4. 高斯积分函数

`gaussianIntegral()` 实现了盒式卷积的分段多项式近似：

```
三次盒式卷积 -> 分段二次函数 -> 积分 -> 分段三次函数
```

该函数用于生成模糊阶跃函数的轮廓曲线。

### 5. 矩形快速模糊原理

矩形模糊利用可分离性：
1. 计算水平和垂直方向的一维模糊扫描线
2. 通过乘法组合成二维模糊结果
3. 每个像素值 = `horizontalScanline[x] * verticalScanline[y] / 255`

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `SkMask` | 遮罩数据结构 |
| `SkMaskBuilder` | 遮罩构建工具 |
| `SkRRect` | 圆角矩形定义 |
| `SkBlurTypes` | 模糊样式枚举 |
| `SkMaskBlurFilter` | 盒式模糊滤波器实现 |
| `SkColorPriv` | Alpha 混合计算 |
| `SkMath` | 数学工具函数 |

### 被依赖的模块

| 模块 | 使用方式 |
|-----|---------|
| `SkBlurMaskFilterImpl` | 调用 BoxBlur 和 BlurRect |
| `SkMaskFilter` | 通过滤镜接口间接使用 |
| `SkCanvas` | 绘制模糊形状时调用 |
| `SkPaint` | 模糊效果配置 |

## 设计模式与设计决策

### 1. 静态工具类模式

`SkBlurMask` 采用纯静态方法设计，无需实例化，所有方法都是无状态的。这样设计的优点：
- 避免对象创建开销
- 清晰表达"工具函数集合"的语义
- 便于在任何地方直接调用

### 2. 多层次模糊策略

提供三种精度级别的模糊实现：
1. **解析式（BlurRect）**: 最快，仅适用于矩形
2. **盒式近似（BoxBlur）**: 快速通用方法
3. **精确高斯（BlurGroundTruth）**: 慢但准确，用于测试

这种分层设计允许根据场景选择性能和质量的权衡。

### 3. 可选边距计算

通过 `SkIVector* margin` 参数，调用者可以选择是否需要知道模糊扩展量。当 `margin == nullptr` 时，跳过边距计算以提高性能。

### 4. CreateMode 灵活性

`BlurRect` 支持三种创建模式：
- `kJustComputeBounds`: 仅计算边界
- `kComputeBoundsAndRenderImage`: 同时计算边界并渲染
- 允许调用者先计算尺寸，再决定是否分配内存

### 5. 历史兼容性考虑

保留 `kBLUR_SIGMA_SCALE` 常数是为了与 CSS 规范和 Safari 的实现保持一致，即使从技术角度看该值并非最优。

## 性能考量

### 1. 算法复杂度

| 方法 | 时间复杂度 | 空间复杂度 |
|-----|----------|----------|
| BoxBlur | O(w×h) | O(w×h) |
| BlurRect | O(w×h) | O(w+h) |
| BlurGroundTruth | O(w×h×σ²) | O(w×h) |

其中 w, h 为遮罩尺寸，σ 为 sigma 值。

### 2. 优化技巧

**矩形模糊优化：**
- 利用可分离性，将二维卷积降为两次一维卷积
- 使用预计算的轮廓表，避免重复计算高斯积分

**盒式滤波器优化：**
- 三次盒式卷积在单次遍历中完成
- 使用整数运算代替浮点运算
- 支持 SIMD 优化（在 SkMaskBlurFilter 中）

**内存优化：**
- 原地处理（对于某些模糊样式）
- 延迟分配（通过 CreateMode 控制）
- 使用 `AutoTMalloc` 实现栈/堆混合分配

### 3. 性能陷阱

**小 Sigma 值：**盒式近似在 sigma < 2 时精度不足，应改用精确方法或跳过模糊。

**大 Sigma 值：**建议先降采样图像，模糊后再升采样，避免巨大的卷积核。

**格式支持：**仅支持 kBW/kA8/kARGB32/kLCD16 格式，其他格式会返回失败。

## 相关文件

| 文件 | 关系 | 说明 |
|-----|------|------|
| src/core/SkBlurMaskFilterImpl.h | 上层使用者 | 遮罩滤镜实现 |
| src/core/SkBlurEngine.h | 相关抽象 | 后端无关的模糊引擎 |
| src/core/SkMaskBlurFilter.h | 内部依赖 | 盒式模糊具体实现 |
| src/core/SkMask.h | 数据结构 | 遮罩定义 |
| include/core/SkBlurTypes.h | 枚举定义 | 模糊样式类型 |
| include/core/SkRRect.h | 几何类型 | 圆角矩形 |
