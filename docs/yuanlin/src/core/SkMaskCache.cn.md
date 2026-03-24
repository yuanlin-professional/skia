# SkMaskCache

> 源文件: src/core/SkMaskCache.h, src/core/SkMaskCache.cpp

## 概述

`SkMaskCache` 是 Skia 中专门用于缓存模糊遮罩 (blur mask) 的工具类。它通过缓存圆角矩形 (RRect) 和矩形 (Rects) 的模糊结果,避免重复计算相同参数的模糊效果,显著提升渲染性能。该类使用 `SkResourceCache` 作为底层缓存机制。

## 架构位置

`SkMaskCache` 位于 Skia 遮罩处理的缓存层:
- 作为 `SkMaskFilterBase` 的辅助缓存工具
- 基于 `SkResourceCache` 构建,利用其 LRU 淘汰策略
- 为模糊滤镜提供 nine-patch 优化的缓存支持
- 支持全局缓存和局部缓存两种模式

## 主要类与结构体

### 内部类型

| 类型 | 基类 | 说明 |
|------|------|------|
| RRectBlurKey | SkResourceCache::Key | 圆角矩形模糊的缓存键 |
| RRectBlurRec | SkResourceCache::Rec | 圆角矩形模糊的缓存记录 |
| RectsBlurKey | SkResourceCache::Key | 矩形模糊的缓存键 |
| RectsBlurRec | SkResourceCache::Rec | 矩形模糊的缓存记录 |

### 关键成员变量

**MaskValue** (内部结构体):
| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fMask | SkMask | 缓存的遮罩数据 |
| fData | SkCachedData* | 遮罩像素数据 |

**RRectBlurKey**:
| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fSigma | SkScalar | 模糊半径 (sigma 值) |
| fStyle | int32_t | 模糊样式 (SkBlurStyle) |
| fRRect | SkRRect | 圆角矩形几何数据 |

**RectsBlurKey**:
| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fSigma | SkScalar | 模糊半径 |
| fStyle | int32_t | 模糊样式 |
| fSizes[4] | SkSize | 矩形尺寸和偏移信息 |

## 公共 API 函数

### 查找缓存

```cpp
// 查找圆角矩形模糊缓存
static SkCachedData* FindAndRef(SkScalar sigma, SkBlurStyle style,
                                const SkRRect& rrect,
                                SkTLazy<SkMask>* mask,
                                SkResourceCache* localCache = nullptr);

// 查找矩形模糊缓存
static SkCachedData* FindAndRef(SkScalar sigma, SkBlurStyle style,
                                SkSpan<const SkRect> rects,
                                SkTLazy<SkMask>* mask,
                                SkResourceCache* localCache = nullptr);
```

**返回值**:
- 成功: 返回 `SkCachedData*` 引用计数已增加,`mask` 参数被初始化
- 失败: 返回 `nullptr`

### 添加缓存

```cpp
// 添加圆角矩形模糊到缓存
static void Add(SkScalar sigma, SkBlurStyle style,
                const SkRRect& rrect, const SkMask& mask,
                SkCachedData* data,
                SkResourceCache* localCache = nullptr);

// 添加矩形模糊到缓存
static void Add(SkScalar sigma, SkBlurStyle style,
                SkSpan<const SkRect> rects,
                const SkMask& mask, SkCachedData* data,
                SkResourceCache* localCache = nullptr);
```

## 内部实现细节

### 缓存键构造

#### RRectBlurKey 实现
```cpp
RRectBlurKey(SkScalar sigma, const SkRRect& rrect, SkBlurStyle style)
    : fSigma(sigma), fStyle(style), fRRect(rrect)
{
    this->init(&gRRectBlurKeyNamespaceLabel, 0,
               sizeof(fSigma) + sizeof(fStyle) + sizeof(fRRect));
}
```
使用全局命名空间标签确保不同类型缓存的键不冲突。

#### RectsBlurKey 实现
对于 1-2 个矩形,使用尺寸和偏移编码:
```cpp
fSizes[0] = SkSize{rects[0].width(), rects[0].height()};  // 外矩形尺寸
if (rects.size() == 2) {
    fSizes[1] = SkSize{rects[1].width(), rects[1].height()};  // 内矩形尺寸
    fSizes[2] = SkSize{rects[0].x() - rects[1].x(),
                       rects[0].y() - rects[1].y()};  // 相对偏移
}
fSizes[3] = SkSize{rects[0].x() - ir.x(), rects[0].y() - ir.y()};  // 亚像素偏移
```

### 缓存记录管理

#### 生命周期管理
```cpp
RRectBlurRec(RRectBlurKey key, const SkMask& mask, SkCachedData* data)
    : fKey(key), fValue({{nullptr, mask.fBounds, mask.fRowBytes, mask.fFormat}, data})
{
    fValue.fData->attachToCacheAndRef();  // 附加到缓存并增加引用
}

~RRectBlurRec() override {
    fValue.fData->detachFromCacheAndUnref();  // 从缓存分离并减少引用
}
```

#### Visitor 模式查找
```cpp
static bool Visitor(const SkResourceCache::Rec& baseRec, void* contextData) {
    const RRectBlurRec& rec = static_cast<const RRectBlurRec&>(baseRec);
    SkTLazy<MaskValue>* result = (SkTLazy<MaskValue>*)contextData;

    SkCachedData* tmpData = rec.fValue.fData;
    tmpData->ref();
    if (nullptr == tmpData->data()) {  // 检查数据是否已被丢弃
        tmpData->unref();
        return false;
    }
    result->init(rec.fValue);
    return true;
}
```

### 全局/局部缓存选择

使用宏简化缓存访问:
```cpp
#define CHECK_LOCAL(localCache, localName, globalName, ...) \
    ((localCache) ? localCache->localName(__VA_ARGS__) \
                  : SkResourceCache::globalName(__VA_ARGS__))
```

调用示例:
```cpp
if (!CHECK_LOCAL(localCache, find, Find, key, RRectBlurRec::Visitor, &result)) {
    return nullptr;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkResourceCache | 底层 LRU 缓存机制 |
| SkCachedData | 可丢弃的数据封装 |
| SkMask | 遮罩数据结构 |
| SkRRect | 圆角矩形几何 |
| SkTLazy | 延迟初始化容器 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| SkMaskFilterBase | 使用缓存优化 nine-patch |
| SkBlurMaskFilterImpl | 具体的模糊滤镜实现 |

## 设计模式与设计决策

### 1. Visitor 模式
通过 Visitor 回调函数访问缓存记录:
```cpp
bool Visitor(const SkResourceCache::Rec& baseRec, void* contextData)
```
优点:
- 解耦缓存查找逻辑和数据访问逻辑
- 允许在访问时进行有效性检查

### 2. 延迟初始化 (SkTLazy)
查找结果使用 `SkTLazy<MaskValue>` 延迟初始化:
```cpp
SkTLazy<MaskValue> result;
if (!CHECK_LOCAL(localCache, find, Find, key, Visitor, &result)) {
    return nullptr;
}
mask->init(result->fData->data(), result->fMask.fBounds, ...);
```

### 3. 引用计数管理
通过 `attachToCacheAndRef()` / `detachFromCacheAndUnref()` 精确控制生命周期:
- 缓存命中时增加引用,调用者负责释放
- 缓存淘汰时自动清理数据

### 4. 命名空间隔离
```cpp
static unsigned gRRectBlurKeyNamespaceLabel;
static unsigned gRectsBlurKeyNamespaceLabel;
```
不同类型的缓存键使用不同的命名空间,避免哈希冲突。

## 性能考量

### 1. 键大小优化
**RRectBlurKey**: 包含完整的 `SkRRect` 几何信息
**RectsBlurKey**: 使用 4 个 `SkSize` 编码 1-2 个矩形,避免直接存储 `SkRect`

### 2. 缓存分类策略
使用不同的 Rec 类型和 namespace:
```cpp
const char* getCategory() const override { return "rrect-blur"; }
const char* getCategory() const override { return "rects-blur"; }
```
便于调试和缓存策略调整。

### 3. 内存占用计算
```cpp
size_t bytesUsed() const override {
    return sizeof(*this) + fValue.fData->size();
}
```
准确计算缓存项占用,支持 LRU 容量管理。

### 4. 数据有效性检查
```cpp
if (nullptr == tmpData->data()) {  // 可丢弃数据可能已被释放
    tmpData->unref();
    return false;
}
```
防止使用已释放的 discardable memory。

### 5. 局部缓存支持
允许使用线程局部缓存 (`localCache`),减少全局缓存的锁竞争:
```cpp
SkMaskCache::FindAndRef(sigma, style, rrect, mask, myLocalCache);
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/core/SkResourceCache.h | 基础设施 | 通用 LRU 缓存 |
| src/core/SkCachedData.h | 数据封装 | 可丢弃数据管理 |
| src/core/SkMask.h | 数据结构 | 遮罩定义 |
| src/core/SkMaskFilterBase.h | 使用者 | Nine-patch 优化 |
| include/core/SkRRect.h | 几何类型 | 圆角矩形 |
| src/base/SkTLazy.h | 工具类 | 延迟初始化 |
