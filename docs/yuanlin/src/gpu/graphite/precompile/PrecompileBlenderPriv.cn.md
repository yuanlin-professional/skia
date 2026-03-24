# PrecompileBlenderPriv - 混合器预编译内部访问接口

> 源文件: `src/gpu/graphite/precompile/PrecompileBlenderPriv.h`

## 概述

`PrecompileBlenderPriv.h` 定义了两个核心组件：`PrecompileBlenderPriv`（混合器内部访问类）和 `PrecompileBlenderList`（混合器列表管理类）。`PrecompileBlenderPriv` 为 `PrecompileBlender` 提供内部访问窗口，暴露了 `asBlendMode()` 等内部方法。`PrecompileBlenderList` 则负责管理和优化混合器的组合列表，将 Porter-Duff 和 HSLC 混合模式合并为统一的代表模式。

## 架构位置

```
预编译混合系统
  ├── PrecompileBlender (公共基类)
  │     └── PrecompileBlenderPriv (内部访问窗口)
  ├── PrecompileBlenderList (混合器列表管理)
  │     ├── Porter-Duff 混合合并
  │     ├── HSLC 混合合并
  │     └── 固定混合效果列表
  └── PaintOptions (使用 BlenderList 管理混合选项)
```

## 主要类与结构体

### `PrecompileBlenderPriv`

标准 Priv 类，提供对 `PrecompileBlender` 内部方法的访问。同时复制了 `PrecompileBasePriv` 的方法，使其可作为基类 Priv 的替代品。

### `PrecompileBlenderList`

混合器列表管理类，对用户提供的混合器/混合模式列表进行分类和优化。

**成员变量**:

| 成员 | 类型 | 说明 |
|------|------|------|
| `fFixedBlenderEffects` | `vector<sk_sp<PrecompileBlender>>` | 固定混合效果列表 |
| `fHasPorterDuffBlender` | `bool` | 是否包含 Porter-Duff 混合 |
| `fHasHSLCBlender` | `bool` | 是否包含 HSLC 混合 |
| `fNumCombos` | `int` | 总组合数量 |

## 公共 API 函数

### PrecompileBlenderPriv 方法

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `asBlendMode()` | `optional<SkBlendMode>` | 如果可以表示为标准混合模式，返回该模式 |
| `numChildCombinations()` | `int` | 子组合数量 |
| `numCombinations()` | `int` | 总组合数量 |
| `addToKey(const KeyContext&, int)` | `void` | 添加到管线键 |

### PrecompileBlenderList 方法

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `PrecompileBlenderList(blenders)` | 构造函数 | 从 PrecompileBlender 列表构造 |
| `PrecompileBlenderList(blendModes)` | 构造函数 | 从 SkBlendMode 列表构造 |
| `numCombinations()` | `int` | 返回优化后的组合数 |
| `selectOption(int)` | `pair<sk_sp<PrecompileBlender>, int>` | 选择指定组合编号的混合器 |

## 内部实现细节

### 混合模式分类与合并

`PrecompileBlenderList` 的核心优化是将混合模式分为三类：

1. **Porter-Duff 混合**: `kClear`, `kSrc`, `kDst`, `kSrcOver`, `kDstOver`, `kSrcIn`, `kDstIn`, `kSrcOut`, `kDstOut`, `kSrcATop`, `kDstATop`, `kXor`, `kPlus`
   - 所有 Porter-Duff 模式使用同一个合并着色器函数，因此只需一个管线变体

2. **HSLC 混合**: `kHue`, `kSaturation`, `kLuminosity`, `kColor`
   - 所有 HSLC 模式使用同一个合并着色器函数

3. **固定混合效果**: 不属于上述两类的 `SkBlendMode`（如 `kMultiply`, `kScreen` 等）以及自定义运行时混合器
   - 每个效果需要独立的管线变体

### 代表混合模式

`selectOption()` 返回的混合器包装对象会从 `asBlendMode()` 返回正确的代表混合模式。代表模式与 `AddBlendMode()` 中的块选择逻辑一致：
- Porter-Duff 类返回一个代表性的 Porter-Duff 模式
- HSLC 类返回一个代表性的 HSLC 模式

### 双构造函数

两个构造函数支持不同的输入形式：
- `SkSpan<const sk_sp<PrecompileBlender>>`: 通用混合器列表（可能包含运行时混合器）
- `SkSpan<const SkBlendMode>`: 纯标准混合模式列表（更常见的使用场景）

## 依赖关系

- **include/gpu/graphite/precompile/PrecompileBlender.h**: 宿主类定义
- **\<vector\>**: `std::vector` 容器

## 设计模式与设计决策

### 混合模式合并优化

这是该文件最重要的设计决策。GPU 中 Porter-Duff 和 HSLC 混合各自使用统一的着色器函数（仅通过 Uniform 区分具体模式），因此即使用户指定了 13 种 Porter-Duff 模式，也只需要 1 个管线变体。`PrecompileBlenderList` 自动执行此合并，大幅减少管线预编译数量。

### Standin 模式

与 `PrecompileShaderPriv` 一样，`PrecompileBlenderPriv` 复制了 `PrecompileBasePriv` 的方法，使其成为基类 Priv 的完全替代品。

### 类型安全的混合模式包装

通过 `SkBlendMode` 列表构造的混合器会被重新包装为 `PrecompileBlender` 对象，确保 `asBlendMode()` 返回正确的值。这维持了整个预编译系统中混合器的统一接口。

## 性能考量

- 混合模式合并将最坏情况下的 29 种标准混合模式（SkBlendMode 枚举值）减少到最多 2+N 个管线变体（1 个 PD + 1 个 HSLC + N 个固定效果）
- `numCombinations()` 为 O(1) 查询
- `selectOption()` 为 O(N) 线性扫描，N 为固定效果数量（通常很小）
- 分类发生在构造时，后续查询不重复计算

## 相关文件

- `include/gpu/graphite/precompile/PrecompileBlender.h` - PrecompileBlender 公共 API
- `src/gpu/graphite/precompile/PrecompileBasePriv.h` - 基类 Priv
- `src/gpu/graphite/precompile/PaintOptionsPriv.h` - PaintOptions 内部（使用 BlenderList）
- `src/gpu/graphite/precompile/PrecompileShaderPriv.h` - Shader Priv（类似结构）
