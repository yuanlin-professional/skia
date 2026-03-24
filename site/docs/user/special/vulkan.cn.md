
---
title: "Vulkan"
linkTitle: "Vulkan"

---


Skia 有其 GPU 后端的 Vulkan 实现。Vulkan 后端可以与 OpenGL 后端
一起构建。客户端可以在运行时选择 OpenGL 和 Vulkan 实现之间切换。
Vulkan 后端已经达到了与 OpenGL 后端的功能对等 (feature parity)。
目前我们发现许多 Vulkan 驱动程序存在 Skia 触发的 bug，但我们没有
相应的解决方法。我们在发现 bug 时会向供应商报告。

Windows 和 Linux
-----------------
要构建 Vulkan 后端，在 `args.gn` 中设置 `skia_use_vulkan=true`。

Android
-------
Vulkan 后端可以在任何具有 Vulkan 驱动程序的设备上运行，包括所有 Android N+ 设备。
要构建 Vulkan 后端，在 `args.gn` 中设置 `ndk_api = 24` 以面向 Android N。

Mac
---
Vulkan 后端可以使用 SwiftShader 在软件模拟中运行。这将允许
通过 `dm` 进行测试和调试。（Vulkan 不支持 `viewer` 等交互式应用。）

Skia 已经将 SwiftShader 库作为外部依赖包含在内。要构建它，你
首先需要安装 [CMake](https://cmake.org/download/)。打开应用程序并按照
_Tools > How to Install For Command Line Use_ 中的说明设置 CMake
的命令行使用。CMake 准备好后，需要编译 SwiftShader。请按照
以下步骤操作，将下面的 `$(SKIA_DIR)` 替换为你实际的 Skia 目录：

<!--?prettify lang=bash-->
    $ cd $(SKIA_DIR)/third_party/externals/swiftshader/build
    $ cmake ..
    $ cmake --build . --parallel

构建完成后，SwiftShader 的 `build` 目录应包含一个 `Darwin`
子目录，其中包含 `libvk_swiftshader.dylib`。要让 Skia 看到这个库，
我们需要在 `args.gn` 中这样引用它：

```
skia_use_vulkan = true
extra_cflags = [ "-D", "SK_GPU_TOOLS_VK_LIBRARY_NAME=$(SKIA_DIR)/third_party/externals/swiftshader/build/Darwin/libvk_swiftshader.dylib" ]
```

使用 Vulkan 后端
------------------------

要创建由 Vulkan 支持的 GrContext，客户端创建一个 Vulkan 设备和队列，初始化 skgpu::VulkanBackendContext 来描述上下文，然后调用 GrDirectContexts::MakeVulkan：

<!--?prettify lang=c++?-->
    skgpu::VulkanBackendContext vkContext;
    vkBackendContext.fInstance = vkInstance;
    vkBackendContext.fPhysicalDevice = vkPhysDevice;
    ...

    sk_sp<GrContext> context = GrDirectContexts::MakeVulkan::MakeVulkan(vkBackendContext);

使用 Vulkan 后端时，GrVkImageInfo 用于构造 GrBackendTexture
和 GrBackendRenderTarget 对象，这些对象又用于创建引用
Skia 客户端创建的 VkImage 的 SkSurface 和 SkImage 对象。

SkImage::getTextureHandle()、SkSurface::getTextureHandle() 和
SkSurface::getRenderTargetHandle() 返回的 GrBackendObject 应被
解释为 GrVkImageInfo*。这允许客户端获取 SkImage 或 SkSurface 的
底层 VkImage。

GrVkImageInfo 指定了 VkImage 和关联的状态（平铺、布局、格式等）。
通过 getTextureHandle() 或 getRenderTargetHandle() 获取 GrVkImageInfo* 后，
客户端应在使用 VkImage 之前检查 fImageLayout 字段以了解
Skia 将 VkImage 留在什么布局 (layout) 中。如果客户端更改了 VkImage 的布局，
应在恢复 Skia 渲染之前调用
GrVkImageInfo::updateImageLayout(VkImageLayout layout)。

客户端负责在 Skia 对通过 GrVkImageInfo 导入的 VkImage 执行 I/O 之前
进行任何所需的同步或屏障 (barrier)。Skia 将
假设它可以开始发出引用 VkImage 的命令，无需额外的同步。

