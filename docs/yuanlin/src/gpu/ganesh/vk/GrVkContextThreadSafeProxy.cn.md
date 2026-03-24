# GrVkContextThreadSafeProxy

> 源文件
> - `src/gpu/ganesh/vk/GrVkContextThreadSafeProxy.h`
> - `src/gpu/ganesh/vk/GrVkContextThreadSafeProxy.cpp`

## 概述

`GrVkContextThreadSafeProxy` 是 Vulkan 后端的线程安全上下文代理类，继承自 `GrContextThreadSafeProxy`。该类提供跨线程访问上下文信息的安全接口，主要用于验证表面特征化（Surface Characterization）与 Vulkan 上下文的兼容性。特别地，它处理次级命令缓冲区、protected content、input attachment 等 Vulkan 特定特性的验证。

## 架构位置

```
GrContextThreadSafeProxy (基类)
    └── GrVkContextThreadSafeProxy (Vulkan 实现)
```

作为跨线程安全访问点，供多线程环境中查询上下文能力和验证兼容性。

## 公共 API 函数

**构造函数**
```cpp
GrVkContextThreadSafeProxy(const GrContextOptions& opts);
```
初始化 Vulkan 后端代理，传递 `GrBackendApi::kVulkan` 给基类。

**isValidCharacterizationForVulkan**
```cpp
bool isValidCharacterizationForVulkan(
    sk_sp<const GrCaps> caps,
    bool isTextureable,
    skgpu::Mipmapped isMipmapped,
    skgpu::Protected isProtected,
    bool vkRTSupportsInputAttachment,
    bool forVulkanSecondaryCommandBuffer) override;
```
验证表面特征化是否与 Vulkan 上下文兼容。检查项包括：
- 次级命令缓冲区不支持纹理、mipmap、input attachment
- Protected content 状态必须匹配上下文能力

## 内部实现细节

### 次级命令缓冲区限制

```cpp
if (forVulkanSecondaryCommandBuffer &&
    (isTextureable || isMipmapped == skgpu::Mipmapped::kYes ||
     vkRTSupportsInputAttachment)) {
    return false;
}
```

次级命令缓冲区（用于外部应用集成）不支持高级特性，因为其渲染目标由外部提供，Skia 无法完全控制。

### Protected Content 验证

```cpp
const GrVkCaps* vkCaps = (const GrVkCaps*)caps.get();
return isProtected == GrProtected(vkCaps->supportsProtectedContent());
```

确保表面的 protected 状态与上下文能力匹配，避免在不支持 protected content 的设备上创建 protected 表面。

## 依赖关系

- `GrContextThreadSafeProxy`: 线程安全代理基类
- `GrVkCaps`: Vulkan 能力查询
- `GrContextOptions`: 上下文选项

## 设计决策

### 线程安全性

作为线程安全代理，该类不持有可变状态，所有操作都是查询和验证，确保多线程环境安全。

### Vulkan 特性验证

针对 Vulkan 特定特性（次级命令缓冲区、protected content）提供专门验证逻辑，确保上层 API 不会创建不兼容的表面。

## 相关文件

- `include/gpu/ganesh/GrContextThreadSafeProxy.h`: 线程安全代理基类
- `src/gpu/ganesh/vk/GrVkCaps.h/cpp`: Vulkan 能力查询
- `include/gpu/ganesh/GrTypes.h`: GPU 类型定义
