# GrVkUtil

> 源文件
> - src/gpu/ganesh/vk/GrVkUtil.h
> - src/gpu/ganesh/vk/GrVkUtil.cpp

## 概述

`GrVkUtil` 是 Ganesh Vulkan 后端的核心工具模块，提供了 Vulkan 格式查询、着色器编译和调试等基础功能。该模块定义了一系列宏和工具函数，用于简化 Vulkan API 调用、错误处理和格式转换。

主要功能包括：
- **格式支持查询**：检查 Vulkan 格式是否被 Skia 支持
- **格式描述转换**：将 Vulkan 格式转换为 Skia 颜色格式描述
- **着色器编译**：将 SkSL 代码编译为 SPIR-V 并创建 Vulkan 着色器模块
- **调试宏**：提供可选的 Vulkan API 调用跟踪和日志功能
- **错误处理**：统一的 Vulkan 结果检查和设备丢失处理

## 架构位置

`GrVkUtil` 位于 Ganesh Vulkan 后端的基础设施层：

```
Ganesh GPU Backend
└── Vulkan Backend (src/gpu/ganesh/vk/)
    ├── GrVkGpu (使用工具函数)
    ├── GrVkCaps (使用格式查询)
    ├── GrVkPipelineStateBuilder (使用着色器编译)
    └── GrVkUtil (本模块) ← 被所有 Vulkan 组件依赖
        ├── 格式工具
        ├── 着色器编译工具
        └── API 调用宏
```

该模块是 Vulkan 后端的横切关注点，被几乎所有 Vulkan 相关代码使用。

## 主要类与结构体

本文件主要提供工具函数和宏定义，没有定义类，但包含重要的宏和 constexpr 函数。

### 核心宏定义

| 宏名称 | 用途 | 参数 |
|--------|------|------|
| `GR_VK_CALL(IFACE, X)` | 调用 Vulkan API 函数 | `IFACE`: Vulkan 接口，`X`: 函数调用 |
| `GR_VK_LOG_IF_NOT_SUCCESS(GPU, RESULT, X, ...)` | 记录非成功的 Vulkan 调用 | `GPU`: GrVkGpu 实例，`RESULT`: VkResult，`X`: 格式化字符串 |
| `GR_VK_CALL_RESULT(GPU, RESULT, X)` | 调用 API 并检查结果 | 同上，会触发设备丢失检查 |
| `GR_VK_CALL_RESULT_NOCHECK(GPU, RESULT, X)` | 调用 API 不检查断言 | 用于可能合法失败的调用 |
| `GR_VK_CALL_ERRCHECK(GPU, X)` | 调用 API 并自动创建结果变量 | 简化错误检查的语法糖 |

### constexpr 函数

| 函数 | 返回类型 | 说明 |
|------|---------|------|
| `GrVkFormatDesc(VkFormat)` | `GrColorFormatDesc` | 将 Vulkan 格式转换为颜色格式描述 |

## 公共 API 函数

### 1. 格式支持查询

```cpp
bool GrVkFormatIsSupported(VkFormat format)
```

**功能**：检查给定的 Vulkan 格式是否被 Skia 支持

**支持的格式**：
- 标准 RGBA 格式：`VK_FORMAT_R8G8B8A8_UNORM`、`VK_FORMAT_B8G8R8A8_UNORM`
- sRGB 格式：`VK_FORMAT_R8G8B8A8_SRGB`
- RGB 格式：`VK_FORMAT_R8G8B8_UNORM`
- 双通道格式：`VK_FORMAT_R8G8_UNORM`
- 10 位格式：`VK_FORMAT_A2B10G10R10_UNORM_PACK32`
- 565 格式：`VK_FORMAT_R5G6B5_UNORM_PACK16`、`VK_FORMAT_B5G6R5_UNORM_PACK16`
- 4444 格式：`VK_FORMAT_B4G4R4A4_UNORM_PACK16`
- 单通道格式：`VK_FORMAT_R8_UNORM`
- 压缩格式：`VK_FORMAT_ETC2_R8G8B8_UNORM_BLOCK`、`VK_FORMAT_BC1_RGB_UNORM_BLOCK` 等
- 16 位浮点格式：`VK_FORMAT_R16G16B16A16_SFLOAT`、`VK_FORMAT_R16_SFLOAT` 等
- YUV 格式：`VK_FORMAT_G8_B8_R8_3PLANE_420_UNORM` 等
- 深度/模板格式：`VK_FORMAT_S8_UINT`、`VK_FORMAT_D24_UNORM_S8_UINT` 等

### 2. 格式描述转换

```cpp
static constexpr GrColorFormatDesc GrVkFormatDesc(VkFormat vkFormat)
```

**功能**：将 Vulkan 格式转换为 Skia 的颜色格式描述

**返回值**：
- 成功：包含通道位深和编码类型的 `GrColorFormatDesc`
- 失败：`GrColorFormatDesc::MakeInvalid()`（用于压缩格式和深度格式）

**示例**：
```cpp
// VK_FORMAT_R8G8B8A8_UNORM -> RGBA(8,8,8,8) Unorm
// VK_FORMAT_R16G16B16A16_SFLOAT -> RGBA(16,16,16,16) Float
```

### 3. 着色器编译与安装

```cpp
bool GrCompileVkShaderModule(
    GrVkGpu* gpu,
    const std::string& shaderString,
    VkShaderStageFlagBits stage,
    VkShaderModule* shaderModule,
    VkPipelineShaderStageCreateInfo* stageInfo,
    const SkSL::ProgramSettings& settings,
    SkSL::NativeShader* outSPIRV,
    SkSL::Program::Interface* outInterface
)
```

**功能**：将 SkSL 着色器源码编译为 Vulkan 着色器模块

**参数说明**：
- `gpu`：Vulkan GPU 上下文
- `shaderString`：SkSL 源代码字符串
- `stage`：着色器阶段（顶点或片段）
- `shaderModule`：输出的 Vulkan 着色器模块句柄
- `stageInfo`：输出的管线阶段创建信息
- `settings`：SkSL 编译设置
- `outSPIRV`：输出的 SPIR-V 二进制数据
- `outInterface`：输出的着色器接口信息

**返回值**：成功返回 `true`，失败返回 `false`

**内部流程**：
1. 调用 `skgpu::SkSLToSPIRV()` 将 SkSL 转换为 SPIR-V
2. 调用 `GrInstallVkShaderModule()` 创建 Vulkan 着色器模块
3. 使用 `TRACE_EVENT0` 记录性能追踪信息

```cpp
bool GrInstallVkShaderModule(
    GrVkGpu* gpu,
    const SkSL::NativeShader& spirv,
    VkShaderStageFlagBits stage,
    VkShaderModule* shaderModule,
    VkPipelineShaderStageCreateInfo* stageInfo
)
```

**功能**：从 SPIR-V 二进制创建 Vulkan 着色器模块

**内部实现**：
1. 填充 `VkShaderModuleCreateInfo` 结构体
2. 调用 `vkCreateShaderModule`
3. 配置 `VkPipelineShaderStageCreateInfo`，设置入口点为 `"main"`

## 内部实现细节

### 着色器阶段转换

```cpp
SkSL::ProgramKind vk_shader_stage_to_skiasl_kind(VkShaderStageFlagBits stage)
```

**功能**：将 Vulkan 着色器阶段标志转换为 SkSL 程序类型

**映射关系**：
- `VK_SHADER_STAGE_VERTEX_BIT` → `SkSL::ProgramKind::kVertex`
- `VK_SHADER_STAGE_FRAGMENT_BIT` → `SkSL::ProgramKind::kFragment`

### 调试日志系统

文件中预留了两种调试方式（默认禁用）：

```cpp
// 方式 1：简单日志
// #define GR_VK_DEBUG_LOG(X) SkDebugf("vk%s (%s:%d)\n", #X, __FILE__, __LINE__)

// 方式 2：性能追踪
// #define GR_VK_DEBUG_LOG(X) \
//     TRACE_EVENT1_ALWAYS("skia.gpu", "vk" #X, "line", __FILE__ ":" SK_MACRO_STRINGIFY(__LINE__))
```

启用后，所有 `GR_VK_CALL` 宏都会记录调用信息。

### 错误处理策略

```cpp
#define GR_VK_CALL_RESULT(GPU, RESULT, X)                                 \
    do {                                                                  \
        (RESULT) = GR_VK_CALL(GPU->vkInterface(), X);                     \
        GR_VK_LOG_IF_NOT_SUCCESS(GPU, RESULT, #X);                        \
        SkASSERT(VK_SUCCESS == RESULT || VK_ERROR_DEVICE_LOST == RESULT); \
        GPU->checkVkResult(RESULT);                                       \
    } while (false)
```

**关键设计**：
1. 自动记录失败的调用（除非设备已丢失）
2. 断言只允许成功或设备丢失两种结果
3. 调用 `checkVkResult()` 更新 GPU 状态

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrVkGpu` | GPU 上下文，提供接口和错误处理 |
| `GrVkCaps` | 能力查询，获取着色器编译能力 |
| `skgpu::VulkanInterface` | Vulkan 函数指针表 |
| `SkSL` | 着色器语言编译器 |
| `skgpu::SkSLToSPIRV` | SkSL 到 SPIR-V 的转换 |
| `GrDirectContext` | 获取错误处理器 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| `GrVkPipelineStateBuilder` | 使用着色器编译函数 |
| `GrVkTexture` | 使用格式查询函数 |
| `GrVkRenderTarget` | 使用格式描述函数 |
| 所有 Vulkan 资源类 | 使用 API 调用宏 |

## 设计模式与设计决策

### 1. 宏封装模式

通过宏封装 Vulkan API 调用，实现：
- **统一错误处理**：所有调用点自动包含日志和断言
- **可选调试**：通过条件编译启用/禁用调试日志
- **代码简洁**：减少样板代码

**权衡**：
- 优点：调用点简洁、统一错误处理
- 缺点：宏调试困难、可能隐藏控制流

### 2. constexpr 格式映射

`GrVkFormatDesc()` 使用 `constexpr` 实现编译期格式转换：
- **性能优势**：零运行时开销
- **类型安全**：编译期检查格式有效性
- **代码可读**：使用 switch-case 清晰表达映射关系

### 3. 分离编译与安装

将着色器编译分为两步：
1. `GrCompileVkShaderModule`：SkSL → SPIR-V → VkShaderModule
2. `GrInstallVkShaderModule`：SPIR-V → VkShaderModule（复用已编译代码）

**设计优势**：
- 支持着色器缓存（离线编译 SPIR-V）
- 允许跳过 SkSL 编译直接使用预编译 SPIR-V
- 更好的错误诊断（可以分别诊断编译和创建错误）

### 4. 错误处理层次

```
GR_VK_CALL_ERRCHECK  (最简单，自动创建结果变量)
    ↓
GR_VK_CALL_RESULT     (标准错误检查)
    ↓
GR_VK_CALL_RESULT_NOCHECK (宽松检查，不断言)
    ↓
GR_VK_CALL            (底层调用，无检查)
```

不同场景使用不同层次的宏，平衡安全性和灵活性。

### 5. 格式支持策略

**白名单设计**：只支持明确列出的格式
- **安全性**：避免使用未测试的格式
- **可维护性**：清晰的支持列表
- **扩展性**：添加新格式需显式修改代码

## 性能考量

### 1. 编译期格式转换

```cpp
static constexpr GrColorFormatDesc GrVkFormatDesc(VkFormat vkFormat)
```

使用 `constexpr` 确保格式映射在编译期完成，运行时零开销。

### 2. 着色器编译追踪

```cpp
TRACE_EVENT0("skia.shaders", "CompileVkShaderModule");
TRACE_EVENT0("skia.shaders", "InstallVkShaderModule");
```

使用 Skia 的性能追踪系统记录着色器编译时间，便于性能分析。

### 3. 错误日志优化

```cpp
if (RESULT != VK_SUCCESS && !GPU->isDeviceLost())
```

只在设备未丢失时记录错误，避免设备丢失后产生大量无用日志。

### 4. 调试开销

调试日志默认禁用，通过条件编译避免在 Release 构建中引入性能开销：
- Debug 构建：可启用详细日志
- Release 构建：零日志开销

### 5. SPIR-V 二进制复用

`GrInstallVkShaderModule` 接受预编译的 SPIR-V，支持：
- 着色器缓存机制
- 减少重复编译
- 加快应用启动速度

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/vk/GrVkGpu.h` | 核心依赖 | 提供 GPU 上下文和接口 |
| `src/gpu/ganesh/vk/GrVkCaps.h` | 能力查询 | 提供 Vulkan 能力信息 |
| `src/gpu/vk/VulkanInterface.h` | API 接口 | Vulkan 函数指针定义 |
| `src/gpu/vk/VulkanUtilsPriv.h` | 共享工具 | 跨后端的 Vulkan 工具 |
| `src/sksl/codegen/SkSLNativeShader.h` | 编译输出 | SPIR-V 数据结构 |
| `src/sksl/SkSLProgramKind.h` | 着色器类型 | SkSL 程序类型定义 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 类型定义 | 颜色格式描述类型 |
| `src/gpu/ganesh/vk/GrVkPipelineStateBuilder.h` | 主要使用者 | 使用着色器编译功能 |
| `src/gpu/ganesh/vk/GrVkVaryingHandler.h` | 同层组件 | Varying 处理器 |
