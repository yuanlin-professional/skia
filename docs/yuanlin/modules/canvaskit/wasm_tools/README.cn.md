# wasm_tools - WASM 分析与调试工具

## 概述

`wasm_tools` 目录包含用于分析、调试和运行 CanvasKit WASM 构建产物的工具集。主要包含两类
工具：GM/单元测试的浏览器运行页面、以及 WASM SIMD 指令分析工具。

`gms.html` 和 `viewer.html` 是用于在浏览器中运行 CanvasKit 的 GM（图形正确性）测试和
Skia Viewer 的 HTML 入口页面。开发者可以通过这些页面加载本地编译的 WASM 二进制，在浏览器
环境中调试特定的 GM 测试或查看 Skia 绘制示例。

`SIMD/` 子目录包含用于检测和验证 WASM SIMD 优化的工具。WASM SIMD（Single Instruction,
Multiple Data）是 WebAssembly 的向量化扩展，能够显著加速图形运算中的数学计算（如向量加法、
矩阵乘法、颜色混合等）。这些工具通过分析编译产物中的 SIMD 指令来验证 Emscripten 是否
成功将 Skia 的 SIMD 代码（基于 `skvx` 库）编译为 WASM SIMD 操作。

## 架构图

```
+---------------------------------------------------+
|              wasm_tools 工具集                      |
+---------------------------------------------------+
|                                                   |
|  +---------------------------------------------+ |
|  | 浏览器运行工具                                | |
|  |                                             | |
|  |  gms.html                                   | |
|  |  - 加载 wasm_gm_tests.js/wasm              | |
|  |  - 运行选定的 GM 测试                        | |
|  |  - 显示绘制结果                              | |
|  |                                             | |
|  |  viewer.html                                | |
|  |  - 加载 canvaskit.js/wasm                   | |
|  |  - Skia Viewer 浏览器端                      | |
|  +---------------------------------------------+ |
|                                                   |
|  +---------------------------------------------+ |
|  | SIMD/ (SIMD 指令分析)                        | |
|  |                                             | |
|  |  simd_float_capabilities.cpp                | |
|  |  - 测试 float SIMD 操作                     | |
|  |  - skvx::Vec<4, float> 向量化               | |
|  |                                             | |
|  |  simd_int_capabilities.cpp                  | |
|  |  - 测试 int SIMD 操作                       | |
|  |  - skvx::Vec<N, int> 向量化                 | |
|  |                                             | |
|  |  build_simd_test.sh                         | |
|  |  - 编译 SIMD 测试程序                        | |
|  |  - 使用 wasm2wat 反汇编                      | |
|  |                                             | |
|  |  simd_test.sh                               | |
|  |  - 运行 SIMD 检测                           | |
|  |                                             | |
|  |  wasm_simd_types.txt                        | |
|  |  - WASM SIMD 指令类型列表                    | |
|  +---------------------------------------------+ |
+---------------------------------------------------+
```

## 目录结构

```
wasm_tools/
|-- gms.html                        # GM 测试浏览器运行页面
|-- viewer.html                     # Skia Viewer 浏览器端页面
|
|-- SIMD/                           # WASM SIMD 分析工具
|   |-- build_simd_test.sh          # 编译 SIMD 测试并分析输出
|   |-- simd_test.sh                # 运行 SIMD 检测脚本
|   |-- simd_float_capabilities.cpp # 浮点 SIMD 操作测试
|   |-- simd_int_capabilities.cpp   # 整数 SIMD 操作测试
|   |-- wasm_simd_types.txt         # WASM SIMD 指令参考列表
|   |-- .gitignore                  # Git 忽略规则
```

## 关键类与函数

### GM 测试运行 (gms.html)

```
使用方式：
1. make gm_tests          # 编译 GM 测试
2. make single-gm         # 启动本地服务器
3. 访问 http://localhost:8000/wasm_tools/gms.html
4. 在页面上选择并运行特定 GM 测试
```

### SIMD 分析工具 (SIMD/)

```
使用方式：
1. 取消注释 simd_float_capabilities.cpp 中想测试的操作
2. 运行 ./build_simd_test.sh simd_float_capabilities.cpp
3. 查看输出中是否包含预期的 WASM SIMD 指令

SIMD 操作分类标注：
  //GOOD              - 已自动编译为 WASM SIMD
  //GOOD (FIXED)      - 需要特殊 intrinsic，已在 SkVx.h 中修复
  //not available      - 无对应 WASM SIMD 操作
  //N/A               - 不适用于此数据类型
  //???               - 需要进一步研究
```

### SIMD 测试代码示例 (simd_float_capabilities.cpp)

```cpp
#include "src/base/SkVx.h"
int main() {
    auto vec1 = skvx::Vec<4, float>({11.f, -22.f, 33.f, -44.f});
    auto vec2 = skvx::Vec<4, float>({-.5f, 100.5f, 100.5f, -.5f});

    // vec1 = vec1 + vec2;  // GOOD - 编译为 f32x4.add
    // vec1 = vec1 * vec2;  // GOOD - 编译为 f32x4.mul
    // auto r = min(vec1, vec2);  // GOOD - 编译为 f32x4.min
}
```

## 依赖关系

- **wasm2wat**: WebAssembly Binary Toolkit 的反汇编工具（版本 1.0.13）
- **Emscripten**: WASM 编译器（用于 SIMD 测试编译）
- **skvx (SkVx.h)**: Skia 的跨平台 SIMD 向量库
- **wasm_gm_tests**: 编译后的 GM 测试 WASM 二进制
- **Python HTTP 服务器**: `tools/serve_wasm.py`

## 设计模式分析

### 编译产物分析模式
SIMD 工具采用"编译-反汇编-检查"的分析流程：将 C++ SIMD 代码编译为 WASM，然后使用
`wasm2wat` 反汇编，通过文本搜索确认是否生成了预期的 SIMD 指令。这种方式能精确地验证
编译器优化的效果。

### 标注驱动测试
SIMD 测试文件使用注释标注（`//GOOD`、`//not available` 等）记录每个操作的 SIMD 支持
状态，既是测试代码也是参考文档。

### 本地优先调试
`gms.html` 提供了在浏览器中直接调试 GM 测试的能力，跳过 CI 系统的反馈延迟，支持快速
迭代的开发工作流。

## 数据流

```
SIMD 分析流程:
  simd_*_capabilities.cpp
       |
       v
  build_simd_test.sh ----> Emscripten 编译 (SIMD 启用)
       |
       v
  输出 .wasm 文件
       |
       v
  wasm2wat ----> 生成 .wat 文本格式
       |
       v
  搜索 SIMD 指令 (v128.*, f32x4.*, i32x4.* 等)
       |
       v
  输出检测结果

GM 调试流程:
  compile_gm.sh ----> wasm_gm_tests.js + .wasm
       |
       v
  serve_wasm.py ----> http://localhost:8000
       |
       v
  gms.html 加载并执行 ----> canvas 绘制结果
```

## 相关文档与参考

- **WASM SIMD 提案**: https://github.com/WebAssembly/simd
- **WASM SIMD 指令参考**: https://github.com/WebAssembly/simd/blob/master/proposals/simd/SIMD.md
- **wasm2wat (WABT)**: https://github.com/WebAssembly/wabt
- **Skia skvx 向量库**: `src/base/SkVx.h`
- **LLVM WASM SIMD intrinsics**: `clang/lib/Headers/wasm_simd128.h`
- **GM 测试编译**: `compile_gm.sh`
- **GM 运行工具**: `tools/run-wasm-gm-tests/`
