# compile_sksl_tests.py - SkSL 测试编译器

> 源文件: `gn/compile_sksl_tests.py`

## 概述
批量编译 SkSL 测试文件到多种目标语言(GLSL、Metal、HLSL、SPIR-V、WGSL、SkRP、Stage),使用 worklist 机制高效调用 `skslc` 编译器。

## 架构位置
Skia SkSL 构建工具链的核心编译脚本。

## 公共 API 函数
无,作为构建脚本执行。

## 内部实现细节
支持 `--settings` 和 `--nosettings` 两种模式。默认启用批量编译(`batchCompile=True`)将所有输入合并为单个 worklist。每种语言输出不同扩展名(`.glsl`、`.metal`、`.hlsl`、`.asm.frag`、`.wgsl` 等)。

## 依赖关系
- `skslc` 编译器工具

## 相关文件
- `gn/minify_sksl_tests.py`
