# tools/ganesh/mock - Ganesh Mock 模拟后端测试上下文

## 概述

`tools/ganesh/mock` 目录实现了 Ganesh GPU 后端的 Mock（模拟）测试上下文。Mock 后端是一个不依赖任何真实 GPU 硬件的虚拟后端，它会对所有 GPU 操作返回成功结果，但不会执行任何实际的图形渲染。

Mock 后端在 Skia 的测试体系中扮演着重要角色。它允许开发者在没有 GPU 硬件的环境中（如 CI 服务器）运行大部分 GPU 相关的逻辑测试，验证 API 调用链、资源管理和状态机行为的正确性。由于不涉及真实的 GPU 驱动，Mock 后端的测试执行速度非常快。

Mock 后端通过 `GrBackendApi::kMock` 标识，是 `GrContextFactory` 中唯一不需要条件编译宏保护的后端（始终可用）。它在 `GrContextFactory::getContextInfoInternal()` 中通过 `CreateMockTestContext()` 工厂函数创建。

本目录结构简洁，仅包含 Mock 测试上下文的声明和实现文件，不依赖任何平台特定的图形 API 库。

## 目录结构

```
tools/ganesh/mock/
├── BUILD.bazel            # Bazel 构建配置
├── MockTestContext.h      # Mock 测试上下文声明
└── MockTestContext.cpp    # Mock 测试上下文实现
```

## 关键类与函数

### CreateMockTestContext
- **命名空间**: `sk_gpu_test`
- **签名**: `TestContext* CreateMockTestContext(TestContext* shareContext = nullptr)`
- **功能**: 创建一个 Mock 测试上下文实例
- **参数**: `shareContext` - 可选的共享上下文，用于模拟上下文共享组
- **返回值**: 指向新创建的 Mock `TestContext` 的指针
- **特点**: 此函数创建的上下文会对所有 GPU 操作"空操作"，不执行实际的图形命令

### MockTestContext（内部实现）
- 继承自 `sk_gpu_test::TestContext`
- 返回 `GrBackendApi::kMock` 作为后端类型
- 所有平台相关方法（`onPlatformMakeCurrent`、`onPlatformMakeNotCurrent` 等）均为空操作
- 通过 `GrDirectContexts::MakeMock()` 创建对应的 `GrDirectContext`

## 依赖关系

- **上游依赖**: `tools/ganesh/TestContext.h`（基类定义）
- **GPU 依赖**: `include/gpu/ganesh/GrDirectContext.h`、`include/gpu/ganesh/mock/GrMockTypes.h`
- **被引用**: `tools/ganesh/GrContextFactory.cpp`（工厂函数中直接调用）
- **无平台依赖**: 不需要任何 GPU 驱动或图形 API 库

## 使用场景

### CI/CD 测试
Mock 后端最常见的使用场景是在 CI/CD 环境中运行不需要实际 GPU 渲染结果的测试。例如：
- API 调用序列验证：确保 Skia 的 GPU API 调用链正确
- 资源生命周期管理：验证纹理、缓冲区等 GPU 资源的创建和销毁逻辑
- 上下文放弃恢复：测试 `abandonContext()` 后的行为

### 性能基准
Mock 后端可用于隔离 CPU 端开销，测量不包含 GPU 执行时间的纯 CPU 操作耗时。

### 代码覆盖率
通过 Mock 后端可以覆盖大量 GPU 代码路径而无需真实硬件，提高整体代码覆盖率。

### 与真实后端的区别
- Mock 后端不分配实际的 GPU 内存
- 不执行着色器编译
- 不进行实际的像素渲染
- 所有 GPU 查询返回预设的默认值
- 纹理读回操作返回空数据

## 实现细节

Mock 后端的内部实现位于 `src/gpu/ganesh/mock/` 目录中，包括：
- `GrMockGpu` - Mock GPU 设备实现
- `GrMockCaps` - Mock 能力查询（返回保守的默认值）
- `GrMockTexture` / `GrMockRenderTarget` - Mock 纹理和渲染目标

在测试上下文层面，`MockTestContext` 继承自 `TestContext` 但覆盖所有平台方法为空操作，因为 Mock 后端不需要真实的平台上下文管理。

## 相关文档与参考

- `tools/ganesh/TestContext.h` - 测试上下文基类
- `tools/ganesh/GrContextFactory.h` - 上下文工厂，通过 `ContextType::kMock` 使用
- `include/gpu/ganesh/mock/GrMockTypes.h` - Mock 后端类型定义
- `src/gpu/ganesh/mock/` - Mock GPU 后端的核心实现
- `tests/` - 许多单元测试使用 Mock 后端以避免 GPU 硬件依赖
