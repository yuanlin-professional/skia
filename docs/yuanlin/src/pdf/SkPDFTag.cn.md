# SkPDFTag (PDF 标签结构树)

> 源文件:
> - `src/pdf/SkPDFTag.h`
> - `src/pdf/SkPDFTag.cpp`

## 概述

`SkPDFTag` 模块实现了 PDF 标签结构树（Tagged PDF），这是 PDF/UA（无障碍访问）和 PDF 结构化内容的核心组件。`SkPDFStructTree` 类管理结构元素（StructElem）的层级关系，负责创建标记内容标识符（MCID）、维护父树（ParentTree）、生成 ID 树（IDTree），以及输出结构树根（StructTreeRoot）和大纲（Outline）。源文件超过 900 行，完整实现了 PDF 规范中的结构化标记体系。

## 架构位置

```
SkPDFDocument
  |-- SkPDFStructTree (结构树管理)
  |     |-- SkPDFStructElem (结构元素节点)
  |     |     |-- MarkedContentInfo (标记内容)
  |     |     |-- ContentItemInfo (内容项)
  |     |     |-- Attributes (属性)
  |     |
  |     |-- ParentTree (父树: MCID/StructParents -> StructElem)
  |     |-- IDTree (ID 树: elemId -> StructElem)
  |
  |-- PDF 页面内容流 (包含 BMC/EMC 标记)
```

## 主要类与结构体

### `SkPDFStructTree`

结构树的顶层管理类。

**关键成员：**
- `fArena` -- Arena 分配器，管理结构元素的内存
- `fStructElemForElemId` -- 元素 ID 到结构元素的映射
- `fRoot` -- 根结构元素
- `fOutline` -- 大纲模式（None/StructureOnly/Full）
- `fParentTree` -- 父树条目数组

### `SkPDFStructTree::Mark`

标记内容的句柄，表示一个活跃的标记内容序列。

**方法：**
- `mcid()` -- 返回标记内容标识符
- `elemId()` -- 返回关联的结构元素 ID
- `structType()` -- 返回结构类型（如 "P", "H1", "Table" 等）
- `accumulate(SkPoint)` -- 积累标记区域的位置信息

### `SkPDFStructElem`（内部结构体）

单个结构元素，在 `.cpp` 文件中定义。

**关键成员：**
- `fParent` -- 父元素
- `fChildren` -- 子元素跨度
- `fMarkedContent` -- 标记内容信息数组
- `fElemId` -- 元素标识符
- `fStructType` -- 结构类型
- `fTitle` / `fAlt` / `fLang` -- 可选的标题、替代文本、语言
- `fAttributes` -- PDF 属性数组
- `fContentItems` -- 内容项（注释等）

## 公共 API 函数

### 标记创建

- **`createMarkForElemId(elemId, pageIndex, structParentsKey)`** -- 为指定的结构元素创建新的 MCID。如果 `structParentsKey` 尚未设置，会创建新的 StructParents 条目。
- **`createStructParentKeyForElemId(elemId, pageIndex, contentItemRef)`** -- 为注释等内容项创建 StructParent 键。

### 内容流关联

- **`setContentStreamRefForStructParentsKey(key, ref)`** -- 设置 StructParents 键对应的内容流引用。
- **`getContentStreamRefForStructParentsKey(key)`** -- 获取 StructParents 键的内容流引用。

### 结构元素操作

- **`addStructElemTitle(elemId, title)`** -- 为结构元素添加标题。

### 文档输出

- **`emitStructTreeRoot(doc)`** -- 输出结构树根到 PDF 文档，返回间接引用。
- **`makeOutline(doc)`** -- 生成文档大纲（书签）。
- **`getRootLanguage()`** -- 获取根元素的语言标记。

## 内部实现细节

### 元素 ID 到字符串的转换

`SkPDFStructElem::StringFromElemId()` 将整数 ID 转换为零填充的字符串格式 `"node00000001"`。零填充确保字典序与数字序一致，满足 PDF IDTree 的排序要求。

### 使用标记传播

`SkPDFStructElem::setUsed()` 递归标记结构元素及其父元素和属性引用的元素为"已使用"。只有标记为已使用的元素才会被输出到最终的 PDF 中。

### 父树（ParentTree）

父树将 StructParents/StructParent 值映射到对应的结构元素。两种条目类型：
- **Stream** -- 包含按 MCID 索引的结构元素数组（用于页面内容流）
- **Item** -- 包含单个结构元素引用（用于注释等内容项）

### 属性列表

`SkPDF::AttributeList` 支持多种属性类型的追加：
- `appendInt/Float/Name/TextString` -- 基本类型属性
- `appendFloatArray` -- 浮点数组属性
- `appendNodeIdArray` -- 节点 ID 数组属性（自动标记引用的元素为需要 ID）

### 位置积累

`Location::accumulate()` 方法用于计算标记内容的包围区域：取各标记点的最小 X、最大 Y（PDF 的 y 轴向上），并在跨页时取较早页面的位置。

### 结构元素输出

`SkPDFStructElem::emitStructElem()` 生成完整的 PDF StructElem 字典：
- `/S` -- 结构类型（如 `P`, `H1`, `Table`, `Figure`）
- `/P` -- 父元素引用
- `/K` -- 子元素数组（MCID、子 StructElem 引用、OBJR 等）
- `/T` -- 标题文本（可选）
- `/Alt` -- 替代文本（可选，用于无障碍访问）
- `/Lang` -- 语言标记（可选）
- `/A` -- 属性（可选）
- `/ID` -- 元素标识符字节串（仅需要被属性引用的元素）

### 大纲生成

`makeOutline()` 从结构树生成 PDF 大纲（书签）：
- 遍历结构元素，查找有标题的元素
- 根据结构层级创建大纲条目的父子关系
- 每个大纲条目包含标题文本和目标位置（页面+坐标）

## 依赖关系

**内部依赖：**
- `SkPDFTypes` -- PDF 基础类型（Dict, Array, Ref）
- `SkPDFDocumentPriv` -- 文档内部接口
- `SkPDFDocument` -- 公共文档结构定义

**外部依赖：**
- `SkArenaAlloc` -- Arena 内存分配器
- `SkTHash` -- 哈希容器
- `SkTArray` -- 动态数组
- `SkString`, `SkPoint` -- 基础类型
- `<variant>` -- ParentTree 条目的多态存储

## 设计模式与设计决策

1. **Arena 分配**：所有 `SkPDFStructElem` 通过 `SkArenaAlloc` 分配，随结构树一起销毁，避免逐个释放的开销。

2. **延迟使用标记**：结构元素只有在被实际引用时才标记为"已使用"，未使用的元素不会出现在最终 PDF 中。

3. **StructParents 动态分配**：页面的 StructParents 键按需创建，第一次在页面上创建标记时自动分配。

4. **ID 零填充**：使用零填充的数字字符串作为元素 ID，确保 PDF IDTree（名称树）的字典序排列与数字排序一致。

5. **大纲从结构树生成**：文档大纲（书签）直接从结构元素的标题生成，避免了单独维护大纲结构。

## 性能考量

- **Arena 分配**：所有结构元素在 arena 中连续分配，具有良好的缓存局部性。
- **哈希映射查找**：元素 ID 到结构元素的映射使用哈希表，O(1) 查找。
- **懒惰输出**：结构元素只在文档完成时才序列化为 PDF 对象，避免了构建过程中的序列化开销。
- **子集输出**：只输出被使用的结构元素，跳过未引用的元素，减小文件大小。

## 相关文件

- `src/pdf/SkPDFDocumentPriv.h` -- 文档内部接口
- `include/docs/SkPDFDocument.h` -- 文档公共接口（StructureElementNode 定义）
- `src/pdf/SkPDFTypes.h` -- PDF 基础类型
