# SkPDFSubsetFont — PDF 字体子集化

> 源文件：[src/pdf/SkPDFSubsetFont.h](../../src/pdf/SkPDFSubsetFont.h)、[src/pdf/SkPDFSubsetFont.cpp](../../src/pdf/SkPDFSubsetFont.cpp)

## 概述

`SkPDFSubsetFont` 模块使用 HarfBuzz 库实现字体子集化功能，用于 PDF 文档生成。字体子集化是指从完整的字体文件中提取仅包含实际使用字形的子集，以减小 PDF 文件大小。

核心特性：
- 基于 HarfBuzz subset API 的字体子集化
- 保留原始字形 ID（`HB_SUBSET_FLAGS_RETAIN_GIDS`）
- 支持从流或表级别访问字体数据
- 条件编译：仅在 `SK_PDF_USE_HARFBUZZ_SUBSET` 定义时启用
- 版本感知：根据 HarfBuzz 版本选择最佳策略

## 架构位置

```
SkPDFFont（字体嵌入管理）
    │
    └── SkPDFSubsetFont()
            │
            └── HarfBuzz Subset API
                ├── hb_face_create() / hb_face_create_for_tables()
                ├── hb_subset_input_create_or_fail()
                └── hb_subset_or_fail()
```

## 公共 API 函数

### `SkPDFSubsetFont(const SkTypeface& typeface, const SkPDFGlyphUse& glyphUsage) -> sk_sp<SkData>`

对字体进行子集化，仅保留 `glyphUsage` 中标记为已使用的字形。字形 ID 在子集中保持不变。返回子集化后的字体数据，失败时返回 `nullptr`。

### `SkPDFCanSubsetTableBasedFonts() -> bool`

检查当前 HarfBuzz 版本是否支持基于表的字体子集化（需要 HarfBuzz 4.4.0+）。

## 内部实现细节

### HarfBuzz 资源管理

使用 RAII 智能指针包装 HarfBuzz 对象：
- `HBBlob` — `hb_blob_t` + `hb_blob_destroy`
- `HBFace` — `hb_face_t` + `hb_face_destroy`
- `HBSubsetInput` — `hb_subset_input_t` + `hb_subset_input_destroy`
- `HBSet` — `hb_set_t` + `hb_set_destroy`

### 字体数据获取策略

`subset_harfbuzz()` 采用分级策略获取 `hb_face_t`：

1. **不支持表级访问**（`!SkPDFCanSubsetTableBasedFonts()`）：
   - 通过 `typeface.openStream()` 获取完整字体流
   - 使用 `stream_to_face()` 转为 `hb_face_t`

2. **支持表级访问**（HarfBuzz 4.4.0+）：
   - 优先尝试 `openExistingStream()` 获取内存映射流
   - 如果无法获取，使用 `hb_face_create_for_tables()` 创建按需加载表的 face
   - HarfBuzz 10.0.0+ 额外设置 `hb_face_set_get_table_tags_func` 回调

### 流到 Blob 的转换

`stream_to_blob()` 优化了两种情况：
- 流有 `getMemoryBase()` → 零拷贝，直接使用内存基址创建 blob
- 流无内存基址 → 分配内存，完整读取流数据

### 子集化标志

- `HB_SUBSET_FLAGS_RETAIN_GIDS`：保留原始字形 ID 不变，使 PDF 中的字形引用无需重映射
- `HB_SUBSET_FLAGS_NOTDEF_OUTLINE`：当字形 0（.notdef）被使用时保留其轮廓

### 数据转换

`to_data()` 将 HarfBuzz blob 转为 `SkData`，使用 `SkData::MakeWithProc` 实现零拷贝转移所有权。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| HarfBuzz（hb.h, hb-subset.h） | 字体子集化引擎 |
| `SkPDFGlyphUse` | 字形使用集合 |
| `SkTypeface` | 字体抽象（提供字体数据和表访问） |
| `SkData` | 不可变数据块 |
| `SkStream` | 字体数据流 |

## 设计模式与设计决策

1. **RAII 包装**：使用 `std::unique_ptr` + `SkFunctionObject` 包装 HarfBuzz 对象，确保资源自动释放。

2. **版本适配**：根据 HarfBuzz 版本（4.4.0、10.0.0）选择最佳的 face 创建策略，确保向后兼容。

3. **按需表加载**：`hb_face_create_for_tables` 允许 HarfBuzz 只请求需要的表，避免加载整个字体文件。

4. **条件编译**：未定义 `SK_PDF_USE_HARFBUZZ_SUBSET` 时提供返回 `nullptr` 的空实现，允许无 HarfBuzz 构建。

5. **保留字形 ID**：通过 `RETAIN_GIDS` 标志避免字形 ID 重映射，简化了 PDF 字体描述和文本流的生成。

## 性能考量

- **零拷贝转换**：`stream_to_blob` 和 `to_data` 在数据有内存基址时实现零拷贝转移。
- **按需表加载**：`hb_face_create_for_tables` 延迟加载字体表，减少不必要的 I/O。
- **子集化效率**：HarfBuzz 子集化通常将 CJK 字体从数 MB 减小到数十 KB，显著减小 PDF 文件大小。
- **单次子集化**：字体在整个文档完成后执行一次子集化，避免重复处理。

## 相关文件

- `src/pdf/SkPDFGlyphUse.h` — 字形使用集合
- `src/pdf/SkPDFFont.h` — PDF 字体嵌入管理
- `include/core/SkTypeface.h` — 字体抽象基类
