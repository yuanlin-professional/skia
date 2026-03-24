# AndroidSkDebugToStdOut - Android 调试输出重定向

> 源文件: `tools/AndroidSkDebugToStdOut.cpp`

## 概述

`AndroidSkDebugToStdOut.cpp` 在 Android 平台上通过静态初始化将 `SkDebugf` 的输出从 Android logcat 重定向到 stdout。这在测试和调试工具中非常有用。

## 架构位置

属于 Skia 的 Android 平台适配层。

## 主要类与结构体

- **`SendToStdOut`**: 静态初始化类,构造函数中设置 `gSkDebugToStdOut = true`

## 内部实现细节

利用全局静态对象 `gSendToStdOut` 的构造函数在 main() 之前执行,设置全局标志。仅在 `SK_BUILD_FOR_ANDROID` 时编译。

## 依赖关系

- `include/core/SkTypes.h` - Skia 类型和平台定义

## 设计模式与设计决策

- **静态初始化技巧**: 利用 C++ 全局对象构造函数实现零配置的输出重定向

## 相关文件

- Skia 的 SkDebugf 实现
