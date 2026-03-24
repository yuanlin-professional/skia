# MSKP Parser - Skia 多页图片文档解析器

> 源文件: `experimental/tools/mskp_parser.py`

## 概述

`mskp_parser.py` 是一个 Python 命令行工具，用于解析 Skia 的 Multi-Picture Document（MSKP）文件格式。该工具可以读取 MSKP 文件的头部信息（版本号、页面数量、页面尺寸及偏移量），并可选地将第一个页面的 SKP 数据提取到单独的文件中。

## 架构位置

该工具位于 `experimental/tools/` 目录下，属于 Skia 的实验性工具集。它是一个独立的辅助脚本，不依赖 Skia 的 C++ 构建系统，主要用于调试和检查 MSKP 文件。

## 主要类与结构体

本文件为脚本形式，未定义类或结构体。核心逻辑通过顶层代码实现。

## 公共 API 函数

- **命令行接口**: `python mskp_parser.py MSKP_FILE [OUTPUT_SKP]`
  - `MSKP_FILE`: 输入的 MSKP 文件路径（必须参数）
  - `OUTPUT_SKP`: 可选的输出路径，用于提取第一个 SKP 页面

## 内部实现细节

1. **魔数验证**: 检查文件头部是否包含 `'Skia Multi-Picture Doc\n\n'` 魔数常量
2. **版本解析**: 使用 `struct.unpack` 读取 4 字节版本号和 4 字节页面计数（`'II'` 格式）
3. **页面遍历**:
   - **版本 1**: 每页 16 字节（8 字节偏移 + 2 个 4 字节浮点尺寸），格式 `'Qff'`
   - **版本 2**: 每页 8 字节（2 个 4 字节浮点尺寸），格式 `'ff'`
4. **SKP 提取**:
   - 版本 2 或单页文件：直接拷贝剩余数据
   - 版本 1 多页文件：使用偏移量差计算第一页大小

## 依赖关系

- Python 标准库: `fileinput`, `sys`, `struct`
- 无外部依赖

## 设计模式与设计决策

- 采用线性脚本模式，适合一次性工具使用场景
- 支持版本 1 和版本 2 两种 MSKP 格式，保持向后兼容性
- 使用 8192 字节块进行文件拷贝，平衡内存使用和 I/O 效率

## 性能考量

- 文件读取使用 8KB 缓冲区分块拷贝，避免大文件一次性加载到内存
- 对于版本 1 的多页文件，仅读取所需的偏移量范围数据

## 相关文件

- `include/core/SkMultiPictureDocument.h`: MSKP 格式的 C++ 定义
- `src/utils/SkMultiPictureDocument.cpp`: MSKP 文件的读写实现
