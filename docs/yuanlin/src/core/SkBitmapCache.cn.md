# SkBitmapCache

> 源文件: src/core/SkBitmapCache.h, src/core/SkBitmapCache.cpp

## 概述

`SkBitmapCache` 是 Skia 图形库中用于缓存位图和 Mipmap 的资源管理系统。该模块提供了高效的位图缓存机制,通过将位图数据存储在共享的资源缓存中,避免重复创建和内存分配,提升渲染性能。系统支持可丢弃内存(Discardable Memory)机制,允许在内存紧张时自动释放缓存的位图数据。

## 架构位置

```
src/core/
  ├── SkBitmapCache.cpp      # 位图缓存实现
  ├── SkBitmapCache.h        # 位图缓存接口
  ├── SkResourceCache.h      # 底层资源缓存系统
  └── SkMipmap.h            # Mipmap 数据结构
```

本模块位于 Skia 核心层,作为图像资源管理的关键组件,与 `SkResourceCache` 底层缓存系统协作,为位图和 Mipmap 提供专门的缓存服务。

## 主要类与结构体

### SkBitmapCacheDesc

| **属性** | **说明** |
|---------|---------|
| **继承关系** | 独立结构体 |
| **作用** | 位图缓存描述符,唯一标识一个缓存项 |

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fImageID` | `uint32_t` | 图像唯一标识符(非零) |
| `fSubset` | `SkIRect` | 位图子集区域 |

### SkBitmapCache

| **属性** | **说明** |
|---------|---------|
| **继承关系** | 无继承 |
| **作用** | 位图缓存的主接口类 |

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `Rec` | 内部类 | 缓存记录,继承自 `SkResourceCache::Rec` |
| `RecPtr` | `std::unique_ptr<Rec, RecDeleter>` | 智能指针类型 |

### SkBitmapCache::Rec

**内部缓存记录类,关键成员:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fKey` | `BitmapKey` | 缓存键 |
| `fDM` | `std::unique_ptr<SkDiscardableMemory>` | 可丢弃内存 |
| `fMalloc` | `void*` | 堆内存指针 |
| `fInfo` | `SkImageInfo` | 图像信息 |
| `fRowBytes` | `size_t` | 行字节数 |
| `fPrUniqueID` | `uint32_t` | PixelRef 唯一 ID |
| `fExternalCounter` | `int` | 外部引用计数 |
| `fDiscardableIsLocked` | `bool` | 可丢弃内存锁定状态 |

### SkMipmapCache

| **属性** | **说明** |
|---------|---------|
| **继承关系** | 无继承 |
| **作用** | Mipmap 专用缓存接口 |

## 公共 API 函数

### SkBitmapCacheDesc 工厂方法

```cpp
static SkBitmapCacheDesc Make(const SkImage* image);
static SkBitmapCacheDesc Make(uint32_t genID, const SkIRect& subset);
```

创建位图缓存描述符,用于标识缓存项。

### SkBitmapCache 核心接口

```cpp
static bool Find(const SkBitmapCacheDesc& desc, SkBitmap* result);
```

**功能:** 根据描述符查找缓存的位图,找到则返回 `true` 并设置结果位图。

```cpp
static RecPtr Alloc(const SkBitmapCacheDesc& desc, const SkImageInfo& info, SkPixmap* pmap);
```

**功能:** 分配新的缓存记录,包含位图像素内存。

```cpp
static void Add(RecPtr rec, SkBitmap* bitmap);
```

**功能:** 将缓存记录添加到资源缓存系统。

### SkMipmapCache 接口

```cpp
static const SkMipmap* FindAndRef(const SkBitmapCacheDesc& desc,
                                   SkResourceCache* localCache = nullptr);
```

**功能:** 查找并引用 Mipmap 缓存项。

```cpp
static const SkMipmap* AddAndRef(const SkImage_Base* image,
                                  SkResourceCache* localCache = nullptr);
```

**功能:** 为图像生成并缓存 Mipmap。

### 辅助函数

```cpp
uint64_t SkMakeResourceCacheSharedIDForBitmap(uint32_t bitmapGenID);
```

**功能:** 为位图生成唯一的共享缓存 ID。

```cpp
void SkNotifyBitmapGenIDIsStale(uint32_t bitmapGenID);
```

**功能:** 通知缓存系统某位图 ID 已过期,触发清除操作。

## 内部实现细节

### 缓存键机制

系统使用 `BitmapKey` 和 `MipMapKey` 作为缓存键,通过命名空间标签和共享 ID 实现唯一标识:

```cpp
struct BitmapKey : public SkResourceCache::Key {
    BitmapKey(const SkBitmapCacheDesc& desc) : fDesc(desc) {
        this->init(&gBitmapKeyNamespaceLabel,
                   SkMakeResourceCacheSharedIDForBitmap(fDesc.fImageID),
                   sizeof(fDesc));
    }
    const SkBitmapCacheDesc fDesc;
};
```

### 内存管理策略

**双重内存模式:**
- **可丢弃内存 (fDM):** 优先使用,允许系统在内存压力下自动释放
- **堆内存 (fMalloc):** 备选方案,两者互斥使用

**引用计数机制:**
```cpp
void ReleaseProc(void* addr, void* ctx) {
    Rec* rec = static_cast<Rec*>(ctx);
    rec->fExternalCounter -= 1;
    if (rec->fDM && rec->fExternalCounter == 0) {
        rec->fDM->unlock();
        rec->fDiscardableIsLocked = false;
    }
}
```

### 安装位图流程

```cpp
bool install(SkBitmap* bitmap) {
    if (fDM && !fDiscardableIsLocked) {
        if (!fDM->lock()) {
            fDM.reset(nullptr);
            return false;
        }
        fDiscardableIsLocked = true;
    }
    bitmap->installPixels(fInfo, fDM ? fDM->data() : fMalloc,
                         fRowBytes, ReleaseProc, this);
    fExternalCounter++;
    return true;
}
```

### Mipmap 缓存流程

1. 从原始图像获取只读像素
2. 使用 `SkMipmap::Build()` 构建 Mipmap 链
3. 创建 `MipMapRec` 并添加到缓存
4. 通知图像已加入光栅缓存

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkResourceCache` | 底层资源缓存系统 |
| `SkDiscardableMemory` | 可丢弃内存机制 |
| `SkPixelRef` | 像素数据引用 |
| `SkMipmap` | Mipmap 数据结构 |
| `SkImage_Base` | 图像基类 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| 图像渲染管线 | 查找缓存位图以避免重复解码 |
| Mipmap 生成器 | 缓存多级纹理数据 |
| 纹理采样器 | 获取预处理的位图数据 |

## 设计模式与设计决策

### 1. 享元模式 (Flyweight Pattern)

通过缓存共享位图数据,避免重复存储相同的像素内容,节省内存。

### 2. 资源获取即初始化 (RAII)

使用智能指针 `RecPtr` 管理缓存记录生命周期,配合自定义 deleter 确保资源正确释放。

### 3. 引用计数与锁定机制

```cpp
fExternalCounter  // 外部引用计数
fDiscardableIsLocked  // 内存锁定状态
```

这种设计允许多个位图共享同一块缓存数据,同时通过锁定机制防止数据被过早释放。

### 4. 命名空间隔离

```cpp
static unsigned gBitmapKeyNamespaceLabel;
static unsigned gMipMapKeyNamespaceLabel;
```

为不同类型的缓存使用独立的命名空间,避免键冲突。

### 5. 延迟锁定策略

可丢弃内存在 `install()` 时才尝试锁定,而非分配时立即锁定,优化内存使用。

## 性能考量

### 内存效率

- **可丢弃内存优先:** 优先使用系统级别的可丢弃内存,允许操作系统在内存压力下自动回收
- **惰性锁定:** 仅在实际使用时才锁定可丢弃内存,减少内存占用峰值

### 缓存命中优化

- **唯一 ID 机制:** 通过 `fImageID` 和 `fSubset` 快速定位缓存项
- **共享 ID 清除:** `SkNotifyBitmapGenIDIsStale()` 批量清除过期缓存

### 线程安全

- **互斥锁保护:** `fMutex` 保护 `fExternalCounter` 和内存锁定状态
- **原子操作:** 引用计数的增减使用互斥锁同步

### 缓存淘汰策略

```cpp
bool canBePurged() override {
    return fExternalCounter == 0;
}
```

仅当没有外部引用时才允许淘汰,确保缓存的正确性。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkResourceCache.h` | 底层资源缓存系统接口 |
| `src/core/SkResourceCache.cpp` | 资源缓存实现 |
| `src/core/SkMipmap.h` | Mipmap 数据结构定义 |
| `src/core/SkMipmap.cpp` | Mipmap 构建实现 |
| `include/core/SkBitmap.h` | 位图类定义 |
| `include/core/SkPixelRef.h` | 像素引用接口 |
| `include/private/chromium/SkDiscardableMemory.h` | 可丢弃内存接口 |
| `src/image/SkImage_Base.h` | 图像基类 |
