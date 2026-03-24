# DrawList

> 源文件
> - src/gpu/graphite/DrawList.h
> - src/gpu/graphite/DrawList.cpp

## 概述

`DrawList` 是 Skia Graphite GPU 后端中用于收集和管理绘制命令的核心数据结构。它以接近 GPU 硬件执行效率的形式表示一组绘制命令及其相关的裁剪和着色状态。该类负责在绘制准备阶段对命令进行排序、优化和合并，以最小化 GPU 管线状态转换并提高渲染效率。

`DrawList` 继承自 `DrawListBase`，提供了命令记录、排序键生成、绘制通道创建等功能。它使用智能的排序机制来平衡绘制顺序约束和 GPU 性能优化需求。

## 架构位置

在 Graphite 架构中，`DrawList` 位于以下层次：

1. **上层接口**：接收来自 `Device` 层或更高层的绘制请求
2. **命令收集**：将绘制操作转换为内部 `Draw` 结构
3. **优化层**：对收集的绘制命令进行排序和优化
4. **生成输出**：创建 `DrawPass` 对象供命令缓冲区执行

它与以下组件紧密协作：
- `Renderer` 和 `RenderStep`：定义如何执行具体的绘制步骤
- `DrawPass`：最终的不可变命令序列
- `DrawWriter`：负责写入顶点和索引数据
- 各种缓存系统：`GraphicsPipelineCache`、`UniformDataCache`、`TextureDataCache`

## 主要类与结构体

### DrawList 类

主要的公共接口：

```cpp
class DrawList : public DrawListBase {
public:
    DrawList() {}

    // 记录一次绘制命令
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

    // 创建 DrawPass 快照
    std::unique_ptr<DrawPass> snapDrawPass(
            Recorder* recorder,
            sk_sp<TextureProxy> target,
            const SkImageInfo& targetInfo,
            DstReadStrategy dstReadStrategy) override;

    // 重置绘制列表
    void reset(LoadOp op, SkColor4f clearColor = {0.f, 0.f, 0.f, 0.f}) override;
};
```

### Draw 结构体

内部表示单个绘制命令：

```cpp
struct Draw {
    Draw(const Renderer* renderer, const Transform& transform,
         const Geometry& geometry, const Clip& clip, DrawOrder order,
         BarrierType barrierBeforeDraws, const StrokeStyle* stroke);

    const Renderer* renderer() const;
    const DrawParams& drawParams() const;

private:
    const Renderer* fRenderer;
    DrawParams fDrawParams;
};
```

### SortKey 类

用于对绘制命令排序的关键数据结构，包含 128 位的排序键：

```cpp
class SortKey {
public:
    SortKey(const Draw* draw, int renderStep,
            GraphicsPipelineCache::Index pipelineIndex,
            UniformDataCache::Index uniformIndex,
            TextureDataCache::Index textureBindingIndex);

    bool operator<(const SortKey& k) const;
    const RenderStep& renderStep() const;
    const Draw& draw() const;

    GraphicsPipelineCache::Index pipelineIndex() const;
    UniformDataCache::Index uniformIndex() const;
    TextureDataCache::Index textureBindingIndex() const;

private:
    uint64_t fPipelineKey;   // 包含颜色/深度顺序、模板索引、渲染步骤、管线索引
    uint64_t fUniformKey;    // 包含 uniform 和纹理绑定索引
    const Draw* fDraw;       // 指向源绘制命令的指针
};
```

### Bitfield 模板

用于在排序键中高效打包位字段：

```cpp
template <uint64_t Bits, uint64_t Offset>
struct Bitfield {
    static constexpr uint64_t kMask = ((uint64_t) 1 << Bits) - 1;
    static constexpr uint64_t kOffset = Offset;

    static uint32_t get(uint64_t v);
    static uint64_t set(uint32_t v);
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

记录一个新的绘制命令。该函数：
1. 验证变换的有效性和几何形状的非空性
2. 创建 `Draw` 对象并添加到 `fDraws` 列表
3. 为渲染器的每个渲染步骤生成 `SortKey`
4. 收集 uniform 数据和纹理绑定
5. 更新绘制边界和各种标志位

### snapDrawPass

```cpp
std::unique_ptr<DrawPass> snapDrawPass(
        Recorder* recorder,
        sk_sp<TextureProxy> target,
        const SkImageInfo& targetInfo,
        DstReadStrategy dstReadStrategy) override;
```

将收集的绘制命令转换为 `DrawPass` 对象。该函数执行以下操作：
1. 对所有 `SortKey` 进行排序
2. 创建新的 `DrawPass` 对象
3. 遍历排序后的键，生成实际的 GPU 命令
4. 处理管线状态变化、uniform 绑定、纹理绑定和裁剪矩形
5. 优化批处理以减少状态改变
6. 重置当前 `DrawList` 以供重用

### reset

```cpp
void reset(LoadOp op, SkColor4f clearColor = {0.f, 0.f, 0.f, 0.f}) override;
```

清除所有先前记录的绘制命令，并设置新的加载操作和清除颜色。

## 内部实现细节

### 排序键设计

`SortKey` 采用精心设计的 128 位结构来优化排序性能：

**第一个 64 位（fPipelineKey）**：
- `ColorDepthOrderField` (16 位)：压缩的画家顺序，确保正确的深度排序
- `StencilIndexField` (16 位)：不相交模板索引
- `RenderStepField` (2 位)：渲染步骤索引（单个绘制可能有多个步骤）
- `PipelineField` (30 位)：管线描述缓存索引

**第二个 64 位（fUniformKey）**：
- `UniformField` (34 位)：uniform 数据缓存索引
- `TextureBindingsField` (30 位)：纹理绑定缓存索引

这种设计确保了：
1. 最重要的排序标准（画家顺序）在最高位
2. 相同管线的绘制被聚集在一起
3. 具有相同 uniform 和纹理的绘制可以批处理

### 绘制通道生成流程

`snapDrawPass` 的核心逻辑：

1. **排序阶段**：使用 `std::sort` 对所有 `SortKey` 排序
2. **命令生成**：遍历排序后的键
   - 检测管线变化：不同管线需要绑定命令
   - 检测状态变化：uniform 绑定、纹理绑定、裁剪矩形变化
   - 使用 `DrawWriter` 累积顶点数据
3. **优化**：
   - 相邻相同状态的绘制自动批处理
   - 通过 `newPipelineState` 和 `newDynamicState` 控制刷新
   - 处理需要屏障的绘制命令

### 缓存系统集成

`DrawList` 利用三个缓存系统来减少重复数据：

- **GraphicsPipelineCache**：存储管线描述符，通过索引引用
- **UniformDataCache**：缓存 uniform 数据块
- **TextureDataCache**：缓存纹理绑定配置

这些缓存在 `recordDraw` 时填充，在 `snapDrawPass` 时使用。

### 内存管理

使用 `SkTBlockList<Draw, 4>` 存储绘制命令，采用斐波那契增长策略：
- 减少内存重新分配
- 保持指针稳定性（`SortKey` 持有 `Draw*`）
- 提供良好的缓存局部性

## 依赖关系

**直接依赖**：
- `DrawListBase.h`：基类定义
- `DrawCommands.h`：绘制命令类型
- `DrawOrder.h`：绘制顺序管理
- `DrawParams.h`：绘制参数封装
- `Renderer.h` / `RenderStep`：定义渲染步骤
- `DrawPass.h`：输出的绘制通道
- `DrawWriter.h`：顶点数据写入

**间接依赖**：
- `Geometry.h`：几何形状定义
- `Transform.h`：变换矩阵
- `PaintParams.h`：绘制样式参数
- `PipelineData.h`：管线数据收集
- `Recorder.h`：录制器上下文

## 设计模式与设计决策

### 1. 命令缓冲模式（Command Buffer Pattern）

`DrawList` 实现了经典的命令缓冲模式：
- 收集阶段：记录所有绘制操作而不立即执行
- 优化阶段：对命令进行重排序和合并
- 执行阶段：生成最终的 GPU 命令流

### 2. 延迟优化（Deferred Optimization）

绘制命令以任意顺序添加，优化推迟到 `snapDrawPass` 时进行。这允许：
- 全局视角下的更好优化
- 考虑所有绘制后再决定批处理策略
- 可能的遮挡剔除（虽然当前未完全实现）

### 3. 索引化缓存（Indexed Cache）

使用索引而非直接指针引用缓存数据：
- 减少 `SortKey` 大小（24 字节 vs 可能的更大尺寸）
- 允许更高效的排序（比较整数而非指针）
- 缓存数据可以独立管理和复用

### 4. 位字段打包（Bitfield Packing）

手动控制位字段布局而非使用 C++ 位字段：
- 确保跨平台一致的排序行为
- 精确控制每个字段的位数
- 优化内存布局以提高排序性能

### 5. 增量状态跟踪（Incremental State Tracking）

在 `snapDrawPass` 中跟踪 `lastPipeline`、`lastScissor` 等：
- 仅在状态实际改变时发出绑定命令
- 减少冗余的 GPU 命令
- 提高命令缓冲区效率

## 性能考量

### 排序性能

- `SortKey` 大小为 24 字节（16 字节键 + 8 字节指针），已针对现代 CPU 优化
- 注释中指出，24 字节比理想的 16 字节慢约 30%
- 使用 `std::sort` 而非稳定排序，在测试中表现更好
- 对于大部分已排序的数据，性能接近 O(n)

### 内存效率

- `SkTBlockList` 使用斐波那契增长策略，平衡内存开销和重新分配成本
- 缓存系统通过共享数据减少重复
- `SortKey` 向量在每次 `reset` 时清除但保留容量

### 批处理优化

- 排序键设计确保相同管线和状态的绘制相邻
- `DrawWriter` 自动批处理相邻的兼容绘制
- 减少绘制调用数量和状态变化

### 验证开销

在 DEBUG 模式下：
- 验证变换有效性
- 检查几何形状和裁剪边界
- 跟踪覆盖蒙版形状绘制计数
- 验证模板索引分配

发布版本中这些检查被移除以提高性能。

### 屏障处理

特殊处理需要屏障的绘制：
- 检测绘制顺序变化
- 在必要时插入刷新命令
- 确保屏障命令和绘制命令正确排序

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/graphite/DrawListBase.h` | 基类定义，提供共享功能 |
| `src/gpu/graphite/DrawPass.h/cpp` | 不可变的绘制通道输出 |
| `src/gpu/graphite/DrawWriter.h/cpp` | 顶点和索引数据写入器 |
| `src/gpu/graphite/DrawCommands.h` | 绘制命令接口定义 |
| `src/gpu/graphite/DrawOrder.h` | 绘制顺序和深度管理 |
| `src/gpu/graphite/DrawParams.h` | 绘制参数封装 |
| `src/gpu/graphite/DrawListTypes.h` | 绘制列表相关类型定义 |
| `src/gpu/graphite/Renderer.h/cpp` | 渲染器和渲染步骤定义 |
| `src/gpu/graphite/PipelineData.h` | 管线数据收集器 |
| `src/gpu/graphite/KeyContext.h` | 键上下文信息 |
| `src/gpu/graphite/RecorderPriv.h` | 录制器私有接口 |
| `src/gpu/graphite/geom/Geometry.h` | 几何形状定义 |
| `src/gpu/graphite/geom/Transform.h` | 变换矩阵 |
| `src/base/SkTBlockList.h` | 块分配列表容器 |
