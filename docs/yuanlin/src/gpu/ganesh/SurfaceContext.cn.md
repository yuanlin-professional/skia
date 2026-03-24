# SurfaceContext

> 源文件: `src/gpu/ganesh/SurfaceContext.h` (280 行), `src/gpu/ganesh/SurfaceContext.cpp` (1410 行)

## 1. 概述

`SurfaceContext` 是 Skia Ganesh GPU 后端中 GPU 表面的基础抽象类，提供像素读写、缩放、异步读取和底层拷贝能力。它是整个表面上下文继承体系的根基类，本身**不拥有写入视图**，只持有只读的 `fReadView`。

**继承关系**：`SurfaceDrawContext` (final) → `SurfaceFillContext` → `SurfaceContext`（INHERITED = SkRefCnt）

**架构位置**：
```
SkCanvas → SkDevice → SurfaceDrawContext → SurfaceFillContext → SurfaceContext
                                                                     ↓
                                                          GrSurfaceProxyView (readView)
                                                          GrRecordingContext
                                                          GrColorInfo
```

**关键成员变量**：

| 成员 | 类型 | 可见性 | 说明 |
|------|------|--------|------|
| `fContext` | `GrRecordingContext*` | protected | 记录上下文指针，用于访问 GPU 资源、caps、drawing manager |
| `fReadView` | `GrSurfaceProxyView` | protected | 只读的表面代理视图，包含 proxy、origin、swizzle |
| `fColorInfo` | `GrColorInfo` | private | 颜色信息，包含颜色类型、alpha 类型和色彩空间 |

**内部结构体**：

```cpp
struct PixelTransferResult {
    using ConversionFn = void(void* dst, const void* mappedBuffer);
    sk_sp<GrGpuBuffer> fTransferBuffer;  // 如果为 null 表示传输失败
    size_t fRowBytes;                     // 传输缓冲区的行字节数
    std::function<ConversionFn> fPixelConverter; // 如果非 null，数据可用时需要调用此转换函数
};
```

---

## 2. 构造函数与析构函数

### SurfaceContext(rContext, readView, colorInfo)

```cpp
SurfaceContext(GrRecordingContext* context, GrSurfaceProxyView readView, const GrColorInfo& info);
```

**流程**：
1. 初始化 `fContext = context`，`fReadView = std::move(readView)`，`fColorInfo = info`
2. 断言 `!context->abandoned()`（context 未被放弃）

### ~SurfaceContext()

```cpp
virtual ~SurfaceContext() = default;
```

默认虚析构函数，允许子类安全析构。

---

## 3. 公共方法

### 3.1 类型别名

```cpp
using ReadPixelsCallback = SkImage::ReadPixelsCallback;
using ReadPixelsContext   = SkImage::ReadPixelsContext;
using RescaleGamma        = SkImage::RescaleGamma;
using RescaleMode         = SkImage::RescaleMode;
```

这些别名将 `SkImage` 中定义的异步读取相关类型引入 SurfaceContext 的作用域，供 `asyncRescaleAndReadPixels` 和 `asyncRescaleAndReadPixelsYUV420` 使用。

### 3.2 查询方法（内联）

| 方法 | 返回类型 | 实现 |
|------|---------|------|
| `recordingContext()` | `GrRecordingContext*` | 返回 `fContext` |
| `colorInfo()` | `const GrColorInfo&` | 返回 `fColorInfo` 的 const 引用 |
| `imageInfo()` | `GrImageInfo` | 返回 `GrImageInfo{fColorInfo, fReadView.proxy()->dimensions()}` |
| `origin()` | `GrSurfaceOrigin` | `fReadView.origin()` |
| `readSwizzle()` | `skgpu::Swizzle` | `fReadView.swizzle()` |
| `readSurfaceView()` | `GrSurfaceProxyView` | 返回 `fReadView`（拷贝，含 ref proxy） |
| `dimensions()` | `SkISize` | `fReadView.dimensions()` |
| `width()` | `int` | `fReadView.proxy()->width()` |
| `height()` | `int` | `fReadView.proxy()->height()` |
| `mipmapped()` | `skgpu::Mipmapped` | `fReadView.mipmapped()` |
| `caps()` | `const GrCaps*` | `fContext->priv().caps()` |
| `asSurfaceProxy()` | `GrSurfaceProxy*` | `fReadView.proxy()` |
| `asSurfaceProxy() const` | `const GrSurfaceProxy*` | `fReadView.proxy()` |
| `asSurfaceProxyRef()` | `sk_sp<GrSurfaceProxy>` | `fReadView.refProxy()` |
| `asTextureProxy()` | `GrTextureProxy*` | `fReadView.asTextureProxy()` |
| `asTextureProxy() const` | `const GrTextureProxy*` | `fReadView.asTextureProxy()` |
| `asTextureProxyRef()` | `sk_sp<GrTextureProxy>` | `fReadView.asTextureProxyRef()` |
| `asRenderTargetProxy()` | `GrRenderTargetProxy*` | `fReadView.asRenderTargetProxy()` |
| `asRenderTargetProxy() const` | `const GrRenderTargetProxy*` | `fReadView.asRenderTargetProxy()` |
| `asRenderTargetProxyRef()` | `sk_sp<GrRenderTargetProxy>` | `fReadView.asRenderTargetProxyRef()` |
| `asFillContext()` | `SurfaceFillContext*` | 返回 `nullptr`（虚函数，`SurfaceFillContext` 重写返回 `this`） |

### 3.3 readPixels(dContext, dst, srcPt)

```cpp
bool readPixels(GrDirectContext* dContext, GrPixmap dst, SkIPoint pt);
```

从表面读取像素到目标 pixmap。内部实现有三条路径：copy 路径、canvas2D 快速路径、直接读取路径。

**流程**：

1. `ASSERT_SINGLE_OWNER` + `RETURN_FALSE_IF_ABANDONED` + `validate()`
2. **前置校验**：
   - context 匹配检查：`fContext->priv().matches(dContext)` → false 则返回
   - `dst.colorType() == GrColorType::kUnknown` → 返回 false
   - `dst.rowBytes() % dst.info().bpp()` 行字节对齐检查 → 未对齐返回 false
   - `dst = dst.clip(this->dimensions(), &pt)` 裁剪 dst 到表面范围
   - `!dst.hasPixels()` → 裁剪后无像素返回 false
   - `alpha_types_compatible` 检查：src 和 dst 的 alphaType 要么都是 kUnknown 要么都非 kUnknown
3. 获取 `srcProxy = this->asSurfaceProxyRef()`
4. 检查 `srcProxy->framebufferOnly()` → 是则返回 false
5. 实例化 proxy：`srcProxy->instantiate(dContext->priv().resourceProvider())` → 失败返回 false
6. 获取 `srcSurface = srcProxy->peekSurface()`
7. **计算颜色转换标志**：`SkColorSpaceXformSteps{this->colorInfo(), dst.info()}.fFlags`
   - `unpremul`：是否需要反预乘
   - `needColorConversion`：linearize || gamut_transform || encode
   - `premul`：是否需要预乘
8. **Canvas2D 快速路径判断**：同时满足以下所有条件时启用：
   - `unpremul` 为 true
   - `!needColorConversion`
   - dst colorType 为 RGBA_8888 或 BGRA_8888
   - srcProxy 是 textureProxy
   - src colorType 为 RGBA_8888 或 BGRA_8888
   - RGBA_8888 默认 backend format 有效
   - `dContext->priv().validPMUPMConversionExists()` 返回 true
9. 再次 `RETURN_FALSE_IF_ABANDONED`（`validPMUPMConversionExists` 可能触发 GPU 提交导致 abandon）
10. **检查 surfaceSupportsReadPixels**：
    - `kUnsupported` → 返回 false
    - `kCopyToTexture2D` 或 `canvas2DFastPath` → 走 copy 路径（步骤 11）
    - 否则 → 走直接读取路径（步骤 12）

11. **Copy 路径**（`kCopyToTexture2D` 或 `canvas2DFastPath`）：

    **如果是 textureProxy**：
    1. 确定临时 colorType：
       - `canvas2DFastPath` 或 `srcIsCompressed` → `colorType = GrColorType::kRGBA_8888`
       - 否则 → 用 `getDefaultBackendFormat(colorType, kYes)` 查默认格式，无效则 fallback 到 RGBA_8888
    2. 确定 alphaType：canvas2DFastPath 用 `dst.alphaType()`，否则用 `this->colorInfo().alphaType()`
    3. 创建临时 SFC：`dContext->priv().makeSFC(tempInfo, "SurfaceContext_ReadPixels", kApprox)`
    4. 构建 FragmentProcessor：
       - canvas2DFastPath → `createPMToUPMEffect(GrTextureEffect::Make(...))`；如果 dst 是 BGRA → 额外包装 `SwizzleOutput(BGRA)`，并将 dst 的 colorType 改为 RGBA_8888
       - 否则 → `GrTextureEffect::Make(readSurfaceView, alphaType)`
    5. `sfc->fillRectToRectWithFP(srcRect, dstRect, fp)` 绘制到临时 SFC
    6. 递归 `tempCtx->readPixels(dContext, dst, {0, 0})`

    **如果不是 textureProxy（render target only）**：
    1. 获取 `getDstCopyRestrictions(this->asRenderTargetProxy(), colorType)`
    2. `fMustCopyWholeSrc` 为 true → `GrSurfaceProxy::Copy` 拷贝整个表面
    3. 否则 → `GrSurfaceProxy::Copy` 仅拷贝 srcRect 区域
    4. 用 copy 创建临时 `SurfaceContext`：`dContext->priv().makeSC(view, colorInfo)`
    5. 递归 `tempCtx->readPixels(dContext, dst, pt)`

12. **直接读取路径**：
    1. 计算 `flip = (origin == kBottomLeft)`
    2. 查询 `caps->supportedReadPixelsColorType(srcColorType, backendFormat, dstColorType)` 获取 `supportedRead`
    3. 判断 `makeTight`：`!readPixelsRowBytesSupport` 且行字节非 minRowBytes
    4. 判断 `convert`：unpremul || premul || needColorConversion || flip || makeTight || (dst.colorType != supportedRead.fColorType)
    5. 如果 `convert`：
       - 创建临时 buffer（`std::make_unique<char[]>(size)`），colorType 使用 supportedRead.fColorType
       - 设置 readDst = tmp，readRB = tmpRB
       - flip 时调整 `pt.fY = srcSurface->height() - pt.fY - dst.height()`
    6. `dContext->priv().flushSurface(srcProxy)` + `dContext->submit()`
    7. `gpu->readPixels(srcSurface, rect, srcColorType, supportedColorType, readDst, readRB)` → 失败返回 false
    8. 如果有 tmp → `GrConvertPixels(dst, tmp, flip)` 执行转换

### 3.4 writePixels(dContext, src, dstPt)（单级）

```cpp
bool writePixels(GrDirectContext* dContext, GrCPixmap src, SkIPoint dstPt);
```

将单个 pixmap 的像素数据写入表面的指定位置。

**流程**：
1. `ASSERT_SINGLE_OWNER` + `RETURN_FALSE_IF_ABANDONED` + `validate()`
2. `src = src.clip(this->dimensions(), &dstPt)` 裁剪 src 到表面范围
3. `!src.hasPixels()` → 裁剪后无像素返回 false
4. 检查 `bpp` 有效、`rowBytes % bpp` 对齐 → 不满足返回 false
5. 委托 `this->internalWritePixels(dContext, &src, 1, dstPt)`

### 3.5 writePixels(dContext, src[], numLevels)（多级 MIP）

```cpp
bool writePixels(GrDirectContext* dContext, const GrCPixmap src[], int numLevels);
```

写入完整的 MIP 链数据到纹理。

**流程**：
1. `ASSERT_SINGLE_OWNER` + `RETURN_FALSE_IF_ABANDONED` + `validate()`
2. 断言 `dContext` 非空、`numLevels >= 1`、`src` 非空
3. 如果 `numLevels == 1`：
   - 检查 `src->dimensions() == this->dimensions()` → 不匹配返回 false
   - 委托单级 `writePixels(dContext, src[0], {0, 0})`
4. 检查 `this->asTextureProxy()` 非空且 `proxyMipmapped() == kYes` → 不满足返回 false
5. 验证 `numLevels == SkMipmap::ComputeLevelCount(dims) + 1` → 不匹配返回 false
6. 逐级验证：
   - 每级的 `colorInfo` 必须与 `src[0]` 一致
   - 每级的 `dimensions` 必须与预期的逐级减半一致
   - 每级的 `rowBytes % bpp` 必须对齐
   - `dims = {max(1, dims.width()/2), max(1, dims.height()/2)}`
7. 委托 `this->internalWritePixels(dContext, src, numLevels, {0, 0})`

### 3.6 asyncRescaleAndReadPixels(dContext, info, srcRect, rescaleGamma, rescaleMode, callback, ctx)

```cpp
void asyncRescaleAndReadPixels(GrDirectContext* dContext,
                               const SkImageInfo& info,
                               const SkIRect& srcRect,
                               RescaleGamma rescaleGamma,
                               RescaleMode rescaleMode,
                               ReadPixelsCallback callback,
                               ReadPixelsContext callbackContext);
```

异步缩放并读取像素。是 `SkImage::asyncRescaleAndReadPixels` 和 `SkSurface::asyncRescaleAndReadPixels` 的 GPU 实现。

**流程**：
1. **前置检查**（任一失败 → `callback(ctx, nullptr)` 返回）：
   - `dContext` 非空
   - 如果是 renderTargetProxy → 非 `wrapsVkSecondaryCB`
   - 如果是 renderTargetProxy → 非 `framebufferOnly`
   - `dstCT = SkColorTypeToGrColorType(info.colorType())` 非 kUnknown
2. **判断 needsRescale**：以下任一条件为 true：
   - `srcRect.size() != info.dimensions()`（尺寸不同）
   - `origin == kBottomLeft`（需要翻转）
   - `alphaType` 不同
   - `colorSpace` 不同
3. 查询 `supportedReadPixelsColorType`，检查 `readInfo.fColorType != kUnknown`
4. 检查通道兼容性：`(~legalReadChannels & dstChannels) & srcChannels` 为 0（read colorType 的通道必须覆盖 dst 所需且 src 拥有的通道）
5. 如果 `needsRescale`：
   - 创建 `tempInfo = GrImageInfo(info).makeColorType(this->colorInfo().colorType())`
   - 调用 `this->rescale(tempInfo, kTopLeft, srcRect, rescaleGamma, rescaleMode)` 到临时 SFC
   - 失败 → `callback(ctx, nullptr)` 返回
   - 重置 `x = y = 0`
6. 选择 srcCtx：有临时 SFC 用临时的，否则用 `this`
7. 委托 `srcCtx->asyncReadPixels(dContext, rect, info.colorType(), callback, ctx)`

### 3.7 asyncRescaleAndReadPixelsYUV420(...)

```cpp
void asyncRescaleAndReadPixelsYUV420(GrDirectContext* dContext,
                                     SkYUVColorSpace yuvColorSpace,
                                     bool readAlpha,
                                     sk_sp<SkColorSpace> dstColorSpace,
                                     const SkIRect& srcRect,
                                     SkISize dstSize,
                                     RescaleGamma rescaleGamma,
                                     RescaleMode rescaleMode,
                                     ReadPixelsCallback callback,
                                     ReadPixelsContext callbackContext);
```

异步缩放并读取像素为 YUV420 格式（可选 A 通道）。是 `SkImage::asyncRescaleAndReadPixelsYUV420` 的 GPU 实现。

**流程**：

1. **前置检查**（任一失败 → `callback(ctx, nullptr)` 返回）：
   - `dContext` 非空
   - 非 `wrapsVkSecondaryCB`
   - 非 `framebufferOnly`
   - 非 Protected
2. 断言 `dstSize` 非零，宽高均为偶数
3. **判断 needsRescale**：`srcRect.size() != dstSize` 或 colorSpace 不同
4. 获取 `srcView = this->readSurfaceView()`
5. **准备源纹理视图**：
   - 如果 `needsRescale` → `this->rescale(...)` 到 RGBA_8888 临时 SFC，失败则 callback(nullptr)；`srcView = tempFC->readSurfaceView()`，`x = y = 0`
   - 否则如果 `srcView` 非 textureProxy → `GrSurfaceProxyView::Copy(...)` 拷贝到纹理，失败则 callback(nullptr)；`x = y = 0`
6. **创建 Y/U/V/A 的 SFC**：
   - Y：`makeSFCWithFallback(A8, dstSize, kApprox, sampleCount=1, kNo mipmap, kNo protected)`
   - A（可选，`readAlpha` 时）：同 Y 的尺寸和格式
   - U：`makeSFCWithFallback(A8, dstSize/2, ...)`
   - V：同 U
   - 任一创建失败 → callback(nullptr)
7. **计算 RGB→YUV 矩阵**：`SkColorMatrix_RGB2YUV(yuvColorSpace, baseM)` → 20 元素矩阵
8. 创建 `texMatrix = SkMatrix::Translate(x, y)`
9. 查询 Y 平面的 `supportedReadPixelsColorType`，检查 readCT 非 kUnknown
10. 判断 `doSynchronousRead`：`!transferFromSurfaceToBufferSupport` 或 `offsetAlignment == 0`
11. **填充 Y 平面**：
    - 构造 yM[20]：前 15 个元素为 0，后 5 个元素从 baseM 第 0 行取（提取 Y 分量到 alpha 通道）
    - `GrTextureEffect::Make(srcView, alphaType, texMatrix)` → `ColorMatrix(yM, unpremulInput=false, clampRGBOutput=true, premulOutput=false)`
    - `yFC->fillWithFP(yFP)`
    - 非同步模式 → `yTransfer = yFC->transferPixels(kAlpha_8, fullRect)`
12. **填充 A 平面**（`readAlpha` 时）：
    - 直接 `GrTextureEffect::Make(srcView, alphaType, texMatrix)` 作为 FP（baseM 中 A 行为 identity：0,0,0,1,0）
    - `aFC->fillWithFP(aFP)`
    - 非同步模式 → `aTransfer = aFC->transferPixels(...)`
13. **填充 U/V 平面**：
    - `texMatrix.preScale(2.f, 2.f)`（UV 为半尺寸，需要 2x 缩放采样）
    - U：从 baseM 第 1 行取 uM[20]，`GrTextureEffect::Make(..., kLinear)` + `ColorMatrix(uM)` → `uFC->fillWithFP`
    - V：从 baseM 第 2 行取 vM[20]，`GrTextureEffect::Make(..., kLinear)` + `ColorMatrix(vM)` → `vFC->fillWithFP`
    - 非同步模式 → 各自 `transferPixels`
14. **读取结果**：

    **同步路径**（`doSynchronousRead`）：
    - 分配 Y/U/V/A 的 CPU pixmap
    - 逐平面 `readPixels(dContext, pmp, {0,0})`，任一失败 → callback(nullptr)
    - 创建 `AsyncReadResult`，逐平面 `addCpuPlane`
    - `callback(ctx, result)`

    **异步路径**：
    - 创建 `FinishContext` 结构体，包含 callback、Y/U/V/A 的 transferResult
    - 创建 `finishCallback` lambda：逐平面 `addTransferResult`（Y → U → V → A），任一失败 → callback(nullptr)，全部成功 → callback(result)
    - 设置 `flushInfo.fFinishedContext` 和 `flushInfo.fFinishedProc`
    - `dContext->priv().flushSurface(proxy, kNoAccess, flushInfo)` 触发 GPU 执行

### 3.8 rescale(info, origin, srcRect, rescaleGamma, rescaleMode)

```cpp
std::unique_ptr<SurfaceFillContext> rescale(const GrImageInfo& info,
                                            GrSurfaceOrigin origin,
                                            SkIRect srcRect,
                                            RescaleGamma rescaleGamma,
                                            RescaleMode rescaleMode);
```

创建新的 SurfaceFillContext 并将 srcRect 区域缩放到其中。

**流程**：
1. 创建临时 SFC：`fContext->priv().makeSFCWithFallback(info, kExact, sampleCount=1, kNo mipmap, isProtected, origin)`
2. 调用 `this->rescaleInto(sfc.get(), MakeSize(sfc->dimensions()), srcRect, rescaleGamma, rescaleMode)`
3. 失败返回 nullptr，成功返回 sfc

### 3.9 rescaleInto(dst, dstRect, srcRect, rescaleGamma, rescaleMode)

```cpp
bool rescaleInto(SurfaceFillContext* dst,
                 SkIRect dstRect,
                 SkIRect srcRect,
                 RescaleGamma rescaleGamma,
                 RescaleMode rescaleMode);
```

将源矩形区域缩放到目标 SurfaceFillContext 的指定矩形区域。采用渐进式缩放策略。

**流程**：

1. **前置检查**：
   - 断言 `dst` 非空
   - `SkIRect::MakeSize(dst->dimensions()).contains(dstRect)` → 不满足返回 false
   - 非 `wrapsVkSecondaryCB` → 是则返回 false
   - 非 `framebufferOnly` → 是则返回 false
2. 获取 `texView = this->readSurfaceView()`
3. 定义 `ensureTexturable` lambda：
   - 如果 `texView` 非 textureProxy → `GrSurfaceProxyView::Copy(...)` 拷贝到纹理
   - 拷贝成功 → `srcRect = MakeSize(srcRect.size())`（重置到原点）
   - 返回 `{texView, srcRect}`
4. 如果 `finalSize == srcRect.size()` → 强制 `rescaleGamma = kSrc`，`rescaleMode = kNearest`（无需缩放）
5. **线性化步骤**（`rescaleGamma == kLinear` 且色彩空间存在且非线性）：
   - 调用 `ensureTexturable` 确保 texView 可采样
   - 创建线性色彩空间：`this->colorInfo().colorSpace()->makeLinearGamma()`
   - 创建 RGBA_F16 临时 SFC：`makeSFCWithFallback(GrColorType::kRGBA_F16, alphaType, linearCS, srcRect.size(), kApprox)`
   - `GrTextureEffect::Make(texView, ..., kNearest)` → `GrColorSpaceXformEffect::Make(fp, srcColorInfo, linearColorInfo)`
   - `linearRTC->fillWithFP(fp)` 填充线性化数据
   - `texView = linearRTC->readSurfaceView()`，`tempA = linearRTC`
   - `srcRect = MakeSize(srcRect.size())`
6. **迭代缩放循环** `do...while(srcRect.size() != finalSize)`：
   1. **计算 nextDims**：
      - 如果 `rescaleMode` 不是 kNearest 也不是 kLinear（即 kRepeatedCubic）：
        - 缩小方向：`nextDims.width = max((srcRect.width + 1) / 2, finalSize.width)`
        - 放大方向：`nextDims.width = min(srcRect.width * 2, finalSize.width)`
        - 高度同理
      - 否则（kNearest/kLinear）：`nextDims = finalSize`（一步到位）
   2. 获取 `input = tempA ? tempA.get() : this`
   3. **确定 stepDst 和 xform**：
      - 如果 `nextDims == finalSize`：`stepDst = dst`，`stepDstRect = dstRect`，计算 `xform = GrColorSpaceXform::Make(input->colorInfo(), dst->colorInfo())`
      - 否则：创建中间 SFC `tempB`，`stepDst = tempB.get()`，`stepDstRect = MakeSize(tempB->dimensions())`
   4. **构建 FragmentProcessor**：
      - **kRepeatedCubic**：
        - `ensureTexturable` 确保可采样
        - 确定 direction：`nextDims.width == srcRect.width` → kY；`nextDims.height == srcRect.height` → kX；否则 kXY
        - `GrBicubicEffect::MakeSubset(texView, alphaType, SkMatrix::I(), kClamp, kClamp, SkRect::Make(srcRect), gCatmullRom, dir, caps)`
      - **kNearest / kLinear**：
        - 确定 filter：kNearest → `Filter::kNearest`，kLinear → `Filter::kLinear`
        - 先尝试 `stepDst->copyScaled(texView.refProxy(), srcRect, stepDstRect, filter)`（hardware blit）
        - 如果有 xform 或 origin 不匹配或 copyScaled 失败 → 退回到 draw：
          - `ensureTexturable` 确保可采样
          - `GrTextureEffect::MakeSubset(texView, alphaType, SkMatrix::I(), {filter, kNone}, srcRectF, srcRectF, caps)`
   5. 如果有 `xform` → `fp = GrColorSpaceXformEffect::Make(fp, xform)` 包装颜色空间转换
   6. 如果 `fp` 非空 → `stepDst->fillRectToRectWithFP(srcRect, stepDstRect, fp)` 绘制
   7. `texView = stepDst->readSurfaceView()`
   8. `tempA = std::move(tempB)`，`srcRect = MakeSize(nextDims)`

---

## 4. 保护方法

### drawingManager() / const

```cpp
GrDrawingManager* drawingManager();
const GrDrawingManager* drawingManager() const;
```

返回 `fContext->priv().drawingManager()`。

### validate()（DEBUG）

```cpp
SkDEBUGCODE(void validate() const;)
```

**流程**：
1. 断言 `fReadView.proxy()` 存在
2. 调用 `fReadView.proxy()->validate(fContext)` 验证 proxy 有效性
3. 如果 `colorType != GrColorType::kUnknown` → 断言 `caps->areColorTypeAndFormatCompatible(colorType, proxy->backendFormat())`（colorType 与 proxy 的 backend format 兼容）
4. 调用 `this->onValidate()`（虚函数，子类可重写）

### singleOwner()（DEBUG）

```cpp
SkDEBUGCODE(skgpu::SingleOwner* singleOwner() const;)
```

返回 `fContext->priv().singleOwner()`，用于 `ASSERT_SINGLE_OWNER` 宏。

### transferPixels(dstCT, rect)

```cpp
PixelTransferResult transferPixels(GrColorType dstCT, const SkIRect& rect);
```

发起 GPU→CPU 异步像素传输，是 `asyncReadPixels` 和 `asyncRescaleAndReadPixelsYUV420` 的内部实现。

**流程**：
1. 断言 rect 在表面范围内
2. 获取 `direct = fContext->asDirectContext()`，为空则返回空结果
3. 如果 renderTargetProxy 且 `wrapsVkSecondaryCB` → 返回空结果
4. 查询 `supportedReadPixelsColorType(srcColorType, backendFormat, dstCT)` → `supportedRead`
5. 检查通道兼容性：`(~legalReadChannels & dstChannels) & srcChannels` 必须为 0
6. 检查 `caps->transferFromSurfaceToBufferSupport()` 且 `supportedRead.fOffsetAlignmentForTransferBuffer` 非 0 → 否则返回空结果
7. 计算 `rowBytes = GrColorTypeBytesPerPixel(supportedRead.fColorType) * rect.width()`，对齐到 `caps->transferBufferRowBytesAlignment()`
8. 计算 `size = rowBytes * rect.height()`
9. 创建 GPU buffer：`resourceProvider->createBuffer(size, kXferGpuToCpu, kStream, ZeroInit::kNo)`
10. 处理 bottomLeft flip：如果 `origin == kBottomLeft` → 翻转 srcRect 的 Y 坐标
11. 调用 `drawingManager->newTransferFromRenderTask(proxyRef, srcRect, srcColorType, supportedRead.fColorType, buffer, 0)`
12. **设置 PixelTransferResult**：
    - `result.fTransferBuffer = buffer`
    - 如果 `supportedRead.fColorType != dstCT` 或 `flip` → 设置 `result.fPixelConverter`（lambda 内调用 `GrConvertPixels` 转换），`result.fRowBytes = dstInfo.minRowBytes()`
    - 否则 → `result.fRowBytes = rowBytes`（无需转换）
13. 返回 result

### asyncReadPixels(dContext, srcRect, colorType, callback, ctx)

```cpp
void asyncReadPixels(GrDirectContext* dContext,
                     const SkIRect& srcRect,
                     SkColorType colorType,
                     ReadPixelsCallback callback,
                     ReadPixelsContext callbackContext);
```

异步读取像素的核心实现，由 `asyncRescaleAndReadPixels` 调用。

**流程**：
1. 断言 rect 在表面范围内
2. 检查 `dContext` 非空且 proxy 非 Protected → 否则 `callback(ctx, nullptr)`
3. 获取 `mappedBufferManager = dContext->priv().clientMappedBufferManager()`
4. 尝试 `transferResult = this->transferPixels(SkColorTypeToGrColorType(colorType), rect)`
5. **如果 transfer 失败**（`fTransferBuffer` 为 null）：
   - 分配 CPU pixmap：`GrPixmap::Allocate(ii)`
   - 创建 `AsyncReadResult`（使用 kInvalid DirectContextID），`addCpuPlane(pm)`
   - 同步 `this->readPixels(dContext, pm, {rect.fLeft, rect.fTop})` → 失败则 callback(nullptr)
   - 成功 → `callback(ctx, result)`
6. **如果 transfer 成功**：
   - 创建 `FinishContext` 结构体，包含 callback、callbackContext、rect.size()、mappedBufferManager、transferResult
   - 创建 `finishCallback` lambda：
     - 创建 `AsyncReadResult(manager->ownerID())`
     - `addTransferResult(transferResult, size, rowBytes, manager)` → 失败则 callback(nullptr)
     - 成功 → `callback(ctx, result)`
     - `delete context`
   - 设置 `flushInfo.fFinishedContext = finishContext`，`flushInfo.fFinishedProc = finishCallback`
   - `dContext->priv().flushSurface(proxy, kNoAccess, flushInfo)` 触发 GPU 执行并注册完成回调

---

## 5. 私有方法

### onValidate()（虚函数）

```cpp
SkDEBUGCODE(virtual void onValidate() const {})
```

默认空实现。`SurfaceFillContext` 重写以验证 `fOpsTask` 与 drawingManager 记录的最后一个 render task 一致。

### copy(src, srcRect, dstPoint)

```cpp
sk_sp<GrRenderTask> copy(sk_sp<GrSurfaceProxy> src, SkIRect srcRect, SkIPoint dstPoint);
```

将 src 的 srcRect 区域拷贝到当前表面的 dstPoint 位置。目前只被 `writePixels` 和 `replaceRenderTarget` 直接调用。

**流程**：
1. `GrClipSrcRectAndDstPoint(this->dimensions(), &dstPoint, src->dimensions(), &srcRect)` 裁剪 src/dst → 无交集返回 nullptr
2. 构造 `dstRect = SkIRect::MakePtSize(dstPoint, srcRect.size())`
3. 委托 `this->copyScaled(src, srcRect, dstRect, GrSamplerState::Filter::kNearest)`

### copyScaled(src, srcRect, dstRect, filter)

```cpp
sk_sp<GrRenderTask> copyScaled(sk_sp<GrSurfaceProxy> src, SkIRect srcRect, SkIRect dstRect,
                                GrSamplerState::Filter filterMode);
```

将 src 的 srcRect 区域缩放拷贝到当前表面的 dstRect 区域。

**流程**：
1. `ASSERT_SINGLE_OWNER` + `RETURN_NULLPTR_IF_ABANDONED` + `validate()`
2. 检查 `this->asSurfaceProxy()->framebufferOnly()` → 是则返回 nullptr
3. `caps->canCopySurface(dstProxy, dstRect, src, srcRect)` → 不可拷贝返回 nullptr
4. **Linear filter + approx-sized 边界检查**（`filter == kLinear` 且 `!src->isFunctionallyExact()`）：
   - 计算 `upscalingXAtApproxEdge`：
     - `SK_USE_SAFE_INSET_FOR_TEXTURE_SAMPLING` 模式：`dstRect.width() >= srcRect.width()` 且 `srcRect.fRight == src->width()` 且 `srcRect.fRight < backingStoreDimensions().width()`
     - 默认模式：`dstRect.width() > srcRect.width()`（严格放大才算）且同上后两个条件
   - `upscalingYAtApproxEdge` 同理
   - 任一为 true → 返回 nullptr（防止线性采样越界到未定义像素）
5. 断言 `src->backendFormat().textureType() != kExternal`（非外部纹理）
6. 断言 `src->backendFormat() == this->asSurfaceProxy()->backendFormat()`（格式匹配）
7. 调用 `drawingManager->newCopyRenderTask(dstProxyRef, dstRect, src, srcRect, filter, origin)`

### internalWritePixels(dContext, src[], numLevels, pt)

```cpp
bool internalWritePixels(GrDirectContext* dContext,
                         const GrCPixmap src[],
                         int numLevels,
                         SkIPoint pt);
```

writePixels 的核心实现，支持单级和多级 MIP 写入。

**流程**：

1. **前置断言和校验**：
   - `numLevels >= 1`，`src` 非空
   - 断言：写子区域（numLevels==1）或写 MIP 全部（pt 为零且 src[0] 大小等于 this）
   - `dContext` 非空 → 否则返回 false
   - `!dstProxy->readOnly()` → 只读返回 false
   - `src[0].colorType() != kUnknown` → 是 kUnknown 返回 false
   - `alpha_types_compatible(src[0].alphaType(), this->colorInfo().alphaType())` → 不兼容返回 false
   - `!dstProxy->framebufferOnly()` → framebufferOnly 返回 false
2. 实例化 dstProxy：`dstProxy->instantiate(resourceProvider)` → 失败返回 false
3. 获取 `dstSurface = dstProxy->peekSurface()`
4. **计算颜色转换标志**：`SkColorSpaceXformSteps{src[0].colorInfo(), this->colorInfo()}.fFlags`
   - `unpremul`、`needColorConversion`、`premul`
5. **Canvas2D 快速路径判断**：同时满足以下条件时启用：
   - `!caps->avoidWritePixelsFastPath()`
   - `premul` 为 true
   - `!needColorConversion`
   - src colorType 为 RGBA_8888 或 BGRA_8888
   - `this->asFillContext()` 非空（当前 context 是 SurfaceFillContext 或其子类）
   - dst colorType 为 RGBA_8888 或 BGRA_8888
   - RGBA_8888 默认 backend format（kNo renderable）有效
   - `validPMUPMConversionExists()` 返回 true
6. 再次 `RETURN_FALSE_IF_ABANDONED`

7. **绘制路径**（`!surfaceSupportsWritePixels` 或 `canvas2DFastPath`，且 `numLevels == 1`）：
   1. 确定临时 proxy 的 colorInfo 和 format：
      - canvas2DFastPath → `tempColorInfo = {RGBA_8888, kUnpremul, this->colorSpace()}`，`format = rgbaDefaultFormat`
      - 否则 → `tempColorInfo = this->colorInfo()`，`format = dstProxy->backendFormat().makeTexture2D()`（无效则返回 false），`tempReadSwizzle = this->readSwizzle()`
   2. 确定 tempOrigin：`this->asFillContext()` 有效 → `kTopLeft`，否则 → `this->origin()`
   3. 创建临时 texture proxy：`proxyProvider->createProxy(format, src[0].dims, kNo renderable, 1, kNo mipmap, kApprox, kYes budgeted, kNo protected)`
   4. 创建临时 `SurfaceContext(dContext, tempView, tempColorInfo)`
   5. canvas2DFastPath 时：将 src 的 colorType 强制视为 RGBA_8888（BGRA 数据写入后 R/B 通道互换，后续绘制时通过 swizzle 校正）
   6. 递归 `tempCtx.writePixels(dContext, srcBase, {0, 0})` 写入临时 proxy → 失败返回 false
   7. **如果 asFillContext() 有效**（可以绘制）：
      - canvas2DFastPath → `createUPMToPMEffect(GrTextureEffect::Make(tempView, alphaType))`；原始 src 为 BGRA 时加 `SwizzleOutput(BGRA)`
      - 否则 → `GrTextureEffect::Make(tempView, alphaType)`
      - `this->asFillContext()->fillRectToRectWithFP(srcRect, dstRect, fp)`
   8. **否则**（只能拷贝）：
      - `this->copy(tempProxy, srcRect, dstPoint)` → 失败返回 false

8. **直接写入路径**（surfaceSupportsWritePixels 为 true 且非 canvas2DFastPath，或 numLevels > 1）：
   1. 查询 `caps->supportedWritePixelsColorType(dstColorType, backendFormat, srcColorType)` → `allowedColorType`
   2. 计算 `flip = (origin == kBottomLeft)`
   3. 判断 `convertAll`：premul || unpremul || needColorConversion || flip || (srcColorType != allowedColorType)
   4. 判断 `mustBeTight`：`!caps->writePixelsRowBytesSupport()`
   5. 计算 tmpSize：遍历各级，如果 `convertAll` 或（`mustBeTight` 且 rowBytes 非 minRowBytes）→ 累加该级转换后的数据大小
   6. 如果 tmpSize > 0 → 分配临时 buffer `SkData::MakeUninitialized(tmpSize)`
   7. 遍历各级构建 `srcLevels[i]`：
      - 需要转换 → 创建 tmpPM，`GrConvertPixels(tmpPM, src[i], flip)`，`srcLevels[i] = {tmpPM.addr(), tmpRB, tmpData}`
      - 不需要转换 → `srcLevels[i] = {src[i].addr(), src[i].rowBytes(), src[i].pixelStorage()}`，更新 `ownAllStorage`
   8. flip 时调整 `pt.fY = dstSurface->height() - pt.fY - src[0].height()`
   9. 调用 `drawingManager->newWritePixelsTask(dstProxy, rect, allowedColorType, dstColorType, srcLevels, numLevels)` → 失败返回 false
   10. `numLevels > 1` → `dstProxy->asTextureProxy()->markMipmapsClean()`
   11. `!ownAllStorage` → `dContext->priv().flushSurface(dstProxy)` 确保非自有像素数据在返回前上传到 GPU

---

## 6. 辅助函数

### alpha_types_compatible(srcAlphaType, dstAlphaType)（文件静态）

```cpp
static bool alpha_types_compatible(SkAlphaType srcAlphaType, SkAlphaType dstAlphaType);
```

判断 src 和 dst 的 alphaType 是否兼容：两者要么都是 `kUnknown`，要么都不是 `kUnknown`。

---

## 7. 关键设计决策

- **只持有 readView**：SurfaceContext 是只读基类，只需 `fReadView`。`fWriteView` 由 `SurfaceFillContext` 添加。这保证了纯读取场景（如 readPixels）不会意外获取写入能力
- **Canvas2D 快速路径**：针对 HTML Canvas `getImageData`/`putImageData` 的 premul/unpremul 需求，利用 GPU 着色器（`PMToUPM` / `UPMToPM` effect）实现高效转换，避免 CPU 逐像素循环。读取时用 `PMToUPM`（premul→unpremul），写入时用 `UPMToPM`（unpremul→premul）
- **渐进式缩放**：`rescaleInto` 使用 `do...while` 循环逐步缩放，`kRepeatedCubic` 模式下每步最多 2x。这比一步到位的插值质量更好，但 `kNearest`/`kLinear` 模式一步完成
- **copyScaled 优先于 draw**：`rescaleInto` 中对于 kNearest/kLinear 模式优先尝试 `copyScaled`（hardware blit），只在需要颜色空间转换、origin 不匹配或 blit 失败时才退回到 FP draw。hardware blit 通常比着色器绘制更快
- **Linear filter approx-fit 边界保护**：`copyScaled` 检查线性采样时是否会越过 approx-fit 纹理的逻辑边界。如果 upscaling 且 srcRect 边缘恰好在逻辑尺寸处但 backing store 更大，线性采样会读取到逻辑边界外的未定义像素，因此返回 nullptr 拒绝此操作
- **异步读取两路径**：`asyncReadPixels` 优先使用 `transferPixels`（GPU→buffer 异步传输，通过 finish callback 通知完成），失败时退回到同步 `readPixels` + CPU copy
- **PixelTransferResult.fPixelConverter**：当 GPU 读取的颜色类型与请求不同，或需要 Y 轴 flip 时，设置转换回调延迟到数据可用时执行，避免在传输阶段进行不必要的格式转换
- **writePixels 绘制路径 origin 选择**：`internalWritePixels` 的绘制路径中，如果当前 context 是 `SurfaceFillContext`（可以绘制），临时 proxy 使用 `kTopLeft` origin（写入更高效）；否则使用 `this->origin()`（拷贝要求 origin 匹配）

---

## 8. 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/SurfaceFillContext.h/.cpp` | 派生类 | 添加写入视图、OpsTask 管理、清除和 FP 填充能力 |
| `src/gpu/ganesh/SurfaceDrawContext.h/.cpp` | 派生类（间接） | 完整绘制功能（clip、stencil、AA） |
| `src/gpu/ganesh/GrSurfaceProxy.h/.cpp` | 成员 | 表面资源的延迟创建代理 |
| `src/gpu/ganesh/GrSurfaceProxyView.h` | 成员 | 表面视图封装（proxy + origin + swizzle） |
| `src/gpu/ganesh/GrColorInfo.h` | 成员 | 颜色类型、alpha 类型、色彩空间 |
| `src/gpu/ganesh/GrDrawingManager.h/.cpp` | 依赖 | 管理 render task 创建和调度 |
| `src/gpu/ganesh/GrCaps.h` | 依赖 | 查询 GPU 能力（读写支持、格式兼容、传输对齐等） |
| `src/gpu/ganesh/GrGpu.h` | 依赖 | 底层 GPU 操作（readPixels 直接读取路径） |
| `src/gpu/ganesh/effects/GrTextureEffect.h` | 依赖 | 纹理采样着色器 |
| `src/gpu/ganesh/effects/GrBicubicEffect.h` | 依赖 | CatmullRom 立方插值着色器（rescaleInto 使用） |
| `src/gpu/ganesh/GrColorSpaceXform.h` | 依赖 | 色彩空间转换 |
| `src/gpu/ganesh/GrClientMappedBufferManager.h` | 依赖 | 管理异步传输缓冲区的生命周期 |
| `src/gpu/AsyncReadTypes.h` | 依赖 | `TAsyncReadResult` 模板，异步读取结果封装 |
| `src/core/SkColorSpaceXformSteps.h` | 依赖 | 计算颜色转换所需步骤的标志位 |
| `src/core/SkYUVMath.h` | 依赖 | RGB→YUV 颜色矩阵计算 |
