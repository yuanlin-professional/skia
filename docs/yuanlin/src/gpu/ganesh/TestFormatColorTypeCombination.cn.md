# TestFormatColorTypeCombination

> 源文件: [src/gpu/ganesh/TestFormatColorTypeCombination.h](../../../../src/gpu/ganesh/TestFormatColorTypeCombination.h)

## 概述

`TestFormatColorTypeCombination` 是 Skia Ganesh GPU 后端中专门用于测试目的的数据结构。它将 `GrColorType`（Ganesh 内部颜色类型）和 `GrBackendFormat`（后端纹理格式）配对在一起，用于验证 GPU 后端所支持的格式与颜色类型组合的正确性。该结构体定义在 `GrTest` 命名空间中，明确表明其仅用于测试场景。

## 架构位置

该结构体位于 Ganesh 后端的测试基础设施层：

```
Ganesh 测试框架
  |
  +-- GrTest 命名空间
       |
       +-- TestFormatColorTypeCombination (格式-颜色类型组合)
       |
       v
  GrCaps / GrBackendSurface (查询和验证格式支持)
```

它通常被 GPU 能力查询（`GrCaps`）的测试代码使用，用于枚举和验证各后端（OpenGL、Vulkan、Metal、D3D）支持的格式与颜色类型的有效组合。

## 主要类与结构体

### `GrTest::TestFormatColorTypeCombination`

一个简单的 POD（Plain Old Data）结构体，包含两个成员：

| 成员 | 类型 | 说明 |
|------|------|------|
| `fColorType` | `GrColorType` | Ganesh 内部使用的颜色类型枚举，表示像素数据的颜色通道布局 |
| `fFormat` | `GrBackendFormat` | GPU 后端的纹理格式，封装了平台特定的纹理格式标识符 |

## 公共 API 函数

该结构体不包含任何成员函数。它是一个纯数据结构，所有成员均为公开字段，直接访问即可。

## 内部实现细节

1. **命名空间隔离**：该结构体被定义在 `GrTest` 命名空间中，这是 Skia 测试代码的惯例命名空间，与生产代码隔离。这样的命名空间约定确保测试辅助类型不会被生产代码路径意外引用。

2. **`GrColorType` 与 `SkColorType` 的区别**：`GrColorType` 是 Ganesh 内部的颜色类型枚举，比 `SkColorType`（公共 API 颜色类型）更细粒度，能够表示 GPU 后端特有的格式（如 `kAlpha_F16`、`kRG_88`、`kRGBA_F16Clamped` 等）。`SkColorType` 是面向用户的简化类型集，而 `GrColorType` 需要覆盖所有 GPU 后端支持的原生像素格式。

3. **`GrBackendFormat` 的多态性**：`GrBackendFormat` 是一个多态包装类，内部使用小对象存储（inline storage）存储了平台特定的格式标识符。不同后端的格式标识包括：
   - OpenGL：`GLenum`（如 `GL_RGBA8`、`GL_R16F`）
   - Vulkan：`VkFormat`（如 `VK_FORMAT_R8G8B8A8_UNORM`）
   - Metal：`MTLPixelFormat`（如 `MTLPixelFormatRGBA8Unorm`）
   - Direct3D：`DXGI_FORMAT`（如 `DXGI_FORMAT_R8G8B8A8_UNORM`）

4. **测试中的典型使用模式**：测试代码通常会从 `GrCaps`（GPU 能力查询类）获取所有支持的格式-颜色类型组合列表，然后遍历该列表进行各种操作的正确性验证，例如纹理创建、渲染目标绑定、数据传输等。

## 依赖关系

- **`include/gpu/ganesh/GrBackendSurface.h`**：提供 `GrBackendFormat` 类
- **`include/private/gpu/ganesh/GrTypesPriv.h`**：提供 `GrColorType` 枚举

## 设计模式与设计决策

1. **测试专用命名空间**：使用 `GrTest` 命名空间将测试辅助类型与生产代码清晰分离，防止测试代码意外泄漏到生产路径中。

2. **值类型设计**：该结构体为值类型，没有指针成员（`GrBackendFormat` 内部管理自身数据），可以安全地复制和存储在容器中。

3. **最小化设计**：仅包含测试所需的最少字段，没有多余的方法或逻辑，符合测试辅助结构体的简洁原则。

## 性能考量

由于该结构体仅用于测试代码，性能不是主要考量。`GrBackendFormat` 使用了小对象优化（inline storage），因此该结构体的复制操作通常不涉及堆分配。

## 相关文件

- `include/gpu/ganesh/GrBackendSurface.h`：`GrBackendFormat` 类定义，封装平台特定纹理格式
- `include/private/gpu/ganesh/GrTypesPriv.h`：`GrColorType` 枚举定义，Ganesh 内部颜色类型
- `src/gpu/ganesh/GrCaps.h`：GPU 能力查询接口，提供 `getTestingCombinations()` 等方法返回该结构体数组
- `src/gpu/ganesh/gl/GrGLCaps.h`：OpenGL 后端能力类，定义 GL 特定的格式组合
- `src/gpu/ganesh/vk/GrVkCaps.h`：Vulkan 后端能力类，定义 Vulkan 特定的格式组合
- `src/gpu/ganesh/mtl/GrMtlCaps.h`：Metal 后端能力类，定义 Metal 特定的格式组合
- `tests/`：Skia 测试目录，包含使用此结构体的格式验证测试用例
