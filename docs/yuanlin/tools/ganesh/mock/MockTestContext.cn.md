# MockTestContext

> 源文件：tools/ganesh/mock/MockTestContext.h, tools/ganesh/mock/MockTestContext.cpp

## 概述

MockTestContext 是 Skia Ganesh 测试框架中的模拟（Mock）上下文实现，专门用于创建不需要真实 GPU 硬件的测试环境。该类继承自 TestContext 基类，提供了一个极简的实现，所有 GPU 操作都会"琐碎地成功"（trivially succeed），即不执行任何实际的图形操作就直接返回成功。

MockTestContext 的核心价值在于：
- 在没有 GPU 的环境中运行测试（如 CI 服务器、容器环境）
- 快速验证 Ganesh API 调用逻辑而无需等待实际 GPU 执行
- 测试上下文管理和资源生命周期而不涉及真实硬件
- 隔离测试纯软件逻辑，避免硬件差异导致的测试不稳定

该模块非常轻量，整个实现不到 50 行代码，但对于构建健壮的测试基础设施至关重要。它使得大量单元测试可以在纯 CPU 环境中运行，大幅提升测试执行速度和可靠性。

## 架构位置

MockTestContext 位于 Ganesh 测试工具的平台特定实现层：

- **基类**：`tools/ganesh/TestContext` - 测试上下文抽象基类

- **同级实现**（其他平台的 TestContext）：
  - `tools/ganesh/gl/GLTestContext` - OpenGL 实现
  - `tools/ganesh/vk/VkTestContext` - Vulkan 实现
  - `tools/ganesh/mtl/MtlTestContext` - Metal 实现
  - `tools/ganesh/d3d/D3DTestContext` - Direct3D 实现

- **上层调用者**：
  - 不需要真实 GPU 的单元测试
  - API 调用顺序验证测试
  - 资源生命周期测试
  - 快速烟雾测试（smoke tests）

- **配合使用的组件**：
  - `GrBackendApi::kMock` - Mock 后端 API 标识
  - `GrDirectContext::MakeMock` - 创建 Mock 上下文的工厂函数
  - Mock GPU 实现（位于 Ganesh 核心代码中）

MockTestContext 作为最简单的 TestContext 实现，也可以作为新平台实现的参考模板。

## 主要类与结构体

### CreateMockTestContext（工厂函数）

```cpp
namespace sk_gpu_test {
TestContext* CreateMockTestContext(TestContext* shareContext = nullptr);
}
```

这是模块提供的唯一公共 API，用于创建 MockTestContext 实例。

**参数**：
- `shareContext` - 可选的共享上下文（当前实现中未使用）

**返回值**：
- 指向新创建的 MockTestContext 的指针（调用者负责释放）

**使用示例**：
```cpp
std::unique_ptr<TestContext> testCtx(sk_gpu_test::CreateMockTestContext());
auto grContext = testCtx->makeContext(GrContextOptions());
// 现在可以使用 grContext 进行测试，但所有 GPU 操作都是模拟的
```

### MockTestContext（内部实现类）

```cpp
class MockTestContext : public sk_gpu_test::TestContext {
public:
    MockTestContext() {}
    ~MockTestContext() override {}

    GrBackendApi backend() override;
    void testAbandon() override;
    sk_sp<GrDirectContext> makeContext(const GrContextOptions& options) override;

protected:
    void teardown() override;
    void onPlatformMakeNotCurrent() const override;
    void onPlatformMakeCurrent() const override;
    std::function<void()> onPlatformGetAutoContextRestore() const override;
};
```

该类位于匿名命名空间中，确保实现细节不对外暴露。所有接口都是必须实现的虚函数或纯虚函数。

## 公共 API 函数

### CreateMockTestContext

```cpp
TestContext* CreateMockTestContext(TestContext* shareContext) {
    return new MockTestContext();
}
```

创建并返回 MockTestContext 实例。虽然接受 `shareContext` 参数以匹配其他平台的接口，但 Mock 实现中忽略了该参数，因为模拟上下文不需要共享实际的 GPU 资源。

**设计理由**：
- 保持与其他 `Create*TestContext` 函数的接口一致性
- 未来可能支持共享模拟状态
- 允许测试代码统一处理不同平台

## 内部实现细节

### backend() - 后端标识

```cpp
GrBackendApi backend() override {
    return GrBackendApi::kMock;
}
```

返回 `GrBackendApi::kMock` 表明这是一个模拟后端。这个信息用于：
- 测试代码判断当前使用的后端类型
- Ganesh 内部选择 Mock 特定的代码路径
- 跳过需要真实 GPU 的测试

### makeContext() - 上下文创建

```cpp
sk_sp<GrDirectContext> makeContext(const GrContextOptions& options) override {
    return GrDirectContext::MakeMock(nullptr, options);
}
```

创建 Mock GrDirectContext。`GrDirectContext::MakeMock` 的第一个参数是 `GrMockOptions`，传入 `nullptr` 使用默认配置。

**关键点**：
- Mock 上下文不需要真实的 GPU 设备
- 所有 GPU 操作都被桩（stub）实现替代
- 支持传递 `GrContextOptions` 以测试不同配置

### testAbandon() - 放弃上下文

```cpp
void testAbandon() override {}
```

空实现。Mock 上下文没有真实资源需要放弃，因此该方法什么也不做。

### 平台特定虚函数

Mock 实现中，所有平台特定的上下文操作都是空操作：

```cpp
void teardown() override {}
void onPlatformMakeNotCurrent() const override {}
void onPlatformMakeCurrent() const override {}
std::function<void()> onPlatformGetAutoContextRestore() const override {
    return nullptr;
}
```

**设计理由**：
- Mock 后端没有"当前上下文"的概念
- 不需要清理平台特定资源
- 返回 `nullptr` 表示自动恢复功能不适用

### 匿名命名空间

实现类位于匿名命名空间中：

```cpp
namespace {
class MockTestContext : public sk_gpu_test::TestContext { ... };
}

namespace sk_gpu_test {
TestContext* CreateMockTestContext(TestContext*) { return new MockTestContext(); }
}
```

这种设计：
- 隐藏实现细节，防止外部直接构造
- 通过工厂函数控制对象创建
- 保持 ABI 稳定性

## 依赖关系

### 核心依赖

- **TestContext**：基类，定义测试上下文接口
- **GrDirectContext**：Ganesh 直接上下文，Mock 实现

### 间接依赖

- **GrBackendApi**：后端 API 枚举
- **GrContextOptions**：上下文配置选项
- **GrMockOptions**：Mock 后端特定选项（使用默认值）

### Mock 后端实现

MockTestContext 依赖 Ganesh 核心中的 Mock GPU 实现：
- `src/gpu/ganesh/mock/GrMockGpu.h` - Mock GPU 设备
- `src/gpu/ganesh/mock/GrMockTypes.h` - Mock 类型定义
- `src/gpu/ganesh/mock/GrMockCaps.h` - Mock 能力

这些组件提供实际的"假"GPU 功能。

## 设计模式与设计决策

### 工厂模式

使用工厂函数而非公开构造函数：

```cpp
TestContext* CreateMockTestContext(TestContext* shareContext = nullptr);
```

**优势**：
- 隐藏实现类
- 统一创建接口（所有平台都有 `Create*TestContext` 函数）
- 灵活性：可以根据参数返回不同的实现

### 模板方法模式（继承自基类）

MockTestContext 实现基类定义的虚函数接口：

```cpp
class MockTestContext : public sk_gpu_test::TestContext {
    // 实现所有纯虚函数和虚函数
};
```

这遵循 TestContext 建立的模板方法模式，提供平台特定实现。

### 空对象模式（Null Object Pattern）

MockTestContext 是空对象模式的典型应用：
- 提供完整的接口实现
- 所有操作都是无操作（no-op）或返回默认值
- 调用者无需特殊处理 Mock 情况

**示例**：
```cpp
// 无论是真实上下文还是 Mock 上下文，代码都一样
testContext->makeCurrent();
testContext->flushAndSyncCpu(grContext);
testContext->makeNotCurrent();
```

### 最小实现原则

MockTestContext 的实现极其简洁：
- 构造/析构函数为空
- 大部分虚函数为空实现
- 只有 `backend()` 和 `makeContext()` 返回有意义的值

这体现了"实现所需最小功能"的原则。

### 接口一致性

尽管 `shareContext` 参数未使用，仍保留在签名中：

```cpp
TestContext* CreateMockTestContext(TestContext* shareContext = nullptr);
```

这确保所有平台的创建函数具有一致的签名，简化测试代码的跨平台编写。

## 性能考量

### 零开销抽象

MockTestContext 本身几乎没有性能开销：
- 所有方法都是空操作
- 没有实际的 GPU 通信
- 内存占用极小（仅基类数据成员）

### 快速测试执行

使用 Mock 上下文的测试执行速度极快：
- 无 GPU 驱动调用
- 无着色器编译
- 无实际渲染

这使得大规模单元测试套件可以在秒级完成。

### Mock GPU 性能

虽然 MockTestContext 本身很快，但 Mock GPU 实现仍会执行部分逻辑：
- 资源管理（创建/销毁代理对象）
- 命令记录（虽然不执行）
- 状态验证

这些操作比真实 GPU 快得多，但不是完全免费的。

### 适用场景

Mock 上下文适合：
- **API 调用测试**：验证调用顺序和参数
- **资源管理测试**：测试引用计数和生命周期
- **快速烟雾测试**：确保基本功能不崩溃

Mock 上下文不适合：
- **渲染结果验证**：无实际渲染输出
- **性能基准测试**：与真实 GPU 性能无关
- **硬件特性测试**：无真实硬件能力

## 相关文件

### 基类定义
- `tools/ganesh/TestContext.h` - 测试上下文抽象基类
- `tools/ganesh/TestContext.cpp` - 基类实现

### 其他平台实现
- `tools/ganesh/gl/GLTestContext.h/cpp` - OpenGL 实现
- `tools/ganesh/vk/VkTestContext.h/cpp` - Vulkan 实现
- `tools/ganesh/mtl/MtlTestContext.h/.mm` - Metal 实现
- `tools/ganesh/d3d/D3DTestContext.h/cpp` - Direct3D 实现

### Ganesh Mock 后端
- `src/gpu/ganesh/mock/GrMockGpu.h` - Mock GPU 设备实现
- `src/gpu/ganesh/mock/GrMockTypes.h` - Mock 类型定义
- `src/gpu/ganesh/mock/GrMockCaps.h` - Mock 能力描述
- `src/gpu/ganesh/mock/GrMockOpsRenderPass.h` - Mock 渲染通道

### 上下文相关
- `include/gpu/ganesh/GrDirectContext.h` - 直接上下文接口
- `include/gpu/ganesh/GrContextOptions.h` - 上下文配置选项
- `include/gpu/ganesh/GrTypes.h` - Ganesh 类型定义（包括 GrBackendApi）

### 测试基础设施
- `tools/ganesh/TestOps.h/cpp` - 测试用绘制操作
- `tools/ganesh/ProxyUtils.h/cpp` - 代理工具函数
- `tools/ganesh/MemoryCache.h/cpp` - 内存缓存
