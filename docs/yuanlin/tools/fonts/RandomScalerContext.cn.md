# RandomScalerContext

> 源文件
> - tools/fonts/RandomScalerContext.h
> - tools/fonts/RandomScalerContext.cpp

## 概述

RandomScalerContext 是一个专门用于调试目的的字体缩放上下文实现。该模块通过 `SkRandomTypeface` 类型包装一个真实的字体，并配合 `RandomScalerContext` 缩放上下文，根据字形 ID 以确定性但"随机"的方式返回不同的光栅化掩码格式（LCD、A8、BW、ARGB），用于测试 Skia 在处理多种掩码格式时的鲁棒性。

该模块的主要功能包括：
- 根据字形 ID 模 4 的结果选择不同的掩码格式（LCD16、A8、ARGB32、BW）
- 代理真实字体的字形度量和渲染
- 对于 ARGB32 格式的字形，使用路径绘制而非直接渲染
- 支持 "fake it" 模式，生成空白图像用于性能测试

## 架构位置

该模块位于 Skia 的测试工具层，具体架构位置如下：

```
skia/
├── include/core/          # 核心 API（SkTypeface）
├── src/core/              # 核心实现（SkScalerContext）
└── tools/fonts/           # 字体测试工具
    ├── RandomScalerContext.h    # 本模块头文件
    └── RandomScalerContext.cpp  # 本模块实现
```

在字体渲染架构中的位置：
- 继承自 `SkScalerContext`：字形光栅化的核心抽象
- 实现 `SkTypeface` 的代理包装器
- 作为测试工具，不参与生产代码路径

## 主要类与结构体

### SkRandomTypeface
```cpp
class SkRandomTypeface : public SkTypeface
```
字体类型的包装器，用于创建随机掩码格式的缩放上下文。

**主要成员**：
- `sk_sp<SkTypeface> fProxy`：被代理的真实字体
- `SkPaint fPaint`：用于 ARGB32 格式渲染的绘制设置
- `bool fFakeIt`：是否启用伪造模式（生成空白图像）

**核心方法**：
- `onCreateScalerContext()`：创建 RandomScalerContext 实例
- `onFilterRec()`：强制设置掩码格式为 ARGB32，禁用字体微调
- 其他 `on*()` 方法：将调用转发给 `fProxy`

### RandomScalerContext
```cpp
class RandomScalerContext : public SkScalerContext
```
缩放上下文的实现，负责生成具有随机掩码格式的字形度量和图像。

**主要成员**：
- `std::unique_ptr<SkScalerContext> fProxy`：代理的真实缩放上下文
- `THashMap<SkPackedGlyphID, SkGlyph> fProxyGlyphs`：缓存代理字形数据
- `bool fFakeIt`：伪造模式标志

**核心方法**：
- `generateMetrics()`：生成字形度量，根据字形 ID 决定掩码格式
- `generateImage()`：生成字形图像
- `generatePath()`：生成字形路径
- `generateDrawable()`：生成可绘制对象
- `generateFontMetrics()`：生成字体度量

## 公共 API 函数

### SkRandomTypeface 构造函数
```cpp
SkRandomTypeface(sk_sp<SkTypeface> proxy, const SkPaint& paint, bool fakeit)
```
**功能**：创建随机字体包装器
**参数**：
- `proxy`：被包装的真实字体
- `paint`：用于 ARGB32 格式渲染的绘制设置
- `fakeit`：是否启用伪造模式

### SkRandomTypeface::proxy()
```cpp
SkTypeface* proxy() const
```
**功能**：返回被代理的真实字体对象

### SkRandomTypeface::paint()
```cpp
const SkPaint& paint() const
```
**功能**：返回用于 ARGB32 渲染的绘制设置

## 内部实现细节

### 掩码格式选择算法
```cpp
SkMask::Format format = SkMask::kA8_Format;
switch (origGlyph.getGlyphID() % 4) {
    case 0: format = SkMask::kLCD16_Format; break;   // LCD 子像素渲染
    case 1: format = SkMask::kA8_Format; break;      // 8 位抗锯齿
    case 2: format = SkMask::kARGB32_Format; break;  // 32 位彩色
    case 3: format = SkMask::kBW_Format; break;      // 黑白位图
}
```
这个简单的模运算确保了：
- 每个字形的格式是确定的（相同字形 ID 总是得到相同格式）
- 四种格式均匀分布
- 易于调试和重现问题

### ARGB32 格式的特殊处理
对于 `glyphID % 4 == 2` 的字形（ARGB32 格式）：
1. 从代理获取字形路径
2. 如果路径存在，缓存到 `fProxyGlyphs` 映射表中
3. 使用 `fPaint` 计算路径边界作为字形边界
4. 在 `generateImage()` 中，使用 `SkCanvas` 绘制路径到位图

这种方法模拟了彩色字形（如 emoji）的渲染流程。

### 伪造模式实现
当 `fFakeIt` 为 true 时：
- `generateMetrics()`：仍然返回真实度量，但标记为 `computeFromPath`
- `generateImage()`：直接用零填充图像缓冲区，跳过渲染

这用于性能测试，避免实际渲染开销。

### 字形缓存机制
`fProxyGlyphs` 哈希表缓存了需要特殊处理的字形：
- 键：`SkPackedGlyphID`（字形 ID + 子像素位置）
- 值：完整的 `SkGlyph` 对象（包含路径）

缓存原因：
- 原始字形对象不保存路径（标记为 `neverRequestPath`）
- 需要在 `generateImage()` 时访问路径数据
- 避免重复从代理获取路径

## 依赖关系

### 核心依赖
- `SkTypeface`：字体类型的基类
- `SkScalerContext`：缩放上下文的基类
- `SkGlyph`：字形数据结构
- `SkPaint`：绘制设置
- `SkPath`：矢量路径

### 内部依赖
- `SkAdvancedTypefaceMetrics`：高级字体元数据
- `SkFontDescriptor`：字体描述符
- `SkScalerContextRec`：缩放上下文记录
- `THashMap`：高效哈希表实现

### 代理模式依赖
所有实际的字体操作都转发给 `fProxy` 成员：
```cpp
fProxy->countGlyphs()
fProxy->getUnitsPerEm()
fProxy->getFamilyName()
// ... 等等
```

## 设计模式与设计决策

### 代理模式（Proxy Pattern）
核心设计模式，体现在两个层面：
1. **SkRandomTypeface 代理 SkTypeface**：
   - 包装真实字体对象
   - 转发大部分方法调用
   - 仅修改缩放上下文创建逻辑

2. **RandomScalerContext 代理 SkScalerContext**：
   - 包装真实缩放上下文
   - 修改字形度量和图像生成
   - 保持字体度量不变

### 策略模式（Strategy Pattern）
通过 `fFakeIt` 标志切换不同的图像生成策略：
- 正常模式：真实渲染或路径绘制
- 伪造模式：生成空白图像

### 确定性随机化
使用字形 ID 的模运算而非真正的随机数：
- **优点**：结果可重现，便于调试和测试
- **缺点**：分布模式固定，可能无法覆盖某些边缘情况

### 延迟路径获取
仅在需要时才从代理获取字形路径：
```cpp
if (fFakeIt || (glyph.getGlyphID() % 4) != 2) {
    // 不需要路径
    return mx;
}
fProxy->getPath(glyph, alloc);  // 仅 ARGB32 格式需要
```
这减少了不必要的路径生成开销。

### 不可序列化设计
```cpp
// TODO: anything that uses this typeface isn't correctly serializable,
// since this typeface cannot be deserialized.
```
该字体仅用于测试，不支持序列化/反序列化。

## 性能考量

### 伪造模式优化
`fFakeIt` 模式显著提升性能：
- 跳过所有实际渲染操作
- 仅执行度量计算
- 适用于布局性能测试

### 字形缓存开销
`fProxyGlyphs` 哈希表带来的影响：
- **空间**：仅缓存 25% 的字形（ARGB32 格式）
- **时间**：哈希查找为 O(1)，额外开销很小
- **收益**：避免重复路径生成

### 路径绘制成本
ARGB32 格式使用路径绘制：
- 需要创建 `SkBitmap` 和 `SkCanvas`
- 执行完整的绘制管线
- 比直接光栅化慢，但模拟了真实的彩色字形场景

### 代理调用开销
每个操作都有额外的虚函数调用：
```
调用者 -> SkRandomTypeface -> fProxy -> 真实实现
```
但由于仅用于测试，这种开销是可接受的。

## 相关文件

### 核心接口
- `include/core/SkTypeface.h`：字体类型基类定义
- `src/core/SkScalerContext.h`：缩放上下文基类
- `src/core/SkGlyph.h`：字形数据结构

### 渲染相关
- `include/core/SkPaint.h`：绘制设置
- `include/core/SkPath.h`：矢量路径
- `include/core/SkCanvas.h`：绘制画布
- `include/core/SkBitmap.h`：位图数据结构

### 工具相关
- `tools/fonts/`：其他字体测试工具
- `src/core/SkAdvancedTypefaceMetrics.h`：字体元数据
- `src/core/SkTHash.h`：哈希表实现

### 测试用途
该模块通常配合以下工具使用：
- DM（Skia 的测试框架）
- 各种字体渲染单元测试
- 性能基准测试工具
