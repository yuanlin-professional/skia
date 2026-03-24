# MutableTextureStatePriv

> 源文件: src/gpu/MutableTextureStatePriv.h

## 概述

`MutableTextureStatePriv` 模块定义了 GPU 纹理可变状态的内部实现接口,用于在不同图形 API 后端(Vulkan、Metal、D3D12 等)之间抽象纹理的布局、访问标志等可变状态信息。该模块提供了类型安全的状态数据封装和访问机制,是 Skia GPU 跨后端纹理状态管理的核心组件。

模块包含两个主要类:`MutableTextureStateData`(抽象基类,定义状态数据接口)和 `MutableTextureStatePriv`(友元访问类,提供类型安全的工厂和访问方法)。通过这种设计,上层代码可以以统一方式操作不同后端的纹理状态,而无需了解具体实现细节。

## 架构位置

`MutableTextureStatePriv` 位于 GPU 层的后端抽象基础设施:

- 命名空间: `skgpu`
- 模块位置: `src/gpu/`
- 类型: 内部实现接口(Priv 后缀表示私有/内部使用)
- 依赖层级: GPU 后端抽象层
- 服务对象: `MutableTextureState`(公共接口)、后端特定实现

该模块是纹理状态管理的底层实现,通过友元模式将内部实现与公共接口分离。

## 主要类与结构体

### 继承关系

```
MutableTextureStateData (抽象基类)
├── VulkanMutableTextureState (Vulkan 后端实现)
├── MetalMutableTextureState (Metal 后端实现)
└── D3D12MutableTextureState (D3D12 后端实现)

MutableTextureStatePriv (友元访问类,无继承)
```

### MutableTextureStateData 成员

| 成员/方法 | 类型 | 说明 |
|---------|------|------|
| `type()` | `virtual BackendApi` | 返回后端类型(仅 Debug 模式) |
| `copyTo()` | `virtual void` | 拷贝状态数据到目标 |
| `~MutableTextureStateData()` | `virtual` | 虚析构函数 |

### MutableTextureStatePriv 成员

| 成员/方法 | 类型 | 说明 |
|---------|------|------|
| `MakeMutableTextureState<T>()` | `static MutableTextureState` | 模板工厂方法 |
| `GetStateData()` | `static const/MutableTextureStateData*` | 获取状态数据指针 |

## 公共 API 函数

### MutableTextureStateData 接口

#### 虚析构函数

```cpp
virtual ~MutableTextureStateData();
```

**用途**: 确保通过基类指针删除时正确调用派生类析构函数

#### 类型查询(Debug 模式)

```cpp
#if defined(SK_DEBUG)
    virtual BackendApi type() const = 0;
#endif
```

**功能**: 返回状态数据对应的后端类型
**用途**: 调试时验证类型转换的正确性

#### 拷贝方法(私有,通过 MutableTextureState 调用)

```cpp
virtual void copyTo(AnyStateData&) const = 0;
```

**功能**: 将状态数据拷贝到目标对象
**参数**: `AnyStateData` - `MutableTextureState` 的内部存储类型

### MutableTextureStatePriv 接口

#### 工厂方法

```cpp
template <typename StateData>
static MutableTextureState MakeMutableTextureState(
    BackendApi backend,
    const StateData& data
);
```

**功能**: 创建类型安全的 `MutableTextureState` 对象
**参数**:
- `backend`: 后端 API 类型(如 `BackendApi::kVulkan`)
- `data`: 后端特定的状态数据

**返回值**: 包含状态数据的 `MutableTextureState` 对象

**示例**:
```cpp
VulkanMutableTextureState vkState = { /* Vulkan state */ };
auto state = MutableTextureStatePriv::MakeMutableTextureState(
    BackendApi::kVulkan,
    vkState
);
```

#### 访问器方法

```cpp
// 获取常量状态数据指针
static const MutableTextureStateData* GetStateData(const MutableTextureState& mts);
static const MutableTextureStateData* GetStateData(const MutableTextureState* mts);

// 获取可变状态数据指针
static MutableTextureStateData* GetStateData(MutableTextureState* mts);
```

**功能**: 从 `MutableTextureState` 对象中提取底层的 `MutableTextureStateData` 指针
**用途**: 后端实现访问具体的状态数据

**示例**:
```cpp
const MutableTextureStateData* data = MutableTextureStatePriv::GetStateData(state);
const auto* vkData = static_cast<const VulkanMutableTextureState*>(data);
// 访问 Vulkan 特定的状态
```

## 内部实现细节

### 友元模式

`MutableTextureStateData` 声明 `MutableTextureState` 为友元:

```cpp
class MutableTextureStateData {
private:
    friend class MutableTextureState;
    virtual void copyTo(AnyStateData&) const = 0;
};
```

**目的**:
- `copyTo` 是私有方法,仅 `MutableTextureState` 可以调用
- 防止外部代码直接操作底层数据
- 保持封装性

### 类型安全的工厂实现

```cpp
template <typename StateData>
static MutableTextureState MakeMutableTextureState(
    BackendApi backend,
    const StateData& data
) {
    return MutableTextureState(backend, data);
}
```

**设计**:
- 使用模板参数推导后端状态类型
- 调用 `MutableTextureState` 的私有构造函数
- 外部无法直接构造,必须通过工厂

### 指针访问的多重重载

提供了三个重载版本:

```cpp
// 1. 从常量引用获取
static const MutableTextureStateData* GetStateData(const MutableTextureState& mts) {
    return mts.fStateData.get();
}

// 2. 从常量指针获取
static const MutableTextureStateData* GetStateData(const MutableTextureState* mts) {
    SkASSERT(mts);
    return mts->fStateData.get();
}

// 3. 从可变指针获取
static MutableTextureStateData* GetStateData(MutableTextureState* mts) {
    SkASSERT(mts);
    return mts->fStateData.get();
}
```

**用途**:
- 适应不同的使用场景
- 保持 const 正确性
- 空指针断言保护

### 类型检查(Debug 模式)

派生类实现 `type()` 方法:

```cpp
#if defined(SK_DEBUG)
BackendApi VulkanMutableTextureState::type() const override {
    return BackendApi::kVulkan;
}
#endif
```

**用途**:
- 运行时验证类型转换
- 捕获后端不匹配的错误
- Release 模式下完全移除,无性能开销

## 依赖关系

### 依赖的模块

| 模块 | 用途 | 头文件 |
|------|------|--------|
| SkTypes | 基础类型定义 | `include/core/SkTypes.h` |
| MutableTextureState | 公共接口 | `include/gpu/MutableTextureState.h` |
| BackendApi | 后端 API 枚举 | `include/gpu/GpuTypes.h` |

### 被依赖的模块

| 模块 | 关系 | 说明 |
|------|------|------|
| VulkanMutableTextureState | 实现 | Vulkan 后端状态实现 |
| MetalMutableTextureState | 实现 | Metal 后端状态实现 |
| D3D12MutableTextureState | 实现 | D3D12 后端状态实现 |
| GrTexture | 使用方 | Ganesh 纹理对象 |
| graphite::Texture | 使用方 | Graphite 纹理对象 |

## 设计模式与设计决策

### 1. 友元访问模式

```cpp
class MutableTextureStateData {
private:
    friend class MutableTextureState;
    // 私有方法只对友元可见
};

class MutableTextureStatePriv final {
    // 提供静态访问接口
};
```

**目的**:
- 分离公共接口(`MutableTextureState`)和内部实现(`MutableTextureStateData`)
- 通过 `Priv` 类提供受控的内部访问
- 保持封装性,防止误用

### 2. 抽象工厂模式

`MakeMutableTextureState` 充当抽象工厂:
- 根据后端类型创建具体对象
- 模板参数自动推导具体类型
- 类型安全的对象创建

### 3. Pimpl(Pointer to Implementation)变体

```cpp
class MutableTextureState {
    std::unique_ptr<MutableTextureStateData> fStateData;
};
```

**优点**:
- 隐藏实现细节
- 减少编译依赖
- 支持多态

### 4. 策略模式

不同后端的状态数据是不同的策略:
- **策略接口**: `MutableTextureStateData`
- **具体策略**: `VulkanMutableTextureState`、`MetalMutableTextureState` 等
- **上下文**: `MutableTextureState`

### 5. 类型安全的向下转型

通过 `type()` 方法(Debug 模式)实现安全的向下转型:

```cpp
const auto* vkData = static_cast<const VulkanMutableTextureState*>(data);
#ifdef SK_DEBUG
SkASSERT(vkData->type() == BackendApi::kVulkan);
#endif
```

### 6. 编译期优化

`type()` 方法仅在 Debug 模式存在:
- Debug: 运行时类型检查
- Release: 完全移除,零开销

## 性能考量

### 1. 内存布局

```cpp
sizeof(MutableTextureStateData) = sizeof(void*);  // 仅 vtable 指针
```

具体后端实现大小取决于状态数据:
- Vulkan: 约 16-32 字节(VkImageLayout + VkAccessFlags 等)
- Metal: 约 8 字节(MTLResourceUsage)
- D3D12: 约 8 字节(D3D12_RESOURCE_STATES)

### 2. 虚函数开销

- `copyTo()`: 虚函数调用,1 次间接跳转
- `type()`: Debug 模式下虚函数,Release 模式不存在

### 3. 智能指针开销

`MutableTextureState` 使用 `std::unique_ptr`:
- 无引用计数开销(与 `shared_ptr` 相比)
- 自动内存管理
- 移动操作零开销

### 4. 内联潜力

`GetStateData` 等简单方法可以内联:
```cpp
static const MutableTextureStateData* GetStateData(const MutableTextureState& mts) {
    return mts.fStateData.get();  // 可内联
}
```

### 5. 类型检查成本

Debug 模式下的 `type()` 检查:
- 每次转型约 1 次虚函数调用
- Release 模式完全移除
- 权衡: 调试安全性 vs 运行时性能

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/gpu/MutableTextureState.h` | 公共接口 | 用户可见的纹理状态类 |
| `include/gpu/GpuTypes.h` | 依赖 | 后端 API 枚举定义 |
| `src/gpu/ganesh/vk/GrVkMutableTextureState.h` | 实现 | Vulkan 后端实现 |
| `src/gpu/ganesh/mtl/GrMtlMutableTextureState.h` | 实现 | Metal 后端实现 |
| `src/gpu/ganesh/d3d/GrD3DMutableTextureState.h` | 实现 | D3D12 后端实现 |
| `src/gpu/ganesh/GrTexture.h` | 使用方 | Ganesh 纹理对象 |
| `src/gpu/graphite/Texture.h` | 使用方 | Graphite 纹理对象 |

## 使用场景示例

### 场景 1: 创建 Vulkan 纹理状态

```cpp
// 定义 Vulkan 特定的状态
VkImageLayout layout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
uint32_t queueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;

VulkanMutableTextureState vkState(layout, queueFamilyIndex);

// 创建通用状态对象
auto state = MutableTextureStatePriv::MakeMutableTextureState(
    BackendApi::kVulkan,
    vkState
);
```

### 场景 2: 访问后端特定数据

```cpp
// 从通用对象获取底层数据
const auto* data = MutableTextureStatePriv::GetStateData(state);

#ifdef SK_DEBUG
// 验证类型
SkASSERT(data->type() == BackendApi::kVulkan);
#endif

// 转型到具体类型
const auto* vkData = static_cast<const VulkanMutableTextureState*>(data);

// 访问 Vulkan 特定字段
VkImageLayout currentLayout = vkData->layout();
```

### 场景 3: 修改纹理状态

```cpp
// 获取可变指针
auto* data = MutableTextureStatePriv::GetStateData(&mutableState);
auto* vkData = static_cast<VulkanMutableTextureState*>(data);

// 修改状态
vkData->setLayout(VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL);
```

### 场景 4: 拷贝状态

```cpp
MutableTextureState newState;
// 内部调用 copyTo() 方法
newState = oldState;  // 触发拷贝
```

## 设计权衡

### 为什么使用虚函数而非类型擦除?

**优点**:
- 更简单的实现
- 更好的类型安全(Debug 模式)
- 标准的 C++ 多态机制

**缺点**:
- 虚函数调用开销(通常可接受)

### 为什么分离 Priv 类?

- **封装性**: 内部方法不暴露给普通用户
- **清晰性**: 区分公共 API 和内部 API
- **灵活性**: 内部 API 可以变更而不影响公共接口

### 为什么使用 unique_ptr 而非 shared_ptr?

- **性能**: 无引用计数开销
- **语义**: 纹理状态通常独占,无需共享
- **简单性**: 无循环引用风险
