# ContextType

> 源文件
> - tools/gpu/ContextType.h
> - tools/gpu/ContextType.cpp

## 概述

`ContextType` 是 Skia GPU 工具集中用于标识和分类不同 GPU 上下文类型的枚举和工具模块。Skia 支持多种 GPU 后端（OpenGL、Vulkan、Metal、Direct3D 等）和多种抽象层（原生、ANGLE、Dawn），该模块提供统一的类型系统来表示这些不同的上下文配置。这对于测试框架在不同平台和后端组合上运行测试至关重要。

核心功能包括：定义涵盖所有支持的 GPU 后端和抽象层组合的枚举类型、提供上下文类型到可读名称的转换、区分原生后端、抽象层后端和模拟后端、将上下文类型映射到 Ganesh 和 Graphite 的后端 API 枚举。该模块是 Skia 测试基础设施的核心组件，允许测试在所有支持的配置上自动运行。

## 架构位置

`ContextType` 位于 `tools/gpu/` 目录下，是 GPU 测试工具层的基础组件。在 Skia 架构中：

1. **类型系统层**：提供测试框架使用的统一类型标识
2. **后端抽象层**：桥接测试代码和特定 GPU 后端实现
3. **平台适配层**：处理不同平台上可用后端的差异

依赖关系：
- **上游依赖**：`GrBackendApi`（Ganesh）、`skgpu::BackendApi`（Graphite）
- **下游使用**：`GrContextFactory`（上下文工厂）、测试框架、GM 测试、基准测试

该模块的设计独立于具体的 Skia 后端实现，作为测试层和实现层之间的接口。

## 主要类与结构体

### skgpu::ContextType 枚举

定义所有支持的 GPU 上下文类型。

**原生后端：**
- `kGL`：桌面 OpenGL
- `kGLES`：OpenGL ES（嵌入式系统）
- `kVulkan`：Vulkan API
- `kMetal`：Apple Metal（macOS/iOS）
- `kDirect3D`：Direct3D 12（Windows）

**ANGLE 后端（OpenGL ES 模拟器）：**
- `kANGLE_D3D9_ES2`：ANGLE 在 Direct3D 9 上模拟 OpenGL ES 2
- `kANGLE_D3D11_ES2`：ANGLE 在 Direct3D 11 上模拟 OpenGL ES 2
- `kANGLE_D3D11_ES3`：ANGLE 在 Direct3D 11 上模拟 OpenGL ES 3
- `kANGLE_GL_ES2`：ANGLE 在 OpenGL 上模拟 OpenGL ES 2
- `kANGLE_GL_ES3`：ANGLE 在 OpenGL 上模拟 OpenGL ES 3
- `kANGLE_Metal_ES2`：ANGLE 在 Metal 上模拟 OpenGL ES 2
- `kANGLE_Metal_ES3`：ANGLE 在 Metal 上模拟 OpenGL ES 3

**Dawn 后端（WebGPU 实现）：**
- `kDawn_D3D11`：Dawn 使用 Direct3D 11 后端
- `kDawn_D3D12`：Dawn 使用 Direct3D 12 后端
- `kDawn_Metal`：Dawn 使用 Metal 后端
- `kDawn_Vulkan`：Dawn 使用 Vulkan 后端
- `kDawn_OpenGL`：Dawn 使用 OpenGL 后端
- `kDawn_OpenGLES`：Dawn 使用 OpenGL ES 后端

**特殊类型：**
- `kMock`：模拟上下文，不实际进行 GPU 绘图，用于测试框架逻辑

**常量：**
- `kLastContextType`：最后一个枚举值（`kMock`）
- `kContextTypeCount`：上下文类型总数

## 公共 API 函数

### ContextTypeName

```cpp
const char* ContextTypeName(skgpu::ContextType type);
```

返回上下文类型的可读名称字符串。

**用途：**
- 测试报告和日志输出
- 调试信息显示
- 命令行参数解析

**示例：**
```cpp
ContextTypeName(ContextType::kVulkan) → "Vulkan"
ContextTypeName(ContextType::kANGLE_D3D11_ES3) → "ANGLE D3D11 ES3"
ContextTypeName(ContextType::kDawn_Metal) → "Dawn Metal"
```

### IsNativeBackend

```cpp
bool IsNativeBackend(skgpu::ContextType type);
```

判断是否为原生 GPU 后端（不经过额外的抽象层）。

**返回 `true` 的类型：**
- `kGL`、`kGLES`、`kVulkan`、`kMetal`、`kDirect3D`

**返回 `false` 的类型：**
- 所有 ANGLE 变体（在原生 API 上添加了 OpenGL ES 抽象）
- 所有 Dawn 变体（WebGPU 抽象层）
- `kMock`（不使用 GPU）

**用途：**
- 区分直接使用 GPU 驱动的场景和通过抽象层的场景
- 某些测试可能只在原生后端上运行（避免抽象层的潜在问题）

### IsDawnBackend

```cpp
bool IsDawnBackend(skgpu::ContextType type);
```

判断是否为 Dawn（WebGPU）后端。

**返回 `true` 的类型：**
- `kDawn_D3D11`、`kDawn_D3D12`、`kDawn_Metal`、`kDawn_Vulkan`、`kDawn_OpenGL`、`kDawn_OpenGLES`

**用途：**
- 识别使用 WebGPU API 的场景
- Dawn 特有的功能或限制处理

### IsRenderingContext

```cpp
bool IsRenderingContext(ContextType type);
```

判断是否为真正的渲染上下文（可以进行 GPU 绘图）。

**返回值：**
- `kMock` → `false`
- 其他所有类型 → `true`

**用途：**
- 跳过需要真实 GPU 绘图的测试（在 Mock 上下文上）
- 验证测试结果（Mock 不产生像素输出）

### ganesh::ContextTypeBackend（Ganesh）

```cpp
GrBackendApi skgpu::ganesh::ContextTypeBackend(skgpu::ContextType type);
```

将 `ContextType` 映射到 Ganesh 的 `GrBackendApi` 枚举。

**映射规则：**
- OpenGL 系列（`kGL`、`kGLES`、所有 ANGLE）→ `GrBackendApi::kOpenGL`
- `kVulkan` → `GrBackendApi::kVulkan`
- `kMetal` → `GrBackendApi::kMetal`
- `kDirect3D` → `GrBackendApi::kDirect3D`
- 所有 Dawn 变体 → `GrBackendApi::kUnsupported`（Ganesh 不支持 Dawn）
- `kMock` → `GrBackendApi::kMock`

**注意：** ANGLE 的所有变体都映射到 OpenGL，因为 ANGLE 提供 OpenGL/ES API。

### graphite::ContextTypeBackend（Graphite）

```cpp
skgpu::BackendApi skgpu::graphite::ContextTypeBackend(ContextType type);
```

将 `ContextType` 映射到 Graphite 的 `BackendApi` 枚举。

**映射规则：**
- OpenGL 系列、ANGLE 系列、`kDirect3D` → `BackendApi::kUnsupported`（Graphite 不支持这些）
- `kVulkan` → `BackendApi::kVulkan`
- `kMetal` → `BackendApi::kMetal`
- 所有 Dawn 变体 → `BackendApi::kDawn`
- `kMock` → `BackendApi::kMock`

**注意：** Graphite 不支持 OpenGL 和 Direct3D 12（仅支持 Vulkan、Metal 和 Dawn）。

## 内部实现细节

### 枚举设计

使用连续的枚举值，从 `kGL = 0` 到 `kMock`：
- 便于数组索引（`kContextTypeCount` 作为数组大小）
- 允许迭代所有类型（在测试框架中常用）

### 命名转换实现

`ContextTypeName` 使用简单的 `switch` 语句：
```cpp
switch (type) {
    case ContextType::kVulkan: return "Vulkan";
    case ContextType::kMetal: return "Metal";
    // ...
}
SkUNREACHABLE;  // 确保所有枚举值都被处理
```

**优点：**
- 编译时检查完整性（缺少 case 会警告）
- 高效（直接跳转，无需哈希或查表）
- 易于维护（添加新类型时编译器会提示）

### 后端分类实现

`IsNativeBackend` 使用白名单方式：
```cpp
switch (type) {
    case ContextType::kDirect3D:
    case ContextType::kGL:
    case ContextType::kGLES:
    case ContextType::kMetal:
    case ContextType::kVulkan:
        return true;
    default:
        return false;
}
```

这确保新增的抽象层后端默认返回 `false`（安全默认值）。

### Ganesh 和 Graphite 的差异

两个后端对 OpenGL 的态度不同：
- **Ganesh**：完全支持 OpenGL/ES 和 ANGLE
- **Graphite**：不支持 OpenGL（专注于现代 API）

Dawn 的支持相反：
- **Ganesh**：不支持 Dawn
- **Graphite**：完全支持 Dawn（作为 WebGPU 的实现）

这反映了两个后端的设计目标差异：
- Ganesh：广泛兼容性，支持旧平台
- Graphite：现代化架构，专注于现代 API

### 条件编译

使用 `#if defined(SK_GANESH)` 和 `#if defined(SK_GRAPHITE)` 分离后端特定代码：
- 允许只编译需要的后端
- 避免链接未使用后端的代码
- 减少二进制大小

## 依赖关系

### 核心依赖

- **SkTypes.h**：Skia 基础类型定义
- **GpuTypes.h**：GPU 通用类型（如 `skgpu` 命名空间）

### Ganesh 依赖

- **GrTypes.h**：Ganesh 类型定义（`GrBackendApi` 枚举）

### Graphite 依赖

- **BackendApi**（通过 GpuTypes.h 或 Graphite 头文件）

### 被依赖

- **GrContextFactory**：根据 `ContextType` 创建实际的 GPU 上下文
- **测试框架（DM）**：遍历所有 `ContextType` 运行测试
- **GM 测试**：选择特定的 `ContextType` 运行
- **基准测试**：在不同后端上测量性能

## 设计模式与设计决策

### 枚举类（Enum Class）

使用 `enum class` 而非普通 `enum`：
- 强类型检查，避免隐式转换
- 命名空间隔离（`ContextType::kVulkan` 而非 `kVulkan`）
- 现代 C++ 最佳实践

### 命名空间组织

类型和函数位于 `skgpu` 命名空间，后端特定函数进一步嵌套：
- `skgpu::ContextType`：通用类型
- `skgpu::ganesh::ContextTypeBackend`：Ganesh 特定
- `skgpu::graphite::ContextTypeBackend`：Graphite 特定

这种组织清晰地表达了所有权和适用范围。

### 查询函数的设计

提供多个查询函数（`IsNativeBackend`、`IsDawnBackend` 等）而非单一的"类别"属性：
- 灵活性高，不同的分类维度可以独立演化
- 表达力强，函数名直接说明查询意图
- 可扩展，添加新的分类维度不影响现有代码

### 平台可用性注释

头文件注释："The availability of context types is subject to platform and build configuration restrictions."

这提醒用户：
- 不是所有 `ContextType` 在所有平台上都可用
- 需要通过 `GrContextFactory` 检查实际可用性
- 枚举定义与运行时可用性分离

### 未来扩展性

枚举设计为开放式：
- 新的后端或抽象层可以轻松添加
- 查询函数通过 `default` 分支处理未知类型
- `kLastContextType` 常量自动更新

### 测试友好设计

`kContextTypeCount` 和连续枚举值使得测试框架可以：
```cpp
for (int i = 0; i < kContextTypeCount; ++i) {
    auto type = static_cast<ContextType>(i);
    // 在每个类型上运行测试
}
```

这是测试框架的核心迭代模式。

## 性能考量

### 查询函数的效率

所有查询函数（`IsNativeBackend`、`ContextTypeName` 等）使用 `switch` 语句：
- 编译器通常优化为跳转表
- O(1) 时间复杂度
- 无内存分配或查表开销

### 枚举大小

`ContextType` 是 `enum class`，默认底层类型为 `int`（通常 32 位）：
- 对于只有 20 多个枚举值，可以使用更小的类型（如 `uint8_t`）节省内存
- 但在测试代码中，这点内存开销可以忽略
- 32 位对齐可能在某些架构上更高效

### 运行时开销

该模块主要在测试初始化阶段使用：
- 决定运行哪些测试
- 创建 GPU 上下文
- 不在热循环中，性能不是瓶颈

### 编译时开销

条件编译减少未使用后端的代码：
- 如果只编译 Ganesh，Graphite 相关代码被排除
- 减少编译时间和二进制大小
- 对于移动平台或嵌入式系统尤为重要

## 相关文件

### 核心依赖

- `include/core/SkTypes.h` - Skia 基础类型
- `include/gpu/GpuTypes.h` - GPU 通用类型

### Ganesh 相关

- `include/gpu/ganesh/GrTypes.h` - Ganesh 类型定义（`GrBackendApi`）
- `tools/gpu/GrContextFactory.h` - 上下文工厂（主要使用者）

### Graphite 相关

- `include/gpu/graphite/GraphiteTypes.h` - Graphite 类型定义
- `tools/gpu/GraphiteContextFactory.h` - Graphite 上下文工厂（如果存在）

### 使用场景

- `dm/DM.cpp` - 测试框架主程序
- `gm/gm.cpp` - GM 测试框架
- `bench/` - 性能基准测试
- `tools/gpu/TestContext.h` - 测试上下文抽象

### 相关工具类

- `tools/gpu/GrContextFactory.h` - 根据 `ContextType` 创建 `GrDirectContext`
- `tools/gpu/TestContext.h` - 测试上下文接口
- `tools/gpu/BackendSurfaceFactory.h` - 后端 Surface 创建（需要知道上下文类型）

## 实际应用场景

### 测试框架中的使用

DM 测试框架使用 `ContextType` 遍历所有后端：
```cpp
for (int i = 0; i < skgpu::kContextTypeCount; ++i) {
    auto type = static_cast<skgpu::ContextType>(i);
    if (!skgpu::IsRenderingContext(type)) continue;  // 跳过 Mock

    auto context = contextFactory.get(type);
    if (!context) continue;  // 跳过不可用的后端

    runTestOnContext(test, context, skgpu::ContextTypeName(type));
}
```

### GM 测试的后端选择

GM 测试可以指定支持的后端：
```cpp
DEF_GM(return new MyGM;)

// 只在原生后端上运行
DEF_CONDITIONAL_GM(
    return skgpu::IsNativeBackend(contextType) ? new MyGM : nullptr;
)
```

### 性能基准测试的分组

基准测试工具按后端分组结果：
```cpp
for (auto type : testedTypes) {
    if (skgpu::IsDawnBackend(type)) {
        results["Dawn"].push_back(runBench(type));
    } else if (skgpu::IsNativeBackend(type)) {
        results["Native"].push_back(runBench(type));
    }
}
```

### 命令行参数解析

测试工具通常支持通过名称指定后端：
```bash
dm --config vulkan metal angle_d3d11_es3
```

解析代码使用 `ContextTypeName` 匹配：
```cpp
for (int i = 0; i < skgpu::kContextTypeCount; ++i) {
    auto type = static_cast<skgpu::ContextType>(i);
    if (configName == skgpu::ContextTypeName(type)) {
        return type;
    }
}
```
