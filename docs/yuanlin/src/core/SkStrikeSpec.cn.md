# SkStrikeSpec

> 源文件
> - src/core/SkStrikeSpec.h
> - src/core/SkStrikeSpec.cpp

## 概述

`SkStrikeSpec` 是 Skia 字形缓存系统中的核心规格类,用于定义和创建字形渲染缓存(Strike)的配置参数。该类封装了字体、绘制属性、设备矩阵等信息,用于生成唯一的 `SkDescriptor`,进而查找或创建对应的字形缓存。它还提供了多个辅助类(Bulk*类)用于批量获取字形度量、路径和图像数据。

主要功能:
- 根据不同场景(遮罩、路径、变换等)创建 Strike 规格
- 管理 `SkDescriptor` 和相关效果(MaskFilter、PathEffect)
- 提供字形缓存的查找和创建接口
- 批量字形数据获取的工具类

## 架构位置

`SkStrikeSpec` 位于 Skia 文本渲染管线的中间层:
- 上层:接收来自 `SkFont`、`SkPaint`、`SkSurfaceProps` 的输入
- 下层:与 `SkStrike`、`SkStrikeCache`、`SkScalerContext` 交互
- 作用:作为字形缓存系统的"配方",将高层绘制参数转换为缓存查找键

## 主要类与结构体

### SkStrikeSpec

**继承关系**: 无基类,独立类

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fAutoDescriptor` | `SkAutoDescriptor` | 包含字形规格的描述符 |
| `fMaskFilter` | `sk_sp<SkMaskFilter>` | 遮罩滤镜效果 |
| `fPathEffect` | `sk_sp<SkPathEffect>` | 路径效果 |
| `fTypeface` | `sk_sp<SkTypeface>` | 字体对象 |

### SkBulkGlyphMetrics

批量获取字形度量信息的工具类。

**继承关系**: 无

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fGlyphs` | `AutoSTArray<20, const SkGlyph*>` | 字形指针数组 |
| `fStrike` | `sk_sp<SkStrike>` | 关联的 Strike 对象 |

### SkBulkGlyphMetricsAndPaths

批量获取字形度量和路径数据。

### SkBulkGlyphMetricsAndImages

批量获取字形度量和图像数据。

### SkBulkGlyphMetricsAndDrawables

批量获取字形度量和 Drawable 对象。

## 公共 API 函数

### 静态工厂方法

```cpp
// 创建遮罩样式缓存规格
static SkStrikeSpec MakeMask(
    const SkFont& font,
    const SkPaint& paint,
    const SkSurfaceProps& surfaceProps,
    SkScalerContextFlags scalerContextFlags,
    const SkMatrix& deviceMatrix);

// 创建用于变换遮罩的规格(禁用子像素定位)
static SkStrikeSpec MakeTransformMask(...);

// 创建路径样式缓存规格,返回规格和缩放比例
static std::tuple<SkStrikeSpec, SkScalar> MakePath(...);

// 创建规范化规格(无设备依赖)
static std::tuple<SkStrikeSpec, SkScalar> MakeCanonicalized(
    const SkFont& font, const SkPaint* paint = nullptr);

// 创建无设备规格
static SkStrikeSpec MakeWithNoDevice(...);
```

### Strike 查找与创建

```cpp
// 从 GPU 缓存查找或创建 Strike
sk_sp<sktext::StrikeForGPU> findOrCreateScopedStrike(
    sktext::StrikeForGPUCacheInterface* cache) const;

// 从全局缓存查找或创建 Strike
sk_sp<SkStrike> findOrCreateStrike() const;

// 从指定缓存查找或创建 Strike
sk_sp<SkStrike> findOrCreateStrike(SkStrikeCache* cache) const;
```

### 辅助方法

```cpp
// 创建 ScalerContext
std::unique_ptr<SkScalerContext> createScalerContext() const;

// 获取描述符
const SkDescriptor& descriptor() const;

// 判断是否应该绘制为路径
static bool ShouldDrawAsPath(const SkPaint& paint, const SkFont& font, const SkMatrix& matrix);
```

## 内部实现细节

### Strike 规格创建逻辑

1. **MakeMask**: 标准遮罩模式,保留所有字体设置
2. **MakeTransformMask**: 禁用子像素定位(`setSubpixel(false)`),用于变换场景
3. **MakePath**: 调用 `setupForAsPaths` 准备路径渲染,返回缩放因子
4. **MakeCanonicalized**: 根据字体大小判断是否需要路径模式,提供规范化配置

### 路径模式判断条件

在 `ShouldDrawAsPath` 中,以下情况使用路径渲染:
- 细线描边(stroke width = 0)
- 透视变换
- 字形尺寸超过 256x256 像素

### Descriptor 生成

通过 `SkScalerContext::CreateDescriptorAndEffectsUsingPaint` 创建:
- 合成字体、绘制属性、表面属性
- 提取 MaskFilter 和 PathEffect
- 生成唯一的 Descriptor 哈希值

### 批量类工作机制

所有 `SkBulkGlyph*` 类:
1. 构造时创建或获取 Strike
2. 预分配典型数量(20或64)的指针数组
3. 调用 Strike 的相应方法填充数据
4. 返回 `SkSpan<const SkGlyph*>` 视图

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkDescriptor` | 生成字形缓存键 |
| `SkScalerContext` | 创建字形渲染上下文 |
| `SkFont` / `SkPaint` | 获取渲染参数 |
| `SkTypeface` | 字体数据源 |
| `SkStrike` | 字形缓存对象 |
| `SkStrikeCache` | 缓存管理器 |
| `SkMaskFilter` / `SkPathEffect` | 渲染效果 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| 文本渲染管线 | 创建 Strike 规格进行字形查找 |
| GPU 文本渲染 | 通过 `StrikeForGPU` 接口 |
| 字形缓存系统 | 作为缓存查找键 |

## 设计模式与设计决策

### 设计模式

1. **工厂模式**: 多个静态 `Make*` 方法根据场景创建不同配置
2. **门面模式**: 封装复杂的 Descriptor 创建逻辑
3. **RAII**: `SkBulkGlyph*` 类自动管理 Strike 生命周期
4. **批量处理**: 提供专门的 Bulk 类优化批量操作

### 设计决策

1. **不可变性**: 一旦创建,SkStrikeSpec 的核心属性不可修改(删除赋值操作符)
2. **移动语义**: 支持 move 构造函数,避免不必要的引用计数操作
3. **返回 tuple**: `MakePath` 和 `MakeCanonicalized` 返回规格和缩放因子,避免多次调用
4. **分离关注点**:
   - SkStrikeSpec 只负责配置
   - Strike 创建委托给 SkStrikeCache
   - 字形生成委托给 SkScalerContext

5. **批量优化**:
   - 使用 `AutoSTArray` 避免小数组的堆分配
   - 典型值设为 20/64,基于实际使用统计

## 性能考量

1. **Descriptor 缓存**: `SkAutoDescriptor` 栈分配小型描述符,避免堆分配
2. **引用计数优化**: 使用 `sk_sp` 智能指针管理共享对象
3. **批量接口**: 一次性获取多个字形,减少虚函数调用和锁竞争
4. **惰性创建**: Strike 在首次需要时才创建,避免预先分配

5. **内存效率**:
   - `AutoSTArray` 结合栈和堆分配
   - 小数组(<=20)使用栈内存
   - 大数组自动切换到堆

6. **缓存友好**:
   - Strike 规格作为哈希键,查找速度快
   - Descriptor 包含完整配置,避免重复计算

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkStrike.h` | Strike 缓存对象 |
| `src/core/SkStrikeCache.h` | Strike 缓存管理器 |
| `src/core/SkDescriptor.h` | 字形描述符 |
| `src/core/SkScalerContext.h` | 字形缩放上下文 |
| `src/core/SkGlyph.h` | 字形数据结构 |
| `src/core/SkFontPriv.h` | 字体私有工具 |
| `src/text/StrikeForGPU.h` | GPU Strike 接口 |
| `include/core/SkFont.h` | 字体 API |
| `include/core/SkPaint.h` | 绘制属性 |
