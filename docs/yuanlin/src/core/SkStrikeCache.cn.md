# SkStrikeCache

> 源文件
> - src/core/SkStrikeCache.h
> - src/core/SkStrikeCache.cpp

## 概述

`SkStrikeCache` 是 Skia 字形缓存系统的全局管理器,负责 `SkStrike` 对象的生命周期管理、查找和内存控制。它维护一个 LRU(最近最少使用)缓存策略,确保字形数据在内存限制内高效复用。作为单例模式实现,它为整个应用程序提供统一的字形缓存服务,支持线程安全的并发访问。

主要功能:
- 全局 Strike 缓存管理(单例或线程本地)
- LRU 淘汰策略
- 内存和数量限制控制
- 线程安全的查找和创建操作
- 支持 Pinner 机制防止 Strike 被过早淘汰

## 架构位置

`SkStrikeCache` 在文本渲染系统中的位置:
- **上层**: 服务于 `SkStrikeSpec`、`StrikeForGPU` 接口
- **下层**: 管理 `SkStrike` 对象集合
- **横向**: 与 `SkGraphics` 配合进行全局资源控制
- **模式**: 作为缓存层,介于文本渲染请求和字形数据生成之间

## 主要类与结构体

### SkStrikeCache

**继承关系**:
```
SkStrikeCache : public sktext::StrikeForGPUCacheInterface
```

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fLock` | `mutable SkMutex` | 全局缓存锁 |
| `fHead` / `fTail` | `SkStrike*` | LRU 链表头尾指针 |
| `fStrikeLookup` | `THashTable<sk_sp<SkStrike>, ...>` | 哈希表快速查找 |
| `fCacheSizeLimit` | `size_t` | 内存限制(默认2MB) |
| `fTotalMemoryUsed` | `size_t` | 当前使用内存 |
| `fCacheCountLimit` | `int32_t` | Strike 数量限制(默认2048) |
| `fCacheCount` | `int32_t` | 当前 Strike 数量 |
| `fPinnerCount` | `int32_t` | 被 Pin 的 Strike 数量 |

### StrikeTraits (内部结构体)

哈希表特征类,定义如何从 Strike 中提取键和计算哈希。

**关键方法**:

| 方法 | 说明 |
|------|------|
| `GetKey(const sk_sp<SkStrike>&)` | 获取 SkDescriptor 作为键 |
| `Hash(const SkDescriptor&)` | 计算 Descriptor 的校验和 |

## 公共 API 函数

### 全局访问

```cpp
// 获取全局单例(或线程本地实例)
static SkStrikeCache* GlobalStrikeCache();
```

### Strike 查找与创建

```cpp
// 查找 Strike(仅查找,不创建)
sk_sp<SkStrike> findStrike(const SkDescriptor& desc);

// 创建新 Strike
sk_sp<SkStrike> createStrike(
    const SkStrikeSpec& strikeSpec,
    SkFontMetrics* maybeMetrics = nullptr,
    std::unique_ptr<SkStrikePinner> = nullptr);

// 查找或创建 Strike
sk_sp<SkStrike> findOrCreateStrike(const SkStrikeSpec& strikeSpec);

// GPU 接口:查找或创建作用域 Strike
sk_sp<sktext::StrikeForGPU> findOrCreateScopedStrike(
    const SkStrikeSpec& strikeSpec) override;
```

### 缓存管理

```cpp
// 清除所有缓存
static void PurgeAll();
void purgeAll();

// 清除包括 pinned Strike 的缓存
void purgePinned(size_t minBytesNeeded = 0);

// 限制设置
int getCacheCountLimit() const;
int setCacheCountLimit(int limit);
size_t getCacheSizeLimit() const;
size_t setCacheSizeLimit(size_t limit);

// 使用情况查询
int getCacheCountUsed() const;
size_t getTotalMemoryUsed() const;
```

### 调试与诊断

```cpp
// 输出缓存统计信息
static void Dump();

// 输出内存使用统计
static void DumpMemoryStatistics(SkTraceMemoryDump* dump);
```

## 内部实现细节

### LRU 链表维护

**数据结构**: 双向链表
- `fHead`: 最近使用的 Strike
- `fTail`: 最久未使用的 Strike
- 每个 Strike 包含 `fNext` 和 `fPrev` 指针

**查找优化**:
```cpp
// 快速路径:检查头节点
if (fHead != nullptr && fHead->getDescriptor() == desc) {
    return sk_ref_sp(fHead);
}
// 慢速路径:哈希表查找
sk_sp<SkStrike>* strikeHandle = fStrikeLookup.find(desc);
```

**LRU 更新**:
- 每次访问将 Strike 移到链表头部
- 新创建的 Strike 插入到头部

### 淘汰策略

**触发条件**:
1. 内存超限: `fTotalMemoryUsed > fCacheSizeLimit`
2. 数量超限: `fCacheCount > fCacheCountLimit`

**淘汰规则**:
```cpp
size_t bytesNeeded = std::max(
    fTotalMemoryUsed - fCacheSizeLimit,
    minBytesNeeded
);
bytesNeeded = std::max(bytesNeeded, fTotalMemoryUsed >> 2); // 至少淘汰25%

int countNeeded = std::max(
    fCacheCount - fCacheCountLimit,
    fCacheCount >> 2
);
```

**保护机制**:
- 带 `SkStrikePinner` 的 Strike 默认不被淘汰
- 除非调用 `purgePinned` 并且 `pinner->canDelete()` 返回 true

### 线程安全

**锁策略**:
- 所有公共方法使用 `SkAutoMutexExclusive` 持有 `fLock`
- Strike 内部有自己的锁(`fStrikeLock`)
- 二级锁设计:
  1. 缓存级别锁(管理集合)
  2. Strike 级别锁(访问字形数据)

**死锁预防**:
- Strike 的 `updateMemoryUsage` 从 Strike 锁内部获取缓存锁
- 使用 `SK_EXCLUDES` / `SK_REQUIRES` 注解标记锁顺序

### 单例模式变体

**全局单例**:
```cpp
static auto* cache = new SkStrikeCache;
return cache;
```

**线程本地模式** (实验性):
```cpp
if (gSkUseThreadLocalStrikeCaches_...) {
    static thread_local auto* cache = new SkStrikeCache;
    return cache;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkStrike` | 被管理的缓存对象 |
| `SkStrikeSpec` | 创建 Strike 的规格 |
| `SkDescriptor` | 查找键 |
| `SkMutex` | 线程同步 |
| `SkTHash` | 哈希表实现 |
| `SkGraphics` | 全局资源控制接口 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `SkStrikeSpec` | 调用 `findOrCreateStrike` |
| `SkCanvas` | 通过字形绘制路径间接使用 |
| GPU 文本渲染 | 实现 `StrikeForGPUCacheInterface` |
| `SkGraphics` | 作为全局缓存访问点 |

## 设计模式与设计决策

### 设计模式

1. **单例模式**: 全局唯一的缓存管理器
2. **对象池**: 复用 Strike 对象,避免重复创建
3. **策略模式**: LRU 淘汰策略可配置
4. **外观模式**: 统一缓存操作接口
5. **观察者模式**: 通过 `SkStrikePinner` 监听 Strike 生命周期

### 设计决策

1. **LRU vs LFU**:
   - 选择 LRU 因为文本渲染具有时间局部性
   - 最近使用的字形很可能再次使用

2. **双数据结构**:
   - 哈希表: O(1) 查找
   - 双向链表: O(1) LRU 更新
   - 权衡: 额外指针开销 vs 性能提升

3. **两级限制**:
   - 内存限制: 防止内存过度使用
   - 数量限制: 防止哈希表过大
   - 同时检查两者,取最严格限制

4. **Pinner 机制**:
   - GPU 渲染需要在帧期间保持 Strike 存活
   - 可插拔的生命周期扩展
   - 避免核心类依赖 GPU 模块

5. **延迟淘汰**:
   - 不立即淘汰,批量处理
   - 至少淘汰 25% 超出部分,减少频繁淘汰

6. **头节点优化**:
   - 检查 `fHead` 作为快速路径
   - 利用时间局部性,大多数查找命中最近使用的 Strike

## 性能考量

1. **快速查找**:
   - 头节点快速路径(最常见情况)
   - 哈希表 O(1) 查找
   - Descriptor 预计算校验和

2. **最小淘汰开销**:
   - 批量淘汰,而非每次插入都淘汰
   - 从链表尾部开始,快速找到淘汰候选

3. **锁粒度**:
   - 缓存锁保护集合操作
   - Strike 锁保护字形数据
   - 减少锁争用时间

4. **内存效率**:
   - Strike 共享 Typeface 和 ScalerContext
   - 引用计数避免重复内存分配
   - 字形数据在 Arena 中连续分配

5. **调试开销**:
   - `validate()` 仅在 DEBUG 模式启用
   - 生产环境零额外开销

6. **默认限制**:
   ```cpp
   #define SK_DEFAULT_FONT_CACHE_COUNT_LIMIT 2048
   #define SK_DEFAULT_FONT_CACHE_LIMIT (2 * 1024 * 1024)
   ```
   - 可通过 SkUserConfig.h 或编译选项配置
   - 平衡内存使用和性能

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkStrike.h` | Strike 缓存对象定义 |
| `src/core/SkStrikeSpec.h` | Strike 规格 |
| `src/core/SkDescriptor.h` | 缓存查找键 |
| `src/core/SkTHash.h` | 哈希表实现 |
| `include/core/SkGraphics.h` | 全局资源控制 |
| `src/text/StrikeForGPU.h` | GPU Strike 接口 |
| `include/core/SkTraceMemoryDump.h` | 内存诊断接口 |
