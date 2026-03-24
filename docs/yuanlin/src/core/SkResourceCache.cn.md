# SkResourceCache

> 源文件
> - src/core/SkResourceCache.h
> - src/core/SkResourceCache.cpp

## 概述

`SkResourceCache` 是 Skia 的通用资源缓存系统,用于缓存位图、缩放图像等昂贵的计算结果。它实现了基于 LRU (Least Recently Used) 策略的内存管理,支持两种模式:固定大小内存池和可丢弃内存 (discardable memory)。该缓存系统线程安全,通过全局单例和消息总线支持跨线程的资源共享和清理。

## 架构位置

`SkResourceCache` 位于 Skia 核心层的资源管理模块:
- **使用者**: SkBitmapCache, SkImageFilter, SkScaledImageCache
- **依赖**: SkCachedData, SkDiscardableMemory, SkMessageBus
- **层级**: 基础设施层,为高层渲染提供缓存支持

## 主要类与结构体

### SkResourceCache

通用资源缓存容器,管理缓存条目的生命周期。

**继承关系**:
```
SkResourceCache (不继承任何类,独立类)
```

**关键成员变量**:

| 变量 | 类型 | 说明 |
|------|------|------|
| fHead | Rec* | LRU 链表头 (最近使用) |
| fTail | Rec* | LRU 链表尾 (最久未使用) |
| fHash | Hash* | 哈希表,用于快速查找 |
| fTotalBytesUsed | size_t | 当前已用字节数 |
| fTotalByteLimit | size_t | 总内存限制 |
| fSingleAllocationByteLimit | size_t | 单个分配大小限制 |
| fCount | int | 缓存条目数量 |
| fDiscardableFactory | DiscardableFactory | 可丢弃内存工厂函数 |
| fPurgeSharedIDInbox | MessageBus::Inbox | 接收清理消息的收件箱 |

### SkResourceCache::Key

缓存键,用于唯一标识缓存条目。

**关键成员变量**:

| 变量 | 类型 | 说明 |
|------|------|------|
| fCount32 | int32_t | 键的 32 位字段数量 (包含本地和用户数据) |
| fHash | uint32_t | 预计算的哈希值 |
| fSharedID_lo/hi | uint32_t | 64 位共享 ID (用于组清理) |
| fNamespace | void* | 命名空间指针 (区分不同类型的键) |

### SkResourceCache::Rec

抽象的缓存记录基类。

**关键方法**:

| 方法 | 说明 |
|------|------|
| getKey() | 返回记录的键 |
| bytesUsed() | 返回记录占用的字节数 |
| canBePurged() | 是否可以被清理 (有外部引用时返回 false) |
| postAddInstall(void*) | 添加到缓存后的回调 |
| getCategory() | 返回类别字符串 (用于调试) |

## 公共 API 函数

### 静态全局方法

```cpp
static bool Find(const Key& key, FindVisitor visitor, void* context)
```
在全局缓存中查找键,调用访问者函数。返回 true 表示找到且访问者返回 true。

```cpp
static void Add(Rec* rec, void* payload = nullptr)
```
添加记录到全局缓存。

```cpp
static size_t GetTotalBytesUsed()
static size_t GetTotalByteLimit()
static size_t SetTotalByteLimit(size_t newLimit)
```
查询和设置全局缓存大小限制。

```cpp
static void PurgeAll()
```
清空全局缓存中的所有条目。

```cpp
static void PostPurgeSharedID(uint64_t sharedID)
```
发送消息,通知所有缓存实例清理指定 sharedID 的条目。

### 实例方法

```cpp
SkResourceCache(DiscardableFactory factory)
SkResourceCache(size_t byteLimit)
```
构造函数:使用可丢弃内存工厂或固定大小限制。

```cpp
bool find(const Key& key, FindVisitor visitor, void* context)
void add(Rec* rec, void* payload = nullptr)
```
查找和添加记录的实例方法。

```cpp
size_t setTotalByteLimit(size_t newLimit)
void purgeSharedID(uint64_t sharedID)
void purgeAll()
```
内存管理和清理方法。

```cpp
SkCachedData* newCachedData(size_t bytes)
```
创建新的缓存数据对象,自动选择可丢弃或固定内存。

## 内部实现细节

### LRU 链表管理

**链表结构**:
- 双向链表: `Rec::fNext` 和 `Rec::fPrev`
- fHead 指向最近使用的条目
- fTail 指向最久未使用的条目

**核心操作**:
```cpp
void moveToHead(Rec* rec)      // 将条目移到链表头 (更新访问时间)
void addToHead(Rec* rec)       // 添加新条目到头部
void release(Rec* rec)         // 从链表中移除
void remove(Rec* rec)          // 移除并删除条目
```

### 哈希表实现

使用 `THashTable` 实现快速查找:
- **哈希函数**: `Key::hash()` 返回预计算的哈希值
- **冲突处理**: 通过 `Key::operator==` 比较所有字段
- **查找复杂度**: O(1) 平均情况

### 内存清理策略

**自动清理触发条件** (purgeAsNeeded):
1. **固定内存模式**: `fTotalBytesUsed >= fTotalByteLimit`
2. **可丢弃内存模式**: `fCount >= SK_DISCARDABLEMEMORY_SCALEDIMAGECACHE_COUNT_LIMIT` (默认 1024)

**清理算法**:
- 从 fTail 开始向前遍历
- 调用 `rec->canBePurged()` 检查是否可清理
- 移除可清理的条目直到满足限制

### 消息总线机制

**PurgeSharedIDMessage**:
- 用于跨线程通知清理特定 sharedID 的缓存
- 通过 `SkMessageBus` 广播消息
- 每个缓存实例通过 `fPurgeSharedIDInbox` 接收消息

**使用场景**:
- SkPixelRef 销毁时通知所有缓存清理相关图像
- 避免悬空指针和内存泄漏

### Key 初始化机制

```cpp
void Key::init(void* nameSpace, uint64_t sharedID, size_t dataSize)
```

**计算布局**:
1. **未哈希字段** (8 字节): fCount32 + fHash
2. **哈希字段** (16 字节): fSharedID_lo + fSharedID_hi + fNamespace
3. **用户数据**: 子类添加的额外字段

**哈希计算**:
```cpp
fHash = SkChecksum::Hash32(this->as32() + kUnhashedLocal32s,
                           (fCount32 - kUnhashedLocal32s) << 2);
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkCachedData | 缓存数据容器,支持引用计数 |
| SkDiscardableMemory | 可丢弃内存抽象 |
| SkMessageBus | 跨线程消息传递 |
| SkTHash | 哈希表实现 |
| SkSynchronizedResourceCache | 线程安全封装 |
| SkChecksum | 哈希值计算 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| SkBitmapCache | 位图缓存实现 |
| SkImageFilter | 图像滤镜结果缓存 |
| SkScaledImageCache | 缩放图像缓存 |
| SkGlyphCache | 字形缓存 |

## 设计模式与设计决策

### 访问者模式

```cpp
typedef bool (*FindVisitor)(const Rec&, void* context);
```

**优点**:
- 允许查找时执行自定义逻辑
- 支持读取数据和验证有效性
- 返回 false 可标记条目为过期并自动清理

### 单例模式

```cpp
static SkSynchronizedResourceCache* get_cache() {
    static SkSynchronizedResourceCache* gResourceCache = nullptr;
    if (nullptr == gResourceCache) {
        gResourceCache = new SkSynchronizedResourceCache(...);
    }
    return gResourceCache;
}
```

**线程安全**: 通过 `SkSynchronizedResourceCache` 包装加锁。

### 写时复制 (COW)

通过引用计数延迟清理:
- 只要有外部引用 (`canBePurged()` 返回 false),条目就不会被删除
- 避免缓存清理时导致正在使用的数据失效

### 策略模式

两种内存管理策略:
1. **固定大小**: 显式内存限制,适合可预测的环境
2. **可丢弃内存**: 依赖系统内存压力,适合移动平台

## 性能考量

### 查找优化

- **O(1) 哈希查找**: 通过预计算哈希值和哈希表
- **LRU 更新**: moveToHead 操作仅涉及指针操作,O(1) 复杂度

### 内存效率

- **Key 紧凑性**: 使用 4 字节对齐,最小化内存浪费
- **引用计数**: 避免数据重复,多个 Rec 可共享底层数据

### 缓存命中率

- **LRU 策略**: 保留最近使用的数据,提高命中率
- **SharedID 清理**: 及时清理无效条目,避免内存浪费

### 调试支持

```cpp
void dump() const
static void TestDumpMemoryStatistics()
static void DumpMemoryStatistics(SkTraceMemoryDump* dump)
```

提供缓存状态可视化,辅助性能分析。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| src/core/SkCachedData.h | 缓存数据容器 |
| src/core/SkSynchronizedResourceCache.h | 线程安全封装 |
| include/private/chromium/SkDiscardableMemory.h | 可丢弃内存接口 |
| src/core/SkMessageBus.h | 消息总线系统 |
| src/core/SkTHash.h | 哈希表实现 |
| src/core/SkChecksum.h | 哈希函数 |
| include/core/SkTraceMemoryDump.h | 内存追踪接口 |
