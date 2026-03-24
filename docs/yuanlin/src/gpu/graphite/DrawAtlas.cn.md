# DrawAtlas

> 源文件
> - src/gpu/graphite/DrawAtlas.h
> - src/gpu/graphite/DrawAtlas.cpp

## 概述

`DrawAtlas` 是 Skia Graphite 中用于管理纹理图集（Texture Atlas）的核心类。它负责在一个或多个纹理中高效地分配和管理小图像（如字形、路径遮罩等）的存储空间。该类实现了智能的空间分配、内存管理和垃圾回收机制，以优化 GPU 内存使用和渲染性能。

图集纹理被划分为多个 Plot（子区域），每个 Plot 使用 Skyline Rectanizer 算法进行空间分配。`DrawAtlas` 支持多页（multi-page）纹理，可以根据需要动态激活或停用页面，并通过 LRU（最近最少使用）策略和代数系统（generation system）来管理 Plot 的生命周期。

## 架构位置

在 Graphite 渲染架构中的位置：

1. **AtlasProvider** → 创建和管理 `DrawAtlas` 实例
2. **DrawAtlas** → 管理纹理空间分配和生命周期
3. **Plot** → 实际存储子图像的区域单元
4. **Rectanizer** → 在 Plot 内执行空间分配算法
5. **TextureProxy** → 后端纹理资源
6. **UploadTask** → 将 CPU 数据上传到 GPU

应用场景：
- **文本渲染**：存储字形位图
- **路径渲染**：存储路径覆盖蒙版
- **小图像缓存**：缓存频繁使用的小图像

## 主要类与结构体

### DrawAtlas 类

```cpp
class DrawAtlas {
public:
    static constexpr auto kMaxMultitexturePages = 4;
    static constexpr int kMaxPlots = 32;

    enum class ErrorCode {
        kError,      // 不可恢复的错误
        kSucceeded,  // 成功添加
        kTryAgain    // 需要刷新后重试
    };

    enum class AllowMultitexturing : bool { kNo, kYes };
    enum class UseStorageTextures : bool { kNo, kYes };

    // 工厂方法
    static std::unique_ptr<DrawAtlas> Make(
            MaskFormat maskFormat,
            int width, int height,
            int plotWidth, int plotHeight,
            GenerationCounter* generationCounter,
            AllowMultitexturing allowMultitexturing,
            UseStorageTextures useStorageTextures,
            PlotEvictionCallback* evictor,
            std::string_view label);

    // 添加图像到图集
    ErrorCode addToAtlas(Recorder*, int width, int height,
                         const void* image, AtlasLocator*);
    ErrorCode addRect(Recorder*, int width, int height, AtlasLocator*);

    // 准备渲染
    SkPixmap prepForRender(const AtlasLocator&, int padding = 0,
                          std::optional<SkColor> initialColor = {});

    // 记录上传操作
    bool recordUploads(DrawContext*, Recorder*);

    // 生命周期管理
    void setLastUseToken(const AtlasLocator&, Token);
    void setLastUseTokenBulk(const BulkUsePlotUpdater&, Token);
    void compact(Token startTokenForNextFlush);

    // 访问器
    const sk_sp<TextureProxy>* getProxies() const;
    uint32_t atlasID() const;
    uint64_t atlasGeneration() const;
    uint32_t numActivePages() const;
};
```

### PlotLocator 类

标识图集中特定 Plot 的位置：

```cpp
class PlotLocator {
public:
    PlotLocator(uint32_t pageIdx, uint32_t plotIdx, uint64_t generation);

    bool isValid() const;
    void makeInvalid();

    uint32_t pageIndex() const;
    uint32_t plotIndex() const;
    uint64_t genID() const;

private:
    uint64_t fGenID : 48;      // 代数，用于检测失效
    uint64_t fPlotIndex : 8;   // Plot 索引（最多 256）
    uint64_t fPageIndex : 8;   // 页面索引（最多 256）
};
```

### AtlasLocator 类

存储图集中子图像的位置和 UV 坐标：

```cpp
class AtlasLocator {
public:
    std::array<uint16_t, 4> getUVs() const;

    PlotLocator plotLocator() const;
    uint32_t pageIndex() const;
    uint32_t plotIndex() const;
    uint64_t genID() const;

    SkIPoint topLeft() const;
    SkISize dimensions() const;
    uint16_t width() const;
    uint16_t height() const;

    void insetSrc(int padding);
    void updatePlotLocator(PlotLocator p);
    void updateRect(SkIRect rect);

private:
    PlotLocator fPlotLocator;
    std::array<uint16_t, 4> fUVs;  // [left, top, right, bottom]
                                    // 页面索引编码在 U 坐标的第 13、14 位
};
```

**UV 编码设计**：
- 低 13 位：实际坐标（支持最大 8192 像素）
- 第 13-14 位（U 坐标）：页面索引
- 这种编码使得 `width = fUVs[2] - fUVs[0]` 自然成立（页面位相减为 0）

### BulkUsePlotUpdater 类

批量更新多个 Plot 的使用令牌：

```cpp
class BulkUsePlotUpdater {
public:
    BulkUsePlotUpdater();

    bool add(const AtlasLocator& atlasLocator);
    void reset();

    int count() const;
    const PlotData& plotData(int index) const;

private:
    struct PlotData {
        uint32_t fPageIndex;
        uint32_t fPlotIndex;
    };

    STArray<kMinItems, PlotData, true> fPlotsToUpdate;
    uint32_t fPlotAlreadyUpdated[kMaxMultitexturePages];  // 位掩码
};
```

使用位掩码快速检测 Plot 是否已添加，避免重复。

### Plot 类

图集纹理的空间划分单元：

```cpp
class Plot final {
public:
    static std::unique_ptr<Plot> Make(int pageIndex, int plotIndex,
                                     GenerationCounter* generationCounter,
                                     int offX, int offY,
                                     int width, int height,
                                     MaskFormat format);

    // 空间分配
    bool addRect(int width, int height, AtlasLocator* atlasLocator);

    // 数据管理
    void copySubImage(const AtlasLocator&, const void* image);
    SkPixmap prepForRender(const AtlasLocator&, int padding = 0,
                          std::optional<SkColor> initialColor = {});

    // 上传准备
    bool needsUpload();
    std::pair<const void*, SkIRect> prepareForUpload();

    // 生命周期
    Token lastUseToken() const;
    void setLastUseToken(Token);
    void resetRects(bool freeData);

    // 状态查询
    bool isEmpty() const;
    bool hasAllocation() const;
    uint64_t genID() const;

private:
    Token fLastUse;
    int fFlushesSinceLastUse;
    GenerationCounter* const fGenerationCounter;
    uint64_t fGenID;
    PlotLocator fPlotLocator;
    std::unique_ptr<std::byte[]> fData;  // CPU 端数据缓冲
    const int fWidth, fHeight;
    const int fX, fY;
    RectanizerSkyline fRectanizer;
    const SkIPoint16 fOffset;
    const MaskFormat fMaskFormat;
    SkIRect fDirtyRect;
    bool fIsFull;
};
```

### GenerationCounter 类

生成唯一的代数（generation ID）：

```cpp
class GenerationCounter {
public:
    static constexpr uint64_t kInvalidGeneration = 0;
    uint64_t next() { return fGeneration++; }

private:
    uint64_t fGeneration{1};
};
```

### PlotEvictionCallback 接口

Plot 被驱逐时的回调接口：

```cpp
class PlotEvictionCallback {
public:
    virtual ~PlotEvictionCallback() = default;
    virtual void evict(PlotLocator) = 0;
};
```

## 公共 API 函数

### Make（工厂方法）

```cpp
static std::unique_ptr<DrawAtlas> Make(
        MaskFormat maskFormat,
        int width, int height,
        int plotWidth, int plotHeight,
        GenerationCounter* generationCounter,
        AllowMultitexturing allowMultitexturing,
        UseStorageTextures useStorageTextures,
        PlotEvictionCallback* evictor,
        std::string_view label);
```

创建 `DrawAtlas` 实例。参数说明：
- `maskFormat`：蒙版格式（Alpha8、A565、ARGB 等）
- `width/height`：图集纹理尺寸
- `plotWidth/plotHeight`：单个 Plot 尺寸（必须整除纹理尺寸）
- `generationCounter`：代数计数器（通常由 Context 持有）
- `allowMultitexturing`：是否允许多页纹理
- `useStorageTextures`：是否使用存储纹理（计算着色器）
- `evictor`：驱逐回调（可选）

### addToAtlas

```cpp
ErrorCode addToAtlas(Recorder* recorder,
                     int width, int height,
                     const void* image,
                     AtlasLocator* atlasLocator);
```

向图集添加图像数据。该函数：
1. 调用 `addRect` 分配空间
2. 如果成功，复制图像数据到 Plot
3. 返回错误码

**返回值**：
- `kSucceeded`：成功添加
- `kTryAgain`：所有 Plot 被当前绘制使用，需要刷新后重试
- `kError`：不可恢复的错误（如图像过大）

### addRect

```cpp
ErrorCode addRect(Recorder* recorder,
                  int width, int height,
                  AtlasLocator* atlasLocator);
```

仅分配空间，不复制数据。流程：

1. **验证尺寸**：检查是否超过 Plot 尺寸
2. **处理零尺寸**：为逆向填充等特殊情况
3. **尝试现有页面**：遍历活动页面，尝试添加到现有 Plot
4. **驱逐旧 Plot**：如果达到最大页数，尝试驱逐 LRU Plot
5. **激活新页面**：如果未达到最大页数，激活新页面
6. **返回 TryAgain**：所有 Plot 都在使用中

### prepForRender

```cpp
SkPixmap prepForRender(const AtlasLocator& locator,
                       int padding = 0,
                       std::optional<SkColor> initialColor = {});
```

为软件光栅化准备 `SkPixmap`。功能：
- 返回指向 CPU 缓冲区的 Pixmap
- 支持内边距（padding），返回的 Pixmap 排除填充区域
- 可选择性地清除为指定颜色
- 用于需要在 CPU 端渲染的场景（如文本光栅化）

### recordUploads

```cpp
bool recordUploads(DrawContext* dc, Recorder* recorder);
```

记录待上传的脏 Plot 数据。遍历所有活动页面的所有 Plot：
1. 检查是否需要上传（`needsUpload()`）
2. 准备上传数据（`prepareForUpload()`）
3. 创建 `UploadSource`
4. 调用 `DrawContext::recordUpload`

返回 `false` 表示上传失败。

### setLastUseToken

```cpp
void setLastUseToken(const AtlasLocator& atlasLocator, Token token);
```

设置 Plot 的最后使用令牌，防止其被过早驱逐。**关键要求**：每当绘制命令引用图集内容时，必须立即调用此函数，否则下次添加可能会覆盖正在使用的数据。

### compact

```cpp
void compact(Token startTokenForNextFlush);
```

执行垃圾回收和压缩操作。该函数：

1. **更新使用计数**：重置本次 flush 中使用的 Plot 的刷新计数器
2. **识别可用 Plot**：在前面的页面中查找超过 `kPlotRecentlyUsedCount` 未使用的 Plot
3. **驱逐过期 Plot**：在最后一页中驱逐过期的 Plot
4. **压缩策略**：如果最后一页使用率低于 25%，尝试将其内容迁移到前面的页面
5. **停用页面**：如果最后一页完全未使用，停用它

**性能参数**：
- `kPlotRecentlyUsedCount = 32`：超过此刷新次数视为不再使用
- `kPlotUsedCountBeforeEvict = 8`：超过此次数可以考虑驱逐
- `kAtlasRecentlyUsedCount = 128`：图集整体的活跃阈值

## 内部实现细节

### 多页纹理管理

页面数组结构：

```cpp
struct Page {
    std::unique_ptr<std::unique_ptr<Plot>[]> fPlotArray;
    PlotList fPlotList;  // LRU 链表
};
sk_sp<TextureProxy> fProxies[kMaxMultitexturePages];
Page fPages[kMaxMultitexturePages];
```

**页面生命周期**：
- 按需激活：第一次添加时激活第 0 页
- 优先低索引：总是优先向低索引页添加
- 反向停用：仅能从高索引向低索引停用页面

### Plot 分配算法

使用 Skyline Rectanizer：
- 维护轮廓线（skyline），表示已占用区域的顶部
- 新矩形放置时选择最低适配的位置
- 提供良好的空间利用率（通常 > 80%）

### 代数系统（Generation System）

用于检测失效的机制：

```cpp
// 创建时
fGenID = fGenerationCounter->next();
fPlotLocator = PlotLocator(pageIndex, plotIndex, fGenID);

// 驱逐时
fAtlasGeneration = fGenerationCounter->next();

// 检查有效性
bool hasID(const PlotLocator& plotLocator) {
    uint64_t plotGeneration = fPages[page].fPlotArray[plot]->genID();
    uint64_t locatorGeneration = plotLocator.genID();
    return plotGeneration == locatorGeneration;
}
```

客户端（如 Glyph）持有 `PlotLocator`，每次使用前检查代数是否匹配。不匹配说明已被驱逐，需要重新添加。

### LRU 策略

每个页面维护 Plot 的 LRU 链表：
- **头部（MRU）**：最近使用的 Plot
- **尾部（LRU）**：最久未使用的 Plot

```cpp
void makeMRU(Plot* plot, int pageIdx) {
    if (fPages[pageIdx].fPlotList.head() == plot) return;
    fPages[pageIdx].fPlotList.remove(plot);
    fPages[pageIdx].fPlotList.addToHead(plot);
}
```

每次访问 Plot 时，将其移到链表头部。驱逐时从尾部选择。

### 脏矩形跟踪

Plot 维护脏矩形（`fDirtyRect`）：

```cpp
bool addRect(int width, int height, AtlasLocator* atlasLocator) {
    SkIPoint16 loc;
    if (!fRectanizer.addRect(width, height, &loc)) {
        return false;
    }
    auto rect = SkIRect::MakeXYWH(loc.fX, loc.fY, width, height);
    fDirtyRect.join(rect);  // 扩展脏矩形
    // ...
}
```

上传时仅上传脏矩形区域，减少数据传输：

```cpp
std::pair<const void*, SkIRect> prepareForUpload() {
    // 4 字节对齐
    auto bpp = this->bpp();
    unsigned int clearBits = 0x3 / bpp;
    fDirtyRect.fLeft &= ~clearBits;
    fDirtyRect.fRight += clearBits;
    fDirtyRect.fRight &= ~clearBits;

    // 计算数据指针和偏移矩形
    dataPtr = fData.get();
    dataPtr += this->rowBytes() * fDirtyRect.fTop;
    dataPtr += bpp * fDirtyRect.fLeft;
    offsetRect = fDirtyRect.makeOffset(fOffset.fX, fOffset.fY);

    fDirtyRect.setEmpty();
    return {dataPtr, offsetRect};
}
```

### 令牌（Token）系统

使用 Token 跟踪 GPU 执行进度：

```cpp
Token fLastUse;  // Plot 最后一次被绘制使用的 Token

// 在 addRect 中检查
if (plot->lastUseToken() < recorder->priv().tokenTracker()->nextFlushToken()) {
    // 此 Plot 的内容已经被 GPU 使用，可以安全驱逐
    this->processEvictionAndResetRects(plot, /*freeData=*/false);
}
```

确保不会覆盖 GPU 仍在读取的数据。

### 内存管理策略

Plot 数据缓冲按需分配：

```cpp
void* dataAt(SkIPoint atlasPoint) {
    if (!fData) {
        // make_unique 会将数据初始化为零
        fData = std::make_unique<std::byte[]>(this->rowBytes() * fHeight);
    }
    // ...
}
```

驱逐时可选择释放内存：

```cpp
void resetRects(bool freeData) {
    fRectanizer.reset();
    fGenID = fGenerationCounter->next();
    fLastUse = Token::InvalidToken();

    if (freeData) {
        fData = {};  // 释放内存
    } else if (fData) {
        sk_bzero(fData.get(), this->rowBytes() * fHeight);  // 清零
    }
    // ...
}
```

- `freeData=true`：完全停用页面时，节省内存
- `freeData=false`：仅驱逐内容，保留缓冲区供后续使用

### 颜色格式处理

支持 BGRA 交换：

```cpp
void copySubImage(const AtlasLocator& al, const void* image) {
    // ...
    constexpr bool kBGRAIsNative = kN32_SkColorType == kBGRA_8888_SkColorType;
    if (bpp == 4 && kBGRAIsNative) {
        for (int i = 0; i < height; ++i) {
            SkOpts::RGBA_to_BGRA((uint32_t*)dataPtr, (const uint32_t*)imagePtr, width);
            dataPtr += plotRB;
            imagePtr += imageRB;
        }
    } else {
        // 直接复制
        for (int i = 0; i < height; ++i) {
            memcpy(dataPtr, imagePtr, imageRB);
            // ...
        }
    }
}
```

根据平台自动处理颜色通道顺序。

## 依赖关系

**核心依赖**：
- `src/gpu/RectanizerSkyline.h`：空间分配算法
- `src/gpu/Token.h`：GPU 执行追踪
- `src/gpu/MaskFormat.h`：蒙版格式定义
- `TextureProxy.h`：纹理资源代理
- `DrawContext.h`：记录上传操作

**工具类**：
- `src/base/SkTInternalLList.h`：内部链表实现
- `src/core/SkIPoint16.h`：16 位整数点
- `include/private/base/SkTArray.h`：动态数组

**间接依赖**：
- `Recorder.h`：录制器上下文
- `Caps.h`：设备能力查询
- `task/UploadTask.h`：上传任务

## 设计模式与设计决策

### 1. 对象池模式（Object Pool）

Plot 预先分配，重复使用：
- 创建时分配所有 Plot 对象
- 驱逐时重置 Plot 状态，不释放对象
- 避免频繁分配/释放开销

### 2. 策略模式（多页 vs 单页）

通过 `AllowMultitexturing` 控制：
- 单页模式：`fMaxPages = 1`，适合简单场景
- 多页模式：`fMaxPages = 4`，适合复杂场景
- 相同接口，不同行为

### 3. 惰性初始化（Lazy Initialization）

- 页面按需激活：仅在需要时创建 `TextureProxy`
- Plot 数据按需分配：仅在首次写入时分配缓冲区
- 减少初始内存占用

### 4. 代数计数器模式

用整数代数而非指针验证有效性：
- 避免悬空指针问题
- 客户端可以安全持有 `PlotLocator`
- 轻量级失效检测

### 5. 观察者模式（驱逐回调）

通过 `PlotEvictionCallback` 通知客户端：
```cpp
for (PlotEvictionCallback* evictor : fEvictionCallbacks) {
    evictor->evict(plotLocator);
}
```
客户端可以清理缓存、更新索引等。

### 6. 命令模式（延迟上传）

不立即上传，而是：
1. 记录脏区域
2. 在 `recordUploads` 中批量生成上传命令
3. 减少 GPU 命令数量，提高效率

## 性能考量

### 空间利用率

- **Skyline 算法**：通常达到 80-90% 的利用率
- **Plot 划分**：平衡碎片化和灵活性（通常 256x256 或 512x512）
- **多页纹理**：避免单个巨大纹理的浪费

### 上传优化

- **脏矩形**：仅上传修改的区域
- **4 字节对齐**：优化 GPU 传输效率
- **批量上传**：一次 flush 中所有脏 Plot 一起上传

### 缓存局部性

- **LRU 排序**：频繁使用的 Plot 在链表头部，提高缓存命中率
- **页面优先级**：优先使用低索引页，提高数据紧密度

### 垃圾回收策略

调优参数平衡性能和内存：
- **激进回收**：降低参数，快速释放内存，但可能增加重新分配
- **保守回收**：提高参数，减少重新分配，但占用更多内存

当前默认值适合一般场景（文本渲染、UI 等）。

### 零尺寸矩形处理

```cpp
if (width == 0 || height == 0) {
    atlasLocator->updateRect(SkIRect::MakeEmpty());
    atlasLocator->updatePlotLocator(fPages[0].fPlotList.head()->plotLocator());
    return ErrorCode::kSucceeded;
}
```

支持逆向填充等特殊路径操作，避免在 Rectanizer 中浪费时间。

### 调试和追踪

```cpp
#if defined(DUMP_ATLAS_DATA)
static const constexpr bool kDumpAtlasData = true;
#else
static const constexpr bool kDumpAtlasData = false;
#endif
```

可选的调试输出，帮助分析图集使用模式。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/RectanizerSkyline.h/cpp` | Skyline 矩形打包算法 |
| `src/gpu/Token.h` | GPU 执行令牌系统 |
| `src/gpu/MaskFormat.h` | 蒙版格式定义 |
| `src/gpu/graphite/TextureProxy.h/cpp` | 纹理代理 |
| `src/gpu/graphite/DrawContext.h/cpp` | 绘制上下文 |
| `src/gpu/graphite/AtlasProvider.h/cpp` | 图集提供者 |
| `src/gpu/graphite/Recorder.h` | 录制器主接口 |
| `src/gpu/graphite/RecorderPriv.h` | 录制器私有接口 |
| `src/gpu/graphite/Caps.h` | 设备能力查询 |
| `src/gpu/graphite/task/UploadTask.h/cpp` | 上传任务实现 |
| `src/base/SkTInternalLList.h` | 内部链表容器 |
| `src/core/SkIPoint16.h` | 16 位整数点 |
| `include/private/base/SkTArray.h` | 动态数组容器 |
