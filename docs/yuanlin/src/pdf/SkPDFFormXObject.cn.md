# SkPDFFormXObject - PDF Form XObject 生成

> 源文件：
> - `src/pdf/SkPDFFormXObject.h`
> - `src/pdf/SkPDFFormXObject.cpp`

## 概述

`SkPDFFormXObject` 模块提供了创建 PDF Form XObject（表单外部对象）的功能。Form XObject 是 PDF 中一种自包含的图形对象描述，其语法与页面对象类似，可以像位图 XObject 一样被绘制到页面内容流中。在 Skia 的 PDF 后端中，Form XObject 主要用于实现 `saveLayer` 操作以及 alpha 蒙版功能，支持隔离（Isolated）透明度混合。

## 架构位置

该模块是 PDF 设备层（`SkPDFDevice`）的辅助模块，在图层保存/恢复以及蒙版创建过程中被调用。

```
SkPDFDocument
  └── SkPDFDevice
        └── SkPDFMakeFormXObject (创建 Form XObject)
              ├── 页面内容流 → content
              ├── 资源字典 → resourceDict
              ├── 媒体盒 → mediaBox
              └── 变换矩阵 → inverseTransform
```

## 主要类与结构体

该模块没有定义类，仅提供一个独立的工厂函数。

## 公共 API 函数

### `SkPDFMakeFormXObject`

```cpp
SkPDFIndirectReference SkPDFMakeFormXObject(
    SkPDFDocument* doc,
    std::unique_ptr<SkStreamAsset> content,
    SkPDFParentTreeKey structParentsKey,
    std::unique_ptr<SkPDFArray> mediaBox,
    std::unique_ptr<SkPDFDict> resourceDict,
    const SkMatrix& inverseTransform,
    const char* colorSpace);
```

**参数：**
- `doc`：PDF 文档对象，用于注册间接引用
- `content`：Form XObject 的内容流（绘图指令）
- `structParentsKey`：结构父节点键，用于 Tagged PDF 的可访问性标记；若无效则不添加
- `mediaBox`：边界框数组（/BBox），定义 Form XObject 的坐标空间范围
- `resourceDict`：资源字典，包含内容流引用的字体、图像等资源
- `inverseTransform`：逆变换矩阵，设置为 /Matrix 属性；若为单位矩阵则省略
- `colorSpace`：颜色空间名称（如 "DeviceRGB"），设置透明度组的 /CS 属性；可为 nullptr

**返回值：** 新创建的 Form XObject 的 `SkPDFIndirectReference` 间接引用

## 内部实现细节

### 字典构建

函数构建一个 PDF 字典，包含以下键值对：
- `/Type` = `/XObject`
- `/Subtype` = `/Form`
- `/Matrix` = 变换矩阵数组（仅当非单位矩阵时添加）
- `/Resources` = 资源字典
- `/BBox` = 边界框数组
- `/StructParents` = 结构父节点索引（仅当有效时添加）

### 透明度组

每个 Form XObject 都附带一个透明度组字典（`/Group`），设置如下：
- `/S` = `/Transparency`（类型为透明度）
- `/CS` = 颜色空间名称（如果提供）
- `/I` = `true`（隔离混合模式）

隔离混合意味着 Form XObject 内部的颜色混合不受底层内容影响，这与 Skia 的 `saveLayer` 语义一致。

### Tagged PDF 支持

当 `structParentsKey` 有效时，函数会：
1. 在字典中添加 `/StructParents` 整数键
2. 调用 `doc->setContentStreamRefForStructParentsKey()` 注册内容流引用，建立结构树映射

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkPDFTypes.h` | PDF 基本类型（SkPDFDict, SkPDFArray, SkPDFIndirectReference）|
| `SkMatrix.h` | 变换矩阵 |
| `SkStream.h` | 内容流资产 |
| `SkPDFDocumentPriv.h` | 文档私有接口（注册引用、结构树）|
| `SkPDFUtils.h` | 矩阵到数组转换等工具函数 |

## 设计模式与设计决策

1. **单函数工厂**：与早期 Skia 版本中 `SkPDFFormXObject` 作为类不同，当前设计将其简化为单个工厂函数，减少了状态管理的复杂性。

2. **默认隔离混合**：所有 Form XObject 默认使用隔离透明度混合（`/I = true`），因为当前唯一的使用场景（saveLayer 和 alpha 蒙版）都要求隔离行为。代码中的 TODO 注释提到如果使用场景扩展可能需要条件化。

3. **Move 语义**：所有大型参数（content、mediaBox、resourceDict）都通过 `std::unique_ptr` 传递并使用 move 语义转移所有权，避免不必要的拷贝。

4. **条件矩阵输出**：当逆变换为单位矩阵时跳过 `/Matrix` 键的写入，减少输出大小。

## 性能考量

- 函数仅构建 PDF 字典并写出流，操作复杂度与参数大小成线性关系。
- 通过省略单位矩阵的 `/Matrix` 键，微量减少输出文件大小。
- 使用 `std::unique_ptr` 的 move 语义避免了内容流和字典的深拷贝。
- 该函数在每次 `saveLayer` 调用时执行一次，频率取决于绘图内容的复杂度。

## 相关文件

- `src/pdf/SkPDFDevice.h` / `src/pdf/SkPDFDevice.cpp` — 主要调用方，在 saveLayer 实现中使用
- `src/pdf/SkPDFDocumentPriv.h` — 文档私有接口
- `src/pdf/SkPDFTypes.h` — PDF 基本类型定义
- `src/pdf/SkPDFUtils.h` — PDF 工具函数（矩阵转换等）
