# GrAtlasManager

> 源文件
> - `src/gpu/ganesh/text/GrAtlasManager.h`
> - `src/gpu/ganesh/text/GrAtlasManager.cpp`

## 概述

`GrAtlasManager` 是 Ganesh 文本渲染系统中的核心 Atlas(纹理图集)管理器,负责管理 `GrDrawOpAtlas` 的生命周期和访问控制。该类仅在 flush 阶段可用,通过 `GrOpFlushState` 访问。它处理字形(Glyph)向 GPU 纹理图集的添加、格式转换、内存管理和同步,支持多种 MaskFormat(A8、A565、ARGB),并提供图集代际(generation)跟踪以检测纹理内容变化。作为 `GrOnFlushCallbackObject`,它参与 GPU 刷新生命周期,确保字形数据在渲染前正确上传。

## 架构位置

`GrAtlasManager` 位于 Skia GPU 文本渲染管线中的资源管理层:

```
Skia 文本渲染架构
├── 文本布局层
│   └── SkStrikeSpec (字形规格)
├── GPU 文本处理层
│   ├── StrikeCache (字形缓存)
│   └── GlyphData (字形数据)
├── GPU 资源管理层
│   ├── GrAtlasManager (Atlas 管理器) ← 当前类
│   ├── GrDrawOpAtlas (纹理图集实现)
│   └── GrAtlasGenerationCounter (代际计数器)
├── GPU 操作调度层
│   ├── GrOnFlushResourceProvider (flush 资源提供者)
│   └── GrDeferredUploadTarget (延迟上传目标)
└── GPU 后端层
    └── GrProxyProvider (纹理代理提供者)
```

该类是文本数据从 CPU 缓存到 GPU 纹理的桥梁。

## 主要类与结构体

### 继承关系

| 类名 | 关系 | 说明 |
|------|------|------|
| `GrOnFlushCallbackObject` | 父类 | 提供 flush 生命周期回调 |
| `GrAtlasGenerationCounter` | 父类 | 提供图集代际跟踪功能 |
| `GrAtlasManager` | 当前类 | 文本 Atlas 管理器实现 |

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fAtlases` | `std::unique_ptr<GrDrawOpAtlas>[3]` | 三种 MaskFormat 的图集数组(A8/A565/ARGB) |
| `fProxyProvider` | `GrProxyProvider*` | 纹理代理提供者 |
| `fCaps` | `sk_sp<const GrCaps>` | GPU 能力查询接口 |
| `fAtlasConfig` | `GrDrawOpAtlasConfig` | 图集配置(尺寸、内存限制) |
| `fAllowMultitexturing` | `GrDrawOpAtlas::AllowMultitexturing` | 是否允许多纹理图集 |
| `fSupportBilerpAtlas` | `bool` | 是否支持双线性插值图集(需要额外 padding) |

## 公共 API 函数

### 图集访问

```cpp
const GrSurfaceProxyView* getViews(skgpu::MaskFormat format,
                                    unsigned int* numActiveProxies);
```
获取指定格式图集的纹理视图,返回活动纹理页数。**必须在使用其他 API 前调用**,触发延迟初始化。

### 字形操作

```cpp
bool hasGlyph(skgpu::MaskFormat, const skgpu::ganesh::GlyphEntry&);
```
检查字形是否已存在于图集中(通过 PlotLocator 检查)。

```cpp
GrDrawOpAtlas::ErrorCode addGlyphToAtlas(const SkGlyph&,
                                          skgpu::ganesh::GlyphEntry*,
                                          int srcPadding,
                                          GrResourceProvider*,
                                          GrDeferredUploadTarget*);
```
将字形图像添加到图集,支持三种 padding 模式:
- `0`: 直接掩码(无 padding,但 bilerp 模式会强制添加 1 像素 padding)
- `1`: 变换掩码(1 像素 padding)
- `SK_DistanceFieldInset`: 有符号距离场(padding 内置于图像中)

```cpp
void addGlyphToBulkAndSetUseToken(GrBulkUsePlotUpdater*,
                                  skgpu::MaskFormat,
                                  const skgpu::ganesh::GlyphEntry&,
                                  skgpu::Token);
```
批量更新字形的使用令牌(use token),防止图集过早驱逐活跃字形。

### 通用添加接口

```cpp
GrDrawOpAtlas::ErrorCode addToAtlas(GrResourceProvider*,
                                    GrDeferredUploadTarget*,
                                    skgpu::MaskFormat,
                                    int width, int height,
                                    const void* image,
                                    GrAtlasLocator*);
```
底层添加接口,直接将像素数据添加到图集(由 `addGlyphToAtlas` 调用)。

### 代际跟踪

```cpp
uint64_t atlasGeneration(skgpu::MaskFormat format) const;
```
返回图集代际号,每次内容被驱逐时递增,用于检测图集失效。

### 生命周期管理

```cpp
void freeAll();
```
释放所有图集资源。

## 内部实现细节

### 格式解析与回退

```cpp
skgpu::MaskFormat resolveMaskFormat(skgpu::MaskFormat format) const {
    if (skgpu::MaskFormat::kA565 == format &&
        !fProxyProvider->caps()->getDefaultBackendFormat(GrColorType::kBGR_565,
                                                         GrRenderable::kNo).isValid()) {
        format = skgpu::MaskFormat::kARGB;  // Metal on macOS 不支持 565
    }
    return format;
}
```

### 字形图像打包

`get_packed_glyph_image` 函数处理多种格式转换:

1. **位图展开** (BW → A8/A565):
   ```cpp
   expand_bits(dst, src, width, height, dstRB, srcRB);
   // 将紧凑的位图展开为字节/字(每像素一个单元)
   ```

2. **565 → ARGB 转换** (macOS Metal 回退):
   ```cpp
   if (maskFormat == MaskFormat::kA565 && expectedMaskFormat == MaskFormat::kARGB) {
       // 使用 SkMasks 解析 RGB565 并重组为 RGBA8888
       // 处理 BGR/RGB 字节序差异(Windows vs 其他平台)
   }
   ```

3. **行字节对齐**:
   处理源和目标行字节不一致的情况,逐行复制。

### Padding 处理

```cpp
void* dataPtr = storage.get();
if (padding > 0) {
    sk_bzero(dataPtr, size);                      // 清零整个缓冲区
    dataPtr = (char*)(dataPtr) + rowBytes + bytesPerPixel;  // 偏移到中心
}
get_packed_glyph_image(skGlyph, rowBytes, expectedMaskFormat, dataPtr);
glyph->fAtlasLocator.insetSrc(srcPadding);  // 记录实际图像区域
```

### 图集延迟初始化

```cpp
bool initAtlas(MaskFormat format) {
    if (fAtlases[index] == nullptr) {
        SkISize atlasDimensions = fAtlasConfig.atlasDimensions(format);
        SkISize plotDimensions = fAtlasConfig.plotDimensions(format);
        fAtlases[index] = GrDrawOpAtlas::Make(
            fProxyProvider, backendFormat, colorType, bytesPerPixel,
            atlasDimensions, plotDimensions, this, fAllowMultitexturing,
            /*label=*/"TextAtlas");
    }
}
```

### Flush 生命周期回调

```cpp
bool preFlush(GrOnFlushResourceProvider* onFlushRP) override {
    for (int i = 0; i < skgpu::kMaskFormatCount; ++i) {
        if (fAtlases[i]) {
            fAtlases[i]->instantiate(onFlushRP);  // 实例化纹理
        }
    }
}

void postFlush(skgpu::Token startTokenForNextFlush) override {
    for (int i = 0; i < skgpu::kMaskFormatCount; ++i) {
        if (fAtlases[i]) {
            fAtlases[i]->compact(startTokenForNextFlush);  // 压缩释放未使用区域
        }
    }
}
```

## 依赖关系

### 依赖的模块

| 模块 | 依赖关系 | 说明 |
|------|---------|------|
| `GrDrawOpAtlas` | 强依赖 | 底层纹理图集实现 |
| `GrProxyProvider` | 强依赖 | 创建和管理纹理代理 |
| `GrCaps` | 强依赖 | 查询 GPU 格式支持和能力 |
| `GrResourceProvider` | 使用依赖 | 提供 GPU 资源创建接口 |
| `GrDeferredUploadTarget` | 使用依赖 | 延迟上传机制 |
| `sktext::gpu::GlyphUtils` | 辅助依赖 | 字形格式转换工具 |
| `SkDistanceFieldGen` | 条件依赖 | SDF 文本常量(如 `SK_DistanceFieldInset`) |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `StrikeCache` | 通过 GrAtlasManager 将字形上传到 GPU |
| `GrTextBlob` | 获取图集视图进行文本渲染 |
| `GrOpsRenderPass` | 绑定图集纹理 |
| `GrOpFlushState` | 在 flush 时访问 GrAtlasManager |

## 设计模式与设计决策

### 单例模式变体

通过 `GrOnFlushResourceProvider` 提供全局访问,每个上下文一个实例,避免重复创建。

### 延迟初始化

图集仅在首次 `getViews` 调用时创建,避免未使用格式的资源浪费:
```cpp
if (this->initAtlas(format)) {  // 延迟创建
    *numActiveProxies = this->getAtlas(format)->numActivePages();
}
```

### 格式适配策略

自动将不支持的格式(如 Metal 的 565)回退到支持的格式(ARGB),在 `resolveMaskFormat` 和 `get_packed_glyph_image` 中协同处理。

### 批量令牌更新

使用 `GrBulkUsePlotUpdater` 批量更新多个字形的使用令牌,减少图集查找开销:
```cpp
void addGlyphToBulkAndSetUseToken(GrBulkUsePlotUpdater* updater, ...) {
    if (updater->add(glyph.fAtlasLocator)) {  // 去重
        this->getAtlas(format)->setLastUseToken(...);
    }
}
```

### 持久化回调对象

```cpp
bool retainOnFreeGpuResources() override { return true; }
```
图集缓存在 `freeGpuResources` 后仍保留,避免重新上传常用字形。

## 性能考量

### 内存分配优化

1. **栈分配缓冲区**:
   ```cpp
   SkAutoSMalloc<1024> storage(size);  // 小于 1KB 使用栈,否则堆分配
   ```

2. **零拷贝路径**:
   当源行字节等于目标行字节时,使用单次 `memcpy`:
   ```cpp
   if (srcRB == dstRB) {
       memcpy(dst, src, dstRB * height);
   }
   ```

### 图集配置

`GrDrawOpAtlasConfig` 根据总内存限制和格式动态调整图集/Plot 尺寸:
- **A8 格式**: 最大图集(文本最常用)
- **ARGB 格式**: 4 倍内存消耗,通常更小图集

### Padding 策略

- **双线性插值**: 强制 1 像素 padding 避免采样伪影
- **SDF 文本**: padding 内置于距离场数据,节省图集空间

### 代际跟踪

通过单调递增的代际号快速检测图集内容变化,避免遍历所有字形:
```cpp
uint64_t cachedGen = ...;
if (cachedGen != atlasGeneration(format)) {
    // 重新上传或重新绘制
}
```

### 格式转换缓存

565 → ARGB 转换仅在必要时触发,转换后的数据直接上传到图集,无需二次处理。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrDrawOpAtlas.h` | 依赖 | 底层纹理图集实现 |
| `src/gpu/ganesh/text/GlyphData.h` | 协作 | 字形数据结构(`GlyphEntry`) |
| `src/text/gpu/StrikeCache.h` | 使用者 | 字形缓存,调用图集添加 |
| `src/gpu/ganesh/GrOnFlushResourceProvider.h` | 协作 | Flush 时资源提供 |
| `src/gpu/ganesh/GrProxyProvider.h` | 依赖 | 纹理代理管理 |
| `src/gpu/ganesh/GrCaps.h` | 依赖 | GPU 能力查询 |
| `src/text/gpu/GlyphUtils.h` | 工具 | 字形格式转换 |
| `src/core/SkDistanceFieldGen.h` | 工具 | SDF 文本常量 |
| `src/gpu/MaskFormat.h` | 类型 | MaskFormat 枚举定义 |
| `src/gpu/ganesh/GrAtlasLocator.h` | 类型 | 图集位置定位器 |
