# GrTextureGenerator

> 源文件: `include/private/gpu/ganesh/GrTextureGenerator.h`

## 概述
GrTextureGenerator 是一个抽象基类,继承自 SkImageGenerator,专门用于生成 GPU 纹理。它定义了将图像数据转换为 GPU 纹理的接口,支持 mipmap 生成和多种纹理生成策略,是 Skia Ganesh GPU 后端中图像数据到纹理转换的核心抽象层。

## 架构位置
该类位于 Skia 的 GPU 后端 Ganesh 子系统中,处于图像生成器层级。它是 SkImageGenerator 的专门化扩展,为 GPU 纹理生成提供了标准化接口。在 Skia 的图像处理流程中,它作为桥梁连接图像数据源和 GPU 纹理代理对象。

## 主要类与结构体

### GrTextureGenerator
这是一个抽象基类,提供了从图像数据生成 GPU 纹理的统一接口。

**继承关系**: SkImageGenerator → GrTextureGenerator

**关键成员变量**:
该类没有在头文件中声明私有成员变量,主要依赖继承自 SkImageGenerator 的基础设施。

## 公共 API 函数

### `bool isTextureGenerator() const final`
- **功能**: 标识此生成器为纹理生成器类型
- **参数**: 无
- **返回值**: 总是返回 true,用于类型识别

### `GrSurfaceProxyView generateTexture(GrRecordingContext*, const SkImageInfo&, skgpu::Mipmapped, GrImageTexGenPolicy)`
- **功能**: 核心纹理生成方法,将图像数据转换为 GPU 纹理代理视图
- **参数**:
  - `GrRecordingContext*`: GPU 录制上下文,必须非空且与生成器内部上下文兼容
  - `const SkImageInfo&`: 目标图像信息描述(尺寸、颜色类型等)
  - `skgpu::Mipmapped`: 指示是否需要生成 mipmap 级别
  - `GrImageTexGenPolicy`: 纹理生成策略,控制是否创建新纹理或复用已有纹理
- **返回值**: GrSurfaceProxyView 对象,包含纹理代理和相关视图信息;失败时返回无效对象

### `virtual GrSurfaceOrigin origin() const`
- **功能**: 返回生成纹理的表面原点方向
- **参数**: 无
- **返回值**: 默认返回 kTopLeft_GrSurfaceOrigin,子类可覆盖以返回其他方向(如 GrAHardwareBufferImageGenerator 可能返回不同原点)

## 内部实现细节

### 纯虚函数接口
`onGenerateTexture` 是必须由派生类实现的核心方法:

```cpp
virtual GrSurfaceProxyView onGenerateTexture(
    GrRecordingContext*,
    const SkImageInfo&,
    skgpu::Mipmapped,
    GrImageTexGenPolicy) = 0;
```

这个方法由 `generateTexture` 公共方法调用,子类需要实现具体的纹理生成逻辑。

### 上下文兼容性检查
生成纹理时,方法会验证传入的 GrRecordingContext 与生成器内部上下文的兼容性:
- 必须是同一个上下文实例
- 或者生成器能够将其纹理转换为传入上下文可用的格式

### Mipmap 生成策略
当请求 mipmap(参数为 kYes)时:
- 生成器应尽量创建至少分配了 mip 级别且基础层已填充数据的纹理代理
- 如果无法生成 mipmap,允许返回非 mipmap 纹理,但后续会有额外开销来分配 mip 级别和复制基础层

### 纹理生成策略(GrImageTexGenPolicy)
- **kDraw**: 允许返回生成器保留的预存纹理,可以提高性能
- **其他策略**: 必须创建新纹理并设置相应的预算状态

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| SkImageGenerator | 基类,提供图像生成的基础框架 |
| GrTypes | GPU 类型定义(GrSurfaceOrigin 等) |
| GrRecordingContext | 录制上下文,用于纹理生成 |
| GrSurfaceProxyView | 返回的纹理代理视图类型 |
| GrImageTexGenPolicy | 纹理生成策略枚举 |
| skgpu::Mipmapped | Mipmap 状态枚举 |
| SkImageInfo | 图像信息结构 |

### 被依赖的模块
- GrExternalTextureGenerator: 外部纹理生成器,派生自此类
- GrAHardwareBufferImageGenerator: Android 硬件缓冲区图像生成器
- Skia 内部各种图像生成器实现(如解码器、特效生成器等)
- SkImage 的 GPU 后端实现,用于按需生成纹理

## 设计模式与设计决策

### 模板方法模式
`generateTexture` 公共方法定义了纹理生成的框架,而 `onGenerateTexture` 纯虚函数让子类实现具体逻辑,这是典型的模板方法模式。

### 策略模式
通过 GrImageTexGenPolicy 参数实现不同的纹理生成策略,允许调用者控制是否复用纹理或创建新纹理。

### 接口隔离原则
该类专门针对纹理生成场景,不处理 CPU 像素读取等其他图像生成操作,保持接口的专一性。

### 线程安全设计
注释明确指出 `origin()` 方法的实现应该是线程安全的,这对于多线程图像处理场景至关重要。

## 性能考量

### Mipmap 预生成优化
设计允许生成器预生成和缓存 mipmap 数据,避免在首次使用时的即时生成开销。如果生成器无法提供 mipmap,系统会在后续自动处理,但会有额外的性能成本。

### 纹理复用机制
GrImageTexGenPolicy::kDraw 策略允许生成器保留和复用纹理,避免重复创建相同纹理的开销。这对于经常绘制的图像特别有效。

### 延迟纹理创建
通过生成器模式,纹理的实际创建可以延迟到真正需要时,减少不必要的 GPU 资源占用。

### 上下文转换开销
当传入的上下文与生成器内部上下文不同时,需要进行纹理转换,这可能涉及跨上下文的数据传输,有一定性能开销。设计上鼓励使用相同上下文以避免此开销。

## 相关文件
| 文件 | 关系 |
|------|------|
| include/core/SkImageGenerator.h | 父类定义 |
| include/gpu/ganesh/GrTypes.h | 类型定义依赖 |
| include/private/gpu/ganesh/GrExternalTextureGenerator.h | 外部客户端应使用的派生类 |
| src/gpu/ganesh/GrAHardwareBufferImageGenerator.h | 具体实现示例(Android 硬件缓冲区) |
| include/gpu/GrRecordingContext.h | 上下文接口 |
| include/gpu/GrSurfaceProxyView.h | 返回值类型 |
