# Skia 文本工具

## 概述

`tools/text` 提供了 Skia 文本渲染相关的工具和调试功能。该模块主要包含两部分：文本 Blob 追踪系统（`SkTextBlobTrace`）和 GPU 文本 Blob 调试工具（`TextBlobTools`）。这些工具用于捕获、序列化、回放和分析文本渲染操作，帮助开发者调试文本渲染管线中的问题。

## 目录结构

```
tools/text/
├── SkTextBlobTrace.h        # 文本 Blob 追踪系统声明
├── SkTextBlobTrace.cpp      # 文本 Blob 追踪系统实现
└── gpu/
    ├── TextBlobTools.h      # GPU 文本 Blob 调试工具声明
    └── TextBlobTools.cpp    # GPU 文本 Blob 调试工具实现
```

## 核心组件

### SkTextBlobTrace

文本 Blob 追踪系统，用于捕获和回放文本渲染操作序列：

#### Record 数据结构

```cpp
struct Record {
    uint32_t origUniqueID;    // 原始唯一标识符
    SkPaint paint;            // 绘制时使用的画笔
    SkPoint offset;           // 文本绘制偏移量
    sk_sp<SkTextBlob> blob;   // 文本 Blob 对象
};
```

#### 主要功能

| 函数 | 说明 |
|------|------|
| `CreateBlobTrace(stream, fontMgr)` | 从流中反序列化文本 Blob 追踪记录 |
| `DumpTrace(records)` | 将追踪记录转储到调试输出 |

#### Capture 类

`SkTextBlobTrace::Capture` 类用于实时捕获文本渲染操作：

```cpp
class Capture {
public:
    Capture();
    ~Capture();
    void capture(const sktext::GlyphRunList&, const SkPaint&);
    void dump(SkWStream* dst = nullptr) const;
};
```

- **capture()**: 捕获一次字形运行列表（GlyphRunList）的绘制操作
- **dump()**: 将捕获的数据序列化输出；若 `dst` 为 nullptr，则写入文件
- 内部使用 `SkBinaryWriteBuffer` 进行高效序列化
- 通过 `SkRefCntSet` 管理 Typeface 引用计数集合

### TextBlobTools (GPU)

位于 `tools/text/gpu/` 子目录，提供 GPU 文本 Blob 的内部调试访问：

```cpp
namespace sktext::gpu {
class TextBlobTools final {
public:
    static const AtlasSubRun* FirstSubRun(const TextBlob*);
};
}
```

- **FirstSubRun()**: 获取文本 Blob 的第一个 Atlas 子运行（AtlasSubRun）
- 这是一个友元工具类，可访问 `TextBlob` 的私有成员
- 主要用于测试和调试 GPU 文本渲染的纹理图集（Atlas）管理

## 工作流程

### 文本追踪的捕获和回放

```
1. 创建 Capture 实例
2. 在文本渲染过程中调用 capture() 记录每次 GlyphRunList 绘制
3. 调用 dump() 序列化到文件或流
4. 使用 CreateBlobTrace() 从文件反序列化记录
5. 使用 DumpTrace() 查看追踪内容
6. 可在不同环境中回放追踪的文本渲染操作
```

### 序列化格式

追踪数据使用 Skia 的二进制写缓冲区（`SkBinaryWriteBuffer`）格式：

- Typeface 集合通过 `SkRefCntSet` 去重存储
- 每条记录包含 Paint、偏移量和序列化的 TextBlob
- 反序列化时需要提供 `SkFontMgr` 用于恢复 Typeface

## 使用场景

1. **文本渲染调试**: 捕获有问题的文本渲染操作，在不同设备上回放分析
2. **回归测试**: 保存文本追踪数据作为参考，检测渲染变更
3. **GPU Atlas 分析**: 使用 TextBlobTools 检查 GPU 文本纹理图集的分配状态
4. **性能分析**: 追踪文本渲染的频率和复杂度

## 与其他模块的关系

- **src/core/SkTextBlob.h**: SkTextBlob 的核心实现
- **src/text/gpu/**: GPU 文本渲染管线（TextBlob、AtlasSubRun）
- **tools/debugger/**: 调试器工具可利用文本追踪分析 SKP 中的文本绘制
- **tools/fonts/**: 提供测试用字体管理器，用于追踪回放时的字体恢复
