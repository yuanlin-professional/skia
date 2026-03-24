# DrawContext

> 源文件
> - src/gpu/graphite/DrawContext.h
> - src/gpu/graphite/DrawContext.cpp

## 概述

`DrawContext` 是 Skia Graphite 渲染管线中的核心类，负责将绘制命令记录到特定的渲染目标表面。它通过构建表示 GPU 工作及其相互依赖关系的任务图来管理渲染操作。`DrawContext` 充当高层绘制 API 和底层 GPU 任务执行之间的桥梁，协调绘制命令、上传操作、计算调度和任务依赖关系。

该类持有一个渲染目标纹理代理（`TextureProxy`），管理待处理的绘制和上传操作，并在适当的时机将这些操作刷新到任务图中。它还支持计算路径图集（Compute Path Atlas）来优化路径渲染性能。

## 架构位置

`DrawContext` 在 Graphite 渲染架构中的位置：

1. **设备层（Device Layer）** → 通过 `DrawContext` 记录绘制操作
2. **DrawContext** → 收集绘制命令到 `DrawList` / `DrawListLayer`
3. **任务构建** → 生成 `DrawTask`，包含 `UploadTask`、`ComputeTask`、`RenderPassTask`
4. **录制器（Recorder）** → 收集并提交任务图
5. **命令缓冲区** → 实际的 GPU 命令执行

相关组件：
- `DrawList` / `DrawListLayer`：实际存储绘制命令
- `DrawPass`：从 `DrawList` 创建的不可变渲染通道
- `DrawTask`：管理任务图中的各种任务
- `UploadList`：管理纹理上传操作
- `ComputePathAtlas`：计算着色器生成的路径图集

## 主要类与结构体

### DrawContext 类

```cpp
class DrawContext final : public SkRefCnt {
public:
    // 工厂方法
    static sk_sp<DrawContext> Make(const Caps* caps,
                                   sk_sp<TextureProxy> target,
                                   SkISize deviceSize,
                                   const SkColorInfo&,
                                   const SkSurfaceProps&);

    // 访问器
    const SkImageInfo& imageInfo() const;
    const SkColorInfo& colorInfo() const;
    TextureProxy* target();
    const TextureProxyView& readSurfaceView() const;
    const SkSurfaceProps& surfaceProps() const;

    int pendingRenderSteps() const;
    bool modifiesTarget() const;
    bool readsTexture(const TextureProxy*) const;

    // 清除和丢弃
    void clear(const SkColor4f& clearColor);
    void discard();

    // 记录绘制
    std::pair<DrawParams*, Insertion> recordDraw(...);

    // 记录上传
    bool recordUpload(...);

    // 添加任务依赖
    void recordDependency(sk_sp<Task>);

    // 获取计算路径图集
    PathAtlas* getComputePathAtlas(Recorder*);

    // 刷新待处理操作
    void flush(Recorder*);

    // 快照当前任务
    sk_sp<Task> snapDrawTask();

    // 目标读取策略
    DstReadStrategy dstReadStrategy() const;

private:
    DrawContext(const Caps*, sk_sp<TextureProxy>, const SkImageInfo&, const SkSurfaceProps&);
    void resetForClearOrDiscard();

    // 成员变量
    sk_sp<TextureProxy> fTarget;
    TextureProxyView fReadView;
    SkImageInfo fImageInfo;
    const SkSurfaceProps fSurfaceProps;

    const DstReadStrategy fDstReadStrategy;
    const bool fSupportsHardwareAdvancedBlend;
    const bool fAdvancedBlendsRequireBarrier;

    sk_sp<DrawTask> fCurrentDrawTask;
    std::unique_ptr<DrawListBase> fPendingDraws;
    std::unique_ptr<UploadList> fPendingUploads;
    std::unique_ptr<ComputePathAtlas> fComputePathAtlas;
};
```

### 关键数据成员

**fTarget**：渲染目标纹理代理，所有绘制操作最终渲染到此纹理。

**fReadView**：用于从目标纹理读取的视图（如果支持），用于需要读取目标缓冲区的绘制操作（如某些混合模式）。

**fPendingDraws**：待处理的绘制命令列表，可能是 `DrawList` 或 `DrawListLayer`（取决于 `Caps::useDrawListLayer()`）。

**fPendingUploads**：待处理的纹理上传操作列表。

**fCurrentDrawTask**：当前正在构建的 `DrawTask`，包含所有待刷新的任务。

**fComputePathAtlas**：计算着色器生成的路径图集，用于优化路径覆盖蒙版的生成。

## 公共 API 函数

### Make（工厂方法）

```cpp
static sk_sp<DrawContext> Make(const Caps* caps,
                               sk_sp<TextureProxy> target,
                               SkISize deviceSize,
                               const SkColorInfo& colorInfo,
                               const SkSurfaceProps& props);
```

创建 `DrawContext` 实例。执行多项验证：
- 检查目标纹理的有效性
- 验证 alpha 类型（不支持 `kUnknown` 或 `kUnpremul`）
- 确保目标纹理可渲染
- 验证颜色类型和纹理格式的兼容性
- 检查纹理尺寸至少包含设备逻辑尺寸

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
        PipelineDataGatherer* gatherer,
        const StrokeStyle* stroke,
        const Insertion& latestInsertion);
```

记录一个绘制命令。该函数：
1. 验证裁剪矩形在图像边界内
2. 根据目标读取策略和混合模式确定是否需要屏障
3. 将绘制操作转发到 `fPendingDraws`

**屏障类型决策**：
- 如果使用 `kReadFromInput` 策略且需要读取目标 → `kReadDstFromInput`
- 如果使用高级混合且硬件支持但需要屏障 → `kAdvancedNoncoherentBlend`

### recordUpload

```cpp
bool recordUpload(Recorder* recorder,
                  sk_sp<TextureProxy> targetProxy,
                  const SkColorInfo& srcColorInfo,
                  const SkColorInfo& dstColorInfo,
                  const UploadSource& source,
                  const SkIRect& dstRect,
                  std::unique_ptr<ConditionalUploadContext>);
```

记录纹理上传操作。调用者应该已经将上传区域裁剪到表面边界。

### recordDependency

```cpp
void recordDependency(sk_sp<Task> task);
```

添加一个任务，该任务将在下次 `flush()` 之前的所有待处理绘制和上传之前执行。直接添加到当前 `DrawTask`，确保执行顺序正确。

### flush

```cpp
void flush(Recorder* recorder);
```

将所有待处理的记录操作（绘制和上传）以及依赖任务移入正在构建的 `DrawTask`。执行流程：

1. **处理上传**：如果有待处理上传，创建 `UploadTask`
2. **处理计算调度**：如果有计算路径图集，记录计算调度并创建 `ComputeTask`
3. **创建渲染通道**：
   - 从 `fPendingDraws` 快照生成 `DrawPass`
   - 如果需要目标读取且策略是 `kTextureCopy`，创建目标副本
   - 创建 `RenderPassDesc` 描述符
   - 生成 `RenderPassTask` 并添加到当前任务
4. **生成 Mipmap**：如果目标纹理需要 mipmap，执行生成操作

### snapDrawTask

```cpp
sk_sp<Task> snapDrawTask();
```

返回当前 `DrawTask` 给调用者，并创建新的 `DrawTask`。所有后续记录的操作将进入新任务。如果当前任务为空，返回 `nullptr`。

### clear 和 discard

```cpp
void clear(const SkColor4f& clearColor);
void discard();
```

`clear` 设置加载操作为 `kClear` 并指定清除颜色。
`discard` 设置加载操作为 `kDiscard`，表示不关心先前的内容。

两者都调用 `resetForClearOrDiscard()`，该方法重置计算路径图集（但保留其他任务以维护图集依赖关系）。

### readsTexture

```cpp
bool readsTexture(const TextureProxy* texture) const;
```

检查待处理的绘制或当前任务是否会采样给定的纹理。用于检测依赖关系和避免读写冲突。

## 内部实现细节

### 构造过程

构造函数执行以下初始化：

1. **确定目标读取策略**：从 `Caps` 获取策略（`kNoneRequired`、`kTextureCopy` 或 `kReadFromInput`）
2. **检测混合支持**：查询硬件高级混合支持和是否需要屏障
3. **创建 DrawTask**：初始化 `fCurrentDrawTask`
4. **选择 DrawList 类型**：根据 `Caps::useDrawListLayer()` 选择使用 `DrawListLayer` 或 `DrawList`
5. **设置读取视图**：如果目标可纹理化，创建 `TextureProxyView` 用于读取

### 刷新逻辑详解

`flush()` 方法实现了复杂的任务编排逻辑：

**第一阶段 - 上传任务**：
```cpp
if (fPendingUploads->size() > 0) {
    fCurrentDrawTask->addTask(UploadTask::Make(fPendingUploads.get()));
}
```
上传任务会在渲染前执行，确保纹理数据就绪。

**第二阶段 - 计算任务**：
```cpp
if (fComputePathAtlas) {
    ComputeTask::DispatchGroupList dispatches;
    if (fComputePathAtlas->recordDispatches(recorder, &dispatches)) {
        fCurrentDrawTask->addTask(ComputeTask::Make(std::move(dispatches)));
    }
    fComputePathAtlas->reset();
}
```
计算任务生成路径覆盖蒙版到图集纹理中。

**第三阶段 - 渲染通道任务**：
1. 提取 `DrawList` 的属性（DST 读取边界、MSAA 需求、深度模板标志）
2. 快照 `DrawPass`
3. 如果需要目标副本，通过 `Image::Copy` 创建
4. 构建 `RenderPassDesc`
5. 创建 `RenderPassTask`

**第四阶段 - Mipmap 生成**：
如果目标纹理启用了 mipmap，调用 `GenerateMipmaps`。

### 目标读取策略处理

三种策略的影响：

1. **kNoneRequired**：不需要读取目标，最高效
2. **kTextureCopy**：在 `flush()` 中创建目标副本，绘制时从副本采样
3. **kReadFromInput**：使用输入附件或帧缓冲获取扩展，需要插入屏障

`recordDraw` 中根据策略设置 `BarrierType`：
```cpp
if (fDstReadStrategy == DstReadStrategy::kReadFromInput &&
    (dstUsage & DstUsage::kDstReadRequired)) {
    barrierBeforeDraws = BarrierType::kReadDstFromInput;
}
```

### 高级混合模式处理

对于硬件支持的高级混合：
```cpp
if ((dstUsage & DstUsage::kAdvancedBlend) &&
    fSupportsHardwareAdvancedBlend && fAdvancedBlendsRequireBarrier) {
    barrierBeforeDraws = BarrierType::kAdvancedNoncoherentBlend;
}
```

一致性（coherent）和非一致性（non-coherent）的区别决定是否需要屏障。

### 计算路径图集

延迟创建策略：
```cpp
PathAtlas* DrawContext::getComputePathAtlas(Recorder* recorder) {
    if (!fComputePathAtlas) {
        fComputePathAtlas = recorder->priv().atlasProvider()->createComputePathAtlas(recorder);
    }
    return fComputePathAtlas.get();
}
```

仅在需要时创建，如果平台不支持计算着色器则返回 `nullptr`。

## 依赖关系

**核心依赖**：
- `TextureProxy.h` / `TextureProxyView.h`：渲染目标管理
- `DrawListBase.h`：绘制命令列表基类
- `DrawList.h` / `DrawListLayer.h`：具体绘制列表实现
- `DrawPass.h`：从绘制列表生成的渲染通道
- `DrawTask.h`：任务图管理
- `Caps.h`：设备能力查询

**任务相关**：
- `task/UploadTask.h`：纹理上传任务
- `task/ComputeTask.h`：计算着色器调度任务
- `task/RenderPassTask.h`：渲染通道任务
- `task/Task.h`：任务基类

**工具类**：
- `PaintParams.h`：绘制参数
- `DrawOrder.h`：绘制顺序管理
- `Renderer.h`：渲染器定义
- `AtlasProvider.h`：图集管理
- `RecorderPriv.h`：录制器私有接口

## 设计模式与设计决策

### 1. 命令记录与延迟执行模式

`DrawContext` 实现了命令记录模式：
- 记录阶段：通过 `recordDraw` 和 `recordUpload` 收集操作
- 刷新阶段：通过 `flush` 将操作转换为 GPU 任务
- 快照阶段：通过 `snapDrawTask` 提取任务供录制器使用

这种分离允许批处理优化和全局视角下的任务重排序。

### 2. 策略模式（目标读取策略）

使用 `DstReadStrategy` 枚举封装不同平台的目标读取能力：
- 通过 `Caps` 查询支持的策略
- 在 `recordDraw` 和 `flush` 中根据策略调整行为
- 对调用者透明，自动选择最优实现

### 3. 工厂模式

使用静态 `Make` 方法而非公共构造函数：
- 执行复杂的验证逻辑
- 失败时可以返回 `nullptr`
- 隐藏构造细节

### 4. 资源管理（智能指针）

广泛使用智能指针：
- `sk_sp<TextureProxy>`：共享纹理代理所有权
- `std::unique_ptr<DrawListBase>`：独占绘制列表所有权
- `sk_sp<Task>`：共享任务所有权

确保资源正确释放，避免内存泄漏。

### 5. 组合优于继承

`DrawContext` 包含 `DrawListBase`、`UploadList`、`ComputePathAtlas` 等组件，而不是继承它们。提供灵活性，允许运行时选择不同的实现（如 `DrawList` vs `DrawListLayer`）。

### 6. 双缓冲任务模式

通过 `fCurrentDrawTask` 和 `snapDrawTask()` 实现：
- 当前任务继续积累操作
- 快照任务可以并行提交和执行
- 减少同步点，提高并行度

## 性能考量

### 批处理优化

- 将多个绘制命令收集到单个 `DrawPass` 中
- 将多个上传收集到单个 `UploadTask` 中
- 减少任务切换开销

### 延迟资源分配

- 计算路径图集仅在需要时创建
- 目标副本仅在需要读取目标时创建
- 减少不必要的内存分配

### 选择性刷新

`flush()` 检查 `fPendingDraws->modifiesTarget()`：
- 如果没有实际的绘制到目标，不创建 `RenderPassTask`
- 但保留上传和计算任务，因为它们可能影响其他资源

### MSAA 和深度模板优化

根据实际需求配置渲染通道：
```cpp
const bool drawsRequireMSAA = fPendingDraws->drawsRequireMSAA();
const SkEnumBitMask<DepthStencilFlags> dsFlags = fPendingDraws->depthStencilFlags();
```
避免为不需要的功能分配资源。

### 屏障最小化

仅在必要时插入屏障：
- 检测是否实际需要读取目标
- 检测混合模式是否需要屏障
- 避免不必要的同步点

### 追踪和调试

使用 `TRACE_EVENT` 宏记录关键操作：
- 追踪上传数量
- 追踪 DST 副本创建
- 帮助性能分析和调试

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/graphite/DrawList.h/cpp` | 标准绘制命令列表实现 |
| `src/gpu/graphite/DrawListLayer.h/cpp` | 分层绘制命令列表实现 |
| `src/gpu/graphite/DrawListBase.h` | 绘制列表基类 |
| `src/gpu/graphite/DrawPass.h/cpp` | 不可变渲染通道 |
| `src/gpu/graphite/DrawTask.h/cpp` | 任务图容器 |
| `src/gpu/graphite/UploadList.h/cpp` | 上传操作列表 |
| `src/gpu/graphite/ComputePathAtlas.h/cpp` | 计算路径图集 |
| `src/gpu/graphite/task/UploadTask.h/cpp` | 上传任务实现 |
| `src/gpu/graphite/task/ComputeTask.h/cpp` | 计算任务实现 |
| `src/gpu/graphite/task/RenderPassTask.h/cpp` | 渲染通道任务实现 |
| `src/gpu/graphite/TextureProxy.h/cpp` | 纹理代理 |
| `src/gpu/graphite/TextureProxyView.h` | 纹理视图 |
| `src/gpu/graphite/Caps.h` | 设备能力查询 |
| `src/gpu/graphite/Recorder.h` | 录制器主接口 |
| `src/gpu/graphite/RecorderPriv.h` | 录制器私有接口 |
| `src/gpu/graphite/RenderPassDesc.h` | 渲染通道描述符 |
| `src/gpu/graphite/TextureUtils.h` | 纹理工具函数 |
