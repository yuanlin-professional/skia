# Zip Utils - 压缩解压工具

> 源文件: `infra/bots/zip_utils.py`

## 概述

`zip_utils.py` 提供了保留文件权限的 zip 压缩和解压功能。它支持文件过滤（通过 glob 模式跳过特定文件）、跨平台路径处理，以及符号链接的优雅跳过。

## 架构位置

位于 `infra/bots/` 目录，是 Skia CI/CD 基础设施的文件打包工具，被构建和部署流程使用。

## 主要类与结构体

无类定义。

## 公共 API 函数

- **`filtered(names, to_skip)`**: 使用 glob 模式过滤文件/目录名列表
- **`zip(target_dir, zip_file, to_skip=None)`**: 将目录压缩为 zip 文件
- **`unzip(zip_file, target_dir)`**: 解压 zip 文件到目标目录

## 内部实现细节

1. **`zip` 函数**:
   - 使用 `os.walk` 遍历目录树，`topdown=True` 允许原地修改 `d[:]` 实现目录过滤
   - 手动构造 `ZipInfo` 对象以保存文件权限（`external_attr = perms << 16`）
   - Windows 路径分隔符自动替换为 POSIX 格式
   - 符号链接读取失败时优雅跳过（打印警告）
   - 使用 `ZIP_DEFLATED` 压缩算法
2. **`unzip` 函数**:
   - 自动创建目标目录
   - 还原文件权限（`external_attr >> 16`）
   - Windows 路径分隔符反向替换
   - 通过路径末尾 `os.path.sep` 判断目录条目

## 依赖关系

- Python 标准库: `fnmatch`, `ntpath`, `os`, `posixpath`, `zipfile`

## 设计模式与设计决策

- 权限保持：通过 `ZipInfo.external_attr` 存储和恢复 Unix 文件权限
- 跨平台兼容：显式处理 Windows 和 POSIX 路径分隔符差异
- 防御性编程：处理符号链接和不存在的目录等边界情况
- 使用 `allowZip64=True` 支持大文件

## 性能考量

- 使用 `ZIP_DEFLATED` 压缩减小传输大小
- 按文件逐一处理，内存占用与单个文件大小成正比

## 相关文件

- `infra/bots/zip_utils_test.py`: 对应的单元测试
- `infra/bots/utils.py`: 通用工具（`tmp_dir` 等）
