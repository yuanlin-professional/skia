# public_headers_warnings_check - 公共头文件警告检查

> 源文件: `tools/public_headers_warnings_check.cpp`

## 概述

`public_headers_warnings_check.cpp` 是一个极简的编译检查文件,仅包含 `#include "skia.h"`,用于验证 Skia 的公共头文件在严格编译警告设置下不会产生警告。

## 架构位置

属于 Skia 的构建质量保证工具。

## 内部实现细节

仅 1 行有效代码(`#include "skia.h"`)。通过编译此文件并启用严格警告来检测公共头文件中的问题。

## 依赖关系

- `skia.h` - Skia 统一公共头文件

## 相关文件

- Skia 的公共 API 头文件
