# Skia GDB 调试辅助工具

## 概述

`tools/gdb` 提供了 GDB（GNU Debugger）的自定义命令扩展，用于在调试 Skia 程序时可视化位图数据。通过加载此模块，开发者可以在 GDB 调试会话中直接查看 SkBitmap 对象的图像内容，极大地简化了图形渲染问题的调试过程。

## 目录结构

```
tools/gdb/
└── bitmap.py    # GDB Python 扩展脚本
```

## 功能说明

### sk_bitmap 命令

在 GDB 中注册自定义命令 `sk_bitmap`，可以将 SkBitmap 变量的内容显示为图像：

```gdb
(gdb) source /path/to/tools/gdb/bitmap.py
(gdb) sk_bitmap myBitmapVariable
```

执行后会弹出一个窗口显示位图内容，支持右键菜单保存为文件。

## 实现原理

### 数据提取

脚本通过 GDB 的 Python API 读取 SkBitmap 对象的内部结构：

```
SkBitmap
└── fPixmap (SkPixmap)
    ├── fPixels    -> 像素数据指针
    ├── fRowBytes  -> 每行字节数
    └── fInfo (SkImageInfo)
        ├── fDimensions -> { fWidth, fHeight }
        ├── fColorType  -> 颜色类型枚举
        └── fAlphaType  -> Alpha 类型枚举
```

### 支持的颜色类型

脚本定义了完整的 Skia 颜色类型枚举：

| 枚举值 | 颜色类型 | 说明 |
|--------|---------|------|
| 0 | unknown | 未知格式 |
| 1 | alpha_8 | 8 位 Alpha |
| 2 | rgb_565 | 16 位 RGB |
| 3 | argb_4444 | 16 位 ARGB |
| 4 | rgba_8888 | 32 位 RGBA |
| 5 | rgbx_8888 | 32 位 RGBX（无 Alpha） |
| 6 | bgra_8888 | 32 位 BGRA |
| 7 | rgba_1010102 | 30 位 RGB + 2 位 Alpha |
| 8 | rgb_101010x | 30 位 RGB |
| 9 | gray_8 | 8 位灰度 |
| 10 | rgba_F16 | 半精度浮点 RGBA |

### Alpha 类型

| 枚举值 | Alpha 类型 | 说明 |
|--------|-----------|------|
| 0 | unknown | 未知 |
| 1 | opaque | 不透明 |
| 2 | premul | 预乘 Alpha |
| 3 | unpremul | 非预乘 Alpha |

### 图像显示

当前支持的格式组合：

- **bgra_8888 + unpremul**: 使用 PIL `"BGRA"` 原始模式
- **bgra_8888 + premul**: 使用 PIL `"BGRa"` 原始模式（预乘 Alpha）

其他格式组合会提示需要添加支持，输出类似：
```
Need to add support for ColorType.rgba_8888 AlphaType.premul.
```

## 依赖项

- **GDB**: 需要带 Python 支持的 GDB
- **Pillow (PIL)**: Python 图像处理库，用于图像显示

```bash
pip install Pillow
```

## 使用步骤

### 1. 加载脚本

```gdb
(gdb) source /path/to/skia/tools/gdb/bitmap.py
```

或在 `~/.gdbinit` 中添加自动加载：

```
source /path/to/skia/tools/gdb/bitmap.py
```

### 2. 在断点处查看位图

```gdb
(gdb) break SkCanvas::drawBitmap
(gdb) run
(gdb) sk_bitmap bitmap
```

### 3. 保存图像

在弹出的图像窗口中右键点击，选择保存选项。

## 技术细节

- 使用 `gdb.selected_inferior().read_memory()` 读取目标进程的像素内存
- 通过 `gdb.selected_frame().read_var()` 获取变量值
- 使用 `Image.frombytes()` 从原始像素数据构建 PIL 图像
- `Image.show()` 使用系统默认图像查看器显示

## 与其他模块的关系

- **include/core/SkBitmap.h**: 被调试的核心位图类
- **include/core/SkImageInfo.h**: SkImageInfo 结构体定义
- **tools/debugger/**: 更全面的 SKP 调试工具（Web 界面）
- **tools/viewer/**: Viewer 应用提供实时渲染调试
