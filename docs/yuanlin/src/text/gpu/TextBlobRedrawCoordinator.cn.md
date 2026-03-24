# TextBlobRedrawCoordinator

> 源文件
> - src/text/gpu/TextBlobRedrawCoordinator.h
> - src/text/gpu/TextBlobRedrawCoordinator.cpp

## 概述

`TextBlobRedrawCoordinator` 是 Skia GPU 文本渲染系统的核心缓存协调器，负责管理和重用 `TextBlob` 对象以优化文本绘制性能。它实现了一个三层缓存系统，通过智能匹配策略决定是否可以重用已有的绘制数据，并通过 LRU（Least Recently Used）策略和消息总线机制管理内存预算。

## 架构位置

该组件位于 Skia 文本渲染层的 GPU 子系统（`src/text/gpu/`），是文本渲染管道的中心协调器：

```
SkCanvas (用户接口)
   ↓
GlyphRunList (文本输入)
   ↓
TextBlobRedrawCoordinator (缓存管理)
   ↓
TextBlob (GPU 绘制数据)
   ↓
SubRunContainer (子运行)
   ↓
Atlas (GPU 纹理图集)
```

## 主要类与结构体

### TextBlobRedrawCoordinator 类

核心协调器类，管理文本块的缓存、查找和清理。

**成员变量：**
- `fBlobList`: `TextBlobList` - LRU 双向链表，按访问时间排序
- `fBlobIDCache`: `THashMap<uint32_t, BlobIDCacheEntry>` - 第一层缓存，按 `SkTextBlob::uniqueID` 索引
- `fSizeBudget`: `size_t` - 缓存内存预算（默认 4MB）
- `fCurrentSize`: `size_t` - 当前使用的内存大小
- `fMessageBusID`: `uint32_t` - 消息总线 ID（通常是 GrContext 的 ID）
- `fPurgeBlobInbox`: 消息收件箱，接收清理请求
- `fSpinLock`: 自旋锁，保护并发访问

### BlobIDCacheEntry 结构体

第一层缓存的条目，将单个 `SkTextBlob` ID 映射到多个 `TextBlob` 对象。

**成员变量：**
- `fID`: `uint32_t` - `SkTextBlob` 的唯一 ID
- `fBlobs`: `STArray<1, sk_sp<TextBlob>>` - 相关的 `TextBlob` 列表（通常只有一个）

**方法：**
- `addBlob()` - 添加新的 `TextBlob`
- `removeBlob()` - 移除指定的 `TextBlob`
- `find()` - 根据 `TextBlob::Key` 查找匹配的 `TextBlob`
- `findBlobIndex()` - 查找 blob 的索引

### PurgeBlobMessage 结构体

用于跨线程通信的清理消息。

**成员变量：**
- `fBlobID`: `uint32_t` - 要清理的 blob ID
- `fContextID`: `uint32_t` - 目标上下文 ID

## 公共 API 函数

### 核心绘制接口
```cpp
void drawGlyphRunList(SkCanvas* canvas,
                      const SkMatrix& viewMatrix,
                      const GlyphRunList& glyphRunList,
                      const SkPaint& paint,
                      SkStrikeDeviceInfo strikeDeviceInfo,
                      const AtlasDrawDelegate&)
```
主要绘制入口，查找或创建 `TextBlob` 并执行绘制。

### 内存管理接口
```cpp
void freeAll()                     // 清空所有缓存
void purgeStaleBlobs()             // 清理过期的 blob
size_t usedBytes() const           // 查询当前内存使用量
bool isOverBudget() const          // 检查是否超出预算
```

## 内部实现细节

### 三层缓存系统

**第一层：SkTextBlob ID 映射**
- 键：`SkTextBlob::uniqueID`（来自用户的 `SkTextBlob` 对象）
- 值：`BlobIDCacheEntry`，包含一个或多个 `TextBlob` 对象
- 用途：快速定位相同源文本块的候选缓存

**第二层：TextBlob Key 匹配**
- 键：`TextBlob::Key`，包含绘制参数的哈希（位置矩阵、paint、设备信息等）
- 值：`sk_sp<TextBlob>`
- 用途：找到绘制参数匹配的 `TextBlob`

**第三层：SubRun 重用检查**
- 每个 `TextBlob` 包含多个 `SubRun`
- 调用 `blob->canReuse(paint, positionMatrix)` 验证各子运行是否仍然有效
- 考虑字形缓存、矩阵变换等因素

### 查找或创建流程（findOrCreateBlob）

```cpp
1. 计算位置矩阵（视图矩阵 + 原点偏移）
2. 生成 TextBlob::Key
3. 如果可缓存，尝试从缓存查找
4. 检查找到的 blob 是否可重用
5. 如果不可重用，移除旧 blob，创建新 blob
6. 如果可缓存，将新 blob 加入缓存
7. 处理多线程竞争（使用已存在的 blob）
```

### LRU 淘汰策略

**访问时更新：**
```cpp
if (blobPtr != fBlobList.head()) {
    fBlobList.remove(blobPtr);
    fBlobList.addToHead(blobPtr);  // 移动到链表头部
}
```

**超预算清理（internalCheckPurge）：**
```cpp
1. 首先清理所有过期 blob（通过消息总线通知）
2. 如果仍超预算，从链表尾部开始移除（最久未使用）
3. 持续移除直到低于预算
4. 特殊保护：不移除刚添加的 blob
```

### 线程安全机制

**自旋锁保护：**
所有公共方法使用 `SkAutoSpinlock` 保护临界区：
```cpp
sk_sp<TextBlob> find(const TextBlob::Key& key) {
    SkAutoSpinlock lock{fSpinLock};  // RAII 锁
    // ... 临界区代码
}
```

**注解标记：**
- `SK_EXCLUDES(fSpinLock)` - 函数不持有锁
- `SK_REQUIRES(fSpinLock)` - 函数要求已持锁
- `SK_GUARDED_BY(fSpinLock)` - 成员由锁保护

### 消息总线集成

**注册机制：**
```cpp
DECLARE_SKMESSAGEBUS_MESSAGE(PurgeBlobMessage, uint32_t, true)
```
声明全局消息总线，支持跨上下文通信。

**消息过滤：**
```cpp
bool SkShouldPostMessageToBus(const PurgeBlobMessage& msg, uint32_t msgBusUniqueID) {
    return msg.fContextID == msgBusUniqueID;
}
```
确保消息只发送给匹配的上下文。

**清理通知：**
当 `SkTextBlob` 被销毁时，通过 `post_purge_blob_message` 通知所有相关的协调器清理对应的缓存。

### 内存预算管理

**默认预算：**
```cpp
static const int kDefaultBudget = 1 << 22;  // 4 MB
```

**大小计算：**
通过 `TextBlob::size()` 累加所有缓存的 blob 大小。

**清理时机：**
- 添加新 blob 后检查（`internalAdd` → `internalCheckPurge`）
- 收到清理消息时（`internalPurgeStaleBlobs`）

## 依赖关系

**核心依赖：**
- `src/text/gpu/TextBlob.h` - 被缓存的对象
- `src/text/gpu/SubRunContainer.h` - SubRun 容器
- `src/core/SkMessageBus.h` - 跨线程通信
- `src/base/SkSpinlock.h` - 并发控制
- `src/base/SkTInternalLList.h` - LRU 链表
- `src/core/SkTHash.h` - 哈希表实现

**使用场景：**
- GPU 文本渲染管道
- `GrRecordingContext` 持有此协调器
- Canvas 文本绘制操作

## 设计模式与设计决策

### 缓存层次设计
三层缓存逐步细化匹配条件，平衡查找速度和重用灵活性。

### LRU 淘汰策略
使用双向链表维护访问顺序，实现高效的 O(1) 移动和移除操作。

### 线性搜索权衡
`BlobIDCacheEntry` 使用 `STArray<1>` 和线性搜索，因为绝大多数情况只有一个 blob。注释明确表明如果使用模式改变，会重新评估数据结构。

### 消息总线解耦
通过消息总线实现跨上下文的生命周期管理，避免直接依赖和循环引用。

### 延迟清理
不立即响应每个清理消息，而是在下次操作时批量处理（`internalPurgeStaleBlobs`），减少锁竞争。

### 线程安全设计
使用自旋锁而非互斥锁，适合短临界区和低竞争场景，减少上下文切换开销。

## 性能考量

### 时间复杂度
- **查找**：O(1) 哈希查找 + O(k) 线性搜索（k 通常为 1）
- **添加**：O(1) 哈希插入 + O(1) 链表头插
- **淘汰**：O(n) 最坏情况（需要移除多个 blob）
- **LRU 更新**：O(1) 链表操作

### 空间复杂度
- O(n) 存储 n 个 `TextBlob` 对象
- 每个 `BlobIDCacheEntry` 额外存储一个小数组（通常 1 个元素）

### 缓存命中率优化
1. **精确匹配**：通过 `TextBlob::Key` 精确匹配绘制参数
2. **重用检查**：`canReuse` 允许在参数轻微变化时仍重用
3. **矩阵预计算**：提前计算位置矩阵，避免重复计算

### 并发性能
1. **细粒度锁**：仅在访问共享数据时持锁
2. **快速路径**：查找操作尽可能快速完成
3. **无锁读取**：`usedBytes` 和 `isOverBudget` 使用只读锁

### 内存效率
1. **智能预算**：默认 4MB 预算适合大多数场景
2. **及时清理**：超预算立即触发清理
3. **消息批处理**：批量处理清理消息减少开销

### 适用场景
- UI 文本渲染（重复绘制相同文本）
- 滚动场景（文本内容稳定）
- 动画场景（需要快速重绘）

## 相关文件

**核心依赖：**
- `src/text/gpu/TextBlob.h` - TextBlob 实现
- `src/text/gpu/SubRunContainer.h` - SubRun 管理
- `src/core/SkMessageBus.h` - 消息系统
- `src/base/SkSpinlock.h` - 同步原语

**使用此协调器的模块：**
- `src/gpu/ganesh/GrRecordingContext.cpp` - 持有协调器实例
- `src/gpu/ganesh/text/GrSDFTControl.cpp` - SDF 文本控制
- GPU 文本渲染管道的各个组件

**测试和调试：**
- `::GrTextBlobTestingPeer` - 友元测试类
- 各种文本渲染测试
