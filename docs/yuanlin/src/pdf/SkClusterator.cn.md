# SkClusterator

> 源文件
> - src/pdf/SkClusterator.h
> - src/pdf/SkClusterator.cpp

## 概述

`SkClusterator` 是 Skia PDF 模块中用于迭代字形簇（glyph clusters）的工具类。它处理 HarfBuzz 等文本整形引擎返回的字形到字符的 m-to-n 映射关系，将文本字符与相应的字形分组为簇，并支持从左到右（LTR）和从右到左（RTL）两种文本方向。

在复杂的文本渲染中，一个字符可能对应多个字形（如连字），或多个字符对应一个字形（如组合字符）。`SkClusterator` 通过迭代器模式简化了这种复杂映射关系的处理，为 PDF 文档生成提供正确的文本到字形映射信息。

## 架构位置

`SkClusterator` 位于 PDF 模块的文本处理层：

```
src/pdf/
├── SkPDFDevice.cpp           // PDF 设备，使用 SkClusterator 处理文本
├── SkPDFFont.cpp             // PDF 字体，需要字形簇信息
├── SkClusterator.h/cpp       // 字形簇迭代器（当前模块）
└── SkPDFMakeToUnicodeCmap.cpp // Unicode 映射表生成
```

它连接了 Skia 的文本整形系统和 PDF 输出系统：
- 输入：`sktext::GlyphRun`（来自文本整形）
- 输出：字形簇信息（用于 PDF 内容生成）

## 主要类与结构体

### SkClusterator

**构造函数:**
```cpp
explicit SkClusterator(const sktext::GlyphRun& run);
```
- 从 `GlyphRun` 初始化迭代器
- 检测文本方向（LTR 或 RTL）
- 验证数据一致性

**公共方法:**
```cpp
uint32_t glyphCount() const { return fGlyphCount; }
bool reversedChars() const { return fReversedChars; }
Cluster next();
```

**成员变量:**
```cpp
uint32_t const * const fClusters;      // 字形到字符的映射数组
char const * const fUtf8Text;          // UTF-8 文本数据
uint32_t const fGlyphCount;            // 字形总数
uint32_t const fTextByteLength;        // 文本字节长度
bool const fReversedChars;             // 是否为 RTL 文本
uint32_t fCurrentGlyphIndex = 0;       // 当前迭代位置
```

### Cluster 结构体

```cpp
struct Cluster {
    const char* fUtf8Text;           // 指向簇对应的 UTF-8 文本
    uint32_t fTextByteLength;        // 文本字节长度
    uint32_t fGlyphIndex;            // 簇中第一个字形的索引
    uint32_t fGlyphCount;            // 簇中字形的数量

    explicit operator bool() const { return fGlyphCount != 0; }
    bool operator==(const Cluster& o) const;
};
```

表示一个字形簇，包含：
- 对应的文本片段
- 字形在字形数组中的位置和数量

## 公共 API 函数

### 构造函数

```cpp
explicit SkClusterator(const sktext::GlyphRun& run);
```

**功能：**
- 从 `GlyphRun` 提取字形、文本和映射数据
- 调用 `is_reversed()` 检测文本方向
- 验证数据完整性

**前置条件：**
- 如果有 clusters 数据，必须有对应的文本数据
- 没有 clusters 数据时，文本数据也应为空

### next()

```cpp
Cluster next();
```

**功能：**
- 返回下一个字形簇
- 自动推进迭代位置
- 到达末尾返回空簇（`fGlyphCount == 0`）

**返回值：**
- 有效簇：包含文本和字形信息
- 无效簇：字形计数为 0
- 无映射数据时：返回单个字形的簇，文本指针为 nullptr

### 访问器方法

```cpp
uint32_t glyphCount() const;
```
- 返回总字形数量

```cpp
bool reversedChars() const;
```
- 返回文本是否为 RTL（从右到左）方向

## 内部实现细节

### RTL 文本检测

```cpp
static bool is_reversed(const uint32_t* clusters, uint32_t count) {
    if (count < 2 || clusters[0] == 0 || clusters[count - 1] != 0) {
        return false;
    }
    for (uint32_t i = 0; i + 1 < count; ++i) {
        if (clusters[i + 1] > clusters[i]) {
            return false;
        }
    }
    return true;
}
```

**检测逻辑：**
1. 至少需要 2 个字形
2. 第一个字形不能映射到字符索引 0
3. 最后一个字形必须映射到字符索引 0
4. 字符索引必须单调递减

这对应 PDF 中 "ReversedChars" 标志的语义。

### next() 实现

**第一步：边界检查**
```cpp
if (fCurrentGlyphIndex >= fGlyphCount) {
    return Cluster{nullptr, 0, 0, 0};  // 返回空簇
}
```

**第二步：处理无映射数据情况**
```cpp
if (!fClusters || !fUtf8Text) {
    return Cluster{nullptr, 0, fCurrentGlyphIndex++, 1};
}
```
每个字形独立成簇，没有文本关联。

**第三步：查找簇边界**
```cpp
uint32_t clusterGlyphIndex = fCurrentGlyphIndex;
uint32_t cluster = fClusters[clusterGlyphIndex];
do {
    ++fCurrentGlyphIndex;
} while (fCurrentGlyphIndex < fGlyphCount &&
         cluster == fClusters[fCurrentGlyphIndex]);
```
所有映射到相同字符索引的连续字形属于同一个簇。

**第四步：确定文本范围**
```cpp
uint32_t clusterEnd = fTextByteLength;
for (unsigned i = 0; i < fGlyphCount; ++i) {
   uint32_t c = fClusters[i];
   if (c > cluster && c < clusterEnd) {
       clusterEnd = c;
   }
}
uint32_t clusterLen = clusterEnd - cluster;
```
遍历所有字形，找到紧邻的下一个字符索引作为簇的文本结束位置。

### 数据结构示例

**LTR 文本示例（"hello"）：**
```
字形索引: 0    1    2    3    4
字符索引: 0    1    2    3    4
簇1: 字形[0], 文本[0..1) = "h"
簇2: 字形[1], 文本[1..2) = "e"
...
```

**RTL 文本示例（阿拉伯文）：**
```
字形索引: 0    1    2    3    4
字符索引: 4    3    2    1    0
簇1: 字形[0], 文本[4..5)
簇2: 字形[1], 文本[3..4)
...
```

**连字示例（"fi"）：**
```
字形索引: 0    1
字符索引: 0    2
簇1: 字形[0], 文本[0..2) = "fi"
簇2: 字形[1], 文本[2..3)
```

## 依赖关系

**直接依赖:**
```cpp
#include "src/text/GlyphRun.h"         // sktext::GlyphRun 类型
#include "include/core/SkSpan.h"       // SkSpan 容器
#include "include/private/base/SkTo.h" // SkToU32 转换函数
```

**被依赖:**
```cpp
src/pdf/SkPDFDevice.cpp              // 使用 SkClusterator 处理文本绘制
src/pdf/SkPDFMakeToUnicodeCmap.cpp   // 使用簇信息生成 Unicode 映射
```

## 设计模式与设计决策

### 1. 迭代器模式

`SkClusterator` 实现了标准的迭代器接口：
- 隐藏内部复杂的映射逻辑
- 提供简单的 `next()` 接口
- 支持流式处理，避免生成中间数据结构

### 2. 不可变迭代器

所有数据成员（除了 `fCurrentGlyphIndex`）都是 `const`：
- 保证迭代过程中数据不变
- 线程安全（多个迭代器可以共享数据）
- 防止误修改输入数据

### 3. 零拷贝设计

```cpp
const char* fUtf8Text;           // 指针而非副本
uint32_t const * const fClusters; // 指针而非副本
```
直接引用 `GlyphRun` 中的数据，避免内存分配和拷贝。

### 4. 优雅降级

当没有映射数据时，仍能正常工作：
```cpp
if (!fClusters || !fUtf8Text) {
    return Cluster{nullptr, 0, fCurrentGlyphIndex++, 1};
}
```
每个字形独立成簇，支持纯字形渲染场景。

### 5. PDF 兼容性

`reversedChars()` 直接对应 PDF 的 "ReversedChars" 标志：
- 简化 PDF 生成逻辑
- 避免重复检测文本方向

## 性能考量

### 1. O(n²) 复杂度问题

```cpp
for (unsigned i = 0; i < fGlyphCount; ++i) {
   uint32_t c = fClusters[i];
   if (c > cluster && c < clusterEnd) {
       clusterEnd = c;
   }
}
```

每次调用 `next()` 都遍历整个 clusters 数组，总时间复杂度为 O(n²)。

**可能的优化：**
- 预处理 clusters 数组，构建排序索引
- 使用二分查找代替线性扫描

但实际中字形数量通常不大，简单实现已足够。

### 2. 缓存友好

```cpp
do {
    ++fCurrentGlyphIndex;
} while (fCurrentGlyphIndex < fGlyphCount &&
         cluster == fClusters[fCurrentGlyphIndex]);
```
顺序访问 clusters 数组，利用了缓存的空间局部性。

### 3. 最小状态

只维护一个索引变量 `fCurrentGlyphIndex`，内存开销极小。

## 相关文件

| 文件路径 | 说明 | 关系 |
|---------|------|------|
| `src/text/GlyphRun.h` | 字形运行定义 | 输入数据源 |
| `src/pdf/SkPDFDevice.cpp` | PDF 设备 | 主要使用者 |
| `src/pdf/SkPDFFont.cpp` | PDF 字体 | 需要簇信息 |
| `src/pdf/SkPDFMakeToUnicodeCmap.cpp` | Unicode 映射表 | 使用簇信息 |
| `src/pdf/SkBitmapKey.h` | 位图键 | 同一模块 |
| `include/core/SkSpan.h` | Span 容器 | 数据访问工具 |
