# SkColorShader

> 源文件
> - src/shaders/SkColorShader.h
> - src/shaders/SkColorShader.cpp

## 概述

`SkColorShader` 是 Skia 着色器系统中最简单的着色器实现,它表示一个单一的纯色。虽然通常可以通过直接设置画笔的颜色字段来实现相同的效果,但当需要一个实际的着色器对象时,`SkColorShader` 提供了这一功能。在绘制时,画笔的 alpha 值会被应用到指定的颜色上。

该着色器将颜色存储为 sRGB 扩展色彩空间格式,并在实际着色阶段转换到目标色彩空间。它继承自 `SkShaderBase`,是着色器系统的基础构建块之一。

## 架构位置

`SkColorShader` 位于 Skia 的着色器模块中,处于以下架构层次:

- **模块路径**: `src/shaders/`
- **基类**: `SkShaderBase` (位于 `src/shaders/SkShaderBase.h`)
- **公共接口**: 通过 `SkShaders::Color()` 工厂函数创建 (位于 `include/effects/SkShaders.h`)
- **用途**: 作为最基本的着色器类型,为绘制提供单一颜色填充功能

该类在着色器类型层次结构中是叶子节点,不被其他着色器继承,但可以作为组合着色器(如混合着色器)的输入。

## 主要类与结构体

### SkColorShader

核心着色器类,表示单一颜色的着色器。

**关键成员**:
```cpp
const SkColor4f fColor;  // 存储在扩展 sRGB 空间的颜色
```

**主要方法**:
- `explicit SkColorShader(const SkColor4f& c)`: 构造函数,接受 sRGB 颜色
- `bool isOpaque() const`: 返回颜色是否完全不透明
- `bool isConstant(SkColor4f* color) const`: 返回 true,表示该着色器产生恒定颜色
- `ShaderType type() const`: 返回 `ShaderType::kColor`
- `const SkColor4f& color() const`: 获取存储的颜色值

### 工厂函数

```cpp
namespace SkShaders {
    sk_sp<SkShader> Color(SkColor color);
    sk_sp<SkShader> Color(const SkColor4f& color, sk_sp<SkColorSpace> space);
}
```

这些工厂函数是创建 `SkColorShader` 实例的推荐方式。

## 公共 API 函数

### SkShaders::Color(SkColor color)

创建一个 sRGB 颜色着色器。

**参数**:
- `color`: 32 位打包的 ARGB 颜色值

**返回值**: 智能指针 `sk_sp<SkShader>`,指向新创建的着色器

**实现**: 内部将 `SkColor` 转换为 `SkColor4f`,然后使用 sRGB 色彩空间调用重载版本。

### SkShaders::Color(const SkColor4f& color, sk_sp<SkColorSpace> space)

创建一个指定色彩空间的颜色着色器。

**参数**:
- `color`: 浮点 RGBA 颜色值(范围 0.0-1.0)
- `space`: 颜色所在的色彩空间

**返回值**: 智能指针 `sk_sp<SkShader>`,如果颜色值无效则返回 `nullptr`

**处理流程**:
1. 验证颜色分量是否为有限值
2. 将 alpha 值钳制到 [0,1] 范围
3. 将颜色从输入色彩空间转换到 sRGB
4. 创建并返回 `SkColorShader` 实例

### isConstant()

```cpp
bool isConstant(SkColor4f* color = nullptr) const override
```

该方法始终返回 `true`,表示该着色器在所有位置产生相同的颜色。如果提供了输出参数,会将颜色值写入。这个特性允许渲染系统进行优化。

### isOpaque()

```cpp
bool isOpaque() const override
```

检查颜色的 alpha 通道是否为 1.0(完全不透明)。返回值用于确定是否需要混合操作。

## 内部实现细节

### 色彩空间管理

`SkColorShader` 采用统一的内部色彩空间策略:

1. **输入处理**: 无论输入颜色是什么色彩空间,都会在构造时转换为扩展 sRGB 格式
2. **存储格式**: `fColor` 成员始终存储未预乘的扩展 sRGB 颜色
3. **输出转换**: 在 `appendStages()` 阶段转换到目标色彩空间并预乘 alpha

这种设计简化了序列化和内部处理,因为只需要存储一个标准化的颜色值。

### Raster Pipeline 集成

```cpp
bool appendStages(const SkStageRec& rec, const SkShaders::MatrixRec&) const override
```

该方法实现了着色器到光栅管线的转换:

1. 复制内部存储的 sRGB 颜色
2. 使用 `SkColorSpaceXformSteps` 执行色彩空间转换:
   - 从 sRGB 未预乘格式
   - 转换到目标色彩空间 (`rec.fDstCS`) 的预乘格式
3. 将转换后的常量颜色追加到管线中

这个过程确保颜色在正确的色彩空间中进行混合操作。

### 序列化支持

**写入 (flatten)**:
```cpp
void flatten(SkWriteBuffer& buffer) const {
    buffer.writeColor4f(fColor);
}
```

仅存储 sRGB 颜色值,不需要额外的色彩空间信息。

**读取 (CreateProc)**:
```cpp
sk_sp<SkFlattenable> SkColorShader::CreateProc(SkReadBuffer& buffer)
```

支持两种版本格式:
- **旧版本**: 读取 8 位打包颜色
- **新版本**: 读取浮点 sRGB 颜色

还支持从更旧的 `SkColorShader4` 格式迁移,该格式存储了独立的色彩空间数据。

### 版本兼容性

代码中包含 `legacy_color4_create_proc` 函数,用于处理旧版本 SKP 文件中的 `SkColorShader4` 类型。这确保了向后兼容性,使旧的序列化数据仍然可以正确加载。

## 依赖关系

### 直接依赖

- **SkShaderBase**: 基类,提供着色器接口
- **SkColor4f**: 浮点颜色表示
- **SkColorSpace**: 色彩空间管理
- **SkColorSpaceXformSteps**: 色彩空间转换工具
- **SkRasterPipeline**: 光栅化管线系统
- **SkFlattenable**: 序列化支持

### 被依赖

- **SkBlendShader**: 可能使用 `SkColorShader` 作为输入
- **SkPaint**: 通过着色器指针使用
- **各种绘制操作**: 作为填充着色器使用

### 模块关系

```
include/core/SkShader.h (公共接口)
    ↓
src/shaders/SkShaderBase.h (内部基类)
    ↓
src/shaders/SkColorShader.h (实现)
    ↓
SkShaders::Color() (工厂函数)
```

## 设计模式与设计决策

### 工厂模式

使用 `SkShaders::Color()` 命名空间函数而不是直接构造函数,提供以下优势:
- 隐藏实现细节
- 允许在创建时执行验证和转换
- 返回基类指针,保持接口灵活性

### 不可变对象模式

`SkColorShader` 是不可变的:
- `fColor` 声明为 `const`
- 没有提供修改颜色的方法
- 线程安全,可以在多个上下文中共享

### 色彩空间标准化

设计决策是将所有输入颜色转换为 sRGB 存储:
- **优点**: 简化序列化,减少存储空间
- **优点**: 统一内部表示,简化代码逻辑
- **权衡**: 在创建时需要一次色彩空间转换

### Flattenable 框架集成

使用 Skia 的序列化框架:
- 支持版本化读取
- 向后兼容旧格式
- 与 SKP (Skia Picture) 文件格式集成

## 性能考量

### 优化特性

1. **常量颜色识别**: `isConstant()` 返回 true 允许渲染器优化:
   - 跳过逐像素着色计算
   - 使用颜色填充而不是着色器评估
   - 在 GPU 上使用常量缓冲区

2. **不透明性检测**: `isOpaque()` 允许:
   - 跳过不必要的混合操作
   - 使用更快的绘制路径
   - 在某些情况下避免创建临时表面

3. **最小内存占用**: 仅存储 16 字节 (4 个 float)

### 色彩空间转换开销

虽然在创建时和着色时都有色彩空间转换,但这些是必要的:
- 创建时转换确保内部一致性
- 着色时转换确保颜色正确性
- 对于单一颜色,这些开销相对于整体绘制成本可以忽略不计

### Pipeline 集成效率

`appendStages()` 使用 `appendConstantColor()`,这是管线中的优化操作:
- 避免逐像素函数调用
- 允许 SIMD 优化
- 在某些情况下可以完全折叠到其他阶段

## 相关文件

### 核心依赖
- `src/shaders/SkShaderBase.h` - 着色器基类定义
- `src/shaders/SkShaderBase.cpp` - 着色器基类实现
- `include/core/SkShader.h` - 公共着色器接口
- `include/effects/SkShaders.h` - 着色器工厂函数声明

### 色彩管理
- `src/core/SkColorSpaceXformSteps.h` - 色彩空间转换
- `src/core/SkColorSpacePriv.h` - 色彩空间私有工具
- `include/core/SkColorSpace.h` - 色彩空间公共接口
- `include/core/SkColor.h` - 颜色定义

### 序列化
- `src/core/SkReadBuffer.h` - 反序列化工具
- `src/core/SkWriteBuffer.h` - 序列化工具
- `include/core/SkFlattenable.h` - 可序列化对象基类
- `src/core/SkPicturePriv.h` - SKP 格式版本管理

### 渲染管线
- `src/core/SkRasterPipeline.h` - 光栅化管线
- `src/core/SkEffectPriv.h` - 效果私有工具

### 相关着色器
- `src/shaders/SkBlendShader.h` - 混合着色器(可能使用 ColorShader)
- `src/shaders/SkEmptyShader.h` - 空着色器(另一个简单着色器)
- `src/shaders/SkImageShader.h` - 图像着色器(更复杂的着色器示例)
