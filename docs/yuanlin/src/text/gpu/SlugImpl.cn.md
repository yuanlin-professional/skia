# SlugImpl - Slug 实现

> 源文件: `src/text/gpu/SlugImpl.h`, `src/text/gpu/SlugImpl.cpp`

## 概述

SlugImpl 是 Slug 接口的具体实现。Slug 是 Skia 为 Chromium 设计的可序列化文本绘制对象，它将文本的 Strike 计算与实际渲染分离：在创建时完成所有 Strike 相关的预处理（确定字形类型、生成 SubRun），然后可以被序列化传输到另一个进程（如 GPU 进程）进行渲染。

Slug 与 TextBlob 的区别在于：Slug 设计为可跨进程序列化，而 TextBlob 主要用于进程内的缓存重用。

## 架构位置

```
Slug (include/private/chromium/Slug.h)
  └── SlugImpl (具体实现)
        ├── SubRunAllocator (内存管理)
        └── SubRunContainer (SubRun 集合)
```

- **创建者**: SkDevice、sktext::gpu::MakeSlug
- **消费者**: Chromium 的 GPU 进程

## 主要类与结构体

### SlugImpl
**成员变量**（按声明顺序，allocator 必须最先销毁）:
- `fAlloc` (SubRunAllocator): 内存分配器
- `fSubRuns` (SubRunContainerOwner): SubRun 容器
- `fSourceBounds` (SkRect): 源空间边界
- `fOrigin` (SkPoint): 绘制原点

**内存管理**: 使用 placement new，对象和 Arena 在同一次分配中完成。`operator new(size_t)` 被禁止（必须使用 placement new）。

## 公共 API 函数

```cpp
static sk_sp<SlugImpl> Make(const SkMatrix& viewMatrix,
                            const GlyphRunList& glyphRunList,
                            const SkPaint& paint,
                            SkStrikeDeviceInfo strikeDeviceInfo,
                            StrikeForGPUCacheInterface* strikeCache);
```
从 GlyphRunList 创建 Slug。如果所有 SubRun 为空则返回 nullptr。

```cpp
static sk_sp<Slug> MakeFromBuffer(SkReadBuffer& buffer, const SkStrikeClient* client);
```
从序列化数据反序列化 Slug。

```cpp
void doFlatten(SkWriteBuffer& buffer) const override;
```
序列化 Slug 数据。

## 内部实现细节

### 创建流程
1. 估算分配大小：`SubRunContainer::EstimateAllocSize()`
2. 联合分配对象+Arena：`AllocateClassMemoryAndArena<SlugImpl>()`
3. 计算 positionMatrix = viewMatrix * translate(origin)
4. 创建 SubRunContainer：`SubRunContainer::MakeInAlloc()`
5. 使用 placement new 初始化 SlugImpl
6. 若 SubRun 容器为空则返回 nullptr

### 反序列化流程
1. 读取 sourceBounds 和 origin
2. 读取分配大小提示
3. 联合分配并创建 SubRunContainer
4. 使用 placement new 初始化 SlugImpl

### 反序列化注册
`Slug::AddDeserialProcs` 将反序列化回调注册到 `SkDeserialProcs` 中，允许 SkPicture 反序列化 Slug。

## 依赖关系

- `Slug` — Chromium 专用的公共接口
- `SubRunContainer` — SubRun 管理
- `SubRunAllocator` — 内存分配
- `GlyphRunList` — 输入数据
- `SkStrikeDeviceInfo` — 设备信息

## 设计模式与设计决策

1. **联合分配**: 对象和 Arena 共享一次 `::operator new` 调用
2. **Placement new**: 禁止常规 new，强制使用联合分配
3. **空检查**: SubRun 为空时返回 nullptr（如单空格 RSXForm blob）
4. **序列化设计**: 为跨进程通信优化，支持 SkStrikeClient 转换 TypefaceID

## 性能考量

- 创建时通过 EstimateAllocSize 预估内存，减少分配次数
- 联合分配避免了对象和 Arena 的独立堆分配
- 空 Slug 提前返回 nullptr 避免无效渲染

## 相关文件

- `include/private/chromium/Slug.h` — Slug 公共接口
- `src/text/gpu/SubRunContainer.h` — SubRun 容器
- `src/text/gpu/TextBlob.h` — TextBlob（类似但用于进程内）
- `src/core/SkDevice.h` — 创建 Slug 的入口
