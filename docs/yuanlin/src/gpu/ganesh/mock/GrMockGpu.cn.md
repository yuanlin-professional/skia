# GrMockGpu - Mock GPU 测试后端

> 源文件: `src/gpu/ganesh/mock/GrMockGpu.h`, `src/gpu/ganesh/mock/GrMockGpu.cpp`

## 概述

`GrMockGpu` 是 Ganesh GPU 后端的模拟（Mock）实现，继承自 `GrGpu`。它不执行任何实际的图形 API 调用，而是返回预配置的成功结果。主要用于 Skia 的单元测试和基准测试，允许在无 GPU 硬件的环境中测试 Ganesh 渲染管线的逻辑正确性。

## 架构位置

```
GrGpu (抽象基类)
    |
    +-- GrGLGpu   (OpenGL)
    +-- GrVkGpu   (Vulkan)
    +-- GrMtlGpu  (Metal)
    +-- GrMockGpu (本文件 - Mock 测试)
```

## 主要类与结构体

### `GrMockGpu`

继承自 `GrGpu`。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fMockOptions` | `GrMockOptions` | Mock 配置选项 |
| `fOutstandingTestingOnlyTextureIDs` | `THashSet<int>` | 跟踪未释放的测试纹理 ID |

## 公共 API 函数

### `Make()`

```cpp
static std::unique_ptr<GrGpu> Make(const GrMockOptions*, const GrContextOptions&, GrDirectContext*);
```

工厂方法，创建 Mock GPU 实例和对应的 `GrMockCaps`。

### 空操作实现

大多数虚方法返回 `true`（成功）或空/`nullptr`：
- `makeSemaphore()` / `wrapBackendSemaphore()`: 返回 `nullptr`。
- `insertSemaphore()` / `waitSemaphore()`: 空操作。
- `onReadPixels()` / `onWritePixels()`: 始终返回 `true`。
- `onCopySurface()`: 始终返回 `true`。
- `onSubmitToGpu()`: 始终返回 `true`。
- `compile()`: 返回 `false`。

### 资源创建

`onCreateTexture`、`onCreateBuffer`、`onCreateBackendTexture` 创建轻量级模拟对象，使用静态递增 ID 进行跟踪。

## 内部实现细节

### ID 分配

通过四个静态方法生成递增的唯一 ID：
- `NextInternalTextureID()` / `NextExternalTextureID()`
- `NextInternalRenderTargetID()` / `NextExternalRenderTargetID()`

### 纹理生命周期跟踪

测试纹理的 ID 被存储在 `fOutstandingTestingOnlyTextureIDs` 中，`isTestingOnlyBackendTexture` 通过查找此集合验证纹理是否有效。

## 依赖关系

- **上游依赖**: `GrGpu`（基类）、`GrMockOptions`（配置）。
- **同层依赖**: `GrMockCaps`（Mock 能力）。
- **被依赖**: Skia 测试框架、DM 测试工具。

## 设计模式与设计决策

1. **空对象模式**: 所有操作返回成功或空结果，不产生实际 GPU 副作用。
2. **可配置能力**: 通过 `GrMockOptions` 控制 Mock 后端报告的能力（如纹理格式支持、最大纹理尺寸等）。
3. **资源跟踪**: 即使是 Mock 实现也追踪资源生命周期，支持泄漏检测测试。

## 性能考量

Mock 后端不执行 GPU 操作，极低开销，适合大规模自动化测试。

## 相关文件

- `src/gpu/ganesh/mock/GrMockCaps.h` - Mock 能力类
- `include/gpu/ganesh/mock/GrMockTypes.h` - Mock 类型定义
- `src/gpu/ganesh/GrGpu.h` - GPU 抽象基类
