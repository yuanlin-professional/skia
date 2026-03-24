# GrAtlasTypes

> 源文件: src/gpu/ganesh/GrAtlasTypes.h, src/gpu/ganesh/GrAtlasTypes.cpp

## 概述

`GrAtlasTypes` 模块定义了 Ganesh GPU 后端中用于纹理图集(Atlas)管理的核心数据类型和抽象接口。该模块提供了图集空间分配、位置编码、代数管理、驱逐回调等关键功能,是 Ganesh 渲染管线中资源管理的基础设施。

主要功能包括:
- **空间表示**: 提供 16 位整数矩形 `GrIRect16` 用于紧凑的空间表示
- **代数追踪**: 通过 `GrAtlasGenerationCounter` 和 `GrPlotLocator` 追踪图集版本
- **位置编码**: `GrAtlasLocator` 将图集位置编码到 UV 坐标中,支持多页图集
- **Plot 管理**: `GrPlot` 类管理图集中的子区域,使用 Skyline 算法进行空间分配
- **批量更新**: `GrBulkUsePlotUpdater` 支持高效的批量 Plot 使用标记
- **驱逐通知**: `GrPlotEvictionCallback` 接口允许客户端响应 Plot 驱逐事件

## 架构位置

该模块位于 Ganesh GPU 后端的核心层:

```
src/gpu/ganesh/
├── GrAtlasTypes.h/cpp          # 图集类型定义(当前模块)
├── GrDrawOpAtlas.h/cpp          # 使用这些类型的图集实现
├── GrDynamicAtlas.h/cpp         # 动态图集实现
└── text/                        # 文字渲染使用图集
    └── GrAtlasManager.h/cpp     # 图集管理器
```

**依赖关系**:
- 被 `GrDrawOpAtlas` 和 `GrDynamicAtlas` 使用作为基础类型
- 被文字渲染系统用于字形缓存
- 被路径渲染器用于小路径缓存

## 主要类与结构体

### GrIRect16
16 位整数矩形,用于节省内存的空间表示。

```cpp
struct GrIRect16 {
    int16_t fLeft, fTop, fRight, fBottom;

    static GrIRect16 MakeWH(int16_t w, int16_t h);
    static GrIRect16 MakeXYWH(int16_t x, int16_t y, int16_t w, int16_t h);
    int width() const;
    int height() const;
    void offset(int16_t dx, int16_t dy);
};
```

### GrAtlasGenerationCounter
代数计数器,用于追踪图集和 Plot 的版本。

```cpp
class GrAtlasGenerationCounter {
    static constexpr uint64_t kInvalidGeneration = 0;
    uint64_t next();  // 返回下一个代数并递增
};
```

### GrPlotLocator
Plot 定位器,编码页索引、Plot 索引和代数信息。

```cpp
class GrPlotLocator {
    static constexpr auto kMaxMultitexturePages = 4;  // 最多 4 页
    static constexpr int kMaxPlots = 32;              // 每页最多 32 个 Plots

    GrPlotLocator(uint32_t pageIdx, uint32_t plotIdx, uint64_t generation);
    bool isValid() const;
    uint32_t pageIndex() const;
    uint32_t plotIndex() const;
    uint64_t genID() const;
};
```

**位域布局**: 使用 64 位整数紧凑存储:
- 48 位代数 ID
- 8 位 Plot 索引
- 8 位页索引

### GrAtlasLocator
图集定位器,编码 UV 坐标和页索引信息。

```cpp
class GrAtlasLocator {
    std::array<uint16_t, 4> getUVs() const;  // 返回 [left, top, right, bottom]
    uint32_t pageIndex() const;
    SkIPoint topLeft() const;
    uint16_t width() const;
    uint16_t height() const;
    void updatePlotLocator(GrPlotLocator p);
    void updateRect(GrIRect16 rect);
    void insetSrc(int padding);
};
```

**UV 编码设计**: UV 坐标的第 13-14 位存储页索引,低 13 位存储实际坐标。这种编码有两个优点:
1. 宽度计算 `fUVs[2] - fUVs[0]` 自动消除页索引位
2. 单个 64 位值可以同时存储位置和页信息

### GrPlotEvictionCallback
驱逐回调接口,当 Plot 被驱逐时通知客户端。

```cpp
class GrPlotEvictionCallback {
    virtual void evict(GrPlotLocator) = 0;
};
```

### GrBulkUsePlotUpdater
批量 Plot 使用更新器,使用位掩码避免重复更新。

```cpp
class GrBulkUsePlotUpdater {
    bool add(const GrAtlasLocator& atlasLocator);  // 添加待更新的 Plot
    void reset();
    int count() const;
    const PlotData& plotData(int index) const;
};
```

使用位掩码 `fPlotAlreadyUpdated[4]` 追踪已标记的 Plot,每个 32 位整数覆盖一页的 32 个 Plots。

### GrPlot
图集中的子区域,使用 Skyline 算法管理空间分配。

```cpp
class GrPlot : public SkRefCnt {
    GrPlot(int pageIndex, int plotIndex,
           GrAtlasGenerationCounter* generationCounter,
           int offX, int offY, int width, int height,
           SkColorType colorType, size_t bpp);

    bool addSubImage(int width, int height,
                     const void* image,
                     GrAtlasLocator* atlasLocator);
    std::pair<const void*, SkIRect> prepareForUpload();
    void resetRects(bool freeData);
    sk_sp<GrPlot> clone() const;
};
```

## 公共 API 函数

### GrPlot::addSubImage
向 Plot 添加子图像。

```cpp
bool GrPlot::addSubImage(int width, int height,
                         const void* image,
                         GrAtlasLocator* atlasLocator)
```

**功能**:
1. 调用 `addRect` 在 Rectanizer 中分配空间
2. 将图像数据复制到 Plot 的后备缓冲区
3. 如果需要,执行 RGBA 到 BGRA 的像素格式转换
4. 更新脏矩形用于后续上传

**返回**: 如果空间分配成功返回 `true`

### GrPlot::prepareForUpload
准备脏区域数据供 GPU 上传。

```cpp
std::pair<const void*, SkIRect> GrPlot::prepareForUpload()
```

**功能**:
1. 将脏矩形对齐到 4 字节边界以提高上传效率
2. 计算数据指针偏移到脏区域起始位置
3. 将脏矩形转换为图集全局坐标
4. 清空脏标记

**返回**: 数据指针和上传区域的矩形

### GrPlot::resetRects
重置 Plot 状态,用于驱逐后的重用。

```cpp
void GrPlot::resetRects(bool freeData)
```

**功能**:
1. 重置 Rectanizer 释放所有分配
2. 递增代数 ID
3. 重置 Token 标记
4. 可选地释放或清零后备数据

**参数**: `freeData` 为 `true` 时释放内存,否则清零

### GrAtlasLocator::updatePlotLocator
更新定位器的 Plot 信息并编码到 UV 中。

```cpp
void GrAtlasLocator::updatePlotLocator(GrPlotLocator p)
```

**实现细节**:
1. 存储新的 `GrPlotLocator`
2. 提取页索引并左移 13 位
3. 保留 UV 坐标的低 13 位,更新高位为页索引

### GrBulkUsePlotUpdater::add
添加 Plot 到批量更新列表。

```cpp
bool GrBulkUsePlotUpdater::add(const GrAtlasLocator& atlasLocator)
```

**功能**: 使用位掩码检查 Plot 是否已添加,避免重复更新。

**返回**: 如果是新添加返回 `true`,已存在返回 `false`

## 内部实现细节

### GrPlot 的延迟分配策略

Plot 的后备数据 `fData` 采用延迟分配:

```cpp
void* GrPlot::dataAt(SkIPoint atlasPoint) {
    if (!fData) {
        fData = reinterpret_cast<std::byte*>(
            sk_calloc_throw(this->rowBytes() * fHeight));
    }
    // ... 计算偏移
}
```

**优势**:
- 未使用的 Plot 不占用内存
- 使用 `sk_calloc_throw` 确保初始数据为零,满足 padding 使用场景

### 像素格式转换

`addSubImage` 在复制数据时处理 ARGB/BGRA 转换:

```cpp
constexpr bool kBGRAIsNative = kN32_SkColorType == kBGRA_8888_SkColorType;
if (4 == fBytesPerPixel && kBGRAIsNative) {
    for (int i = 0; i < height; ++i) {
        SkOpts::RGBA_to_BGRA((uint32_t*)dataPtr,
                             (const uint32_t*)imagePtr, width);
        dataPtr += plotRB;
        imagePtr += imageRB;
    }
}
```

使用 SkOpts 优化的 SIMD 转换函数提高性能。

### 脏矩形对齐

`prepareForUpload` 将脏区域对齐到 4 字节边界:

```cpp
unsigned int clearBits = 0x3 / fBytesPerPixel;
fDirtyRect.fLeft &= ~clearBits;
fDirtyRect.fRight += clearBits;
fDirtyRect.fRight &= ~clearBits;
```

**原因**: GPU 上传通常要求 4 字节对齐以获得最佳性能。

### Token 生命周期管理

Plot 使用两个 Token 追踪状态:
- `fLastUpload`: 最后一次上传的 Token,用于判断是否可以"搭便车"上传
- `fLastUse`: 最后一次使用的 Token,用于判断是否可以驱逐

```cpp
skgpu::Token lastUploadToken() const { return fLastUpload; }
skgpu::Token lastUseToken() const { return fLastUse; }
```

这种设计允许在 GPU 完成使用前复用 CPU 端的数据。

## 依赖关系

### 外部依赖
```cpp
#include "src/gpu/RectanizerSkyline.h"  // Skyline 空间分配算法
#include "src/gpu/Token.h"              // GPU 同步 Token
#include "src/core/SkIPoint16.h"        // 16 位点类型
#include "src/core/SkSwizzlePriv.h"     // 像素格式转换
```

### 被依赖模块
- `GrDrawOpAtlas`: 使用 `GrPlot` 和相关类型实现操作图集
- `GrDynamicAtlas`: 使用相同类型实现动态图集
- `GrAtlasManager`: 文字渲染的图集管理
- `GrSmallPathAtlasMgr`: 小路径缓存管理

## 设计模式与设计决策

### 1. 代数模式 (Generational Pattern)
使用递增的代数 ID 追踪 Plot 版本,避免指针失效问题:

```cpp
uint64_t fGenID;  // 每次驱逐后递增
```

客户端缓存 `GrPlotLocator` 并通过比较代数判断缓存是否有效。

### 2. 位域紧凑存储
`GrPlotLocator` 使用位域将三个字段压缩到 64 位:

```cpp
uint64_t fGenID:48;
uint64_t fPlotIndex:8;
uint64_t fPageIndex:8;
```

**权衡**: 限制了页数(4)和 Plot 数(32),但提供了高效的存储和传递。

### 3. UV 编码嵌入页索引
将页索引编码到 UV 坐标的高位:

```cpp
uint16_t page = fPlotLocator.pageIndex() << 13;
fUVs[0] = (fUVs[0] & 0x1FFF) | page;
```

**优势**: 单个 UV 坐标即包含位置和页信息,减少着色器 uniform 数量。

### 4. 批量更新优化
`GrBulkUsePlotUpdater` 使用位掩码避免重复更新:

```cpp
uint32_t fPlotAlreadyUpdated[4];  // 每页一个 32 位掩码
```

在文字渲染等场景中,同一 Plot 可能被多次引用,批量更新避免重复操作。

### 5. 观察者模式
`GrPlotEvictionCallback` 提供驱逐通知:

```cpp
virtual void evict(GrPlotLocator) = 0;
```

允许客户端(如字形缓存)在 Plot 驱逐时清理引用。

### 6. 引用计数管理
`GrPlot` 继承 `SkRefCnt`:

```cpp
class GrPlot : public SkRefCnt
```

通过 `sk_sp<GrPlot>` 智能指针管理生命周期,确保 Plot 在被引用时不会被释放。

## 性能考量

### 1. 内存效率
- **16 位坐标**: `GrIRect16` 使用 16 位整数,节省 50% 内存
- **延迟分配**: Plot 数据按需分配,未使用的 Plot 不占用内存
- **位域压缩**: `GrPlotLocator` 压缩到 8 字节

### 2. 上传优化
- **4 字节对齐**: 脏矩形对齐到 4 字节边界,利用 GPU 快速路径
- **增量上传**: 只上传脏区域,减少带宽消耗
- **批量标记**: 避免重复更新同一 Plot 的 Token

### 3. 空间分配效率
- **Skyline 算法**: `RectanizerSkyline` 提供较好的空间利用率
- **Plot 网格**: 将图集分割为固定大小的 Plot,简化管理

### 4. 缓存友好性
- **紧凑布局**: 相关字段紧密排列,减少缓存行浪费
- **行优先存储**: Plot 数据按行存储,匹配 GPU 上传模式

### 5. SIMD 优化
像素格式转换使用 SkOpts 优化路径:

```cpp
SkOpts::RGBA_to_BGRA((uint32_t*)dataPtr,
                     (const uint32_t*)imagePtr, width);
```

在支持的平台上使用 SSE/NEON 指令加速。

### 6. 驱逐策略支持
通过 Token 和 flush 计数追踪使用情况:

```cpp
int fFlushesSinceLastUse;
void incFlushesSinceLastUsed();
```

上层可以根据这些信息实现 LRU 等驱逐策略。

## 相关文件

### 核心实现
- `src/gpu/ganesh/GrDrawOpAtlas.h/cpp` - 操作图集实现
- `src/gpu/ganesh/GrDynamicAtlas.h/cpp` - 动态图集实现

### 依赖组件
- `src/gpu/RectanizerSkyline.h/cpp` - Skyline 空间分配算法
- `src/gpu/Token.h` - GPU 同步 Token 系统
- `src/core/SkIPoint16.h` - 16 位点类型

### 使用场景
- `src/gpu/ganesh/text/GrAtlasManager.h` - 字形图集管理
- `src/gpu/ganesh/text/GrTextBlob.cpp` - 文字块使用图集
- `src/gpu/ganesh/geometry/GrSmallPathAtlasMgr.h` - 小路径图集管理
- `src/gpu/ganesh/ops/AtlasTextOp.cpp` - 文字操作使用图集

### 测试文件
- `tests/DrawOpAtlasTest.cpp` - 图集功能测试
- `tests/RectanizerTest.cpp` - 空间分配测试
