# SkSL WGSL 验证器 (SkSLWGSLValidator)

> 源文件:
> - `src/sksl/codegen/SkSLWGSLValidator.h`
> - `src/sksl/codegen/SkSLWGSLValidator.cpp`

## 概述

`SkSLWGSLValidator` 是一个轻量级的 WGSL 代码验证工具，使用 Google Tint 编译器来验证 SkSL WGSL 代码生成器生成的 WGSL 代码是否有效。它提供两种验证模式：静默模式和详细模式（在 debug 构建中通过断言报告错误）。

## 架构位置

该验证器位于 SkSL 代码生成层，作为 WGSL 代码生成器的后处理步骤使用。

```
SkSL Program -> WGSLCodeGenerator -> WGSL 文本 -> WGSLValidator -> 验证结果
```

## 主要类与结构体

本模块不定义任何类，只提供两个独立的验证函数。

## 公共 API 函数

- **`ValidateWGSL(reporter, wgsl, warnings)`** -- 验证 WGSL 代码。如果无效，通过 `ErrorReporter` 报告错误。用于测试的 golden 文件输出。

- **`ValidateWGSLVerbose(reporter, wgsl, warnings)`** -- 详细验证模式。如果无效，通过 `SkDEBUGFAIL` 报告错误并附带完整的 WGSL 源码，方便调试。

**参数：**
- `reporter` -- SkSL 错误报告器
- `wgsl` -- 待验证的 WGSL 代码文本
- `warnings` -- 输出参数，接收 Tint 编译器的警告信息

**返回值：** `true` 表示 WGSL 有效，`false` 表示包含错误。

## 内部实现细节

### Tint 集成

验证器使用 Google Tint（WebGPU 的参考编译器）解析和验证 WGSL 代码：

1. 配置 Tint 的 WGSL Reader Options，启用 Skia 可能依赖的可选特性：
   - `ChromiumExperimentalPixelLocal` -- Chromium 实验性像素局部存储
   - `ChromiumExperimentalFramebufferFetch` -- Chromium 实验性帧缓冲获取
   - `DualSourceBlending` -- 双源混合
   - `F16` -- 半精度浮点支持
   - `UnrestrictedPointerParameters` -- 无限制指针参数

2. 调用 `tint::wgsl::reader::Parse` 解析 WGSL 源码。
3. 检查 `program.Diagnostics().ContainsErrors()` 判断是否有效。
4. 非错误的诊断信息（警告）通过 `warnings` 参数返回。

### 两种错误报告模式

- **静默模式**（`ValidateWGSL`）：将错误附带完整 WGSL 源码报告给 `ErrorReporter`。适用于测试输出。
- **详细模式**（`ValidateWGSLVerbose`）：通过 `SkDEBUGFAIL` 触发断言，附带格式化的诊断信息和源码。适用于开发调试。

## 依赖关系

**内部依赖：**
- `SkSLErrorReporter` -- 错误报告
- `SkSLPosition` -- 源码位置

**外部依赖（关键）：**
- `tint/tint.h` -- Google Tint WGSL 编译器
- `src/tint/lang/wgsl/reader/options.h` -- Tint WGSL Reader 配置
- `src/tint/lang/wgsl/enums.h` -- Tint WGSL 扩展枚举

## 设计模式与设计决策

1. **委托给 Tint**：验证逻辑完全委托给 Tint 编译器，确保验证结果与实际的 WebGPU 实现一致。
2. **可选特性预注册**：在验证前注册 Skia 可能使用的所有 WGSL 可选特性，避免因特性未启用导致的误报。
3. **双模式设计**：开发时使用 Verbose 模式快速定位问题，测试中使用静默模式生成可比对的输出。

## 性能考量

- **验证开销**：Tint 解析和验证需要一定时间，通常只在测试和开发中启用。
- **按需调用**：验证器通过 `ValidateWGSLProc` 回调传递给 WGSL 代码生成器，可选择性启用。

## 相关文件

- `src/sksl/codegen/SkSLWGSLCodeGenerator.h` -- WGSL 代码生成器（使用本验证器）
- `src/sksl/SkSLErrorReporter.h` -- 错误报告接口
