# GrVkPipelineStateDataManager

> 源文件
> - src/gpu/ganesh/vk/GrVkPipelineStateDataManager.h
> - src/gpu/ganesh/vk/GrVkPipelineStateDataManager.cpp

## 概述

`GrVkPipelineStateDataManager` 是 Skia Ganesh Vulkan 后端中负责管理 uniform 数据的核心类。它继承自 `GrUniformDataManager`，专门处理 Vulkan 的 uniform 缓冲区和推送常量（push constants）两种 uniform 数据传输机制。

该类的主要职责包括：
- 根据 uniform 布局信息初始化数据管理器
- 支持 std140（uniform buffer）和 std430（push constants）两种内存布局
- 提供统一接口设置各种类型的 uniform 数据
- 将 uniform 数据上传到 GPU（通过 uniform buffer 或 push constants）
- 管理 uniform buffer 的生命周期

## 架构位置

`GrVkPipelineStateDataManager` 在 Vulkan 渲染管线中的位置：

```
Skia Ganesh 渲染管线
  └─ Vulkan 后端
      ├─ GrVkGpu (设备管理)
      ├─ GrVkPipelineState (管线状态)
      │   └─ GrVkPipelineStateDataManager (uniform 数据管理) ← 当前类
      ├─ GrVkUniformHandler (uniform 布局处理)
      └─ GrVkCommandBuffer (命令提交)
```

该类是连接高层 uniform 设置接口和底层 Vulkan API 的桥梁。

## 主要类与结构体

### 继承关系

| 类名 | 父类 | 说明 |
|------|------|------|
| `GrVkPipelineStateDataManager` | `GrUniformDataManager` | Vulkan 专用的 uniform 数据管理器 |
| `GrUniformDataManager` | 无 | 平台无关的 uniform 数据管理基类 |

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fUniformBuffer` | `sk_sp<GrGpuBuffer>` | 存储 uniform 数据的 GPU 缓冲区（使用 UBO 时） |
| `fUsePushConstants` | `bool` | 是否使用推送常量而非 uniform buffer |
| `fUniforms` | 继承自基类 | uniform 元数据数组（偏移、类型等） |
| `fUniformData` | 继承自基类 | CPU 端 uniform 数据缓冲区 |
| `fUniformsDirty` | 继承自基类 | uniform 数据脏标记 |
| `fUniformSize` | 继承自基类 | uniform 数据总大小 |

## 公共 API 函数

### 构造函数

```cpp
GrVkPipelineStateDataManager(
    const UniformInfoArray& uniforms,
    uint32_t uniformSize,
    bool usePushConstants);
```
根据 uniform 布局信息和使用模式初始化数据管理器。`usePushConstants` 决定使用 std430（推送常量）还是 std140（uniform buffer）布局。

### Uniform 上传

```cpp
std::pair<sk_sp<GrGpuBuffer>, bool> uploadUniforms(
    GrVkGpu* gpu,
    VkPipelineLayout layout,
    GrVkCommandBuffer* commandBuffer);
```
将 uniform 数据上传到 GPU。返回 uniform buffer（使用 UBO 时）和成功标志。对于推送常量，直接通过命令缓冲区推送数据。

### 资源释放

```cpp
void releaseData();
```
释放 uniform buffer 资源，用于清理缓存的 GPU 缓冲区。

### Uniform 设置方法

```cpp
void set1iv(UniformHandle, int arrayCount, const int32_t v[]) const override;
void set1fv(UniformHandle, int arrayCount, const float v[]) const override;
void set2iv(UniformHandle, int arrayCount, const int32_t v[]) const override;
void set2fv(UniformHandle, int arrayCount, const float v[]) const override;
void setMatrix2fv(UniformHandle, int arrayCount, const float matrices[]) const override;
```
设置不同类型的 uniform 值。当使用推送常量时，这些方法直接写入内存；否则委托给基类的实现。

## 内部实现细节

### 两种 Uniform 传输机制

**Uniform Buffer Objects (UBO)**：
- 使用 std140 内存布局
- 创建动态 GPU 缓冲区存储 uniform 数据
- 适合较大的 uniform 数据集
- 缓冲区在多次绘制间可重用（通过脏标记优化）
- 数据通过 `GrResourceProvider` 创建的 `GrGpuBuffer` 传输

**推送常量（Push Constants）**：
- 使用 std430 内存布局（更紧凑）
- 数据直接通过命令缓冲区推送
- 适合小量、频繁变化的 uniform 数据
- 无需创建额外的 GPU 缓冲区
- 更低的延迟，但大小受限（通常限制在 128 或 256 字节）

### 内存布局处理

构造时根据 `usePushConstants` 选择内存布局：
```cpp
GrVkUniformHandler::Layout memLayout =
    usePushConstants ? GrVkUniformHandler::kStd430Layout
                     : GrVkUniformHandler::kStd140Layout;
```

std140 和 std430 的主要区别：
- **std140**：对齐要求更严格（例如 vec3 按 vec4 对齐），兼容性更好
- **std430**：更紧凑的布局（vec3 按 vec3 对齐），节省内存

### Uniform 设置优化

当使用推送常量时，直接写入内存：
```cpp
void* buffer = this->getBufferPtrAndMarkDirty(uni);
memcpy(buffer, v, arrayCount * sizeof(float));
```

当使用 UBO 时，委托给基类处理，基类会处理 std140 的对齐和打包规则。

### 脏标记机制

仅在 uniform 数据改变且使用 UBO 时重新创建缓冲区：
```cpp
if (fUniformsDirty) {
    fUniformBuffer = resourceProvider->createBuffer(...);
    fUniformsDirty = false;
}
```

这避免了每帧都创建新的 GPU 缓冲区。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrUniformDataManager` | 基类，提供通用 uniform 管理功能 |
| `GrVkUniformHandler` | 提供 uniform 布局信息和内存布局常量 |
| `GrVkGpu` | 访问 Vulkan 设备、能力和上下文 |
| `GrVkCommandBuffer` | 推送常量到命令缓冲区 |
| `GrResourceProvider` | 创建 GPU 缓冲区 |
| `GrGpuBuffer` | GPU 缓冲区抽象 |
| `GrVkCaps` | 查询推送常量的 stage flags |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| `GrVkPipelineState` | 持有数据管理器实例，用于设置和上传 uniform |
| `GrVkOpsRenderPass` | 通过管线状态间接使用 |

## 设计模式与设计决策

### 策略模式
通过 `fUsePushConstants` 标志在两种 uniform 传输策略间切换。这种设计允许在运行时选择最优策略，而不需要创建不同的子类。

### 统一接口
尽管内部实现不同（UBO vs 推送常量），但对外提供统一的 `setXxx` 接口，隐藏了底层差异。

### 延迟创建
仅在实际需要时（`uploadUniforms` 调用时）才创建 GPU 缓冲区，避免不必要的资源分配。

### 脏标记优化
使用脏标记避免重复创建缓冲区。当 uniform 数据未改变时，可以重用之前的缓冲区。

### 类型安全
通过断言检查 uniform 类型匹配，在调试模式下捕获类型错误：
```cpp
SkASSERT(uni.type() == SkSLType::kFloat2 || uni.type() == SkSLType::kHalf2);
```

## 性能考量

### 推送常量优势
对于小量 uniform 数据，推送常量比 UBO 更高效：
- 无需创建和绑定 GPU 缓冲区
- 数据直接嵌入命令流
- 更低的 CPU 和 GPU 开销

### UBO 优势
对于较大的 uniform 数据集，UBO 更合适：
- 可以在多次绘制间共享
- 避免推送常量的大小限制
- 更好的缓存局部性

### 内存布局选择
- std430 比 std140 更节省内存，特别是对于包含 vec3 的结构体
- 推送常量使用 std430 可以在有限的空间内容纳更多数据

### 缓冲区重用
通过脏标记机制，避免每帧重新创建 uniform buffer，减少内存分配和驱动开销。

### 直接内存拷贝
使用 `memcpy` 直接拷贝数据，避免逐元素赋值的开销：
```cpp
memcpy(buffer, v, arrayCount * 2 * sizeof(float));
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/ganesh/GrUniformDataManager.h` | 父类 | 平台无关的 uniform 管理基类 |
| `src/gpu/ganesh/vk/GrVkUniformHandler.h` | 协作 | 处理 uniform 布局和绑定 |
| `src/gpu/ganesh/vk/GrVkPipelineState.h` | 使用者 | 持有并使用该数据管理器 |
| `src/gpu/ganesh/vk/GrVkGpu.h` | 依赖 | 提供 Vulkan 设备接口 |
| `src/gpu/ganesh/vk/GrVkCommandBuffer.h` | 依赖 | 推送常量接口 |
| `src/gpu/ganesh/GrResourceProvider.h` | 依赖 | 创建 GPU 缓冲区 |
| `src/gpu/ganesh/GrGpuBuffer.h` | 依赖 | GPU 缓冲区抽象 |
