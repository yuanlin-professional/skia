# RasterWindowContext_win - Windows 光栅化窗口上下文

> 源文件: `tools/window/win/RasterWindowContext_win.cpp`

## 概述

`RasterWindowContext_win` 是 Windows 平台上基于纯 CPU 软件光栅化的窗口上下文实现。它使用 Windows GDI（图形设备接口）的 DIB（设备无关位图）进行像素数据管理，并通过 `StretchDIBits` 将渲染结果呈现到窗口。这是不需要或不支持 GPU 加速时的备用渲染路径。

## 架构位置

- 继承自 `skwindow::internal::RasterWindowContext`
- 由 `skwindow::MakeRasterForWin` 工厂函数创建
- 属于 Skia 窗口工具的 Windows 平台实现层
- 作为匿名命名空间内的类，不直接对外暴露

## 主要类与结构体

### `RasterWindowContext_win`（匿名命名空间）
- 继承自 `RasterWindowContext`
- 成员变量：
  - `fSurfaceMemory` (`SkAutoMalloc`) - 管理 DIB 和像素数据的内存
  - `fBackbufferSurface` (`sk_sp<SkSurface>`) - 后台缓冲区 SkSurface
  - `fWnd` (`HWND`) - Windows 窗口句柄

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `MakeRasterForWin(HWND, unique_ptr<const DisplayParams>)` | 工厂函数，创建光栅化窗口上下文 |
| `getBackbufferSurface()` | 获取后台缓冲区表面 |
| `isValid()` | 检查窗口句柄是否有效 |
| `resize(int, int)` | 调整渲染尺寸 |
| `setDisplayParams(unique_ptr<const DisplayParams>)` | 更新显示参数 |

## 内部实现细节

### 像素缓冲区管理
- `resize()` 方法分配包含 `BITMAPINFOHEADER` 和像素数据的连续内存块
- 使用负 `biHeight` 值创建自顶向下的位图（与 Skia 的绘制方向一致）
- 像素格式为 32 位（`biBitCount = 32`），使用 `BI_RGB` 压缩方式
- 通过 `SkSurfaces::WrapPixels` 将原始像素内存包装为 `SkSurface`

### 帧呈现
- `onSwapBuffers()` 通过 `StretchDIBits` 将 DIB 像素复制到窗口 DC
- 使用 `SRCCOPY` 光栅操作直接复制

## 依赖关系

- `include/core/SkSurface.h` - SkSurface API
- `src/base/SkAutoMalloc.h` - 自动内存管理
- `tools/window/RasterWindowContext.h` - 光栅化基类
- `tools/window/win/WindowContextFactory_win.h` - 工厂声明
- `<Windows.h>` - Win32 GDI API

## 设计模式与设计决策

- **工厂方法模式**: 通过 `MakeRasterForWin` 创建具体实现
- **内存布局优化**: BITMAPINFO 头和像素数据在同一块连续内存中，减少分配次数
- **零拷贝包装**: 像素内存直接被 `SkSurface` 包装，避免不必要的数据复制
- **匿名命名空间**: 隐藏实现细节，仅暴露工厂函数

## 性能考量

- 每次 `resize` 会重新分配整块内存（BITMAPINFO + 像素），这是必要的因为尺寸变化
- `onSwapBuffers` 使用 `StretchDIBits` 进行系统级像素传输，效率取决于 GDI 实现
- 纯 CPU 渲染，适合不需要 GPU 加速的调试和测试场景
- 没有双缓冲或垂直同步机制

## 相关文件

- `tools/window/RasterWindowContext.h` - 光栅化基类
- `tools/window/win/WindowContextFactory_win.h` - 工厂函数声明
- `tools/window/win/GLWindowContext_win.cpp` - GPU 加速替代方案
