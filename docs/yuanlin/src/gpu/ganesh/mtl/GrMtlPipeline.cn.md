# GrMtlPipeline

> 源文件: src/gpu/ganesh/mtl/GrMtlPipeline.h

## 概述

`GrMtlRenderPipeline` 是 Skia Ganesh GPU 后端中对 Metal 渲染管线状态对象（`MTLRenderPipelineState`）的轻量级封装类。该类继承自 `GrManagedResource`，提供了智能的生命周期管理和 GPU 资源追踪功能。Metal 的渲染管线状态对象是一个不可变对象，封装了顶点着色器、片段着色器、混合状态、光栅化状态等所有渲染状态。

该类的设计非常简洁，主要职责是包装 Metal 原生对象并提供 Skia 资源管理系统所需的接口。

## 架构位置

在 Skia 的 Metal 后端架构中的位置：

```
skia/
├── src/
    └── gpu/
        └── ganesh/
            ├── GrManagedResource.h              # 资源管理基类
            └── mtl/
                ├── GrMtlPipeline.h              # 本文件
                ├── GrMtlGpu.cpp                 # 创建管线对象
                ├── GrMtlRenderCommandEncoder.h  # 使用管线对象
                └── GrMtlPipelineStateBuilder.h  # 构建管线
```

该类在渲染流程中的角色：
- **创建**: `GrMtlPipelineStateBuilder` 构建管线状态
- **缓存**: `GrMtlGpu` 缓存已创建的管线对象
- **使用**: `GrMtlRenderCommandEncoder` 绑定管线进行渲染
- **销毁**: 引用计数为 0 时自动释放 GPU 资源

## 主要类与结构体

### GrMtlRenderPipeline

**继承关系：**
```cpp
class GrMtlRenderPipeline : public GrManagedResource
```

**核心成员：**
```cpp
private:
    mutable id<MTLRenderPipelineState> fPipelineState;
```

- 使用 `mutable` 修饰符允许在 `const` 方法中修改（用于资源释放）
- 存储 Metal 原生的渲染管线状态对象
- 使用 Objective-C 的引用计数管理内存

## 公共 API 函数

### 工厂方法

```cpp
static sk_sp<GrMtlRenderPipeline> Make(id<MTLRenderPipelineState> pso)
```

**功能：** 创建管线对象包装器

**参数：**
- `pso`: Metal 原生的渲染管线状态对象

**返回值：** 智能指针 `sk_sp`，自动管理引用计数

**使用示例：**
```cpp
id<MTLRenderPipelineState> mtlPSO = [device newRenderPipelineStateWithDescriptor:desc error:&error];
auto pipeline = GrMtlRenderPipeline::Make(mtlPSO);
```

### 调试信息输出

```cpp
#ifdef SK_TRACE_MANAGED_RESOURCES
void dumpInfo() const override
#endif
```

**功能：** 在启用资源追踪时输出调试信息

**输出格式：**
```
GrMtlRenderPipeline: 0x1234567890 (2 refs)
```

**用途：**
- 诊断资源泄漏
- 分析资源使用情况
- 调试引用计数问题

### GPU 资源释放

```cpp
void freeGPUData() const override
```

**功能：** 释放 GPU 资源

**实现：**
```cpp
fPipelineState = nil;  // 触发 ARC 释放
```

**调用时机：**
- 对象引用计数降为 0 时
- 上下文销毁时强制清理
- 内存压力时主动释放缓存

### 访问器

```cpp
id<MTLRenderPipelineState> mtlPipelineState() const
```

**功能：** 获取底层 Metal 管线状态对象

**返回值：** Metal 原生的 PSO 对象

**使用场景：**
```cpp
auto pipeline = ...;
encoder->setRenderPipelineState(pipeline->mtlPipelineState());
```

## 内部实现细节

### 构造函数

```cpp
private:
GrMtlRenderPipeline(id<MTLRenderPipelineState> pso)
    : GrManagedResource()
    , fPipelineState(pso) {
}
```

**设计特点：**
- 私有构造函数，强制使用工厂方法
- 调用基类构造函数初始化资源管理
- 直接存储 Metal 对象引用

### 资源管理

**GrManagedResource 继承的功能：**
1. **引用计数**: 使用 `sk_sp` 智能指针管理
2. **资源追踪**: 在调试模式下追踪所有活跃资源
3. **延迟释放**: 可在适当时机批量释放资源

### Metal 对象生命周期

**ARC（Automatic Reference Counting）机制：**
```cpp
id<MTLRenderPipelineState> fPipelineState;
```

- Objective-C 对象自动引用计数
- 赋值时自动 retain
- 设为 `nil` 时自动 release
- 与 C++ 的 `sk_sp` 配合工作

### mutable 成员变量

```cpp
mutable id<MTLRenderPipelineState> fPipelineState;
```

**原因：**
- `freeGPUData()` 是 `const` 方法（基类接口要求）
- 需要在该方法中设置 `fPipelineState = nil`
- `mutable` 允许在 `const` 方法中修改

## 依赖关系

### 直接依赖

1. **GrManagedResource** (src/gpu/ganesh/GrManagedResource.h)
   - 提供资源管理基础设施
   - 引用计数和生命周期管理
   - 资源追踪和调试支持

2. **Metal.framework**
   - `MTLRenderPipelineState` 协议
   - Metal 原生 API

### 被依赖模块

1. **GrMtlGpu** - 创建和缓存管线对象
2. **GrMtlRenderCommandEncoder** - 使用管线对象进行渲染
3. **GrMtlOpsRenderPass** - 间接使用（通过编码器）
4. **GrMtlPipelineStateBuilder** - 构建管线状态

## 设计模式与设计决策

### 1. 包装器模式（Wrapper Pattern）

将 Metal 原生对象包装在 Skia 对象中：

**优势：**
- 统一的资源管理接口
- 跨平台的抽象层
- 添加调试和追踪功能
- 控制对象创建和销毁

### 2. 工厂方法模式

使用静态工厂方法创建对象：

```cpp
static sk_sp<GrMtlRenderPipeline> Make(...)
```

**优势：**
- 隐藏构造细节
- 强制使用智能指针
- 可添加创建失败处理
- 保证对象正确初始化

### 3. RAII 资源管理

使用 C++ 的 RAII 结合智能指针：

**机制：**
- `sk_sp` 自动管理引用计数
- 析构时自动调用 `freeGPUData()`
- 确保资源及时释放

### 4. 最小接口原则

类接口极其简洁：
- 仅暴露必要的访问器
- 隐藏实现细节
- 降低耦合度

### 5. 不可变对象

Metal 的 PSO 本身是不可变的：

**优势：**
- 线程安全
- 可安全缓存和共享
- 驱动程序可优化
- 减少状态变化错误

## 性能考量

### 1. 管线状态对象创建开销

**问题：**
- PSO 创建是昂贵的操作（可能需要数毫秒）
- 涉及着色器编译、状态验证、驱动优化

**优化策略：**
- 缓存已创建的 PSO
- 异步创建管线对象
- 使用管线库预热

**性能数据：**
- 创建时间：1-10 ms（取决于复杂度）
- 查找缓存：~100 ns
- 绑定 PSO：~100-500 ns

### 2. 缓存策略

**缓存键：**
```cpp
struct PipelineKey {
    程序描述符 (着色器、入口点)
    + 渲染状态 (混合、深度、模板)
    + 顶点布局
    + 像素格式
};
```

**缓存容量：**
- 通常限制为 100-1000 个 PSO
- 使用 LRU 淘汰策略
- 内存压力时清理缓存

### 3. 引用计数开销

**sk_sp 的性能影响：**
- 原子操作：~5-10 ns
- 相比 PSO 创建和绑定开销可忽略
- 线程安全的保证

### 4. 内存占用

**单个 PSO 的内存：**
- 对象本身：~64 bytes
- Metal 驱动内部状态：~1-10 KB
- 着色器代码：~10-100 KB

**管理策略：**
- 及时释放不再使用的 PSO
- 监控内存使用
- 实施缓存大小限制

### 5. 资源追踪开销

```cpp
#ifdef SK_TRACE_MANAGED_RESOURCES
void dumpInfo() const override { ... }
#endif
```

**影响：**
- 仅在调试构建启用
- 生产构建零开销
- 帮助诊断资源泄漏

## 相关文件

### 核心依赖
- `src/gpu/ganesh/GrManagedResource.h` - 资源管理基类
- `Metal/Metal.h` - Metal 框架

### 配套实现
- `src/gpu/ganesh/mtl/GrMtlPipelineStateBuilder.h` - 构建管线状态
- `src/gpu/ganesh/mtl/GrMtlPipelineStateBuilder.cpp` - 构建实现
- `src/gpu/ganesh/mtl/GrMtlGpu.cpp` - GPU 实现，管理缓存

### 使用者
- `src/gpu/ganesh/mtl/GrMtlRenderCommandEncoder.h` - 绑定管线
- `src/gpu/ganesh/mtl/GrMtlOpsRenderPass.cpp` - 渲染通道

### 类似类
- `src/gpu/ganesh/vk/GrVkPipeline.h` - Vulkan 版本
- `src/gpu/ganesh/d3d/GrD3DPipeline.h` - Direct3D 版本
- `src/gpu/ganesh/gl/GrGLProgram.h` - OpenGL 版本（不同设计）

### 测试文件
- `tests/MtlPipelineTest.cpp` - 管线对象测试
- `tests/ResourceCacheTest.cpp` - 资源缓存测试
