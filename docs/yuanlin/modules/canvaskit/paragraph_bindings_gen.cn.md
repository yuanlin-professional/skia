# CanvasKit 段落绑定生成代码 (paragraph_bindings_gen)

> 源文件: `modules/canvaskit/paragraph_bindings_gen.cpp`

## 概述

`paragraph_bindings_gen.cpp` 是 CanvasKit 中一个自动生成绑定代码的概念验证（POC）文件。它使用 Emscripten 的 `embind` 机制，将 Skia 段落排版模块（skparagraph）中的 C++ 枚举类型暴露给 JavaScript/WebAssembly 环境。该文件定义了文本排版所需的各种枚举常量，包括文本对齐方式、字体样式、文本方向等，是 CanvasKit 文本功能的基础配置层。

## 架构位置

该文件位于 CanvasKit 模块中，作为 Skia 文本排版子系统（skparagraph）与 WebAssembly 之间的桥梁。它属于绑定层的一部分，是更自动化代码生成流程的实验性实现。与手动编写的 `paragraph_bindings.cpp` 不同，该文件仅负责枚举绑定，不涉及类或函数的绑定。

```
CanvasKit (WebAssembly)
  └── paragraph_bindings_gen.cpp  ← 枚举绑定（自动生成 POC）
  └── paragraph_bindings.cpp      ← 主段落绑定（手动编写）
      └── skparagraph 模块 (C++)
          └── DartTypes.h / Paragraph.h
```

## 主要类与结构体

该文件不定义自定义类或结构体，而是通过 `EMSCRIPTEN_BINDINGS(ParagraphGen)` 宏导出以下枚举：

| 枚举名称 | C++ 源类型 | 用途 |
|---------|-----------|------|
| `Affinity` | `para::Affinity` | 光标亲和性（上游/下游） |
| `DecorationStyle` | `para::TextDecorationStyle` | 文本装饰样式（实线/双线/虚线等） |
| `FontSlant` | `SkFontStyle::Slant` | 字体倾斜度（直立/斜体/倾斜） |
| `FontWeight` | `SkFontStyle::Weight` | 字体粗细（从 Invisible 到 ExtraBlack） |
| `FontWidth` | `SkFontStyle::Width` | 字体宽度（从 UltraCondensed 到 UltraExpanded） |
| `PlaceholderAlignment` | `para::PlaceholderAlignment` | 占位符对齐方式 |
| `RectHeightStyle` | `para::RectHeightStyle` | 矩形高度计算策略 |
| `RectWidthStyle` | `para::RectWidthStyle` | 矩形宽度计算策略 |
| `TextAlign` | `para::TextAlign` | 文本水平对齐方式 |
| `TextBaseline` | `para::TextBaseline` | 文本基线类型 |
| `TextDirection` | `para::TextDirection` | 文本方向（LTR/RTL） |
| `TextHeightBehavior` | `para::TextHeightBehavior` | 文本高度行为控制 |
| `LineBreakType` | `SkUnicode::LineBreakType` | 换行类型（软换行/硬换行） |

### 枚举值详细列表

**Affinity（亲和性）**:
- `Upstream` — 光标偏向前方字符
- `Downstream` — 光标偏向后方字符

**DecorationStyle（装饰样式）**:
- `Solid` — 实线
- `Double` — 双线
- `Dotted` — 点线
- `Dashed` — 虚线
- `Wavy` — 波浪线

**FontWeight（字体粗细）**:
- 从 `Invisible`（最轻）到 `ExtraBlack`（最重），共 11 个级别
- 包括常用的 `Thin`(100)、`Light`(300)、`Normal`(400)、`Medium`(500)、`Bold`(700)、`Black`(900)

**FontWidth（字体宽度）**:
- 从 `UltraCondensed` 到 `UltraExpanded`，共 9 个级别
- `Normal` 为默认宽度

**TextAlign（文本对齐）**:
- `Left` / `Right` / `Center` / `Justify` — 绝对对齐方式
- `Start` / `End` — 与文本方向相关的相对对齐方式

**TextHeightBehavior（文本高度行为）**:
- `All` — 默认行为
- `DisableFirstAscent` — 禁用首行上升
- `DisableLastDescent` — 禁用末行下降
- `DisableAll` — 全部禁用

## 公共 API 函数

该文件不导出函数，仅导出枚举常量。所有枚举值在 JavaScript 端以命名常量形式访问，例如：

```javascript
// JavaScript 端用法
CanvasKit.TextAlign.Left
CanvasKit.FontWeight.Bold
CanvasKit.TextDirection.RTL
```

## 内部实现细节

- 使用 `namespace para = skia::textlayout` 别名简化段落命名空间引用
- 所有绑定包含在单一 `EMSCRIPTEN_BINDINGS(ParagraphGen)` 块中
- 枚举的 JavaScript 名称与 C++ 值之间的映射是显式的、一对一的
- 文件注释指出这是"更自动化绑定代码生成的 POC 的一部分"，暗示未来可能被自动生成工具替代
- `FontWeight` 和 `FontWidth` 枚举来自 `SkFontStyle` 类的嵌套枚举，而非段落模块自身的类型，说明段落绑定需要跨模块引用 Skia 核心字体样式
- `LineBreakType` 来自 `SkUnicode` 模块，体现了文本排版对 Unicode 处理的依赖
- 枚举值的 JavaScript 名称省略了 C++ 前缀和后缀（如 `kUpright_Slant` 简化为 `Upright`），遵循 Web 开发的命名惯例

### Emscripten 绑定机制

`emscripten::enum_<T>` 模板函数的工作方式：
1. 创建一个名为指定字符串的 JavaScript 对象（如 `"Affinity"`）
2. 每个 `.value("name", cppValue)` 调用在该对象上创建一个属性
3. 在 JavaScript 端，枚举值是整数，可直接作为函数参数传递
4. 类型检查仅在 TypeScript 层通过 `index.d.ts` 中的 opaque 类型实现

## 依赖关系

| 依赖项 | 说明 |
|-------|------|
| `modules/skparagraph/include/DartTypes.h` | 段落排版枚举定义 |
| `modules/skparagraph/include/Paragraph.h` | 段落排版核心类 |
| `modules/skunicode/include/SkUnicode.h` | Unicode 处理（LineBreakType） |
| `<emscripten/bind.h>` | Emscripten 绑定基础设施 |

## 设计模式与设计决策

- **枚举映射模式**: 使用 `emscripten::enum_<>` 模板逐一映射 C++ 枚举值到 JavaScript 命名常量，保持类型安全
- **命名策略**: JavaScript 端名称采用简洁的 PascalCase（如 `FontWeight`, `TextAlign`），而非 C++ 端的命名空间限定名
- **POC 分离**: 将自动生成代码与手动编写的绑定分离在不同文件中，便于将来替换。文件名中的 `_gen` 后缀暗示其可自动生成的性质
- **值不变**: 枚举值采用 `.value()` 方法逐个定义，确保 JS 端获得与 C++ 完全一致的常量
- **跨模块枚举聚合**: 该文件聚合了来自三个不同模块的枚举（skparagraph、SkFontStyle、SkUnicode），为 JS 端提供了统一的段落排版枚举访问点
- **宏块封装**: 使用 `EMSCRIPTEN_BINDINGS(ParagraphGen)` 而非与 `paragraph_bindings.cpp` 中的 `EMSCRIPTEN_BINDINGS(Paragraph)` 合并，保持了模块化和独立编译的灵活性
- **无函数导出**: 刻意只导出枚举而不导出函数或类，体现了"枚举绑定可以自动生成而类/函数绑定需要手动编写"的设计理念

## 性能考量

- 枚举绑定在编译时确定，运行时无性能开销。Emscripten 在模块初始化时一次性创建所有枚举对象，后续访问仅为简单的属性读取
- 所有枚举以整数形式在 JS/WASM 边界传递，不涉及字符串转换或复杂序列化。这是 Emscripten 枚举绑定的固有特性
- 文件体积小（约 106 行），对最终 WASM 包大小的影响微乎其微
- 枚举值在 JavaScript 端是不可变的常量对象，适合被 JavaScript 引擎内联优化
- 相比在每次调用时传递字符串并在 C++ 端解析，整数枚举避免了字符串比较的开销
- 该文件中的枚举被 `paragraph_bindings.cpp` 和 `paragraph.js` 高频使用，因此选择在独立文件中预先绑定而非在运行时动态查找是合理的优化决策

### 与字符串常量的对比

一种替代方案是在 JS 端使用字符串常量（如 `"left"`, `"right"`）并在 C++ 端解析。当前的整数枚举方案有以下优势：

1. **类型安全**: TypeScript 定义文件中可以对枚举值进行严格类型检查
2. **零转换开销**: 整数值直接传递，无需字符串到枚举的转换
3. **代码体积**: 整数常量比字符串字面量更紧凑
4. **一致性**: 与 C++ 端的枚举值保持一对一映射，避免名称不匹配的 bug

## 相关文件

- `modules/canvaskit/paragraph_bindings.cpp` — 段落排版的主要绑定实现，包含类和函数绑定
- `modules/skparagraph/include/DartTypes.h` — 段落枚举类型的 C++ 定义（Affinity, TextAlign, TextDirection 等）
- `modules/skparagraph/include/Paragraph.h` — 段落排版核心类定义（RectHeightStyle, RectWidthStyle 等）
- `include/core/SkFontStyle.h` — 字体样式枚举定义（Weight, Width, Slant）
- `modules/skunicode/include/SkUnicode.h` — Unicode 处理接口（LineBreakType）
- `modules/canvaskit/canvaskit_bindings.cpp` — CanvasKit 核心绑定
- `modules/canvaskit/paragraph.js` — 段落功能的 JavaScript 辅助层
- `modules/canvaskit/npm_build/types/index.d.ts` — TypeScript 类型定义中对应的枚举类型声明
- `modules/canvaskit/paragraph_bindings_gen.cpp` 中绑定的枚举在 JS 端的最终访问方式为 `CanvasKit.<EnumName>.<ValueName>`，如 `CanvasKit.TextAlign.Center`
- 若需新增段落排版相关枚举，应在此文件中添加对应的 `enum_<>` 绑定，并在 `index.d.ts` 中添加对应的 TypeScript 类型声明
- `modules/canvaskit/skottie_bindings.cpp` — 也使用了部分相同的段落排版枚举（如 TextAlign、TextDirection），用于 Skia Lottie 动画的文本属性
