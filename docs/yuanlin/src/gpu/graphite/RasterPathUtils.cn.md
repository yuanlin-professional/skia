# RasterPathUtils

> 源文件
> - src/gpu/graphite/RasterPathUtils.h
> - src/gpu/graphite/RasterPathUtils.cpp

## 概述

`RasterPathUtils` 是 Graphite 渲染引擎中用于软件光栅化路径和裁剪掩码的工具模块。该模块提供了 `RasterMaskHelper` 类和多个键生成函数，用于在 CPU 端生成 Alpha 掩码纹理，这些掩码随后可以在 GPU 上用于复杂路径的渲染和裁剪操作。

核心功能包括：
1. **软件光栅化**：使用 Skia 的 CPU 光栅化器（`SkDraw`）将路径和形状渲染为 A8 格式的掩码
2. **掩码缓存键生成**：为路径掩码和裁剪掩码生成唯一键，支持缓存复用
3. **灵活的存储管理**：支持自动分配或使用调用者提供的存储空间

该模块在处理复杂路径（如自由形状、高级混合模式、反向填充等）时特别有用，通过软件光栅化生成掩码后在 GPU 上应用，避免了完全在 GPU 上处理复杂路径的困难。

## 架构位置

`RasterPathUtils` 位于 Graphite 渲染管线的路径处理子系统中：

```
skgpu::graphite 命名空间
├── RasterPathAtlas (光栅路径图集 - 使用 RasterMaskHelper)
│   └── RasterMaskHelper (掩码辅助类 - 执行实际光栅化)
├── Shape (形状抽象 - 被光栅化的对象)
├── Transform (变换 - 定义形状的空间位置)
├── ClipStack (裁剪栈 - 使用 GenerateClipMaskKey)
└── 缓存系统 (使用 UniqueKey 缓存掩码纹理)
```

该模块连接了 CPU 端的光栅化能力和 GPU 端的纹理缓存系统，是混合 CPU-GPU 渲染策略的关键组件。

## 主要类与结构体

### RasterMaskHelper 类

```cpp
class RasterMaskHelper : SkNoncopyable {
public:
    static std::tuple<SkBitmap, RasterMaskHelper> Allocate(
        SkISize size,
        SkIVector translation = {0, 0},
        int padding = 0,
        SkAlpha initialAlpha = 0);

    explicit RasterMaskHelper(SkPixmap pixmap, SkIVector translation = {0, 0});

    void drawShape(const Shape& shape,
                   const Transform& localToDevice,
                   const SkStrokeRec& strokeRec);

    void drawClip(const Shape& shape, const Transform& localToDevice, uint8_t alpha);

private:
    SkPixmap     fPixels;        // 目标像素存储
    SkRasterClip fRasterClip;    // 光栅化裁剪区域
    SkVector     fTranslate;     // 绘制时的额外平移
};
```

**核心职责：**
- 管理 A8 格式的掩码位图
- 使用 Skia 的软件光栅化器绘制形状
- 支持路径掩码和裁剪掩码的不同绘制模式

**设计特点：**
- 不可拷贝（继承自 `SkNoncopyable`）
- 支持自动分配或外部提供存储
- 可选的填充（padding）和初始化 alpha 值

### 键生成函数

```cpp
skgpu::UniqueKey GeneratePathMaskKey(const Shape& shape,
                                     const Transform& transform,
                                     const SkStrokeRec& strokeRec,
                                     skvx::half2 maskOrigin,
                                     skvx::half2 maskSize);

skgpu::UniqueKey GenerateClipMaskKey(uint32_t stackRecordID,
                                     const ClipStack::ElementList* elementsForMask,
                                     SkIRect maskDeviceBounds,
                                     bool includeBounds,
                                     SkIRect* keyBounds,
                                     bool* usesPathKey);
```

这些函数生成缓存系统使用的唯一键，确保相同的路径配置能够复用已缓存的掩码纹理。

## 公共 API 函数

### RasterMaskHelper::Allocate (静态工厂方法)

```cpp
static std::tuple<SkBitmap, RasterMaskHelper> Allocate(
    SkISize size,
    SkIVector translation = {0, 0},
    int padding = 0,
    SkAlpha initialAlpha = 0);
```

**功能：**创建一个新的位图和对应的 `RasterMaskHelper` 实例。

**参数说明：**
- `size`: 实际可绘制区域的尺寸（不包括填充）
- `translation`: 应用于每次绘制的额外平移
- `padding`: 四边添加的填充像素数，填充区域不会被渲染
- `initialAlpha`: 整个位图的初始 alpha 值（包括填充区域）

**返回值：**返回一个元组，包含分配的位图和配置好的辅助类实例。

**实现细节：**
```cpp
SkISize paddedSize{size.width() + 2 * padding, size.height() + 2 * padding};
SkBitmap bitmap;
bitmap.allocPixels(SkImageInfo::MakeA8(paddedSize));
memset(bitmap.getAddr(0, 0), initialAlpha, bitmap.computeByteSize());

const SkPixmap outerPM = bitmap.pixmap();
SkPixmap innerPM;
SkAssertResult(outerPM.extractSubset(&innerPM,
    SkIRect::MakePtSize({padding, padding}, size)));

return std::make_tuple(std::move(bitmap), RasterMaskHelper{innerPM, translation});
```

分配带填充的位图，但 helper 仅操作内部子集，坐标 (0,0) 对应填充内的第一个像素。

### RasterMaskHelper 构造函数

```cpp
explicit RasterMaskHelper(SkPixmap pixmap, SkIVector translation = {0, 0});
```

**功能：**使用调用者提供的 `SkPixmap` 创建 helper 实例。

**前提条件：**
- `pixmap` 必须是 `kAlpha_8_SkColorType` 格式
- `pixmap` 不能为空
- `pixmap` 必须有有效的地址

### drawShape

```cpp
void drawShape(const Shape& shape,
               const Transform& localToDevice,
               const SkStrokeRec& strokeRec);
```

**功能：**将形状光栅化到掩码位图中，用于路径掩码。

**行为特点：**
- 使用 `SkBlendMode::kSrc` 模式，直接替换目标像素
- 启用抗锯齿
- 使用白色（alpha = 1.0）绘制
- 应用 `strokeRec` 定义的描边样式
- 反向填充类型会被重置（由着色器处理反转）

**实现逻辑：**
```cpp
SkPaint paint;
paint.setBlendMode(SkBlendMode::kSrc);
paint.setAntiAlias(true);
paint.setColor(SK_ColorWHITE);
strokeRec.applyToPaint(&paint);

SkMatrix translatedMatrix = SkMatrix(localToDevice);
translatedMatrix.postTranslate(fTranslate.fX, fTranslate.fY);

SkPath path = shape.asPath();
if (path.isInverseFillType()) {
    path.toggleInverseFillType();  // 着色器会处理反转
}
make_draw(fPixels, fRasterClip, translatedMatrix).drawPathCoverage(path, paint);
```

### drawClip

```cpp
void drawClip(const Shape& shape, const Transform& localToDevice, uint8_t alpha);
```

**功能：**将形状光栅化到掩码位图中，用于裁剪掩码。

**与 drawShape 的区别：**
- 接受自定义的 alpha 值（支持部分透明裁剪）
- **不重置反向填充类型**（因为可能合并多个路径到一个掩码）
- 根据 alpha 值选择不同的绘制方法：
  - `alpha == 0xFF`: 使用 `drawPathCoverage`（更快）
  - `alpha < 0xFF`: 使用 `drawPath`（支持半透明）

**实现逻辑：**
```cpp
paint.setColor(SkColorSetARGB(alpha, 0xFF, 0xFF, 0xFF));
SkPath path = shape.asPath();
skcpu::Draw draw = make_draw(fPixels, fRasterClip, translatedMatrix);

if (0xFF == alpha) {
    draw.drawPathCoverage(path, paint);
} else {
    draw.drawPath(path, paint, nullptr);
}
```

### GeneratePathMaskKey

```cpp
skgpu::UniqueKey GeneratePathMaskKey(const Shape& shape,
                                     const Transform& transform,
                                     const SkStrokeRec& strokeRec,
                                     skvx::half2 maskOrigin,
                                     skvx::half2 maskSize);
```

**功能：**为路径掩码生成缓存键，考虑形状、变换、描边样式和掩码尺寸。

**键组成部分：**
1. **掩码几何信息**（2 个 uint32）：
   - `builder[0]`: `maskOrigin.x | (maskOrigin.y << 16)`
   - `builder[1]`: `maskSize.x | (maskSize.y << 16)`

2. **变换信息**（4 个 uint32）：
   - 缩放因子 sx, sy
   - 倾斜因子 kx, ky
   - 亚像素平移的小数部分（8 位精度）

3. **描边样式信息**（2-4 个 uint32）：
   - 填充样式：`styleBits`（样式类型 + 端点样式）
   - 描边样式：额外包括连接样式、宽度和斜接限制

4. **形状键**：调用 `shape.keySize()` 和 `shape.writeKey()`

**Android 特殊处理：**
```cpp
#ifdef SK_BUILD_FOR_ANDROID_FRAMEWORK
    SkFixed fracX = 0;
    SkFixed fracY = 0;
#else
    SkScalar tx = mat.get(SkMatrix::kMTransX);
    SkScalar ty = mat.get(SkMatrix::kMTransY);
    SkFixed fracX = SkScalarToFixed(SkScalarFraction(tx)) & 0x0000FF00;
    SkFixed fracY = SkScalarToFixed(SkScalarFraction(ty)) & 0x0000FF00;
#endif
```

Android 框架忽略小数平移以提高缓存命中率，匹配 HWUI 行为。

### GenerateClipMaskKey

```cpp
skgpu::UniqueKey GenerateClipMaskKey(uint32_t stackRecordID,
                                     const ClipStack::ElementList* elementsForMask,
                                     SkIRect maskDeviceBounds,
                                     bool includeBounds,
                                     SkIRect* keyBounds,
                                     bool* usesPathKey);
```

**功能：**为裁剪掩码生成缓存键，支持多元素裁剪栈。

**两种键生成策略：**

**1. 路径键（Path Key）模式**：
- 条件：元素数量 ≤ 2 且所有形状都能生成键
- 为每个元素编码：
  - 变换矩阵（5 个 uint32）
  - 裁剪操作类型（包含在 fracBits 中）
  - 形状键
- 可选地包含 `keyBounds`（2 个 uint32）

**keyBounds 的作用：**
```cpp
*keyBounds = maskDeviceBounds.makeOffset(-unclippedBounds.left(),
                                         -unclippedBounds.top());
```

`keyBounds` 是相对于完整变换掩码的 `maskDeviceBounds`，确保捕获由整数平移导致的不同掩码区域（整数平移不在键中体现）。

**2. 记录 ID（Record ID）模式**：
- 条件：元素过多（> 2）或某个形状无法生成键
- 仅使用 `stackRecordID`（1 个 uint32）
- 更简单但缓存复用性较差

**输出参数：**
- `keyBounds`: 相对边界矩形
- `usesPathKey`: 标识使用了哪种键生成策略

## 内部实现细节

### make_draw 辅助函数

```cpp
skcpu::Draw make_draw(const SkPixmap& pm, const SkRasterClip& rc, const SkMatrix& m) {
    skcpu::Draw draw;
    draw.fDst = pm;
    draw.fBlitterChooser = SkA8Blitter_Choose;  // 使用 A8 专用 blitter
    draw.fCTM = &m;
    draw.fRC = &rc;
    return draw;
}
```

创建 `skcpu::Draw` 对象，配置为 A8 掩码渲染：
- `SkA8Blitter_Choose`: 针对 Alpha 通道优化的 blitter 选择器
- 绑定目标像素图、裁剪区域和变换矩阵

### add_transform_key 辅助函数

```cpp
uint32_t add_transform_key(skgpu::UniqueKey::Builder* builder,
                           int startIndex,
                           const Transform& transform);
```

**功能：**将变换矩阵的关键部分添加到键构建器中。

**编码内容：**
1. 缩放和倾斜：`[sx, sy, kx, ky]` 的浮点位表示
2. 亚像素平移：小数部分的 8 位精度

**返回值：**打包的小数位信息（`fracX | (fracY >> 8)`），调用者可将其与样式位组合。

**亚像素精度处理：**
```cpp
SkFixed fracX = SkScalarToFixed(SkScalarFraction(tx)) & 0x0000FF00;
SkFixed fracY = SkScalarToFixed(SkScalarFraction(ty)) & 0x0000FF00;
uint32_t fracBits = fracX | (fracY >> 8);
```

每个方向保留 8 位小数精度，足以区分亚像素定位的不同情况。

### 变换矩阵缓存策略

只要求矩阵的左上 2×2 部分精确匹配，但平移可以有 8 位亚像素容差：
- **精确匹配**：sx, sy, kx, ky（影响形状几何）
- **亚像素容差**：tx, ty 的小数部分（影响抗锯齿边界）
- **忽略整数平移**：通过 `maskOrigin`/`keyBounds` 间接编码

这种策略在保证正确性的同时提高了缓存命中率。

### 描边样式编码

```cpp
uint32_t styleBits = strokeRec.getStyle();
if (!strokeRec.isFillStyle()) {
    styleBits |= (strokeRec.getCap() << 2);
}
if (!strokeRec.isHairlineStyle() && !strokeRec.isFillStyle()) {
    styleBits |= (strokeRec.getJoin() << 4);
    builder[6] = SkFloat2Bits(strokeRec.getWidth());
    builder[7] = SkFloat2Bits(strokeRec.getMiter());
}
```

**位布局：**
- 位 0-1：描边样式（填充、描边、填充+描边、细线）
- 位 2-3：端点样式（仅非填充）
- 位 4-5：连接样式（仅描边和填充+描边）
- 额外数据：描边宽度和斜接限制

静态断言确保枚举值范围适配位布局：
```cpp
static_assert(SkStrokeRec::kStyleCount <= (1 << 2));
static_assert(SkPaint::kCapCount <= (1 << 2));
static_assert(SkPaint::kJoinCount <= (1 << 2));
```

## 依赖关系

### 直接依赖

| 依赖项 | 类型 | 用途 |
|-------|------|------|
| `SkBitmap` | Skia 核心类 | 掩码位图存储 |
| `SkPixmap` | Skia 核心类 | 像素数据访问 |
| `skcpu::Draw` | Skia 光栅化 | 执行 CPU 端绘制 |
| `SkRasterClip` | Skia 光栅化 | 定义光栅裁剪区域 |
| `SkA8Blitter_Choose` | Skia blitter | A8 格式专用混合器 |
| `Shape` | Graphite 几何 | 被光栅化的形状抽象 |
| `Transform` | Graphite 几何 | 形状的空间变换 |
| `SkStrokeRec` | Skia 绘图 | 描边样式信息 |
| `UniqueKey` | GPU 资源键 | 缓存系统键 |
| `ClipStack` | Graphite 裁剪 | 裁剪元素列表 |

### 被依赖关系

- `RasterPathAtlas`: 使用 `RasterMaskHelper` 生成路径掩码纹理
- `ClipStack`: 使用 `GenerateClipMaskKey` 缓存裁剪掩码
- 各种着色器和渲染器：使用生成的掩码纹理进行绘制

## 设计模式与设计决策

### 1. 工厂方法模式（Factory Method）

```cpp
static std::tuple<SkBitmap, RasterMaskHelper> Allocate(...);
```

**设计决策：**
- 返回位图和 helper 的元组，确保调用者持有位图所有权
- 位图必须保持存活，因为 helper 仅持有 `SkPixmap`（非拥有引用）
- 分离"内部子集"（helper 操作区域）和"外部完整位图"（包含填充）

### 2. 策略模式（Strategy Pattern）

两个键生成函数实现了不同的键生成策略：
- **路径键策略**：详细编码所有路径信息，缓存精度高
- **记录 ID 策略**：使用栈记录 ID，简单但缓存复用性低

选择策略基于：
- 元素数量（≤ 2 个元素）
- 形状是否支持键生成

### 3. 适配器模式（Adapter Pattern）

`RasterMaskHelper` 适配了 Skia 的 CPU 光栅化系统（`skcpu::Draw`）到 Graphite 的渲染管线：
- 输入：Graphite 的 `Shape` 和 `Transform`
- 输出：A8 掩码纹理（可上传到 GPU）
- 转换：调用 `shape.asPath()` 并配置 `skcpu::Draw`

### 4. 模板参数优化

填充（padding）的设计允许：
- 避免边界伪影：周围的填充可以防止纹理采样时的边缘问题
- 灵活的坐标系统：(0,0) 始终是可绘制区域的左上角
- 高效的内存布局：连续分配但逻辑分离

### 5. 平台特定优化

```cpp
#ifdef SK_BUILD_FOR_ANDROID_FRAMEWORK
    SkFixed fracX = 0;
    SkFixed fracY = 0;
#else
    // 标准平台保留亚像素精度
#endif
```

**设计权衡：**
- Android：更高的缓存命中率，匹配系统 UI 框架行为
- 其他平台：更精确的渲染，避免亚像素对齐问题

## 性能考量

### 1. 掩码缓存键的设计

**优化目标：**
- 尽可能高的缓存命中率
- 避免不必要的重新光栅化

**关键策略：**
- 只编码影响渲染结果的属性
- 整数平移不编码在键中（通过 `maskOrigin`/`keyBounds` 处理）
- 亚像素平移仅保留 8 位精度（256 个子位置）

### 2. 裁剪掩码键的限制

```cpp
static constexpr int kMaxShapeCountForKey = 2;
```

**设计决策：**
- 限制路径键模式为最多 2 个元素
- 避免键过大导致的内存和计算开销
- 超过限制时降级为简单的记录 ID 键

**权衡：**
- 简单裁剪（≤ 2 元素）：高缓存复用性
- 复杂裁剪（> 2 元素）：依赖栈记录唯一性，缓存效果受限

### 3. CPU 光栅化的开销

**何时使用软件光栅化：**
- 复杂路径（GPU 难以直接渲染）
- 反向填充
- 需要精确抗锯齿的形状

**性能考虑：**
- A8 格式：每像素 1 字节，内存和带宽效率高
- `SkA8Blitter_Choose`：针对 Alpha 通道优化的 blitter
- `drawPathCoverage` vs `drawPath`：前者更快但仅适用于不透明绘制

### 4. 亚像素定位的精度

8 位小数精度意味着：
- 每个像素单位内有 256 个子位置
- 对于屏幕空间，这通常是过剩的（1/256 像素）
- 但避免了浮点精度问题导致的缓存未命中

### 5. 内存布局

```cpp
SkISize paddedSize{size.width() + 2 * padding, size.height() + 2 * padding};
bitmap.allocPixels(SkImageInfo::MakeA8(paddedSize));
```

**填充的性能影响：**
- 额外内存：`4 * padding * (size.width + size.height) + 4 * padding^2` 字节
- 避免边界检查：光栅化器可以安全地在填充区域周围操作
- 纹理采样安全：GPU 采样时不会读取到未初始化的内存

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/graphite/RasterPathAtlas.h` | 使用方 | 使用 RasterMaskHelper 填充图集 |
| `src/gpu/graphite/geom/Shape.h` | 依赖 | 被光栅化的形状抽象 |
| `src/gpu/graphite/geom/Transform.h` | 依赖 | 形状的空间变换 |
| `src/gpu/graphite/ClipStack.h` | 依赖 | 裁剪元素列表 |
| `src/core/SkDraw.h` | 依赖 | CPU 光栅化核心 |
| `src/core/SkBlitter_A8.h` | 依赖 | A8 格式专用 blitter |
| `src/core/SkRasterClip.h` | 依赖 | 光栅裁剪区域 |
| `src/gpu/ResourceKey.h` | 依赖 | UniqueKey 定义 |
| `include/core/SkBitmap.h` | 依赖 | 位图存储 |
| `include/core/SkStrokeRec.h` | 依赖 | 描边样式 |
