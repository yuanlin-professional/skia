# SkPDFGraphicState - PDF 图形状态管理

> 源文件：
> - `src/pdf/SkPDFGraphicState.h`
> - `src/pdf/SkPDFGraphicState.cpp`

## 概述

`SkPDFGraphicState` 是 Skia PDF 后端中负责管理 PDF 图形状态字典（Graphics State Dictionary）的模块。PDF 图形状态字典大致对应于 `SkPaint` 对象的属性，包括 Alpha 透明度、混合模式、描边参数（宽度、端帽、连接方式、斜接限制）等。该模块实现了图形状态的规范化和去重，确保相同的图形状态在 PDF 文件中只输出一次。此外，它还提供了创建软蒙版（Soft Mask / SMask）图形状态的功能。

## 架构位置

该模块是 PDF 渲染管线中的中间层，被 `SkPDFDevice` 在每次绘图操作时调用以获取对应的图形状态。

```
SkPDFDevice (绘图操作)
  └── SkPDFGraphicState
        ├── GetGraphicStateForPaint → 填充/描边图形状态
        │     ├── doc->fFillGSMap (填充状态缓存)
        │     └── doc->fStrokeGSMap (描边状态缓存)
        └── GetSMaskGraphicState → 软蒙版图形状态
              └── make_invert_function → Alpha 反转函数
```

## 主要类与结构体

### `SkPDFStrokeGraphicState`

```cpp
struct SkPDFStrokeGraphicState {
    SkScalar fStrokeWidth;   // 描边宽度
    SkScalar fStrokeMiter;   // 斜接限制
    SkScalar fAlpha;         // 透明度
    uint8_t fStrokeCap;      // 端帽样式 (SkPaint::Cap)
    uint8_t fStrokeJoin;     // 连接样式 (SkPaint::Join)
    uint8_t fBlendMode;      // 混合模式 (SkBlendMode)
    uint8_t fPADDING = 0;   // 填充字节
};
```

描边模式的图形状态键。使用 `SK_BEGIN_REQUIRE_DENSE` 确保紧凑内存布局，支持 `memcmp` 进行快速比较。`Hash` 类型为 `SkForceDirectHash`，直接对结构体内存进行哈希。

### `SkPDFFillGraphicState`

```cpp
struct SkPDFFillGraphicState {
    SkScalar fAlpha;          // 透明度
    uint8_t fBlendMode;       // 混合模式
    uint8_t fPADDING[3] = {0, 0, 0};  // 填充字节
};
```

填充模式的图形状态键。相比描边状态，填充状态只需要 Alpha 和混合模式两个参数。同样使用紧凑布局和直接哈希。

### `SkPDFSMaskMode` 枚举

```cpp
enum SkPDFSMaskMode {
    kAlpha_SMaskMode,       // 使用 Alpha 通道作为蒙版
    kLuminosity_SMaskMode   // 使用亮度作为蒙版
};
```

## 公共 API 函数

### `GetGraphicStateForPaint`

```cpp
SkPDFIndirectReference GetGraphicStateForPaint(SkPDFDocument*, const SkPaint&);
```

根据 `SkPaint` 的属性生成或查找对应的 PDF 图形状态字典。区分填充和描边两种模式：

- **填充模式**：生成包含 `/ca`（填充透明度）和 `/BM`（混合模式）的字典
- **描边模式**：生成包含 `/CA`（描边透明度）、`/ca`（填充透明度）、`/LC`（线帽）、`/LJ`（线连接）、`/LW`（线宽）、`/ML`（斜接限制）、`/SA`（自动描边调整）和 `/BM`（混合模式）的字典

### `GetSMaskGraphicState`

```cpp
SkPDFIndirectReference GetSMaskGraphicState(SkPDFIndirectReference sMask,
                                            bool invert,
                                            SkPDFSMaskMode sMaskMode,
                                            SkPDFDocument* doc);
```

创建软蒙版图形状态。生成一个 `/ExtGState` 字典，包含 `/SMask` 子字典（指定蒙版类型 Alpha 或 Luminosity、蒙版 Form XObject 引用，以及可选的 Alpha 反转函数）。注意：SMask 图形状态不进行去重，因为实际重复使用同一蒙版的概率很低。

## 内部实现细节

### 混合模式映射

`pdf_blend_mode()` 将 `SkBlendMode` 映射为 PDF 支持的混合模式。PDF 不支持 `kXor` 和 `kPlus` 模式，这些会回退到 `kSrcOver`。

### 描边参数映射

- **线帽**：`to_stroke_cap()` 将 `SkPaint::Cap` 映射为 PDF 整数值（Butt=0, Round=1, Square=2）
- **线连接**：`to_stroke_join()` 将 `SkPaint::Join` 映射为 PDF 整数值（Miter=0, Round=1, Bevel=2）

### Alpha 反转函数

`make_invert_function()` 创建一个 Type 4 PostScript 函数 `{1 exch sub}`，用于反转蒙版的 Alpha 值。选择 Type 4 函数是因为 Acrobat 在 Type 0 函数时崩溃，kpdf 在 Type 2 函数时崩溃。该函数在文档级别去重（`doc->fInvertFunction`），因为多个蒙版可能共用同一个反转函数。

### 缓存策略

填充和描边图形状态分别存储在 `doc->fFillGSMap` 和 `doc->fStrokeGSMap` 中。键为结构体本身（通过紧凑内存布局支持直接哈希和比较），值为 PDF 间接引用。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkPDFTypes.h` | PDF 基本类型（SkPDFDict, SkPDFIndirectReference）|
| `SkChecksum.h` | `SkForceDirectHash` 直接哈希 |
| `SkPDFDocumentPriv.h` | 文档私有接口（缓存映射、对象发射）|
| `SkPDFUtils.h` | 混合模式名称转换 |
| `SkPaint.h` | 画笔属性 |
| `SkBlendMode.h` | 混合模式枚举 |
| `SkData.h` | 反转函数数据 |
| `SkStream.h` | 流操作 |
| `SkTHash.h` | 哈希映射容器 |

## 设计模式与设计决策

1. **规范化去重**：填充和描边图形状态通过哈希映射实现规范化，确保相同属性组合只输出一次到 PDF 文件。这对于大量绘图操作使用相同画笔的场景特别有效。

2. **紧凑结构体**：使用 `SK_BEGIN_REQUIRE_DENSE` / `SK_END_REQUIRE_DENSE` 宏确保结构体无填充，使得 `memcmp` 比较和直接内存哈希安全可靠。

3. **填充/描边分离**：将填充和描边状态分为不同的结构体和缓存，因为填充状态更简单（只有两个参数），这样填充操作的缓存查找更高效。

4. **SMask 不去重**：SMask 图形状态不进行缓存去重，因为实际场景中重复使用同一蒙版的概率极低，去重带来的收益不足以弥补缓存维护的开销。

5. **兼容性妥协**：Alpha 反转函数使用 Type 4 是为了同时兼容 Acrobat 和 kpdf，代码注释明确说明了原因。

## 性能考量

- **O(1) 缓存查找**：图形状态通过哈希映射缓存，查找时间为常数级别。
- **紧凑键设计**：键结构体体积小（描边 20 字节，填充 8 字节），直接内存哈希避免了字段逐一处理的开销。
- **反转函数共享**：文档级别共享单一反转函数对象，避免在多个 SMask 使用时重复创建。
- **按需创建**：图形状态字典仅在首次使用时创建，后续相同参数的请求直接返回缓存的引用。

## 相关文件

- `src/pdf/SkPDFDevice.h` / `src/pdf/SkPDFDevice.cpp` — 主要调用方，在绘图操作中设置图形状态
- `src/pdf/SkPDFDocumentPriv.h` — 文档私有接口（包含缓存映射字段）
- `src/pdf/SkPDFUtils.h` — PDF 工具函数（混合模式名称）
- `src/pdf/SkPDFGradientShader.cpp` — 渐变着色器中使用 SMask 图形状态
- `src/pdf/SkPDFTypes.h` — PDF 基本类型
