# get_current_monitor_profile - 显示器 ICC 配置文件提取工具

> 源文件: `tools/get_current_monitor_profile.cpp`

## 概述

`get_current_monitor_profile` 提取当前系统显示器的 ICC 颜色配置文件并保存到文件。支持 macOS (CoreGraphics) 和 Windows (ICM) 平台。

## 架构位置

属于 Skia 颜色管理调试工具。

## 公共 API 函数

- **`main()`**: 根据平台提取 ICC 配置文件

## 内部实现细节

- **macOS**: 通过 `CGDisplayCopyColorSpace` + `CGColorSpaceCopyICCProfile` 获取主显示器配置文件
- **Windows**: 遍历 `EnumDisplayDevices`,对已连接的显示器通过 `GetICMProfile` 获取配置文件路径,使用 `CopyFile` 复制
- 输出文件: `monitor_0.icc`, `monitor_1.icc` 等

## 依赖关系

- macOS: ApplicationServices 框架
- Windows: windows.h (ICM API)

## 设计模式与设计决策

- **平台抽象**: 通过条件编译支持不同平台的 ICC 获取方式
- Windows 版本遍历所有已连接显示器(比 Chrome 更完整)

## 性能考量

单次运行,开销极小。

## 相关文件

- `tools/imgcvt.cpp` - 使用 ICC 配置文件的颜色转换工具
