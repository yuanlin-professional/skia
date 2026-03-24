# MtlTexture -- Metal 纹理实现

> 源文件:
> - `src/gpu/graphite/mtl/MtlTexture.h`
> - `src/gpu/graphite/mtl/MtlTexture.mm`

## 概述

MtlTexture 是 Graphite Metal 后端的纹理实现,继承自 `Texture` 基类。它封装了 `id<MTLTexture>` 对象,支持创建新纹理和包装外部提供的 Metal 纹理。该类处理多重采样、Mipmap、纹理用途验证以及 memoryless 存储模式的检测。

## 架构位置

```
Texture (抽象基类)
  -> MtlTexture  <-- 本模块
       -> id<MTLTexture> (Metal 纹理对象)
       -> MtlSharedContext (设备访问)
```

## 主要类与结构体

### MtlTexture

```cpp
class MtlTexture : public Texture {
    sk_cfp<id<MTLTexture>> fTexture;
};
```

## 公共 API 函数

### MakeMtlTexture -- 创建底层 Metal 纹理

```cpp
static sk_cfp<id<MTLTexture>> MakeMtlTexture(const MtlSharedContext*,
                                              SkISize dimensions, const TextureInfo&);
```
验证并创建 `MTLTexture`:
- 检查尺寸不超过最大纹理大小
- 验证纹理用途（ShaderRead -> isTexturable, RenderTarget -> isRenderable, ShaderWrite -> isStorage）
- 计算 Mipmap 层级数
- 配置 `MTLTextureDescriptor`（类型、格式、尺寸、采样数、存储模式等）

### Make / MakeWrapped

```cpp
static sk_sp<Texture> Make(const MtlSharedContext*, SkISize, const TextureInfo&, std::string_view label);
static sk_sp<Texture> MakeWrapped(const MtlSharedContext*, SkISize, const TextureInfo&,
                                  sk_cfp<id<MTLTexture>>, std::string_view label);
```
- `Make`: 创建 Graphite 拥有的新纹理（`Ownership::kOwned`）
- `MakeWrapped`: 包装客户端提供的纹理（`Ownership::kWrapped`）

### 访问器

```cpp
id<MTLTexture> mtlTexture() const;
const MtlTextureInfo& mtlTextureInfo() const;
```

## 内部实现细节

### Transient 纹理检测

```cpp
static bool has_transient_usage(const TextureInfo& info) {
    return mtlInfo.fStorageMode == MTLStorageModeMemoryless;
}
```
Memoryless 存储模式（macOS 11+ / iOS 10+）下纹理为 transient,仅在 tile 内存中存在,不占用系统内存。

### 多重采样配置

采样数大于 1 时纹理类型自动切换为 `MTLTextureType2DMultisample`。

### 标签同步

```cpp
void setBackendLabel(char const* label) override;
```
仅在 `SK_ENABLE_MTL_DEBUG_INFO` 编译标志下设置 Metal 纹理标签,用于 GPU 调试工具。

## 依赖关系

- `Texture` -- 基类
- `MtlSharedContext` -- 设备和能力查询
- `MtlCaps` -- 格式和能力验证
- `MtlGraphiteUtils` -- 格式转换
- `SkMipmap` -- Mipmap 层级计算

## 设计模式与设计决策

1. **工厂方法分层**: `MakeMtlTexture` 仅创建底层 Metal 对象,`Make` 和 `MakeWrapped` 在此基础上创建 Graphite 资源对象,关注点分离。
2. **所有权区分**: `Owned` vs `Wrapped` 纹理通过相同的内部构造函数区分,仅影响资源释放行为。
3. **FramebufferOnly 断言**: 明确禁止 `framebufferOnly` 纹理,因为 Graphite 需要着色器读取能力。

## 性能考量

- `freeGpuData` 仅重置引用计数指针,Metal 运行时处理实际释放。
- Memoryless 纹理检测确保 transient 标记正确,使 Graphite 资源管理可以跳过不必要的内存追踪。

## 相关文件

- `src/gpu/graphite/Texture.h` -- 纹理基类
- `src/gpu/graphite/mtl/MtlSharedContext.h` -- Metal 共享上下文
- `src/gpu/graphite/mtl/MtlCaps.h` -- Metal 能力查询
- `src/gpu/graphite/mtl/MtlResourceProvider.h` -- 纹理创建入口
