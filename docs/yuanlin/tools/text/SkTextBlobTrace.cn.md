# SkTextBlobTrace

> 源文件：tools/text/SkTextBlobTrace.h, tools/text/SkTextBlobTrace.cpp

## 概述

SkTextBlobTrace 是 Skia 文本渲染调试工具，用于捕获、序列化和重放文本 blob 绘制操作。该模块可以记录应用程序中的所有文本渲染调用，将其保存为追踪文件，然后在其他环境中重放，非常适用于文本渲染问题的复现和调试。

主要功能：
- 捕获 GlyphRunList 到二进制追踪文件
- 序列化字体和文本 blob 数据
- 从追踪文件重建文本 blob
- 转储追踪内容用于分析
- 支持跨平台重放（包含字体数据）

该工具对于诊断平台特定的文本渲染问题、性能分析和回归测试非常有价值。

## 架构位置

- **角色**：调试和测试工具
- **使用者**：DM 测试工具、文本渲染测试
- **捕获对象**：sktext::GlyphRunList、SkTextBlob、SkPaint
- **序列化目标**：文件流（.trace 文件）

## 主要类与结构体

### Record

```cpp
struct Record {
    uint32_t origUniqueID;      // 原始 blob 唯一 ID
    SkPaint paint;              // 绘制参数
    SkPoint offset;             // 绘制偏移
    sk_sp<SkTextBlob> blob;     // 文本 blob
};
```

表示单次文本绘制调用的完整信息。

### Capture

```cpp
class Capture {
public:
    Capture();
    ~Capture();
    void capture(const sktext::GlyphRunList&, const SkPaint&);
    void dump(SkWStream* dst = nullptr) const;

private:
    size_t fBlobCount;
    sk_sp<SkRefCntSet> fTypefaceSet;
    SkBinaryWriteBuffer fWriteBuffer;
};
```

捕获会话管理器，记录所有文本绘制到内存缓冲区。

## 公共 API 函数

### CreateBlobTrace

```cpp
std::vector<Record> CreateBlobTrace(SkStream* stream,
                                    sk_sp<SkFontMgr> lastResortMgr);
```

从追踪文件创建 Record 向量。

**追踪文件格式**：
1. 字体数量（uint32）
2. 序列化的字体数据（每个字体）
3. 数据大小（uint32）
4. Record 数据（重复）

**参数**：
- `stream` - 追踪文件流
- `lastResortMgr` - 后备字体管理器（当字体加载失败时）

**返回**：Record 向量，失败时返回空向量

**实现流程**：
```cpp
1. 读取字体数量
2. 反序列化所有字体到数组
3. 读取数据大小并加载到 SkData
4. 创建 SkReadBuffer 并设置字体数组
5. 循环读取 Record：
   - origUniqueID
   - SkPaint
   - SkPoint
   - SkTextBlob（通过 SkTextBlobPriv::MakeFromBuffer）
```

### DumpTrace

```cpp
void DumpTrace(const std::vector<Record>& trace);
```

将追踪内容转储到调试输出（SkDebugf）。

**输出格式**：
```
Blob <ID> ( <x> <y> ) <weirdPaint>
  Run <N>
    Font <typeface_id> <size> <scaleX> <skewX> <flags> <edging> <hinting>
    <glyph_ids...>
```

**用途**：
- 分析追踪内容
- 验证捕获正确性
- 调试字体和字形问题

### Capture::capture

```cpp
void capture(const sktext::GlyphRunList& glyphRunList, const SkPaint& paint);
```

捕获单次文本绘制调用。

**捕获内容**：
- blob 唯一 ID
- SkPaint（颜色、样式、效果等）
- 绘制原点
- SkTextBlob（完整序列化）

**实现**：
```cpp
const SkTextBlob* blob = glyphRunList.blob();
if (blob != nullptr) {
    fWriteBuffer.writeUInt(blob->uniqueID());
    fWriteBuffer.writePaint(paint);
    fWriteBuffer.writePoint(glyphRunList.origin());
    SkTextBlobPriv::Flatten(*blob, fWriteBuffer);
    fBlobCount++;
}
```

### Capture::dump

```cpp
void dump(SkWStream* dst = nullptr) const;
```

将捕获的数据写入文件。

**参数**：
- `dst` - 输出流，`nullptr` 时自动生成文件名

**文件命名**：
```cpp
diff-canvas-<hash>-<count>.trace
```

其中 hash 基于对象地址，count 是 blob 数量。

**写入顺序**：
1. 字体数量
2. 所有字体的序列化数据
3. 缓冲区大小
4. 缓冲区内容

## 内部实现细节

### 字体序列化

Capture 使用 `SkRefCntSet` 跟踪所有使用的字体：

```cpp
fWriteBuffer.setTypefaceRecorder(fTypefaceSet);
```

写入时：
```cpp
int count = fTypefaceSet->count();
dst->write32(count);
SkPtrSet::Iter iter(*fTypefaceSet);
while (void* ptr = iter.next()) {
    ((const SkTypeface*)ptr)->serialize(dst, SkTypeface::SerializeBehavior::kDoIncludeData);
}
```

包含完整字体数据（`kDoIncludeData`）确保跨平台可重放。

### 二进制写入缓冲区

使用 `SkBinaryWriteBuffer` 序列化复杂对象：
- 自动处理引用计数
- 记录字体引用
- 支持嵌套对象

### 文本 Blob 序列化

通过 `SkTextBlobPriv::Flatten` 和 `MakeFromBuffer`：
```cpp
// 写入
SkTextBlobPriv::Flatten(*blob, fWriteBuffer);

// 读取
record.blob = SkTextBlobPriv::MakeFromBuffer(readBuffer);
```

这些私有 API 访问内部序列化格式。

### "Weird Paint" 检测

```cpp
bool weirdPaint = p.getStyle() != SkPaint::kFill_Style
    || p.getMaskFilter() != nullptr
    || p.getPathEffect() != nullptr;
```

标记使用了非标准绘制参数的 blob，便于识别复杂情况。

### 字形 ID 转储

```cpp
for (uint32_t i = 0; i < glyphCount; i++) {
    SkDebugf("%02X ", glyphs[i]);
}
```

以十六进制显示字形 ID，便于分析。

## 依赖关系

### Skia 核心
- `include/core/SkTextBlob.h` - 文本 blob
- `include/core/SkFont.h` - 字体
- `include/core/SkTypeface.h` - 字体面
- `include/core/SkFontMgr.h` - 字体管理器
- `src/core/SkWriteBuffer.h` - 序列化
- `src/core/SkReadBuffer.h` - 反序列化

### 文本系统
- `src/text/GlyphRun.h` - 字形运行列表
- `src/core/SkTextBlobPriv.h` - 文本 blob 私有 API

### 工具
- `src/core/SkPtrRecorder.h` - 指针记录器
- `src/core/SkChecksum.h` - 校验和（用于文件命名）

## 设计模式与设计决策

### 记录-重放模式
捕获实际应用行为并在测试环境中重放。

### 序列化策略
包含完整字体数据而非字体名称，确保跨平台兼容性。

### 二进制格式
使用二进制而非文本格式：
- 更紧凑
- 精确保留浮点数
- 更快的读写

### 自动文件命名
生成唯一文件名避免覆盖：
```cpp
SkString f = SkStringPrintf("diff-canvas-%08x-%04zu.trace", id, fBlobCount);
```

### 最后保障字体管理器
`lastResortMgr` 参数允许在字体缺失时使用替代字体，提高鲁棒性。

## 性能考量

- 捕获有开销（序列化）但对调试必要
- 使用二进制格式减少文件大小
- 字体去重（通过 SkRefCntSet）
- 可选的捕获（通过条件编译或运行时标志）

## 相关文件

### 文本相关
- `src/text/GlyphRun.h` - 字形运行
- `include/core/SkTextBlob.h` - 文本 blob
- `src/core/SkTextBlobPriv.h` - 文本 blob 私有 API

### 序列化
- `src/core/SkWriteBuffer.h` - 写入缓冲
- `src/core/SkReadBuffer.h` - 读取缓冲
- `src/core/SkPtrRecorder.h` - 指针记录

### 字体
- `include/core/SkTypeface.h` - 字体面
- `include/core/SkFontMgr.h` - 字体管理
- `src/core/SkFontPriv.h` - 字体私有 API
