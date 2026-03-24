# PathAtlas

> 源文件
> - src/gpu/graphite/PathAtlas.h
> - src/gpu/graphite/PathAtlas.cpp

## 概述

`PathAtlas` 是 Skia Graphite 渲染引擎中用于管理路径覆盖率遮罩（coverage mask）图集纹理的抽象基类。它负责将复杂路径的抗锯齿遮罩渲染到共享的图集纹理中，提供高效的路径绘制能力。

与 `DrawAtlas`（用于文本字形）不同，`PathAtlas` 的内容被视为瞬态的：图集区域仅在采样它们的渲染过程范围内有效。大多数子类不支持部分驱逐和重用，一旦图集纹理填满，所有子分配必须在重用前失效。

该类不规定图集内容如何上传到 GPU，具体的任务机制由子类定义（如光栅化、计算着色器等）。

## 架构位置

```
Shape (路径/几何)
  └── PathAtlas (图集管理器)
      ├── DrawAtlas (底层纹理分配)
      ├── CoverageMaskShape (遮罩表示)
      └── Renderer (coverageMask 渲染器)
```

`PathAtlas` 位于路径渲染管线的中间层，协调形状输入、图集分配和遮罩采样。

## 主要类与结构体

### PathAtlas

**核心职责**：
- 管理一个或多个图集纹理
- 为路径形状分配图集空间
- 调度遮罩渲染任务
- 提供遮罩采样信息

**关键成员**：

```cpp
Recorder* fRecorder;   // 拥有此图集的记录器
uint32_t fWidth = 0;   // 图集宽度（2的幂次）
uint32_t fHeight = 0;  // 图集高度（2的幂次）
```

### MaskAndOrigin

```cpp
using MaskAndOrigin = std::pair<CoverageMaskShape, SkIPoint>;
```

**用途**：返回遮罩形状和设备空间原点的配对

**组成**：
- `CoverageMaskShape`：包含纹理代理、UV坐标、遮罩尺寸等
- `SkIPoint`：遮罩应绘制的设备空间原点（整数平移）

### DrawAtlasMgr

嵌套类，封装 `DrawAtlas` 和缓存操作：

```cpp
class DrawAtlasMgr : public DrawAtlas::GenerationCounter,
                     public DrawAtlas::PlotEvictionCallback {
protected:
    std::unique_ptr<DrawAtlas> fDrawAtlas;

private:
    ShapeCache fShapeCache;              // UniqueKey → AtlasLocator 映射
    SkTDArray<ShapeKeyList> fKeyLists;   // 每个 Plot 的键列表
};
```

**职责**：
- 管理 `DrawAtlas` 实例
- 维护形状缓存（避免重复渲染）
- 处理 Plot 驱逐时的缓存失效

### ShapeCache

```cpp
using ShapeCache = skia_private::THashMap<UniqueKey, DrawAtlas::AtlasLocator, UniqueKeyHash>;
```

**用途**：根据形状的唯一键快速查找其在图集中的位置

**键生成**：`GeneratePathMaskKey(shape, transform, stroke, origin, size)`

### ShapeKeyList

```cpp
struct ShapeKeyEntry {
    UniqueKey fKey;
    SK_DECLARE_INTERNAL_LLIST_INTERFACE(ShapeKeyEntry);
};
using ShapeKeyList = SkTInternalLList<ShapeKeyEntry>;
```

**用途**：存储每个 Plot 中的形状键，用于驱逐时批量删除缓存条目

## 公共 API 函数

### 构造函数

```cpp
PathAtlas(Recorder* recorder, uint32_t requestedWidth, uint32_t requestedHeight);
```

**初始化逻辑**：
```cpp
int maxTextureSize = std::max(caps->maxPathAtlasTextureSize(), kMinAtlasTextureSize);
maxTextureSize = std::min(maxTextureSize, caps->maxTextureSize());

fWidth = SkPrevPow2(std::min<uint32_t>(requestedWidth, maxTextureSize));
fHeight = SkPrevPow2(std::min<uint32_t>(requestedHeight, maxTextureSize));
```

**关键点**：
- 尊重设备的最大纹理尺寸
- 向下取整到 2 的幂次（`SkPrevPow2`）
- 最小尺寸为 512（`kMinAtlasTextureSize`）

### addShape

```cpp
std::pair<const Renderer*, std::optional<MaskAndOrigin>> addShape(
    const Rect& transformedShapeBounds,
    const Shape& shape,
    const Transform& localToDevice,
    const SkStrokeRec& style);
```

**功能**：搜索图集中的空位，提交遮罩绘制

**参数说明**：
- `transformedShapeBounds`：裁剪后的形状边界（设备空间）
- `shape`：要渲染的形状
- `localToDevice`：本地到设备的变换
- `style`：描边样式（或填充）

**返回值**：
- `Renderer*`：应使用的渲染器（`coverageMask`）
- `std::optional<MaskAndOrigin>`：成功时包含遮罩信息，失败时为 `std::nullopt`

**核心流程**：

1. **处理空遮罩**：
   ```cpp
   const bool emptyMask = transformedShapeBounds.isEmptyNegativeOrNaN();
   ```
   完全裁剪的形状可能仍因反向填充产生覆盖率，返回空遮罩由 `CoverageMaskRenderStep` 处理。

2. **计算遮罩边界**：
   ```cpp
   Rect maskBounds = transformedShapeBounds.makeRoundOut();
   maskInfo.fMaskSize = emptyMask ? skvx::half2(0) : skvx::cast<uint16_t>(maskBounds.size());
   ```

3. **计算裁剪偏移**：
   ```cpp
   skvx::float2 clippedMaskOrigin = maskBounds.topLeft() - shapeDevBounds.topLeft();
   ```
   用于区分相同尺寸但不同裁剪的遮罩。

4. **调用子类实现**：
   ```cpp
   sk_sp<TextureProxy> atlasProxy = this->onAddShape(...);
   ```

5. **构造返回值**：
   ```cpp
   CoverageMaskShape(shape, std::move(atlasProxy), localToDevice.inverse(), maskInfo)
   ```

### isSuitableForAtlasing

```cpp
virtual bool isSuitableForAtlasing(const Rect& transformedShapeBounds,
                                   const Rect& clipBounds) const {
    return true;
}
```

**功能**：判断路径是否适合图集化

**默认实现**：总是返回 `true`，子类可重写实现启发式策略

**常见策略**：
- 过大的路径不适合（占用太多图集空间）
- 过小的路径可能直接绘制更高效

## 内部实现细节

### 填充策略

`addShape` 将形状外扩 1 像素的填充：

```cpp
static constexpr int kEntryPadding = 1;
```

**原因**：
- 线性过滤时防止采样到相邻条目
- UV 原点考虑填充，遮罩尺寸不包括填充
- 子类在 `onAddShape` 中假设已计入填充

### 变换处理

形状绘制时应用 `localToDevice` 的线性部分（缩放、旋转、倾斜）：

```cpp
// 通过反向平移保持子像素精度
translate(shape, -roundedMaskBounds.topLeft());
```

**效果**：
- 未裁剪形状：平移回原点，保留子像素偏移
- 裁剪形状：可见部分居中，不可见部分被裁剪

### DrawAtlasMgr 工作流

#### 添加条目（带缓存）

```cpp
sk_sp<TextureProxy> DrawAtlasMgr::findOrCreateEntry(...) {
    UniqueKey maskKey = GeneratePathMaskKey(...);
    if (DrawAtlas::AtlasLocator* cachedLocator = fShapeCache.find(maskKey)) {
        // 缓存命中，更新使用时间戳
        fDrawAtlas->setLastUseToken(*cachedLocator, ...);
        return fDrawAtlas->getProxies()[cachedLocator->pageIndex()];
    }

    // 缓存未命中，添加新条目
    sk_sp<TextureProxy> proxy = this->addToAtlas(...);
    fShapeCache.set(maskKey, locator);
    fKeyLists[index].addToTail(new ShapeKeyEntry{maskKey});
    return proxy;
}
```

#### 添加条目（无缓存）

```cpp
sk_sp<TextureProxy> DrawAtlasMgr::addToAtlas(...) {
    // 外扩边界（包括填充）
    SkIRect iAtlasBounds = iShapeBounds.makeOutset(kEntryPadding, kEntryPadding);

    // 在 DrawAtlas 中请求空间
    ErrorCode errorCode = fDrawAtlas->addRect(..., &locator);
    if (errorCode != kSucceeded) {
        return nullptr;
    }

    // 调用子类的渲染逻辑
    if (!this->onAddToAtlas(shape, localToDevice, strokeRec, ...)) {
        return nullptr;
    }

    return fDrawAtlas->getProxies()[locator->pageIndex()];
}
```

#### Plot 驱逐处理

```cpp
void DrawAtlasMgr::evict(DrawAtlas::PlotLocator plotLocator) {
    uint32_t index = fDrawAtlas->getListIndex(plotLocator);
    ShapeKeyList::Iter iter;
    iter.init(fKeyLists[index], ...);

    while (ShapeKeyEntry* currEntry = iter.get()) {
        iter.next();
        fShapeCache.remove(currEntry->fKey);   // 从缓存移除
        fKeyLists[index].remove(currEntry);     // 从列表移除
        delete currEntry;
    }
}
```

**原理**：
- 每个 Plot 维护其包含的形状键列表
- Plot 被驱逐时，遍历列表批量删除缓存条目
- 确保缓存与图集状态一致

## 依赖关系

### 核心依赖

| 依赖项 | 作用 |
|--------|------|
| `DrawAtlas` | 底层纹理分配和管理 |
| `CoverageMaskShape` | 遮罩的几何表示 |
| `Shape` | 输入路径/几何 |
| `Transform` | 几何变换 |
| `Renderer` | 渲染器（coverageMask） |

### 工具类

| 类型 | 用途 |
|------|------|
| `GeneratePathMaskKey` | 生成形状的唯一键 |
| `SkTInternalLList` | 侵入式链表 |
| `skia_private::THashMap` | 哈希表 |

## 设计模式与设计决策

### 1. 模板方法模式

`PathAtlas::addShape` 定义算法骨架，`onAddShape` 由子类实现：

```cpp
virtual sk_sp<TextureProxy> onAddShape(...) = 0;
```

**子类实现**：
- `RasterPathAtlas`：CPU 光栅化
- `ComputePathAtlas`：GPU 计算着色器
- `TessellationPathAtlas`：GPU 曲面细分

### 2. 策略模式

不同的图集实现使用不同的渲染策略，但共享相同的接口。

### 3. 享元模式

通过缓存避免重复渲染相同的形状：

```cpp
ShapeCache fShapeCache;  // 共享遮罩数据
```

### 4. 观察者模式

`DrawAtlasMgr` 实现 `PlotEvictionCallback`，在 Plot 驱逐时收到通知：

```cpp
class DrawAtlasMgr : public DrawAtlas::PlotEvictionCallback {
    void evict(DrawAtlas::PlotLocator) override;
};
```

### 5. RAII 资源管理

使用智能指针管理纹理代理生命周期：

```cpp
sk_sp<TextureProxy> atlasProxy = ...;
```

## 性能考量

### 图集尺寸优化

1. **2 的幂次尺寸**：`SkPrevPow2` 确保纹理尺寸对 GPU 友好
2. **设备限制尊重**：不超过 `maxTextureSize`
3. **最小尺寸保证**：至少 512×512，避免过小图集频繁重建

### 缓存效率

1. **哈希表查找**：O(1) 平均时间复杂度
2. **键生成优化**：`GeneratePathMaskKey` 包含足够信息区分形状
3. **批量驱逐**：使用链表快速遍历并删除 Plot 的所有条目

### 内存管理

1. **瞬态内容**：图集内容不持久化，减少内存压力
2. **紧凑驱逐**：`compact` 方法移除未使用的 Plot
3. **全部驱逐**：`evictAll` 快速清空图集

### 填充优化

1 像素填充避免边缘伪影，但增加内存占用：

```cpp
// 实际分配：(width+2) × (height+2)
// 有效区域：width × height
```

**权衡**：质量 vs. 内存

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `src/gpu/graphite/DrawAtlas.h` | 底层图集纹理管理 |
| `src/gpu/graphite/geom/CoverageMaskShape.h` | 覆盖率遮罩形状 |
| `src/gpu/graphite/geom/Shape.h` | 几何形状 |
| `src/gpu/graphite/geom/Transform.h` | 几何变换 |
| `src/gpu/graphite/Renderer.h` | 渲染器 |
| `src/gpu/graphite/RasterPathUtils.h` | 路径光栅化工具（包含 `GeneratePathMaskKey`） |
| `src/gpu/graphite/Caps.h` | 设备能力 |
| `src/gpu/graphite/Recorder.h` | 记录器 |
| `src/core/SkStrokeRec.h` | 描边记录 |
| `include/core/SkRect.h` | 矩形 |
