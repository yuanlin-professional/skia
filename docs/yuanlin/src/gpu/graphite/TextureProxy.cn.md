# TextureProxy

> 源文件: src/gpu/graphite/TextureProxy.h, src/gpu/graphite/TextureProxy.cpp

## 概述

`TextureProxy` 是 Skia Graphite 渲染架构中纹理资源的延迟实例化代理对象。该类在纹理实际需要之前持有纹理的描述信息（尺寸、格式、用途等），并在适当时机通过 `ResourceProvider` 实例化为真实的 `Texture` 对象。代理模式允许 Graphite 延迟 GPU 资源分配、优化资源复用并支持跨帧的资源追踪。

## 架构位置

```
Graphite 纹理系统：
  ├── TextureProxy（纹理代理）★
  │   ├── 延迟实例化
  │   └── 资源追踪
  ├── Texture（真实纹理）
  ├── TextureInfo（格式描述）
  └── ResourceProvider（资源创建）
```

## 主要类与结构体

### TextureProxy 类

```cpp
class TextureProxy : public Resource, public SkPixelStorage {
public:
    // 创建新纹理的代理
    static sk_sp<TextureProxy> Make(Caps* caps,
                                   ResourceProvider* resourceProvider,
                                   SkISize dimensions,
                                   const TextureInfo& textureInfo,
                                   std::string_view label,
                                   Budgeted budgeted);

    // 包装已有纹理
    static sk_sp<TextureProxy> Wrap(sk_sp<Texture>);

    ~TextureProxy() override;

    // 访问器
    SkISize dimensions() const;
    const TextureInfo& textureInfo() const;
    bool isInstantiated() const;
    sk_sp<Texture> refTexture() const;
    const Texture* texture() const;

    // 实例化
    bool instantiate(ResourceProvider*);
    void deinstantiate();

protected:
    TextureProxy(SkISize dimensions,
                const TextureInfo&,
                std::string_view label,
                Budgeted);
    TextureProxy(sk_sp<Texture>);

private:
    SkISize fDimensions;
    TextureInfo fTextureInfo;
    sk_sp<Texture> fTexture;  // 实例化后的纹理
};
```

## 公共 API 函数

### Make 工厂函数

```cpp
static sk_sp<TextureProxy> Make(Caps* caps,
                               ResourceProvider* resourceProvider,
                               SkISize dimensions,
                               const TextureInfo& textureInfo,
                               std::string_view label,
                               Budgeted budgeted);
```

**功能**: 创建延迟实例化的纹理代理。

### Wrap 工厂函数

```cpp
static sk_sp<TextureProxy> Wrap(sk_sp<Texture> texture);
```

**功能**: 包装已有的纹理对象为代理（立即实例化）。

### instantiate

```cpp
bool instantiate(ResourceProvider* resourceProvider);
```

**功能**: 通过资源提供者创建真实的 GPU 纹理。

**返回值**: 成功返回 true，失败或已实例化返回 false。

### deinstantiate

```cpp
void deinstantiate();
```

**功能**: 释放底层纹理，代理回到未实例化状态。

### 访问器

```cpp
bool isInstantiated() const;  // 是否已实例化
sk_sp<Texture> refTexture() const;  // 获取纹理引用
const Texture* texture() const;  // 获取纹理指针
```

## 内部实现细节

### 延迟实例化

```cpp
bool TextureProxy::instantiate(ResourceProvider* resourceProvider) {
    if (fTexture) {
        return true;  // 已实例化
    }
    fTexture = resourceProvider->findOrCreateTexture(fDimensions, fTextureInfo, fLabel);
    return fTexture != nullptr;
}
```

### 资源追踪

继承自 `Resource`，纳入资源缓存管理。

### 包装模式

```cpp
TextureProxy::TextureProxy(sk_sp<Texture> texture)
    : Resource(texture->sharedContext(), ...)
    , SkPixelStorage(texture->dimensions())
    , fDimensions(texture->dimensions())
    , fTextureInfo(texture->textureInfo())
    , fTexture(std::move(texture)) {}
```

立即实例化，但仍作为代理使用。

## 依赖关系

### 内部依赖

| 依赖类 | 用途 |
|--------|------|
| `Resource` | 资源基类 |
| `Texture` | 真实纹理对象 |
| `TextureInfo` | 纹理格式描述 |
| `ResourceProvider` | 纹理创建 |
| `SkPixelStorage` | 像素存储基类 |

### 被依赖情况

| 依赖者 | 用途 |
|--------|------|
| `Device` | 渲染目标 |
| `Image` | 图像纹理 |
| `TextureProxyView` | 纹理视图 |

## 设计模式与设计决策

### 代理模式

延迟真实对象创建，直到实际需要时才分配 GPU 资源。

### 智能指针管理

使用 `sk_sp` 管理纹理生命周期，支持引用计数。

### 关键设计决策

1. **延迟实例化**: 减少不必要的 GPU 内存分配
2. **可去实例化**: 支持资源回收和重用
3. **立即包装**: `Wrap()` 支持外部纹理管理
4. **资源追踪**: 继承 `Resource` 纳入缓存系统

## 性能考量

### 内存优化

1. **延迟分配**: 仅在需要时创建纹理
2. **资源复用**: 通过 `ResourceProvider` 复用纹理
3. **去实例化**: 释放未使用的纹理

### 访问效率

- `isInstantiated()`: 简单指针检查，O(1)
- `texture()`: 直接访问，无虚函数开销

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `src/gpu/graphite/Texture.h` | 真实纹理类 |
| `src/gpu/graphite/TextureInfo.h` | 纹理格式描述 |
| `src/gpu/graphite/ResourceProvider.h` | 纹理创建 |
| `src/gpu/graphite/TextureProxyView.h` | 纹理视图 |
| `src/gpu/graphite/Resource.h` | 资源基类 |
