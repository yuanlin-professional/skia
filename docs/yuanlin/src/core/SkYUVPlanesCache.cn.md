# SkYUVPlanesCache

> 源文件: src/core/SkYUVPlanesCache.h, src/core/SkYUVPlanesCache.cpp

## 概述

SkYUVPlanesCache 是 Skia 中专门用于缓存 YUV 平面数据的资源管理类。该模块通过 Skia 的通用资源缓存系统存储解码后的 YUV 图像数据,避免重复解码和转换开销。它管理多平面（Y、U、V、可选的 A）的像素数据及其描述信息,支持全局缓存和局部缓存两种模式,为视频渲染和图像处理提供高效的内存管理。

## 架构位置

SkYUVPlanesCache 位于 Skia 核心层的资源缓存子系统:

```
src/core/
  ├── SkResourceCache.h/cpp    # 通用资源缓存基础
  ├── SkBitmapCache.h/cpp      # 位图缓存
  ├── SkYUVPlanesCache.h/cpp   # YUV 平面缓存（本模块）
  └── SkCachedData.h           # 缓存数据包装器
```

该模块桥接图像解码器与渲染管线,特别服务于视频和 YUV 图像格式。

## 主要类与结构体

### SkYUVPlanesCache 类

| 类名 | 继承关系 | 关键成员变量 | 说明 |
|------|---------|------------|------|
| `SkYUVPlanesCache` | 无（静态工具类） | 无实例变量 | 提供静态方法管理缓存 |

### 内部辅助结构（匿名命名空间）

| 结构体 | 继承关系 | 关键成员变量 | 说明 |
|--------|---------|------------|------|
| `YUVValue` | 无 | `SkYUVAPixmaps fPixmaps`<br>`SkCachedData* fData` | 缓存值封装 |
| `YUVPlanesKey` | `SkResourceCache::Key` | `uint32_t fGenID` | 缓存键,基于生成 ID |
| `YUVPlanesRec` | `SkResourceCache::Rec` | `YUVPlanesKey fKey`<br>`YUVValue fValue` | 缓存记录 |

## 公共 API 函数

### 核心缓存操作

```cpp
// 查找并返回缓存的 YUV 平面
static SkCachedData* FindAndRef(
    uint32_t genID,
    SkYUVAPixmaps* pixmaps,
    SkResourceCache* localCache = nullptr
);

// 添加 YUV 平面到缓存
static void Add(
    uint32_t genID,
    SkCachedData* data,
    const SkYUVAPixmaps& pixmaps,
    SkResourceCache* localCache = nullptr
);
```

### 函数说明

**FindAndRef**
- 功能: 根据生成 ID 查找缓存的 YUV 平面数据
- 参数:
  - `genID`: 像素引用的唯一生成 ID
  - `pixmaps`: 输出参数,返回 YUVA 像素映射描述
  - `localCache`: 可选的局部缓存（默认使用全局缓存）
- 返回: 成功返回 SkCachedData 指针（已增加引用计数）,失败返回 nullptr
- 注意: 调用者负责调用 `unref()` 释放返回的数据

**Add**
- 功能: 将 YUV 平面数据添加到缓存
- 参数:
  - `genID`: 关联的生成 ID
  - `data`: 包含像素数据的 SkCachedData（必须包含足够的内存）
  - `pixmaps`: YUVA 像素映射,其 SkPixmap 指向 data 中的内存
  - `localCache`: 可选的局部缓存
- 返回: 无（void）

## 内部实现细节

### 缓存键设计

**YUVPlanesKey 结构**:
```cpp
struct YUVPlanesKey : public SkResourceCache::Key {
    YUVPlanesKey(uint32_t genID) : fGenID(genID) {
        this->init(&gYUVPlanesKeyNamespaceLabel,
                   SkMakeResourceCacheSharedIDForBitmap(genID),
                   sizeof(genID));
    }
    uint32_t fGenID;  // 唯一标识符
};
```

- 使用 `genID` 作为主键
- 共享位图缓存的 ID 空间
- 通过命名空间标签区分缓存类型

### 缓存记录管理

**YUVPlanesRec 生命周期**:
1. **构造**: 将 SkCachedData 附加到缓存并增加引用计数
   ```cpp
   YUVPlanesRec(YUVPlanesKey key, SkCachedData* data, ...) {
       fValue.fData = data;
       fValue.fData->attachToCacheAndRef();
   }
   ```

2. **析构**: 从缓存分离并减少引用计数
   ```cpp
   ~YUVPlanesRec() override {
       fValue.fData->detachFromCacheAndUnref();
   }
   ```

3. **内存计算**: 包含结构体大小和实际数据大小
   ```cpp
   size_t bytesUsed() const override {
       return sizeof(*this) + fValue.fData->size();
   }
   ```

### 访问者模式

**Visitor 回调**:
```cpp
static bool Visitor(const SkResourceCache::Rec& baseRec, void* contextData) {
    const YUVPlanesRec& rec = static_cast<const YUVPlanesRec&>(baseRec);
    YUVValue* result = static_cast<YUVValue*>(contextData);

    SkCachedData* tmpData = rec.fValue.fData;
    tmpData->ref();
    if (nullptr == tmpData->data()) {
        tmpData->unref();
        return false;  // 数据已失效
    }
    result->fData = tmpData;
    result->fPixmaps = rec.fValue.fPixmaps;
    return true;
}
```

功能:
- 验证缓存数据有效性
- 增加引用计数防止数据被释放
- 复制 pixmaps 描述信息

### 宏辅助

```cpp
#define CHECK_LOCAL(localCache, localName, globalName, ...) \
    ((localCache) ? localCache->localName(__VA_ARGS__) \
                  : SkResourceCache::globalName(__VA_ARGS__))
```

作用: 统一处理全局缓存和局部缓存的 API 调用

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkYUVAPixmaps.h` | YUVA 像素映射描述 |
| `src/core/SkBitmapCache.h` | 共享缓存 ID 生成 |
| `src/core/SkCachedData.h` | 缓存数据包装 |
| `src/core/SkResourceCache.h` | 通用资源缓存框架 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| 图像解码器 (如 SkJpegCodec) | 缓存解码的 YUV 数据 |
| GPU 纹理加载器 | 避免重复上传 YUV 纹理 |
| SkImage 实现 | 懒加载 YUV 图像 |

## 设计模式与设计决策

### 访问者模式

**决策**: 使用访问者模式遍历和验证缓存条目

**优点**:
- 解耦缓存遍历逻辑和业务逻辑
- 支持类型安全的向下转型
- 便于扩展不同的查找策略

**实现**:
```cpp
SkResourceCache::Find(key, YUVPlanesRec::Visitor, &result)
```

### 引用计数管理

**双重引用计数机制**:
1. **SkCachedData 引用**: 管理实际内存生命周期
2. **缓存附着引用**: 管理缓存条目生命周期

```cpp
attachToCacheAndRef()   // 附着到缓存 + ref()
detachFromCacheAndUnref() // 从缓存分离 + unref()
```

**优点**: 防止缓存持有数据时意外释放

### 全局/局部缓存统一

**决策**: 通过宏和可选参数支持两种缓存模式

**使用场景**:
- 全局缓存: 跨 SkSurface 共享（节省内存）
- 局部缓存: 单个 SkSurface 独占（线程安全）

## 性能考量

### 内存管理

**懒数据验证**:
```cpp
if (nullptr == tmpData->data()) {
    tmpData->unref();
    return false;  // 快速失败
}
```
- 避免不必要的数据复制
- 支持可丢弃内存 (SkDiscardableMemory)

### 缓存命中优化

1. **快速键比较**: 仅使用 `genID`（4 字节整数）
2. **避免重复解码**: YUV 解码开销通常较大
3. **内存复用**: 缓存数据直接映射为 SkPixmap

### 线程安全

- 全局缓存使用互斥锁保护
- 局部缓存无需同步（单线程访问）
- `attachToCacheAndRef()` 原子操作

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkYUVAPixmaps.h` | 依赖 | YUVA 像素映射定义 |
| `src/core/SkResourceCache.h` | 依赖 | 缓存基础设施 |
| `src/core/SkCachedData.h` | 依赖 | 数据包装器 |
| `src/core/SkBitmapCache.h` | 依赖 | ID 生成辅助 |
| `src/codec/SkJpegCodec.cpp` | 使用者 | JPEG 解码缓存 |
| `src/image/SkImage_Lazy.cpp` | 使用者 | 懒加载图像 |
