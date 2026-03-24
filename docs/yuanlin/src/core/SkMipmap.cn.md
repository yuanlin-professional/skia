# SkMipmap

> 源文件: src/core/SkMipmap.h, src/core/SkMipmap.cpp

## 概述

`SkMipmap` 是 Skia 中用于生成和管理多级纹理映射（Mipmap）的核心类。Mipmap 是一系列预先计算的纹理图像序列，每一级的尺寸是上一级的一半，用于在不同距离和缩放级别下提供高质量的纹理采样，减少走样（aliasing）和摩尔纹（moiré patterns）。

该类继承自 `SkCachedData`，支持可丢弃内存（discardable memory）管理，能够在内存压力下自动释放 mipmap 数据。`SkMipmap` 提供了完整的 mipmap 层级计算、存储、访问和查询功能，是 Skia 纹理系统的基础组件之一。

## 架构位置

`SkMipmap` 位于 Skia 核心渲染管道的纹理采样子系统中，处于以下架构层次：

- **上层**：被 `SkImage`、`SkBitmap`、着色器（Shader）等高级组件使用
- **同层**：与 `SkMipmapAccessor`（访问器）、`SkMipmapBuilder`（构建器）协作
- **下层**：依赖 `SkCachedData`（缓存管理）、`SkPixmap`（像素数据）、下采样算法

在渲染流程中，`SkMipmap` 为纹理采样提供不同分辨率的图像层级，支持双线性和三线性过滤等高质量采样模式。

## 主要类与结构体

### SkMipmap

| **特性** | **说明** |
|---------|---------|
| **继承关系** | 继承自 `SkCachedData`，支持缓存管理和可丢弃内存 |
| **类型** | 数据管理类，存储多级纹理层级数据 |
| **线程安全** | 不保证线程安全，需要外部同步 |

**关键成员变量：**

| **成员变量** | **类型** | **说明** |
|------------|---------|---------|
| `fCS` | `sk_sp<SkColorSpace>` | 颜色空间信息，所有层级共享 |
| `fLevels` | `Level*` | 指向层级数组的指针，由基类管理，可能为 `nullptr` |
| `fCount` | `int` | mipmap 层级数量（不包括基础级别） |

### SkMipmap::Level

8 字节对齐的结构体，表示单个 mipmap 层级：

| **成员变量** | **类型** | **说明** |
|------------|---------|---------|
| `fPixmap` | `SkPixmap` | 该层级的像素数据和元信息 |
| `fScale` | `SkSize` | 相对于基础级别的缩放比例（< 1.0） |

### SkMipmapDownSampler

抽象接口，定义下采样算法：

```cpp
struct SkMipmapDownSampler {
    virtual ~SkMipmapDownSampler() {}
    virtual void buildLevel(const SkPixmap& dst, const SkPixmap& src) = 0;
};
```

不同的实现提供不同质量的下采样算法（如高质量 HQ 下采样、基于绘制的下采样）。

## 公共 API 函数

### 构建函数

```cpp
static SkMipmap* Build(const SkPixmap& src, SkDiscardableFactoryProc,
                       bool computeContents = true);
static SkMipmap* Build(const SkBitmap& src, SkDiscardableFactoryProc);
```

- **功能**：从源图像构建完整的 mipmap 层级
- **参数**：
  - `src`：源图像数据
  - `SkDiscardableFactoryProc`：可选的可丢弃内存分配器
  - `computeContents`：是否计算像素内容，`false` 时仅分配结构
- **返回值**：成功返回 `SkMipmap*`，失败返回 `nullptr`

### 层级计算

```cpp
static int ComputeLevelCount(int baseWidth, int baseHeight);
static SkISize ComputeLevelSize(int baseWidth, int baseHeight, int level);
static float ComputeLevel(SkSize scaleSize);
```

- **`ComputeLevelCount`**：计算给定尺寸需要的 mipmap 层级数量
- **`ComputeLevelSize`**：计算指定层级的尺寸
- **`ComputeLevel`**：根据缩放比例计算浮点层级值，用于三线性过滤

### 层级访问

```cpp
int countLevels() const;
bool getLevel(int index, Level* levelPtr) const;
bool extractLevel(SkSize scale, Level* levelPtr) const;
```

- **`countLevels`**：返回 mipmap 层级总数（不包括基础级别）
- **`getLevel`**：按索引获取特定层级（索引 0 代表第一个 mipmap 层级）
- **`extractLevel`**：根据缩放比例提取最合适的层级

### 验证函数

```cpp
bool validForRootLevel(const SkImageInfo& root) const;
```

检查 mipmap 是否与给定的基础图像信息兼容（尺寸、颜色类型、alpha 类型）。

### 工厂方法

```cpp
static std::unique_ptr<SkMipmapDownSampler> MakeDownSampler(const SkPixmap&);
```

根据像素格式创建适合的下采样器实现。

## 内部实现细节

### 层级计算算法

层级数量根据最大边计算：

```cpp
int SkMipmap::ComputeLevelCount(int baseWidth, int baseHeight) {
    const int largestAxis = std::max(baseWidth, baseHeight);
    if (largestAxis < 2) return 0;

    const int leadingZeros = SkCLZ(static_cast<uint32_t>(largestAxis));
    const int significantBits = (sizeof(uint32_t) * 8) - leadingZeros;
    int mipLevelCount = significantBits;

    if (mipLevelCount > 0) {
        --mipLevelCount;  // 不包括基础级别
    }
    return mipLevelCount;
}
```

遵循 OpenGL 规范，每级尺寸为 `max(1, floor(original / 2^i))`，持续到两边都为 1。

### 内存布局

mipmap 数据采用连续内存布局：

```
[Level 0 结构][Level 1 结构]...[Level N 结构][Level 0 像素][Level 1 像素]...[Level N 像素]
```

- 结构数组在前，像素数据在后
- Level 结构 8 字节对齐，确保 F16 像素数据正确对齐
- 一次性分配所有内存，避免碎片

### 构建流程

1. **尺寸验证**：检查源图像尺寸是否大于 1x1
2. **层级计算**：计算所需层级数和总内存大小
3. **内存分配**：使用普通或可丢弃内存分配器
4. **结构初始化**：设置每个层级的 `SkPixmap` 和缩放比例
5. **像素计算**：使用下采样器逐级生成像素数据
6. **级联下采样**：每级基于上一级生成，形成链式计算

### 下采样器选择

根据编译宏和像素格式选择下采样器：

- **`SK_USE_DRAWING_MIPMAP_DOWNSAMPLER`**：使用基于 `SkDraw` 的下采样（支持高质量三次重采样）
- **默认**：使用优化的模板化下采样器（`SkMipmapHQDownSampler`），支持多种像素格式

### 层级选择算法

```cpp
float SkMipmap::ComputeLevel(SkSize scaleSize) {
    const float scale = std::min(scaleSize.width(), scaleSize.height());
    if (scale >= SK_Scalar1 || scale <= 0 || !SkIsFinite(scale)) {
        return -1;
    }
    float L = std::max(-SkScalarLog2(scale) - 0.5f, 0.f);
    return L;
}
```

- 使用最小缩放维度计算层级
- 应用 -0.5 偏移以模拟 GPU 的 sharpen mipmap 选项
- 返回浮点层级值，支持三线性插值

## 依赖关系

### 依赖的模块

| **模块** | **用途** |
|---------|---------|
| `SkCachedData` | 基类，提供缓存和可丢弃内存管理 |
| `SkPixmap` | 存储和访问各层级的像素数据 |
| `SkColorSpace` | 管理颜色空间信息 |
| `SkImageInfo` | 描述图像格式和属性 |
| 下采样算法 | `SkMipmapHQDownSampler` 或 `SkMipmapDrawDownSampler` |

### 被依赖的模块

| **模块** | **关系** |
|---------|---------|
| `SkImage` | 存储和使用 mipmap 数据 |
| `SkMipmapAccessor` | 从 mipmap 中提取合适的层级用于渲染 |
| `SkMipmapBuilder` | 手动构建 mipmap 的工具类 |
| `SkBitmapCache` | 缓存和共享 mipmap 对象 |
| 着色器系统 | 纹理采样时使用 mipmap 层级 |

## 设计模式与设计决策

### 工厂模式

通过静态 `Build()` 方法创建实例，封装复杂的构建逻辑：

- 统一的创建接口
- 内部处理内存分配、层级计算、像素生成
- 失败时返回 `nullptr`，易于错误处理

### 策略模式

通过 `SkMipmapDownSampler` 接口支持多种下采样算法：

- 可根据像素格式选择优化的实现
- 支持在编译时或运行时切换算法
- 易于添加新的下采样策略

### 缓存友好设计

- **连续内存布局**：提高缓存命中率
- **8 字节对齐**：优化 SIMD 访问和 F16 像素处理
- **可丢弃内存支持**：在内存压力下自动释放，节省资源

### 延迟计算与预计算分离

- 支持 `computeContents = false`，允许手动填充层级
- 适用于从磁盘加载预生成的 mipmap 数据
- 避免不必要的计算开销

## 性能考量

### 内存管理

- **一次性分配**：所有层级数据在一个连续块中，减少分配次数
- **可丢弃内存**：支持系统在内存紧张时回收 mipmap 数据，后续可重新生成
- **内存占用**：完整 mipmap 链额外占用约 33% 的基础图像大小（几何级数求和）

### 下采样性能

- **模板化实现**：针对不同像素格式的编译时优化
- **SIMD 加速**：使用 `skvx::Vec` 进行向量化计算
- **多种过滤器**：支持 2x2、2x3、3x2、3x3 等各向异性过滤器，适应奇数尺寸

### 层级选择优化

- **O(1) 访问**：通过索引直接访问层级数组
- **浮点层级**：支持三线性过滤，提供平滑的 LOD 过渡
- **Sharpen 偏移**：-0.5 偏移提高细节保留

### 使用建议

- **大图像优先**：大尺寸纹理更能从 mipmap 中受益
- **缓存共享**：使用 `SkMipmapCache` 避免重复计算
- **可丢弃内存**：对于临时或可重建的 mipmap，使用可丢弃内存减少峰值内存
- **格式选择**：某些格式（如 `kSRGBA_8888`）不支持自动生成，需要特殊处理

## 相关文件

| **文件路径** | **说明** |
|-------------|---------|
| `src/core/SkMipmapBuilder.h/cpp` | 手动构建 mipmap 的辅助类 |
| `src/core/SkMipmapAccessor.h/cpp` | 从 mipmap 中选择合适层级的访问器 |
| `src/core/SkMipmapHQDownSampler.cpp` | 高质量下采样算法实现 |
| `src/core/SkMipmapDrawDownSampler.cpp` | 基于绘制的下采样实现 |
| `src/core/SkCachedData.h` | 基类，提供缓存数据管理 |
| `src/core/SkBitmapCache.h` | mipmap 缓存系统 |
| `include/core/SkPixmap.h` | 像素映射接口 |
