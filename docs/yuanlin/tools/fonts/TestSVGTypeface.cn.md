# TestSVGTypeface

> 源文件
> - tools/fonts/TestSVGTypeface.h
> - tools/fonts/TestSVGTypeface.cpp

## 概述

TestSVGTypeface 是 Skia 的测试工具模块,用于创建基于 SVG 的字体。该模块将 SVG 资源文件作为字形内容,并提供完整的字体功能,包括字形渲染、度量计算和字体导出。主要用途包括:

- 创建用于测试的 SVG 字体(如 emoji、图标字体)
- 将 SVG 字形导出为 TrueType 字体格式(CBDT、sbix、COLR)
- 测试 Skia 对彩色字形格式的支持
- 提供预定义的测试字体(Default、Planets)

核心特性:
- 延迟加载 SVG 资源,仅在需要时解析
- 支持将 SVG 渲染为 ARGB32 位图
- 可导出为多种 OpenType 彩色字体格式
- 线程安全的 SVG 解析和渲染

## 架构位置

```
skia/
├── include/core/          # 核心 API
│   └── SkTypeface.h       # 字体基类
├── src/core/              # 核心实现
│   └── SkScalerContext.h  # 缩放上下文
├── modules/svg/           # SVG 模块
│   └── include/SkSVGDOM.h # SVG 文档对象模型
├── tools/
│   ├── Resources.h        # 资源加载工具
│   └── fonts/             # 字体工具
│       ├── TestSVGTypeface.h    # 本模块头文件
│       └── TestSVGTypeface.cpp  # 本模块实现
└── resources/fonts/svg/   # SVG 字形资源文件
```

在字体渲染架构中:
- 继承 `SkTypeface` 实现自定义字体
- 通过 `SkTestSVGScalerContext` 处理字形光栅化
- 依赖 `SkSVGDOM` 模块渲染 SVG 内容
- 仅在启用 `SK_ENABLE_SVG` 时编译

## 主要类与结构体

### SkSVGTestTypefaceGlyphData
```cpp
struct SkSVGTestTypefaceGlyphData {
    const char* fSvgResourcePath;  // SVG 资源路径
    SkPoint     fOrigin;           // 字形原点(y 轴向下)
    SkScalar    fAdvance;          // 字形前进宽度
    SkUnichar   fUnicode;          // Unicode 码点
};
```
定义单个字形的数据,用于构造字体。

### TestSVGTypeface
```cpp
class TestSVGTypeface : public SkTypeface
```
抽象基类,实现基于 SVG 的字体。

**主要成员**:
- `fName`: 字体名称
- `fUpem`: 每 em 单位数(units per em)
- `fFontMetrics`: 字体度量信息
- `fGlyphs`: 字形数组
- `fGlyphCount`: 字形数量
- `fCMap`: Unicode 到字形 ID 的映射表

**核心方法**:
- `Default()`: 创建默认测试字体(emoji)
- `Planets()`: 创建行星主题字体
- `exportTtxCbdt()`: 导出为 CBDT 格式
- `exportTtxSbix()`: 导出为 sbix 格式
- `exportTtxColr()`: 导出为 COLR 格式
- `getPathOp()`: 获取路径操作类型(用于合成字形)

### TestSVGTypeface::Glyph
```cpp
struct Glyph {
    SkPoint     fOrigin;        // 字形原点
    SkScalar    fAdvance;       // 前进宽度
    const char* fResourcePath;  // SVG 资源路径

    // 延迟加载的 SVG 数据
    mutable SkMutex         fSvgMutex;
    mutable bool            fParsedSvg;
    mutable sk_sp<SkSVGDOM> fSvg;
};
```
存储单个字形的数据,支持延迟加载 SVG。

**核心方法**:
- `size()`: 获取 SVG 容器尺寸
- `render()`: 渲染 SVG 到画布
- `withSVG()`: 线程安全地访问 SVG 对象

### SkTestSVGScalerContext
```cpp
class SkTestSVGScalerContext : public SkScalerContext
```
处理 SVG 字形的缩放和渲染。

**主要成员**:
- `fMatrix`: 从字体单位到像素的变换矩阵

**核心方法**:
- `generateMetrics()`: 生成字形度量
- `generateImage()`: 渲染字形图像
- `generatePath()`: 返回空路径(SVG 字形不使用路径)
- `generateDrawable()`: 生成可绘制对象

### GlyfInfo 和 GlyfLayerInfo
```cpp
struct GlyfLayerInfo {
    int     fLayerColorIndex;  // COLR 颜色索引
    SkIRect fBounds;           // 层边界
};

struct GlyfInfo {
    SkIRect                             fBounds;   // 字形边界
    skia_private::TArray<GlyfLayerInfo> fLayers;   // 颜色层
};
```
用于 COLR 字体导出,存储字形的颜色层信息。

### DefaultTypeface 和 PlanetTypeface
```cpp
class DefaultTypeface : public TestSVGTypeface
class PlanetTypeface : public TestSVGTypeface
```
两个具体的字体实现,提供预定义的字形集。

## 公共 API 函数

### TestSVGTypeface::Default()
```cpp
static sk_sp<TestSVGTypeface> Default()
```
**功能**: 创建默认 SVG 测试字体
**字形内容**:
- `.notdef` (U+0000): 默认字形
- 空格 (U+0020): 空字形
- 菱形 (U+2662): ♢
- 笑脸 (U+1F600): 😀

### TestSVGTypeface::Planets()
```cpp
static sk_sp<TestSVGTypeface> Planets()
```
**功能**: 创建行星主题字体
**字形内容**: 冥王星、水星、金星、地球、火星、木星、土星、天王星、海王星

### exportTtxCbdt()
```cpp
void exportTtxCbdt(SkWStream* out, SkSpan<unsigned> strikeSizes) const
```
**功能**: 导出为 CBDT(彩色位图数据表)格式的 TTX XML
**参数**:
- `out`: 输出流
- `strikeSizes`: 要生成的字号数组

**特点**:
- CBDT 格式限制严格,需验证尺寸是否在范围内
- 使用 PNG 编码存储位图
- 格式 17: SmallGlyphMetrics + PNG 数据

### exportTtxSbix()
```cpp
void exportTtxSbix(SkWStream* out, SkSpan<unsigned> strikeSizes) const
```
**功能**: 导出为 sbix(标准位图图像表)格式
**参数**: 同 `exportTtxCbdt()`

**特点**:
- Apple 的彩色字体格式
- 需要 `glyf` 表提供轮廓数据
- 使用退化轮廓解决 CoreText 边界计算问题
- PNG 图像填充透明像素以兼容不同平台

### exportTtxColr()
```cpp
void exportTtxColr(SkWStream* out) const
```
**功能**: 导出为 COLR/CPAL(颜色表)格式
**特点**:
- 基于矢量的彩色字体格式
- 将 SVG 转换为二次曲线轮廓
- 使用路径操作合成字形
- 支持 "currentColor" 特殊颜色

### getAdvance()
```cpp
SkVector getAdvance(SkGlyphID glyphID) const
```
**功能**: 获取字形的前进向量
**返回**: (fAdvance, 0) 向量

### getFontMetrics()
```cpp
void getFontMetrics(SkFontMetrics* metrics) const
```
**功能**: 获取字体度量信息

## 内部实现细节

### 延迟 SVG 加载机制
```cpp
template <typename Fn>
void TestSVGTypeface::Glyph::withSVG(Fn&& fn) const {
    SkAutoMutexExclusive lock(fSvgMutex);
    if (!fParsedSvg) {
        fParsedSvg = true;
        std::unique_ptr<SkStreamAsset> stream = GetResourceAsStream(fResourcePath);
        fSvg = SkSVGDOM::MakeFromStream(*stream);
    }
    if (fSvg) {
        fn(*fSvg);
    }
}
```
**特性**:
- 使用互斥锁保证线程安全
- 首次访问时才加载和解析 SVG
- 解析失败时优雅处理
- 通过回调函数模式访问 SVG

### 字形度量计算
```cpp
GlyphMetrics generateMetrics(const SkGlyph& glyph, SkArenaAlloc*) {
    GlyphMetrics mx(SkMask::kARGB32_Format);
    mx.neverRequestPath = true;  // SVG 字形不提供路径
    mx.advance = this->computeAdvance(glyph.getGlyphID());

    // 计算边界: 应用变换矩阵和子像素偏移
    SkRect newBounds = SkRect::MakeXYWH(
        glyphData.fOrigin.fX,
        -glyphData.fOrigin.fY,
        containerSize.fWidth,
        containerSize.fHeight);
    fMatrix.mapRect(&newBounds);
    newBounds.offset(dx, dy);
    newBounds.roundOut(&mx.bounds);
    return mx;
}
```
**关键点**:
- 固定使用 ARGB32 格式
- 坐标系转换: SVG 使用 y 轴向下,字体使用 y 轴向上
- 考虑子像素定位偏移

### 字形渲染流程
```cpp
void generateImage(const SkGlyph& glyph, void* imageBuffer) {
    SkBitmap bm;
    bm.installPixels(SkImageInfo::MakeN32(glyph.width(), glyph.height(), ...),
                     imageBuffer, glyph.rowBytes());
    bm.eraseColor(0);

    SkCanvas canvas(bm);
    canvas.translate(-glyph.left(), -glyph.top());  // 移动到字形原点
    canvas.translate(dx, dy);                        // 子像素偏移
    canvas.concat(fMatrix);                          // 缩放到字号
    canvas.translate(glyphData.fOrigin.fX, -glyphData.fOrigin.fY);  // 字形原点

    glyphData.render(&canvas);
}
```

### SVG 到 TrueType 轮廓转换
COLR 导出需要将 SVG 转换为 TrueType 二次曲线:

1. **路径效果应用**:
```cpp
skpathutils::FillPathWithPaint(path, paint, &builder);
```

2. **坐标系转换**:
```cpp
m.postTranslate(0, fBaselineOffset);  // 基线对齐
m.postScale(1, -1);                   // y 轴翻转(OpenType 是 y 向上)
```

3. **三次曲线转二次曲线**:
```cpp
void convertCubicToQuads(const SkPoint p[4], SkScalar tolScale, TArray<SkPoint>* quads)
```
使用递归细分算法,在拐点处分割三次曲线。

4. **圆锥曲线转二次曲线**:
```cpp
SkAutoConicToQuads converter;
quadPts = converter.computeQuads(pts, *w, SK_Scalar1);
```

### 路径操作策略
根据颜色决定如何合成字形:
```cpp
// DefaultTypeface
bool getPathOp(SkColor color, SkPathOp* op) const {
    int brightness = (R + G + B) / 3;
    if (brightness > 0x20) {
        *op = kDifference_SkPathOp;  // 亮色做差集
    } else {
        *op = kUnion_SkPathOp;       // 暗色做并集
    }
    return true;
}
```
这用于创建 COLR 字体的默认字形轮廓。

### CBDT 格式限制检查
```cpp
// CBLC 元数据限制
if (!SkTFitsIn<int8_t>((int)(-fm.fTop)) ||
    !SkTFitsIn<int8_t>((int)(-fm.fBottom)) ||
    !SkTFitsIn<uint8_t>((int)(fm.fXMax - fm.fXMin))) {
    continue;  // 跳过过大的字号
}

// CBDT 字形限制
if (!SkTFitsIn<int8_t>(ibounds.fLeft) ||
    !SkTFitsIn<int8_t>(ibounds.fTop) ||
    !SkTFitsIn<uint8_t>(ibounds.width()) ||
    !SkTFitsIn<uint8_t>(ibounds.height()) ||
    !SkTFitsIn<uint8_t>((int)advance)) {
    return true;  // 字形过大
}
```

### sbix 跨平台兼容性处理
注释中详细说明了不同平台的边界计算差异:
- **DWrite**: `bbox = ((0,0), png.size) + originOffset`
- **FreeType**: `bbox = ((0,0), png.size) + (lsb, bbox.yMin) + originOffset`
- **CoreText**: `bbox = ((lsb, bbox.yMin), (lsb + bbox.width, bbox.yMax))`

为了兼容,使用:
```cpp
lsb = x
bbox = ((0, y), (png.width, png.height + y))
originOffset = (0, 0)
```

## 依赖关系

### 核心依赖
- `SkTypeface`: 字体基类
- `SkScalerContext`: 缩放上下文基类
- `SkSVGDOM`: SVG 文档对象模型
- `SkCanvas`: 画布渲染
- `SkPath`: 路径表示

### 字体相关
- `SkFontMetrics`: 字体度量
- `SkFontDescriptor`: 字体描述符
- `SkAdvancedTypefaceMetrics`: 高级字体元数据
- `SkScalerContextRec`: 缩放上下文记录

### 图形相关
- `SkBitmap`, `SkSurface`, `SkImage`: 位图处理
- `SkPngEncoder`: PNG 编码
- `SkPathOps`: 路径操作(并集、差集等)

### 工具依赖
- `tools/Resources.h`: 资源加载(`GetResourceAsStream()`)
- `SkOTUtils`: OpenType 工具
- `skpathutils`: 路径工具

### 线程安全
- `SkMutex`: 互斥锁,保护 SVG 解析

## 设计模式与设计决策

### 模板方法模式
`TestSVGTypeface` 作为抽象基类,定义字体操作流程:
```cpp
virtual bool getPathOp(SkColor color, SkPathOp* op) const = 0;
```
子类(`DefaultTypeface`, `PlanetTypeface`)实现具体策略。

### 延迟初始化模式
SVG 资源仅在首次使用时加载:
- **优点**: 节省内存,加快字体创建速度
- **线程安全**: 使用互斥锁保护
- **实现**: `withSVG()` 模板方法

### 访问者模式的变体
`withSVG()` 接受回调函数,访问 SVG 对象:
```cpp
glyphData.withSVG([](const SkSVGDOM& svg) {
    svg.render(canvas);
});
```
这避免了暴露 `mutable` 成员的锁定细节。

### 工厂方法模式
```cpp
static sk_sp<TestSVGTypeface> Default();
static sk_sp<TestSVGTypeface> Planets();
```
提供预配置的字体实例,隐藏构造细节。

### 策略模式
不同的字体导出格式使用不同的策略:
- `exportTtxCbdt()`: 位图 PNG 策略
- `exportTtxSbix()`: 位图 + 退化轮廓策略
- `exportTtxColr()`: 矢量颜色层策略

### 字体序列化设计
使用 `FactoryId` 机制支持字体序列化/反序列化:
```cpp
static constexpr FactoryId = SkSetFourByteTag('d','s','v','g');
SkTypeface::Register(FactoryId, &MakeFromStream);
```
这允许字体通过 Skia 的序列化系统传输。

### 坐标系设计决策
统一使用 OpenType 坐标系(y 轴向上):
- SVG 输入: y 轴向下
- 内部存储: 使用 `fOrigin` 和 `-glyphData.fOrigin.fY`
- 输出: OpenType y 轴向上

### 格式选择的权衡
- **CBDT**: 紧凑但限制严格,适合小尺寸位图
- **sbix**: Apple 生态,需要特殊边界处理
- **COLR**: 矢量可缩放,但转换损失精度

## 性能考量

### 延迟加载优化
```cpp
mutable bool fParsedSvg = false;
```
- 避免预加载所有 SVG
- 减少初始化时间
- 节省未使用字形的内存

**场景**: 文档可能只使用少数字形,不需要全部加载。

### SVG 解析缓存
一旦解析完成,SVG DOM 保留在内存中:
```cpp
mutable sk_sp<SkSVGDOM> fSvg;
```
**权衡**: 内存占用 vs. 重复解析时间

### 三次曲线转换优化
```cpp
static const int kMaxSubdivs = 10;
if (dSqd < toleranceSqd || sublevel > kMaxSubdivs) {
    // 停止递归
}
```
限制递归深度,避免过度细分。

### 位图格式选择
```cpp
SkImageInfo::MakeN32Premul(width, height)
```
使用平台原生格式,减少转换开销。

### 路径操作效率
```cpp
SkOpBuilder fBasePath;
fBasePath.add(path, op);
SkPath result = fBasePath.resolve();
```
使用 `SkOpBuilder` 累积操作,一次性求解。

### TTX 输出优化
```cpp
SkDynamicMemoryWStream glyfOut;
// ... 生成 glyf 表 ...
out->writeStream(glyfOut.detachAsStream(), ...);
```
使用内存流缓冲,避免多次 I/O。

## 相关文件

### 核心接口
- `include/core/SkTypeface.h`: 字体基类
- `src/core/SkScalerContext.h`: 缩放上下文
- `include/core/SkFontMetrics.h`: 字体度量

### SVG 模块
- `modules/svg/include/SkSVGDOM.h`: SVG DOM
- `modules/svg/include/SkSVGNode.h`: SVG 节点

### 工具依赖
- `tools/Resources.h`: 资源加载
- `src/sfnt/SkOTUtils.h`: OpenType 工具

### 图形相关
- `include/core/SkCanvas.h`: 画布渲染
- `include/pathops/SkPathOps.h`: 路径操作
- `include/encode/SkPngEncoder.h`: PNG 编码

### 字体格式参考
- CBDT/CBLC: OpenType 嵌入位图表
- sbix: Apple 扩展位图表
- COLR/CPAL: OpenType 彩色字体表
- TTX: FontTools XML 字体表示

### 测试用途
该模块主要用于:
- `tests/`: 字体渲染测试
- `gm/`: 黄金图像测试
- `tools/viewer/`: 字体查看器
- `dm/`: DM 测试框架
