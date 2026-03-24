# ClipAtlasManager (裁剪遮罩图集管理器)

> 源文件：[src/gpu/graphite/ClipAtlasManager.h](../../../../src/gpu/graphite/ClipAtlasManager.h)、[src/gpu/graphite/ClipAtlasManager.cpp](../../../../src/gpu/graphite/ClipAtlasManager.cpp)

## 概述

`ClipAtlasManager` 负责管理裁剪遮罩（clip mask）的光栅化、缓存和图集（atlas）分配。当 Graphite 渲染管线遇到需要软件光栅化的裁剪路径时，`ClipAtlasManager` 会将裁剪路径渲染为 alpha 遮罩，并将结果存储在 `DrawAtlas` 纹理图集中。通过基于唯一键的缓存机制，相同的裁剪组合可以在多次绘制间复用，避免重复光栅化。

该管理器维护两个独立的图集：一个用于可通过路径键（path key）标识的裁剪，另一个用于仅能通过 SaveRecord ID 标识的裁剪。两者分离的原因是 SaveRecord 键的裁剪更加短暂——一旦对应的保存记录被弹出，就不会再被使用。

## 架构位置

`ClipAtlasManager` 位于 Graphite 渲染管线中裁剪处理与纹理图集管理的交汇处：

- **上游**：`ClipStack` 提供裁剪元素列表和元素的唯一标识。
- **同级**：与 `DrawAtlas`（通用图集分配器）紧密协作，管理图集空间分配与驱逐。
- **下游**：生成的裁剪遮罩纹理代理（`TextureProxy`）被传递给绘制命令，在着色器中用于裁剪测试。
- **Recorder** 持有 `ClipAtlasManager` 实例，在 flush 时调用 `recordUploads` 将数据上传到 GPU。

## 主要类与结构体

### `ClipAtlasManager`
顶层管理类，协调两个内部 `DrawAtlasMgr` 实例。

**成员变量：**
- `fRecorder`：指向所属 Recorder 的指针。
- `fPathKeyAtlasMgr`：管理路径键（稳定、可长期复用）裁剪遮罩的图集，尺寸为 2048x2048，分为 4 个 1024x1024 Plot。
- `fSaveRecordKeyAtlasMgr`：管理 SaveRecord 键（短暂）裁剪遮罩的图集，尺寸为 1024x1024，单个 1024x1024 Plot。

### `ClipAtlasManager::DrawAtlasMgr` (内部类)
封装了单个 `DrawAtlas` 实例及其关联的缓存逻辑。同时实现了 `DrawAtlas::GenerationCounter` 和 `DrawAtlas::PlotEvictionCallback` 接口。

**核心数据结构：**
- `fDrawAtlas`：底层图集分配器。
- `fMaskCache`：`THashMap<UniqueKey, MaskHashEntry>`，从裁剪键映射到图集位置。支持链表结构以存储同一键但不同边界的多个条目。
- `fKeyLists`：每个 Plot 对应一个 `MaskKeyList`，存储该 Plot 中所有条目的键，用于 Plot 驱逐时批量清除缓存。

### `MaskHashEntry` (内部结构)
缓存条目，记录裁剪遮罩在图集中的位置：
- `fBounds`：遮罩的关键边界（相对于完整变换后遮罩的位置）。
- `fLocator`：图集定位器，包含页面索引和 Plot 内位置。
- `fNext`：链表指针，同一键可关联多个不同边界的条目。

### `MaskKeyEntry` (内部结构)
Plot 驱逐跟踪条目：
- `fKey`：对应的唯一键。
- `fBounds`：对应的边界。
- 内部链表接口（`SK_DECLARE_INTERNAL_LLIST_INTERFACE`）。

## 公共 API 函数

### `ClipAtlasManager::findOrCreateEntry`
```cpp
sk_sp<TextureProxy> findOrCreateEntry(uint32_t stackRecordID,
                                      const ClipStack::ElementList*,
                                      SkIRect maskDeviceBounds,
                                      SkIPoint* outPos);
```
核心入口函数。首先尝试在对应的图集管理器（路径键或 SaveRecord 键）中查找已缓存的遮罩。如果图集中未找到，则回退到 `ProxyCache` 创建独立纹理代理。`outPos` 输出遮罩在返回纹理中的偏移位置。

### `recordUploads(DrawContext*) -> bool`
将两个图集管理器中的待上传数据记录到 DrawContext，在 flush 时执行 GPU 上传。

### `compact()`
压缩两个图集管理器的内存，释放不再使用的 Plot。

### `freeGpuResources()`
释放两个图集管理器的 GPU 资源。

### `evictAtlases()`
强制驱逐两个图集的所有 Plot，清空所有缓存。

## 内部实现细节

### 裁剪遮罩光栅化
遮罩的光栅化由 `RasterMaskHelper` 完成。光栅化逻辑根据裁剪操作类型（Intersect / Difference）确定初始 alpha 值和绘制策略：

- **第一个 Intersect 元素**：清除缓冲区为 0，直接以覆盖度 1 绘制形状。
- **后续 Intersect 元素**：以覆盖度 0 绘制形状的反转（inverse fill），擦除形状外部区域。
- **Difference 元素**：以覆盖度 0 直接绘制形状，从遮罩中减去。

每个条目周围有 1 像素的填充（`kEntryPadding`），确保反转裁剪等情况下的上下文正确。

### 缓存查找与匹配策略
缓存使用 `GenerateClipMaskKey` 生成唯一键。在图集缓存中查找时：
1. 先不包含边界生成键，在对应图集管理器中查找。
2. 如果缓存命中，还需检查已缓存条目的边界是否包含请求的边界。同一键可能有多个不同大小的条目（链表结构），选择最小的包含请求边界的条目。
3. 如果图集中未命中，包含边界重新生成键，回退到 `ProxyCache` 创建独立纹理。

### Plot 驱逐处理
当 `DrawAtlas` 驱逐一个 Plot 时，`evict(PlotLocator)` 回调被触发：
1. 通过 `fKeyLists[index]` 获取该 Plot 的所有键条目。
2. 遍历每个键条目，在 `fMaskCache` 中找到并删除对应的 hash 条目。
3. 维护 `fHashEntryCount` 和 `fListEntryCount` 一致性断言。

链表删除逻辑处理三种情况：中间/尾部节点删除、头节点有后继时替换、头节点无后继时移除整个键。

## 依赖关系

### 上游依赖
- `DrawAtlas`：底层图集分配与管理。
- `ClipStack` / `ClipStack::ElementList`：裁剪元素来源。
- `RasterMaskHelper`：CPU 光栅化引擎。
- `Recorder`：提供 TokenTracker、ProxyCache、Caps 等资源。
- `ProxyCache`：作为图集未命中时的回退缓存。

### 下游使用者
- `DrawContext`：通过 `recordUploads` 接收上传命令。
- 着色器阶段：使用返回的 `TextureProxy` 进行裁剪测试。

## 设计模式与设计决策

1. **双图集分离策略**：稳定的路径键裁剪和短暂的 SaveRecord 键裁剪使用不同大小的图集。SaveRecord 键的图集更小（1024x1024 vs 2048x2048），因为这类裁剪使用频率低且生命周期短，避免浪费 GPU 内存。

2. **多级缓存回退**：先查图集缓存 -> 图集未命中时使用 ProxyCache 创建独立纹理。这种层级结构在空间效率和命中率之间取得平衡。

3. **链表结构处理同键不同边界**：相同的裁剪组合可能在不同视口偏移下有不同的边界需求，链表允许存储同一键的多个版本。

4. **驱逐回调一致性维护**：通过反向索引（每个 Plot 维护键列表）和引用计数断言确保缓存与图集状态始终一致。

## 性能考量

- **CPU 光栅化开销**：裁剪遮罩的光栅化在 CPU 上执行（`RasterMaskHelper`），对于复杂裁剪路径可能较慢。缓存机制是关键优化，避免重复光栅化。
- **图集空间效率**：每个条目有 1 像素填充，增加约 2 像素的宽高开销。图集大小固定（2048x2048 / 1024x1024），Plot 数量有限，满时需要驱逐。
- **内存管理**：`compact()` 方法在 flush 后调用，释放不再使用的 Plot，控制 GPU 内存占用。
- **缓存命中优化**：边界包含检查允许更大的已缓存遮罩服务于更小的请求区域，减少重复绘制。

## 相关文件

- `src/gpu/graphite/DrawAtlas.h/.cpp`：通用图集分配器实现。
- `src/gpu/graphite/ClipStack.h/.cpp`：裁剪栈与裁剪元素管理。
- `src/gpu/graphite/RasterPathUtils.h/.cpp`：CPU 光栅化辅助工具。
- `src/gpu/graphite/ProxyCache.h/.cpp`：纹理代理缓存。
- `src/gpu/graphite/TextureProxy.h`：纹理代理类。
- `src/gpu/graphite/DrawContext.h`：绘制上下文，接收上传命令。
