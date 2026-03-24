# MtlSampler -- Metal 采样器

> 源文件:
> - `src/gpu/graphite/mtl/MtlSampler.h`
> - `src/gpu/graphite/mtl/MtlSampler.mm`

## 概述

MtlSampler 是 Graphite Metal 后端的采样器实现,继承自 `Sampler` 基类。它将 Skia 的采样选项（过滤模式、Mipmap 模式、平铺模式）转换为 Metal 的 `MTLSamplerState` 对象。

## 架构位置

```
Sampler (抽象基类)
  -> MtlSampler  <-- 本模块
       -> id<MTLSamplerState> (Metal 采样器状态)
```

## 主要类与结构体

### MtlSampler

```cpp
class MtlSampler : public Sampler {
    sk_cfp<id<MTLSamplerState>> fSamplerState;
};
```

## 公共 API 函数

### Make
```cpp
static sk_sp<MtlSampler> Make(const MtlSharedContext*, const SkSamplingOptions&,
                              SkTileMode xTileMode, SkTileMode yTileMode);
```

### 访问器
```cpp
id<MTLSamplerState> mtlSamplerState() const;
```

## 内部实现细节

### 平铺模式映射

| SkTileMode | MTLSamplerAddressMode |
|------------|----------------------|
| kClamp | ClampToEdge |
| kRepeat | Repeat |
| kMirror | MirrorRepeat |
| kDecal | ClampToBorderColor (macOS 10.12+ / iOS 14+) |

Decal 模式需要 `clampToBorderSupport` 能力,否则触发 assert。

### 采样器创建

配置 `MTLSamplerDescriptor`:
- `magFilter` / `minFilter`: Nearest 或 Linear
- `mipFilter`: NotMipmapped / Nearest / Linear
- `lodMinClamp=0`, `lodMaxClamp=FLT_MAX`
- `maxAnisotropy=1`（各向异性暂不使用）
- `compareFunction=Never`
- r 轴地址模式固定为 ClampToEdge

### 调试标签

仅在 `SK_ENABLE_MTL_DEBUG_INFO` 下生成描述性标签,格式如 `"XClampYRepeatLinearMipNearest"`。

## 依赖关系

- `Sampler` -- 基类
- `MtlSharedContext` -- 设备和能力
- `MtlCaps` -- 能力查询（clampToBorderSupport）

## 设计模式与设计决策

1. **不可变对象**: 创建后采样器状态不可变,符合 Metal 的设计理念。
2. **Decal 回退**: 不支持 ClampToBorderColor 时,着色器层面已处理回退逻辑。

## 性能考量

- `MTLSamplerState` 创建是轻量操作,但 Graphite 仍通过全局缓存避免重复创建。
- 调试标签仅在 debug 构建中生成。

## 相关文件

- `src/gpu/graphite/Sampler.h` -- 采样器基类
- `src/gpu/graphite/mtl/MtlSharedContext.h` -- Metal 共享上下文
- `src/gpu/graphite/SamplerDesc.h` -- 采样器描述
