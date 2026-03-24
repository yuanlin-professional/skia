# cp.py - 跨平台文件复制

> 源文件: `gn/cp.py`

## 概述
跨平台的文件/目录复制脚本,用于 GN 构建系统中的文件复制操作。自动处理目标已存在的情况,支持文件和目录。

## 架构位置
Skia GN 构建系统的文件操作工具。

## 内部实现细节
先删除已有目标(文件用 `os.remove`，目录用 `shutil.rmtree`)，然后复制(文件用 `shutil.copy2`，目录用 `shutil.copytree`)。调用 `os.utime` 解决 Ninja 的时间戳问题(ninja#1554)。

## 相关文件
- `gn/rm.py`
