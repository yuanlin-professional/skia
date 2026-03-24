# imgcvt - 图像颜色空间转换工具

> 源文件: `tools/imgcvt.cpp`

## 概述

`imgcvt` 是一个图像或 ICC 配置文件的颜色空间转换工具。当输入为 ICC 配置文件时,展示颜色坐标变换;当输入为图像时,使用三种不同的方法(skcms 直接变换、writePixels、draw)将其转换到目标颜色空间并输出 PNG。

## 架构位置

属于 Skia 工具链中的颜色管理调试工具。

## 公共 API 函数

- **`main(argc, argv)`**: 读取输入(图像或 ICC 配置文件),执行转换
- **`write_png()`**: 将 SkImage 编码为 PNG 写入文件

## 内部实现细节

三种转换路径:
1. **skcms 直接变换**: 使用 `skcms_Transform` 原地变换像素数据 -> `transformed-skcms.png`
2. **writePixels**: 通过 SkSurface::writePixels 利用 Skia 的颜色空间转换 -> `transformed-writepixels.png`
3. **draw**: 通过 SkCanvas::drawImage 渲染时转换 -> `transformed-draw.png`

当输入为 ICC 配置文件时,变换 8 个关键颜色点(黑/白/三原色/补色)。

## 依赖关系

- `modules/skcms/skcms.h` - 颜色管理
- `include/codec/SkCodec.h` - 图像解码
- `include/core/SkSurface.h` - 渲染表面

## 设计模式与设计决策

- **三路对比**: 三种转换方法的输出可对比验证颜色管理的一致性
- **不可转换处理**: 对不可直接用作目标的配置文件尝试 `MakeUsableAsDestinationWithSingleCurve`

## 性能考量

对大图像,skcms 直接变换最快;draw 方法涉及完整的渲染管线开销。

## 相关文件

- `modules/skcms/` - skcms 颜色管理模块
