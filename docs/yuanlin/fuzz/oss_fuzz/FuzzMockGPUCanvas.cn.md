# FuzzMockGPUCanvas (OSS-Fuzz)

> 源文件: fuzz/oss_fuzz/FuzzMockGPUCanvas.cpp

## 概述

使用模拟 GPU 上下文测试 Canvas 绘图 API。Mock GPU 提供轻量级的 GPU 模拟,无需真实图形驱动,适合快速 fuzzing。

## 架构位置

测试 GPU Canvas 在模拟环境中的行为。

## 主要类与结构体

**__lsan_default_options**: 配置 LeakSanitizer 选项,抑制已知的无害泄漏报告

**LLVMFuzzerTestOneInput**:
- 最大 4000 字节
- 使用可移植字体
- 创建 Mock GPU 上下文

**fuzz_MockGPUCanvas**: 在 Mock GPU 上下文中执行绘图

## 内部实现细节

Mock GPU 特性:
- 模拟 GL/Vulkan/Metal 调用
- 无需真实硬件
- 快速执行,适合 CI

LSAN 配置:
```cpp
const char *__lsan_default_options() {
    return "print_suppressions=0";
}
```

## 依赖关系

- `tools/gpu/GrContextFactory.h`: GPU 上下文工厂
- `tools/fonts/FontToolUtils.h`: 字体工具

## 设计模式与设计决策

**模拟对象**: 通过 Mock 加速测试,避免真实 GPU 的复杂性。

## 性能考量

Mock GPU 比真实 GPU 快数倍,提高 fuzzing 吞吐量。

## 相关文件

- `tools/gpu/mock/GrMockGpu.cpp`: Mock GPU 实现
- `fuzz/FuzzCanvas.cpp`: Canvas fuzzing 逻辑
