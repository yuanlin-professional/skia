# TsanSuppressions - ThreadSanitizer 抑制规则

> 源文件: `tools/TsanSuppressions.cpp`

## 概述

`TsanSuppressions.cpp` 定义了 ThreadSanitizer (TSAN) 的默认抑制规则,用于过滤已知的第三方库数据竞争报告。目前抑制了 Intel Vulkan 驱动(mesa-22.1.3)中 `anv_shader_bin_create` 的竞争问题。

## 架构位置

属于 Skia 测试/调试基础设施。

## 公共 API 函数

- **`__tsan_default_suppressions()`**: TSAN 回调,返回抑制规则字符串

## 内部实现细节

仅在同时满足 thread_sanitizer 启用、SK_GRAPHITE 和 SK_VULKAN 编译时激活。当前抑制了 b/373932392 (Precompile 在 Native Vulkan 上非线程安全)。

## 依赖关系

- Clang ThreadSanitizer

## 相关文件

- `tools/LsanSuppressions.cpp` - LeakSanitizer 抑制规则
