# D3DTestContext

> 源文件：tools/ganesh/d3d/D3DTestContext.h, tools/ganesh/d3d/D3DTestContext.cpp

## 概述

D3DTestContext 是 Skia Ganesh 测试框架中用于 Direct3D 12 后端的测试上下文实现。Direct3D 12 是 Microsoft 的现代图形 API，主要用于 Windows 平台。该类封装了 D3D12 设备、命令队列和适配器的创建，为 Direct3D GPU 测试提供统一接口。

主要特性：
- 创建 Direct3D 12 设备和命令队列
- 支持上下文共享（共享 D3D12 设备）
- 支持受保护内存（用于 DRM 内容）
- 支持调试层（用于开发和调试）
- 创建 Ganesh D3D 直接上下文

该模块仅在 Windows 平台且定义了 `SK_DIRECT3D` 时编译。

## 架构位置

- **基类**：TestContext
- **同级实现**：OpenGL、Vulkan、Metal、Mock 实现
- **平台**：仅 Windows（Direct3D 12）
- **依赖**：D3D12、DXGI、GrD3DBackendContext

## 主要类与结构体

### D3DTestContext（抽象类）

```cpp
class D3DTestContext : public TestContext {
public:
    virtual GrBackendApi backend() override { return GrBackendApi::kDirect3D; }
    const GrD3DBackendContext& getD3DBackendContext() const;

protected:
    D3DTestContext(const GrD3DBackendContext& d3d, bool ownsContext);
    GrD3DBackendContext fD3D;
    bool fOwnsContext;
};
```

### CreatePlatformD3DTestContext（工厂函数）

```cpp
D3DTestContext* CreatePlatformD3DTestContext(D3DTestContext* sharedContext);
```

创建 Direct3D 12 测试上下文。如果提供共享上下文，将重用其 D3D12 资源。

## 内部实现细节

### 上下文创建

共享和非共享路径：

```cpp
if (sharedContext) {
    ownsContext = false;
    backendContext = sharedContext->getD3DBackendContext();
} else {
    if (!sk_gpu_test::CreateD3DBackendContext(&backendContext)) {
        return nullptr;
    }
    ownsContext = true;
}
```

### Ganesh 上下文创建

```cpp
sk_sp<GrDirectContext> makeContext(const GrContextOptions& options) override {
    return GrDirectContexts::MakeD3D(fD3D, options);
}
```

### 栅栏支持

```cpp
fFenceSupport = true;
```

Direct3D 12 支持栅栏（`ID3D12Fence`）进行同步。

### 上下文切换

```cpp
void onPlatformMakeNotCurrent() const override {}
void onPlatformMakeCurrent() const override {}
std::function<void()> onPlatformGetAutoContextRestore() const override { return nullptr; }
```

D3D12 没有"当前上下文"概念（类似 Vulkan 和 Metal）。

### 资源清理

```cpp
void teardown() override {
    INHERITED::teardown();
    if (fOwnsContext) {
        // delete all the D3D objects in the backend context
    }
}
```

仅当拥有上下文所有权时才清理 D3D12 资源。

## 依赖关系

- **D3D12**：Direct3D 12 API
- **DXGI**：DirectX Graphics Infrastructure
- **GrD3DBackendContext**：D3D12 后端上下文
- **D3DTestUtils**：D3D12 测试工具函数

## 设计模式与设计决策

### 所有权语义
`fOwnsContext` 标志控制是否清理 D3D12 资源，支持上下文共享。

### 条件编译
整个模块使用 `#ifdef SK_DIRECT3D` 保护，仅在支持 D3D12 时编译。

### 延迟清理
`teardown()` 中的注释表明 D3D12 对象清理已在 GrD3DBackendContext 的析构函数中处理。

## 性能考量

- D3D12 的低开销 API 设计
- 支持上下文共享避免重复初始化
- 无上下文切换开销
- 命令列表批处理优化

## 相关文件

- `tools/ganesh/TestContext.h/cpp` - 基类
- `tools/ganesh/d3d/D3DTestUtils.h/cpp` - D3D12 工具函数
- `include/gpu/ganesh/d3d/GrD3DBackendContext.h` - D3D12 后端上下文
- `include/gpu/ganesh/d3d/GrD3DDirectContext.h` - D3D12 直接上下文
