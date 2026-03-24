# ParagraphCache

> 源文件: [modules/skparagraph/include/ParagraphCache.h](../../../../modules/skparagraph/include/ParagraphCache.h)

## 概述

`ParagraphCache` 实现了段落排版结果的缓存机制，用于避免对相同或相似文本内容的重复排版计算。当段落的文本内容、样式和布局参数未发生变化时，可以直接复用之前的排版结果。该类由 `FontCollection` 拥有，服务于所有通过同一字体集合创建的段落。它还包含文本编辑检测功能，用于优化文本编辑场景下的增量排版。

## 架构位置

```
skia::textlayout 命名空间
  FontCollection
    └── ParagraphCache  ← 本文件定义
          ├── findParagraph(ParagraphImpl*) - 查找缓存
          ├── updateParagraph(ParagraphImpl*) - 更新缓存
          └── 内部 Cache 结构体管理缓存条目
```

`ParagraphCache` 嵌入在 `FontCollection` 中，生命周期与字体集合绑定。

## 主要类与结构体

### ParagraphCache
- 段落排版结果缓存管理器
- 使用互斥锁（`SkMutex`）保护并发访问
- 内部使用 `Cache` 结构体（前向声明）存储缓存条目
- 支持缓存统计和测试用的检查器回调

### ParagraphCache::Entry（内部结构体）
- 缓存条目，存储段落的排版结果
- 在 `private` 区域前向声明

## 公共 API 函数

### 缓存操作
```cpp
void abandon();
```
放弃缓存（通常在字体集合销毁时调用）。

```cpp
void reset();
```
清空所有缓存条目。

```cpp
bool updateParagraph(ParagraphImpl* paragraph);
```
将段落的排版结果更新到缓存中。返回是否成功。

```cpp
bool findParagraph(ParagraphImpl* paragraph);
```
在缓存中查找匹配的段落排版结果，如找到则将缓存数据应用到传入的段落对象。

### 文本编辑检测
```cpp
bool isPossiblyTextEditing(ParagraphImpl* paragraph);
```
检测当前段落是否可能处于文本编辑状态（即与缓存中的段落仅有微小差异），用于启用增量排版优化。

### 测试与调试
```cpp
void setChecker(std::function<void(ParagraphImpl* impl, const char*, bool)> checker);
```
设置缓存检查器回调，用于测试时验证缓存行为。

```cpp
void printStatistics();
```
打印缓存统计信息（由 `PARAGRAPH_CACHE_STATS` 宏控制）。

```cpp
void turnOn(bool value);
```
启用或禁用缓存。

```cpp
int count();
```
返回当前缓存条目数量。

## 内部实现细节

### 线程安全

使用 `SkMutex` 互斥锁保护缓存的所有读写操作，确保多线程环境下的安全性。锁声明为 `mutable`，允许在 `const` 方法中加锁。

### 缓存更新机制

- `updateFrom(const ParagraphImpl*, Entry*)` - 从段落对象提取数据到缓存条目
- `updateTo(ParagraphImpl*, const Entry*)` - 从缓存条目恢复数据到段落对象

这种双向更新设计将缓存的序列化/反序列化逻辑集中管理。

### 统计功能

`PARAGRAPH_CACHE_STATS` 宏在头文件中默认定义，启用缓存命中率等统计信息的收集。`printStatistics()` 输出这些统计数据，用于性能分析和调优。

### Pimpl 模式

`Cache` 结构体通过 `std::unique_ptr<Cache>` 持有，使用 Pimpl 惯用法隐藏缓存的实际实现细节（如哈希表结构、哈希函数等）。

## 依赖关系

- **Skia 私有工具**: `SkMutex`（互斥锁）
- **标准库**: `<functional>`（`std::function`）
- **skparagraph 模块**: `ParagraphImpl`（前向声明）

## 设计模式与设计决策

1. **Pimpl 惯用法**: `Cache` 结构体的实现隐藏在 cpp 文件中，减少头文件的编译依赖，加速编译。

2. **缓存失效策略**: `abandon()` 和 `reset()` 提供了两种不同级别的缓存清除机制。`turnOn(false)` 可以完全禁用缓存（用于调试或测试）。

3. **测试友好设计**: `setChecker` 回调允许测试代码注入验证逻辑，`count()` 和 `printStatistics()` 提供缓存状态的可观测性。

4. **增量排版检测**: `isPossiblyTextEditing` 方法检测文本编辑场景，这是一种启发式优化，在用户逐字输入时避免完整的重新排版。

5. **互斥锁保护**: 整个缓存通过单一互斥锁保护，简单但可能在高并发场景下成为瓶颈。

## 性能考量

- 缓存查找（`findParagraph`）是段落布局路径上的关键优化，可以将 O(N) 的排版计算降低为 O(1) 的缓存查找。
- 互斥锁可能在多线程文本渲染场景下引入锁竞争。
- `isPossiblyTextEditing` 的增量排版检测可以显著减少文本编辑场景下的排版开销。
- `PARAGRAPH_CACHE_STATS` 统计功能在发布版本中可能需要禁用以避免微小的性能开销。

## 相关文件

- `modules/skparagraph/include/FontCollection.h` - 持有 ParagraphCache 实例
- `modules/skparagraph/src/ParagraphCache.cpp` - 实际实现
- `modules/skparagraph/src/ParagraphImpl.h` - 被缓存的段落实现类
