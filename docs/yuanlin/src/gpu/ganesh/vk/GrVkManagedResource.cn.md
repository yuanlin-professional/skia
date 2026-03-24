# GrVkManagedResource

> 源文件
> - src/gpu/ganesh/vk/GrVkManagedResource.h

## 概述

`GrVkManagedResource` 是 Skia 图形库中用于管理 Vulkan 资源的基类,继承自 `GrManagedResource`。它为所有需要访问 `GrVkGpu` 对象的 Vulkan 托管资源提供统一的接口。该类通过在构造时存储 GPU 指针,使得派生类在资源释放(`freeGPUData()`)时能够访问必要的 Vulkan 设备句柄和接口。

此外,该文件还定义了 `GrVkRecycledResource` 类,用于可回收的 Vulkan 资源,提供非 const 的 GPU 指针以支持资源回收操作。

## 架构位置

```
Skia 资源管理架构
├── GrManagedResource (托管资源基类)
│   └── GrVkManagedResource ← 当前类
│       ├── GrVkImageView (图像视图)
│       ├── GrVkRenderPass (渲染通道)
│       ├── GrVkPipeline (管线)
│       ├── GrVkSampler (采样器)
│       └── 其他 Vulkan 资源
│
├── GrRecycledResource (可回收资源基类)
│   └── GrVkRecycledResource
│       ├── GrVkSecondaryCommandBuffer (辅助命令缓冲区)
│       └── GrVkDescriptorSet (描述符集)
```

`GrVkManagedResource` 是所有 Vulkan 托管资源的通用基类,提供访问 GPU 对象的能力。`GrVkRecycledResource` 则用于需要回收复用的资源。

## 主要类与结构体

### GrVkManagedResource 类

```cpp
class GrVkManagedResource : public GrManagedResource {
public:
    GrVkManagedResource(const GrVkGpu* gpu) : fGpu(gpu) {}

protected:
    const GrVkGpu* fGpu;  // GPU 对象指针,可在 freeGPUData() 中使用

private:
    using INHERITED = GrManagedResource;
};
```

### 继承关系
```
GrManagedResource (基类 - 托管资源)
  ↑
GrVkManagedResource (Vulkan 托管资源)
  ↑
派生类 (具体的 Vulkan 资源)
```

### GrVkRecycledResource 类

```cpp
class GrVkRecycledResource : public GrRecycledResource {
public:
    GrVkRecycledResource(GrVkGpu* gpu) : fGpu(gpu) {}

protected:
    GrVkGpu* fGpu;  // 非 const GPU 指针,可在 freeGPUData() 和 onRecycle() 中使用

private:
    using INHERITED = GrRecycledResource;
};
```

### 继承关系
```
GrRecycledResource (基类 - 可回收资源)
  ↑
GrVkRecycledResource (Vulkan 可回收资源)
  ↑
派生类 (具体的可回收 Vulkan 资源)
```

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fGpu` (GrVkManagedResource) | `const GrVkGpu*` | GPU 对象指针(const,仅用于释放) |
| `fGpu` (GrVkRecycledResource) | `GrVkGpu*` | GPU 对象指针(非 const,用于释放和回收) |

## 公共 API 函数

### GrVkManagedResource

| 函数签名 | 功能说明 |
|---------|---------|
| `GrVkManagedResource(const GrVkGpu* gpu)` | 构造函数,存储 GPU 指针 |

### GrVkRecycledResource

| 函数签名 | 功能说明 |
|---------|---------|
| `GrVkRecycledResource(GrVkGpu* gpu)` | 构造函数,存储非 const GPU 指针 |

## 内部实现细节

### 设计目的

`GrVkManagedResource` 的主要目的是为派生类提供访问 `GrVkGpu` 对象的能力。在 `freeGPUData()` 虚函数中,派生类需要调用 Vulkan API 来释放资源,这需要访问:

1. **Vulkan 设备句柄**: `fGpu->device()`
2. **Vulkan 接口**: `fGpu->vkInterface()`
3. **Vulkan 调用宏**: `GR_VK_CALL(fGpu->vkInterface(), ...)`

### 典型使用模式

```cpp
// 派生类示例: GrVkImageView
class GrVkImageView : public GrVkManagedResource {
public:
    static sk_sp<const GrVkImageView> Make(GrVkGpu* gpu, ...) {
        // 创建 VkImageView
        VkImageView imageView;
        GR_VK_CALL_RESULT(gpu, err,
            CreateImageView(gpu->device(), &viewInfo, nullptr, &imageView));

        // 传递 gpu 指针给基类
        return sk_sp<const GrVkImageView>(
            new GrVkImageView(gpu, imageView, ...));
    }

private:
    GrVkImageView(const GrVkGpu* gpu, VkImageView imageView, ...)
        : INHERITED(gpu),  // 初始化基类
          fImageView(imageView) {}

    void freeGPUData() const override {
        // 使用 fGpu 访问 Vulkan 接口
        GR_VK_CALL(fGpu->vkInterface(),
                   DestroyImageView(fGpu->device(), fImageView, nullptr));
    }

    VkImageView fImageView;
    using INHERITED = GrVkManagedResource;
};
```

### 托管资源 vs 可回收资源

**GrVkManagedResource (托管资源)**:
- GPU 指针为 const
- 仅用于资源释放
- 示例: `GrVkImageView`, `GrVkRenderPass`, `GrVkPipeline`

**GrVkRecycledResource (可回收资源)**:
- GPU 指针为非 const
- 支持资源回收(`onRecycle()`)
- 可在回收时修改 GPU 状态
- 示例: `GrVkSecondaryCommandBuffer`, `GrVkDescriptorSet`

```cpp
// 可回收资源示例: GrVkSecondaryCommandBuffer
class GrVkSecondaryCommandBuffer : public GrVkRecycledResource {
public:
    GrVkSecondaryCommandBuffer(GrVkGpu* gpu, ...)
        : INHERITED(gpu) {}  // 非 const GPU 指针

    void recycle(GrVkCommandPool* pool) {
        // 使用 fGpu 重置命令缓冲区
        GR_VK_CALL(fGpu->vkInterface(),
                   ResetCommandBuffer(fCommandBuffer, 0));

        // 将资源归还到池中
        pool->recycleSecondaryCommandBuffer(this);
    }

protected:
    void freeGPUData() override {
        // 释放 Vulkan 资源
        GR_VK_CALL(fGpu->vkInterface(),
                   FreeCommandBuffers(fGpu->device(), ...));
    }

    void onRecycle() override {
        // 回收时的清理操作
        // fGpu 可用于访问 GPU 状态
    }

private:
    VkCommandBuffer fCommandBuffer;
    using INHERITED = GrVkRecycledResource;
};
```

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖说明 |
|---------|---------|
| `GrManagedResource` | 托管资源基类,提供引用计数和资源管理 |
| `GrRecycledResource` | 可回收资源基类 |
| `GrVkGpu` | GPU 对象,提供设备和接口访问 |

### 被依赖的模块

| 模块名称 | 依赖说明 |
|---------|---------|
| `GrVkImageView` | 图像视图,托管资源 |
| `GrVkRenderPass` | 渲染通道,托管资源 |
| `GrVkPipeline` | 管线,托管资源 |
| `GrVkSampler` | 采样器,托管资源 |
| `GrVkFramebuffer` | 帧缓冲区,托管资源 |
| `GrVkSecondaryCommandBuffer` | 辅助命令缓冲区,可回收资源 |
| `GrVkDescriptorSet` | 描述符集,可回收资源 |

## 设计模式与设计决策

### 1. 模板方法模式 (Template Method Pattern)

基类 `GrManagedResource` 定义资源生命周期模板,派生类实现具体的释放逻辑:

```cpp
// 基类定义模板
class GrManagedResource {
    virtual ~GrManagedResource() {
        if (this->unique()) {
            this->freeGPUData();  // 调用子类实现
        }
    }
    virtual void freeGPUData() const = 0;  // 纯虚函数
};

// 派生类实现具体逻辑
class GrVkImageView : public GrVkManagedResource {
    void freeGPUData() const override {
        DestroyImageView(...);  // Vulkan 特定释放
    }
};
```

### 2. 依赖注入 (Dependency Injection)

通过构造函数注入 GPU 依赖:

```cpp
GrVkManagedResource(const GrVkGpu* gpu) : fGpu(gpu) {}
```

**优势**:
- 解耦资源和 GPU 对象的创建
- 支持多个 GPU 实例
- 便于测试(可注入 mock GPU)

### 3. CRTP 的轻量替代

通过成员变量存储 GPU 指针,而非使用 CRTP(Curiously Recurring Template Pattern):

```cpp
// 当前设计: 简单直接
class GrVkManagedResource {
    const GrVkGpu* fGpu;
};

// 替代方案(未使用): CRTP
template<typename Derived>
class GrVkManagedResource {
    const GrVkGpu* gpu() { return static_cast<Derived*>(this)->getGpu(); }
};
```

**当前设计的优势**:
- 更简单,易于理解
- 避免模板膨胀
- 编译更快

### 4. 策略模式 - const vs 非 const

通过两个基类区分托管资源和可回收资源的访问策略:

```cpp
// 策略1: 只读访问(托管资源)
class GrVkManagedResource {
    const GrVkGpu* fGpu;  // 仅用于释放
};

// 策略2: 读写访问(可回收资源)
class GrVkRecycledResource {
    GrVkGpu* fGpu;  // 用于释放和回收
};
```

### 5. 最小接口原则

`GrVkManagedResource` 仅提供最小必要的接口:
- 单一构造函数
- 单一成员变量
- 无额外方法

**优势**:
- 减少耦合
- 简化派生类实现
- 提高可维护性

### 6. 保护级别设计

`fGpu` 成员为 protected:

```cpp
protected:
    const GrVkGpu* fGpu;
```

**原因**:
- 允许派生类访问
- 防止外部代码直接访问
- 封装实现细节

## 性能考量

### 1. 最小内存开销

`GrVkManagedResource` 仅增加一个指针(8 字节)的开销:

```cpp
sizeof(GrVkManagedResource) = sizeof(GrManagedResource) + sizeof(void*);
// = 基类大小 + 8 字节
```

### 2. 无虚函数开销

`GrVkManagedResource` 本身不引入新的虚函数,虚函数开销来自基类:

```cpp
class GrVkManagedResource : public GrManagedResource {
    // 无新的虚函数
};
```

### 3. 内联潜力

简单的构造函数可以内联:

```cpp
GrVkManagedResource(const GrVkGpu* gpu) : fGpu(gpu) {}
// 编译器可内联此构造函数
```

### 4. 缓存友好

GPU 指针存储在对象内部,局部性好:

```cpp
class GrVkImageView : public GrVkManagedResource {
    VkImageView fImageView;
    // fGpu 紧邻 fImageView,缓存友好
};
```

### 5. 避免虚函数调用

派生类直接访问 `fGpu`,无需虚函数调用:

```cpp
void freeGPUData() const override {
    // 直接访问,无虚函数开销
    fGpu->device();
    fGpu->vkInterface();
}
```

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `src/gpu/ganesh/GrManagedResource.h` | 托管资源基类 |
| `src/gpu/ganesh/GrRecycledResource.h` | 可回收资源基类 |
| `src/gpu/ganesh/vk/GrVkGpu.h` | GPU 对象定义 |
| `src/gpu/ganesh/vk/GrVkImageView.h` | 图像视图(派生类) |
| `src/gpu/ganesh/vk/GrVkRenderPass.h` | 渲染通道(派生类) |
| `src/gpu/ganesh/vk/GrVkPipeline.h` | 管线(派生类) |
| `src/gpu/ganesh/vk/GrVkSampler.h` | 采样器(派生类) |
| `src/gpu/ganesh/vk/GrVkFramebuffer.h` | 帧缓冲区(派生类) |
| `src/gpu/ganesh/vk/GrVkSecondaryCommandBuffer.h` | 辅助命令缓冲区(可回收资源) |
| `src/gpu/ganesh/vk/GrVkDescriptorSet.h` | 描述符集(可回收资源) |
