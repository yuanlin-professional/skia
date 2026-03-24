# GrVkCaps

> 源文件: `src/gpu/ganesh/vk/GrVkCaps.h`, `src/gpu/ganesh/vk/GrVkCaps.cpp`

## 概述

`GrVkCaps` 是 Skia Ganesh Vulkan 后端的能力查询类，继承自 `GrCaps`。它封装了 Vulkan 物理设备的全部图形能力、格式支持、供应商特定的修正措施，以及各种驱动程序规避策略。该类是 Vulkan 后端做出格式选择、渲染策略、拷贝路径等决策的核心依据。

## 架构位置

`GrVkCaps` 在 Ganesh 渲染架构中位于最底层的能力抽象层，是所有 Vulkan 渲染决策的基础。它在 `GrVkGpu` 创建时初始化，之后作为只读对象被整个渲染管线引用。`GrCaps` 是所有后端共享的能力基类，`GrVkCaps` 在此基础上增加了大量 Vulkan 特有的能力查询。

## 主要类与结构体

### `GrVkCaps`
- 继承自 `GrCaps`，提供通用 GPU 能力查询接口
- 包含 `FormatInfo` 和 `ColorTypeInfo` 内部结构体用于管理格式支持信息
- 包含 `IntelGPUType` 枚举用于识别 Intel GPU 世代

### `FormatInfo`（内部结构体）
- 存储每种 `VkFormat` 的能力标志（可纹理化、可渲染、Blit 源/目标）
- 存储线性和最优 tiling 的标志
- 存储支持的颜色采样数
- 包含 `ColorTypeInfo` 数组用于颜色类型映射

### `ColorTypeInfo`（内部结构体）
- 映射 `GrColorType` 到特定 `VkFormat`
- 包含上传标志、可渲染标志、读写 Swizzle 等信息

## 公共 API 函数

### 格式查询
- `isFormatSRGB()` / `isFormatTexturable()` / `isFormatRenderable()` - 查询格式的 sRGB、纹理、渲染能力
- `isVkFormatTexturable()` / `isVkFormatTexturableLinearly()` - 直接通过 VkFormat 查询
- `getRenderTargetSampleCount()` / `maxRenderTargetSampleCount()` - 查询渲染目标的采样数
- `formatCanBeDstofBlit()` / `formatCanBeSrcofBlit()` - 查询 Blit 操作能力

### 拷贝能力
- `canCopyImage()` - 检查是否可通过 `vkCmdCopyImage` 拷贝
- `canCopyAsBlit()` - 检查是否可通过 Blit 拷贝
- `canCopyAsResolve()` - 检查是否可通过 resolve 拷贝

### 设备特性查询
- `mustSyncCommandBuffersWithQueue()` - Windows Nvidia/Imagination 的围栏同步需求
- `shouldAlwaysUseDedicatedImageMemory()` - 是否应使用专用图像内存
- `supportsSwapchain()` / `supportsYcbcrConversion()` / `supportsAndroidHWBExternalMemory()` - 扩展支持
- `preferredStencilFormat()` - 首选模板格式
- `preferPrimaryOverSecondaryCommandBuffers()` - 命令缓冲区策略
- `gpuOnlyBuffersMorePerformant()` / `shouldPersistentlyMapCpuToGpuBuffers()` - 缓冲区策略
- `supportsDiscardableMSAAForDMSAA()` / `supportsMemorylessAttachments()` - DMSAA 支持

### 管线构建
- `makeDesc()` - 构建 `GrProgramDesc`，包含 Vulkan 管线完整状态的 key
- `addExtraSamplerKey()` - 添加 YCbCr 采样器相关的额外 key

## 内部实现细节

### 初始化流程
1. 构造函数设置 Vulkan 始终支持的基础能力（mipmap、NPOT 纹理等）
2. `init()` 检查扩展支持（swapchain、Android HWB、YCbCr 转换、DRM 格式修饰符等）
3. `initGrCaps()` 设置通用 GPU 能力（最大纹理尺寸、混合方程等）
4. `initShaderCaps()` 配置着色器能力（GLSL 版本、精度等）
5. `initFormatTable()` 枚举 25 种 `VkFormat`，查询每种格式的能力和颜色类型映射
6. `initStencilFormat()` 选择首选模板格式（S8 > D24S8 > D32S8）
7. `applyDriverCorrectnessWorkarounds()` 应用供应商特定的修正措施

### 供应商修正措施
- **Qualcomm**: 禁用 `vkCmdUpdateBuffer`、纹理屏障、间接绘制
- **ARM (Mali)**: Android 28 及以下需要专用内存分配、禁用 DMSAA、修正 Perlin 噪声
- **Nvidia (Windows)**: 需要队列同步围栏
- **Intel (Windows)**: Gen 9+ 禁用纹理屏障
- **AMD**: 限制顶点属性最大数为 32
- **Swiftshader**: 禁用 scratch buffer 重用
- **Imagination**: 需要队列同步、`atan2` 实现为 `atan(y/x)`

### 格式表
- 支持 25 种 `VkFormat`，按使用频率排序
- 每种格式记录线性和最优 tiling 标志
- 格式兼容性类用于 `vkCmdCopyImage` 的合法性检查

## 依赖关系

- **GrCaps**: 基类，定义通用 GPU 能力接口
- **GrShaderCaps**: 着色器能力子对象
- **skgpu::VulkanInterface**: Vulkan API 函数指针表
- **skgpu::VulkanExtensions**: Vulkan 扩展查询
- **GrVkRenderPass / GrVkRenderTarget**: 用于渲染通道和管线 key 构建
- **GrVkUniformHandler / GrVkSampler**: 用于 uniform 和采样器绑定信息

## 设计模式与设计决策

1. **初始化时全量查询**: 所有能力在构造时一次性查询并缓存，运行时为纯查询操作
2. **格式表设计**: 使用固定大小的数组和线性搜索查找格式，保证所有 25 种格式都有对应信息
3. **颜色类型优先级**: `setColorType()` 按格式列表顺序选择第一个支持的格式
4. **防御性编程**: 对未知 Intel GPU 世代返回 0，确保新的驱动修正不会意外应用于旧设备
5. **平台条件编译**: 通过 `SK_BUILD_FOR_WIN`、`SK_BUILD_FOR_ANDROID` 等宏进行平台特定的修正

## 性能考量

- 格式查询为 O(n) 线性搜索（n=25），对于频繁调用可能有影响，但格式数量有限
- ARM GPU 上启用 memoryless attachments 和 discardable MSAA，可减少 50-60% 的性能开销
- 离散 GPU (Nvidia/AMD) 上启用 GPU-only buffer 以获得更好的读取性能
- 离散 GPU 上禁用持久映射的 CPU-to-GPU buffer，利用特殊的 DEVICE_LOCAL+HOST_VISIBLE 内存
- Qualcomm 上禁用间接绘制以避免性能下降

## 相关文件

- `src/gpu/ganesh/GrCaps.h` - 通用 GPU 能力基类
- `src/gpu/ganesh/GrShaderCaps.h` - 着色器能力
- `src/gpu/ganesh/vk/GrVkGpu.h` - Vulkan GPU 实现
- `src/gpu/ganesh/vk/GrVkRenderPass.h` - 渲染通道
- `src/gpu/ganesh/vk/GrVkRenderTarget.h` - 渲染目标
- `include/gpu/vk/VulkanExtensions.h` - Vulkan 扩展管理
- `src/gpu/vk/VulkanUtilsPriv.h` - Vulkan 工具函数
