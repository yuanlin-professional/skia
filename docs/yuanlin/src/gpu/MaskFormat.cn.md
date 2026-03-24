# MaskFormat

> 源文件: src/gpu/MaskFormat.h

## 概述

`MaskFormat` 模块定义了 GPU 字体缓存使用的蒙版格式枚举和相关工具函数。该模块提供了三种蒙版格式:`kA8`(单通道灰度)、`kA565`(LCD 子像素渲染)和 `kARGB`(彩色表情符号),用于在 GPU 上高效渲染文本和字形。

该模块是 Skia GPU 文本渲染系统的基础组件,定义了字形图集(glyph atlas)的像素格式,影响内存使用、渲染质量和性能。通过编译期常量函数,提供了高效的格式属性查询能力。

## 架构位置

`MaskFormat` 位于 GPU 层的文本渲染基础设施:

- 命名空间: `skgpu`
- 模块位置: `src/gpu/`
- 类型: 枚举定义和工具函数
- 依赖层级: GPU 基础类型层
- 服务对象: 字形缓存、文本绘制、字体图集管理

该模块是文本渲染管线的底层抽象,被 Ganesh 和 Graphite 两个渲染引擎的文本系统使用。

## 主要类与结构体

本模块不包含类或结构体,仅定义枚举和工具函数。

### MaskFormat 枚举

```cpp
enum class MaskFormat : int {
    kA8,    // 1 字节/像素,灰度蒙版
    kA565,  // 2 字节/像素,RGB 子像素 LCD 覆盖率
    kARGB,  // 4 字节/像素,彩色格式

    kLast = kARGB
};
```

### 常量定义

| 常量 | 值 | 说明 |
|------|------|------|
| `kMaskFormatCount` | 3 | 蒙版格式的总数 |
| `kLast` | `kARGB` | 最后一个枚举值 |

## 公共 API 函数

### MaskFormat 枚举值

```cpp
// 单通道灰度蒙版
skgpu::MaskFormat::kA8

// LCD 子像素渲染(3 通道)
skgpu::MaskFormat::kA565

// 彩色蒙版(表情符号)
skgpu::MaskFormat::kARGB
```

### MaskFormatBytesPerPixel 函数

```cpp
constexpr int MaskFormatBytesPerPixel(MaskFormat format);
```

**功能**: 返回指定蒙版格式的每像素字节数
**参数**: `format` - 蒙版格式枚举值
**返回值**: 每像素字节数(1、2 或 4)

**行为**:
```cpp
constexpr int MaskFormatBytesPerPixel(MaskFormat format) {
    switch (format) {
        case MaskFormat::kA8:   return 1;
        case MaskFormat::kA565: return 2;
        case MaskFormat::kARGB: return 4;
    }
    SkUNREACHABLE;
}
```

### MaskFormatToColorType 函数

```cpp
static constexpr SkColorType MaskFormatToColorType(MaskFormat format);
```

**功能**: 将蒙版格式转换为 Skia 颜色类型
**参数**: `format` - 蒙版格式枚举值
**返回值**: 对应的 `SkColorType`

**映射关系**:
```cpp
static constexpr SkColorType MaskFormatToColorType(MaskFormat format) {
    switch (format) {
        case MaskFormat::kA8:   return kAlpha_8_SkColorType;
        case MaskFormat::kA565: return kRGB_565_SkColorType;
        case MaskFormat::kARGB: return kRGBA_8888_SkColorType;
    }
    SkUNREACHABLE;
}
```

## 内部实现细节

### 枚举值到属性的映射

#### kA8 格式

- **字节数**: 1
- **颜色类型**: `kAlpha_8_SkColorType`
- **用途**: 标准灰度文本渲染
- **适用场景**: 大部分文本,单色图标

#### kA565 格式

- **字节数**: 2
- **颜色类型**: `kRGB_565_SkColorType`
- **用途**: LCD 子像素渲染
- **适用场景**: 高清晰度文本,利用 RGB 子像素排列

#### kARGB 格式

- **字节数**: 4
- **颜色类型**: `kRGBA_8888_SkColorType`
- **用途**: 彩色表情符号和图标
- **适用场景**: 需要全彩色的字形

### constexpr 优化

两个工具函数都使用 `constexpr`,允许编译期计算:

```cpp
constexpr int size = MaskFormatBytesPerPixel(MaskFormat::kA8);  // 编译期常量 1
```

**优点**:
- 零运行时开销
- 可用于模板参数和数组大小
- 编译器可以内联和优化

### 枚举基础类型

```cpp
enum class MaskFormat : int
```

显式指定基础类型为 `int`:
- 确保枚举大小一致(4 字节)
- 便于与整数互操作
- 明确的类型转换语义

## 依赖关系

### 依赖的模块

| 模块 | 用途 | 头文件 |
|------|------|--------|
| SkColorType | 颜色类型定义 | `include/core/SkColorType.h` |

### 被依赖的模块

| 模块 | 关系 | 说明 |
|------|------|------|
| GrDrawOpAtlas | 使用方 | Ganesh 字形图集 |
| sktext::gpu::StrikeCache | 使用方 | GPU 字形缓存 |
| sktext::gpu::TextBlob | 使用方 | 文本 Blob 渲染 |
| graphite::AtlasManager | 使用方 | Graphite 图集管理 |
| GrMaskFormat (旧版) | 迁移 | 旧的 Ganesh 特定类型 |

## 设计模式与设计决策

### 1. enum class 设计

使用 `enum class` 而非普通 `enum`:
- **类型安全**: 不能隐式转换为整数
- **作用域隔离**: 避免命名冲突
- **强类型**: 编译器检查更严格

### 2. 基于 0 的枚举值

注释强调 "Important that these are 0-based":
```cpp
kA8,    // 隐式为 0
kA565,  // 隐式为 1
kARGB,  // 隐式为 2
```

**原因**:
- 可以直接用作数组索引
- 简化循环和映射表
- 与 `kMaskFormatCount` 配合使用

### 3. constexpr 函数

使用 `constexpr` 而非查找表:
```cpp
// 不使用
static const int bytes[] = {1, 2, 4};

// 使用
constexpr int MaskFormatBytesPerPixel(MaskFormat format) { ... }
```

**优点**:
- 更好的类型安全
- 编译期检查
- 无全局数据段占用

### 4. 不可达标记

使用 `SkUNREACHABLE` 标记 switch 后的代码:
```cpp
switch (format) {
    case MaskFormat::kA8:   return 1;
    case MaskFormat::kA565: return 2;
    case MaskFormat::kARGB: return 4;
}
SkUNREACHABLE;  // 帮助编译器优化,捕获错误
```

**作用**:
- 告知编译器所有分支已覆盖
- Debug 模式下可能触发断言
- 优化器可以假定此处不可达

### 5. 分离关注点

模块仅定义格式,不包含:
- 图集管理逻辑
- 字形光栅化
- GPU 上传

这些职责由上层模块实现,保持模块职责单一。

## 性能考量

### 1. 内存使用

不同格式的内存占用差异显著:

| 格式 | 字节/像素 | 1024x1024 图集大小 |
|------|----------|-------------------|
| kA8 | 1 | 1 MB |
| kA565 | 2 | 2 MB |
| kARGB | 4 | 4 MB |

**权衡**:
- kA8: 最节省内存,但不支持彩色和子像素
- kA565: 适中,支持 LCD 渲染
- kARGB: 内存较大,但支持全彩色

### 2. GPU 带宽

纹理采样带宽与字节数成正比:
- kA8: 最低带宽
- kA565: 中等带宽
- kARGB: 最高带宽

### 3. 渲染质量

| 格式 | 适用场景 | 质量 |
|------|---------|------|
| kA8 | 普通文本,单色 | 良好 |
| kA565 | LCD 屏幕,高 DPI | 优秀(子像素抗锯齿) |
| kARGB | 表情符号,彩色图标 | 最佳(全彩色) |

### 4. 缓存效率

格式选择影响字形缓存的命中率和容量:
- **kA8**: 可以缓存更多字形
- **kARGB**: 缓存容量减少,但支持更多类型

### 5. 编译期优化

使用 `constexpr` 函数的性能优势:

```cpp
// 编译期计算
constexpr int stride = 1024 * MaskFormatBytesPerPixel(MaskFormat::kA8);
// 编译器生成: constexpr int stride = 1024;

// 运行时无函数调用开销
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkColorType.h` | 依赖 | 颜色类型定义 |
| `src/gpu/ganesh/GrDrawOpAtlas.h` | 使用方 | Ganesh 字形图集 |
| `src/text/gpu/StrikeCache.h` | 使用方 | GPU 字形缓存 |
| `src/text/gpu/TextBlob.h` | 使用方 | 文本 Blob 渲染 |
| `src/gpu/graphite/text/AtlasManager.h` | 使用方 | Graphite 图集管理 |
| `src/gpu/ganesh/GrMaskFormat.h` | 历史 | 旧的 Ganesh 特定定义(已废弃) |

## 使用场景示例

### 场景 1: 分配图集

```cpp
MaskFormat format = MaskFormat::kA8;
int bytesPerPixel = MaskFormatBytesPerPixel(format);
int atlasSize = width * height * bytesPerPixel;
```

### 场景 2: 创建纹理

```cpp
SkColorType colorType = MaskFormatToColorType(maskFormat);
auto texture = context->createTexture(
    dimensions, colorType, /* other params */
);
```

### 场景 3: 遍历所有格式

```cpp
for (int i = 0; i < kMaskFormatCount; ++i) {
    MaskFormat format = static_cast<MaskFormat>(i);
    InitializeAtlas(format);
}
```

### 场景 4: 格式选择

```cpp
MaskFormat ChooseFormat(const SkPaint& paint) {
    if (paint.isColorEmoji()) {
        return MaskFormat::kARGB;
    } else if (paint.isLCDRenderText()) {
        return MaskFormat::kA565;
    } else {
        return MaskFormat::kA8;
    }
}
```

## 设计演进

### 历史背景

早期 Skia 有 `GrMaskFormat`,仅用于 Ganesh:
```cpp
// 旧代码
enum GrMaskFormat {
    kA8_GrMaskFormat,
    kA565_GrMaskFormat,
    kARGB_GrMaskFormat
};
```

### 迁移到 skgpu 命名空间

随着 Graphite 的引入,需要共享的类型:
```cpp
// 新代码
namespace skgpu {
    enum class MaskFormat { ... };
}
```

**改进**:
- 统一 Ganesh 和 Graphite 的类型
- 更好的命名空间组织
- 使用 `enum class` 提高类型安全

### 未来扩展

可能的新格式:
- **kA16**: 16 位灰度(HDR 文本)
- **kDistanceField**: 距离场字形(可伸缩)
- **kSDF**: 有符号距离场
