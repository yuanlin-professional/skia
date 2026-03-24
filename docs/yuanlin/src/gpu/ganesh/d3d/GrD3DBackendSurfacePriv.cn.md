# GrD3DBackendSurfacePriv

> 源文件: src/gpu/ganesh/d3d/GrD3DBackendSurfacePriv.h

## 概述

`GrD3DBackendSurfacePriv.h` 是 Skia Ganesh GPU 后端中用于 Direct3D 12 平台的后端表面私有接口定义文件。该文件提供了创建和管理 D3D12 后端纹理和渲染目标的工厂函数，允许外部代码将 Direct3D 12 资源导入到 Ganesh 渲染系统中。与 Vulkan 版本类似，该文件支持可变资源状态管理，这对于 D3D12 的资源转换屏障至关重要。

该文件是 Skia 与 Direct3D 12 API 集成的桥梁，使应用程序能够在 D3D12 和 Skia 之间共享纹理资源。

## 架构位置

在 Skia 的 Direct3D 12 后端架构中的位置：

```
skia/
├── include/
│   └── gpu/ganesh/d3d/        # D3D12 公共 API
├── src/
    └── gpu/
        └── ganesh/
            └── d3d/            # D3D12 后端实现
                └── GrD3DBackendSurfacePriv.h  # 本文件
```

该文件的依赖关系：
- **上游**: 依赖 D3D12 类型定义和资源状态类
- **下游**: 被 D3D12 GPU 实现和客户端代码使用
- **协同**: 与 `GrBackendTexture`/`GrBackendRenderTarget` 配合工作

## 主要类与结构体

### 命名空间 GrBackendTextures

提供创建和查询 D3D12 后端纹理的函数。

#### MakeD3D

```cpp
GrBackendTexture MakeD3D(int width,
                         int height,
                         const GrD3DTextureResourceInfo& d3dInfo,
                         sk_sp<GrD3DResourceState> state,
                         std::string_view label = {});
```

**功能：** 从 D3D12 资源信息创建后端纹理

**参数说明：**
- `width`/`height`: 纹理尺寸（像素）
- `d3dInfo`: D3D12 纹理资源信息（资源指针、格式等）
- `state`: 资源状态对象，管理 D3D12 资源状态转换
- `label`: 可选的调试标签（用于 PIX 等调试工具）

#### GetD3DResourceState

```cpp
sk_sp<GrD3DResourceState> GetD3DResourceState(const GrBackendTexture&);
```

**功能：** 从后端纹理提取 D3D12 资源状态

**返回值：** 资源状态的智能指针

**使用场景：**
- 同步跨 API 的资源状态
- 手动管理资源转换
- 调试资源状态问题

### 命名空间 GrBackendRenderTargets

提供创建和查询 D3D12 后端渲染目标的函数。

#### MakeD3D

```cpp
GrBackendRenderTarget MakeD3D(int width,
                              int height,
                              const GrD3DTextureResourceInfo& d3dInfo,
                              sk_sp<GrD3DResourceState> state);
```

**功能：** 从 D3D12 资源信息创建后端渲染目标

**参数说明：** 与纹理版本相同（不包含 label 参数）

#### GetD3DResourceState

```cpp
sk_sp<GrD3DResourceState> GetD3DResourceState(const GrBackendRenderTarget&);
```

**功能：** 从后端渲染目标提取 D3D12 资源状态

## 公共 API 函数

### GrBackendTextures::MakeD3D

**函数签名：**
```cpp
GrBackendTexture MakeD3D(int width,
                         int height,
                         const GrD3DTextureResourceInfo& d3dInfo,
                         sk_sp<GrD3DResourceState> state,
                         std::string_view label = {});
```

**功能：** 创建包装 D3D12 纹理的后端对象

**D3DTextureResourceInfo 内容：**
```cpp
struct GrD3DTextureResourceInfo {
    ID3D12Resource* fResource;           // D3D12 资源指针
    D3D12_RESOURCE_STATES fResourceState; // 初始资源状态
    DXGI_FORMAT fFormat;                 // 像素格式
    uint32_t fLevelCount;                // Mipmap 级别数
    // ...
};
```

**使用示例：**
```cpp
// 创建 D3D12 纹理
ID3D12Resource* d3dTexture = ...;
GrD3DTextureResourceInfo info = {
    d3dTexture,
    D3D12_RESOURCE_STATE_COMMON,
    DXGI_FORMAT_R8G8B8A8_UNORM,
    1
};
auto state = sk_make_sp<GrD3DResourceState>(D3D12_RESOURCE_STATE_COMMON);
auto backendTex = GrBackendTextures::MakeD3D(
    width, height, info, state, "MyTexture");
```

### GrBackendTextures::GetD3DResourceState

**函数签名：**
```cpp
sk_sp<GrD3DResourceState> GetD3DResourceState(const GrBackendTexture&);
```

**功能：** 提取资源状态对象

**使用场景：**
```cpp
auto backendTex = ...;
auto state = GrBackendTextures::GetD3DResourceState(backendTex);
if (state) {
    D3D12_RESOURCE_STATES currentState = state->getResourceState();
    // 根据当前状态插入转换屏障
}
```

### GrBackendRenderTargets::MakeD3D

**函数签名：**
```cpp
GrBackendRenderTarget MakeD3D(int width,
                              int height,
                              const GrD3DTextureResourceInfo& d3dInfo,
                              sk_sp<GrD3DResourceState> state);
```

**功能：** 创建包装 D3D12 渲染目标的后端对象

**典型使用场景：**
- 包装交换链缓冲区
- 创建离屏渲染目标
- 跨 API 渲染目标共享

**示例：**
```cpp
// 获取交换链后缓冲
IDXGISwapChain3* swapChain = ...;
ID3D12Resource* backBuffer = nullptr;
swapChain->GetBuffer(0, IID_PPV_ARGS(&backBuffer));

GrD3DTextureResourceInfo info = {
    backBuffer,
    D3D12_RESOURCE_STATE_PRESENT,
    DXGI_FORMAT_R8G8B8A8_UNORM,
    1
};
auto state = sk_make_sp<GrD3DResourceState>(D3D12_RESOURCE_STATE_PRESENT);
auto backendRT = GrBackendRenderTargets::MakeD3D(
    width, height, info, state);
```

### GrBackendRenderTargets::GetD3DResourceState

**函数签名：**
```cpp
sk_sp<GrD3DResourceState> GetD3DResourceState(const GrBackendRenderTarget&);
```

**功能：** 从渲染目标提取资源状态

## 内部实现细节

### GrD3DResourceState

资源状态类管理 D3D12 资源转换：

**核心功能：**
```cpp
class GrD3DResourceState {
public:
    D3D12_RESOURCE_STATES getResourceState() const;
    void setResourceState(D3D12_RESOURCE_STATES state);

    // 队列所有权转移
    void setQueueFamilyIndex(uint32_t queueFamilyIndex);

private:
    D3D12_RESOURCE_STATES fState;
    uint32_t fQueueFamilyIndex;
};
```

**状态转换：**
- `COMMON`: 通用状态
- `RENDER_TARGET`: 渲染目标
- `PIXEL_SHADER_RESOURCE`: 着色器资源
- `COPY_SOURCE`/`COPY_DEST`: 复制操作
- `PRESENT`: 呈现状态

### 调试标签支持

```cpp
std::string_view label = {}
```

**用途：**
- Windows PIX 调试器标识
- RenderDoc 资源命名
- 调试日志输出

**D3D12 集成：**
```cpp
if (!label.empty()) {
    std::wstring wLabel(label.begin(), label.end());
    d3dResource->SetName(wLabel.c_str());
}
```

### 头文件依赖

```cpp
#include "include/core/SkRefCnt.h"  // 智能指针

// 前向声明
class GrBackendTexture;
class GrBackendRenderTarget;
class GrD3DResourceState;
```

**设计优势：**
- 减少编译时依赖
- 加快编译速度
- 避免循环依赖

## 依赖关系

### 直接依赖

1. **GrD3DTextureResourceInfo**
   - D3D12 资源描述符
   - 像素格式、尺寸等信息

2. **GrD3DResourceState**
   - 资源状态管理
   - 支持状态跟踪和转换

3. **GrBackendTexture/GrBackendRenderTarget**
   - 后端无关的表面抽象
   - 统一的接口层

4. **SkRefCnt**
   - 引用计数基础设施
   - 智能指针支持

### 被依赖模块

1. **GrD3DGpu 实现**
   - 使用工厂函数创建后端表面
   - 管理资源状态转换

2. **客户端代码**
   - 应用程序导入 D3D12 资源
   - 实现自定义资源管理

3. **交换链集成**
   - 包装窗口系统缓冲区
   - 实现渲染到窗口

## 设计模式与设计决策

### 1. 工厂方法模式

使用命名空间函数作为工厂：

**优势：**
- 与其他后端保持一致
- 避免构造函数重载冲突
- 清晰的 API 分组

### 2. 显式状态管理

要求调用者提供 `GrD3DResourceState`：

**原因：**
- D3D12 的资源转换屏障需要显式管理
- 支持多队列和异步计算
- 允许精确控制性能关键路径

### 3. 智能指针所有权

使用 `sk_sp<GrD3DResourceState>`：

**优势：**
- 自动生命周期管理
- 支持状态共享
- 线程安全的引用计数

### 4. 可选调试标签

```cpp
std::string_view label = {}
```

**设计理由：**
- 生产代码无开销
- 调试时提供有用信息
- 符合现代 C++ 最佳实践

### 5. 版本标注

```cpp
/*
 * Copyright 2026 Google LLC
 */
```

**注意：** 这是较新的文件（2026 年），可能是 Skia 对 D3D12 支持的最新完善

## 性能考量

### 1. 零拷贝资源导入

与 Vulkan 版本类似，实现零拷贝：

**机制：**
- 仅包装 D3D12 资源句柄
- 不进行数据复制
- 共享原始 GPU 内存

### 2. 资源状态同步开销

D3D12 的资源屏障有成本：

**开销来源：**
- 状态跟踪需要检查
- 转换可能触发管道刷新
- 多队列同步需要围栏

**优化策略：**
- 批量提交屏障
- 最小化状态转换
- 使用 `COMMON` 状态优化

### 3. 引用计数性能

`sk_sp` 的原子操作：

**性能数据：**
- 引用计数更新：~5-10 ns
- 相比资源创建开销可忽略

### 4. 调试标签开销

```cpp
d3dResource->SetName(wLabel.c_str());
```

**影响：**
- 仅在提供标签时调用
- 驱动程序内部存储字符串
- 生产构建应禁用

### 5. 状态查询优化

```cpp
GetD3DResourceState(backendTexture);
```

**实现：**
- O(1) 查找（存储在后端对象中）
- 无需查询 D3D12 API
- 缓存友好的访问模式

## 相关文件

### 核心依赖
- `include/core/SkRefCnt.h` - 引用计数系统
- `include/gpu/d3d/GrD3DTypes.h` - D3D12 类型定义
- `src/gpu/ganesh/d3d/GrD3DResourceState.h` - 资源状态管理

### 配套实现
- `src/gpu/ganesh/d3d/GrD3DGpu.cpp` - D3D12 GPU 实现
- `src/gpu/ganesh/GrBackendSurface.cpp` - 后端表面通用实现
- `src/gpu/ganesh/d3d/GrD3DTexture.cpp` - D3D12 纹理实现

### 类似接口
- `src/gpu/ganesh/vk/GrVkBackendSurfacePriv.h` - Vulkan 版本
- `src/gpu/ganesh/mtl/GrMtlBackendSurfacePriv.h` - Metal 版本
- `src/gpu/ganesh/gl/GrGLBackendSurface.h` - OpenGL 版本

### 测试文件
- `tests/BackendSurfaceTest.cpp` - 后端表面测试
- `tests/D3DBackendSurfaceTest.cpp` - D3D12 特定测试
