# ParagraphCache - 段落缓存

> 源文件: `modules/skparagraph/src/ParagraphCache.cpp`

## 概述

ParagraphCache 是 Skia 文本排版模块（skparagraph）中的段落排版结果缓存系统。它使用 LRU（最近最少使用）策略缓存段落的文本塑形（shaping）和 Unicode 分析结果，以避免在相同文本和样式配置下重复执行高开销的排版计算。缓存的核心数据包括 Run（文本塑形运行）、Cluster（字符簇）、代码单元属性、单词边界、BiDi 区域等。

## 架构位置

ParagraphCache 位于 `skia::textlayout` 命名空间内，是 FontCollection 的子组件。它处于段落排版管线的入口，在 ParagraphImpl 进行完整排版之前先查询缓存，命中则直接复用历史结果，未命中则在排版完成后将结果写入缓存。

**调用链**: `ParagraphBuilder::Build()` -> `ParagraphImpl::layout()` -> `ParagraphCache::findParagraph()` / `updateParagraph()`

## 主要类与结构体

### `ParagraphCache`
顶层缓存管理器，对外提供查询、更新、重置等接口。内部持有一个 `Cache` 结构体和一个互斥锁 `fParagraphMutex`。

### `ParagraphCache::Cache`（内部结构体）
封装实际的 LRU 缓存数据结构：
- `fLRUCacheMap`: 基于 `SkLRUCache` 的哈希映射，容量上限 128 条目
- `fCacheIsOn`: 缓存开关
- `fLastCachedValue`: 指向最后一次缓存的值，用于文本编辑检测
- 可选的统计字段（`PARAGRAPH_CACHE_STATS` 宏守护）

### `ParagraphCacheKey`
缓存键，由段落的文本内容、占位符列表、文本样式列表和段落样式组成。实现了自定义哈希计算（`computeHash`）和相等性比较（`operator==`）。

### `ParagraphCacheValue`
缓存值，存储排版后的结果数据：
- `fRuns`: 文本塑形运行数组
- `fClusters`: 字符簇数组
- `fClustersIndexFromCodeUnit`: 代码单元到簇的索引映射
- `fCodeUnitProperties`: ICU 代码单元属性
- `fWords`, `fBidiRegions`: 单词边界和 BiDi 区域
- `fHasLineBreaks`, `fHasWhitespacesInside`, `fTrailingSpaces`: 布局特征标记

### `ParagraphCache::Entry`
缓存条目的包装器，持有 `ParagraphCacheValue` 的唯一指针。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `ParagraphCache()` / `~ParagraphCache()` | 构造和析构，初始化内部 Cache |
| `turnOn(bool value)` | 启用或禁用缓存 |
| `count()` | 返回当前缓存条目数 |
| `findParagraph(ParagraphImpl*)` | 查找段落的缓存结果，命中时更新段落数据并返回 true |
| `updateParagraph(ParagraphImpl*)` | 将新的排版结果写入缓存，如果检测到可能是文本编辑则跳过 |
| `printStatistics()` | 打印缓存命中统计信息（需 `PARAGRAPH_CACHE_STATS` 宏） |
| `abandon()` / `reset()` | 清空缓存并重置统计数据 |

## 内部实现细节

### 哈希计算（`ParagraphCacheKey::computeHash`）
使用自定义的 `mix` 函数（Jenkins hash 变体），对以下数据进行混合哈希：
1. 占位符的范围、尺寸、对齐方式和基线偏移
2. 文本样式的字间距、词间距、区域设置、行高、基线偏移、字体族名、字体特性、字体参数、字体样式和大小
3. 段落样式的行高、文本方向、tab 替换标志
4. 支撑样式（Strut Style）的各项参数
5. 文本内容本身

### 浮点数松弛（`relax` 函数）
为匹配 Flutter 测试，将浮点数四舍五入到 1/4096 精度后再转为位表示，确保微小浮点差异不影响缓存匹配。

### 精确相等（`exactlyEqual`）
使用 `x == y || (x != x && y != y)` 的方式同时处理 NaN 的相等比较。

### 文本编辑检测（`isPossiblyTextEditing`）
当新段落文本与最后缓存的文本共享前 40 个字符或后 40 个字符时，认为用户可能正在编辑文本。此时跳过缓存写入，避免缓存污染。阈值由 `NOCACHE_PREFIX_LENGTH` (40) 定义。

### 缓存更新流程（`updateTo`）
从缓存条目中将所有排版数据复制到 ParagraphImpl，包含以下步骤：
1. 清空并复制 `fRuns` 数组
2. 复制 `fClusters` 字符簇数组
3. 复制 `fClustersIndexFromCodeUnit` 索引映射
4. 复制 `fCodeUnitProperties` ICU 属性
5. 复制 `fWords` 和 `fBidiRegions`
6. 复制布局标记（`fHasLineBreaks`, `fHasWhitespacesInside`, `fTrailingSpaces`）
7. 遍历所有 Run 和 Cluster，调用 `setOwner(paragraph)` 重新绑定所有者指针

### 缓存查找流程（`findParagraph`）
1. 检查缓存开关，若关闭则直接返回 false
2. 更新统计计数器（条件编译）
3. 获取互斥锁
4. 从 ParagraphImpl 构造 ParagraphCacheKey
5. 在 LRU 缓存中查找该键
6. 未命中：增加未命中计数，调用 checker 回调，返回 false
7. 命中：调用 updateTo 复制数据到 paragraph，调用 checker 回调，返回 true

### 缓存写入流程（`updateParagraph`）
1. 检查缓存开关
2. 获取互斥锁
3. 构造 ParagraphCacheKey 并查找
4. 若键已存在则跳过（不更新已有条目）
5. 调用 `isPossiblyTextEditing` 检测文本编辑
6. 若可能是编辑则跳过缓存写入
7. 创建新的 ParagraphCacheValue 并插入 LRU 缓存
8. 更新 `fLastCachedValue` 指针

### 相等性比较（`ParagraphCacheKey::operator==`）
比较两个缓存键的完整流程：
1. 比较文本长度、占位符数量、文本内容、文本样式数量
2. 比较段落样式的行高、文本方向、支撑样式、tab 替换标志
3. 逐一比较文本样式的字体相关属性（`equalsByFonts`）和范围
4. 逐一比较占位符的样式和范围（跳过零宽占位符）

## 依赖关系

- **SkLRUCache**: 提供 LRU 缓存数据结构
- **SkFloatBits**: 提供 `SkFloat2Bits` 等浮点位操作工具
- **ParagraphImpl**: 段落实现，作为缓存读写的数据源和目标
- **FontArguments**: 字体参数的可选值和哈希支持
- **SkAutoMutexExclusive**: 线程安全的互斥锁守护

## 设计模式与设计决策

1. **LRU 缓存策略**: 固定容量 128 条目，自动淘汰最久未使用的条目，平衡内存占用和命中率。
2. **键值分离**: CacheKey 包含输入参数，CacheValue 包含输出结果，职责清晰。
3. **互斥锁保护**: `findParagraph` 和 `updateParagraph` 均使用 `SkAutoMutexExclusive` 保证线程安全。
4. **文本编辑启发式**: 通过比较文本前后缀来检测可能的文本编辑行为，避免在交互式输入场景下缓存大量一次性变体，这是一个针对移动端实时输入场景的实用优化。
5. **浮点松弛**: `relax` 函数是为了与 Flutter 框架兼容而引入的精度折中设计。
6. **调试支持**: 通过条件编译宏 `PARAGRAPH_CACHE_STATS` 提供缓存命中率统计。

## 性能考量

- **缓存命中时开销极低**: 仅需哈希查找和数组复制，避免重新调用 HarfBuzz 塑形引擎和 ICU 分析
- **缓存容量限制**: 128 条目上限防止内存膨胀
- **文本编辑检测**: `isPossiblyTextEditing` 使用 `strncmp` 对前后各 40 字节进行快速比较，时间复杂度 O(1)
- **哈希冲突处理**: `operator==` 执行完整的深度比较，确保在哈希冲突时的正确性
- **线程安全开销**: 每次缓存访问需获取互斥锁，在高并发场景下可能成为瓶颈

## 相关文件

- `modules/skparagraph/include/ParagraphCache.h` - ParagraphCache 的公共头文件声明
- `modules/skparagraph/src/ParagraphImpl.h` - ParagraphImpl 的定义，缓存的数据源
- `modules/skparagraph/include/FontArguments.h` - 字体参数类型定义
- `src/core/SkLRUCache.h` - LRU 缓存模板实现
- `src/base/SkFloatBits.h` - 浮点位操作工具

## 使用注意事项

1. ParagraphCache 默认开启，可通过 `turnOn(false)` 关闭
2. 缓存键基于文本内容和样式，不包含宽度信息——同一文本不同宽度的排版共享缓存
3. 缓存仅存储塑形和 Unicode 分析结果，不存储行布局结果
4. `reset()` 应在字体变更时调用以清除过期缓存
5. 文本编辑检测（`isPossiblyTextEditing`）可能导致正在编辑的长文本不被缓存
6. 哈希冲突时的深度比较包含逐元素的文本样式和占位符比较，开销不可忽略
7. `fChecker` 回调可用于调试缓存行为（如记录命中/未命中事件）
