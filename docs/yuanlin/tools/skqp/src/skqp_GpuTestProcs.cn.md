# skqp_GpuTestProcs.cpp - SkQP GPU 测试过程实现

> 源文件: `tools/skqp/src/skqp_GpuTestProcs.cpp`

## 概述

`skqp_GpuTestProcs.cpp` 实现了 SkQP（Skia Quality Program）中 GPU 测试的运行过程。该文件提供了在 SkQP 环境下运行 Ganesh 和 Graphite GPU 测试所需的上下文管理和测试调度逻辑。它是 Skia 测试框架中 `RunWithGaneshTestContexts` 和 `RunWithGraphiteTestContexts` 的 SkQP 特定实现，决定了在 SkQP 合规性测试中应测试哪些 GPU 后端。

此文件的核心职责是根据设备能力自动选择合适的 GPU 上下文类型（OpenGL、Vulkan 等），并为每种上下文运行注册的 GPU 测试。

## 架构位置

```
Skia 测试框架
├── tests/Test.h                       <-- 测试基础设施定义
├── tools/skqp/src/
│   ├── skqp_GpuTestProcs.cpp          <-- 本文件：SkQP 版 GPU 测试调度
│   └── skqp.h                         <-- SkQP 核心定义
├── tests/DMGpuTestProcs.cpp           <-- DM 版 GPU 测试调度（对比参考）
└── tools/ganesh/
    └── vk/VkTestContext.h             <-- Vulkan 测试上下文
```

## 主要类与结构体

本文件不定义新的类，但在 `skiatest` 命名空间中实现了多个关键函数。

### 上下文类型辅助函数

```cpp
bool IsGLContextType(skgpu::ContextType type);      // 是否为 OpenGL 上下文
bool IsVulkanContextType(skgpu::ContextType type);   // 是否为 Vulkan 上下文
bool IsMockContextType(skgpu::ContextType type);     // 是否为 Mock 上下文
bool IsMetalContextType(skgpu::ContextType type);    // 始终返回 false（不支持）
bool IsDirect3DContextType(skgpu::ContextType type); // 始终返回 false（不支持）
bool IsDawnContextType(skgpu::ContextType type);     // 始终返回 false（不支持）
```

SkQP 仅支持 OpenGL/ES、Vulkan 和 Mock 后端；Metal、Direct3D 和 Dawn 在 SkQP 中不被支持。

## 公共 API 函数

### `RunWithGaneshTestContexts`
```cpp
void RunWithGaneshTestContexts(GrContextTestFn* testFn,
                               ContextTypeFilterFn* filter,
                               Reporter* reporter,
                               const GrContextOptions& options);
```
遍历所有支持的 GPU 上下文类型，为每种通过过滤的上下文创建 `GrContextFactory`，获取上下文信息后执行测试函数。测试完成后执行 `flushAndSubmit` 同步。

### `RunWithGraphiteTestContexts`（SK_GRAPHITE 条件编译）
```cpp
void RunWithGraphiteTestContexts(GraphiteTestFn* test,
                                 ContextTypeFilterFn* filter,
                                 Reporter* reporter,
                                 const TestOptions& options);
```
Graphite 版本的 GPU 测试调度，逻辑类似 Ganesh 版本，但使用 Graphite 的 `ContextFactory` 和 `ContextInfo`。

### `SkQP::printBackendInfo`
```cpp
void SkQP::printBackendInfo(const char* dstPath);
```
将 GPU 后端信息转储到指定文件（JSON 格式），用于调试和诊断。仅在 `SK_ENABLE_DUMP_GPU` 宏启用时有效。

## 内部实现细节

### GPU 上下文选择策略

`skip_context()` 函数实现了 SkQP 的上下文过滤逻辑：

1. **OpenGL 版本选择**：在桌面平台使用 `kGL`（OpenGL），在移动平台使用 `kGLES`（OpenGL ES）。避免同时测试两种 GL 标准。
   ```cpp
   #if defined(SK_BUILD_FOR_UNIX) || defined(SK_BUILD_FOR_WIN) || defined(SK_BUILD_FOR_MAC)
   static constexpr auto kNativeGLType = skgpu::ContextType::kGL;
   #else
   static constexpr auto kNativeGLType = skgpu::ContextType::kGLES;
   #endif
   ```

2. **Vulkan 可用性检查**：通过 `vk_has_physical_devices()` 检查设备是否有可用的 Vulkan 物理设备。如果没有物理设备则跳过 Vulkan 测试。

### Vulkan 物理设备检测

```cpp
static bool vk_has_physical_devices() {
    static bool supported = false;
    static std::once_flag flag;
    std::call_once(flag, []() {
        std::unique_ptr<TestContext> testCtx(
            sk_gpu_test::CreatePlatformVkTestContext(nullptr));
        if (testCtx) supported = true;
    });
    return supported;
}
```

使用 `std::call_once` 确保仅检测一次，结果被缓存。通过尝试创建平台 Vulkan 测试上下文来判断设备支持情况。

### Android CDD 合规性

代码中特别注明了 Android CDD（Compatibility Definition Document）对 Vulkan 的要求：
- Android CDD 不强制要求 Vulkan 支持
- 但如果设备枚举了至少一个 VkPhysicalDevice，则预期 Vulkan 应该可用

### 后端信息转储

`printBackendInfo` 对 GL 和 Vulkan 后端分别创建测试上下文，然后调用 `ctx->dump()` 输出 GPU 信息。输出格式为 JSON 数组。

## 依赖关系

- **Skia 测试框架**：`tests/Test.h`
- **SkQP 框架**：`tools/skqp/src/skqp.h`
- **Ganesh GPU**：`GrDirectContext`, `GrContextOptions`
- **Graphite GPU**（条件编译）：`skgpu::graphite::Context`, `ContextFactory`
- **Vulkan 测试**（条件编译）：`tools/ganesh/vk/VkTestContext.h`
- **OpenGL 测试**（条件编译）：通过 `sk_gpu_test::GLTestContext`
- **C++ 标准库**：`<mutex>`

## 设计模式与设计决策

1. **模板方法模式**：`RunWithGaneshTestContexts` 和 `RunWithGraphiteTestContexts` 定义了 GPU 测试执行的骨架算法（遍历上下文、过滤、创建工厂、执行测试），具体的测试逻辑通过函数指针注入。

2. **条件编译隔离**：通过 `SK_VULKAN`、`SK_GL`、`SK_GRAPHITE` 等宏控制不同 GPU 后端的编译，使得不支持某后端的平台可以正常编译。

3. **单次初始化**：`vk_has_physical_devices()` 使用 `std::call_once` 确保 Vulkan 设备检测仅执行一次，避免重复的设备枚举开销。

4. **平台适配**：通过编译时常量 `kNativeGLType` 自动选择平台的原生 GL 类型，避免在运行时进行平台判断。

5. **与 DM 的行为镜像**：代码注释明确表示逻辑"旨在镜像 DMGpuTestProcs.cpp 中的行为"，确保 SkQP 和 DM 的测试行为一致。

## 性能考量

- **Vulkan 检测缓存**：通过 `static bool` + `std::call_once` 将 Vulkan 设备检测结果缓存，避免为每个测试重复创建和销毁 Vulkan 实例。
- **上下文工厂生命周期**：每次调用 `RunWithGaneshTestContexts` 时都创建新的 `GrContextFactory`，确保测试间的隔离性但增加了初始化开销。
- **同步等待**：Ganesh 测试完成后执行 `flushAndSubmit(GrSyncCpu::kYes)` 强制 CPU-GPU 同步，确保所有 GPU 操作完成，确保 release/finished procs 被调用。
- **非支持后端直接跳过**：Metal、D3D、Dawn 的检查函数直接返回 `false`，零开销跳过不支持的后端。
- **上下文类型枚举**：通过整数遍历所有上下文类型，使用 `skip_context` 和 `filter` 双重过滤，避免创建不需要的上下文。
- **Graphite 上下文工厂复用**：`RunWithGraphiteTestContexts` 中 `ContextFactory` 在循环外创建，允许多个上下文类型共享工厂的内部缓存。

## 相关文件

- `tests/Test.h` - 测试框架基础定义（Reporter, GrContextTestFn, ContextTypeFilterFn 等）
- `tests/DMGpuTestProcs.cpp` - DM 版本的 GPU 测试过程（本文件参照其行为实现）
- `tools/skqp/src/skqp.h` - SkQP 核心定义
- `tools/ganesh/vk/VkTestContext.h` - Vulkan 测试上下文创建（`CreatePlatformVkTestContext`）
- `tools/graphite/ContextFactory.h` - Graphite 上下文工厂
- `include/gpu/ganesh/GrDirectContext.h` - Ganesh 直接上下文
- `include/gpu/ganesh/GrContextOptions.h` - GPU 上下文选项
- `include/core/SkStream.h` - 文件流（用于 `printBackendInfo`）
