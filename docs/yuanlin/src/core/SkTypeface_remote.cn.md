# SkTypeface_remote

> 源文件: src/core/SkTypeface_remote.h, src/core/SkTypeface_remote.cpp

## 概述

`SkTypeface_remote` 模块实现了 Skia 的远程字体系统,专为 Chromium 的 OOP-D (Out-of-Process Display Compositing) 架构设计。该模块包含 `SkTypefaceProxy` 和 `SkScalerContextProxy` 两个核心类,允许渲染进程使用 GPU 进程中的字体资源,而无需复制完整的字体数据。这是一种跨进程字体共享机制,通过序列化字体元数据和按需请求字形数据实现。

## 架构位置

远程字体系统位于 Skia 核心层,是字体系统的特殊实现分支:

- **上游**: Chromium 的 `SkStrikeClient`/`SkStrikeServer` 架构
- **同级**: 标准 `SkTypeface` 实现(FreeType、CoreText、DirectWrite)
- **下游**: `SkScalerContext`、字形缓存系统
- **用途**: 在 Chromium 的渲染进程中提供字体代理

## 主要类与结构体

### SkTypefaceProxy

**继承关系**:
```
SkWeakRefCnt
    └── SkTypeface
            └── SkTypefaceProxy
```

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fTypefaceID` | `SkTypefaceID` | 服务器端字体的 ID |
| `fGlyphCount` | `int` | 字形数量 |
| `fIsLogging` | `bool` | 是否记录缓存未命中 |
| `fGlyphMaskNeedsCurrentColor` | `bool` | 是否需要前景色(COLR 字体) |
| `fDiscardableManager` | `sk_sp<SkStrikeClient::DiscardableHandleManager>` | 缓存管理器 |

### SkScalerContextProxy

**继承关系**:
```
SkRefCnt
    └── SkScalerContext
            └── SkScalerContextProxy
```

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fDiscardableManager` | `sk_sp<SkStrikeClient::DiscardableHandleManager>` | 缓存管理器 |

### SkTypefaceProxyPrototype

序列化格式类,用于在进程间传输字体元数据。

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fServerTypefaceID` | `SkTypefaceID` | 服务器端字体 ID |
| `fGlyphCount` | `int` | 字形总数 |
| `fStyleValue` | `int32_t` | 字体样式值 |
| `fIsFixedPitch` | `bool` | 是否等宽字体 |
| `fGlyphMaskNeedsCurrentColor` | `bool` | 颜色字体标志 |

## 公共 API 函数

### SkTypefaceProxy

| 函数签名 | 功能描述 |
|---------|---------|
| `SkTypefaceProxy(const SkTypefaceProxyPrototype&, ...)` | 从原型构造代理字体 |
| `SkTypefaceID remoteTypefaceID()` | 获取远程字体 ID |
| `int glyphCount()` | 获取字形数量 |
| `bool isLogging()` | 是否启用调试日志 |

### SkScalerContextProxy

| 函数签名 | 功能描述 |
|---------|---------|
| `SkScalerContextProxy(SkTypeface&, ...)` | 构造代理缩放上下文 |
| `GlyphMetrics generateMetrics(const SkGlyph&, SkArenaAlloc*)` | 生成字形度量(触发缓存未命中) |
| `void generateImage(const SkGlyph&, void*)` | 生成字形图像(触发缓存未命中) |
| `std::optional<GeneratedPath> generatePath(const SkGlyph&)` | 生成字形路径(触发缓存未命中) |
| `sk_sp<SkDrawable> generateDrawable(const SkGlyph&)` | 生成可绘制对象(触发缓存未命中) |

### SkTypefaceProxyPrototype

| 函数签名 | 功能描述 |
|---------|---------|
| `static std::optional<...> MakeFromBuffer(SkReadBuffer&)` | 从缓冲区反序列化 |
| `explicit SkTypefaceProxyPrototype(const SkTypeface&)` | 从字体创建原型 |
| `void flatten(SkWriteBuffer&)` | 序列化到缓冲区 |
| `SkTypefaceID serverTypefaceID()` | 获取服务器端 ID |

## 内部实现细节

### 代理机制

`SkTypefaceProxy` 是一个"空壳"字体对象,它不包含实际的字体数据:

```cpp
std::unique_ptr<SkStreamAsset> onOpenStream(int* ttcIndex) const override {
    SK_ABORT("Should never be called.");
}
```

大多数方法直接调用 `SK_ABORT`,因为这些操作在客户端进程中不应被执行。

### 缓存未命中处理

当需要字形数据时,代理对象报告缓存未命中:

```cpp
SkScalerContext::GlyphMetrics SkScalerContextProxy::generateMetrics(
    const SkGlyph& glyph, SkArenaAlloc*) {

    if (this->getProxyTypeface()->isLogging()) {
        SkDebugf("GlyphCacheMiss generateMetrics looking for glyph: %x\n",
                 glyph.getPackedID().value());
    }

    fDiscardableManager->notifyCacheMiss(
        SkStrikeClient::CacheMissType::kGlyphMetrics, fRec.fTextSize);

    return {glyph.maskFormat()};
}
```

**工作流程**:
1. 客户端请求字形数据
2. 代理对象记录缓存未命中
3. 通知 `DiscardableHandleManager`
4. 管理器向服务器请求数据
5. 服务器推送数据到客户端缓存
6. 后续请求直接从缓存获取

### 序列化格式

`SkTypefaceProxyPrototype` 定义了字体元数据的序列化格式:

```cpp
void SkTypefaceProxyPrototype::flatten(SkWriteBuffer& buffer) const {
    buffer.writeUInt(fServerTypefaceID);
    buffer.writeInt(fGlyphCount);
    buffer.write32(fStyleValue);
    buffer.writeBool(fIsFixedPitch);
    buffer.writeBool(fGlyphMaskNeedsCurrentColor);
}
```

**序列化数据**:
- 服务器端字体 ID(4 字节)
- 字形数量(4 字节)
- 样式值(4 字节)
- 固定宽度标志(1 字节)
- 颜色标志(1 字节)

总计约 14 字节,比完整字体文件小得多。

### 颜色字体支持

`fGlyphMaskNeedsCurrentColor` 标志用于 COLRv0/v1 字体:

```cpp
bool onGlyphMaskNeedsCurrentColor() const override {
    return fGlyphMaskNeedsCurrentColor;
}
```

这影响字体缓存的分类,因为使用不同前景色的字形需要分别缓存。

### 过滤器旁路

```cpp
void onFilterRec(SkScalerContextRec* rec) const override {
    // The rec filtering is already applied by the server when generating
    // the glyphs.
}
```

字形处理参数(提示、LCD 过滤等)在服务器端已应用,客户端不需要重复处理。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `SkTypeface` | 基类,提供字体接口 |
| `SkScalerContext` | 字形生成上下文基类 |
| `SkStrikeClient` | Chrome 特定的远程字形缓存客户端 |
| `SkReadBuffer`/`SkWriteBuffer` | 序列化支持 |
| `SkTraceEvent` | 性能追踪 |

### 被依赖的模块

| 模块 | 关系 |
|-----|------|
| Chromium 渲染进程 | 使用代理字体进行文本渲染 |
| `SkStrikeClient` | 创建和管理代理字体 |
| 字形缓存系统 | 存储从服务器获取的字形数据 |

## 设计模式与设计决策

### 设计模式

1. **代理模式**: `SkTypefaceProxy` 代理服务器端的真实字体
2. **原型模式**: `SkTypefaceProxyPrototype` 用于创建代理对象
3. **策略模式**: 通过回调通知缓存未命中

### 设计决策

**为什么使用代理而不是复制字体?**
- 字体文件可能很大(数 MB)
- 跨进程传输成本高
- 内存占用翻倍
- 仅传输元数据和按需字形数据

**为什么大多数方法都调用 `SK_ABORT`?**
- 这些操作需要完整字体数据
- 在客户端调用表示架构错误
- 帮助开发者快速发现问题

**缓存未命中通知机制**
- 异步请求,不阻塞渲染
- 首次绘制可能不完整,后续帧正常
- 平衡性能和正确性

**为什么需要 `isLogging` 标志?**
- 调试远程字体系统时启用
- 生产环境关闭以提高性能
- 帮助诊断缓存未命中问题

**序列化最小化原则**
- 仅传输必要的元数据
- 样式信息打包为 32 位整数
- 布尔值使用单字节

## 性能考量

### 优化策略

1. **按需传输**: 只传输使用的字形,不传输整个字体
2. **元数据缓存**: 在客户端缓存字形度量和图像
3. **批量请求**: 通过 `DiscardableHandleManager` 批量处理缓存未命中
4. **追踪支持**: 使用 `TRACE_EVENT1` 监控性能

### 性能权衡

**优势**:
- 减少进程间内存占用
- 加快启动速度(无需传输完整字体)
- 支持字体动态加载

**代价**:
- 首次渲染可能延迟(等待字形数据)
- 增加进程间通信开销
- 需要复杂的缓存同步逻辑

### 追踪示例

```cpp
TRACE_EVENT1("skia", "generateMetrics",
             "rec", TRACE_STR_COPY(this->getRec().dump().c_str()));
```

允许在 Chrome 追踪工具中分析字形生成性能。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `include/core/SkTypeface.h` | 基类定义 |
| `src/core/SkScalerContext.h` | 缩放上下文基类 |
| `include/private/chromium/SkChromeRemoteGlyphCache.h` | Chrome 远程字形缓存接口 |
| `src/core/SkGlyph.h` | 字形数据结构 |
| `src/core/SkReadBuffer.h` | 反序列化 |
| `src/core/SkWriteBuffer.h` | 序列化 |
| `src/core/SkTraceEvent.h` | 性能追踪 |
