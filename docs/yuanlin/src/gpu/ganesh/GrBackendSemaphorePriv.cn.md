# GrBackendSemaphorePriv

> 源文件: [src/gpu/ganesh/GrBackendSemaphorePriv.h](../../../../src/gpu/ganesh/GrBackendSemaphorePriv.h)

## 概述

`GrBackendSemaphorePriv.h` 定义了 Ganesh GPU 后端信号量（semaphore）系统的内部访问接口。该文件包含两个类：`GrBackendSemaphoreData`（信号量数据基类）和 `GrBackendSemaphorePriv`（友元访问代理类）。它们共同构成了 `GrBackendSemaphore` 公共类的内部实现支撑层，允许各 GPU 后端（Vulkan、Metal、D3D 等）以类型擦除的方式注入平台特定的信号量数据。

## 架构位置

该文件位于 Ganesh 信号量系统的内部层：

```
GrBackendSemaphore (公共 API)
  |
  +-- GrBackendSemaphorePriv (友元访问代理)
  |     |
  |     +-- MakeGrBackendSemaphore() (内部构造)
  |     +-- GetBackendData() (内部数据访问)
  |
  +-- GrBackendSemaphoreData (抽象数据基类)
        |
        +-- [Vulkan] VkSemaphoreData
        +-- [Metal] MtlSemaphoreData
        +-- [D3D]   D3DSemaphoreData
```

后端特定的代码通过 `GrBackendSemaphorePriv::MakeGrBackendSemaphore` 创建包含平台信号量句柄的 `GrBackendSemaphore` 对象，然后通过 `GetBackendData` 取回内部数据。

## 主要类与结构体

### `GrBackendSemaphoreData` — 信号量数据抽象基类

所有后端信号量数据的基类，使用多态实现类型擦除。

**关键特性：**

| 特性 | 说明 |
|------|------|
| 虚析构函数 | 确保派生类资源被正确释放 |
| `type()` (Debug only) | 返回 `GrBackendApi` 枚举，用于运行时类型校验 |
| `copyTo()` | 纯虚函数，将数据复制到 `AnySemaphoreData`（小对象存储） |
| 受保护默认构造和拷贝构造 | 仅允许派生类使用 |

**类型别名：**

- `AnySemaphoreData`：映射到 `GrBackendSemaphore::AnySemaphoreData`，即 `SkAnySubclass<GrBackendSemaphoreData, 24>`，一个 24 字节的小对象存储。

### `GrBackendSemaphorePriv` — 友元访问代理类

`final` 类，仅包含静态方法，提供对 `GrBackendSemaphore` 私有成员的受控访问。

## 公共 API 函数

### `GrBackendSemaphorePriv::MakeGrBackendSemaphore`

```cpp
template <typename SemaphoreData>
static GrBackendSemaphore MakeGrBackendSemaphore(GrBackendApi backend,
                                                  const SemaphoreData& data)
```

工厂方法模板。根据指定的后端 API 类型和后端特定数据创建 `GrBackendSemaphore` 对象。该方法调用 `GrBackendSemaphore` 的私有构造函数。

- **模板参数：** `SemaphoreData` — `GrBackendSemaphoreData` 的具体派生类型
- **参数：**
  - `backend`：GPU 后端 API 类型枚举（如 Vulkan、Metal 等）
  - `data`：后端特定的信号量数据

### `GrBackendSemaphorePriv::GetBackendData`

```cpp
static const GrBackendSemaphoreData* GetBackendData(const GrBackendSemaphore& sem)
```

从 `GrBackendSemaphore` 中提取内部的后端信号量数据指针。

- **参数：** `sem` — `GrBackendSemaphore` 对象
- **返回：** 内部 `GrBackendSemaphoreData` 指针（可能为 `nullptr`）

## 内部实现细节

1. **友元代理模式**：`GrBackendSemaphorePriv` 被声明为 `GrBackendSemaphore` 的友元类，因此可以访问其私有构造函数和私有成员 `fSemaphoreData`。这种模式在 Skia 中广泛使用（如 `SkFontPriv`、`SkPathPriv` 等），用于在不暴露公共 API 的情况下允许内部模块间的访问。

2. **类型擦除机制**：`GrBackendSemaphore` 内部使用 `SkAnySubclass<GrBackendSemaphoreData, 24>`（24 字节的小对象存储）来存储后端特定数据。这避免了堆分配，同时通过虚函数实现多态行为。

3. **Debug 类型检查**：`GrBackendSemaphoreData::type()` 仅在 `SK_DEBUG` 宏启用时存在，用于在运行时验证信号量数据的后端类型是否匹配，防止跨后端误用。

4. **`copyTo` 虚函数**：用于将派生类数据复制到小对象存储中，支持 `GrBackendSemaphore` 的拷贝构造操作。

5. **`final` 修饰符**：`GrBackendSemaphorePriv` 标记为 `final`，明确表示不应被继承——它仅作为静态方法的容器存在。

## 依赖关系

- **`include/core/SkTypes.h`**：基础类型和宏定义
- **`include/gpu/ganesh/GrBackendSemaphore.h`**：`GrBackendSemaphore` 公共类定义
- **`GrBackendApi`**（前向声明）：GPU 后端 API 枚举

## 设计模式与设计决策

1. **Passkey/友元代理模式**：通过专用的 `Priv` 类作为友元代理，限制对私有 API 的访问范围。只有能够 `#include` 此私有头文件的内部模块才能使用这些接口。

2. **类型擦除 + 小对象优化**：使用 `SkAnySubclass`（类似 `std::any`）将后端特定数据以值语义存储在固定大小的内联缓冲区中，避免堆分配的同时支持多态操作。

3. **公共/私有头文件分离**：`GrBackendSemaphore.h` 是公共头文件（在 `include/` 目录），`GrBackendSemaphorePriv.h` 是私有头文件（在 `src/` 目录）。公共 API 隐藏了实现细节，私有头文件提供内部访问。

4. **模板工厂方法**：`MakeGrBackendSemaphore` 是模板方法，允许传入任意 `SemaphoreData` 子类而无需为每个后端编写特化版本。

## 性能考量

- **小对象优化**：24 字节的内联存储避免了信号量对象的堆分配，减少了内存碎片和分配开销。
- **Debug-only 开销**：`type()` 方法仅在 Debug 构建中存在，Release 构建无额外开销。
- **值语义**：`GrBackendSemaphore` 可以通过值传递而无需堆分配，适合在 API 边界传递。

## 相关文件

- `include/gpu/ganesh/GrBackendSemaphore.h`：`GrBackendSemaphore` 公共 API
- `src/gpu/ganesh/GrSemaphore.h`：`GrSemaphore` 内部抽象接口
- `include/private/base/SkAnySubclass.h`：`SkAnySubclass` 小对象存储模板
- `include/gpu/ganesh/GrTypes.h`：`GrBackendApi` 枚举定义
- `src/gpu/ganesh/vk/GrVkSemaphore.h`：Vulkan 后端信号量实现（示例）
