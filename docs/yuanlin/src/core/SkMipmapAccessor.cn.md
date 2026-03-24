# SkMipmapAccessor

> 源文件: src/core/SkMipmapAccessor.h, src/core/SkMipmapAccessor.cpp

## 概述

`SkMipmapAccessor` 是 Skia 中用于从图像的 mipmap 层级中选择和访问合适层级的辅助类。它根据给定的变换矩阵和 mipmap 模式，自动计算并提供最优的 mipmap 层级以及相应的变换矩阵，支持最近邻（nearest）和线性（linear）两种 mipmap 采样模式。

该类封装了 mipmap 层级选择的复杂逻辑，包括层级缓存加载、矩阵分解、浮点层级计算和双层级插值支持。它是着色器和图像渲染系统在进行纹理采样时的关键组件，确保在不同缩放级别下提供最佳的采样质量。

## 架构位置

`SkMipmapAccessor` 位于 Skia 渲染管道的纹理采样层，处于以下位置：

- **上层**：被着色器（如 `SkImageShader`）和图像绘制代码使用
- **同层**：与 `SkMipmap`（mipmap 存储）、`SkBitmapCache`（缓存管理）协作
- **下层**：依赖 `SkImage_Base`（图像基类）、`SkMatrix`（变换矩阵）

在纹理采样流程中，`SkMipmapAccessor` 负责"选择合适的层级"这一关键步骤，将复杂的层级计算和缓存管理逻辑封装起来，为上层提供简洁的访问接口。

## 主要类与结构体

### SkMipmapAccessor

| **特性** | **说明** |
|---------|---------|
| **继承关系** | 继承自 `SkNoncopyable`，禁止拷贝 |
| **类型** | 访问器辅助类 |
| **生命周期** | 通常通过 `SkArenaAlloc` 分配，与渲染上下文绑定 |

**关键成员变量：**

| **成员变量** | **类型** | **说明** |
|------------|---------|---------|
| `fUpper` | `SkPixmap` | 上层 mipmap 层级的像素数据（主层级） |
| `fLower` | `SkPixmap` | 下层 mipmap 层级的像素数据（仅用于线性模式） |
| `fLowerWeight` | `float` | 下层权重，范围 [0, 1]，用于三线性插值 |
| `fUpperInv` | `SkMatrix` | 上层的逆变换矩阵，映射到该层级坐标空间 |
| `fLowerInv` | `SkMatrix` | 下层的逆变换矩阵（仅用于线性模式） |
| `fBaseStorage` | `SkBitmap` | 存储基础图像数据的生命周期管理器 |
| `fCurrMip` | `sk_sp<const SkMipmap>` | 持有当前使用的 mipmap 对象引用 |

## 公共 API 函数

### 工厂方法

```cpp
static SkMipmapAccessor* Make(SkArenaAlloc* alloc,
                              const SkImage* image,
                              const SkMatrix& inv,
                              SkMipmapMode mode);
```

- **功能**：创建 mipmap 访问器实例
- **参数**：
  - `alloc`：内存分配器，用于对象生命周期管理
  - `image`：源图像对象
  - `inv`：逆变换矩阵（从设备空间到图像空间）
  - `mode`：mipmap 模式（`kNone`/`kNearest`/`kLinear`）
- **返回值**：成功返回访问器指针，失败返回 `nullptr`

### 层级访问

```cpp
std::pair<SkPixmap, SkMatrix> level() const;
std::pair<SkPixmap, SkMatrix> lowerLevel() const;
float lowerWeight() const;
```

- **`level()`**：返回上层（主层级）的像素数据和对应的变换矩阵
- **`lowerLevel()`**：返回下层的像素数据和变换矩阵（仅用于线性模式）
- **`lowerWeight()`**：返回下层的插值权重，`0` 表示无下层或完全使用上层

### 构造函数（公开但不应直接调用）

```cpp
SkMipmapAccessor(const SkImage_Base* image,
                 const SkMatrix& inv,
                 SkMipmapMode requestedMode);
```

构造函数公开仅供 `SkArenaAlloc::make()` 使用，外部应通过 `Make()` 创建实例。

## 内部实现细节

### 层级选择流程

构造函数执行复杂的层级选择逻辑：

1. **矩阵分解**：
   ```cpp
   SkSize scale;
   if (!inv.decomposeScale(&scale, nullptr)) {
       resolvedMode = SkMipmapMode::kNone;  // 无法分解则回退到基础图像
   }
   ```
   从逆矩阵中提取缩放因子，判断是否需要 mipmap。

2. **层级计算**：
   ```cpp
   level = SkMipmap::ComputeLevel({1/scale.width(), 1/scale.height()});
   if (level <= 0) {
       resolvedMode = SkMipmapMode::kNone;  // 缩放不需要 mipmap
   }
   ```
   计算浮点层级值，`level <= 0` 表示放大或无缩放。

3. **模式调整**：
   - **最近邻模式**：将浮点层级四舍五入为整数
   - **线性模式**：使用层级的整数部分作为上层，小数部分为插值权重

4. **缓存加载**：
   ```cpp
   fCurrMip = try_load_mips(image);
   ```
   尝试从图像或缓存中加载 mipmap，失败则回退到基础图像。

5. **层级提取**：
   - 从 mipmap 中获取指定索引的层级（注意索引偏移：`levelNum - 1`）
   - 如果层级不存在，回退到基础图像
   - 线性模式额外获取下一层级

6. **矩阵缩放**：
   ```cpp
   fUpperInv = SkMatrix::Scale(
       SkIntToScalar(pm.width()) / image->width(),
       SkIntToScalar(pm.height()) / image->height());
   ```
   计算从图像空间到层级空间的缩放矩阵。

### 缓存策略

辅助函数 `try_load_mips()` 实现分层缓存查找：

```cpp
static sk_sp<const SkMipmap> try_load_mips(const SkImage_Base* image) {
    sk_sp<const SkMipmap> mips = image->refMips();  // 1. 从图像获取
    if (!mips) {
        mips.reset(SkMipmapCache::FindAndRef(...));  // 2. 从缓存查找
    }
    if (!mips) {
        mips.reset(SkMipmapCache::AddAndRef(image));  // 3. 生成并缓存
    }
    return mips;
}
```

三级缓存策略确保 mipmap 尽可能被复用，避免重复计算。

### 回退机制

多种失败情况下会回退到基础图像：

- 矩阵无法分解为缩放（包含透视或复杂变换）
- 计算的层级 <= 0（放大或 1:1 映射）
- mipmap 加载失败（内存不足或格式不支持）
- 请求的层级不存在

回退时通过 `load_upper_from_base()` 加载原始图像：

```cpp
auto load_upper_from_base = [&]() {
    if (fBaseStorage.getPixels() == nullptr) {
        auto dContext = as_IB(image)->directContext();
        (void)image->getROPixels(dContext, &fBaseStorage);
        fUpper.reset(fBaseStorage.info(), fBaseStorage.getPixels(), fBaseStorage.rowBytes());
    }
};
```

### 线性模式插值

线性模式（三线性过滤）需要两个层级：

- **上层**：`floor(level)` 对应的层级
- **下层**：`floor(level) + 1` 对应的层级
- **权重**：`fract(level)` 作为插值系数

上层采样结果与下层采样结果按权重混合：

```
result = upper * (1 - weight) + lower * weight
```

## 依赖关系

### 依赖的模块

| **模块** | **用途** |
|---------|---------|
| `SkMipmap` | mipmap 数据存储，提供层级访问 |
| `SkBitmapCache` / `SkMipmapCache` | mipmap 对象缓存管理 |
| `SkImage_Base` | 图像基类，提供像素和 mipmap 访问 |
| `SkMatrix` | 变换矩阵分解和缩放计算 |
| `SkPixmap` | 层级像素数据访问 |
| `SkArenaAlloc` | 内存分配器，管理访问器生命周期 |

### 被依赖的模块

| **模块** | **关系** |
|---------|---------|
| `SkImageShader` | 使用访问器选择纹理采样层级 |
| 图像绘制系统 | 在缩放绘制时使用 mipmap |
| 着色器系统 | 纹理采样的核心组件 |
| 测试和基准测试 | 验证 mipmap 选择逻辑 |

## 设计模式与设计决策

### 访问器模式

`SkMipmapAccessor` 实现访问器模式，封装复杂的层级选择逻辑：

- 提供统一的接口访问不同层级
- 隐藏缓存查找、回退策略等细节
- 支持多种 mipmap 模式的统一处理

### 工厂方法 + Arena 分配

使用静态 `Make()` 方法配合 `SkArenaAlloc`：

- 对象生命周期与渲染上下文绑定，自动释放
- 避免单独的内存管理开销
- 失败时返回 `nullptr`，调用者易于处理

### 延迟加载与懒惰求值

- 基础图像数据仅在需要时加载（回退场景）
- mipmap 尝试从多级缓存获取，避免重复生成
- 变换矩阵按需计算

### 非拷贝语义

继承 `SkNoncopyable`，强制单一所有权：

- 避免意外的昂贵拷贝操作
- 明确对象生命周期管理责任
- 与 Arena 分配器配合使用

## 性能考量

### 缓存效率

- **三级缓存查找**：图像 → 全局缓存 → 动态生成，最小化重复计算
- **智能指针共享**：多个访问器可共享同一个 mipmap 对象
- **缓存命中率**：常用图像的 mipmap 可长期驻留缓存

### 矩阵分解优化

使用 `decomposeScale()` 快速提取缩放因子：

- 避免完整的矩阵分解（SVD）
- 对于纯缩放和旋转矩阵，O(1) 复杂度
- 复杂变换无法分解时快速回退

### 内存管理

- **Arena 分配**：批量分配和释放，减少堆管理开销
- **懒惰加载**：仅在实际需要时加载基础图像数据
- **智能指针**：自动引用计数，防止 mipmap 过早释放

### 分支预测友好

代码结构按常见路径优化：

- 最常见：成功加载 mipmap 并使用中间层级
- 次常见：使用基础图像（无 mipmap 或放大）
- 罕见：加载失败或层级不存在

### 使用建议

- 在渲染上下文中通过 `SkArenaAlloc` 分配，避免单独管理生命周期
- 检查返回值：`Make()` 失败时返回 `nullptr`
- 线性模式下检查 `lowerWeight() > 0` 判断是否需要双层级采样
- 大规模绘制时复用 mipmap 缓存，避免重复计算

## 相关文件

| **文件路径** | **说明** |
|-------------|---------|
| `src/core/SkMipmap.h/cpp` | mipmap 核心数据结构和层级计算 |
| `src/core/SkBitmapCache.h/cpp` | mipmap 和图像数据缓存 |
| `src/image/SkImage_Base.h` | 图像基类，提供 mipmap 访问接口 |
| `include/core/SkMatrix.h` | 变换矩阵和分解方法 |
| `src/base/SkArenaAlloc.h` | 内存分配器 |
| `include/core/SkSamplingOptions.h` | 采样选项定义，包含 `SkMipmapMode` |
| `src/shaders/SkImageShader.cpp` | 使用 `SkMipmapAccessor` 的典型场景 |
