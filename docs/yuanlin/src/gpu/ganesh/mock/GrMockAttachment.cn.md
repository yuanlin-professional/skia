# GrMockAttachment — Mock 后端附件实现

> 源文件: `src/gpu/ganesh/mock/GrMockAttachment.h`

## 概述

`GrMockAttachment` 是 Mock GPU 后端中 `GrAttachment` 的具体实现，用于模拟模板缓冲区附件 (stencil attachment)。Mock 后端是 Skia 的测试后端，不执行实际 GPU 操作，但完整模拟 GPU 资源管理流程。此类专门用于模板附件，在构造时通过断言确保仅用于此用途。

## 架构位置

```
GrGpu (抽象 GPU 接口)
    └── GrMockGpu (Mock GPU 实现)
        └── GrAttachment (附件基类)
            └── GrMockAttachment (本文件 - Mock 模板附件)
                └── GrResourceCache (资源缓存)
```

## 主要类与结构体

### GrMockAttachment

继承自 `GrAttachment`，仅重写必要的虚函数。

| 成员/方法 | 描述 |
|-----------|------|
| 构造函数 | 接受 GPU、尺寸、用途标志、采样数和标签，强制无 mipmap、无保护模式 |
| `backendFormat()` | 返回 Mock 模板格式 (`GrBackendFormats::MakeMockStencilFormat()`) |

构造函数特征：
- `supportedUsages` 必须为 `kStencilAttachment`（通过 `SkASSERT` 验证）
- `Mipmapped::kNo` — 模板缓冲区不使用 mipmap
- `Protected::kNo` — 不使用保护模式
- 自动注册到资源缓存 (`skgpu::Budgeted::kYes`)

## 公共 API 函数

### 构造函数

```cpp
GrMockAttachment(GrMockGpu* gpu, SkISize dimensions, UsageFlags supportedUsages,
                  int sampleCnt, std::string_view label);
```

创建 Mock 模板附件。`supportedUsages` 必须为 `kStencilAttachment`。创建后立即注册到资源缓存中。

### backendFormat()

```cpp
GrBackendFormat backendFormat() const override;
```

返回 Mock 模板后端格式，通过 `GrBackendFormats::MakeMockStencilFormat()` 创建。

## 内部实现细节

1. **仅限模板附件**: 通过 `SkASSERT` 断言确保此类仅用于模板附件，不支持颜色或深度附件。
2. **立即缓存注册**: 构造时调用 `registerWithCache(Budgeted::kYes)`，将资源纳入 Ganesh 的资源缓存管理。
3. **最小实现**: 仅覆盖 `backendFormat()` 虚函数，其余行为继承自 `GrAttachment` 基类。

## 依赖关系

- **`src/gpu/ganesh/GrAttachment.h`**: 附件基类
- **`src/gpu/ganesh/mock/GrMockGpu.h`**: Mock GPU 实现
- **`include/gpu/ganesh/mock/GrMockBackendSurface.h`**: `MakeMockStencilFormat()`
- **`include/gpu/ganesh/GrBackendSurface.h`**: `GrBackendFormat`
- **`include/gpu/GpuTypes.h`**: `Mipmapped`, `Protected`, `Budgeted`

## 设计模式与设计决策

1. **测试替身 (Test Double)**: 作为 Mock 对象，提供 `GrAttachment` 的最小有效实现，用于在不依赖真实 GPU 的情况下测试资源管理和渲染管线逻辑。

2. **单一职责**: 仅处理模板附件类型，通过断言而非运行时检查来强制约束，体现测试代码中"快速失败"的理念。

3. **内联头文件实现**: 整个类实现在头文件中，因为代码量极少且 Mock 后端不关心编译性能。

## 性能考量

- Mock 后端不执行 GPU 操作，性能考量仅限于内存分配。
- 资源缓存注册使得 Mock 附件参与正常的缓存淘汰流程，确保测试行为与真实后端一致。

## 相关文件

- `src/gpu/ganesh/GrAttachment.h` — 附件基类
- `src/gpu/ganesh/mock/GrMockGpu.h` — Mock GPU 实现
- `src/gpu/ganesh/mock/GrMockBuffer.h` — Mock 缓冲区实现
- `src/gpu/ganesh/gl/GrGLAttachment.h` — OpenGL 附件实现（对比参考）
- `src/gpu/ganesh/vk/GrVkAttachment.h` — Vulkan 附件实现（对比参考）
