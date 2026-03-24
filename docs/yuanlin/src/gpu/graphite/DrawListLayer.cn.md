# DrawListLayer

> 源文件
> - src/gpu/graphite/DrawListLayer.h
> - src/gpu/graphite/DrawListLayer.cpp

## 概述

`DrawListLayer` 是 `DrawListBase` 的高级实现，采用分层（layering）策略来优化绘制命令的组织和排序。与 `DrawList` 的简单排序不同，`DrawListLayer` 将绘制命令组织成多个层（Layer），每层包含多个绑定组（BindingWrapper），实现更智能的命令合并和批处理。

该类的核心设计思想是通过边界测试（bounds testing）和兼容性检查，将具有相同或兼容管线状态的绘制命令聚集到同一层中，从而减少 GPU 状态切换。它还针对深度仅绘制（depth-only draws）和被裁剪绘制（clipped draws）实现了特殊的优化路径。

## 架构位置

在 Graphite 渲染架构中的位置：

1. **Device/Canvas** → 发起绘制请求
2. **DrawContext** → 选择使用 `DrawListLayer` 或 `DrawList`（由 `Caps::useDrawListLayer()` 决定）
3. **DrawListLayer** → 组织绘制命令到分层结构
4. **Layer** → 包含具有相似画家顺序的绘制命令
5. **BindingWrapper** → 管理具有相同绑定的绘制列表
6. **DrawPass** → 最终生成的不可变命令流

与 `DrawList` 的对比：
- **DrawList**：简单的排序键方法，适合轻量场景
- **DrawListLayer**：复杂的分层方法，适合重度场景，提供更好的批处理

## 主要类与结构体

### DrawListLayer 类

```cpp
class DrawListLayer final : public DrawListBase {
public:
    DrawListLayer() : DrawListBase() {}

    // 记录绘制命令
    std::pair<DrawParams*, Insertion> recordDraw(
            const Renderer* renderer,
            const Transform& localToDevice,
            const Geometry& geometry,
            const Clip& clip,
            DrawOrder ordering,
            UniquePaintParamsID paintID,
            SkEnumBitMask<DstUsage> dstUsage,
            BarrierType barrierBeforeDraws,
            PipelineDataGatherer* gatherer,
            const StrokeStyle* stroke,
            const Insertion& latestInsertion) override;

    // 创建 DrawPass
    std::unique_ptr<DrawPass> snapDrawPass(
            Recorder* recorder,
            sk_sp<TextureProxy> target,
            const SkImageInfo& targetInfo,
            const DstReadStrategy dstReadStrategy) override;

    // 重置状态
    void reset(LoadOp op, SkColor4f clearColor = {0.f, 0.f, 0.f, 0.f}) override;

private:
    // 向后搜索并记录绘制
    template<bool kIsDepthOnly>
    void recordBackwards(int stepIndex,
                        bool isStencil,
                        bool dependsOnDst,
                        bool requiresBarrier,
                        const RenderStep* step,
                        const UniformDataCache::Index& uniformIndex,
                        const LayerKey& key,
                        const DrawParams* drawParams,
                        const Insertion& stop,
                        Insertion* capture);

    // 向前搜索并记录绘制
    void recordForwards(int stepIndex,
                       bool isStencil,
                       bool dependsOnDst,
                       bool requiresBarrier,
                       const RenderStep* step,
                       const UniformDataCache::Index& uniformIndex,
                       const LayerKey& key,
                       const DrawParams* drawParams,
                       const Insertion& start);

    // 成员变量
    static constexpr uint32_t kMaxSearchLimit = 32;
    static constexpr uint32_t kDefaultAllocation = 4096;

    SkArenaAllocWithReset fStorage{kDefaultAllocation};  // 内存分配器
    SkTInternalLList<Layer> fLayers;                     // 层链表

    int fDrawCount = 0;
    CompressedPaintersOrder fOrderCounter = CompressedPaintersOrder::First();

    // 模板绘制快速路径
    Layer* fStencilLayer = nullptr;
    BindingWrapper* fStencilWrapper = nullptr;
    StencilDraws* fStencilList = nullptr;
};
```

### 关键数据结构（定义在 DrawListTypes.h）

#### Layer

```cpp
class Layer {
public:
    Layer(CompressedPaintersOrder order);

    // 搜索兼容的绑定
    BindingWrapper* searchBinding(const LayerKey& key, BindingWrapper* boundary);

    // 边界测试
    template <bool kIsStencil, bool kIsDepthOnly, bool kForwards>
    std::pair<BoundsTest, BindingWrapper*> test(
            const Rect& bounds,
            const LayerKey& key,
            bool requiresBarrier,
            BindingWrapper* boundary);

    // 添加绘制
    template <bool kIsDepthOnly>
    BindingWrapper* add(SkArenaAllocWithReset* storage,
                       BindingWrapper* match,
                       const LayerKey& key,
                       SingleDraw* draw,
                       const RenderStep* step,
                       bool canAppendToMRU);

    // 添加模板绘制
    template <bool kIsDepthOnly>
    BindingWrapper* addStencil(SkArenaAllocWithReset* storage,
                              BindingWrapper* match,
                              const LayerKey& key,
                              SingleDraw* draw,
                              const RenderStep* step,
                              StencilDraws** stencilList);

    CompressedPaintersOrder fOrder;
    SkTInternalLList<BindingWrapper> fBindings;
    Rect fBounds;  // 该层所有绘制的联合边界
};
```

#### LayerKey

```cpp
struct LayerKey {
    GraphicsPipelineCache::Index fPipelineIndex;
    TextureDataCache::Index fTextureIndex;

    bool operator==(const LayerKey& other) const;
};
```

#### BindingWrapper

基类，派生出 `SingleDrawList` 和 `StencilDrawList`：

```cpp
class BindingWrapper {
public:
    BindingListType fType;
    LayerKey fKey;
    Rect fBounds;
    bool fRequiresBarrier;
};
```

#### SingleDrawList

```cpp
class SingleDrawList : public BindingWrapper {
public:
    const RenderStep* fStep;
    SkTInternalLList<SingleDraw> fDraws;
};
```

#### StencilDrawList

```cpp
class StencilDrawList : public BindingWrapper {
public:
    SkTInternalLList<StencilDraws> fStencilDraws;
};
```

#### SingleDraw

```cpp
class SingleDraw {
public:
    const DrawParams* fDrawParams;
    UniformDataCache::Index fUniformIndex;
};
```

#### Insertion

跟踪最近插入的位置：

```cpp
struct Insertion {
    const Layer* fLayer;
    const BindingWrapper* fWrapper;

    bool operator>(const Insertion& other) const;
};
```

## 公共 API 函数

### recordDraw

```cpp
std::pair<DrawParams*, Insertion> recordDraw(
        const Renderer* renderer,
        const Transform& localToDevice,
        const Geometry& geometry,
        const Clip& clip,
        DrawOrder ordering,
        UniquePaintParamsID paintID,
        SkEnumBitMask<DstUsage> dstUsage,
        BarrierType barrierBeforeDraws,
        PipelineDataGatherer* gatherer,
        const StrokeStyle* stroke,
        const Insertion& latestInsertion) override;
```

记录绘制命令的主入口。执行流程：

1. **创建 DrawParams**：在 arena 中分配共享的绘制参数
2. **遍历渲染步骤**：为渲染器的每个步骤：
   - 收集 uniform 数据和纹理绑定
   - 插入管线描述到缓存
   - 创建 `LayerKey`
3. **选择记录策略**：
   - **深度仅绘制**（`paintID == Invalid`）：调用 `recordBackwards<true>`
   - **被裁剪绘制**（`latestInsertion.fLayer` 有效且不依赖 DST）：调用 `recordForwards`
   - **其他**：调用 `recordBackwards<false>`
4. **更新统计信息**：边界、MSAA 需求、深度模板标志等

**返回值**：
- `DrawParams*`：指向共享参数的指针
- `Insertion`：记录深度仅绘制的插入位置（供后续被裁剪绘制使用）

### snapDrawPass

```cpp
std::unique_ptr<DrawPass> snapDrawPass(
        Recorder* recorder,
        sk_sp<TextureProxy> target,
        const SkImageInfo& targetInfo,
        const DstReadStrategy dstReadStrategy) override;
```

将分层结构转换为线性的 `DrawPass` 命令流。执行流程：

1. **创建 DrawPass**：初始化命令列表和 DrawWriter
2. **遍历层**：按画家顺序（从前到后）
3. **遍历绑定**：每层中的每个绑定
4. **处理绘制列表**：
   - `SingleDrawList`：遍历绘制，调用 `recordDraw` lambda
   - `StencilDrawList`：遍历模板绘制组，每组调用 `recordDraw`
5. **优化绑定不变性**：第一个绘制设置绑定，后续绘制如果绑定不变则跳过
6. **刷新和重置**：完成后重置 `DrawListLayer`

### reset

```cpp
void reset(LoadOp loadOp, SkColor4f color) override;
```

重置所有状态：
- 调用基类 `reset`
- 重置 arena 分配器
- 清空层链表
- 重置计数器和模板快速路径

## 内部实现细节

### 分层策略

每个 `Layer` 对应一个 `CompressedPaintersOrder`，表示该层中所有绘制的画家顺序。关键规则：

1. **相同顺序的绘制在同一层**：如果边界和绑定兼容
2. **不兼容的绘制创建新层**：保证正确的视觉顺序
3. **层按顺序遍历**：快照时保证从前到后的顺序

### 向后搜索（recordBackwards）

用于大多数绘制，从最近的层向旧层搜索：

```cpp
template <bool kIsDepthOnly>
void recordBackwards(/* ... */) {
    // 1. 模板快速路径
    if (isStencil && stepIndex > 0) {
        // 子模板步骤直接添加到父层
        fStencilLayer->addStencil(...);
        return;
    }

    // 2. 简单绘制的优化路径
    if (!isStencil && !dependsOnDst) {
        // 尝试直接添加到 stop.fLayer（深度仅绘制插入的层）
        targetLayer = stop.fLayer ? stop.fLayer : fLayers.head();
        if (targetLayer) {
            targetMatch = targetLayer->searchBinding(key, stop.fWrapper);
        }
    }

    // 3. 完整向后搜索
    else {
        current = fLayers.tail();
        for (uint32_t limit = 0; limit < kMaxSearchLimit && current != stop.fLayer; ++limit) {
            auto result = current->test<...>(bounds, key, requiresBarrier, nullptr);
            if (result.first == kIncompatibleOverlap) {
                if (dependsOnDst) break;  // 不能跨越
                else continue;            // 继续搜索
            } else {
                targetLayer = current;
                targetMatch = result.second;
                if (result.first == kCompatibleOverlap) break;
            }
            current = current->fPrev;
        }
    }

    // 4. 创建新层（如果需要）
    if (!targetLayer) {
        fOrderCounter = fOrderCounter.next();
        targetLayer = fStorage.make<Layer>(fOrderCounter);
        fLayers.addToTail(targetLayer);
    }

    // 5. 添加绘制到目标层
    insertedWrapper = targetLayer->add(...);

    // 6. 捕获插入位置（深度仅绘制）
    if constexpr (kIsDepthOnly) {
        *capture = {targetLayer, insertedWrapper};
    }
}
```

**搜索限制**：`kMaxSearchLimit = 32`，防止过度向后搜索导致性能下降。

### 向前搜索（recordForwards）

用于被深度仅绘制裁剪的绘制，从特定起点向新层搜索：

```cpp
void recordForwards(/* ... */) {
    // 1. 模板快速路径（同 recordBackwards）

    // 2. 从 start.fLayer 开始向前搜索
    current = start.fLayer;
    if (current) {
        if (!processLayer(start.fWrapper)) {
            current = current->fNext;
            for (uint32_t limit = 0; limit < kMaxSearchLimit && current; ++limit) {
                if (processLayer(nullptr)) break;
                current = current->fNext;
            }
        }
    }

    // 3. 创建新层（如果需要）
    if (!targetLayer) {
        fOrderCounter = fOrderCounter.next();
        targetLayer = fStorage.make<Layer>(fOrderCounter);
        if (start.fLayer) {
            fLayers.addAfter(targetLayer, start.fLayer);
        } else {
            fLayers.addToTail(targetLayer);
        }
    }

    // 4. 添加绘制
    targetLayer->add(...);
}
```

**关键差异**：
- 从 `start.fLayer` 开始，而非 `fLayers.tail()`
- 向前（`fNext`）而非向后（`fPrev`）
- 新层插入在 `start.fLayer` 之后，而非尾部

### 边界测试（Bounds Testing）

`Layer::test` 方法执行三种结果的边界测试：

```cpp
enum class BoundsTest {
    kCompatibleOverlap,    // 边界重叠，绑定兼容
    kDisjoint,             // 边界不重叠
    kIncompatibleOverlap   // 边界重叠，但绑定不兼容
};
```

逻辑：

1. **检查边界**：
   - 不相交 → `kDisjoint`（可以添加到该层）
   - 相交 → 继续检查兼容性

2. **检查屏障**：
   - 如果需要屏障且层有重叠绘制 → `kIncompatibleOverlap`

3. **搜索兼容绑定**：
   - 调用 `searchBinding` 查找相同的 `LayerKey`
   - 找到 → `kCompatibleOverlap`
   - 未找到 → `kIncompatibleOverlap`

### 模板绘制快速路径

对于多步骤模板渲染器（如复杂路径）：

```cpp
if (isStencil && stepIndex > 0) {
    // 第二个及以后的步骤直接添加到第一个步骤创建的层和绑定
    fStencilLayer->addStencil(fStencilWrapper, ...);
    return;
}
```

避免重复搜索，因为所有步骤必须在同一层。

### 深度仅绘制与被裁剪绘制的协作

**深度仅绘制**（如阴影体积、遮挡剔除）：
- 使用 `recordBackwards<true>`
- 返回插入位置到 `capture`
- 不依赖 DST

**被裁剪绘制**（受深度仅绘制影响）：
- 接收 `latestInsertion`（所有影响它的深度仅绘制的最新插入位置）
- 如果不依赖 DST，使用 `recordForwards` 从 `latestInsertion` 开始向前搜索
- 如果依赖 DST，使用 `recordBackwards<false>`，因为必须停在任何着色重叠绘制前

### Arena 分配器

使用 `SkArenaAllocWithReset`：

```cpp
SkArenaAllocWithReset fStorage{kDefaultAllocation};

// 分配对象
DrawParams* drawParams = fStorage.make<DrawParams>(...);
Layer* layer = fStorage.make<Layer>(...);
SingleDraw* draw = fStorage.make<SingleDraw>(...);

// 重置（保留第一个块）
fStorage.reset();
```

**优势**：
- 快速分配（无锁，无碎片）
- 批量释放（reset 时一次性释放）
- 缓存友好（对象连续分配）

### 绑定不变性优化

在 `snapDrawPass` 中，lambda `recordDraw` 接受 `bindingsAreInvariant` 参数：

```cpp
const SingleDraw* current = singleList->fDraws.head();
recordDraw(..., /*bindingsAreInvariant=*/false);  // 第一个绘制

current = current->fNext;
while (current) {
    recordDraw(..., /*bindingsAreInvariant=*/true);  // 后续绘制
    current = current->fNext;
}
```

当 `bindingsAreInvariant=true` 时，跳过管线和纹理绑定检查，因为已知它们与前一个绘制相同。

### 预取优化

在搜索循环中使用编译器内建函数预取下一个层：

```cpp
#if defined(__GNUC__) || defined(__clang__)
    __builtin_prefetch(current->fPrev);  // 或 current->fNext
#endif
```

提高缓存命中率，减少内存访问延迟。

## 依赖关系

**直接依赖**：
- `DrawListBase.h`：基类
- `DrawListTypes.h`：Layer、BindingWrapper、SingleDraw 等类型
- `DrawCommands.h`：命令接口
- `DrawOrder.h`：画家顺序
- `DrawParams.h`：绘制参数
- `DrawPass.h`：输出
- `Renderer.h` / `RenderStep`：渲染步骤

**间接依赖**：
- `src/base/SkArenaAllocWithReset.h`：Arena 分配器
- `src/base/SkTInternalLList.h`：内部链表
- `Geometry.h`：几何形状
- `Transform.h`：变换矩阵
- `PipelineData.h`：管线数据收集

## 设计模式与设计决策

### 1. 空间分区（Spatial Partitioning）

通过边界测试将绘制命令分组到层中：
- 不重叠的绘制可以在同一层
- 重叠但绑定兼容的绘制可以在同一层
- 重叠且不兼容的绘制必须在不同层

类似 BSP 树或 R 树，但更简单。

### 2. 延迟决策（Deferred Decision）

不立即确定绘制的最终位置：
- 向后搜索有限步数
- 未找到合适层时才创建新层
- 平衡搜索成本和层数量

### 3. 快速路径优化（Fast Path Optimization）

为常见情况提供优化路径：
- 模板子步骤快速路径
- 简单绘制的头部尝试路径
- 绑定不变性优化

### 4. 双向搜索策略

- **向后搜索**：默认策略，找到最旧的兼容层
- **向前搜索**：被裁剪绘制的特殊路径，确保在深度仅绘制之后

### 5. 对象池（Arena 分配器）

所有临时对象从 arena 分配：
- 无需逐个 delete
- 重置时批量释放
- 减少分配器开销

### 6. 观察者模式（Insertion 跟踪）

深度仅绘制作为"观察者"通知后续被裁剪绘制：
- 深度仅绘制更新 `capture`
- 被裁剪绘制读取 `latestInsertion`
- 解耦两类绘制的处理逻辑

## 性能考量

### 搜索限制

`kMaxSearchLimit = 32` 平衡：
- **过小**：创建过多层，失去批处理机会
- **过大**：搜索时间过长，抵消批处理收益

实际测试表明 32 是良好的默认值。

### Arena 分配器大小

`kDefaultAllocation = 4096` 字节：
- 足够容纳典型场景的初始对象
- 避免过多小块分配
- 后续块以倍数增长

### 预取效果

预取下一个层的指针：
- 隐藏内存延迟（~100 周期）
- 在搜索密集循环中效果显著
- GCC/Clang 优化

### 绑定不变性

跳过重复的绑定检查：
- 减少条件分支
- 减少缓存查找
- 对于长绘制列表，节省显著

### 层数量

理想情况：层数量 = 不同画家顺序数量。
实际情况：由于搜索限制和边界冲突，可能更多。

典型场景：
- 简单 UI：5-20 层
- 复杂场景：50-100 层
- 病态场景：可能数百层（罕见）

### 深度仅绘制开销

深度仅绘制需要：
1. 向后搜索（可能完整遍历）
2. 捕获插入位置
3. 后续被裁剪绘制向前搜索

权衡：额外开销 vs 更好的批处理。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/graphite/DrawListBase.h` | 基类定义 |
| `src/gpu/graphite/DrawListTypes.h` | Layer、BindingWrapper 等类型 |
| `src/gpu/graphite/DrawList.h/cpp` | 简单排序键实现 |
| `src/gpu/graphite/DrawPass.h/cpp` | 最终输出 |
| `src/gpu/graphite/DrawWriter.h/cpp` | 顶点数据写入 |
| `src/gpu/graphite/DrawCommands.h` | 命令接口 |
| `src/gpu/graphite/DrawOrder.h` | 画家顺序 |
| `src/gpu/graphite/DrawParams.h` | 绘制参数 |
| `src/gpu/graphite/Renderer.h/cpp` | 渲染器和渲染步骤 |
| `src/gpu/graphite/PipelineData.h` | 管线数据收集 |
| `src/base/SkArenaAllocWithReset.h` | Arena 分配器 |
| `src/base/SkTInternalLList.h` | 内部链表 |
| `src/gpu/graphite/geom/Geometry.h` | 几何形状 |
| `src/gpu/graphite/geom/Transform.h` | 变换矩阵 |
| `src/gpu/graphite/geom/Rect.h` | 矩形边界 |
