# WASM SIMD 整数能力测试 (simd_int_capabilities)

> 源文件: `modules/canvaskit/wasm_tools/SIMD/simd_int_capabilities.cpp`

## 概述

`simd_int_capabilities.cpp` 是一个测试和文档工具，用于评估 WebAssembly SIMD 对 Skia `skvx::Vec<4, int>` 整数向量操作的支持状况。文件与 `simd_float_capabilities.cpp` 配对，覆盖了所有常用的 4 路整数 SIMD 操作，通过注释标注每个操作的 WASM SIMD 兼容性。所有操作代码默认被注释掉，按需取消注释后编译检查。

## 架构位置

该文件位于 `wasm_tools/SIMD/` 目录下，是 CanvasKit 开发工具链的一部分，不参与生产构建。

```
开发者
  └── 取消注释目标操作
      └── build_simd_test.sh simd_int_capabilities.cpp
          └── Emscripten 编译
              └── WASM 输出（检查 SIMD 指令）
                  └── skvx::Vec<4, int> ← SkVx.h
```

## 主要类与结构体

无。使用 `skvx::Vec<4, int>` 作为测试向量类型。

## 公共 API 函数

无公共 API。`main()` 函数作为编译入口。

## 内部实现细节

### 操作兼容性分类

**GOOD（自动 SIMD 化）**:
- 算术: `+`, `-`, `*`
- 位运算: `^`, `&`, `|`
- 逻辑: `!`, `-`（取反）, `~`（按位取反）
- 移位: `<<`, `>>`
- 比较: `==`, `!=`, `<=`, `>=`, `<`, `>`
- 混洗: `shuffle<2,1,0,3>`

**GOOD (FIXED)（需要 SkVx.h 中的专用内置函数）**:
- `skvx::any`, `skvx::all`
- `skvx::max`, `skvx::min`
- `skvx::abs`

**not available in wasm**:
- `skvx::pow`, `skvx::atan`
- `ceil`, `skvx::floor`, `skvx::sqrt`
- `skvx::sin`, `skvx::cos`, `skvx::tan`
- `skvx::join`
- `skvx::fma`

**N/A（类型不适用）**:
- 整数除法: `/`
- `skvx::trunc`, `skvx::round`
- `skvx::rcp`, `skvx::rsqrt`
- `skvx::fract`

**???（待进一步研究）**:
- `skvx::lrint`
- `skvx::if_then_else`

### 与浮点版本的关键差异

整数 SIMD 相比浮点 SIMD 有更好的位运算支持（`^`, `&`, `|`, `!`, `~`, `<<`, `>>`），但缺少除法、平方根等数学运算的 SIMD 支持。`any` 和 `all` 在整数版本中标记为 GOOD (FIXED)，而在浮点版本中标记为 N/A。

### 使用流程

与 `simd_float_capabilities.cpp` 相同：取消注释 → 编译 → 检查 WASM 输出中的 SIMD 指令。

## 依赖关系

| 依赖项 | 说明 |
|-------|------|
| `src/base/SkVx.h` | Skia 的 SIMD 向量库 |
| `<emscripten.h>` | Emscripten 编译环境 |
| `build_simd_test.sh` | 编译和分析脚本 |

## 设计模式与设计决策

- **配对测试**: 与 `simd_float_capabilities.cpp` 配对，分别测试浮点和整数类型
- **文档即代码**: 注释直接标注每个操作的 SIMD 状态
- **选择性编译**: 通过注释控制测试范围

## 性能考量

- 整数 SIMD 操作覆盖面广（算术、位运算、比较、移位均支持），是 Skia 像素处理的性能基础
- 位运算全面支持 WASM SIMD，适合颜色分量操作
- 整数除法不支持 SIMD，需要标量回退
- `any`/`all` 通过 SkVx.h 中的修复支持 SIMD 化，用于条件分支优化

## 相关文件

- `modules/canvaskit/wasm_tools/SIMD/simd_float_capabilities.cpp` — 浮点 SIMD 能力测试
- `src/base/SkVx.h` — Skia SIMD 向量库
- `modules/canvaskit/wasm_tools/SIMD/build_simd_test.sh` — 编译测试脚本
