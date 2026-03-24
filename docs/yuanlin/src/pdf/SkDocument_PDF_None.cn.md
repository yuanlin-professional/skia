# SkDocument_PDF_None

> 源文件
> - src/pdf/SkDocument_PDF_None.cpp

## 概述

`SkDocument_PDF_None` 是当 Skia 构建时禁用 PDF 支持时的占位实现。它提供了 PDF 文档 API 的空实现，确保依赖 PDF 功能的代码仍能编译和链接，但实际调用会返回空结果或执行空操作。

这种设计允许 Skia 在不需要 PDF 功能的平台或配置中减小二进制大小，同时保持 API 的一致性。

## 架构位置

该文件是 PDF 模块的条件编译分支：

```
src/pdf/
├── SkPDFDocument.cpp           // 完整的 PDF 实现（编译时选择其一）
├── SkDocument_PDF_None.cpp     // 空实现（当前模块）
└── include/docs/SkPDFDocument.h // 公共 API 声明
```

构建系统根据配置选择编译哪个实现文件。

## 实现的 API

### SkPDF::MakeDocument()

```cpp
sk_sp<SkDocument> SkPDF::MakeDocument(SkWStream*, const SkPDF::Metadata&) {
    return nullptr;
}
```

**功能：**
- 创建 PDF 文档对象的工厂函数
- 空实现返回 `nullptr`

**正常实现：**
```cpp
// 在 SkPDFDocument.cpp 中
sk_sp<SkDocument> SkPDF::MakeDocument(SkWStream* stream, const SkPDF::Metadata& metadata) {
    return sk_make_sp<SkPDFDocument>(stream, metadata);
}
```

**使用示例：**
```cpp
auto doc = SkPDF::MakeDocument(&outputStream, metadata);
if (!doc) {
    // PDF 支持未启用
    return false;
}
```

### SkPDF::SetNodeId()

```cpp
void SkPDF::SetNodeId(SkCanvas* c, int n) {
    c->drawAnnotation({0, 0, 0, 0}, "PDF_Node_Key",
                      SkData::MakeWithCopy(&n, sizeof(n)).get());
}
```

**功能：**
- 为 Canvas 节点设置 PDF 结构树 ID
- 用于 PDF 的辅助功能（Accessibility）支持

**实现说明：**
即使在无 PDF 模式下，此函数仍有实现：
- 将节点 ID 作为注解写入 Canvas
- 如果最终不生成 PDF，注解会被忽略
- 保持 API 调用的一致性

**正常实现：**
在完整 PDF 实现中，这个函数会关联到 PDF 的结构树节点。

### SkPDF::AttributeList

```cpp
SkPDF::AttributeList::AttributeList() = default;
SkPDF::AttributeList::~AttributeList() = default;
```

**功能：**
- PDF 属性列表的空实现
- 提供默认构造和析构函数

**正常实现：**
```cpp
// 在完整实现中，AttributeList 管理 PDF 属性
class AttributeList {
    std::vector<Attribute> fAttributes;
    // ...
};
```

### SkPDFArray 声明

```cpp
class SkPDFArray {};
```

**功能：**
- PDF 数组对象的空声明
- 允许代码引用该类型而不会产生链接错误

**说明：**
这是一个空类声明，仅用于满足编译器的符号解析需求。在正常实现中，`SkPDFArray` 是完整的 PDF 数组实现类。

## 设计模式与设计决策

### 1. 空对象模式

提供空实现而非编译时错误：
- 优点：使用 PDF 功能的代码可以正常编译
- 缺点：运行时才能发现 PDF 功能不可用

这是一种权衡，优先考虑编译时兼容性。

### 2. 条件编译

通过构建配置选择实现文件：
```gn
# 在 BUILD.gn 中
if (skia_enable_pdf) {
  sources += [ "SkPDFDocument.cpp" ]
} else {
  sources += [ "SkDocument_PDF_None.cpp" ]
}
```

### 3. 最小化实现

只实现必要的符号：
- 减少二进制大小
- 避免引入不必要的依赖
- 保持清晰的边界

### 4. 返回 nullptr vs 抛出异常

选择返回 `nullptr` 而非抛出异常：
- Skia 通常使用返回值指示错误
- 避免异常处理开销
- 与 Skia 的整体风格一致

### 5. SetNodeId() 的特殊处理

即使在无 PDF 模式下也保留部分功能：
- 允许上层代码无条件调用
- 通过注解机制传递信息
- 如果最终输出 PDF，数据可以被使用

## 使用场景

### 1. 嵌入式系统

不需要 PDF 功能的嵌入式设备：
- 节省存储空间（PDF 实现较大）
- 减少代码复杂度
- 降低依赖（如 zlib、字体子系统等）

### 2. 纯渲染应用

只需要光栅化或 GPU 渲染的应用：
- 游戏引擎
- 实时图形应用
- 简单的图像处理工具

### 3. 平台限制

某些平台可能不支持 PDF 所需的功能：
- 缺少文件系统
- 内存受限
- 法律或许可限制

## 性能考量

### 1. 零开销

空实现几乎没有运行时开销：
- 函数调用立即返回
- 无内存分配
- 无复杂计算

### 2. 二进制大小

避免链接完整 PDF 实现可以显著减小二进制：
- PDF 实现包含大量代码
- 避免链接字体、压缩等子系统
- 典型节省：数百 KB 到数 MB

### 3. 编译时间

减少编译的代码量：
- 更快的增量构建
- 减少模板实例化
- 简化依赖关系

## 与完整实现的对比

| 功能 | 完整实现 | 空实现 |
|------|---------|-------|
| MakeDocument | 返回完整文档对象 | 返回 nullptr |
| SetNodeId | 设置 PDF 结构节点 | 写入注解（可能被忽略） |
| AttributeList | 管理属性 | 空类 |
| SkPDFArray | 完整 PDF 数组 | 空声明 |
| 二进制大小 | 大 | 极小 |
| 依赖 | 多（zlib、字体等） | 极少 |

## 相关文件

| 文件路径 | 说明 | 关系 |
|---------|------|------|
| `src/pdf/SkPDFDocument.cpp` | 完整 PDF 实现 | 互斥实现 |
| `include/docs/SkPDFDocument.h` | PDF 文档 API | 接口定义 |
| `include/core/SkCanvas.h` | Canvas 类 | SetNodeId 使用 |
| `include/core/SkData.h` | 数据对象 | 注解数据 |
| `BUILD.gn` | 构建配置 | 选择实现 |

## 诊断 PDF 功能是否启用

**运行时检测：**
```cpp
bool isPDFAvailable() {
    SkDynamicMemoryWStream stream;
    SkPDF::Metadata metadata;
    auto doc = SkPDF::MakeDocument(&stream, metadata);
    return doc != nullptr;
}
```

**编译时检测：**
```cpp
#ifdef SK_PDF_USE_SFNTLY
    // PDF 功能已启用
#else
    // PDF 功能未启用或使用简化版本
#endif
```

## 最佳实践

### 1. 检查返回值

始终检查 `MakeDocument()` 的返回值：
```cpp
auto doc = SkPDF::MakeDocument(&stream, metadata);
if (!doc) {
    // 处理 PDF 不可用的情况
    return handleNoPDF();
}
```

### 2. 提供替代方案

为无 PDF 模式提供备选功能：
```cpp
if (isPDFAvailable()) {
    generatePDF();
} else {
    generatePNG();  // 备选输出格式
}
```

### 3. 文档化依赖

在文档中明确说明 PDF 功能是可选的：
```cpp
/**
 * 导出为 PDF。
 * @return 如果 PDF 支持未启用，返回 false。
 */
bool exportPDF();
```
