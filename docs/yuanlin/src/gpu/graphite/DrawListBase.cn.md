# DrawListBase

> 源文件
> - src/gpu/graphite/DrawListBase.h

## 概述

`DrawListBase` 是所有绘制列表实现的抽象基类，定义了记录绘制命令和生成绘制通道（DrawPass）的统一接口。它为 `DrawList` 和 `DrawListLayer` 两种实现提供共享的基础设施，包括变换去重、uniform 数据缓存、纹理缓存和管线缓存。

该类还提供了两个重要的内部辅助类：`UniformTracker` 和 `TextureTracker`，用于管理 uniform 缓冲区和纹理绑定的状态跟踪。

## 主要类与结构体

### DrawListBase 类

```cpp
class DrawListBase {
public:
    static constexpr int kMaxRenderSteps = 4096;

    DrawListBase() {}
    virtual ~DrawListBase() = default;

    // 纯虚函数 - 子类必须实现
    virtual std::pair<DrawParams*, Insertion> recordDraw(...) = 0;
    virtual std::unique_ptr<DrawPass> snapDrawPass(...) = 0;

    // 查询方法
    int renderStepCount() const;
    bool modifiesTarget() const;
    bool samplesTexture(const TextureProxy* texture) const;
    const Rect& dstReadBounds() const;
    const Rect& passBounds() const;
    bool drawsReadDst() const;
    bool drawsRequireMSAA() const;
    SkEnumBitMask<DepthStencilFlags> depthStencilFlags() const;

    // 重置状态
    virtual void reset(LoadOp op, SkColor4f clearColor = {});

protected:
    // 变换去重
    const Transform& deduplicateTransform(const Transform& localToDevice);

    // 共享缓存
    SkTBlockList<Transform, 4> fTransforms;
    UniformDataCache fUniformDataCache;
    TextureDataCache fTextureDataCache;
    GraphicsPipelineCache fPipelineCache;

    // 统计信息
    int fRenderStepCount = 0;
    Rect fDstReadBounds;
    Rect fPassBounds;
    bool fRequiresMSAA = false;
    SkEnumBitMask<DepthStencilFlags> fDepthStencilFlags;
    LoadOp fLoadOp = LoadOp::kLoad;
    std::array<float, 4> fClearColor;

    // 辅助类
    class UniformTracker;
    class TextureTracker;
};
```

### UniformTracker 类

管理 uniform 数据的上传和绑定：

```cpp
class UniformTracker {
public:
    UniformTracker(bool useStorageBuffers);

    // 写入 uniform 数据到缓冲区，返回是否需要重新绑定
    bool writeUniforms(UniformDataCache& uniformCache,
                      DrawBufferManager* bufferMgr,
                      UniformDataCache::Index index);

    // 绑定 uniform 缓冲区
    void bindUniforms(UniformSlot slot, DrawPassCommands::List* commandList);

    // 获取 SSBO 索引（仅当使用存储缓冲区时有效）
    uint32_t ssboIndex() const;

private:
    BufferSubAllocator fCurrentBuffer;
    BindBufferInfo fLastBinding;
    UniformDataCache::Index fLastIndex;
    const bool fUseStorageBuffers;
};
```

**关键特性**：
- **UBO 模式**：每次绘制都需要绑定不同偏移的缓冲区
- **SSBO 模式**：数据写入大缓冲区，仅在缓冲区切换时重新绑定，通过索引访问

### TextureTracker 类

跟踪纹理绑定状态：

```cpp
class TextureTracker {
public:
    TextureTracker(TextureDataCache* textureCache);

    // 设置当前纹理绑定，返回是否需要重新绑定
    bool setCurrentTextureBindings(TextureDataCache::Index bindingIndex);

    // 绑定纹理和采样器
    void bindTextures(DrawPassCommands::List* commandList);

private:
    TextureDataCache::Index fLastIndex;
    TextureDataCache* const fTextureCache;
};
```

## 公共 API 函数

### recordDraw（纯虚函数）

```cpp
virtual std::pair<DrawParams*, Insertion> recordDraw(
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
        const Insertion& latestInsertion) = 0;
```

记录一个绘制命令。子类实现不同的记录策略（排序键 vs 分层）。

### snapDrawPass（纯虚函数）

```cpp
virtual std::unique_ptr<DrawPass> snapDrawPass(
        Recorder* recorder,
        sk_sp<TextureProxy> target,
        const SkImageInfo& targetInfo,
        const DstReadStrategy dstReadStrategy) = 0;
```

将记录的绘制命令转换为不可变的 DrawPass 对象。

### reset

```cpp
virtual void reset(LoadOp op, SkColor4f clearColor = {});
```

重置所有状态，清空缓存和统计信息。保留内存分配以供重用。

### deduplicateTransform

```cpp
const Transform& deduplicateTransform(const Transform& localToDevice);
```

去重变换矩阵。如果变换与最后一个相同，返回最后一个的引用；否则添加新变换并返回引用。减少内存占用和比较开销。

## 内部实现细节

### UniformTracker 的两种模式

**Uniform Buffer Object (UBO) 模式**：
- 每次绘制都需要绑定不同的缓冲区偏移
- 偏移需要满足对齐要求（通常 256 字节）
- 适合支持 UBO 但不支持 SSBO 的设备

**Storage Buffer Object (SSBO) 模式**：
- 将所有 uniform 数据写入大缓冲区
- 仅在缓冲区切换时重新绑定
- 通过 `fLastBinding.fOffset` 存储 SSBO 索引
- 绘制时使用索引访问数据
- 减少绑定命令，提高性能

关键代码：

```cpp
if (fUseStorageBuffers) {
    // SSBO 模式：偏移存储索引，大小为整个缓冲区
    uniformData.fBufferBinding.fOffset /= uniformDataSize;
    uniformData.fBufferBinding.fSize = uniformData.fBufferBinding.fBuffer->size();
} else {
    // UBO 模式：确保对齐
    fCurrentBuffer.resetForNewBinding();
}
```

### 缓存系统

三个缓存协同工作：

1. **UniformDataCache**：缓存 uniform 数据块
   - 键：数据内容的哈希
   - 值：CPU 数据 + GPU 缓冲区绑定信息

2. **TextureDataCache**：缓存纹理绑定配置
   - 键：纹理代理和采样器的组合
   - 值：`TextureDataBlock`

3. **GraphicsPipelineCache**：缓存管线描述符
   - 键：渲染步骤 ID + paint 参数 ID
   - 值：索引（实际管线由后端延迟创建）

### 统计信息跟踪

`DrawListBase` 跟踪各种渲染需求：

- **fRenderStepCount**：总渲染步骤数
- **fPassBounds**：所有绘制的联合边界
- **fDstReadBounds**：需要读取目标的绘制边界
- **fRequiresMSAA**：是否需要 MSAA
- **fDepthStencilFlags**：深度和模板需求

这些信息用于优化 `DrawPass` 创建和资源分配。

## 依赖关系

**核心依赖**：
- `DrawCommands.h`：命令列表类型
- `DrawOrder.h`：绘制顺序
- `DrawParams.h`：绘制参数
- `PipelineData.h`：管线数据收集
- `Transform.h`：变换矩阵

**缓存依赖**：
- `ContextUtils.h`：缓存实现（`UniformDataCache`、`TextureDataCache`、`GraphicsPipelineCache`）

**工具类**：
- `src/base/SkTBlockList.h`：块分配列表
- `src/base/SkEnumBitMask.h`：枚举位掩码

## 设计模式与设计决策

### 1. 模板方法模式

`DrawListBase` 定义框架，子类实现具体策略：
- `recordDraw` 和 `snapDrawPass` 是模板方法
- 共享基础设施（缓存、统计）在基类
- 具体算法（排序 vs 分层）在子类

### 2. 策略模式（UBO vs SSBO）

`UniformTracker` 根据 `fUseStorageBuffers` 标志选择策略：
- 相同接口
- 不同的上传和绑定逻辑
- 运行时选择

### 3. 缓存模式

三个缓存避免重复数据：
- 减少 GPU 内存占用
- 减少数据传输
- 通过索引引用

### 4. 对象池（变换去重）

`fTransforms` 使用 `SkTBlockList`：
- 避免重复存储相同变换
- 稳定指针/引用
- 块分配提高效率

## 性能考量

### Uniform 上传优化

- **延迟上传**：仅在数据首次使用时上传
- **缓存检测**：`fLastIndex` 避免重复上传
- **SSBO 重用**：在 SSBO 模式下，如果缓冲区相同且数据已上传，重用而非上传新副本

### 绑定最小化

- **状态跟踪**：`fLastBinding` 和 `fLastIndex` 跟踪当前绑定
- **条件绑定**：仅在状态实际改变时发出绑定命令
- **批处理**：相同绑定的绘制自动批处理

### 内存效率

- **变换去重**：减少重复存储（常见场景下节省 50%+）
- **缓存共享**：uniform 和纹理数据跨绘制共享
- **块分配**：`SkTBlockList` 减少分配次数

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/graphite/DrawList.h/cpp` | 排序键实现 |
| `src/gpu/graphite/DrawListLayer.h/cpp` | 分层实现 |
| `src/gpu/graphite/DrawPass.h/cpp` | 绘制通道输出 |
| `src/gpu/graphite/DrawCommands.h` | 命令列表定义 |
| `src/gpu/graphite/DrawParams.h` | 绘制参数 |
| `src/gpu/graphite/PipelineData.h` | 管线数据收集器 |
| `src/gpu/graphite/ContextUtils.h` | 缓存实现 |
| `src/gpu/graphite/geom/Transform.h` | 变换矩阵 |
| `src/base/SkTBlockList.h` | 块分配列表容器 |
