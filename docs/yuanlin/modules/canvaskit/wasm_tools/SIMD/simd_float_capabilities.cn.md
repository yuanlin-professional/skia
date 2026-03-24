# WASM SIMD 浮点能力测试 (simd_float_capabilities)

> 源文件: `modules/canvaskit/wasm_tools/SIMD/simd_float_capabilities.cpp`

## 概述

`simd_float_capabilities.cpp` 是一个测试和文档工具，用于评估 WebAssembly SIMD 对 Skia `skvx::Vec<4, float>` 浮点向量操作的支持状况。文件中列出了所有常用的 4 路浮点 SIMD 操作，并通过注释标注每个操作的 WASM SIMD 兼容性状态（GOOD / GOOD (FIXED) / not available in wasm / N/A / ???）。所有操作代码默认被注释掉，按需取消注释后通过 `build_simd_test.sh` 编译，即可检查 Emscripten 是否将其编译为 WASM SIMD 指令。

## 架构位置

该文件是 CanvasKit WASM 工具链的开发辅助工具，不参与生产构建。位于 `wasm_tools/SIMD/` 目录下，与 `simd_int_capabilities.cpp` 配对。

```
开发者
  └── 取消注释目标操作
      └── build_simd_test.sh
          └── Emscripten 编译
              └── WASM 输出（检查是否包含 SIMD 指令）
                  └── skvx::Vec<4, float> ← SkVx.h
```

## 主要类与结构体

无。使用 `skvx::Vec<4, float>` 作为测试向量类型。

## 公共 API 函数

无公共 API。`main()` 函数作为编译入口。

## 内部实现细节

### 操作兼容性分类

**GOOD（自动 SIMD 化）**:
- 算术: `+`, `-`, `*`, `/`
- 取反: `-vec`
- 比较: `==`, `!=`, `<=`, `>=`, `<`, `>`
- 混洗: `shuffle<2,1,0,3>`

**GOOD (FIXED)（需要 SkVx.h 中的专用内置函数）**:
- `skvx::max`, `skvx::min`
- `skvx::sqrt`, `skvx::abs`
- `skvx::rcp`（倒数）, `skvx::rsqrt`（倒数平方根）

**not available in wasm（无对应 WASM SIMD 指令）**:
- `skvx::pow`, `skvx::atan`, `ceil`, `skvx::floor`, `skvx::trunc`, `skvx::round`
- `skvx::sin`, `skvx::cos`, `skvx::tan`
- `skvx::join`（可能通过 widening 实现）
- `skvx::fma`（无融合乘加指令）

**N/A（类型不适用）**:
- 位运算: `^`, `&`, `|`, `!`, `~`
- 移位: `<<`, `>>`
- `any`, `all`
- `if_then_else`

**???（待进一步研究）**:
- `skvx::lrint` — 可能通过 `f32x4.convert_i32x4_s` 实现
- `skvx::fract`

### 使用流程

1. 参考 WebAssembly SIMD 提案文档和 LLVM WASM SIMD 头文件
2. 取消注释目标操作行
3. 运行 `./build_simd_test.sh simd_float_capabilities.cpp`
4. 检查输出中是否包含预期的 WASM SIMD 指令

## 依赖关系

| 依赖项 | 说明 |
|-------|------|
| `src/base/SkVx.h` | Skia 的 SIMD 向量库 |
| `<emscripten.h>` | Emscripten 编译环境 |
| `build_simd_test.sh` | 编译和分析脚本 |

## 设计模式与设计决策

- **文档即代码**: 用可执行代码记录每个操作的 SIMD 兼容性，注释即文档
- **选择性编译**: 通过注释/取消注释控制测试范围，避免一次编译所有操作
- **分类标注系统**: 使用清晰的标注（GOOD / GOOD (FIXED) / not available / N/A / ???）分类操作状态

## 性能考量

- **GOOD** 标记的操作可直接受益于 WASM SIMD，获得约 2-4 倍加速
- **GOOD (FIXED)** 标记的操作需要 SkVx.h 中的特殊内置函数才能触发 SIMD 化
- **not available** 标记的操作在 WASM 中会回退到标量实现，是潜在的性能瓶颈
- 三角函数（sin/cos/tan）和幂函数（pow）在 WASM SIMD 中无原生支持

## 相关文件

- `modules/canvaskit/wasm_tools/SIMD/simd_int_capabilities.cpp` — 整数 SIMD 能力测试
- `src/base/SkVx.h` — Skia SIMD 向量库（含 WASM SIMD 内置函数）
- `modules/canvaskit/wasm_tools/SIMD/build_simd_test.sh` — 编译测试脚本
