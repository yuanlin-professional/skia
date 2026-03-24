# make_gm_gni.py - GM 源文件列表生成器

> 源文件: `gn/make_gm_gni.py`

## 概述
扫描 `gm/` 目录下的所有 C/C++ 源文件,生成 `gm.gni` 文件供 GN 构建系统使用。

## 架构位置
Skia 构建系统的辅助脚本。

## 公共 API 函数
无,作为脚本直接执行。

## 内部实现细节
使用 `glob.glob('../gm/*.c*')` 匹配所有 C/C++ 文件,排序后写入 GNI 文件格式。

## 依赖关系
Python 标准库 os, glob。

## 相关文件
- `gn/gm.gni`: 生成的输出文件
