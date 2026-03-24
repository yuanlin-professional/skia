# SkImageFilters

> 源文件: `include/effects/SkImageFilters.h`

## 概述
SkImageFilters 提供了一组丰富的图像滤镜工厂函数,用于创建各种图像处理效果,包括模糊、颜色变换、光照、形态学操作、合成等。该模块是 Skia 图像处理系统的核心,支持构建复杂的滤镜链(DAG),实现高级视觉效果。所有滤镜接受可选的输入滤镜,nullptr 表示使用动态源图像。

## 架构位置
SkImageFilters 位于 Skia 的效果(effects)模块,是图像滤镜(SkImageFilter)子系统的工厂层。它为上层绘图 API 提供声明式的图像处理能力,底层由 GPU 或 CPU 光栅管道实现具体的图像操作,支持与 SkCanvas 的保存层(save layer)无缝集成。

## 核心概念

### 输入滤镜机制
所有接受 `sk_sp<SkImageFilter> input` 参数的函数:
- **nullptr**: 自动使用动态源图像
  - 在 SkCanvas::saveLayer() 中是层的内容
  - 在 SkImages::MakeWithFilter() 中是显式传入的 SkImage
- **非 nullptr**: 使用指定滤镜的输出作为输入

### 滤镜链(DAG)
滤镜可以组合成有向无环图(DAG):
```cpp
auto blur = SkImageFilters::Blur(5, 5, nullptr);
auto colorized = SkImageFilters::ColorFilter(colorFilter, blur);
auto offset = SkImageFilters::Offset(10, 10, colorized);
// 结果: offset(colorize(blur(source)))
```

## 主要类与结构体

### SkImageFilters::CropRect
便利类型,用于指定裁剪矩形。

**继承关系**: `public std::optional<SkRect>`

**构造函数**:
```cpp
CropRect();                                    // 空(无裁剪)
CropRect(const SkIRect& crop);                 // 从整数矩形
CropRect(const SkRect& crop);                  // 从浮点矩形
CropRect(const std::optional<SkRect>& crop);   // 从 optional
CropRect(const std::nullopt_t&);               // 空
CropRect(std::nullptr_t);                      // 向后兼容
CropRect(const SkIRect* optionalCrop);         // 指针形式
CropRect(const SkRect* optionalCrop);          // 指针形式
```

**说明**:
- 封装了多种输入形式,简化 API 使用
- 可以隐式转换,调用者无需关心内部类型
- 与旧版 API(使用 `const SkRect*`)向后兼容

## 公共 API 函数分类

### 1. 合成与混合滤镜

#### `Arithmetic()`
```cpp
static sk_sp<SkImageFilter> Arithmetic(SkScalar k1, SkScalar k2, SkScalar k3, SkScalar k4,
                                       bool enforcePMColor,
                                       sk_sp<SkImageFilter> background,
                                       sk_sp<SkImageFilter> foreground,
                                       const CropRect& cropRect = {});
```
- **功能**: 使用四系数公式混合前景和背景
- **公式**: `k1 * fg * bg + k2 * fg + k3 * bg + k4`
- **参数**:
  - `k1-k4`: 混合系数
  - `enforcePMColor`: 是否将 RGB 钳制到计算出的 alpha
  - `background/foreground`: 输入滤镜(nullptr = 源图像)
  - `cropRect`: 可选裁剪区域
- **用途**: 自定义混合模式,实现特殊的合成效果

#### `Blend()`
```cpp
static sk_sp<SkImageFilter> Blend(SkBlendMode mode,
                                  sk_sp<SkImageFilter> background,
                                  sk_sp<SkImageFilter> foreground = nullptr,
                                  const CropRect& cropRect = {});

static sk_sp<SkImageFilter> Blend(sk_sp<SkBlender> blender,
                                  sk_sp<SkImageFilter> background,
                                  sk_sp<SkImageFilter> foreground = nullptr,
                                  const CropRect& cropRect = {});
```
- **功能**: 使用混合模式或自定义 Blender 合成两个滤镜
- **参数**:
  - `mode/blender`: 混合模式或自定义混合器
  - `background`: 背景(Dst)
  - `foreground`: 前景(Src),默认 nullptr
- **用途**: 标准混合模式(src-over、multiply、screen 等)

#### `Merge()`
```cpp
static sk_sp<SkImageFilter> Merge(sk_sp<SkImageFilter>* const filters, int count,
                                  const CropRect& cropRect = {});

static sk_sp<SkImageFilter> Merge(sk_sp<SkImageFilter> first,
                                  sk_sp<SkImageFilter> second,
                                  const CropRect& cropRect = {});
```
- **功能**: 使用 src-over 模式依次绘制多个滤镜的结果
- **参数**:
  - `filters`: 输入滤镜数组
  - `count`: 数组长度
  - `first/second`: 双输入便利重载
- **用途**: 合并多个图层

### 2. 模糊与卷积滤镜

#### `Blur()`
```cpp
static sk_sp<SkImageFilter> Blur(SkScalar sigmaX, SkScalar sigmaY,
                                 SkTileMode tileMode,
                                 sk_sp<SkImageFilter> input,
                                 const CropRect& cropRect = {});

// 默认 decal 模式
static sk_sp<SkImageFilter> Blur(SkScalar sigmaX, SkScalar sigmaY,
                                 sk_sp<SkImageFilter> input,
                                 const CropRect& cropRect = {});
```
- **功能**: 高斯模糊滤镜
- **参数**:
  - `sigmaX/sigmaY`: X/Y 方向的高斯 sigma 值(模糊半径)
  - `tileMode`: 边界处理模式(注意:kMirror 尚未支持)
  - `input`: 输入滤镜
- **用途**: 模糊效果,景深,毛玻璃
- **性能**: 两遍可分离卷积,O(n) 复杂度

#### `MatrixConvolution()`
```cpp
static sk_sp<SkImageFilter> MatrixConvolution(const SkISize& kernelSize,
                                              const SkScalar kernel[],
                                              SkScalar gain,
                                              SkScalar bias,
                                              const SkIPoint& kernelOffset,
                                              SkTileMode tileMode,
                                              bool convolveAlpha,
                                              sk_sp<SkImageFilter> input,
                                              const CropRect& cropRect = {});
```
- **功能**: NxM 图像卷积滤镜
- **参数**:
  - `kernelSize`: 卷积核尺寸(N x M)
  - `kernel`: 卷积核数组(N*M 个元素,行优先)
  - `gain`: 卷积后的缩放因子(用于归一化)
  - `bias`: 卷积后的偏移量
  - `kernelOffset`: 卷积核中心偏移(如 3x3 核应为 {1,1})
  - `tileMode`: 边界处理模式
  - `convolveAlpha`: true = 所有通道卷积,false = 仅 RGB
- **用途**: 锐化、边缘检测、浮雕等
- **示例核**:
  ```cpp
  // 锐化
  SkScalar sharpen[] = { 0, -1,  0,
                        -1,  5, -1,
                         0, -1,  0 };
  ```

### 3. 颜色处理滤镜

#### `ColorFilter()`
```cpp
static sk_sp<SkImageFilter> ColorFilter(sk_sp<SkColorFilter> cf,
                                        sk_sp<SkImageFilter> input,
                                        const CropRect& cropRect = {});
```
- **功能**: 应用颜色滤镜(色彩变换)
- **参数**:
  - `cf`: SkColorFilter 对象(如色彩矩阵、颜色查找表等)
  - `input`: 输入滤镜
- **用途**: 色调调整、灰度化、色彩校正

### 4. 阴影滤镜

#### `DropShadow()`
```cpp
static sk_sp<SkImageFilter> DropShadow(SkScalar dx, SkScalar dy,
                                       SkScalar sigmaX, SkScalar sigmaY,
                                       SkColor4f color,
                                       sk_sp<SkColorSpace> colorSpace,
                                       sk_sp<SkImageFilter> input,
                                       const CropRect& cropRect = {});

// SkColor 便利重载
static sk_sp<SkImageFilter> DropShadow(SkScalar dx, SkScalar dy,
                                       SkScalar sigmaX, SkScalar sigmaY,
                                       SkColor color,
                                       sk_sp<SkImageFilter> input,
                                       const CropRect& cropRect = {});
```
- **功能**: 在输入内容下方绘制阴影(包含原内容)
- **参数**:
  - `dx/dy`: 阴影偏移
  - `sigmaX/sigmaY`: 阴影模糊
  - `color`: 阴影颜色
  - `colorSpace`: 颜色空间(nullptr = 默认)
- **用途**: UI 元素阴影,文本阴影

#### `DropShadowOnly()`
```cpp
static sk_sp<SkImageFilter> DropShadowOnly(SkScalar dx, SkScalar dy,
                                           SkScalar sigmaX, SkScalar sigmaY,
                                           SkColor4f color,
                                           sk_sp<SkColorSpace>,
                                           sk_sp<SkImageFilter> input,
                                           const CropRect& cropRect = {});
```
- **功能**: 仅渲染阴影,不包含原内容
- **用途**: 需要独立控制阴影和内容的合成

### 5. 几何变换滤镜

#### `Offset()`
```cpp
static sk_sp<SkImageFilter> Offset(SkScalar dx, SkScalar dy,
                                   sk_sp<SkImageFilter> input,
                                   const CropRect& cropRect = {});
```
- **功能**: 平移输入图像
- **参数**: `dx/dy` - 偏移量
- **用途**: 图层定位,简单动画

#### `MatrixTransform()`
```cpp
static sk_sp<SkImageFilter> MatrixTransform(const SkMatrix& matrix,
                                            const SkSamplingOptions& sampling,
                                            sk_sp<SkImageFilter> input);
```
- **功能**: 对输入应用矩阵变换(在局部空间)
- **参数**:
  - `matrix`: 变换矩阵(缩放、旋转、倾斜等)
  - `sampling`: 采样选项(滤波质量)
- **用途**: 缩放、旋转、透视变换

#### `Crop()`
```cpp
static sk_sp<SkImageFilter> Crop(const SkRect& rect,
                                 SkTileMode tileMode,
                                 sk_sp<SkImageFilter> input);

static sk_sp<SkImageFilter> Crop(const SkRect& rect,
                                 sk_sp<SkImageFilter> input);  // 默认 decal
```
- **功能**: 裁剪输入到指定矩形
- **参数**:
  - `rect`: 裁剪矩形
  - `tileMode`: 矩形外的平铺模式
- **说明**: 其他滤镜的 CropRect 参数等价于 `::Crop(rect, kDecal, filter)`

### 6. 位移与扭曲滤镜

#### `DisplacementMap()`
```cpp
static sk_sp<SkImageFilter> DisplacementMap(SkColorChannel xChannelSelector,
                                            SkColorChannel yChannelSelector,
                                            SkScalar scale,
                                            sk_sp<SkImageFilter> displacement,
                                            sk_sp<SkImageFilter> color,
                                            const CropRect& cropRect = {});
```
- **功能**: 使用位移图扭曲图像
- **参数**:
  - `xChannelSelector/yChannelSelector`: 位移图的哪个通道编码 x/y 位移(R/G/B/A)
  - `scale`: 位移缩放因子
  - `displacement`: 位移图滤镜
  - `color`: 被位移的颜色图像
- **公式**: `newPos = oldPos + scale * (displacement[channel], displacement[channel])`
- **用途**: 水波纹、热浪、玻璃扭曲效果

#### `Magnifier()`
```cpp
static sk_sp<SkImageFilter> Magnifier(const SkRect& lensBounds,
                                      SkScalar zoomAmount,
                                      SkScalar inset,
                                      const SkSamplingOptions& sampling,
                                      sk_sp<SkImageFilter> input,
                                      const CropRect& cropRect = {});
```
- **功能**: 放大镜效果
- **参数**:
  - `lensBounds`: 放大镜外边界
  - `zoomAmount`: 放大倍数
  - `inset`: 鱼眼扭曲区域的宽度
  - `sampling`: 采样选项
- **用途**: 局部放大,鱼眼透镜效果

### 7. 形态学滤镜

#### `Dilate()`
```cpp
static sk_sp<SkImageFilter> Dilate(SkScalar radiusX, SkScalar radiusY,
                                   sk_sp<SkImageFilter> input,
                                   const CropRect& cropRect = {});
```
- **功能**: 膨胀滤镜(最大值滤波)
- **参数**: `radiusX/radiusY` - X/Y 方向的膨胀半径
- **用途**: 加粗边缘,填充小孔

#### `Erode()`
```cpp
static sk_sp<SkImageFilter> Erode(SkScalar radiusX, SkScalar radiusY,
                                  sk_sp<SkImageFilter> input,
                                  const CropRect& cropRect = {});
```
- **功能**: 腐蚀滤镜(最小值滤波)
- **参数**: `radiusX/radiusY` - X/Y 方向的腐蚀半径
- **用途**: 细化边缘,移除小噪点

### 8. 光照滤镜

#### 漫反射光照

##### `DistantLitDiffuse()`
```cpp
static sk_sp<SkImageFilter> DistantLitDiffuse(const SkPoint3& direction,
                                              SkColor lightColor,
                                              SkScalar surfaceScale,
                                              SkScalar kd,
                                              sk_sp<SkImageFilter> input,
                                              const CropRect& cropRect = {});
```
- **功能**: 远光源漫反射照明
- **参数**:
  - `direction`: 光源方向(3D 向量)
  - `lightColor`: 光源颜色
  - `surfaceScale`: alpha 值到物理高度的缩放系数
  - `kd`: 漫反射系数
- **说明**: 将输入的 alpha 通道解释为高度图,计算漫反射

##### `PointLitDiffuse()`
```cpp
static sk_sp<SkImageFilter> PointLitDiffuse(const SkPoint3& location,
                                            SkColor lightColor,
                                            SkScalar surfaceScale,
                                            SkScalar kd,
                                            sk_sp<SkImageFilter> input,
                                            const CropRect& cropRect = {});
```
- **功能**: 点光源漫反射照明
- **参数**: `location` - 光源位置(3D 坐标)

##### `SpotLitDiffuse()`
```cpp
static sk_sp<SkImageFilter> SpotLitDiffuse(const SkPoint3& location,
                                           const SkPoint3& target,
                                           SkScalar falloffExponent,
                                           SkScalar cutoffAngle,
                                           SkColor lightColor,
                                           SkScalar surfaceScale,
                                           SkScalar kd,
                                           sk_sp<SkImageFilter> input,
                                           const CropRect& cropRect = {});
```
- **功能**: 聚光灯漫反射照明
- **参数**:
  - `location`: 聚光灯位置
  - `target`: 聚光灯指向目标
  - `falloffExponent`: 截止角外的衰减指数
  - `cutoffAngle`: 全光照的最大角度

#### 镜面反射光照

##### `DistantLitSpecular()` / `PointLitSpecular()` / `SpotLitSpecular()`
```cpp
// 与漫反射类似,但额外参数:
// ks: 镜面反射系数
// shininess: 镜面光泽度指数
```
- **功能**: 镜面高光照明(三种光源类型)
- **用途**: 创建金属质感、高光效果

### 9. 源图像滤镜

#### `Image()`
```cpp
static sk_sp<SkImageFilter> Image(sk_sp<SkImage> image,
                                  const SkRect& srcRect,
                                  const SkRect& dstRect,
                                  const SkSamplingOptions& sampling);

static sk_sp<SkImageFilter> Image(sk_sp<SkImage> image,
                                  const SkSamplingOptions& sampling);
```
- **功能**: 将 SkImage 作为滤镜输出(叶子节点)
- **参数**:
  - `image`: 源图像(null 时返回透明黑色)
  - `srcRect/dstRect`: 采样和绘制区域
  - `sampling`: 采样选项
- **用途**: 在滤镜链中引入外部图像

#### `Picture()`
```cpp
static sk_sp<SkImageFilter> Picture(sk_sp<SkPicture> pic,
                                    const SkRect& targetRect);

static sk_sp<SkImageFilter> Picture(sk_sp<SkPicture> pic);  // 使用 cullRect
```
- **功能**: 将 SkPicture 作为滤镜输出
- **参数**:
  - `pic`: SkPicture 对象(null 时返回透明黑色)
  - `targetRect`: 绘制区域(默认使用 picture 的 cullRect)
- **用途**: 将矢量绘图作为滤镜输入

#### `Shader()`
```cpp
static sk_sp<SkImageFilter> Shader(sk_sp<SkShader> shader,
                                   const CropRect& cropRect = {});

enum class Dither : bool { kNo = false, kYes = true };
static sk_sp<SkImageFilter> Shader(sk_sp<SkShader> shader,
                                   Dither dither,
                                   const CropRect& cropRect = {});
```
- **功能**: 将 Shader 作为滤镜输出
- **参数**:
  - `shader`: SkShader 对象(null 时返回透明黑色)
  - `dither`: 是否抖动
- **用途**: 使用渐变、图案等填充滤镜区域
- **说明**: 叶子节点,通常与其他滤镜组合使用

### 10. 特殊效果滤镜

#### `Tile()`
```cpp
static sk_sp<SkImageFilter> Tile(const SkRect& src,
                                 const SkRect& dst,
                                 sk_sp<SkImageFilter> input);
```
- **功能**: 平铺输入图像
- **参数**:
  - `src`: 源矩形(定义平铺单元)
  - `dst`: 目标矩形(定义平铺区域)
- **用途**: 创建重复图案,无缝纹理

#### `Empty()`
```cpp
static sk_sp<SkImageFilter> Empty();
```
- **功能**: 返回始终输出透明黑色的滤镜
- **用途**: 作为占位符,或有意清空某些输入

#### `Compose()`
```cpp
static sk_sp<SkImageFilter> Compose(sk_sp<SkImageFilter> outer,
                                    sk_sp<SkImageFilter> inner);
```
- **功能**: 组合两个滤镜,`result = outer(inner(source))`
- **说明**: 显式组合语义,等价于 `outer` 以 `inner` 作为输入

### 11. Runtime Shader 滤镜

#### `RuntimeShader()` - 单输入版本
```cpp
static sk_sp<SkImageFilter> RuntimeShader(const SkRuntimeEffectBuilder& builder,
                                          std::string_view childShaderName,
                                          sk_sp<SkImageFilter> input);

static sk_sp<SkImageFilter> RuntimeShader(const SkRuntimeEffectBuilder& builder,
                                          SkScalar sampleRadius,
                                          std::string_view childShaderName,
                                          sk_sp<SkImageFilter> input);
```
- **功能**: 使用 SkSL 自定义 shader 作为滤镜
- **参数**:
  - `builder`: SkRuntimeEffectBuilder 对象(包含 SkSL 代码和 uniform)
  - `childShaderName`: 绑定到输入的子 shader 名称(空字符串则自动绑定唯一的子 shader)
  - `sampleRadius`: 采样半径(定义 child.eval() 的最大偏移)
  - `input`: 输入滤镜
- **要求**: 需要 GPU 后端或 SkSL 支持
- **用途**: 自定义图像处理算法

#### `RuntimeShader()` - 多输入版本
```cpp
static sk_sp<SkImageFilter> RuntimeShader(const SkRuntimeEffectBuilder& builder,
                                          std::string_view childShaderNames[],
                                          const sk_sp<SkImageFilter> inputs[],
                                          int inputCount);

static sk_sp<SkImageFilter> RuntimeShader(const SkRuntimeEffectBuilder& builder,
                                          SkScalar maxSampleRadius,
                                          std::string_view childShaderNames[],
                                          const sk_sp<SkImageFilter> inputs[],
                                          int inputCount);
```
- **功能**: 支持多个输入的自定义 shader 滤镜
- **参数**:
  - `childShaderNames`: 子 shader 名称数组
  - `inputs`: 输入滤镜数组
  - `inputCount`: 输入数量
  - `maxSampleRadius`: 所有子 shader 的最大采样半径
- **验证**: 如果名称重复或为 null,返回 nullptr

## 内部实现细节

### 滤镜 DAG 构建
滤镜通过智能指针(sk_sp)连接,形成有向无环图:
- 每个滤镜节点持有输入滤镜的引用
- 叶子节点(Image、Picture、Shader、Empty)无输入
- 内部节点处理一个或多个输入

### 边界计算
每个滤镜都实现边界计算逻辑:
- **输入边界映射**: 确定需要多大的输入区域
- **输出边界扩展**: 计算输出可能影响的区域
- **CropRect**: 限制输出边界,优化性能

### GPU 加速
大多数滤镜在 GPU 后端高度优化:
- 通过 fragment shader 实现
- 利用纹理采样硬件
- 支持滤镜链的内联优化

### 光栅回退
某些复杂滤镜(如 RuntimeShader)可能在某些平台上回退到 CPU 实现。

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/core/SkColor.h | 颜色类型 |
| include/core/SkColorSpace.h | 颜色空间管理 |
| include/core/SkImage.h | 图像对象 |
| include/core/SkImageFilter.h | 滤镜基类 |
| include/core/SkPicture.h | 矢量绘图记录 |
| include/core/SkShader.h | Shader 对象 |
| include/core/SkTileMode.h | 平铺模式 |
| include/core/SkBlendMode.h | 混合模式枚举 |

### 被依赖的模块
| 模块 | 用途 |
|------|------|
| include/core/SkPaint.h | 通过 setImageFilter 应用滤镜 |
| include/core/SkCanvas.h | saveLayer 使用滤镜 |
| include/core/SkImage.h | SkImages::MakeWithFilter |
| 应用层代码 | UI 效果、图像编辑 |

## 设计模式与设计决策

### 工厂模式
所有创建函数都是静态工厂方法,返回 sk_sp<SkImageFilter>,隐藏具体实现类。

### 组合模式
滤镜通过输入参数组合,形成树状或 DAG 结构,支持复杂效果的声明式构建。

### 不可变对象
滤镜对象创建后不可变,确保线程安全和可缓存性。

### 延迟计算
滤镜仅定义操作,实际计算在绘制时进行,支持优化和剪枝。

## 性能考量

### 滤镜链优化
- **内联**: 简单滤镜可能被内联到父滤镜的 shader
- **边界剪枝**: 不在视口内的滤镜节点被跳过
- **缓存**: 中间结果可能被缓存(取决于后端)

### GPU vs CPU
| 滤镜类型 | GPU 性能 | CPU 性能 |
|----------|----------|----------|
| Blur | 优秀 | 好 |
| ColorFilter | 优秀 | 优秀 |
| MatrixConvolution | 好 | 慢 |
| Lighting | 优秀 | 慢 |
| RuntimeShader | 优秀(如果简单) | 不支持 |

### 内存考虑
- 大 sigma 的模糊可能需要大量中间缓冲区
- 复杂滤镜链可能导致多次纹理传递
- CropRect 可以显著减少内存使用

## 使用场景与示例

### 基础模糊
```cpp
auto blur = SkImageFilters::Blur(5.0f, 5.0f, nullptr);
paint.setImageFilter(blur);
```

### 投影效果
```cpp
auto shadow = SkImageFilters::DropShadow(4, 4, 3, 3,
                                         SkColorSetARGB(128, 0, 0, 0),
                                         nullptr);
```

### 发光效果
```cpp
auto dilate = SkImageFilters::Dilate(2, 2, nullptr);
auto blur = SkImageFilters::Blur(4, 4, dilate);
auto glow = SkImageFilters::Merge(blur, nullptr);  // 原图在上
```

### 复杂组合
```cpp
auto blur = SkImageFilters::Blur(3, 3, nullptr);
auto colorMatrix = SkColorFilters::Matrix(...);
auto colored = SkImageFilters::ColorFilter(colorMatrix, blur);
auto offset = SkImageFilters::Offset(10, 10, colored);
```

## 平台相关说明

### GPU 后端要求
某些滤镜(RuntimeShader、复杂光照)需要:
- GPU 后端启用(Ganesh 或 Graphite)
- Shader 编译支持
- 足够的纹理单元

### 移动平台
在移动设备上:
- 避免过大的模糊半径(内存和带宽限制)
- 优先使用简单滤镜组合而非单个复杂滤镜
- 注意功耗(GPU 滤镜可能更耗电)

## 相关文件
| 文件 | 关系 |
|------|------|
| include/core/SkImageFilter.h | 滤镜基类定义 |
| src/effects/imagefilters/ | 各滤镜的实现 |
| include/core/SkPaint.h | 通过 setImageFilter 应用 |
| include/core/SkCanvas.h | saveLayer 集成 |
| include/effects/SkRuntimeEffect.h | RuntimeShader 的 SkSL 支持 |
| src/gpu/ganesh/effects/ | GPU 实现 |
