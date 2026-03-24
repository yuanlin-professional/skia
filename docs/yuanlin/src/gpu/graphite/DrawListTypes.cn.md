# DrawListTypes

> 源文件
> - src/gpu/graphite/DrawListTypes.h

## 概述

`DrawListTypes.h` 定义了 `DrawListLayer` 分层实现所需的所有数据结构，包括层（Layer）、绑定包装器（BindingWrapper）、绘制列表（DrawList）和相关的辅助类型。这些类型共同实现了智能的绘制命令组织和批处理策略。

## 主要类型

### BoundsTest 枚举

```cpp
enum class BoundsTest {
    kDisjoint,              // 边界不相交
    kCompatibleOverlap,     // 边界相交且绑定兼容
    kIncompatibleOverlap    // 边界相交但绑定不兼容
};
```

### LayerKey 结构

```cpp
struct LayerKey {
    GraphicsPipelineCache::Index fPipelineIndex;
    TextureDataCache::Index fTextureIndex;

    bool operator==(const LayerKey& other) const;
};
```

标识绘制所需的管线和纹理绑定。

### SingleDraw 结构

```cpp
struct SingleDraw {
    const DrawParams* fDrawParams;
    const UniformDataCache::Index fUniformIndex;
    SK_DECLARE_INTERNAL_LLIST_INTERFACE(SingleDraw);
};
```

单个绘制的数据。

### Layer 结构

```cpp
struct Layer {
    const CompressedPaintersOrder fOrder;
    SkTInternalLList<BindingWrapper> fBindings;

    BindingWrapper* searchBinding(const LayerKey& key, BindingWrapper* startList);

    template <bool kIsStencil, bool kIsDepthOnly, bool kForwards>
    std::pair<BoundsTest, BindingWrapper*> test(...);

    SK_DECLARE_INTERNAL_LLIST_INTERFACE(Layer);
};
```

包含具有相同压缩画家顺序的绘制命令。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/graphite/DrawListLayer.h` | 使用这些类型的实现 |
| `src/gpu/graphite/DrawOrder.h` | 绘制顺序定义 |
| `src/gpu/graphite/DrawParams.h` | 绘制参数 |
