# RasterPathAtlas

> 源文件
> - src/gpu/graphite/RasterPathAtlas.h
> - src/gpu/graphite/RasterPathAtlas.cpp

## 概述

`RasterPathAtlas` 是 Graphite 渲染引擎中用于在 CPU 上光栅化路径覆盖掩码的图集管理类。它继承自 `PathAtlas`，通过软件光栅化将复杂路径转换为 Alpha 掩码纹理，并将这些掩码打包到纹理图集中以提高 GPU 渲染效率。

该类的核心功能包括：
1. **CPU 路径光栅化**：使用 `RasterMaskHelper` 在 CPU 端生成高质量的抗锯齿掩码
2. **多图集策略**：维护三种不同的图集管理器（缓存图集、小路径图集、非缓存图集）以优化不同类型路径的存储
3. **智能缓存降级**：当图集空间不足时，降级到 `ProxyCache` 为单个路径创建独立纹理
4. **批量上传**：通过 `recordUploads` 收集所有待上传的掩码数据，在合适的时机批量提交到 GPU

这种混合策略在处理大量小路径时非常高效，同时为特殊情况（如超大路径、易变路径）提供了回退机制。

## 架构位置

`RasterPathAtlas` 位于 Graphite 的路径渲染子系统中：

```
skgpu::graphite 命名空间
├── PathAtlas (路径图集基类)
│   └── RasterPathAtlas (CPU 光栅化图集 - 本类)
│       ├── RasterAtlasMgr (图集管理器)
│       │   ├── DrawAtlasMgr (基类 - 提供图集分配逻辑)
│       │   └── DrawAtlas (底层图集 - 纹理和布局管理)
│       ├── RasterMaskHelper (光栅化辅助类)
│       └── ProxyCache (代理缓存 - 降级回退)
├── AtlasProvider (图集提供者 - 创建和管理图集)
└── Recorder (记录器 - 拥有图集和缓存)
```

`RasterPathAtlas` 与 GPU 路径图集（`ComputePathAtlas`）形成互补，分别适用于不同的硬件能力和路径类型。

## 主要类与结构体

### RasterPathAtlas 类

```cpp
class RasterPathAtlas : public PathAtlas {
public:
    explicit RasterPathAtlas(Recorder* recorder);
    ~RasterPathAtlas() override {}

    void recordUploads(DrawContext*);
    void compact();
    void freeGpuResources();
    void evictAtlases();

protected:
    sk_sp<TextureProxy> onAddShape(...) override;

private:
    RasterAtlasMgr fCachedAtlasMgr;      // 主缓存图集
    RasterAtlasMgr fSmallPathAtlasMgr;    // 小路径专用图集
    RasterAtlasMgr fUncachedAtlasMgr;     // 非缓存临时图集
};
```

**三种图集管理器的配置：**
- `fCachedAtlasMgr`: 2048×2048，plot 大小 1024×1024，用于大路径缓存
- `fSmallPathAtlasMgr`: 至少 2048×2048，plot 大小 512×256，用于小路径（≤162 像素）
- `fUncachedAtlasMgr`: 2048×2048，plot 大小 1024×1024，用于易变路径（不缓存）

### RasterAtlasMgr 嵌套类

```cpp
class RasterAtlasMgr : public PathAtlas::DrawAtlasMgr {
public:
    RasterAtlasMgr(size_t width, size_t height,
                   size_t plotWidth, size_t plotHeight,
                   const Caps* caps);

protected:
    bool onAddToAtlas(const Shape&,
                      const Transform& localToDevice,
                      const SkStrokeRec&,
                      SkIRect shapeBounds,
                      SkIVector transformedMaskOffset,
                      const DrawAtlas::AtlasLocator&) override;
};
```

继承自 `DrawAtlasMgr`，重写 `onAddToAtlas` 以实现 CPU 光栅化的具体逻辑。

## 公共 API 函数

### 构造函数

```cpp
explicit RasterPathAtlas(Recorder* recorder);
```

**功能：**创建 CPU 路径图集实例，初始化三种图集管理器。

**实现细节：**
```cpp
RasterPathAtlas::RasterPathAtlas(Recorder* recorder)
        : PathAtlas(recorder, kDefaultAtlasDim, kDefaultAtlasDim)
        , fCachedAtlasMgr(fWidth, fHeight,
                          /*plotWidth=*/fWidth/2, /*plotHeight=*/fHeight/2,
                          recorder->priv().caps())
        , fSmallPathAtlasMgr(std::max(fWidth, kSmallPathPlotWidth),
                             std::max(fHeight, kSmallPathPlotHeight),
                             kSmallPathPlotWidth, kSmallPathPlotHeight,
                             recorder->priv().caps())
        , fUncachedAtlasMgr(kUncachedAtlasDim, kUncachedAtlasDim,
                            /*plotWidth=*/kUncachedAtlasDim/2,
                            /*plotHeight=*/kUncachedAtlasDim/2,
                            recorder->priv().caps()) {}
```

小路径图集使用 `std::max` 确保至少能容纳标准尺寸的 plot。

### recordUploads

```cpp
void recordUploads(DrawContext* dc);
```

**功能：**记录所有待上传的掩码数据到绘制上下文，随后会添加到 `UploadTask`。

**实现逻辑：**
```cpp
void RasterPathAtlas::recordUploads(DrawContext* dc) {
    fCachedAtlasMgr.recordUploads(dc, fRecorder);
    fSmallPathAtlasMgr.recordUploads(dc, fRecorder);
    fUncachedAtlasMgr.recordUploads(dc, fRecorder);
}
```

按顺序处理三个图集管理器的上传任务。

### compact

```cpp
void compact();
```

**功能：**压缩图集空间，释放未使用的 plot，优化内存占用。

**典型使用场景：**
- 帧结束后清理临时数据
- 内存压力下的主动优化

### freeGpuResources

```cpp
void freeGpuResources();
```

**功能：**释放所有 GPU 资源（纹理），但保留 CPU 端的数据结构。

**用途：**
- 上下文丢失恢复
- 后台应用的资源释放

### evictAtlases

```cpp
void evictAtlases();
```

**功能：**清空所有图集，移除所有缓存的路径掩码。

**与 `freeGpuResources` 的区别：**
- `evictAtlases`: 清空缓存键和分配映射
- `freeGpuResources`: 仅释放 GPU 纹理

## 内部实现细节

### onAddShape 实现

```cpp
sk_sp<TextureProxy> RasterPathAtlas::onAddShape(
    const Shape& shape,
    const Transform& localToDevice,
    const SkStrokeRec& strokeRec,
    skvx::half2 maskOrigin,
    skvx::half2 maskSize,
    SkIVector transformedMaskOffset,
    skvx::half2* outPos);
```

**执行流程：**

**1. 缓存路径的处理：**
```cpp
if (!shape.isVolatilePath()) {
    constexpr int kMaxSmallPathSize = 162;
    if (maskSize.x() <= kMaxSmallPathSize && maskSize.y() <= kMaxSmallPathSize) {
        proxy = fSmallPathAtlasMgr.findOrCreateEntry(...);
    }
    if (!proxy) {
        proxy = fCachedAtlasMgr.findOrCreateEntry(...);
    }
}
```

- 非易变路径尝试缓存
- 小于 162 像素的路径优先使用小路径图集
- 失败则尝试主缓存图集

**2. 非缓存路径的处理：**
```cpp
if (!proxy) {
    DrawAtlas::AtlasLocator loc;
    proxy = fUncachedAtlasMgr.addToAtlas(...);
}
```

易变路径或缓存图集已满时使用非缓存图集。

**3. 降级到 ProxyCache：**
```cpp
if (proxy) {
    return proxy;
}

skgpu::UniqueKey maskKey = GeneratePathMaskKey(shape, localToDevice, strokeRec,
                                               maskOrigin, maskSize);
struct PathDrawContext {
    const Shape& fShape;
    const Transform& fLocalToDevice;
    const SkStrokeRec& fStrokeRec;
    SkIRect fShapeBounds;
    SkIVector fTransformedMaskOffset;
} context = { ... };

sk_sp<TextureProxy> cachedProxy = fRecorder->priv().proxyCache()->findOrCreateCachedProxy(
    fRecorder, maskKey, &context,
    [](const void* ctx) {
        const PathDrawContext* pdc = static_cast<const PathDrawContext*>(ctx);
        auto [bm, helper] = RasterMaskHelper::Allocate(
            pdc->fShapeBounds.size(),
            -pdc->fTransformedMaskOffset,
            kEntryPadding);
        helper.drawShape(pdc->fShape, pdc->fLocalToDevice, pdc->fStrokeRec);
        bm.setImmutable();
        return bm;
    });

*outPos = { kEntryPadding, kEntryPadding };
return cachedProxy;
```

**降级策略的关键点：**
- 为路径生成唯一键用于缓存查找
- 使用 lambda 延迟光栅化，只在缓存未命中时执行
- 创建独立纹理而非图集区域
- 位图标记为不可变以支持共享

### RasterAtlasMgr::onAddToAtlas 实现

```cpp
bool RasterPathAtlas::RasterAtlasMgr::onAddToAtlas(
    const Shape& shape,
    const Transform& localToDevice,
    const SkStrokeRec& strokeRec,
    SkIRect shapeBounds,
    SkIVector transformedMaskOffset,
    const DrawAtlas::AtlasLocator& locator) {

    SkPixmap pixmap = fDrawAtlas->prepForRender(locator, kEntryPadding);
    RasterMaskHelper helper(pixmap, -transformedMaskOffset);
    helper.drawShape(shape, localToDevice, strokeRec);

    return true;
}
```

**关键步骤：**
1. `prepForRender`: 从图集获取目标像素区域，应用填充
2. 创建 `RasterMaskHelper` 并设置偏移量
3. 直接光栅化到图集的像素缓冲区
4. 始终返回 `true`（光栅化不会失败）

**填充（kEntryPadding）的作用：**
- 避免纹理采样时的边缘伪影
- 为双线性插值提供安全边界

## 依赖关系

### 直接依赖

| 依赖项 | 类型 | 用途 |
|-------|------|------|
| `PathAtlas` | Graphite 基类 | 路径图集抽象 |
| `DrawAtlasMgr` | Graphite 管理器 | 图集分配和缓存逻辑 |
| `DrawAtlas` | Graphite 图集 | 底层纹理图集实现 |
| `RasterMaskHelper` | Graphite 工具 | CPU 光栅化辅助 |
| `ProxyCache` | Graphite 缓存 | 独立纹理缓存 |
| `Shape` | Graphite 几何 | 路径形状抽象 |
| `Transform` | Graphite 几何 | 空间变换 |
| `SkStrokeRec` | Skia 绘图 | 描边样式 |
| `Recorder` | Graphite 上下文 | 记录器上下文 |
| `DrawContext` | Graphite 上下文 | 绘制上下文 |
| `UniqueKey` | GPU 资源键 | 路径掩码键 |

### 被依赖关系

- `AtlasProvider`: 创建和管理 `RasterPathAtlas` 实例
- `PathRenderer`: 使用图集中的掩码进行路径绘制
- `RenderStep`: 路径渲染步骤中访问图集数据

## 设计模式与设计决策

### 1. 策略模式（Strategy Pattern）

三个图集管理器代表三种不同的缓存策略：
- **小路径策略**：高效打包小掩码
- **大路径策略**：标准缓存，适用于一般路径
- **易变路径策略**：不缓存，每帧重新分配

### 2. 降级策略（Fallback Strategy）

```
尝试顺序：
1. 小路径图集 (仅 ≤162px && !volatile)
2. 主缓存图集 (仅 !volatile)
3. 非缓存图集
4. ProxyCache (独立纹理)
```

**设计优势：**
- 优雅地处理图集空间耗尽
- 确保所有路径都能被渲染
- 平衡性能和内存使用

### 3. 延迟光栅化（Lazy Rasterization）

ProxyCache 的 lambda 回调实现延迟光栅化：
```cpp
[](const void* ctx) {
    // 仅在缓存未命中时执行
    auto [bm, helper] = RasterMaskHelper::Allocate(...);
    helper.drawShape(...);
    return bm;
}
```

### 4. 填充边界（Padding Boundary）

所有掩码添加 `kEntryPadding` 像素的边界：
- 避免纹理采样伪影
- 支持双线性过滤
- 简化坐标计算（outPos 始终从填充内侧开始）

### 5. 资源管理的分离关注点

```cpp
void compact();           // 压缩空间
void freeGpuResources();  // 释放 GPU 资源
void evictAtlases();      // 清空缓存
```

三个方法分别处理不同层次的资源管理，提供灵活的控制粒度。

## 性能考量

### 1. 小路径优化

**kMaxSmallPathSize = 162 像素**

**设计理由：**
- 典型文本字形的尺寸范围
- 小 plot (512×256) 可容纳更多小掩码
- 减少主图集的碎片化

**trade-off：**
- 额外的图集增加了管理开销
- 但大幅提高了小路径的缓存命中率

### 2. CPU 光栅化的开销

**何时使用 RasterPathAtlas：**
- 复杂路径（GPU 难以处理）
- 需要高质量抗锯齿
- 路径会被重复使用（缓存收益）

**性能特点：**
- CPU 光栅化阻塞录制线程
- 但生成的掩码可在多帧复用
- 批量上传减少 GPU 同步开销

### 3. 图集尺寸选择

**默认配置：**
- 主图集：2048×2048
- Plot 大小：1024×1024（主）、512×256（小）

**考虑因素：**
- 适配主流 GPU 的纹理尺寸限制
- Plot 大小影响内存浪费和分配灵活性
- 较大 plot 减少纹理切换但增加碎片

### 4. 易变路径的处理

```cpp
if (!shape.isVolatilePath()) {
    // 尝试缓存
}
```

**易变路径特征：**
- 动画路径
- 每帧不同的路径

**处理策略：**
- 跳过缓存查找，直接使用非缓存图集
- 避免缓存污染
- 非缓存图集可以整体重置

### 5. ProxyCache 作为最后防线

当所有图集都满时，降级到 ProxyCache：
- 创建独立纹理（内存成本高）
- 但保证渲染正确性
- 适用于超大路径或极端情况

**潜在问题：**
- 大量降级会导致纹理碎片化
- 独立纹理增加纹理绑定开销

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/graphite/PathAtlas.h` | 基类 | 路径图集抽象接口 |
| `src/gpu/graphite/DrawAtlas.h` | 使用 | 底层纹理图集实现 |
| `src/gpu/graphite/RasterPathUtils.h` | 使用 | CPU 光栅化工具 |
| `src/gpu/graphite/ProxyCache.h` | 使用 | 纹理代理缓存 |
| `src/gpu/graphite/AtlasProvider.h` | 被使用 | 图集提供者 |
| `src/gpu/graphite/Recorder.h` | 使用 | 记录器上下文 |
| `src/gpu/graphite/DrawContext.h` | 使用 | 绘制上下文 |
| `src/gpu/graphite/geom/Shape.h` | 使用 | 形状抽象 |
| `src/gpu/graphite/geom/Transform.h` | 使用 | 空间变换 |
| `include/core/SkStrokeRec.h` | 使用 | 描边样式 |
| `src/gpu/ResourceKey.h` | 使用 | 路径掩码键生成 |
