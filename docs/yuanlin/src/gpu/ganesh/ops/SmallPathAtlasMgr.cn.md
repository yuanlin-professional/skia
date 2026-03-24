# SmallPathAtlasMgr

> 源文件
> - `src/gpu/ganesh/ops/SmallPathAtlasMgr.h`
> - `src/gpu/ganesh/ops/SmallPathAtlasMgr.cpp`

## 概述

`SmallPathAtlasMgr` 是 Ganesh GPU 后端中管理小路径纹理图集的管理器类。该类负责在刷新时操作，管理小路径渲染器的图集，包括图集的创建、形状数据的缓存、图集空间的分配和驱逐策略。

该管理器仅在未定义 `SK_ENABLE_OPTIMIZE_SIZE` 时可用，专门服务于 `SmallPathRenderer`，实现了高效的小路径批处理渲染。

## 架构位置

```
skia/src/gpu/ganesh/ops/
  SmallPathAtlasMgr
    ├── 实现 GrOnFlushCallbackObject
    ├── 实现 GrPlotEvictionCallback
    ├── 实现 GrAtlasGenerationCounter
    ├── 使用 GrDrawOpAtlas
    └── 管理 SmallPathShapeData
```

## 主要类与结构体

### SmallPathAtlasMgr

**继承关系：**
- `GrOnFlushCallbackObject`：刷新回调
- `GrPlotEvictionCallback`：图集驱逐回调
- `GrAtlasGenerationCounter`：图集代计数器

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fAtlas` | `std::unique_ptr<GrDrawOpAtlas>` | 绘制操作图集 |
| `fShapeCache` | `ShapeCache` | 形状数据哈希表 |
| `fShapeList` | `ShapeDataList` | 形状数据LRU列表 |

## 公共 API 函数

### 生命周期管理

```cpp
SmallPathAtlasMgr()
~SmallPathAtlasMgr()
void reset()
```
构造、析构和重置管理器。

```cpp
bool initAtlas(GrProxyProvider* proxyProvider, const GrCaps* caps)
```
初始化图集。

### 形状查找与创建

```cpp
SmallPathShapeData* findOrCreate(
    const GrStyledShape& shape,
    int desiredDimension
)
```
根据形状和期望尺寸查找或创建形状数据。

```cpp
SmallPathShapeData* findOrCreate(
    const GrStyledShape& shape,
    const SkMatrix& ctm
)
```
根据形状和变换矩阵查找或创建形状数据。

### 图集操作

```cpp
GrDrawOpAtlas::ErrorCode addToAtlas(
    GrResourceProvider* resourceProvider,
    GrDeferredUploadTarget* target,
    int width,
    int height,
    const void* image,
    GrAtlasLocator* locator
)
```
添加图像到图集。

```cpp
void setUseToken(SmallPathShapeData* data, skgpu::Token token)
```
设置形状数据的使用令牌。

### 图集访问

```cpp
const GrSurfaceProxyView* getViews(int* numActiveProxies)
```
获取图集视图。

### 缓存管理

```cpp
void deleteCacheEntry(SmallPathShapeData* data)
```
删除缓存条目。

### 刷新回调（覆盖）

```cpp
bool preFlush(GrOnFlushResourceProvider* onFlushRP) override
void postFlush(skgpu::Token startTokenForNextFlush) override
bool retainOnFreeGpuResources() override
```

## 内部实现细节

### 图集初始化

```cpp
bool SmallPathAtlasMgr::initAtlas(
    GrProxyProvider* proxyProvider,
    const GrCaps* caps
) {
    if (!fAtlas) {
        // 创建图集
        constexpr int kAtlasTextureWidth = 2048;
        constexpr int kAtlasTextureHeight = 2048;
        constexpr SkColorType kAtlasColorType = kAlpha_8_SkColorType;

        fAtlas = GrDrawOpAtlas::Make(
            proxyProvider,
            caps,
            kAtlasTextureWidth,
            kAtlasTextureHeight,
            kAtlasColorType,
            /* numPlotsX= */ 2,
            /* numPlotsY= */ 2,
            this,  // 驱逐回调
            /* allowMultitexturing= */ true,
            /* label= */ "SmallPathAtlas"
        );
    }
    return fAtlas != nullptr;
}
```

**图集配置：**
- 尺寸：2048×2048
- 格式：Alpha 8（单通道）
- 分块：2×2（4个区块）
- 多纹理：启用

### 形状数据缓存

```cpp
using ShapeCache = SkTDynamicHash<SmallPathShapeData, SmallPathShapeDataKey>;

SmallPathShapeData* SmallPathAtlasMgr::findOrCreate(
    const SmallPathShapeDataKey& key
) {
    SmallPathShapeData* data = fShapeCache.find(key);

    if (!data) {
        // 创建新条目
        data = new SmallPathShapeData(key);
        fShapeCache.add(data);
        fShapeList.addToTail(data);
    }

    return data;
}
```

**缓存键：**
- 形状几何
- 样式（描边/填充）
- 目标尺寸

### 图集驱逐回调

```cpp
void SmallPathAtlasMgr::evict(GrPlotLocator locator) {
    // 遍历所有缓存的形状
    for (auto* shapeData : fShapeList) {
        // 如果形状在被驱逐的区块中
        if (shapeData->fAtlasLocator.plotLocator() == locator) {
            // 使图集位置无效
            shapeData->fAtlasLocator.invalidate();
        }
    }
}
```

**驱逐策略：**
- 当图集区块满时触发
- 使相关形状数据无效
- 下次使用时重新光栅化

### 使用令牌管理

```cpp
void SmallPathAtlasMgr::setUseToken(
    SmallPathShapeData* data,
    skgpu::Token token
) {
    SkASSERT(data->fAtlasLocator.isValid());
    fAtlas->setLastUseToken(data->fAtlasLocator, token);
}
```

**令牌作用：**
- 跟踪最后使用时间
- 实现LRU驱逐策略
- 保护活跃的数据

### 刷新生命周期

```cpp
bool SmallPathAtlasMgr::preFlush(GrOnFlushResourceProvider* onFlushRP) {
#if defined(GPU_TEST_UTILS)
    if (onFlushRP->failFlushTimeCallbacks()) {
        return false;
    }
#endif

    if (fAtlas) {
        // 实例化图集代理
        fAtlas->instantiate(onFlushRP);
    }
    return true;
}

void SmallPathAtlasMgr::postFlush(skgpu::Token startTokenForNextFlush) {
    if (fAtlas) {
        // 压缩图集，驱逐过期数据
        fAtlas->compact(startTokenForNextFlush);
    }
}
```

**刷新流程：**
1. **preFlush**：实例化GPU资源
2. **绘制使用图集**
3. **postFlush**：清理和压缩

### 缓存条目删除

```cpp
void SmallPathAtlasMgr::deleteCacheEntry(SmallPathShapeData* data) {
    // 从哈希表移除
    fShapeCache.remove(data->key());

    // 从LRU列表移除
    fShapeList.remove(data);

    // 删除数据
    delete data;
}
```

### 尺寸计算

```cpp
SmallPathShapeData* SmallPathAtlasMgr::findOrCreate(
    const GrStyledShape& shape,
    const SkMatrix& ctm
) {
    // 计算设备空间边界
    SkRect devBounds;
    ctm.mapRect(&devBounds, shape.bounds());

    // 计算期望的图集尺寸
    int desiredDimension = compute_dim(devBounds, ctm);

    // 查找或创建
    SmallPathShapeDataKey key(shape, desiredDimension);
    return findOrCreate(key);
}
```

**尺寸分桶：**
- 根据设备空间大小选择
- 考虑DPI和缩放
- 避免过度采样或欠采样

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `GrDrawOpAtlas` | 绘制操作图集 |
| `GrOnFlushCallbackObject` | 刷新回调接口 |
| `GrPlotEvictionCallback` | 驱逐回调接口 |
| `GrAtlasGenerationCounter` | 代计数器接口 |
| `SmallPathShapeData` | 形状数据 |
| `SkTDynamicHash` | 动态哈希表 |
| `SkTInternalLList` | 内部链表 |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| `SmallPathRenderer` | 小路径渲染器 |
| `GrContext` | 图形上下文 |

## 设计模式与设计决策

### 单例服务模式

作为 `GrOnFlushCallbackObject`，管理器在上下文生命周期内存在：
```cpp
bool retainOnFreeGpuResources() override { return true; }
```

### 观察者模式

实现 `GrPlotEvictionCallback` 监听图集驱逐事件。

### 双重索引

使用哈希表和链表双重索引：
- 哈希表：快速查找
- 链表：LRU顺序

### 延迟实例化

图集代理在 `preFlush` 时才实例化，支持 DDL 模式。

### 分离的查找接口

提供两种查找方式：
1. 按尺寸：精确控制
2. 按变换：自动计算

## 性能考量

### 内存管理

1. **图集大小固定**：2048×2048
2. **Alpha 8 格式**：每像素1字节
3. **多纹理支持**：可扩展到多个图集

### 缓存效率

1. **哈希查找**：O(1) 平均时间
2. **LRU列表**：快速访问最近使用
3. **驱逐策略**：自动管理内存

### 图集布局

1. **2×2 分块**：平衡分配和驱逐粒度
2. **多纹理**：支持更多形状
3. **压缩**：postFlush 时清理

### 线程安全

作为刷新回调对象，在刷新线程上操作：
- 不需要额外的同步
- 与录制线程分离

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| `SmallPathShapeData.h` | 依赖 | 形状数据定义 |
| `SmallPathRenderer.h` | 使用者 | 小路径渲染器 |
| `GrDrawOpAtlas.h` | 依赖 | 绘制操作图集 |
| `GrOnFlushResourceProvider.h` | 依赖 | 刷新资源提供者 |
| `SkTDynamicHash.h` | 依赖 | 动态哈希表 |
| `SkTInternalLList.h` | 依赖 | 内部链表 |
