# BackendSemaphorePriv

> 源文件
> - src/gpu/graphite/BackendSemaphorePriv.h

## 概述

`BackendSemaphorePriv` 是 Graphite 渲染系统中用于管理后端特定信号量数据的私有接口类。它提供了创建和访问 `BackendSemaphore` 对象内部数据的工厂方法和访问器，支持 Vulkan、Metal 等不同后端的信号量抽象。

该模块采用类型擦除技术，通过 `BackendSemaphoreData` 抽象基类隐藏后端差异，使上层代码可以统一处理不同 GPU API 的同步原语。

## 架构位置

```
Graphite Synchronization Layer
├── BackendSemaphore (公共接口)
│   └── AnyBackendSemaphoreData (类型擦除存储)
└── BackendSemaphorePriv (本类) ← 私有访问接口
    └── BackendSemaphoreData (抽象数据基类)
        ├── VulkanSemaphoreData
        ├── MetalSemaphoreData
        └── DawnSemaphoreData
```

## 主要类与结构体

### BackendSemaphoreData 抽象基类

```cpp
class BackendSemaphoreData
```

**职责**：定义后端信号量数据的通用接口

**关键成员**：

| 成员 | 类型 | 说明 |
|------|------|------|
| `type()` | `virtual skgpu::BackendApi` | 返回后端 API 类型（Debug 构建） |
| `copyTo()` | `virtual void` | 拷贝数据到目标存储 |

**生命周期**：
- 虚析构函数确保多态删除安全
- 使用默认拷贝构造函数
- Protected 构造函数防止直接实例化

### BackendSemaphorePriv 工厂类

```cpp
class BackendSemaphorePriv
```

**设计模式**：静态工厂 + 友元访问

**成员函数表**：

| 函数 | 返回类型 | 说明 |
|------|---------|------|
| `Make<T>()` | `BackendSemaphore` | 创建 BackendSemaphore 对象 |
| `GetData()` | `const BackendSemaphoreData*` | 获取内部数据指针 |

## 公共 API 函数

### 1. 工厂方法

```cpp
template <typename SomeBackendSemaphoreData>
static BackendSemaphore Make(BackendApi backend, const SomeBackendSemaphoreData& textureData)
```

**功能**：创建包含特定后端数据的 `BackendSemaphore` 对象

**模板参数**：`SomeBackendSemaphoreData` - 具体后端的信号量数据类型（如 `VulkanSemaphoreData`）

**参数**：
- `backend`：后端 API 类型枚举（`BackendApi::kVulkan`、`BackendApi::kMetal` 等）
- `textureData`：后端特定的信号量数据

**返回值**：包含后端数据的 `BackendSemaphore` 对象

**使用示例**：
```cpp
VulkanSemaphoreData vkData{vkSemaphore};
BackendSemaphore sem = BackendSemaphorePriv::Make(BackendApi::kVulkan, vkData);
```

### 2. 数据访问器

```cpp
static const BackendSemaphoreData* GetData(const BackendSemaphore& info)
```

**功能**：获取 `BackendSemaphore` 内部存储的后端数据指针

**返回值**：指向 `BackendSemaphoreData` 的常量指针，可能为 `nullptr`

**访问权限**：通过友元关系访问 `BackendSemaphore` 的私有成员 `fSemaphoreData`

**用途**：
- 后端实现提取特定类型数据
- Debug 构建中验证类型一致性

## 内部实现细节

### 类型擦除机制

`BackendSemaphore` 使用 `std::unique_ptr<BackendSemaphoreData>` 存储数据：

```cpp
// BackendSemaphore 内部（概念代码）
class BackendSemaphore {
private:
    std::unique_ptr<BackendSemaphoreData> fSemaphoreData;
};
```

通过虚函数实现多态：
- `copyTo()`：拷贝语义
- `type()`：运行时类型识别（RTTI 替代）

### copyTo() 虚函数

```cpp
virtual void copyTo(AnyBackendSemaphoreData& dstData) const = 0
```

**用途**：支持 `BackendSemaphore` 的拷贝构造和赋值

**实现要求**：子类必须实现深拷贝逻辑

**示例实现**：
```cpp
void VulkanSemaphoreData::copyTo(AnyBackendSemaphoreData& dst) const {
    dst.emplace<VulkanSemaphoreData>(*this);
}
```

### Debug 类型检查

```cpp
#if defined(SK_DEBUG)
    virtual skgpu::BackendApi type() const = 0;
#endif
```

**设计原因**：
- Release 构建中移除类型检查开销
- Debug 构建中提供类型安全验证
- 帮助捕获跨后端使用错误

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `BackendSemaphore` | 公共信号量接口 |
| `skgpu::BackendApi` | 后端 API 类型枚举 |
| `SkDebug` | Debug 断言支持 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| `VulkanCommandBuffer` | 创建和使用 Vulkan 信号量 |
| `MetalCommandBuffer` | 创建和使用 Metal 信号量 |
| `Context` | 跨后端信号量创建 |
| `InsertRecordingInfo` | 设置信号量同步 |

## 设计模式与设计决策

### 1. 类型擦除（Type Erasure）

通过虚函数隐藏后端差异：
```cpp
BackendSemaphoreData (抽象)
    ↓ (继承)
VulkanSemaphoreData (具体实现)
```

**优点**：
- 公共接口无需知道具体后端
- 支持运行时后端切换
- 简化跨模块依赖

### 2. 友元访问模式

`BackendSemaphorePriv` 声明为 `BackendSemaphore` 的友元：
```cpp
friend class BackendSemaphorePriv;
```

**目的**：
- 限制内部数据的访问范围
- 公共 API 保持简洁
- 后端实现可访问私有数据

### 3. 模板工厂方法

```cpp
template <typename SomeBackendSemaphoreData>
static BackendSemaphore Make(...)
```

**优势**：
- 类型安全的数据传递
- 编译期类型检查
- 避免显式向下转型

### 4. 条件编译的类型检查

仅在 Debug 构建中启用 `type()` 函数：
- **Release**：零运行时开销
- **Debug**：提供类型验证

### 5. 私有基类设计

`BackendSemaphoreData` 使用 protected 构造函数：
```cpp
protected:
    BackendSemaphoreData() = default;
```

防止直接实例化，强制使用具体子类。

## 性能考量

### 1. 零拷贝设计

通过引用传递后端数据：
```cpp
static BackendSemaphore Make(BackendApi backend, const SomeBackendSemaphoreData& data)
```

避免不必要的数据拷贝。

### 2. Debug/Release 分离

类型检查仅在 Debug 构建中存在：
```cpp
#if defined(SK_DEBUG)
    virtual skgpu::BackendApi type() const = 0;
#endif
```

Release 构建中移除虚函数表条目，减少内存占用。

### 3. 内联优化

静态工厂方法和访问器定义在头文件中，支持编译器内联优化。

### 4. 虚析构函数开销

```cpp
virtual ~BackendSemaphoreData();
```

**代价**：增加虚函数表指针（8 字节）
**必要性**：确保多态删除安全，避免内存泄漏

### 5. 类型擦除的运行时成本

- 虚函数调用开销（~5-10 纳秒）
- 间接访问降低缓存命中率
- 但信号量操作本身涉及系统调用（微秒级），虚函数开销可忽略

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/gpu/graphite/BackendSemaphore.h` | 公共接口 | 用户可见的信号量类 |
| `src/gpu/graphite/vk/VulkanSemaphore.h` | 具体实现 | Vulkan 信号量数据 |
| `src/gpu/graphite/mtl/MtlSemaphore.h` | 具体实现 | Metal 信号量数据 |
| `src/gpu/graphite/CommandBuffer.h` | 使用者 | 绑定信号量到命令缓冲 |
| `src/gpu/graphite/Context.h` | 使用者 | 跨后端信号量管理 |
| `include/private/gpu/graphite/ContextOptionsPriv.h` | 配置 | 信号量相关选项 |
| `include/gpu/graphite/Recording.h` | 使用者 | 录制提交时的同步 |
