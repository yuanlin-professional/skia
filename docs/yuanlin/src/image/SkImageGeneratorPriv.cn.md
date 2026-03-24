# SkImageGeneratorPriv — 图像生成器私有接口

> 源文件: `src/image/SkImageGeneratorPriv.h`

## 概述

`SkImageGeneratorPriv.h` 定义了 `SkImageGenerator` 的私有工厂函数接口，位于 `SkImageGenerators` 命名空间中。`SkImageGenerator` 是 Skia 中用于延迟生成图像像素数据的抽象接口，该头文件提供了两个关键的工厂方法：

1. **`MakeFromPicture`**: 将 `SkPicture`（录制的绘制指令序列）转换为图像生成器，在需要像素时按需光栅化
2. **`MakeFromEncoded`**: 将编码的图像数据（如 PNG、JPEG 等）转换为图像生成器，在需要像素时按需解码

这些接口被声明为"私有"（Priv），意味着它们是 Skia 的内部 API，不属于稳定的公共接口。

## 架构位置

```
Skia
├── include/core/
│   ├── SkImageGenerator.h        // 公共基类声明
│   └── SkPicture.h               // Picture 录制对象
├── src/image/
│   ├── SkImageGeneratorPriv.h    // 本文件：私有工厂接口
│   ├── SkImage_Lazy.cpp          // 延迟图像（使用生成器）
│   └── SkImage_Picture.cpp       // Picture 图像生成器实现
└── src/codec/
    └── SkCodecImageGenerator.cpp // 编码数据图像生成器实现
```

`SkImageGenerator` 是 Skia 延迟加载架构的核心组件，被 `SkImage_Lazy` 用于按需生成像素。

## 主要类与结构体

本文件不定义类，仅在 `SkImageGenerators` 命名空间中声明工厂函数。

### 前向声明的类型

| 类型 | 用途 |
|------|------|
| `SkColorSpace` | 色彩空间 |
| `SkData` | 编码图像数据 |
| `SkImageGenerator` | 图像生成器基类 |
| `SkMatrix` | 变换矩阵 |
| `SkPaint` | 画笔（绘制属性） |
| `SkPicture` | 绘制指令录制 |
| `SkSurfaceProps` | 渲染表面属性 |
| `SkAlphaType` | Alpha 预乘类型 |
| `SkImages::BitDepth` | 位深度枚举 |
| `SkISize` | 整数尺寸 |

## 公共 API 函数

### `std::unique_ptr<SkImageGenerator> SkImageGenerators::MakeFromPicture(...)`（2 个重载）

- **功能**: 从 `SkPicture` 创建图像生成器
- **参数**:
  - `SkISize`: 输出图像尺寸
  - `sk_sp<SkPicture>`: 绘制指令录制
  - `const SkMatrix*`: 可选变换矩阵（传给 `drawPicture`）
  - `const SkPaint*`: 可选画笔（传给 `drawPicture`）
  - `SkImages::BitDepth`: 位深度
  - `sk_sp<SkColorSpace>`: 色彩空间
  - `SkSurfaceProps` (可选): 渲染表面属性
- **返回值**: 成功返回 `unique_ptr`，尺寸为空或 picture 为 null 时返回 `nullptr`

### `std::unique_ptr<SkImageGenerator> SkImageGenerators::MakeFromEncoded(...)`

- **功能**: 从编码的图像数据创建图像生成器
- **参数**:
  - `sk_sp<const SkData>`: 编码图像数据
  - `std::optional<SkAlphaType>`: 可选 alpha 类型覆盖（默认 `std::nullopt`，使用 premul）
- **返回值**: 成功返回 `unique_ptr`；数据无法识别或指定了 `kOpaque_SkAlphaType` 时返回 `nullptr`

## 内部实现细节

### 所有权模型

两个工厂函数都返回 `std::unique_ptr<SkImageGenerator>`，表示调用者拥有返回对象的独占所有权。这与 Skia 中 `sk_sp` 的共享所有权形成对比，反映了生成器通常与单个 `SkImage_Lazy` 一一对应的设计。

### Alpha 类型限制

`MakeFromEncoded` 支持 `kPremul_SkAlphaType` 和 `kUnpremul_SkAlphaType`，但不支持 `kOpaque_SkAlphaType`。这是因为编码数据可能包含透明度信息，强制标记为 opaque 可能导致不正确的渲染。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkRefCnt.h` | `sk_sp` 智能指针 |
| `<memory>` | `std::unique_ptr` |
| `<optional>` | `std::optional` 用于可选参数 |

## 设计模式与设计决策

1. **工厂模式**: 通过命名空间中的自由函数创建具体的 `SkImageGenerator` 子类实例
2. **私有接口分离**: 使用 `Priv` 后缀的头文件将内部工厂函数与公共 API 分离，允许在不破坏公共 ABI 的情况下修改内部接口
3. **延迟计算**: 图像生成器体现了延迟计算模式——像素数据仅在实际需要时才生成
4. **前向声明**: 大量使用前向声明而非 `#include`，最小化头文件的编译依赖
5. **可选参数**: 使用 `std::optional<SkAlphaType>` 和 `std::nullopt` 默认值，提供了比传统指针参数更清晰的可选语义

## 性能考量

- 工厂函数本身是轻量操作，仅创建生成器对象，不执行实际的光栅化或解码
- Picture 生成器在每次需要像素时都重新光栅化，适用于需要多种分辨率的场景
- 编码数据生成器支持按需解码，减少内存占用

## 相关文件

- `include/core/SkImageGenerator.h` — 公共基类
- `src/image/SkImage_Lazy.cpp` — 使用 `SkImageGenerator` 的延迟图像
- `src/image/SkImage_Picture.cpp` — Picture 生成器实现
- `src/codec/SkCodecImageGenerator.cpp` — 编码数据生成器实现
- `include/core/SkPicture.h` — Picture 录制对象
