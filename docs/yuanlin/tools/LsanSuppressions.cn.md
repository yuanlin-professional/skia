# LsanSuppressions - LeakSanitizer 抑制规则

> 源文件: `tools/LsanSuppressions.cpp`

## 概述

`LsanSuppressions.cpp` 定义了 AddressSanitizer 的 LeakSanitizer (LSAN) 抑制规则,用于过滤已知的非 Skia 源的内存泄漏报告。这些抑制规则避免了第三方库(如 fontconfig、freetype、NVidia 驱动、Intel Vulkan 驱动)的误报干扰 Skia 自身的内存泄漏检测。

## 架构位置

属于 Skia 的测试/调试基础设施。

## 公共 API 函数

- **`__lsan_default_suppressions()`**: LSAN 回调函数,返回抑制规则字符串

## 内部实现细节

抑制的库: libfontconfig, libfreetype, libGLX_nvidia.so, libnvidia-glcore.so, libnvidia-tls.so, terminator_CreateDevice, vkEnumeratePhysicalDevices

仅在支持 address_sanitizer 且非 Windows 平台时编译。

## 依赖关系

- Clang AddressSanitizer

## 相关文件

- `tools/TsanSuppressions.cpp` - ThreadSanitizer 抑制规则
