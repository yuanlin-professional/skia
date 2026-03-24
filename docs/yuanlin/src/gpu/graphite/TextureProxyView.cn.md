# TextureProxyView

> 源文件: src/gpu/graphite/TextureProxyView.h

## 概述

`TextureProxyView` 是 Skia Graphite 架构中表示纹理代理视图的轻量级类。该类组合了 `TextureProxy`（纹理代理）和 `Swizzle`（通道重排），为纹理采样和渲染提供统一的视图抽象。视图允许在不创建新纹理的情况下重新解释纹理的通道顺序，支持灵活的颜色格式处理。

## 架构位置

```
Graphite 纹理视图系统：
  ├── TextureProxy（纹理代理）
  ├── Swizzle（通道重排）
  └── TextureProxyView（纹理视图）★
      ├── 用于图像采样
      └── 用于渲染目标
```

## 主要类与结构体

### TextureProxyView 类

```cpp
class TextureProxyView {
public:
    TextureProxyView();
    TextureProxyView(sk_sp<TextureProxy> proxy, Swizzle swizzle = Swizzle::RGBA());

    const sk_sp<TextureProxy>& proxy() const;
    const Swizzle& swizzle() const;

    operator bool() const;  // 检查是否有效

    TextureProxyView makeSwizzle(Swizzle newSwizzle) const;

private:
    sk_sp<TextureProxy> fProxy;
    Swizzle fSwizzle;
};
```

## 公共 API 函数

### 构造函数

```cpp
TextureProxyView(sk_sp<TextureProxy> proxy, Swizzle swizzle = Swizzle::RGBA());
```

创建纹理代理视图，默认使用 RGBA 通道顺序。

### 访问器

```cpp
const sk_sp<TextureProxy>& proxy() const;  // 获取纹理代理
const Swizzle& swizzle() const;  // 获取通道重排
```

### makeSwizzle

```cpp
TextureProxyView makeSwizzle(Swizzle newSwizzle) const;
```

创建具有不同 swizzle 的新视图，共享相同的纹理代理。

### operator bool

```cpp
operator bool() const { return fProxy != nullptr; }
```

检查视图是否有效（代理非空）。

## 内部实现细节

### 轻量级设计

```cpp
class TextureProxyView {
    sk_sp<TextureProxy> fProxy;  // 智能指针（8字节）
    Swizzle fSwizzle;            // 4字节整数
};  // 总共约12字节
```

### Swizzle 应用

在着色器中应用 swizzle：
```glsl
// swizzle = "bgra"
vec4 color = texture(sampler, uv).bgra;
```

### 视图共享

多个视图可共享同一纹理代理，仅 swizzle 不同：
```cpp
TextureProxyView rgbaView(proxy, Swizzle::RGBA());
TextureProxyView bgraView(proxy, Swizzle::BGRA());
```

## 依赖关系

### 内部依赖

| 依赖类 | 用途 |
|--------|------|
| `TextureProxy` | 纹理代理 |
| `Swizzle` | 通道重排 |

### 被依赖情况

| 依赖者 | 用途 |
|--------|------|
| `Device` | 渲染目标视图 |
| `Image` | 图像纹理视图 |
| `ShaderInfo` | 纹理采样配置 |

## 设计模式与设计决策

### 值语义

轻量级类，支持值拷贝，无虚函数。

### 视图模式

提供不同的数据解释方式，不修改底层纹理。

### 不可变性

一旦创建，视图的 swizzle 不可更改（通过 `makeSwizzle()` 创建新视图）。

### 关键设计决策

1. **轻量级**: 仅12字节，可按值传递
2. **视图共享**: 多个视图共享纹理，节省内存
3. **零开销抽象**: GPU 自动处理 swizzle，无运行时开销
4. **默认 RGBA**: 最常见的通道顺序为默认值

## 性能考量

### 内存开销

- 视图本身仅12字节
- 共享纹理代理，无额外纹理分配

### GPU 开销

- Swizzle 由硬件处理，零运行时开销
- 视图创建无 GPU 命令

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `src/gpu/graphite/TextureProxy.h` | 纹理代理 |
| `src/gpu/Swizzle.h` | 通道重排定义 |
| `src/gpu/graphite/Device.h` | 渲染设备 |
| `src/gpu/graphite/Image_Graphite.h` | Graphite 图像 |
