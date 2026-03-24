# DM GPU 测试过程

> 源文件: `dm/DMGpuTestProcs.cpp`

## 概述

此文件实现了 DM（Skia 的测试运行器）中 GPU 后端测试所需的运行函数。它提供了上下文类型检测函数和用于在各种 GPU 上下文中运行测试的入口函数，支持 Ganesh 和 Graphite 两个 GPU 后端。

## 架构位置

位于 DM 测试框架 (`dm/`) 中，实现 `tests/Test.h` 中声明的 GPU 测试支持函数。是 DM 测试运行器的 GPU 测试基础设施。

## 主要类与结构体

无自定义结构体。使用 `skgpu::ContextType` 枚举和 `GrContextFactory`/`ContextInfo` 等现有类型。

## 公共 API 函数

### 上下文类型检测
- `IsGLContextType(type)` - 判断 OpenGL 上下文
- `IsVulkanContextType(type)` - 判断 Vulkan 上下文
- `IsMetalContextType(type)` - 判断 Metal 上下文
- `IsDirect3DContextType(type)` - 判断 Direct3D 上下文
- `IsDawnContextType(type)` - 判断 Dawn 上下文
- `IsMockContextType(type)` - 判断 Mock 上下文

### 测试运行
- `RunWithGaneshTestContexts(testFn, filter, reporter, options)` - 在所有 Ganesh GPU 上下文中运行测试
- `RunWithGraphiteTestContexts(test, filter, reporter, options)` - 在所有 Graphite 上下文中运行测试

## 内部实现细节

- Ganesh 测试在桌面平台使用 `kGL`，其他平台使用 `kGLES`
- 每个测试后销毁 `GrContextFactory`，避免命令缓冲区层与原生窗口系统 API 冲突
- Ganesh 测试后执行 `flushAndSubmit(GrSyncCpu::kYes)` 确保异步操作完成
- Graphite 使用 `ContextFactory` 统一管理所有后端上下文

## 依赖关系

- `tests/Test.h` - 测试框架接口
- `include/gpu/ganesh/GrDirectContext.h` - Ganesh GPU 上下文
- `include/gpu/graphite/Context.h` - Graphite GPU 上下文

## 设计模式与设计决策

- **策略模式**：通过 `ContextTypeFilterFn` 过滤器让测试选择在哪些 GPU 后端上运行
- **工厂模式**：`GrContextFactory` 管理 GPU 上下文的生命周期

## 性能考量

每个测试重新创建 GrContextFactory 有开销，但避免了上下文状态泄漏问题。

## 相关文件

- `tests/Test.h` - 测试框架声明
- `dm/DM.cpp` - DM 主程序
