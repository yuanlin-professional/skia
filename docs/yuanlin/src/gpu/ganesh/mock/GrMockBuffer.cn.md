# GrMockBuffer — Mock 后端 GPU 缓冲区

> 源文件: `src/gpu/ganesh/mock/GrMockBuffer.h`

## 概述

`GrMockBuffer` 是 Mock GPU 后端中 `GrGpuBuffer` 的具体实现。它模拟 GPU 缓冲区的行为（如顶点缓冲区、索引缓冲区、uniform 缓冲区等），在测试环境中提供完整的缓冲区生命周期管理，但不执行实际的 GPU 数据传输。映射操作使用堆内存模拟，数据更新操作直接返回成功。

## 架构位置

```
GrGpu (抽象 GPU 接口)
    └── GrMockGpu (Mock GPU)
        └── GrGpuBuffer (缓冲区基类)
            └── GrMockBuffer (本文件 - Mock 缓冲区)
                └── GrResourceCache (资源缓存)
```

## 主要类与结构体

### GrMockBuffer

继承自 `GrGpuBuffer`，实现所有必要的虚函数：

| 方法 | 描述 |
|------|------|
| 构造函数 | 创建缓冲区并注册到资源缓存 |
| `onMap()` | 如果 caps 支持映射，分配堆内存模拟映射 |
| `onUnmap()` | 释放映射的堆内存 |
| `onClearToZero()` | 无操作，直接返回成功 |
| `onUpdateData()` | 无操作，直接返回成功 |

## 公共 API 函数

### 构造函数

```cpp
GrMockBuffer(GrMockGpu* gpu, size_t sizeInBytes, GrGpuBufferType type,
              GrAccessPattern accessPattern, std::string_view label);
```

创建指定大小和类型的 Mock 缓冲区。参数：
- `type`: 缓冲区类型（顶点、索引、uniform 等）
- `accessPattern`: 访问模式（静态、动态、流式）
- `label`: 调试标签

创建后立即通过 `registerWithCache(Budgeted::kYes)` 注册到资源缓存。

## 内部实现细节

1. **条件映射**: `onMap()` 检查 GPU caps 的 `mapBufferFlags()`。只有当 Mock caps 声明支持缓冲区映射时，才通过 `sk_malloc_throw()` 分配堆内存。这允许测试模拟不同的 GPU 能力配置。

2. **内存管理**: 映射时分配的内存在 `onUnmap()` 中通过 `sk_free()` 释放。使用 Skia 的内存分配函数而非标准 `malloc`/`free`。

3. **空操作更新**: `onClearToZero()` 和 `onUpdateData()` 直接返回 true，不执行实际数据操作。Mock 后端只需要验证调用流程正确性，不需要真实数据。

4. **fMapPtr**: 基类 `GrGpuBuffer` 的成员，在 `onMap()` 中设置，供调用者通过 `map()` 方法获取映射指针。

## 依赖关系

- **`src/gpu/ganesh/GrGpuBuffer.h`**: GPU 缓冲区基类
- **`src/gpu/ganesh/GrGpu.h`**: GPU 接口（获取 caps）
- **`src/gpu/ganesh/GrCaps.h`**: GPU 能力查询（`mapBufferFlags()`）
- **`src/gpu/ganesh/mock/GrMockGpu.h`**: Mock GPU 实现
- **`include/private/base/SkMalloc.h`**: `sk_malloc_throw()`, `sk_free()`
- **`include/gpu/GpuTypes.h`**: `Budgeted`

## 设计模式与设计决策

1. **测试替身**: 与 `GrMockAttachment` 类似，提供 `GrGpuBuffer` 的最小有效实现用于测试。

2. **能力感知模拟**: `onMap()` 根据 caps 决定是否支持映射，使测试可以覆盖"不支持缓冲区映射"的 GPU 场景。

3. **头文件内联实现**: 所有方法实现均在头文件中，因为代码量极少。

4. **自动缓存注册**: 与真实后端行为一致，构造后立即注册到资源缓存，确保缓存逻辑得到测试覆盖。

## 性能考量

- Mock 后端不涉及 GPU 性能。
- `onMap()` 的堆分配模拟了真实缓冲区映射的内存使用模式，有助于检测内存泄漏。
- `onUpdateData()` 的空操作意味着测试不验证数据内容正确性，只验证 API 调用序列。

## 相关文件

- `src/gpu/ganesh/GrGpuBuffer.h` — GPU 缓冲区基类
- `src/gpu/ganesh/mock/GrMockGpu.h` — Mock GPU 实现
- `src/gpu/ganesh/mock/GrMockAttachment.h` — Mock 附件实现
- `src/gpu/ganesh/gl/GrGLBuffer.h` — OpenGL 缓冲区实现（对比参考）
- `src/gpu/ganesh/vk/GrVkBuffer.h` — Vulkan 缓冲区实现（对比参考）
