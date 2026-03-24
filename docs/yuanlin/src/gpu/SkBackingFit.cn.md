# SkBackingFit

> 源文件: src/gpu/SkBackingFit.h, src/gpu/SkBackingFit.cpp

## 概述

`SkBackingFit` 模块定义了 GPU 资源后备存储的尺寸匹配策略,用于控制资源分配时是精确匹配请求大小还是允许分配更大的尺寸。该模块包含一个枚举类型 `SkBackingFit` 和一个尺寸近似计算函数 `GetApproxSize`,是 Skia GPU 资源管理中的核心策略组件。

通过 `kApprox` 和 `kExact` 两种策略,系统可以在资源复用和内存精确控制之间取得平衡。`GetApproxSize` 函数将请求的尺寸映射到更大的 2 的幂次或中间值,从而提高资源缓存的命中率。

## 架构位置

`SkBackingFit` 位于 GPU 资源管理的策略层:

- 定义位置: 全局命名空间(枚举) + `skgpu` 命名空间(函数)
- 模块位置: `src/gpu/`
- 依赖层级: GPU 基础设施层
- 服务对象: 纹理代理、表面代理、资源缓存

该模块是资源分配决策的核心,影响整个 GPU 资源系统的内存使用和性能表现。

## 主要类与结构体

### 枚举类型

```cpp
enum class SkBackingFit {
    kApprox,  // 允许分配大于请求尺寸的资源
    kExact    // 必须精确匹配请求尺寸
};
```

### 关键常量

虽然没有显式定义类或结构体,但 `GetApproxSize` 实现中包含关键常量:

| 常量 | 值 | 说明 |
|------|------|------|
| `kMinApproxSize` | 16 | 近似尺寸的最小值(像素) |
| `kMagicTol` | 1024 | 魔术阈值,决定尺寸映射策略 |

## 公共 API 函数

### SkBackingFit 枚举

```cpp
// 允许分配更大的资源,以提高缓存复用
SkBackingFit::kApprox

// 必须精确匹配请求的尺寸
SkBackingFit::kExact
```

### GetApproxSize 函数

```cpp
namespace skgpu {
    // 将尺寸映射到更大的 2 的幂次或中间值
    SkISize GetApproxSize(SkISize size);
}
```

**参数**:
- `size`: 请求的尺寸(宽度和高度)

**返回值**:
- `SkISize`: 向上调整后的近似尺寸

**行为**:
- 对宽度和高度分别独立处理
- 每个维度按照特定规则向上取整

## 内部实现细节

### GetApproxSize 算法

`GetApproxSize` 的核心逻辑通过内部 lambda 函数 `adjust` 实现:

```cpp
SkISize GetApproxSize(SkISize size) {
    auto adjust = [](int value) {
        constexpr int kMinApproxSize = 16;
        constexpr int kMagicTol = 1024;

        // 1. 确保最小值
        value = std::max(kMinApproxSize, value);

        // 2. 如果已经是 2 的幂,直接返回
        if (SkIsPow2(value)) {
            return value;
        }

        // 3. 计算向上取整的 2 的幂
        int ceilPow2 = SkNextPow2(value);

        // 4. 小值策略: <= 1024,直接向上取到 2 的幂
        if (value <= kMagicTol) {
            return ceilPow2;
        }

        // 5. 大值策略: > 1024,可能取中间值
        int floorPow2 = ceilPow2 >> 1;         // 向下取整的 2 的幂
        int mid = floorPow2 + (floorPow2 >> 1); // 1.5 倍的 floorPow2

        if (value <= mid) {
            return mid;  // 返回中间值
        }
        return ceilPow2;  // 返回上界
    };

    return {adjust(size.width()), adjust(size.height())};
}
```

### 映射规则示例

| 输入范围 | 输出 | 说明 |
|---------|------|------|
| 1-16 | 16 | 最小值限制 |
| 17-32 | 32 | 小于等于 1024 时直接取 2 的幂 |
| 512 | 512 | 已是 2 的幂,不变 |
| 513-768 | 768 | 介于 512 和 1024 之间,取中间值 768 |
| 769-1024 | 1024 | 超过中间值,取上界 |
| 1025-1536 | 1536 | 介于 1024 和 2048 之间,取 1.5 * 1024 |
| 1537-2048 | 2048 | 超过中间值,取上界 |

### 设计决策说明

**为什么是 1024 作为阈值?**
- 小纹理(≤ 1024)通常是字体图集、小图标等,使用 2 的幂可以最大化复用
- 大纹理(> 1024)通常是渲染目标,允许 1.5x 的中间档可以减少浪费

**为什么允许 1.5x 中间档?**
- 纯 2 的幂策略对于大纹理会造成显著浪费(例如 1025 像素分配 2048)
- 1.5x 档位(768, 1536, 3072 等)提供了更细粒度的选择

## 依赖关系

### 依赖的模块

| 模块 | 用途 | 头文件 |
|------|------|--------|
| SkSize | 尺寸类型 | `include/core/SkSize.h` |
| SkMath | 数学工具(SkIsPow2) | `include/private/base/SkMath.h` |
| SkMathPriv | 私有数学工具(SkNextPow2) | `src/base/SkMathPriv.h` |
| std::algorithm | 标准算法(max) | `<algorithm>` |

### 被依赖的模块

| 模块 | 关系 | 说明 |
|------|------|------|
| GrSurfaceProxy | 使用方 | Ganesh 表面代理,决定资源大小 |
| GrTextureProxy | 使用方 | Ganesh 纹理代理 |
| GrRenderTargetProxy | 使用方 | Ganesh 渲染目标代理 |
| graphite::TextureProxy | 使用方 | Graphite 纹理代理 |
| GrResourceCache | 使用方 | 资源缓存,匹配资源 |

## 设计模式与设计决策

### 1. 枚举类设计

使用 `enum class` 而非 `enum`:
- 类型安全,避免隐式转换
- 明确的作用域,避免命名冲突

### 2. 分离策略和实现

- `SkBackingFit` 表达意图(策略)
- `GetApproxSize` 实现具体算法(机制)
- 调用方根据 `SkBackingFit` 决定是否调用 `GetApproxSize`

### 3. 独立处理宽度和高度

不强制正方形纹理,宽高独立计算:
- 适应非正方形纹理需求
- 最大化资源复用灵活性

### 4. 双层阈值策略

**小尺寸(≤ 1024)**: 严格 2 的幂
- 目标: 最大化缓存命中率
- 场景: 字体图集、小纹理

**大尺寸(> 1024)**: 2 的幂 + 1.5x 中间档
- 目标: 平衡复用和浪费
- 场景: 大渲染目标

### 5. 性能优先设计

- 所有计算使用整数运算
- 无分支预测失败(明确的 if-else 链)
- 内联友好的小函数

## 性能考量

### 1. 计算复杂度

- **时间复杂度**: O(1),常数时间操作
- **空间复杂度**: O(1),无额外分配

### 2. 优化技术

**位运算**:
```cpp
int floorPow2 = ceilPow2 >> 1;         // 除以 2
int mid = floorPow2 + (floorPow2 >> 1); // 1.5x = 1 + 0.5
```

**提前返回**:
```cpp
if (SkIsPow2(value)) {
    return value;  // 避免后续计算
}
```

**常量表达式**:
```cpp
constexpr int kMinApproxSize = 16;
constexpr int kMagicTol = 1024;
```

### 3. 缓存命中率影响

使用 `GetApproxSize` 可以显著提高缓存命中率:
- **未使用**: 每个尺寸都是独特的,缓存命中率低
- **使用后**: 尺寸收敛到有限的档位,命中率大幅提升

例如,500-768 像素的所有请求都映射到 768,共享同一个缓存条目。

### 4. 内存浪费权衡

| 请求尺寸 | 分配尺寸 | 浪费比例 |
|---------|---------|---------|
| 513 | 768 | 49.7% |
| 600 | 768 | 28% |
| 768 | 768 | 0% |
| 1025 | 1536 | 49.9% |
| 1200 | 1536 | 28% |

对于大尺寸,引入中间档将最大浪费从 ~100%(纯 2 的幂)降低到 ~50%。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrSurfaceProxy.h` | 使用方 | Ganesh 表面代理基类 |
| `src/gpu/ganesh/GrTextureProxy.h` | 使用方 | Ganesh 纹理代理 |
| `src/gpu/ganesh/GrRenderTargetProxy.h` | 使用方 | Ganesh 渲染目标代理 |
| `src/gpu/graphite/TextureProxy.h` | 使用方 | Graphite 纹理代理 |
| `src/gpu/ganesh/GrResourceCache.h` | 使用方 | 资源缓存实现 |
| `include/core/SkSize.h` | 依赖 | 尺寸类型定义 |
| `src/base/SkMathPriv.h` | 依赖 | 数学工具函数 |
| `tests/BackingFitTest.cpp` | 测试 | 单元测试(如果存在) |
