# GrBackendUtils

> 源文件: src/gpu/ganesh/GrBackendUtils.h, src/gpu/ganesh/GrBackendUtils.cpp

## 概述

`GrBackendUtils` 是 Ganesh GPU 后端的工具模块,提供了用于查询和转换后端格式相关信息的辅助函数。该模块封装了不同 GPU 后端(如 Vulkan、Metal、OpenGL 等)的格式查询逻辑,通过统一的接口暴露纹理压缩类型、像素/块大小以及模板位深度等底层属性。这些工具函数在纹理创建、内存计算和格式验证等场景中被广泛使用。

该模块的设计遵循简洁性原则,所有函数均为独立的实用函数,不涉及状态管理。实现依赖于 `GrBackendSurfacePriv` 来访问后端格式的内部数据结构。

## 架构位置

```
Skia Graphics Library
└── src/gpu/ganesh/              # Ganesh GPU 后端核心
    ├── GrBackendUtils.h/cpp     # [本模块] 后端格式工具函数
    ├── GrBackendSurfacePriv.h   # 后端表面内部访问接口
    ├── GrBackendSurface.h       # 后端表面公共接口
    ├── GrCaps.h                 # GPU 能力查询
    └── GrTexture.h              # 纹理资源管理
```

该模块处于 Ganesh 后端的底层工具层,为上层的纹理管理、资源分配等模块提供格式查询服务。

## 主要类与结构体

本模块为纯工具函数集合,不包含类定义。所有功能通过全局函数提供:

| 函数名称 | 功能描述 |
|---------|---------|
| `GrBackendFormatToCompressionType` | 将后端格式转换为纹理压缩类型 |
| `GrBackendFormatBytesPerBlock` | 获取每块的字节数(对于压缩格式) |
| `GrBackendFormatBytesPerPixel` | 获取每像素的字节数(对于非压缩格式) |
| `GrBackendFormatStencilBits` | 获取模板缓冲区的位深度 |

## 公共 API 函数

### 纹理压缩类型查询

```cpp
SkTextureCompressionType GrBackendFormatToCompressionType(const GrBackendFormat& format)
```

**功能**: 将 `GrBackendFormat` 转换为 `SkTextureCompressionType` 枚举值。

**参数**:
- `format`: 需要查询的后端格式对象

**返回值**:
- 有效格式返回对应的压缩类型(如 `kETC2_RGB8_UNORM`)
- 无效格式或非压缩格式返回 `SkTextureCompressionType::kNone`

**实现细节**:
- 通过 `GrBackendSurfacePriv::GetBackendData` 获取后端数据
- 调用后端数据的 `compressionType()` 虚函数
- 不同后端(Vulkan/Metal/GL)通过多态实现各自的逻辑

### 块大小查询

```cpp
size_t GrBackendFormatBytesPerBlock(const GrBackendFormat& format)
```

**功能**: 返回纹理块的字节大小。对于非压缩格式,块大小为 1x1,等同于像素大小。

**参数**:
- `format`: 需要查询的后端格式对象

**返回值**:
- 有效格式返回每块字节数(如 BC1 为 8 字节,RGBA8 为 4 字节)
- 无效格式返回 0

**应用场景**:
- 计算纹理内存占用
- 确定数据传输缓冲区大小
- 压缩纹理的块对齐计算

### 像素大小查询

```cpp
size_t GrBackendFormatBytesPerPixel(const GrBackendFormat& format)
```

**功能**: 返回每像素的字节数。仅适用于非压缩格式。

**参数**:
- `format`: 需要查询的后端格式对象

**返回值**:
- 非压缩格式返回每像素字节数
- 压缩格式返回 0

**实现逻辑**:
```cpp
if (GrBackendFormatToCompressionType(format) != SkTextureCompressionType::kNone) {
    return 0;  // 压缩格式不按像素计算
}
return GrBackendFormatBytesPerBlock(format);  // 非压缩格式块大小即像素大小
```

### 模板位深度查询

```cpp
int GrBackendFormatStencilBits(const GrBackendFormat& format)
```

**功能**: 返回格式的模板缓冲区位深度。

**参数**:
- `format`: 需要查询的后端格式对象

**返回值**:
- 深度模板格式返回模板位数(如 D24S8 返回 8)
- 纯颜色格式返回 0
- 无效格式返回 0

## 内部实现细节

### 格式数据访问机制

所有函数均通过 `GrBackendSurfacePriv` 访问内部数据:

```cpp
GrBackendSurfacePriv::GetBackendData(format)->compressionType()
```

该机制通过以下步骤实现跨后端抽象:
1. `GrBackendFormat` 内部持有 `unique_ptr<GrBackendFormatData>`
2. `GrBackendFormatData` 为纯虚基类,各后端有具体实现:
   - `GrVkFormatData` (Vulkan)
   - `GrMtlFormatData` (Metal)
   - `GrGLFormatData` (OpenGL)
3. 虚函数多态实现平台特定逻辑

### 错误处理策略

- **无效格式检查**: 所有函数首先检查 `format.isValid()`
- **断言保护**: 使用 `SkASSERT` 确保后端类型不为 `kUnsupported`
- **安全返回值**: 无效输入返回安全的默认值(0 或 kNone)

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖关系 | 用途说明 |
|---------|---------|---------|
| `GrBackendSurface.h` | 强依赖 | 定义 `GrBackendFormat` 接口 |
| `GrBackendSurfacePriv.h` | 强依赖 | 访问格式内部数据 |
| `SkTextureCompressionType` | 强依赖 | 压缩类型枚举定义 |
| `GrTypesPriv.h` | 弱依赖 | GPU 类型私有定义 |
| `DataUtils.h` | 包含引用 | 数据处理工具 |

### 被依赖的模块

| 模块名称 | 使用场景 |
|---------|---------|
| `GrAttachment.cpp` | 计算附件内存大小时查询格式信息 |
| `GrTexture.cpp` | 纹理创建时验证格式兼容性 |
| `GrGpu.cpp` | 资源分配时计算缓冲区大小 |
| `GrCaps.cpp` | 能力查询时格式特性检测 |

## 设计模式与设计决策

### 函数式设计

采用纯函数设计,所有函数无副作用:
- **优点**: 线程安全,易于测试和理解
- **决策**: 后端格式为不可变对象,查询操作不应修改状态

### 外观模式 (Facade Pattern)

将复杂的后端格式数据访问封装为简单接口:
```
客户端 → GrBackendUtils → GrBackendSurfacePriv → 后端特定实现
```

**优势**:
- 客户端代码无需了解后端类型
- 简化跨平台代码编写
- 集中格式查询逻辑便于维护

### 早期返回策略

对无效输入快速返回默认值:
```cpp
if (!format.isValid()) {
    return 0;  // 或 SkTextureCompressionType::kNone
}
```

**益处**:
- 避免空指针解引用
- 提高热路径性能
- 减少嵌套层级

## 性能考量

### 虚函数调用开销

每次查询涉及一次虚函数调用:
- **开销**: 约 1-2 纳秒(现代 CPU)
- **缓解**: 格式查询通常在纹理创建等低频路径,开销可忽略
- **优化建议**: 高频场景可缓存查询结果

### 内联优化

头文件仅声明不包含内联:
- **原因**: 函数体依赖完整类型定义,无法头文件内联
- **编译器优化**: LTO(链接时优化)可能实现跨翻译单元内联

### 分支预测友好

无效格式检查位于函数开头:
- **优势**: CPU 分支预测器能有效预测常见路径(有效格式)
- **数据**: 生产环境中 99%+ 的格式查询为有效输入

## 相关文件

| 文件路径 | 关系类型 | 说明 |
|---------|---------|------|
| `src/gpu/ganesh/GrBackendSurfacePriv.h` | 实现依赖 | 提供后端数据访问接口 |
| `include/gpu/ganesh/GrBackendSurface.h` | 接口依赖 | 定义公共后端表面类型 |
| `src/gpu/DataUtils.h` | 工具依赖 | 数据压缩块计算工具 |
| `src/gpu/ganesh/GrAttachment.cpp` | 使用者 | 附件内存计算 |
| `include/core/SkTextureCompressionType.h` | 类型定义 | 压缩类型枚举 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 类型定义 | GPU 私有类型 |
| `src/gpu/ganesh/vk/GrVkCaps.cpp` | Vulkan 实现 | Vulkan 格式能力 |
| `src/gpu/ganesh/mtl/GrMtlCaps.mm` | Metal 实现 | Metal 格式能力 |
| `src/gpu/ganesh/gl/GrGLCaps.cpp` | OpenGL 实现 | OpenGL 格式能力 |
