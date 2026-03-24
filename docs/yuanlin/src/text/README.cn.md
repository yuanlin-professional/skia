# src/text - 文本渲染核心模块

## 概述

`src/text` 是 Skia 图形库中负责文本渲染基础设施的核心目录。该模块定义了从原始文本数据到字形序列（GlyphRun）的完整转换流水线，是 Skia 文本绘制系统的基石层。所有上层的 GPU 文本渲染、CPU 文本光栅化，以及远程字形缓存（Chrome Remote Glyph Cache）功能都依赖于本模块提供的核心抽象。

该模块的核心设计理念是将文本处理分为两个阶段：首先将用户提供的文本（UTF-8/UTF-16/GlyphID 等编码）通过 `GlyphRunBuilder` 转换为统一的 `GlyphRun` 表示；然后通过 `StrikeForGPU` 接口将字形信息传递给 GPU 或 CPU 后端进行实际的渲染。这种分层设计使得文本处理逻辑与具体的渲染后端完全解耦。

`SkStrikePromise` 是本模块中一个精妙的延迟求值机制。在多线程环境中创建字形数据时，它通过持有一个 `SkStrikeSpec` 或 `sk_sp<SkStrike>` 的变体（variant）来延迟 Strike 的实际查找操作，直到单线程的 GPU 环境中才真正解析。这种设计对于远程字形缓存场景尤为重要——序列化时使用描述符（SkDescriptor），反序列化时通过描述符查找对应的 Strike。

本模块所处的命名空间为 `sktext`，其子目录 `gpu` 则包含所有 GPU 文本渲染的具体实现。`src/text` 自身保持了高度的精简性，仅包含跨后端共享的核心抽象。

## 架构图

```
+-------------------------------------------------------------------+
|                        用户 API 层                                 |
|  SkCanvas::drawText()  /  SkCanvas::drawTextBlob()                |
+-------------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------------+
|                    GlyphRunBuilder                                 |
|  textToGlyphRunList()  |  blobToGlyphRunList()                    |
|  convertRSXForm()      |  textToGlyphIDs()                        |
+-------------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------------+
|                GlyphRun / GlyphRunList                             |
|  SkGlyphID[] + SkPoint[]  +  SkFont                               |
|  原始文本 + 簇映射 + RSXForm 缩放旋转                              |
+-------------------------------------------------------------------+
           |                              |
           v                              v
+---------------------+    +-------------------------------+
| CPU 渲染路径        |    | GPU 渲染路径                   |
| SkStrike            |    | StrikeForGPU                  |
| (src/core)          |    | SkStrikePromise               |
+---------------------+    | StrikeMutationMonitor         |
                           +-------------------------------+
                                          |
                                          v
                           +-------------------------------+
                           | src/text/gpu/                  |
                           | SubRunContainer               |
                           | SlugImpl / TextBlob            |
                           +-------------------------------+
```

## 目录结构

```
src/text/
|-- BUILD.bazel              # Bazel 构建配置
|-- GlyphRun.h               # GlyphRun、GlyphRunList、GlyphRunBuilder 类声明
|-- GlyphRun.cpp             # GlyphRun 相关类的实现
|-- StrikeForGPU.h           # GPU Strike 接口、SkStrikePromise、IDOrPath 等
|-- StrikeForGPU.cpp         # SkStrikePromise 和 StrikeMutationMonitor 的实现
|-- SlugFromBuffer.cpp       # Slug 的反序列化支持（CPU/GPU 共用）
|-- gpu/                     # GPU 文本渲染子模块（见独立文档）
```

## 关键类与函数

### GlyphRun（字形运行）
```cpp
class GlyphRun {
    const SkZip<const SkGlyphID, const SkPoint> fSource;  // 字形ID与位置的配对
    const SkSpan<const char> fText;                        // 原始UTF-8文本
    const SkSpan<const uint32_t> fClusters;                // 字符到字形的簇映射
    const SkSpan<const SkVector> fScaledRotations;         // RSXForm旋转缩放信息
    SkFont fFont;                                          // 字体配置
};
```
`GlyphRun` 是文本渲染的最小单元，代表一段使用相同字体的字形序列。每个 `GlyphRun` 包含字形 ID 数组和对应的位置数组，以 `SkZip` 的形式成对存储。可选的 `fText` 和 `fClusters` 字段保留原始文本信息，用于可访问性和文本选择等高级功能。

### GlyphRunList（字形运行列表）
```cpp
class GlyphRunList {
    SkSpan<const GlyphRun> fGlyphRuns;       // 运行数组
    const SkTextBlob* fOriginalTextBlob;      // 原始TextBlob引用
    const SkRect fSourceBounds;               // 源坐标空间边界
    const SkPoint fOrigin;                    // 绘制原点
    GlyphRunBuilder* const fBuilder;          // 创建者引用
};
```
`GlyphRunList` 是从 `SkTextBlob` 或原始文本构建而来的完整字形信息集合。它持有对原始 `SkTextBlob` 的引用以支持缓存回调机制，并提供 `anyRunsLCD()` 等查询方法用于确定渲染策略。

### GlyphRunBuilder（字形运行构建器）
```cpp
class GlyphRunBuilder {
    // 核心方法
    const GlyphRunList& textToGlyphRunList(...);   // 从原始文本构建
    const GlyphRunList& blobToGlyphRunList(...);   // 从TextBlob构建
    GlyphRunList makeGlyphRunList(...);             // 从单个GlyphRun构建
    std::tuple<...> convertRSXForm(...);            // RSXForm转换
};
```
`GlyphRunBuilder` 是本模块的核心工厂类。它负责处理四种不同的文本布局方式：默认布局（自动计算位置）、水平布局（仅指定X坐标）、完全定位布局（指定X/Y坐标）和 RSXForm 布局（旋转缩放变换）。内部使用 `AutoTMalloc` 管理位置缓冲区以避免频繁分配。

### SkStrikePromise（Strike 承诺）
```cpp
class SkStrikePromise {
    std::variant<sk_sp<SkStrike>, std::unique_ptr<SkStrikeSpec>> fStrikeOrSpec;
    SkStrike* strike();                    // 延迟获取Strike
    void flatten(SkWriteBuffer&) const;    // 序列化
    static std::optional<SkStrikePromise> MakeFromBuffer(...);  // 反序列化
};
```
这是一个延迟求值的智能包装器。在普通操作中直接包装 `SkStrike`；在远程字形缓存场景下，序列化为 `SkDescriptor`，反序列化时通过描述符查找 Strike。使用 `std::variant` 实现两种状态的无开销切换。

### StrikeForGPU（GPU Strike 接口）
```cpp
class StrikeForGPU : public SkRefCnt {
    virtual SkGlyphDigest digestFor(skglyph::ActionType, SkPackedGlyphID) = 0;
    virtual bool prepareForImage(SkGlyph*) = 0;
    virtual bool prepareForPath(SkGlyph*) = 0;
    virtual bool prepareForDrawable(SkGlyph*) = 0;
};
```
定义了 GPU 后端访问字形数据的抽象接口，支持三种字形绘制方式：图像（位图/SDF）、路径和可绘制对象（Drawable）。

### StrikeMutationMonitor（Strike 变更监视器）
RAII 风格的锁管理器，在构造时调用 `StrikeForGPU::lock()`，析构时调用 `unlock()`，确保在多线程环境中对 Strike 的安全访问。

### IDOrPath / IDOrDrawable（联合体）
```cpp
union IDOrPath {
    SkGlyphID fGlyphID;
    SkPath fPath;
};
union IDOrDrawable {
    SkGlyphID fGlyphID;
    SkDrawable* fDrawable;
};
```
这些联合体用于在字形处理过程中就地转换数据类型——从初始的 `SkGlyphID` 转换为路径或可绘制对象，避免额外的内存分配。

## 依赖关系

### 上游依赖（本模块依赖的模块）
- `include/core/` - SkFont、SkTextBlob、SkPoint、SkRect 等核心类型
- `src/core/SkGlyph.h` - 字形数据结构（SkGlyph、SkGlyphDigest、SkPackedGlyphID）
- `src/core/SkStrike.h` - 字形缓存 Strike 实现
- `src/core/SkStrikeSpec.h` - Strike 规格说明
- `src/core/SkStrikeCache.h` - 全局 Strike 缓存
- `src/core/SkDescriptor.h` - 字形缓存键描述符
- `src/core/SkTextBlobPriv.h` - TextBlob 内部遍历接口
- `src/base/SkZip.h` - 多数组并行遍历工具

### 下游依赖（依赖本模块的模块）
- `src/text/gpu/` - GPU 文本渲染（SubRunContainer、SlugImpl、TextBlob）
- `src/gpu/ganesh/` - Ganesh GPU 后端
- `src/gpu/graphite/` - Graphite GPU 后端
- `include/private/chromium/Slug.h` - Chromium Slug 接口

## 设计模式分析

### 建造者模式（Builder Pattern）
`GlyphRunBuilder` 是典型的建造者模式实现。它通过 `prepareBuffers()` 预分配缓冲区，通过 `makeGlyphRun()` 逐步构建单个运行，最终通过 `setGlyphRunList()` 组装完整的结果。这种设计避免了中间对象的反复创建和销毁。

### 承诺模式（Promise Pattern）
`SkStrikePromise` 实现了一种变体的承诺模式（也称为延迟求值/Lazy Evaluation）。它通过 `std::variant` 持有两种可能的状态（已解析的 Strike 或待解析的 StrikeSpec），在调用 `strike()` 时才真正执行昂贵的 Strike 查找操作。

### RAII 模式
`StrikeMutationMonitor` 使用 RAII（资源获取即初始化）模式管理 Strike 的锁定状态，保证异常安全性。

### 策略模式（Strategy Pattern）
`StrikeForGPUCacheInterface` 定义了可替换的 Strike 缓存策略接口，允许不同的后端（Ganesh、Graphite）提供各自的 Strike 缓存实现。

## 数据流

```
1. 文本输入
   用户调用 SkCanvas::drawText/drawTextBlob
        |
        v
2. 编码转换
   GlyphRunBuilder::textToGlyphIDs()
   将 UTF-8/UTF-16/UTF-32 编码转换为 SkGlyphID 数组
        |
        v
3. 位置计算
   draw_text_positions() / SkTextBlobRunIterator
   根据字形度量信息计算每个字形的位置
   支持四种定位模式: Default/Horizontal/Full/RSXForm
        |
        v
4. 边界计算
   glyphrun_source_bounds()
   使用字体边界或精确字形边界计算整体包围盒
        |
        v
5. GlyphRunList 组装
   setGlyphRunList() 将所有 GlyphRun 打包为 GlyphRunList
        |
        v
6. 分发到渲染后端
   CPU 路径: 直接使用 SkStrike 光栅化
   GPU 路径: 通过 StrikeForGPU 创建 SubRun，
            使用 SkStrikePromise 延迟 Strike 解析
```

## 相关文档与参考

- `src/text/gpu/README.md` - GPU 文本渲染子模块文档
- `src/core/SkStrike.h` - Strike（字形缓存条目）的核心实现
- `src/core/SkStrikeSpec.h` - Strike 规格说明，控制字形光栅化参数
- `include/core/SkTextBlob.h` - 公共 API 中的 SkTextBlob 定义
- `include/core/SkFont.h` - 字体配置相关的公共 API
- OpenType 规范 - 字形 ID 和文本编码的标准定义
- Skia 官方文档中的文本渲染架构说明
- `src/core/SkTextBlobPriv.h` - TextBlob 内部的 Run 遍历迭代器
