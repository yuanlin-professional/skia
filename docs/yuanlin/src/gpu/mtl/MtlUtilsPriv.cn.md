# MtlUtilsPriv

> 源文件
> - src/gpu/mtl/MtlUtilsPriv.h

## 概述

`MtlUtilsPriv.h` 是 Skia Metal GPU 后端的内部工具函数头文件，声明了 Metal 像素格式处理函数和 SkSL 到 MSL（Metal Shading Language）的编译函数。该头文件为 Metal 后端提供格式查询、着色器编译等核心功能的接口。

主要内容：
- SkSL 到 MSL 的编译接口
- Metal 格式压缩判断
- Metal 格式属性查询（通道、字节数）
- Metal 格式转换（到压缩类型、到字符串）

## 架构位置

```
skgpu (GPU 抽象层)
  └── mtl (Metal 后端)
      ├── MtlUtilsPriv.h (工具头文件 - 本文件)
      ├── MtlUtils.mm (实现文件)
      └── 其他 Metal 后端组件
```

## 主要函数声明

### SkSLToMSL

```cpp
inline bool SkSLToMSL(const SkSL::ShaderCaps* caps,
                      const std::string& sksl,
                      SkSL::ProgramKind programKind,
                      const SkSL::ProgramSettings& settings,
                      SkSL::NativeShader* msl,
                      SkSL::ProgramInterface* outInterface,
                      ShaderErrorHandler* errorHandler)
```

**功能：** 将 SkSL（Skia Shading Language）编译为 MSL（Metal Shading Language）。

**参数：**
- `caps` - 着色器能力对象
- `sksl` - SkSL 源代码
- `programKind` - 程序类型（顶点着色器、片段着色器等）
- `settings` - 编译设置
- `msl` - 输出的 MSL 代码
- `outInterface` - 输出的程序接口信息
- `errorHandler` - 错误处理器

**实现：** 调用通用的 `SkSLToBackend` 函数，使用 `SkSL::ToMetal` 后端。

### Metal 格式查询函数

```cpp
bool MtlFormatIsCompressed(MTLPixelFormat);
uint32_t MtlFormatChannels(MTLPixelFormat);
size_t MtlFormatBytesPerBlock(MTLPixelFormat);
SkTextureCompressionType MtlFormatToCompressionType(MTLPixelFormat);
const char* MtlFormatToString(MTLPixelFormat);
```

**注释说明：** 这些函数实际上仅由 Ganesh 使用，在独立构建 Graphite 时链接器会移除它们。

## 依赖关系

### 依赖的头文件

| 头文件 | 用途 |
|--------|------|
| `<Metal/Metal.h>` | Metal 框架 API |
| `include/core/SkTextureCompressionType.h` | 压缩类型枚举 |
| `src/gpu/SkSLToBackend.h` | SkSL 后端编译接口 |
| `src/sksl/codegen/SkSLMetalCodeGenerator.h` | MSL 代码生成器 |

### 被依赖关系

- **MtlPipelineStateBuilder** - 编译着色器
- **MtlCaps** - 查询格式属性
- **MtlTexture** - 格式验证和内存计算
- **MtlGpu** - GPU 上下文初始化

## 设计模式

### 内联封装

`SkSLToMSL` 函数作为内联函数直接在头文件中实现，封装了对通用 `SkSLToBackend` 的调用，简化 Metal 特定代码的使用。

### 前向声明

使用前向声明减少头文件依赖：
```cpp
namespace SkSL {
    enum class ProgramKind : int8_t;
    struct ProgramInterface;
    // ...
}
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/mtl/MtlUtils.mm` | 实现文件 | 格式查询函数实现 |
| `src/gpu/SkSLToBackend.h` | 编译框架 | 通用 SkSL 后端编译接口 |
| `src/sksl/codegen/SkSLMetalCodeGenerator.h` | 代码生成 | MSL 代码生成后端 |
| `src/gpu/mtl/MtlGpu.h` | 使用者 | Metal GPU 上下文 |
