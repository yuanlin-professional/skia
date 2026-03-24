# SkImage_LazyTexture - 延迟纹理图像

> 源文件: `src/gpu/ganesh/image/SkImage_LazyTexture.h`, `src/gpu/ganesh/image/SkImage_LazyTexture.cpp`

## 概述

`SkImage_LazyTexture` 是一个 GPU 后端支持的延迟图像实现，继承自 `SkImage_Lazy`。它将后备纹理的创建推迟到实际需要绘制或读取像素时才执行。通过 `GrTextureGenerator` 工厂对象，它能够按需创建 GPU 纹理。此类是 Android `AHardwareBuffer` 等平台特定对象创建的 `SkImage` 的具体实现。

## 架构位置

```
SkImage (公共 API)
    |
SkImage_Base -> SkImage_Lazy
    |
SkImage_LazyTexture (本文件)
    |
GrTextureGenerator (纹理生成器)
    |
GrAHardwareBufferImageGenerator 等
```

## 主要类与结构体

### `SkImage_LazyTexture`

继承自 `SkImage_Lazy`，标记为 `final`。

无额外成员变量，状态完全由基类管理。

## 公共 API 函数

### 构造函数

```cpp
explicit SkImage_LazyTexture(SkImage_Lazy::Validator* validator);
```

通过验证器初始化，验证器包含 `GrTextureGenerator` 和图像元信息。

### `readPixelsProxy()`

```cpp
bool readPixelsProxy(GrDirectContext*, const SkPixmap&) const override;
```

通过生成器创建纹理后读取像素到 CPU 内存。

### `onMakeSubset()`

```cpp
sk_sp<SkImage> onMakeSubset(SkRecorder*, const SkIRect&, RequiredProperties) const override;
```

创建子区域图像。

### `type()`

返回 `SkImage_Base::Type::kLazyTexture`。

## 内部实现细节

纹理的实际创建延迟到 `asView` 或 `readPixelsProxy` 被调用时。生成器（如 `GrAHardwareBufferImageGenerator`）负责将外部资源导入图形 API。

## 依赖关系

- **上游依赖**: `SkImage_Lazy`（延迟图像基类）、`GrDirectContext`。
- **被依赖**: `GrAHardwareBufferImageGenerator`、跨上下文纹理导入。

## 设计模式与设计决策

1. **延迟实例化**: 与 Ganesh 的懒代理（lazy proxy）机制配合，在渲染时才触发纹理创建。
2. **生成器解耦**: 纹理创建逻辑封装在 `GrTextureGenerator` 中，`SkImage_LazyTexture` 不关心具体的纹理来源。
3. **最小化类**: 仅覆盖必要的虚方法，大部分逻辑继承自 `SkImage_Lazy`。

## 性能考量

- 延迟创建避免了不必要的 GPU 资源分配。
- 首次使用时的纹理创建开销是一次性的，后续使用复用已创建的纹理。

## 相关文件

- `src/image/SkImage_Lazy.h` - 延迟图像基类
- `include/private/gpu/ganesh/GrTextureGenerator.h` - 纹理生成器接口
- `src/gpu/ganesh/GrAHardwareBufferImageGenerator.h` - AHB 生成器
