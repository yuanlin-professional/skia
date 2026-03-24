# SkPixelRef

> 源文件
> - include/core/SkPixelRef.h
> - src/core/SkPixelRef.cpp

## 概述

`SkPixelRef` 是 Skia 中像素内存的智能容器，用于与 `SkBitmap` 配合管理像素数据。它提供了引用计数、生成ID追踪、不可变性标记等功能，是像素数据的生命周期管理核心。该类线程安全，支持多线程共享访问。

`SkPixelRef` 继承自 `SkPixelStorage` 和 `SkRefCnt`，不仅存储像素数据的地址和尺寸信息，还维护像素变更通知机制（通过生成ID）和缓存失效监听器。它是连接像素内存和图形资源缓存系统的桥梁。

## 架构位置

`SkPixelRef` 位于 Skia 核心图形层的底层：

- 被 `SkBitmap` 使用来持有像素数据
- 继承自 `SkPixelStorage` 基类（新增的抽象层）
- 与资源缓存系统（`SkBitmapCache`）交互
- 支持 `SkIDChangeListener` 变更通知机制

## 主要类与结构体

### SkPixelRef

像素引用管理类。

**继承关系**
- 继承自：`SkPixelStorage`, `SkRefCnt`
- 友元类：`SkSurface_Raster`, `SkBitmapCache_setImmutableWithID`

**关键成员变量**

| 成员变量 | 类型 | 描述 |
|---------|------|------|
| fWidth | int | 像素宽度 |
| fHeight | int | 像素高度 |
| fPixels | void* | 像素数据指针 |
| fRowBytes | size_t | 行字节数 |
| fTaggedGenID | atomic<uint32_t> | 标记的生成ID（最低位表示唯一性） |
| fGenIDChangeListeners | SkIDChangeListener::List | 生成ID变更监听器列表 |
| fAddedToCache | atomic<bool> | 是否已添加到缓存 |
| fMutability | Mutability | 可变性状态 |

**可变性枚举**

| 枚举值 | 描述 |
|-------|------|
| kMutable | 可变（初始状态） |
| kTemporarilyImmutable | 临时不可变（可恢复为可变） |
| kImmutable | 永久不可变 |

## 公共 API 函数

### 构造与类型

```cpp
// 构造函数
SkPixelRef(int width, int height, void* addr, size_t rowBytes);

// 析构函数
~SkPixelRef() override;

// 获取存储类型
Type type() const override;  // 返回 kPixelRef
```

### 尺寸访问

```cpp
SkISize dimensions() const;  // 返回 {fWidth, fHeight}
int width() const;
int height() const;
void* pixels() const;        // 像素数据指针
size_t rowBytes() const;     // 行字节数
```

### 生成ID管理

```cpp
// 获取当前生成ID（唯一标识像素内容）
uint32_t getGenerationID() const;

// 通知像素已变更（生成新ID）
void notifyPixelsChanged();
```

### 不可变性管理

```cpp
// 查询是否不可变
bool isImmutable() const;

// 标记为永久不可变
void setImmutable();
```

### 变更监听

```cpp
// 注册生成ID变更监听器
void addGenIDChangeListener(sk_sp<SkIDChangeListener> listener);

// 通知已添加到缓存
void notifyAddedToCache();
```

### 调试接口

```cpp
// 获取可丢弃内存（如果有）
virtual SkDiscardableMemory* diagnostic_only_getDiscardable() const;
```

## 内部实现细节

### 生成ID机制

生成ID使用带标记的32位整数：

```cpp
// 生成新ID（偶数，保留最低位）
uint32_t SkNextID::ImageID() {
    static std::atomic<uint32_t> nextID{2};  // 从2开始
    uint32_t id;
    do {
        id = nextID.fetch_add(2, std::memory_order_relaxed);
    } while (id == 0);  // 跳过0
    return id;
}

// 检查生成ID是否唯一
bool genIDIsUnique() const {
    return SkToBool(fTaggedGenID.load() & 1);
}

// 获取生成ID（延迟分配）
uint32_t SkPixelRef::getGenerationID() const {
    uint32_t id = fTaggedGenID.load();
    if (0 == id) {
        // 首次访问，分配新ID并标记为唯一
        uint32_t next = SkNextID::ImageID() | 1u;
        if (fTaggedGenID.compare_exchange_strong(id, next)) {
            id = next;  // 成功设置
        } else {
            // 竞争失败，使用赢家的ID
        }
    }
    return id & ~1u;  // 屏蔽唯一性位
}
```

**关键设计**：
- 偶数ID：避免与唯一性标记冲突
- 最低位：标记ID是否唯一（仅当前 PixelRef 持有）
- 延迟分配：首次 `getGenerationID()` 才分配
- 原子操作：线程安全

### 像素变更通知

```cpp
void SkPixelRef::notifyPixelsChanged() {
#ifdef SK_DEBUG
    if (this->isImmutable()) {
        SkDebugf("========== notifyPixelsChanged called on immutable pixelref");
    }
#endif
    this->callGenIDChangeListeners();
    this->needsNewGenID();
}

void SkPixelRef::needsNewGenID() {
    fTaggedGenID.store(0);  // 重置为0，下次访问重新分配
    SkASSERT(!this->genIDIsUnique());
}
```

重置生成ID到0触发延迟重新分配，确保新ID与旧ID不同。

### 变更监听器管理

```cpp
void SkPixelRef::addGenIDChangeListener(sk_sp<SkIDChangeListener> listener) {
    if (!listener || !this->genIDIsUnique()) {
        // 不唯一的ID不触发监听器
        return;
    }
    SkASSERT(!listener->shouldDeregister());
    fGenIDChangeListeners.add(std::move(listener));
}

void SkPixelRef::callGenIDChangeListeners() {
    if (this->genIDIsUnique()) {
        // 只有唯一ID才调用监听器
        fGenIDChangeListeners.changed();

        // 通知缓存系统
        if (fAddedToCache.exchange(false)) {
            SkNotifyBitmapGenIDIsStale(this->getGenerationID());
        }
    } else {
        // 非唯一ID，清空监听器
        fGenIDChangeListeners.reset();
    }
}
```

**唯一性检查**：
- 只有唯一ID才触发监听器
- 避免多个 PixelRef 共享ID时错误通知
- 监听器只触发一次

### 不可变性管理

```cpp
void SkPixelRef::setImmutable() {
    fMutability = kImmutable;  // 永久不可变
}

void SkPixelRef::setImmutableWithID(uint32_t genID) {
    // 强制设置特定生成ID（用于与 SkImage 同步）
    fMutability = kImmutable;
    fTaggedGenID.store(genID);
}

void SkPixelRef::setTemporarilyImmutable() {
    SkASSERT(fMutability != kImmutable);
    fMutability = kTemporarilyImmutable;
}

void SkPixelRef::restoreMutability() {
    SkASSERT(fMutability != kImmutable);
    fMutability = kMutable;
}
```

**临时不可变**：
- `SkSurface_Raster` 使用，在读取像素期间锁定
- 防止并发修改但不永久锁定
- 可恢复为可变状态

### Android 重置接口

```cpp
void SkPixelRef::android_only_reset(int width, int height, size_t rowBytes) {
    fWidth = width;
    fHeight = height;
    fRowBytes = rowBytes;
    // 注意：不改变 fPixels

    // 保守起见触发变更通知
    this->notifyPixelsChanged();
}
```

Android 特定接口，用于重用 PixelRef 对象。

### 工厂函数

```cpp
sk_sp<SkPixelRef> SkMakePixelRefWithProc(
    int width, int height, size_t rowBytes, void* addr,
    void (*releaseProc)(void* addr, void* ctx), void* ctx)
{
    SkASSERT(width >= 0 && height >= 0);
    if (nullptr == releaseProc) {
        return sk_make_sp<SkPixelRef>(width, height, addr, rowBytes);
    }

    // 创建带释放回调的子类
    struct PixelRef final : public SkPixelRef {
        void (*fReleaseProc)(void*, void*);
        void* fReleaseProcContext;

        PixelRef(int w, int h, void* s, size_t r,
                 void (*proc)(void*, void*), void* ctx)
            : SkPixelRef(w, h, s, r)
            , fReleaseProc(proc)
            , fReleaseProcContext(ctx) {}

        ~PixelRef() override {
            fReleaseProc(this->pixels(), fReleaseProcContext);
        }
    };

    return sk_sp<SkPixelRef>(new PixelRef(
        width, height, addr, rowBytes, releaseProc, ctx));
}
```

支持自定义内存释放逻辑。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| SkPixelStorage | 基类，定义存储类型接口 |
| SkRefCnt | 引用计数基类 |
| SkIDChangeListener | 变更监听器接口 |
| SkNextID | 生成唯一ID |
| SkBitmapCache | 缓存失效通知 |

### 被依赖的模块

| 模块 | 关系 |
|-----|------|
| SkBitmap | 使用 SkPixelRef 管理像素 |
| SkSurface_Raster | 使用临时不可变功能 |
| SkBitmapCache | 监听生成ID变更 |

## 设计模式与设计决策

### 引用计数

继承自 `SkRefCnt`：
- 自动管理生命周期
- 支持多线程共享
- 避免手动内存管理

### 观察者模式

`SkIDChangeListener` 实现观察者模式：
- PixelRef 是主题（Subject）
- 缓存系统是观察者（Observer）
- 像素变更时自动通知

### 延迟初始化

生成ID延迟分配：
- 节省ID资源
- 避免不必要的原子操作
- 首次需要时才分配

### 状态机

可变性使用状态机：
```
kMutable <-> kTemporarilyImmutable
    ↓
kImmutable（不可逆）
```

### 位标记优化

生成ID最低位标记唯一性：
- 节省额外的布尔变量
- 单一原子变量存储两个状态
- 高效的位操作

## 性能考量

### 原子操作

关键成员使用原子类型：
- `fTaggedGenID`：线程安全访问
- `fAddedToCache`：无锁标记
- 使用 `memory_order_relaxed` 优化性能

### 延迟分配

生成ID按需分配：
- 避免每个 PixelRef 都分配ID
- 临时 PixelRef 可能永不需要ID
- 减少ID生成器竞争

### 监听器优化

唯一性检查避免无效监听：
- 共享ID的 PixelRef 不注册监听器
- 减少监听器列表维护开销
- 避免错误的失效通知

### 缓存标记

`fAddedToCache` 使用 `exchange`：
- 原子测试并清除
- 避免重复通知缓存
- 单次原子操作完成检查和重置

## 相关文件

| 文件路径 | 描述 |
|---------|------|
| include/private/SkPixelStorage.h | 基类定义 |
| src/core/SkPixelRefPriv.h | 私有辅助函数 |
| src/core/SkBitmapCache.h/cpp | 缓存系统集成 |
| src/core/SkNextID.h/cpp | ID生成器 |
| include/core/SkBitmap.h | 使用 SkPixelRef |
| include/private/SkIDChangeListener.h | 监听器接口 |
| src/core/SkSurface_Raster.cpp | 临时不可变使用者 |
