# SkPDFGradientShader - PDF 渐变着色器生成

> 源文件：
> - `src/pdf/SkPDFGradientShader.h`
> - `src/pdf/SkPDFGradientShader.cpp`

## 概述

`SkPDFGradientShader` 是 Skia PDF 后端中负责将 Skia 渐变着色器（`SkShader`）转换为 PDF 着色模式（Shading Pattern）的模块。它支持四种渐变类型：线性渐变（Linear）、径向渐变（Radial）、锥形渐变（Conical/Two-Point Radial）和扫描渐变（Sweep）。该模块能处理多种平铺模式（Clamp、Repeat、Mirror、Decal），支持透视变换，并能正确处理包含 Alpha 通道的渐变。

## 架构位置

该模块是 PDF 着色器子系统的核心组件，位于 `SkPDFDevice` 和实际 PDF 输出之间。

```
SkPDFDevice
  └── SkPDFShader (着色器调度)
        └── SkPDFGradientShader::Make (渐变着色器入口)
              ├── make_key (构建缓存键)
              ├── find_pdf_shader (缓存查找/创建)
              │     ├── make_function_shader (不透明渐变)
              │     └── make_alpha_function_shader (带Alpha渐变)
              └── gradient_function_code (PostScript函数生成)
```

## 主要类与结构体

### `SkPDFGradientShader::Key`

```cpp
struct Key {
    SkShaderBase::GradientType fType;       // 渐变类型
    SkShaderBase::GradientInfo fInfo;       // 渐变参数（颜色、停靠点、控制点等）
    std::unique_ptr<SkColor4f[]> fColors;   // 颜色数组（拥有所有权）
    std::unique_ptr<SkScalar[]> fStops;     // 停靠点数组（拥有所有权）
    SkMatrix fCanvasTransform;              // 画布变换矩阵
    SkMatrix fShaderTransform;              // 着色器局部变换矩阵
    SkIRect fBBox;                          // 表面边界框
    uint32_t fHash;                         // 预计算哈希值
};
```

用作渐变着色器的缓存键，包含完整描述一个渐变所需的全部参数。`fColors` 和 `fStops` 拥有数据的所有权，`fInfo` 中的指针指向它们。

### `SkPDFGradientShader::KeyHash`

```cpp
struct KeyHash {
    uint32_t operator()(const Key& k) const { return k.fHash; }
};
```

哈希函子，直接返回预计算的哈希值，用于 `SkTHashMap` 中的缓存查找。

### 相等性比较运算符

为 `Key` 和 `SkShaderBase::GradientInfo` 提供了 `operator==`，用于缓存键的精确比较。比较涵盖渐变类型、所有颜色、停靠点、控制点、半径、平铺模式、变换矩阵和边界框。

## 公共 API 函数

### `SkPDFGradientShader::Make`

```cpp
SkPDFIndirectReference Make(SkPDFDocument* doc,
                            SkShader* shader,
                            const SkMatrix& matrix,
                            const SkIRect& surfaceBBox);
```

主入口函数。从 Skia 着色器提取渐变信息，构建缓存键，判断是否需要 Alpha 处理，然后查找或创建对应的 PDF 着色模式。

**流程：**
1. 调用 `make_key()` 从 `SkShader` 提取渐变参数并构建 `Key`
2. 通过 `gradient_has_alpha()` 检测是否包含半透明颜色
3. 调用 `find_pdf_shader()` 进行缓存查找或创建新的 PDF 着色器

## 内部实现细节

### PostScript Type 4 函数生成

对于需要 Type 4（PostScript 计算器）函数的渐变（如扫描渐变或带透视的渐变），模块生成 PostScript 代码：

- **`gradient_function_code`**：生成颜色插值的 PostScript 代码。使用二分查找结构（通过递归的 `write_gradient_ranges`），对梯度停靠点进行二叉树划分，实现 O(log n) 的区间定位。支持 3 分量（RGB）和 4 分量（RGBA premul）模式。
- **`linearCode`**：线性渐变，丢弃 y 坐标，直接使用 x 作为参数 t
- **`radialCode`**：径向渐变，计算 `sqrt(x^2 + y^2)` 作为参数 t
- **`twoPointConicalCode`**：锥形渐变，求解二次方程确定参数 t
- **`sweepCode`**：扫描渐变，使用 `atan` 计算角度

### Stitch 函数路径

当满足以下条件时使用更高效的 PDF Type 2/3 函数（stitch）路径：
- 渐变类型为线性、径向或锥形
- 平铺模式为 Clamp 或 Decal
- 无透视变换
- 无 premultiplied alpha 插值

`gradientStitchCode()` 生成 Type 3 Stitch 函数，将多段渐变拼接为连续的颜色函数。对于仅有两个停靠点的简单情况，直接生成 Type 2 插值函数。

### Alpha 渐变处理

当渐变包含半透明颜色时，采用双层结构：
1. 创建一个不透明的颜色着色器（将所有 Alpha 设为 1.0）
2. 创建一个亮度遮罩（Luminosity SMask），将 Alpha 值映射到灰度
3. 通过 Graphics State 的 SMask 将两者组合

### 透视处理

`split_perspective()` 将包含透视的矩阵分解为仿射部分和透视部分。仿射部分应用于 PDF 的模式矩阵，透视部分在 PostScript 函数中通过 `apply_perspective_to_coordinates()` 实现坐标变换。

### 平铺模式

`tileModeCode()` 生成 PostScript 代码实现 Repeat 和 Mirror 平铺：
- **Repeat**：`t - truncate(t)`，取小数部分映射到 [0,1)
- **Mirror**：基于 `t mod 2` 的奇偶性决定是否翻转

### 缓存机制

通过 `SkPDFDocument::fGradientPatternMap`（`SkTHashMap<Key, SkPDFIndirectReference, KeyHash>`）缓存已生成的渐变着色器。键的哈希通过 `SkChecksum::Hash32` 多级计算。

### 渐变范围优化

`gradient_function_code` 中的范围优化逻辑：
- 跳过退化范围（两端偏移量相同）
- 合并相邻的同色固定区间
- 区分 premul 模式下的颜色比较逻辑

### 相切圆修复

`FixUpRadius()` 检测锥形渐变中内外圆相切的边缘情况，通过微调半径（+0.002）避免渲染异常。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkPDFTypes.h` | PDF 基本类型（字典、数组、间接引用）|
| `SkPDFUtils.h` | PDF 工具函数（矩阵转换、标量输出等）|
| `SkPDFDocumentPriv.h` | 文档私有接口（缓存映射、对象发射）|
| `SkPDFFormXObject.h` | Form XObject 创建（Alpha 蒙版）|
| `SkPDFGraphicState.h` | 图形状态（SMask 创建）|
| `SkPDFResourceDict.h` | 资源字典构建 |
| `SkShaderBase.h` | 着色器基类（渐变信息提取）|
| `SkChecksum.h` | 哈希计算 |
| `SkTHash.h` | 哈希映射容器 |
| `SkMatrix.h` | 变换矩阵 |
| `SkGradient.h` | 渐变效果 |

## 设计模式与设计决策

1. **双路径策略**：根据渐变特性选择 Stitch 函数（Type 2/3）或 PostScript 计算器函数（Type 4）。Stitch 路径更高效且被 PDF 查看器更好支持，但不支持透视和 premul 插值。

2. **缓存去重**：相同参数的渐变在文档级别缓存，避免重复生成。Key 的哈希预计算并存储在 `fHash` 字段中。

3. **Alpha 分离**：PDF 不直接支持带 Alpha 的着色器颜色空间，因此将 Alpha 分离为 SMask 亮度遮罩。这是 PDF 规范限制下的标准做法。

4. **透视分解**：将透视矩阵分解为仿射+透视两部分，使 PDF 的模式矩阵处理仿射变换，PostScript 代码处理透视投影，最大化利用 PDF 原生支持。

5. **二叉树区间查找**：渐变函数代码使用二叉树结构进行停靠点区间定位，将线性搜索的 O(n) 降低为 O(log n)，对多停靠点渐变性能更优。

6. **Premultiplied Alpha 支持**：当渐变使用 premul 插值时，在 PostScript 函数中进行 4 分量（RGBA）插值，最后调用 `unpremul` 转回非预乘格式。

## 性能考量

- **缓存命中**：相同渐变参数直接复用已生成的 PDF 对象，避免重复计算和输出。
- **Stitch 函数优先**：在条件允许时优先使用 Type 2/3 函数，这些函数由 PDF 查看器原生高效执行，无需解释 PostScript 代码。
- **二叉树查找**：PostScript 函数内部使用二叉树结构查找颜色区间，减少运行时条件判断次数。
- **范围优化**：跳过退化范围和相邻同色区间，减少生成的 PostScript 代码量。
- **哈希预计算**：Key 的哈希值在创建时一次性计算，缓存查找时直接使用，避免重复哈希。
- **透视快速路径**：无透视时跳过坐标变换代码，减少 PostScript 函数体积。
- **poppler 兼容性**：代码中多处针对 Preview 11.0 等 PDF 查看器的行为差异进行了适配（如避免使用 `eq` 运算符与某些操作数组合）。

## 相关文件

- `src/pdf/SkPDFShader.h` / `src/pdf/SkPDFShader.cpp` — 着色器调度层，决定使用渐变还是图像着色器
- `src/pdf/SkPDFDevice.h` / `src/pdf/SkPDFDevice.cpp` — PDF 设备，着色器的使用方
- `src/pdf/SkPDFFormXObject.h` — Form XObject 创建
- `src/pdf/SkPDFGraphicState.h` — 图形状态管理（SMask）
- `src/pdf/SkPDFResourceDict.h` — 资源字典构建
- `src/pdf/SkPDFDocumentPriv.h` — 文档私有接口
- `src/shaders/SkShaderBase.h` — 着色器基类定义
