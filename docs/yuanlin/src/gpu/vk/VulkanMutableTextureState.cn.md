# VulkanMutableTextureState

> 源文件：
> - include/gpu/vk/VulkanMutableTextureState.h
> - src/gpu/vk/VulkanMutableTextureState.cpp

## 概述

`VulkanMutableTextureState` 是 Skia 中用于封装和管理 Vulkan 纹理可变状态的模块，主要包括图像布局（`VkImageLayout`）和队列家族索引（`queueFamilyIndex`）。该模块提供了后端无关的 `MutableTextureState` 接口的 Vulkan 实现，允许在跨队列或跨上下文操作时正确传递和管理纹理状态。

这是一个轻量级的状态管理模块，专注于纹理状态的创建、访问和修改，是 Skia GPU 后端多后端抽象架构的一部分。

## 架构位置

该模块位于 Skia GPU 层次结构中的 Vulkan 后端：

```
skia/
├── include/
│   └── gpu/
│       ├── MutableTextureState.h           # 后端无关的状态接口
│       └── vk/
│           └── VulkanMutableTextureState.h # Vulkan 公共 API
└── src/
    └── gpu/
        ├── MutableTextureStatePriv.h       # 内部实现辅助
        └── vk/
            ├── VulkanMutableTextureState.cpp        # Vulkan 实现
            └── VulkanMutableTextureStatePriv.h      # Vulkan 私有接口
```

该模块是 Skia 多后端纹理状态管理系统的一部分，与 Metal、Direct3D 等后端的类似模块并存。

## 主要类与结构体

### VulkanMutableTextureState（内部类）

在 `src/gpu/vk/VulkanMutableTextureState.cpp` 中定义的内部实现类。

**继承关系：**
```
MutableTextureStateData (抽象基类)
    └── VulkanMutableTextureState
```

**关键成员变量：**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fLayout` | `VkImageLayout` | Vulkan 图像布局状态 |
| `fQueueFamilyIndex` | `uint32_t` | 拥有图像的队列家族索引 |

**关键成员函数：**

| 函数签名 | 说明 |
|---------|------|
| `VulkanMutableTextureState(VkImageLayout, uint32_t)` | 构造函数，初始化布局和队列家族索引 |
| `BackendApi type() const override` | 返回 `BackendApi::kVulkan` 标识后端类型 |
| `void copyTo(AnyStateData&) const override` | 将状态复制到通用状态容器 |

### 命名空间函数（公共 API）

所有公共 API 函数都在 `skgpu::MutableTextureStates` 命名空间中定义。

## 公共 API 函数

### 状态创建

| 函数签名 | 说明 |
|---------|------|
| `MutableTextureState MakeVulkan(VkImageLayout layout, uint32_t queueFamilyIndex)` | 创建包含 Vulkan 纹理状态的 `MutableTextureState` 对象 |

### 状态读取

| 函数签名 | 说明 |
|---------|------|
| `VkImageLayout GetVkImageLayout(const MutableTextureState& state)` | 从状态对象读取图像布局（引用版本） |
| `VkImageLayout GetVkImageLayout(const MutableTextureState* state)` | 从状态对象读取图像布局（指针版本） |
| `uint32_t GetVkQueueFamilyIndex(const MutableTextureState& state)` | 从状态对象读取队列家族索引（引用版本） |
| `uint32_t GetVkQueueFamilyIndex(const MutableTextureState* state)` | 从状态对象读取队列家族索引（指针版本） |

### 状态修改（私有 API）

在 `src/gpu/vk/VulkanMutableTextureStatePriv.h` 中定义（未在公共头文件中暴露）：

| 函数签名 | 说明 |
|---------|------|
| `void SetVkImageLayout(MutableTextureState* state, VkImageLayout layout)` | 修改图像布局 |
| `void SetVkQueueFamilyIndex(MutableTextureState* state, uint32_t queueFamilyIndex)` | 修改队列家族索引 |

## 内部实现细节

### 类型安全机制

所有访问函数都使用 `get_and_cast_data()` 辅助函数确保类型安全：

```cpp
static const VulkanMutableTextureState* get_and_cast_data(const MutableTextureState& mts) {
    auto data = skgpu::MutableTextureStatePriv::GetStateData(mts);
    SkASSERT(!data || data->type() == BackendApi::kVulkan);
    return static_cast<const VulkanMutableTextureState*>(data);
}
```

**安全检查：**
1. 从 `MutableTextureState` 获取内部数据指针
2. 断言验证数据类型为 `BackendApi::kVulkan`
3. 执行静态类型转换

这种设计防止了跨后端的错误类型访问（如在 Vulkan 状态对象上调用 Metal 的访问函数）。

### 状态存储方式

`MutableTextureState` 使用类型擦除模式存储后端特定数据：
- 基类 `MutableTextureStateData` 提供虚函数接口
- `VulkanMutableTextureState` 实现 Vulkan 特定的存储和访问
- 通过 `AnyStateData`（类似 `std::any`）实现多态存储

### 对象创建流程

`MakeVulkan()` 函数的实现：

```cpp
MutableTextureState MakeVulkan(VkImageLayout layout, uint32_t queueFamilyIndex) {
    return MutableTextureStatePriv::MakeMutableTextureState(
            BackendApi::kVulkan,
            VulkanMutableTextureState(layout, queueFamilyIndex));
}
```

1. 创建 `VulkanMutableTextureState` 临时对象
2. 调用 `MutableTextureStatePriv::MakeMutableTextureState()` 包装
3. 返回后端无关的 `MutableTextureState` 对象

### 状态访问实现

读取函数的实现模式：

```cpp
VkImageLayout GetVkImageLayout(const MutableTextureState& state) {
    SkASSERT(state.backend() == BackendApi::kVulkan);  // 验证后端类型
    return get_and_cast_data(state)->fLayout;           // 类型转换并访问
}
```

每次访问都包含：
1. 后端类型断言检查
2. 安全的类型转换
3. 成员变量访问

### 状态修改实现

修改函数直接操作内部数据：

```cpp
void SetVkImageLayout(MutableTextureState* state, VkImageLayout layout) {
    SkASSERT(state->backend() == BackendApi::kVulkan);
    get_and_cast_data(state)->fLayout = layout;
}
```

**注意：** 修改函数不是公共 API，仅供 Skia 内部使用。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/gpu/MutableTextureState.h` | 后端无关的状态接口定义 |
| `include/gpu/GpuTypes.h` | `BackendApi` 枚举定义 |
| `include/private/base/SkAPI.h` | API 导出宏 |
| `include/private/base/SkAssert.h` | 断言宏 |
| `include/private/base/SkDebug.h` | 调试支持 |
| `include/private/gpu/vk/SkiaVulkan.h` | Vulkan 类型定义 |
| `src/gpu/MutableTextureStatePriv.h` | 状态管理内部接口 |
| `src/gpu/vk/VulkanMutableTextureStatePriv.h` | Vulkan 私有接口 |

### 被依赖的模块

该模块主要被以下模块使用：

| 模块 | 使用场景 |
|------|---------|
| `VulkanTexture` | 纹理对象管理自身状态 |
| `VulkanGpu` | GPU 操作时更新纹理状态 |
| `VulkanCommandBuffer` | 记录状态转换命令 |
| Skia 公共 API | 应用程序创建和查询纹理状态 |
| 跨上下文共享 | 多个上下文共享纹理时传递状态信息 |

## 设计模式与设计决策

### 类型擦除模式

使用类型擦除（Type Erasure）隐藏后端特定实现：
- 公共接口使用 `MutableTextureState` 抽象类型
- 内部通过虚函数和类型转换访问具体实现
- 允许不同后端共存于同一代码库

### 命名空间函数而非成员函数

采用命名空间自由函数而非 `MutableTextureState` 成员函数：
- **优点**：避免污染基类接口，每个后端独立扩展
- **优点**：编译隔离，修改 Vulkan 实现不影响其他后端
- **缺点**：无法利用成员函数的 `this` 指针便利性

### 不可变性与可变性分离

- **公共 API**：只提供创建和读取接口，状态表现为不可变
- **私有 API**：提供修改接口，仅供 Skia 内部使用
- **设计理由**：控制状态修改，避免外部代码破坏一致性

### 双重检查（断言）

每个访问函数都包含后端类型断言：
- 第一层：在调用点检查 `state.backend() == BackendApi::kVulkan`
- 第二层：在 `get_and_cast_data()` 中再次断言
- **目的**：尽早发现类型错误，提供清晰的错误信息

### 值语义与指针语义

提供引用和指针两种重载版本：
- 引用版本：适用于必定有效的状态对象
- 指针版本：适用于可能为空的场景（内部包含空指针断言）

## 性能考量

### 内存开销

`VulkanMutableTextureState` 对象非常轻量：
- `VkImageLayout`：4 字节枚举
- `uint32_t queueFamilyIndex`：4 字节
- 总计：8 字节（不包括虚函数表指针）

### 虚函数调用开销

- `type()` 和 `copyTo()` 是虚函数，有间接调用开销
- 频繁访问的 `GetVkImageLayout` 等函数通过类型转换避免虚函数
- 实际开销：一次虚函数调用（`GetStateData`）+ 一次静态转换

### 类型检查开销

断言在 Release 模式下被编译掉，无运行时开销。

### 拷贝性能

`copyTo()` 实现使用 `emplace` 直接构造：
```cpp
void copyTo(AnyStateData& formatData) const override {
    formatData.emplace<VulkanMutableTextureState>(fLayout, fQueueFamilyIndex);
}
```
- 避免不必要的拷贝构造
- 8 字节数据拷贝，性能影响可忽略

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/gpu/MutableTextureState.h` | 基类 | 后端无关的状态接口 |
| `src/gpu/MutableTextureStatePriv.h` | 依赖 | 内部实现辅助函数 |
| `src/gpu/vk/VulkanMutableTextureStatePriv.h` | 扩展 | Vulkan 私有修改接口 |
| `src/gpu/vk/VulkanTexture.h` | 使用 | Vulkan 纹理使用该状态 |
| `src/gpu/vk/VulkanGpu.h` | 使用 | GPU 操作更新状态 |
| `src/gpu/vk/VulkanCommandBuffer.h` | 使用 | 记录状态转换命令 |
| `include/gpu/GpuTypes.h` | 依赖 | `BackendApi` 类型定义 |

### 典型使用场景

#### 场景 1：创建纹理状态

```cpp
// 创建处于 COLOR_ATTACHMENT 布局的纹理状态
auto state = skgpu::MutableTextureStates::MakeVulkan(
    VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
    graphicsQueueFamilyIndex
);
```

#### 场景 2：查询纹理状态

```cpp
// 获取当前布局
VkImageLayout layout = skgpu::MutableTextureStates::GetVkImageLayout(state);

// 获取队列家族索引
uint32_t queueFamily = skgpu::MutableTextureStates::GetVkQueueFamilyIndex(state);
```

#### 场景 3：跨上下文共享纹理

```cpp
// 上下文 A：准备共享纹理，记录最终状态
auto finalState = texture->getMutableState();

// 传递给上下文 B
contextB->importTexture(backendTexture, finalState);

// 上下文 B：使用状态信息正确设置布局转换
VkImageLayout currentLayout = GetVkImageLayout(finalState);
// ... 执行必要的布局转换 ...
```

### 使用注意事项

1. **类型匹配**：只能在 Vulkan 后端上下文中使用 Vulkan 状态
2. **状态同步**：状态对象不会自动与实际 Vulkan 图像状态同步，需要手动维护一致性
3. **队列所有权**：`queueFamilyIndex` 用于跨队列家族的所有权转移，必须与实际 Vulkan 操作匹配
4. **线程安全**：状态对象本身不提供线程安全保证，需要外部同步
