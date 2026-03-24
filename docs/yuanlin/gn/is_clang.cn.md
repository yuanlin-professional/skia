# is_clang.py - Clang 编译器检测

> 源文件: `gn/is_clang.py`

## 概述
检测指定的 C 和 C++ 编译器是否为 Clang,输出 `true` 或 `false`。

## 架构位置
Skia GN 构建系统的编译器检测工具。

## 公共 API 函数
无,通过命令行执行: `is_clang.py <cc> <cxx>`

## 内部实现细节
对两个编译器分别执行 `--version`，检查输出中是否包含 `clang` 字符串。

## 相关文件
- GN BUILDCONFIG.gn
