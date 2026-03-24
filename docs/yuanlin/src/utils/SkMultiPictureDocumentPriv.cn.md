# SkMultiPictureDocumentPriv

> 源文件: src/utils/SkMultiPictureDocumentPriv.h

## 概述

`SkMultiPictureDocumentPriv.h` 是 Skia 图形库中多图片文档(Multi-Picture Document)的私有扩展API头文件。该文件在公共API `SkMultiPictureDocument.h` 的基础上,提供了额外的内部功能,主要用于在不解析整个文档的情况下读取文档中所有页面的尺寸信息。

这是一个私有头文件,主要供 Skia 的内部工具(如 DM 测试框架)使用,不属于公开的 Skia API。

## 架构位置

该文件位于 Skia 的工具模块中,是多图片文档功能的扩展接口:

```
src/
  └── utils/
      └── SkMultiPictureDocumentPriv.h  # 私有扩展API(本文件)

include/
  └── docs/
      └── SkMultiPictureDocument.h      # 公共API
```

作为私有扩展,它补充了公共API的功能,提供了更高效的元数据读取能力。

## 主要类与结构体

该文件不定义类或结构体,仅在 `SkMultiPictureDocument` 命名空间中声明扩展函数。

## 公共 API 函数

### `ReadPageSizes()`

```cpp
namespace SkMultiPictureDocument {

bool ReadPageSizes(SkStreamSeekable* src,
                   SkDocumentPage* dstArray,
                   int dstArrayCount);

}
```

**功能**: 从多图片文档流中读取所有页面的尺寸信息,而无需解析整个文档内容。

**参数**:
- `src`: 可seek的输入流,指向多图片文档数据
- `dstArray`: 用于接收页面信息的数组
- `dstArrayCount`: 数组的容量(页面数)

**返回值**:
- `true`: 成功读取页面尺寸
- `false`: 读取失败(文档格式错误、流错误等)

**使用场景**:
- 快速获取文档页面数和每页尺寸
- 无需加载完整的图片数据
- 用于文档预览、索引生成等场景

## 内部实现细节

### 设计动机

多图片文档可能包含大量页面和复杂的绘制指令,完整解析可能非常耗时。`ReadPageSizes()` 提供了一种**轻量级的元数据读取方式**:

1. **只读取文档头部**: 页面尺寸信息通常存储在文档开始位置
2. **跳过绘制指令**: 不需要反序列化 `SkPicture` 对象
3. **快速索引**: 可以快速构建文档的页面索引

### `SkDocumentPage` 结构

虽然该头文件中未定义,但 `SkDocumentPage` 通常包含:

```cpp
struct SkDocumentPage {
    SkSize fSize;        // 页面尺寸(宽度和高度)
    // 可能还包含其他元数据
};
```

### 流的可seek性要求

```cpp
SkStreamSeekable* src
```

**为何需要可seek**:
- 多图片文档格式可能将页面索引信息存储在文档末尾
- 需要跳转到特定位置读取元数据
- 不可seek的流(如网络流)无法使用该功能

## 依赖关系

### 公共API依赖

```cpp
#include "include/docs/SkMultiPictureDocument.h"
```

该头文件扩展了公共API的命名空间,因此必须包含公共头文件。

### 可能的类型依赖

```cpp
// 推测的依赖(未在本文件中直接包含)
#include "include/core/SkStream.h"     // SkStreamSeekable
#include "include/core/SkDocument.h"   // SkDocumentPage
```

## 设计模式与设计决策

### 1. 命名空间扩展模式

将扩展函数放在相同的命名空间中:

```cpp
namespace SkMultiPictureDocument {
    // 公共API(在公共头文件中)
    sk_sp<SkDocument> Make(...);

    // 私有扩展API(在本文件中)
    bool ReadPageSizes(...);
}
```

**优点**:
- 保持API的逻辑一致性
- 避免命名冲突
- 清晰的功能归属

### 2. 私有头文件策略

将扩展功能放在私有头文件中:

**优点**:
- 不污染公共API
- 可以随时修改而不影响公共契约
- 明确标识内部使用的功能

**使用者**: 主要是 DM(Draw Manager)测试框架,用于:
- 验证文档格式正确性
- 快速扫描测试文档
- 生成测试报告

### 3. 错误处理策略

使用布尔返回值表示成功/失败:
- 简单明了,无需异常
- 调用者需要检查返回值
- 失败时 `dstArray` 的内容未定义

## 性能考量

### 性能优势

相比完整解析文档:

| 操作 | 完整解析 | ReadPageSizes() |
|------|---------|-----------------|
| 时间复杂度 | O(n × p) | O(n) |
| 内存使用 | 高(加载所有图片) | 低(仅元数据) |
| 典型时间 | 秒级 | 毫秒级 |

其中:
- `n`: 页面数
- `p`: 每页平均绘制指令数

### 适用场景

**适合使用**:
- 文档浏览器(显示页面缩略图尺寸)
- 打印预览(计算页面布局)
- 文档转换工具(确定输出格式)
- 测试验证(检查页面数和尺寸)

**不适合使用**:
- 需要渲染内容的场景(必须完整解析)
- 流式处理(需要可seek的流)

### 内存占用

假设 100 页文档:
```cpp
SkDocumentPage pages[100];  // 约 100 × 8 bytes = 800 bytes
ReadPageSizes(stream, pages, 100);
```

内存占用极小,适合大规模文档处理。

## 相关文件

### 公共API

- `include/docs/SkMultiPictureDocument.h`: 多图片文档的公共接口
- `include/core/SkDocument.h`: 文档抽象基类

### 实现文件

- `src/utils/SkMultiPictureDocument.cpp`: 多图片文档的实现(推测)

### 使用场景

#### DM(Draw Manager)使用示例

```cpp
#include "src/utils/SkMultiPictureDocumentPriv.h"
#include "include/core/SkStream.h"

void ValidateDocument(const char* filepath) {
    auto stream = SkFILEStream::Make(filepath);
    if (!stream) return;

    // 快速读取页面尺寸
    constexpr int kMaxPages = 1000;
    SkDocumentPage pages[kMaxPages];

    if (SkMultiPictureDocument::ReadPageSizes(stream.get(), pages, kMaxPages)) {
        for (int i = 0; i < kMaxPages; ++i) {
            if (pages[i].fSize.isEmpty()) break;
            printf("Page %d: %.2f x %.2f\n",
                   i, pages[i].fSize.width(), pages[i].fSize.height());
        }
    }
}
```

#### 文档浏览器使用示例

```cpp
class DocumentViewer {
public:
    bool LoadDocument(SkStreamSeekable* stream) {
        // 先读取页面尺寸
        std::vector<SkDocumentPage> pages(100);
        if (!SkMultiPictureDocument::ReadPageSizes(
                stream, pages.data(), pages.size())) {
            return false;
        }

        // 根据尺寸信息显示页面列表
        for (size_t i = 0; i < pages.size(); ++i) {
            if (pages[i].fSize.isEmpty()) break;
            AddPageThumbnail(i, pages[i].fSize);
        }

        return true;
    }
};
```

## 文档格式考虑

多图片文档格式通常在文件头部包含:
1. **文件签名**: 标识文档类型
2. **版本号**: 格式版本
3. **页面数**: 文档总页数
4. **页面索引表**: 每页的偏移和尺寸

`ReadPageSizes()` 利用这种结构,只解析索引表部分。

## 兼容性注意事项

### 版本兼容

- 需要处理不同版本的文档格式
- 旧版本文档可能不包含页面索引
- 需要降级处理(返回 `false`)

### 流的有效性

调用者需要确保:
- 流有效且可读
- 流支持 seek 操作
- 流内容是有效的多图片文档

### 错误处理

```cpp
if (!SkMultiPictureDocument::ReadPageSizes(stream, pages, count)) {
    // 可能的错误:
    // 1. 流无效
    // 2. 文档格式错误
    // 3. 文档版本不支持
    // 需要降级到完整解析或报告错误
}
```

该私有API为 Skia 的内部工具提供了高效的文档元数据读取能力,展示了在性能和功能之间的精心权衡,是大规模文档处理和测试验证的重要工具。
