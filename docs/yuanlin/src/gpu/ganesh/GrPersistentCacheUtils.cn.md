# GrPersistentCacheUtils

> 源文件: src/gpu/ganesh/GrPersistentCacheUtils.h, src/gpu/ganesh/GrPersistentCacheUtils.cpp

## 概述

`GrPersistentCacheUtils` 是一个命名空间，提供了用于序列化和反序列化着色器缓存数据的工具函数。该模块负责将编译后的着色器（GLSL、SPIR-V 等）打包成不透明的二进制数据块（blobs），并在需要时将其解包还原。这些工具函数被 Ganesh 后端代码和调试工具共享使用。

主要功能包括：
- 将编译后的着色器和元数据打包成 `SkData` 对象
- 从序列化数据中恢复着色器和相关接口信息
- 管理着色器缓存的版本控制
- 处理不同着色器类型（顶点、片段、几何等）的序列化

该模块是 Skia 持久化缓存系统的核心组件，通过避免重复编译着色器来显著提升渲染性能。

## 架构位置

`GrPersistentCacheUtils` 位于 Ganesh GPU 后端的核心层，作为着色器缓存系统的序列化工具：

```
src/gpu/ganesh/
├── GrPersistentCacheUtils    # 着色器缓存序列化工具
├── GrContext                  # 使用缓存系统的主要上下文
├── gl/GrGLGpu                # GL 后端使用此工具序列化 GLSL
├── vk/GrVkGpu                # Vulkan 后端使用此工具序列化 SPIR-V
└── mtl/GrMtlGpu              # Metal 后端使用此工具序列化 MSL
```

它与 `SkSL` 编译器模块紧密协作，处理编译器生成的着色器代码和接口信息。

## 主要类与结构体

### ShaderMetadata

着色器元数据结构，包含编译和运行时需要的额外信息。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fSettings` | `SkSL::ProgramSettings*` | SkSL 程序设置指针 |
| `fAttributeNames` | `skia_private::TArray<std::string>` | 顶点属性名称数组 |
| `fHasSecondaryColorOutput` | `bool` | 是否有次级颜色输出 |
| `fPlatformData` | `sk_sp<SkData>` | 平台特定的附加数据 |

## 公共 API 函数

### GetCurrentVersion()

```cpp
int GetCurrentVersion();
```

返回当前的缓存版本号（当前为 12）。每当 `SkSL::Program::Interface` 结构发生变化时，版本号必须递增以使旧缓存失效。

### PackCachedShaders()

```cpp
sk_sp<SkData> PackCachedShaders(
    SkFourByteTag shaderType,
    const SkSL::NativeShader shaders[],
    const SkSL::Program::Interface interfaces[],
    int numInterfaces,
    const ShaderMetadata* meta = nullptr
);
```

将多个着色器打包成单个 `SkData` 对象：
- **参数**：
  - `shaderType`: 四字节标签标识着色器类型
  - `shaders`: 着色器数组（文本或二进制）
  - `interfaces`: 程序接口数组
  - `numInterfaces`: 接口数量（1 到 kGrShaderTypeCount）
  - `meta`: 可选的元数据指针
- **返回值**：包含序列化数据的 `SkData` 智能指针

**序列化格式**：
1. 版本号（int）
2. 着色器类型标签（uint）
3. 对每个着色器阶段：
   - 着色器代码（二进制或文本）
   - 接口信息结构体
4. 元数据（如果提供）

### GetType()

```cpp
SkFourByteTag GetType(SkReadBuffer* reader);
```

从序列化数据中读取着色器类型标签。如果版本不匹配，返回无效标签（~0）。

### UnpackCachedShaders()

```cpp
bool UnpackCachedShaders(
    SkReadBuffer* reader,
    SkSL::NativeShader shaders[],
    bool areShadersBinary,
    SkSL::Program::Interface interfaces[],
    int numInterfaces,
    ShaderMetadata* meta = nullptr
);
```

从序列化数据中恢复着色器和接口信息：
- **参数**：
  - `reader`: 读取器对象
  - `shaders`: 输出着色器数组
  - `areShadersBinary`: 着色器是否为二进制格式
  - `interfaces`: 输出接口数组
  - `numInterfaces`: 需要的接口数量
  - `meta`: 可选的输出元数据指针
- **返回值**：成功返回 true，失败返回 false 并清空着色器数据

## 内部实现细节

### 版本控制机制

```cpp
static constexpr int kCurrentVersion = 12;
```

使用编译时断言确保版本更新：
```cpp
struct KnownSkSLProgramInterface {
    bool useLastFragColor;
    bool useRTFlipUniform;
    bool outputSecondaryColor;
};
static_assert(sizeof(SkSL::Program::Interface) == sizeof(KnownSkSLProgramInterface));
```

当 `SkSL::Program::Interface` 结构体变化时，该断言会失败，提醒开发者更新版本号。

### 着色器类型处理

系统始终序列化 `kGrShaderTypeCount` 个着色器槽位。如果实际提供的接口少于这个数量，会复制最后一个接口来填充：

```cpp
writer.writePad32(&interfaces[std::min(i, numInterfaces - 1)],
                  sizeof(SkSL::Program::Interface));
```

### 二进制 vs 文本格式

着色器可以存储为：
- **二进制格式**：SPIR-V 使用 `uint32_t` 数组
- **文本格式**：GLSL/MSL 使用字符串

序列化时根据 `shaders[i].isBinary()` 自动选择格式。

### 元数据序列化

元数据序列化包含：
1. 元数据是否存在的标志位
2. ProgramSettings（如果存在）
3. 属性名称数组
4. 次级颜色输出标志
5. 平台特定数据（由平台自行读取）

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkData` | 数据存储和传输 |
| `SkReadBuffer`/`SkWriteBuffer` | 序列化框架 |
| `SkSL::NativeShader` | 着色器表示 |
| `SkSL::Program::Interface` | 着色器接口信息 |
| `SkSL::ProgramSettings` | 编译器设置 |
| `GrTypesPriv` | 着色器类型计数等常量 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrGLGpu` | 缓存 GLSL 着色器 |
| `GrVkGpu` | 缓存 SPIR-V 二进制 |
| `GrMtlGpu` | 缓存 MSL 着色器 |
| `GrPersistentCache` | 作为序列化工具 |
| 调试工具 | 检查和验证缓存内容 |

## 设计模式与设计决策

### 命名空间设计

使用命名空间而非类的原因：
- 这些函数是无状态的工具函数
- 不需要实例化对象
- 提供清晰的作用域分隔

### 版本控制策略

采用显式版本号而非哈希：
- **优点**：
  - 明确的版本管理
  - 便于调试和日志记录
  - 版本不匹配时快速失败
- **实现**：在序列化数据的开头存储版本号

### 统一接口设计

所有后端（GL、Vulkan、Metal）使用相同的序列化格式：
- 简化工具开发
- 便于跨平台缓存共享（理论上）
- 代码复用最大化

### 防御性编程

解包失败时清空所有着色器数据：
```cpp
if (!reader->isValid()) {
    for (int i = 0; i < kGrShaderTypeCount; ++i) {
        shaders[i].fText.clear();
        shaders[i].fBinary.clear();
    }
}
```

## 性能考量

### 序列化效率

- 使用 `SkBinaryWriteBuffer` 提供高效的二进制序列化
- 直接写入字节数组，避免不必要的拷贝
- `writePad32` 确保结构体对齐，提高读取性能

### 缓存命中优化

版本号放在开头的原因：
- 快速检测不兼容的缓存
- 避免解析整个数据块
- 减少无效缓存的处理时间

### 内存管理

- 使用 `sk_sp<SkData>` 进行引用计数管理
- 着色器文本和二进制数据共享内存
- 避免不必要的深拷贝

### 扩展性考虑

元数据采用可选设计：
- 向后兼容性：旧代码可以忽略元数据
- 灵活性：不同后端可以存储自定义平台数据
- 未来扩展：可以添加新的元数据字段而不破坏兼容性

## 相关文件

| 文件路径 | 关系 |
|---------|------|
| `src/sksl/ir/SkSLProgram.h` | 定义 Program::Interface 结构 |
| `src/sksl/SkSLProgramSettings.h` | 定义编译器设置 |
| `src/sksl/codegen/SkSLNativeShader.h` | 定义着色器表示 |
| `src/core/SkReadBuffer.h` | 提供反序列化功能 |
| `src/core/SkWriteBuffer.h` | 提供序列化功能 |
| `src/gpu/ganesh/gl/GrGLGpu.cpp` | GL 后端使用示例 |
| `src/gpu/ganesh/vk/GrVkGpu.cpp` | Vulkan 后端使用示例 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 定义 kGrShaderTypeCount |
