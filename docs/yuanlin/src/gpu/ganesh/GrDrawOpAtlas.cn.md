# GrDrawOpAtlas

> 源文件: src/gpu/ganesh/GrDrawOpAtlas.h, src/gpu/ganesh/GrDrawOpAtlas.cpp

## 概述

`GrDrawOpAtlas` 是 Ganesh GPU 后端中管理固定尺寸多页纹理图集的核心类,专门用于支持绘制操作(DrawOps)的纹理上传。该类实现了复杂的资源管理策略,包括多纹理页支持、ASAP/inline 上传模式切换、LRU 驱逐策略、以及智能的垃圾回收机制。

主要功能包括:
- **多页支持**: 支持最多 4 个纹理页,根据需求动态激活和停用
- **智能上传**: 根据数据冒险检测自动在 ASAP 和 inline 上传模式间切换
- **LRU 管理**: 每页维护 Plot 的 MRU 链表,优先驱逐最少使用的 Plot
- **垃圾回收**: 定期压缩图集,将高索引页的数据迁移到低索引页,释放未使用页
- **驱逐通知**: 通过回调机制通知客户端 Plot 被驱逐,避免悬空引用
- **Token 同步**: 使用 GPU Token 系统追踪上传和使用时间,避免数据冒险

## 架构位置

该模块位于 Ganesh 渲染管线的纹理图集层:

```
src/gpu/ganesh/
├── GrDrawOpAtlas.h/cpp              # 固定尺寸图集(当前模块)
├── GrAtlasTypes.h                   # 图集基础类型
├── GrDynamicAtlas.h/cpp             # 动态增长图集
├── text/
│   └── GrAtlasManager.h/cpp         # 字形图集管理器
└── ops/
    └── AtlasTextOp.cpp              # 文字操作使用图集
```

**主要使用场景**:
- 字形渲染的纹理缓存
- SDF(Signed Distance Field)文字
- 小路径的纹理化缓存

## 主要类与结构体

### GrDrawOpAtlas
固定尺寸多页纹理图集主类。

```cpp
class GrDrawOpAtlas {
public:
    enum class AllowMultitexturing : bool { kNo, kYes };
    enum class ErrorCode { kError, kSucceeded, kTryAgain };

    static std::unique_ptr<GrDrawOpAtlas> Make(
        GrProxyProvider* proxyProvider,
        const GrBackendFormat& format,
        SkColorType ct, size_t bpp,
        int width, int height,
        int plotWidth, int plotHeight,
        GrAtlasGenerationCounter* generationCounter,
        AllowMultitexturing allowMultitexturing,
        GrPlotEvictionCallback* evictor,
        std::string_view label);

    ErrorCode addToAtlas(GrResourceProvider*,
                         GrDeferredUploadTarget*,
                         int width, int height,
                         const void* image,
                         GrAtlasLocator*);

    void setLastUseToken(const GrAtlasLocator&, skgpu::Token);
    void compact(skgpu::Token startTokenForNextFlush);
    void instantiate(GrOnFlushResourceProvider*);
};
```

**核心成员变量**:
- `fViews[4]`: 纹理代理视图数组,最多 4 页
- `fPages[4]`: 页数组,每页包含 Plot 数组和 LRU 链表
- `fNumActivePages`: 当前激活的页数
- `fAtlasGeneration`: 图集代数,驱逐时递增
- `fPrevFlushToken`: 上次 flush 的 Token
- `fEvictionCallbacks`: 驱逐回调向量

### GrDrawOpAtlas::Page
单个图集页的数据结构。

```cpp
struct Page {
    std::unique_ptr<sk_sp<GrPlot>[]> fPlotArray;  // Plot 数组
    GrPlotList fPlotList;                         // MRU 链表
};
```

### GrDrawOpAtlasConfig
图集配置类,根据内存预算计算图集和 Plot 尺寸。

```cpp
class GrDrawOpAtlasConfig {
public:
    GrDrawOpAtlasConfig(int maxTextureSize, size_t maxBytes);
    SkISize atlasDimensions(skgpu::MaskFormat type) const;
    SkISize plotDimensions(skgpu::MaskFormat type) const;

private:
    static constexpr int kMaxAtlasDim = 2048;
    SkISize fARGBDimensions;
    int fMaxTextureSize;
};
```

## 公共 API 函数

### GrDrawOpAtlas::Make
创建图集实例的工厂方法。

```cpp
static std::unique_ptr<GrDrawOpAtlas> Make(...)
```

**功能**:
1. 验证后端格式有效性
2. 构造图集对象
3. 调用 `createPages` 创建所有页的代理和 Plot
4. 注册驱逐回调

**返回**: 成功返回图集唯一指针,失败返回 `nullptr`

### GrDrawOpAtlas::addToAtlas
向图集添加子图像。

```cpp
ErrorCode addToAtlas(GrResourceProvider* resourceProvider,
                     GrDeferredUploadTarget* target,
                     int width, int height,
                     const void* image,
                     GrAtlasLocator* atlasLocator)
```

**实现流程**:
1. **尺寸检查**: 如果 `width > fPlotWidth` 或 `height > fPlotHeight`,返回 `kError`
2. **尝试现有页**: 从第一页开始遍历,尝试在现有 Plot 中分配空间
3. **驱逐策略**: 如果达到最大页数,尝试驱逐已 flush 的最旧 Plot
4. **激活新页**: 如果未达最大页数,激活新页并重试
5. **Inline 上传**: 如果以上都失败,找到未在当前绘制中使用的 Plot,执行 inline 上传
6. **返回 kTryAgain**: 如果所有 Plot 都在使用中,返回 `kTryAgain` 让操作结束当前绘制

**错误码**:
- `kSucceeded`: 成功添加
- `kTryAgain`: 需要结束当前绘制后重试
- `kError`: 不可恢复错误

### GrDrawOpAtlas::setLastUseToken
设置 Plot 的最后使用 Token,防止驱逐。

```cpp
void setLastUseToken(const GrAtlasLocator& atlasLocator, skgpu::Token token)
```

**功能**:
1. 验证 PlotLocator 有效性
2. 将 Plot 移动到 MRU 链表头
3. 设置 Plot 的 `fLastUse` Token

**重要性**: 绘制操作在准备读取图集数据的绘制时必须立即调用此函数,否则下次 `addToAtlas` 可能覆盖数据。

### GrDrawOpAtlas::setLastUseTokenBulk
批量设置多个 Plot 的最后使用 Token。

```cpp
void setLastUseTokenBulk(const GrBulkUsePlotUpdater& updater, skgpu::Token token)
```

**优化**: 使用 `GrBulkUsePlotUpdater` 避免重复更新同一 Plot。

### GrDrawOpAtlas::compact
执行垃圾回收,压缩图集并释放未使用页。

```cpp
void compact(skgpu::Token startTokenForNextFlush)
```

**实现流程**:
1. **重置计数器**: 对在本次 flush 中使用的 Plot,重置 `fFlushesSinceLastUsed`
2. **构建可用列表**: 收集前 N-1 页中超过 32 次 flush 未使用的 Plot
3. **驱逐老化 Plot**: 驱逐最后一页中老化的 Plot
4. **迁移策略**: 如果最后一页使用率低于 25%,且前面页有空间,驱逐最后一页的 Plot 触发迁移
5. **停用页**: 如果最后一页完全未使用,停用该页释放纹理

**调用时机**: 通常在 `GrOnFlushCallbackObject::postFlush()` 中调用。

### GrDrawOpAtlas::uploadToPage
尝试在指定页上传子图像。

```cpp
bool uploadToPage(unsigned int pageIdx,
                  GrDeferredUploadTarget* target,
                  int width, int height,
                  const void* image,
                  GrAtlasLocator* atlasLocator)
```

**功能**: 遍历页的 MRU 链表,尝试在 Plot 中添加子图像,成功则调用 `updatePlot` 安排上传。

### GrDrawOpAtlas::activateNewPage
激活新的图集页。

```cpp
bool activateNewPage(GrResourceProvider* resourceProvider)
```

**功能**: 实例化下一页的纹理代理,递增 `fNumActivePages`。

### GrDrawOpAtlas::deactivateLastPage
停用最后一页。

```cpp
void deactivateLastPage()
```

**功能**:
1. 重置最后一页所有 Plot 的矩形分配
2. 重建 LRU 链表
3. 去实例化纹理代理释放 GPU 内存
4. 递减 `fNumActivePages`

## 内部实现细节

### 上传模式切换

`updatePlot` 根据 Token 判断上传模式:

```cpp
if (plot->lastUploadToken() < target->tokenTracker()->nextFlushToken()) {
    target->addASAPUpload([...] { uploadPlotToTexture(...); });
} // else 搭便车现有上传
```

**ASAP 模式**: 在 flush 开始时尽早上传
**Inline 模式**: 在绘制之间上传

### Plot 驱逐和克隆

当需要 inline 上传时,克隆 Plot 避免修改正在使用的数据:

```cpp
sk_sp<GrPlot>& newPlot = fPages[pageIdx].fPlotArray[plot->plotIndex()];
newPlot = plot->clone();
```

**原因**: 原 Plot 可能在当前 Token 的绘制中被引用,克隆确保不覆盖其数据。

### 驱逐回调机制

`processEviction` 通知所有注册的回调:

```cpp
for (GrPlotEvictionCallback* evictor : fEvictionCallbacks) {
    evictor->evict(plotLocator);
}
fAtlasGeneration = fGenerationCounter->next();
```

客户端(如字形缓存)在回调中使缓存的 PlotLocator 失效。

### 垃圾回收策略

**老化阈值**:
- `kPlotRecentlyUsedCount = 32`: Plot 被认为活跃的 flush 次数
- `kAtlasRecentlyUsedCount = 128`: 图集被认为活跃的 flush 次数

**压缩触发条件**:
- 图集在本次 flush 中被使用,或
- 图集超过 128 次 flush 未使用(处理闪烁光标场景)

**迁移策略**:
1. 优先上传到低索引页
2. 最后一页使用率低于 25% 时触发主动驱逐
3. 驱逐最后一页的活跃 Plot,同时驱逐前面页的老化 Plot,创造迁移机会

### MRU 链表维护

`makeMRU` 将 Plot 移动到链表头:

```cpp
inline void makeMRU(GrPlot* plot, uint32_t pageIdx) {
    if (fPages[pageIdx].fPlotList.head() == plot) {
        return;
    }
    fPages[pageIdx].fPlotList.remove(plot);
    fPages[pageIdx].fPlotList.addToHead(plot);
}
```

**用途**: 每次访问 Plot 时更新 MRU,驱逐时从链表尾部开始。

### Plot 网格布局

Plot 按从右到左、从下到上的顺序创建:

```cpp
for (int y = numPlotsY - 1, r = 0; y >= 0; --y, ++r) {
    for (int x = numPlotsX - 1, c = 0; x >= 0; --x, ++c) {
        uint32_t plotIndex = r * numPlotsX + c;
        currPlot->reset(new GrPlot(i, plotIndex, ..., x, y, ...));
    }
}
```

**plotIndex 映射**: `plotIndex = row * numPlotsX + col`,其中 `row = numPlotsY - 1 - y`。

## 依赖关系

### 外部依赖
```cpp
#include "src/gpu/ganesh/GrAtlasTypes.h"        // Plot, AtlasLocator 等类型
#include "src/gpu/ganesh/GrDeferredUpload.h"    // 延迟上传系统
#include "src/gpu/ganesh/GrSurfaceProxyView.h"  // 纹理代理视图
#include "src/gpu/MaskFormat.h"                 // 掩码格式枚举
```

### 被依赖模块
- `src/gpu/ganesh/text/GrAtlasManager.h` - 管理多个格式的图集
- `src/gpu/ganesh/text/GrTextBlob.cpp` - 文字块使用图集
- `src/gpu/ganesh/ops/AtlasTextOp.cpp` - 文字绘制操作

## 设计模式与设计决策

### 1. 工厂方法模式
使用静态 `Make` 方法创建对象:

```cpp
static std::unique_ptr<GrDrawOpAtlas> Make(...)
```

**优势**: 可以在构造失败时返回 `nullptr`,而不是抛出异常。

### 2. 观察者模式
通过 `GrPlotEvictionCallback` 通知驱逐:

```cpp
std::vector<GrPlotEvictionCallback*> fEvictionCallbacks;
```

支持多个观察者响应同一驱逐事件。

### 3. 延迟实例化
纹理代理在构造时创建,但实际纹理延迟到 `activateNewPage` 时分配:

```cpp
fViews[fNumActivePages].proxy()->instantiate(resourceProvider)
```

**优势**: 避免过早占用 GPU 内存。

### 4. 三返回值错误处理
`ErrorCode` 枚举区分三种结果:
- `kSucceeded`: 成功
- `kTryAgain`: 需要客户端协作(结束绘制)
- `kError`: 不可恢复错误

**优势**: 比布尔值提供更丰富的错误信息。

### 5. Token 同步
使用 `skgpu::Token` 系统追踪时序:

```cpp
skgpu::Token fLastUpload;  // 上传时间
skgpu::Token fLastUse;     // 使用时间
```

**优势**: 精确判断数据冒险,避免过早驱逐或覆盖。

### 6. 分级老化策略
使用两级老化阈值:
- Plot 级别: 32 次 flush
- Atlas 级别: 128 次 flush

**原因**: 处理不同使用模式(持续渲染 vs 闪烁光标)。

## 性能考量

### 1. 优先低索引页
上传和驱逐都优先低索引页:
- **上传**: 从 page 0 开始尝试
- **驱逐**: 从最后一页开始驱逐

**收益**: 将活跃数据集中在低索引页,高索引页可以完全停用释放内存。

### 2. ASAP vs Inline 权衡
- **ASAP**: 并行 CPU/GPU,低延迟,但可能浪费带宽
- **Inline**: 串行,高延迟,但避免不必要上传

自动切换策略在大多数场景下接近最优。

### 3. MRU 链表
O(1) 的访问和驱逐操作:
- 访问时移动到头部
- 驱逐从尾部取出

### 4. 批量 Token 更新
`setLastUseTokenBulk` 配合 `GrBulkUsePlotUpdater` 避免重复操作:
- 文字渲染中同一字形可能在多个绘制中使用
- 位掩码快速去重

### 5. 渐进式垃圾回收
不是一次性驱逐所有老化 Plot,而是逐步迁移:
- 避免帧率抖动
- 保持热数据在缓存中

### 6. Plot 克隆 vs 等待
在 inline 上传时克隆 Plot:
- **克隆成本**: 小对象分配 + 元数据复制
- **等待成本**: 阻塞 CPU,降低并行度

大多数情况下克隆更优。

### 7. 配置优化
`GrDrawOpAtlasConfig` 根据内存预算选择尺寸:
- A8 格式图集是 ARGB 的 2 倍(字形更频繁)
- 更大的 Plot 尺寸用于 SDF 字形(最大 170×170)

## 相关文件

### 核心实现
- `src/gpu/ganesh/GrAtlasTypes.h/cpp` - 图集基础类型
- `src/gpu/ganesh/GrDynamicAtlas.h/cpp` - 动态图集

### 上传系统
- `src/gpu/ganesh/GrDeferredUpload.h` - 延迟上传抽象
- `src/gpu/ganesh/GrDeferredUploadTarget.h` - 上传目标接口

### 使用模块
- `src/gpu/ganesh/text/GrAtlasManager.h/cpp` - 图集管理器
- `src/gpu/ganesh/text/GrTextBlob.cpp` - 文字块
- `src/gpu/ganesh/ops/AtlasTextOp.cpp` - 文字操作

### 资源管理
- `src/gpu/ganesh/GrResourceProvider.h` - 资源提供者
- `src/gpu/ganesh/GrOnFlushResourceProvider.h` - Flush 时资源提供者

### 测试文件
- `tests/DrawOpAtlasTest.cpp` - 图集单元测试
