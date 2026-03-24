# CanvasKit Bidi Bindings Gen - Unicode 双向文本绑定生成

> 源文件: `modules/canvaskit/bidi_bindings_gen.cpp`

## 概述

bidi_bindings_gen.cpp 是 CanvasKit 模块中用于将 SkUnicode 的 `CodeUnitFlags` 枚举绑定到 JavaScript 的 Emscripten 绑定文件。它是更自动化的绑定代码生成概念验证（POC）的一部分，当前手动定义了 Unicode 代码单元标志的枚举映射，使 JavaScript 代码能够访问 Skia 内部的 Unicode 文本属性分类。

## 架构位置

该文件属于 CanvasKit 的 C++ Emscripten 绑定层，专门处理 Unicode/Bidi（双向文本）相关的类型导出。

```
JavaScript (CanvasKit.CodeUnitFlags)
  └── Emscripten EMSCRIPTEN_BINDINGS
        └── bidi_bindings_gen.cpp ← 本文件
              └── SkUnicode::CodeUnitFlags (Skia C++)
```

## 主要类与结构体

本文件不定义新的类，而是通过 Emscripten 绑定导出已有的枚举。

### 导出的枚举：`CodeUnitFlags`

| JavaScript 名称 | C++ 值 | 说明 |
|---|---|---|
| `NoCodeUnitFlag` | `SkUnicode::CodeUnitFlags::kNoCodeUnitFlag` | 无特殊标志 |
| `Whitespace` | `SkUnicode::CodeUnitFlags::kPartOfWhiteSpaceBreak` | 属于空白断行区域 |
| `Space` | `SkUnicode::CodeUnitFlags::kPartOfIntraWordBreak` | 属于词内断行区域 |
| `Control` | `SkUnicode::CodeUnitFlags::kControl` | 控制字符 |
| `Ideographic` | `SkUnicode::CodeUnitFlags::kIdeographic` | 表意文字（如 CJK） |

## 公共 API 函数

本文件不定义函数，仅导出枚举值。在 JavaScript 中通过 `CanvasKit.CodeUnitFlags.Whitespace` 等方式访问。

## 内部实现细节

### Emscripten 绑定机制

使用 `EMSCRIPTEN_BINDINGS` 宏和 `enum_<T>` 模板进行枚举绑定：

```cpp
EMSCRIPTEN_BINDINGS(CodeUnitsGen) {
    enum_<SkUnicode::CodeUnitFlags>("CodeUnitFlags")
        .value("NoCodeUnitFlag", SkUnicode::CodeUnitFlags::kNoCodeUnitFlag)
        .value("Whitespace", SkUnicode::CodeUnitFlags::kPartOfWhiteSpaceBreak)
        // ...
}
```

`EMSCRIPTEN_BINDINGS` 宏在 WASM 模块加载时自动注册绑定，绑定名称 `"CodeUnitsGen"` 仅用于内部标识。

### 名称映射

JavaScript 侧使用了简化的名称：
- `kPartOfWhiteSpaceBreak` -> `Whitespace`
- `kPartOfIntraWordBreak` -> `Space`

这使得 JavaScript API 更加简洁直观。

## 依赖关系

- **Skia Unicode 模块**：`modules/skunicode/include/SkUnicode.h`（`SkUnicode::CodeUnitFlags`）
- **Emscripten 绑定**：`<emscripten/bind.h>`（`enum_`、`EMSCRIPTEN_BINDINGS`）

## 设计模式与设计决策

1. **代码生成 POC**：文件注释指出这是自动绑定代码生成的概念验证，目前可手动编辑。未来可能由工具自动生成此类文件。

2. **枚举值重命名**：JavaScript 侧的名称更简短，遵循 CanvasKit 的命名风格而非 Skia C++ 的 `kPrefix` 风格。

3. **最小绑定**：仅导出必要的枚举值，避免暴露不需要的内部实现细节。

## 性能考量

- 枚举绑定在模块加载时一次性注册，无运行时开销
- 枚举值作为整数常量在 JavaScript 和 C++ 之间传递，零拷贝

## 相关文件

- `modules/canvaskit/externs.js` - JavaScript 外部声明（包含 CodeUnitFlags 声明）
- `modules/skunicode/include/SkUnicode.h` - SkUnicode::CodeUnitFlags 定义
- `modules/canvaskit/canvaskit_bindings.cpp` - CanvasKit 主绑定文件
- `modules/canvaskit/paragraph_bindings.cpp` - 段落排版绑定（使用 CodeUnitFlags）
