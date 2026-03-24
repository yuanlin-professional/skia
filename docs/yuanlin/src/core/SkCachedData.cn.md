# SkCachedData

> 源文件：src/core/SkCachedData.h, src/core/SkCachedData.cpp

## 概述

`SkCachedData` 是 Skia 资源缓存系统的核心数据封装类，提供线程安全的引用计数、可选的可丢弃内存（Discardable Memory）支持，以及与 `SkResourceCache` 的集成机制。它抽象了缓存数据的生命周期管理，支持锁定/解锁状态切换，允许系统在内存压力下自动释放未使用的数据。

核心特性：
- 线程安全的引用计数
- 支持普通堆内存和可丢弃内存两种存储类型
- 锁定/解锁状态管理
- 与 `SkResourceCache` 的生命周期协作
- 数据变化通知机制（通过 `onDataChange` 钩子）

## 架构位置

```
SkResourceCache
  ├── SkResourceCache::Rec
  │     └── 包含 -> SkCachedData
  ├── SkMaskCache::Rec
  │     └── 包含 -> SkCachedData
  └── SkImageCacherator::CachedFormat
        └── 包含 -> SkCachedData
```

`SkCachedData` 是缓存记录（Rec）的数据载体，被各类缓存（遮罩缓存、图像缓存等）广泛使用。

## 主要类与结构体

### SkCachedData

**继承关系：**`SkNoncopyable`（不可拷贝）

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fMutex | SkMutex | 保护所有可变状态的互斥锁 |
| fStorage | union{fDM, fMalloc} | 存储指针（可丢弃内存或堆内存） |
| fData | void* | 当前可访问的数据指针（锁定时有效） |
| fSize | size_t | 数据字节数 |
| fRefCnt | int | 引用计数（包含缓存持有的引用） |
| fStorageType | StorageType | 存储类型枚举 |
| fInCache | bool | 是否被缓存持有 |
| fIsLocked | bool | 是否处于锁定状态 |

**存储类型枚举：**

| 枚举值 | 说明 |
|-------|------|
| kMalloc_StorageType | 普通堆分配（`sk_malloc`） |
| kDiscardableMemory_StorageType | 可丢弃内存（`SkDiscardableMemory`） |

## 公共 API 函数

### 1. 构造函数

```cpp
// 使用普通堆内存构造
SkCachedData(void* mallocData, size_t size)

// 使用可丢弃内存构造
SkCachedData(size_t size, SkDiscardableMemory* dm)
```

**行为：**
- 初始引用计数为 1
- 初始状态为已锁定（`fIsLocked = true`）
- 不在缓存中（`fInCache = false`）

### 2. 引用计数管理

```cpp
void ref() const      // 增加引用计数
void unref() const    // 减少引用计数，降至 0 时删除自身
```

**线程安全：**所有操作通过 `fMutex` 保护。

### 3. 数据访问

```cpp
size_t size() const               // 获取数据大小
const void* data() const          // 只读访问（锁定时有效，否则 nullptr）
void* writable_data()             // 可写访问
```

**注意：**`data()` 在解锁状态下返回 `nullptr`。

### 4. 缓存集成接口

```cpp
void attachToCacheAndRef() const      // 缓存持有时调用
void detachFromCacheAndUnref() const  // 缓存释放时调用
```

**典型用法：**
```cpp
// 缓存记录构造函数
MyCacheRec(SkCachedData* data) {
    fData = data;
    fData->attachToCacheAndRef();
}

// 缓存记录析构函数
~MyCacheRec() {
    fData->detachFromCacheAndUnref();
}
```

### 5. 测试辅助接口

```cpp
int testing_only_getRefCnt() const
bool testing_only_isLocked() const
bool testing_only_isInCache() const
SkDiscardableMemory* diagnostic_only_getDiscardable() const
```

## 内部实现细节

### 1. 引用计数机制

引用计数的低位用于标记缓存所有权（历史遗留注释，当前实现使用独立的 `fInCache` 标志）：

```cpp
void inMutexRef(bool fromCache) {
    if ((1 == fRefCnt) && fInCache) {
        this->inMutexLock();  // 从仅缓存持有变为外部引用时，自动锁定
    }
    fRefCnt += 1;
    if (fromCache) {
        fInCache = true;
    }
}
```

### 2. 锁定/解锁状态转换

#### 锁定（inMutexLock）

```cpp
void inMutexLock() {
    fIsLocked = true;
    switch (fStorageType) {
        case kMalloc_StorageType:
            this->setData(fStorage.fMalloc);
            break;
        case kDiscardableMemory_StorageType:
            if (fStorage.fDM->lock()) {
                this->setData(fStorage.fDM->data());
            } else {
                this->setData(nullptr);  // 锁定失败，数据已被丢弃
            }
            break;
    }
}
```

#### 解锁（inMutexUnlock）

```cpp
void inMutexUnlock() {
    fIsLocked = false;
    switch (fStorageType) {
        case kMalloc_StorageType:
            // 无需操作
            break;
        case kDiscardableMemory_StorageType:
            if (fData) {
                fStorage.fDM->unlock();
            }
            break;
    }
    this->setData(nullptr);
}
```

### 3. 自动锁定/解锁策略

**自动锁定：**当引用计数从 1 增加到 2 且缓存持有时，自动锁定数据。

```cpp
if ((1 == fRefCnt) && fInCache) {
    this->inMutexLock();
}
```

**自动解锁：**当引用计数从 2 降至 1 且缓存持有时，自动解锁数据。

```cpp
if (fInCache && !fromCache) {
    this->inMutexUnlock();
}
```

**原理：**
- `fRefCnt == 1` 且 `fInCache == true`：仅缓存持有，数据可解锁
- `fRefCnt >= 2`：外部客户持有引用，数据必须锁定

### 4. 数据变化通知

```cpp
void setData(void* newData) {
    if (newData != fData) {
        this->onDataChange(fData, newData);  // 通知子类
        fData = newData;
    }
}
```

子类可重写 `onDataChange()` 以响应数据指针变化（如 `SkPixelRef` 中更新像素指针）。

### 5. 线程安全封装

```cpp
class AutoMutexWritable {
public:
    AutoMutexWritable(const SkCachedData* cd) : fCD(const_cast<SkCachedData*>(cd)) {
        fCD->fMutex.acquire();
        fCD->validate();
    }
    ~AutoMutexWritable() {
        fCD->validate();
        fCD->fMutex.release();
    }
private:
    SkCachedData* fCD;
};
```

所有内部状态修改都通过此 RAII 类自动加锁。

### 6. 状态验证（DEBUG 模式）

```cpp
#ifdef SK_DEBUG
void validate() const {
    if (fIsLocked) {
        SkASSERT((fInCache && fRefCnt > 1) || !fInCache);
        if (kMalloc_StorageType) {
            SkASSERT(fData == fStorage.fMalloc);
        }
    } else {
        SkASSERT((fInCache && 1 == fRefCnt) || (0 == fRefCnt));
        SkASSERT(nullptr == fData);
    }
}
#endif
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `SkDiscardableMemory` | 可丢弃内存接口 |
| `SkMutex` | 线程同步原语 |
| `SkNoncopyable` | 基类（禁止拷贝） |
| `sk_malloc` / `sk_free` | 内存分配函数 |

### 被依赖的模块

| 模块 | 使用方式 |
|-----|---------|
| `SkResourceCache` | 通过 `newCachedData()` 创建实例 |
| `SkMaskCache` | 存储模糊遮罩数据 |
| `SkImageCacherator` | 缓存解码后的图像数据 |
| `SkPixelRef` | 作为像素数据的后端存储 |

## 设计模式与设计决策

### 1. RAII 模式

通过 `AutoMutexWritable` 确保互斥锁在所有路径上正确释放：

```cpp
void internalRef(bool fromCache) const {
    AutoMutexWritable(this)->inMutexRef(fromCache);
}  // 自动解锁
```

### 2. 策略模式

通过 `fStorageType` 枚举，统一处理两种内存类型：

```cpp
switch (fStorageType) {
    case kMalloc_StorageType: /* 堆内存逻辑 */ break;
    case kDiscardableMemory_StorageType: /* 可丢弃内存逻辑 */ break;
}
```

### 3. 观察者模式

`onDataChange()` 虚函数允许子类监听数据指针变化：

```cpp
virtual void onDataChange(void* oldData, void* newData) {}
```

### 4. 单一职责原则

`SkCachedData` 专注于内存生命周期管理，不负责缓存策略（由 `SkResourceCache` 处理）。

### 5. 引用计数与缓存协作

通过 `fInCache` 标志区分缓存引用和客户引用，实现以下语义：
- 缓存引用不阻止数据解锁
- 客户引用强制数据锁定

这种设计允许系统在无外部引用时释放内存。

## 性能考量

### 1. 可丢弃内存优势

对于大型数据（如图像解码结果），使用可丢弃内存可节省内存：

```
普通缓存: 内存占用恒定
可丢弃缓存: 无外部引用时可释放，需要时重新锁定
```

### 2. 锁定开销

**堆内存：**锁定/解锁为空操作（O(1)）

**可丢弃内存：**锁定可能涉及系统调用（页表映射），解锁会释放物理内存。

### 3. 引用计数原子性

虽然 `fRefCnt` 不是原子变量，但通过 `fMutex` 保护，确保线程安全。代价是每次 `ref()`/`unref()` 都需要加锁。

**权衡：**相比原子操作，互斥锁开销略高，但简化了复杂状态管理。

### 4. 内存布局

```cpp
sizeof(SkCachedData) ≈ 48 字节 (64位平台)
  SkMutex: 8 字节
  union: 8 字节
  fData: 8 字节
  fSize: 8 字节
  fRefCnt: 4 字节
  枚举和布尔: 4 字节
  + 填充
```

### 5. 性能陷阱

**频繁锁定/解锁：**如果客户端反复 `ref()`/`unref()` 可丢弃内存，会导致频繁的系统调用。

**过早解锁：**缓存作为唯一持有者时，数据立即解锁，下次访问可能需要重建。

## 相关文件

| 文件 | 关系 | 说明 |
|-----|------|------|
| src/core/SkResourceCache.h | 使用者 | 资源缓存系统 |
| src/core/SkMaskCache.h | 使用者 | 遮罩缓存 |
| include/private/chromium/SkDiscardableMemory.h | 依赖 | 可丢弃内存接口 |
| include/private/base/SkMutex.h | 依赖 | 互斥锁 |
| src/core/SkPixelRef.h | 子类 | 像素引用实现 |
