# StrikeCache - GPU 文本 Strike 缓存

> 源文件: `src/text/gpu/StrikeCache.h`, `src/text/gpu/StrikeCache.cpp`

## 概述

StrikeCache 是 GPU 文本渲染的 Strike（字形缓存）管理器，通过 LRU（最近最少使用）策略管理 TextStrikeBase 对象。每个 TextStrikeBase 以 SkStrikeSpec（描述符）为键索引，存储后端特定的字形数据（如 Atlas 位置信息）。

该缓存系统同时支持 Ganesh 和 Graphite 后端，通过抽象基类 TextStrikeBase 让不同后端存储各自的字形数据类型。本文件还包含 SkStrikePromise::MakeFromBuffer 的实现，用于从序列化数据中恢复 Strike 引用。

## 架构位置

```
sktext::gpu 命名空间
  ├── TextStrikeBase (SkRefCnt) — Strike 抽象基类
  └── StrikeCache — LRU 缓存管理器
```

- **使用者**: GlyphVector::initBackendData
- **后端实现**: Ganesh 和 Graphite 各自提供 TextStrikeBase 的子类

## 主要类与结构体

### TextStrikeBase
Strike 的抽象基类（继承 SkRefCnt）。

**成员变量**:
- `fStrikeCache` — 所属缓存的指针
- `fStrikeSpec` — Strike 查找规范
- `fAlloc` (SkArenaAlloc, 512) — 字形数据的 arena 分配器
- `fNext / fPrev` — LRU 双向链表指针
- `fMemoryUsed` — 内存使用量
- `fRemoved` — 是否已从缓存移除

**静态辅助方法**（供子类使用）:
- `Find(cache, descriptor)` — 从缓存查找 Strike
- `Add(cache, strike)` — 添加 Strike 到缓存

**实例方法**:
- `addMemoryUsed(bytes)` — 增加内存使用计数（同步更新缓存总量）
- `strikeSpec()` / `getDescriptor()` / `memoryUsed()` — 查询方法

### StrikeCache
**成员变量**:
- `fHead / fTail` — LRU 链表头尾
- `fCache` (StrikeHash) — 哈希表（SkDescriptor -> sk_sp<TextStrikeBase>）
- `fCacheSizeLimit` — 缓存大小上限（默认 2MB）
- `fTotalMemoryUsed` — 当前总内存使用
- `fCacheCountLimit` — 缓存条目上限（默认 2048）
- `fCacheCount` — 当前条目数

## 公共 API 函数

```cpp
void StrikeCache::freeAll();
```
释放所有缓存条目。

### TextStrikeBase 静态方法（内联实现）
```cpp
static sk_sp<TextStrikeBase> Find(const StrikeCache*, const SkDescriptor&);
static void Add(StrikeCache*, sk_sp<TextStrikeBase>);
```

## 内部实现细节

### LRU 淘汰策略（internalPurge）
1. 计算需要释放的字节数: max(超出预算, minBytesNeeded)
2. 计算需要释放的条目数: 超出条目限制的数量
3. "no small purges" 策略: 释放量至少为总量的 1/4
4. 从尾部（最旧）开始释放，直到满足字节和条目要求
5. 添加新 Strike 后自动触发 purge

### 链表操作
- `internalAttachToHead`: 新 Strike 插入头部，更新内存和计数
- `internalRemoveStrike`: 从链表和哈希表中移除，标记 fRemoved

### 内存计数
- `addMemoryUsed`: 子类分配字形数据时调用，同步更新 Strike 和缓存的内存计数
- 已移除的 Strike（fRemoved=true）不再更新缓存计数

### SkStrikePromise::MakeFromBuffer
反序列化流程：
1. 从 buffer 读取 SkAutoDescriptor
2. 如果有 SkStrikeClient（跨进程场景），转换 TypefaceID
3. 从 SkStrikeCache（CPU 缓存）查找 Strike
4. 返回 SkStrikePromise

### HashTraits
- `GetKey`: 从 `sk_sp<TextStrikeBase>` 提取 SkDescriptor
- `Hash`: 使用 SkDescriptor 的 checksum

### 调试验证
`validate()` 遍历链表验证内存使用和条目数的一致性。

## 依赖关系

- `SkDescriptor` — Strike 描述符（哈希键）
- `SkStrikeSpec` — Strike 查找规范
- `SkArenaAlloc` — 字形数据分配
- `SkTHash` — 哈希表实现
- `SkStrikeCache` — CPU 端 Strike 缓存
- `SkChromeRemoteGlyphCache` — 远程字形缓存支持
- `SkStrikePromise` — 反序列化中使用

## 设计模式与设计决策

1. **LRU 缓存**: 双向链表 + 哈希表的经典 LRU 实现
2. **抽象基类**: TextStrikeBase 允许不同 GPU 后端存储不同的字形数据
3. **内联查找/添加**: Find 和 Add 定义为内联函数以减少调用开销
4. **Protected 构造/添加**: 子类通过 protected 方法与缓存交互
5. **"No small purges"**: 至少释放 1/4 的缓存，减少频繁小量释放的开销
6. **默认配置**: 2MB / 2048 条目的默认限制，可通过编译宏调整

## 性能考量

- 哈希表查找 O(1)
- LRU 链表操作 O(1)
- 批量淘汰策略（至少 1/4）减少淘汰频率
- SkArenaAlloc 为字形数据提供高效的批量分配
- fRemoved 标记避免已移除 Strike 的重复内存扣除

## 相关文件

- `src/text/gpu/GlyphVector.h` — GlyphVector（使用 TextStrikeBase）
- `src/text/StrikeForGPU.h` — SkStrikePromise
- `src/core/SkStrikeCache.h` — CPU 端 Strike 缓存
- `src/core/SkDescriptor.h` — SkDescriptor
- `src/core/SkStrikeSpec.h` — SkStrikeSpec
