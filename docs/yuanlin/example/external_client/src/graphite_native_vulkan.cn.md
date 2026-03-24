# graphite_native_vulkan.cpp - Graphite Vulkan 原生渲染示例

> 源文件: `example/external_client/src/graphite_native_vulkan.cpp`

## 概述

`graphite_native_vulkan.cpp` 是一个示例程序，演示了如何使用 Skia 的 Graphite 渲染后端通过 Vulkan API 进行 GPU 加速渲染。与 Metal 版本不同，此示例主要用于验证 Vulkan 后端的编译和链接正确性，并**不能直接运行**（因为缺少完整的 Vulkan 实例、设备和队列初始化代码）。

该示例展示了 Graphite Vulkan 后端所需的 API 调用序列，作为构建系统验证和外部客户端集成的参考。

## 架构位置

```
Skia 示例程序
├── example/external_client/src/
│   ├── graphite_native_vulkan.cpp   <-- 本文件：Vulkan 渲染示例（编译验证）
│   ├── graphite_native_metal.cpp    <-- Metal 渲染示例（可运行）
│   └── ...
├── include/gpu/graphite/vk/         <-- Graphite Vulkan API
└── include/gpu/vk/                  <-- 通用 Vulkan 工具
```

## 主要类与结构体

本文件不定义新类，使用 Skia 的 Graphite Vulkan API。

### 使用的核心类型
- `skgpu::VulkanBackendContext` - Vulkan 后端上下文配置
- `skgpu::VulkanExtensions` - Vulkan 扩展管理
- `skgpu::graphite::Context` - Graphite 上下文
- `skgpu::graphite::Recorder` - 命令录制器
- `SkSurface` / `SkCanvas` - 渲染表面和画布

## 公共 API 函数

### `main(int argc, char** argv)`
程序入口。演示 Graphite Vulkan 后端的 API 使用模式。

代码结构：
1. 创建（空的）Vulkan 后端上下文
2. 尝试创建 Graphite Context（将因空句柄失败）
3. 创建 Recorder 和 RenderTarget Surface
4. 在 Canvas 上绘制（浅灰色背景 + 蓝色圆角矩形）

## 内部实现细节

### Vulkan 后端上下文设置（桩代码）

```cpp
skgpu::VulkanBackendContext backendContext;
std::unique_ptr<skgpu::VulkanExtensions> extensions(new skgpu::VulkanExtensions());
backendContext.fInstance = VK_NULL_HANDLE;
backendContext.fDevice = VK_NULL_HANDLE;
```

这些句柄被设置为 `VK_NULL_HANDLE`，使得后续的 Context 创建会失败。在真实应用中需要：
- 创建 `VkInstance`
- 选择 `VkPhysicalDevice`
- 创建 `VkDevice`
- 获取图形队列
- 配置扩展

### Graphite Context 创建

```cpp
std::unique_ptr<skgpu::graphite::Context> context =
    skgpu::graphite::ContextFactory::MakeVulkan(backendContext, options);
```

使用 `ContextFactory::MakeVulkan` 从 Vulkan 后端上下文创建 Graphite Context。

### 绘制操作

```cpp
SkCanvas* canvas = surface->getCanvas();
canvas->clear(SK_ColorLTGRAY);
SkRRect rrect = SkRRect::MakeRectXY(SkRect::MakeLTRB(10, 20, 50, 70), 10, 10);
SkPaint paint;
paint.setColor(SK_ColorBLUE);
paint.setAntiAlias(true);
canvas->drawRRect(rrect, paint);
```

绘制逻辑与 Metal 版本类似，但使用不同的颜色方案（浅灰色背景 + 蓝色圆角矩形）。

### 缺失的清理代码

源码注释指出：
```cpp
// There would need to be vulkan cleanup here.
```

真实应用需要在退出前销毁 Vulkan 设备、实例等资源。

## 依赖关系

- **Skia 核心**：`SkCanvas`, `SkSurface`, `SkRRect`, `SkRect`, `SkColor`
- **Skia Graphite**：`Context`, `Recorder`, `ContextOptions`, `Surface`
- **Skia Graphite Vulkan**：`VulkanGraphiteContext`
- **Skia Vulkan 通用**：`VulkanBackendContext`, `VulkanExtensions`
- **Vulkan SDK**（隐式）：`VK_NULL_HANDLE` 等 Vulkan 类型

## 设计模式与设计决策

1. **编译验证目的**：此示例的主要目的是验证 Vulkan 后端的头文件包含和链接依赖是否正确，而非作为可运行的演示。

2. **最小 Vulkan 设置**：故意省略了复杂的 Vulkan 初始化代码（实例创建、物理设备选择、逻辑设备创建等），使示例专注于 Skia Graphite API。

3. **与 Metal 版本的对称**：结构与 `graphite_native_metal.cpp` 对称，便于对比两种后端的 API 差异。

4. **提前退出**：由于 Vulkan 上下文创建会失败，程序在第一个检查点就会退出，后续代码展示了理想的使用模式。

## 性能考量

- 此示例不涉及实际的 GPU 操作，因此性能考量不适用。
- 在真实的 Vulkan 应用中，Vulkan 的显式内存管理和命令缓冲区提交可以提供比 Metal 更精细的性能控制。
- Graphite 的 Recorder/Recording 模式与 Vulkan 的命令缓冲区模型自然对应。

## 相关文件

- `example/external_client/src/graphite_native_metal.cpp` - Metal 版本的可运行示例
- `include/gpu/graphite/vk/VulkanGraphiteContext.h` - Vulkan Graphite Context 创建
- `include/gpu/vk/VulkanBackendContext.h` - Vulkan 后端上下文
- `include/gpu/vk/VulkanExtensions.h` - Vulkan 扩展管理
- `include/gpu/graphite/Context.h` - Graphite Context API
