# GrVkDescriptorSet

> 源文件
> - `src/gpu/ganesh/vk/GrVkDescriptorSet.h`
> - `src/gpu/ganesh/vk/GrVkDescriptorSet.cpp`

## 概述

`GrVkDescriptorSet` 封装 Vulkan 描述符集对象（`VkDescriptorSet`），是绑定着色器资源（uniform buffer、纹理采样器、input attachment）的容器。该类继承自 `GrVkRecycledResource`，支持自动回收复用机制。当描述符集不再使用时，自动回收到 `GrVkDescriptorSetManager` 的空闲列表，供下次分配使用，显著减少描述符集分配开销。

## 架构位置

```
GrVkManagedResource
    └── GrVkRecycledResource
        └── GrVkDescriptorSet (描述符集封装)
```

由 `GrVkDescriptorSetManager` 管理其生命周期和回收。

## 主要类与结构体

### GrVkDescriptorSet 类

**核心成员**：
```cpp
VkDescriptorSet fDescSet;                    // Vulkan 描述符集对象
GrVkDescriptorPool* fPool;                   // 所属描述符池（持有引用）
GrVkDescriptorSetManager::Handle fHandle;    // 管理器句柄（用于回收）
```

## 公共 API 函数

**构造函数**
```cpp
GrVkDescriptorSet(GrVkGpu* gpu,
                  VkDescriptorSet descSet,
                  GrVkDescriptorPool* pool,
                  GrVkDescriptorSetManager::Handle handle);
```
创建描述符集包装器，增加描述符池引用计数。

**descriptorSet**
```cpp
const VkDescriptorSet* descriptorSet() const;
```
获取 Vulkan 描述符集对象指针，用于 Vulkan API 调用。

## 内部实现细节

### 构造与资源管理

```cpp
GrVkDescriptorSet::GrVkDescriptorSet(...)
    : INHERITED(gpu)
    , fDescSet(descSet)
    , fPool(pool)
    , fHandle(handle) {
    fPool->ref();  // 增加描述符池引用计数
}
```

持有描述符池引用，确保描述符集有效期间池不被销毁。

### 资源释放

```cpp
void freeGPUData() const {
    fPool->unref();  // 释放描述符池引用
}
```

描述符集本身不需要显式销毁（由描述符池管理），只需释放池引用。

### 自动回收

```cpp
void onRecycle() const {
    fGpu->resourceProvider().recycleDescriptorSet(this, fHandle);
}
```

当引用计数归零时，`GrVkRecycledResource` 自动调用 `onRecycle()`，将描述符集回收到管理器的空闲列表。

## 依赖关系

- `GrVkGpu`: GPU 接口
- `GrVkResourceProvider`: 资源提供器（负责回收）
- `GrVkDescriptorPool`: 描述符池（拥有者）
- `GrVkDescriptorSetManager`: 描述符集管理器（维护空闲列表）
- `GrVkRecycledResource`: 可回收资源基类

## 设计模式与设计决策

### 可回收资源模式

继承 `GrVkRecycledResource`，自动实现回收逻辑：
- 引用计数归零时自动回收
- 无需手动管理回收流程
- 与 `GrVkDescriptorSetManager` 紧密集成

### 描述符池依赖

持有描述符池引用而非拥有权：
- 多个描述符集共享同一池
- 池的生命周期由管理器控制
- 避免重复引用计数逻辑

### 句柄传递

构造时传入管理器句柄，回收时用于定位正确的管理器，支持多类型描述符集管理。

## 性能考量

### 零拷贝回收

回收时仅将指针放回空闲列表，无需复制或重置描述符集内容，开销极低。

### 池引用管理

通过引用计数确保池在描述符集有效期间不被销毁，避免悬空指针。

### 自动回收时机

利用引用计数机制，在不再被使用的第一时间回收，最大化复用率。

## 相关文件

- `src/gpu/ganesh/vk/GrVkGpu.h/cpp`: GPU 接口
- `src/gpu/ganesh/vk/GrVkResourceProvider.h/cpp`: 资源提供器
- `src/gpu/ganesh/vk/GrVkDescriptorPool.h/cpp`: 描述符池
- `src/gpu/ganesh/vk/GrVkDescriptorSetManager.h/cpp`: 描述符集管理器
- `src/gpu/ganesh/vk/GrVkRecycledResource.h`: 可回收资源基类
