# bitmap.py - GDB SkBitmap 可视化插件

> 源文件: [tools/gdb/bitmap.py](../../tools/gdb/bitmap.py)

## 概述

此 Python 脚本是一个 GDB 调试器扩展，提供了在调试 Skia 代码时可视化 `SkBitmap` 对象内容的能力。通过在 GDB 中加载此脚本，开发者可以使用 `sk_bitmap` 命令将指定的位图变量渲染为图像窗口显示。它通过读取进程内存中的像素数据，使用 Python Imaging Library（PIL/Pillow）将其转换为可显示的图像。

## 架构位置

该脚本属于 Skia 工具层的调试辅助子系统（`tools/gdb/`），是一个 GDB Python 扩展。它直接与 Skia 核心的 `SkBitmap` 内存布局交互，需要了解 `SkBitmap` -> `SkPixmap` -> `SkImageInfo` 的内部结构层级。

## 主要类与结构体

### Python 类

- **`ColorType(Enum)`**：Skia 颜色类型枚举的 Python 映射
  - `unknown=0`, `alpha_8=1`, `rgb_565=2`, `argb_4444=3`, `rgba_8888=4`, `rgbx_8888=5`, `bgra_8888=6`, `rgba_1010102=7`, `rgb_101010x=8`, `gray_8=9`, `rgba_F16=10`

- **`AlphaType(Enum)`**：Skia Alpha 类型枚举的 Python 映射
  - `unknown=0`, `opaque=1`, `premul=2`, `unpremul=3`

- **`sk_bitmap(gdb.Command)`**：GDB 自定义命令类
  - 注册为 `'sk_bitmap'` 命令
  - 属于 `gdb.COMMAND_SUPPORT` 类别
  - 支持文件名补全

## 公共 API 函数

| 函数/命令 | 参数 | 返回值 | 描述 |
|-----------|------|--------|------|
| GDB 命令 `sk_bitmap <var>` | 变量名 | 无（弹出图像窗口） | 在调试器中可视化位图 |

**使用方式**：
```gdb
(gdb) source /path/to/bitmap.py
(gdb) sk_bitmap myBitmapVariable
```

## 内部实现细节

1. **变量读取**：通过 `gdb.selected_frame().read_var(arg)` 获取指定变量的 GDB Value 对象。
2. **类型验证**：检查变量类型（去除 typedef 后）是否为 `'SkBitmap'`。
3. **结构体字段遍历**：按照 SkBitmap 内部结构访问嵌套字段：
   - `val['fPixmap']` -> `pixmap['fPixels']`：像素数据指针
   - `pixmap['fRowBytes']`：行字节步长
   - `pixmap['fInfo']['fDimensions']`：宽高
   - `pixmap['fInfo']['fColorType']`：颜色类型
   - `pixmap['fInfo']['fAlphaType']`：Alpha 类型
4. **内存读取**：通过 `gdb.selected_inferior().read_memory(pixels, row_bytes * height)` 从被调试进程内存读取像素数据。
5. **图像创建**（目前仅支持 `bgra_8888`）：
   - **unpremul**：使用 PIL 的 `"BGRA"` 原始模式
   - **premul**：使用 PIL 的 `"BGRa"` 原始模式（小写 `a` 表示预乘 alpha）
6. **显示**：调用 `image.show()` 弹出系统默认图像查看器。

## 依赖关系

- **GDB Python API**：`gdb` 模块
- **Python 库**：`PIL`（Pillow）或旧版 `Image` 模块
- **Python 标准库**：`enum`
- **运行环境**：带 Python 支持的 GDB 调试器

## 设计模式与设计决策

- **GDB 命令框架**：继承 `gdb.Command` 实现自定义命令，这是 GDB Python API 的标准模式。
- **有限的格式支持**：目前仅支持 `bgra_8888` 颜色类型的两种 alpha 模式。对于不支持的格式，输出提示信息而非崩溃。这是一种渐进式开发策略。
- **PIL 兼容层**：`try/except` 块处理 `PIL.Image` 和独立 `Image` 包的导入差异。
- **模块级自注册**：脚本末尾的 `sk_bitmap()` 调用立即注册 GDB 命令，无需额外配置。
- **内存布局依赖**：直接访问 C++ 对象的字段名（如 `fPixmap`、`fPixels`），与 Skia 源码紧耦合。

## 性能考量

- 从被调试进程读取大量内存（`row_bytes * height`）可能较慢，特别是对大图像。
- `Image.show()` 通常会写入临时文件并启动外部查看器，增加延迟。
- 作为调试工具，性能不是首要考虑因素。
- 右键菜单支持将图像保存到文件，方便离线分析。

## 相关文件

- `include/core/SkBitmap.h`：SkBitmap 类定义
- `include/core/SkPixmap.h`：SkPixmap 结构定义
- `include/core/SkImageInfo.h`：颜色类型和 Alpha 类型枚举
- GDB 的 `.gdbinit` 配置文件（可自动加载此脚本）
