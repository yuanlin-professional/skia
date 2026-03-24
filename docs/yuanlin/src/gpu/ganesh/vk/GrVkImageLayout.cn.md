# GrVkImageLayout

> 源文件
> - src/gpu/ganesh/vk/GrVkImageLayout.h

## 概述

`GrVkImageLayout` 是 Skia 图形库中用于管理 Vulkan 图像布局状态的轻量级封装类。它继承自 `SkRefCnt`,提供引用计数管理,并使用原子操作(`std::atomic`)封装 `VkImageLayout`,确保在多线程环境下的线程安全访问。该类的主要作用是跟踪和更新 Vulkan 图像的当前布局,支持在不同渲染阶段之间安全地转换图像布局。

`GrVkImageLayout` 设计简洁,仅包含一个原子变量和两个简单的访问方法,专注于提供线程安全的布局状态管理。它作为 Skia 内部共享状态机制的一部分,允许多个对象安全地读写同一个图像布局状态。

## 架构位置

```
Skia 资源管理架构
├── SkRefCnt (引用计数基类)
│   └── GrVkImageLayout ← 当前类
│       └── std::atomic<VkImageLayout> (原子布局状态)
│
├── 使用者
│   ├── GrBackendSurfaceMutableState (后端表面可变状态)
│   ├── GrVkTexture (Vulkan 纹理)
│   └── GrVkRenderTarget (Vulkan 渲染目标)
```

`GrVkImageLayout` 通常通过 `GrBackendSurfaceMutableState` 在跨后端 API 边界时共享,也可能被内部的 Vulkan 资源对象引用以跟踪布局状态。

## 主要类与结构体

### 继承关系
```
SkRefCnt (引用计数基类)
  ↑
GrVkImageLayout (Vulkan 图像布局)
```

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fLayout` | `std::atomic<VkImageLayout>` | 原子化的 Vulkan 图像布局状态 |

## 公共 API 函数

| 函数签名 | 功能说明 |
|---------|---------|
| `GrVkImageLayout(VkImageLayout layout)` | 构造函数,初始化布局状态 |
| `void setImageLayout(VkImageLayout layout)` | 设置新的图像布局(原子操作) |
| `VkImageLayout getImageLayout() const` | 获取当前图像布局(原子操作) |

## 内部实现细节

### 构造函数

```cpp
GrVkImageLayout(VkImageLayout layout) : fLayout(layout) {}
```

- 接受初始布局值
- 初始化 `std::atomic<VkImageLayout>` 成员
- 使用默认内存序(memory_order_seq_cst)

### setImageLayout - 设置布局

```cpp
void setImageLayout(VkImageLayout layout) {
    // 使用默认内存序(std::memory_order_seq_cst)进行原子存储
    fLayout.store(layout);
}
```

**内存序说明**:
- 使用 `std::memory_order_seq_cst`(顺序一致性)
- 提供最强的内存序保证
- 确保所有线程看到一致的布局变化顺序

### getImageLayout - 获取布局

```cpp
VkImageLayout getImageLayout() const {
    // 使用默认内存序(std::memory_order_seq_cst)进行原子加载
    return fLayout.load();
}
```

**内存序说明**:
- 使用 `std::memory_order_seq_cst`
- 保证读取到最新的布局值
- 与其他内存操作保持顺序一致性

### 原子操作保证

`std::atomic<VkImageLayout>` 提供以下保证:

1. **原子性**: 读写操作不可分割,不会出现部分更新
2. **线程安全**: 多线程同时访问无数据竞争
3. **内存可见性**: 一个线程的修改对其他线程可见
4. **内存序**: 控制操作的执行顺序和可见性

### VkImageLayout 枚举

`VkImageLayout` 是 Vulkan 定义的枚举类型,表示图像的内存布局:

```cpp
// 常见的 Vulkan 图像布局
VK_IMAGE_LAYOUT_UNDEFINED                      // 未定义
VK_IMAGE_LAYOUT_GENERAL                        // 通用布局
VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL       // 颜色附件最优
VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL  // 深度模板附件最优
VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL       // 着色器只读最优
VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL           // 传输源最优
VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL           // 传输目标最优
VK_IMAGE_LAYOUT_PREINITIALIZED                 // 预初始化
VK_IMAGE_LAYOUT_PRESENT_SRC_KHR                // 呈现源
```

### 典型使用场景

```cpp
// 1. 创建共享布局对象
sk_sp<GrVkImageLayout> layout(new GrVkImageLayout(VK_IMAGE_LAYOUT_UNDEFINED));

// 2. 在多个对象间共享
GrBackendTexture backendTex = ...;
backendTex.setVkImageLayout(layout.get());

// 3. 线程 A: 读取当前布局
VkImageLayout currentLayout = layout->getImageLayout();

// 4. 线程 B: 更新布局(线程安全)
layout->setImageLayout(VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL);

// 5. 线程 A: 再次读取(立即可见新值)
currentLayout = layout->getImageLayout();
```

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖说明 |
|---------|---------|
| `SkRefCnt` | 引用计数基类,提供自动内存管理 |
| `GrVkTypes` | Vulkan 类型定义,包含 VkImageLayout |
| `std::atomic` | C++ 标准库,提供原子操作 |

### 被依赖的模块

| 模块名称 | 依赖说明 |
|---------|---------|
| `GrBackendSurfaceMutableState` | 后端表面可变状态,包含布局对象 |
| `GrVkTexture` | Vulkan 纹理,可能引用布局对象 |
| `GrVkRenderTarget` | Vulkan 渲染目标,可能引用布局对象 |
| `GrBackendTexture` | 后端纹理,共享布局状态 |
| `GrBackendRenderTarget` | 后端渲染目标,共享布局状态 |

## 设计模式与设计决策

### 1. 引用计数管理 (Reference Counting)

继承 `SkRefCnt` 实现自动内存管理:

```cpp
class GrVkImageLayout : public SkRefCnt {
    // 通过 sk_sp<GrVkImageLayout> 使用
};

// 使用示例
sk_sp<GrVkImageLayout> layout(new GrVkImageLayout(...));
// 离开作用域时自动删除
```

**优势**:
- 自动管理生命周期
- 支持多个对象共享
- 避免手动 delete

### 2. 原子操作封装

使用 `std::atomic` 提供线程安全:

```cpp
std::atomic<VkImageLayout> fLayout;
```

**优势**:
- 无需显式锁(mutex)
- 性能更好(lock-free)
- API 简单直观

### 3. 不可变对象的替代

虽然布局可变,但通过原子操作保证线程安全:

```cpp
// 非原子版本(不安全):
class UnsafeLayout {
    VkImageLayout fLayout;  // 多线程访问有数据竞争
};

// 原子版本(安全):
class GrVkImageLayout {
    std::atomic<VkImageLayout> fLayout;  // 线程安全
};
```

### 4. 单一职责原则 (Single Responsibility)

类仅负责一件事:管理图像布局状态

```cpp
class GrVkImageLayout {
    // 仅管理布局,不涉及其他图像属性
    void setImageLayout(VkImageLayout);
    VkImageLayout getImageLayout() const;
};
```

### 5. 最小接口原则

仅暴露必要的两个方法:

```cpp
setImageLayout()  // 写
getImageLayout()  // 读
```

无多余功能,接口清晰简洁。

### 6. 值语义 vs 引用语义

使用引用计数指针共享单一状态:

```cpp
// 引用语义(当前设计):
sk_sp<GrVkImageLayout> layout = ...;
obj1->setLayout(layout);  // 共享同一对象
obj2->setLayout(layout);  // 修改对两者可见

// 值语义(替代方案):
VkImageLayout layout = ...;
obj1->setLayout(layout);  // 复制值
obj2->setLayout(layout);  // 独立副本
```

**当前设计的优势**:
- 多个对象同步状态
- 减少内存开销
- 支持跨对象通信

## 性能考量

### 1. 原子操作开销

```cpp
fLayout.store(layout);  // 原子存储
fLayout.load();         // 原子加载
```

**性能特点**:
- 比普通变量慢(需要内存屏障)
- 比互斥锁快(无上下文切换)
- 对于单个整数,开销可接受

### 2. 内存序选择

使用 `std::memory_order_seq_cst` 默认内存序:

```cpp
// 代码注释中明确说明:
// Defaulting to use std::memory_order_seq_cst
```

**权衡**:
- **优势**: 最简单,最安全,无数据竞争
- **劣势**: 最保守,可能不是最快
- **替代**: 可使用 `memory_order_acquire/release` 优化(需谨慎)

### 3. 缓存行友好

`GrVkImageLayout` 对象非常小:

```cpp
sizeof(GrVkImageLayout) = sizeof(SkRefCnt) + sizeof(std::atomic<int>)
                        ≈ 8 字节(vtable 指针) + 4 字节(atomic) + 4 字节(refcnt)
                        ≈ 16 字节
```

**优势**:
- 适合缓存行(通常 64 字节)
- 多个对象可共享缓存行
- 减少缓存未命中

### 4. 无锁设计

`std::atomic` 提供 lock-free 实现(在大多数平台):

```cpp
static_assert(std::atomic<VkImageLayout>::is_always_lock_free);
// VkImageLayout 是 int32_t 枚举,通常 lock-free
```

**优势**:
- 无上下文切换开销
- 避免优先级反转
- 更好的可预测性

### 5. 引用计数开销

`SkRefCnt` 使用原子引用计数:

```cpp
sk_sp<GrVkImageLayout> ptr1 = layout;  // 原子增加引用计数
sk_sp<GrVkImageLayout> ptr2 = ptr1;    // 再次原子增加
// 离开作用域时原子减少
```

**权衡**:
- 每次复制/赋值有原子操作开销
- 但避免了手动内存管理的复杂性
- 对于长生命周期对象,开销摊销可接受

### 6. 避免伪共享 (False Sharing)

如果多个 `GrVkImageLayout` 对象在同一缓存行:

```cpp
// 潜在的伪共享问题:
struct Container {
    GrVkImageLayout layout1;  // 线程 1 频繁写
    GrVkImageLayout layout2;  // 线程 2 频繁写
    // 如果在同一缓存行,会导致缓存行乒乓(cache line ping-pong)
};
```

**缓解措施**:
- 通常通过指针共享,而非内嵌
- 每个图像有独立的布局对象
- 减少伪共享可能性

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `include/core/SkRefCnt.h` | 引用计数基类 |
| `include/gpu/ganesh/vk/GrVkTypes.h` | Vulkan 类型定义,包含 VkImageLayout |
| `include/gpu/ganesh/GrBackendSurface.h` | 后端表面,使用布局对象 |
| `src/gpu/ganesh/vk/GrVkTexture.h` | Vulkan 纹理,可能引用布局 |
| `src/gpu/ganesh/vk/GrVkRenderTarget.h` | Vulkan 渲染目标,可能引用布局 |
| `include/gpu/MutableTextureState.h` | 可变纹理状态接口 |
| `include/gpu/vk/VulkanMutableTextureState.h` | Vulkan 可变状态实现 |
