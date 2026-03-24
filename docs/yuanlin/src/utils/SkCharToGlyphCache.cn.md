# SkCharToGlyphCache

> 源文件
> - src/utils/SkCharToGlyphCache.h
> - src/utils/SkCharToGlyphCache.cpp

## 概述

`SkCharToGlyphCache` 是一个高效的字符到字形映射缓存类，用于加速 Unicode 字符到字形 ID 的转换过程。该类通过维护一个排序的字符-字形对数组，并使用智能查找算法来快速检索已缓存的映射关系，从而避免重复的字体查询操作。

## 架构位置

该组件位于 Skia 工具层（`src/utils/`），作为字体渲染系统的性能优化辅助工具。它主要服务于文本渲染管道，在字体 typeface 和文本布局引擎之间提供缓存层，减少字符到字形转换的开销。

## 主要类与结构体

### SkCharToGlyphCache 类

核心缓存类，提供字符到字形的快速映射功能。

**成员变量：**
- `fKUnichar`: `SkTDArray<SkUnichar>` - 存储排序的 Unicode 字符数组（键）
- `fVGlyph`: `SkTDArray<SkGlyphID>` - 存储对应的字形 ID 数组（值）
- `fDenom`: `double` - 斜率查找算法的分母缓存值，用于优化大规模查找

**哨兵设计：**
数组的首尾各有一个哨兵元素（`0x80000000` 和 `0x7FFFFFFF`），这些非法 Unicode 值保证线性搜索总能停止，无需额外的边界检查。

## 公共 API 函数

### 构造与析构
- `SkCharToGlyphCache()`: 构造函数，初始化缓存并添加哨兵元素
- `~SkCharToGlyphCache()`: 析构函数
- `reset()`: 清空缓存内容，重置为初始状态（保留哨兵）

### 查询接口
```cpp
int findGlyphIndex(SkUnichar c) const
```
查找字符对应的字形 ID。返回值含义：
- 正数：直接返回字形 ID
- 负数：返回 `~index`，表示应该插入的位置

### 插入接口
```cpp
void insertCharAndGlyph(int index, SkUnichar, SkGlyphID)
```
在指定索引位置插入新的字符-字形对，并在必要时更新斜率缓存。

```cpp
void addCharAndGlyph(SkUnichar unichar, SkGlyphID glyph)
```
便利函数，自动处理查找和插入逻辑，避免重复插入相同字符。

### 计数接口
- `count()`: 返回当前缓存的字符数量（包括哨兵）

## 内部实现细节

### 双阶段查找策略

根据缓存大小自适应选择查找算法：

**1. 简单线性查找（`find_simple`）**
- 适用于小规模缓存（≤16 个元素，`kSmallCountLimit`）
- 顺序遍历数组直到找到目标或超过目标值
- 时间复杂度：O(n)，但在小数据集上具有良好的缓存局部性

**2. 斜率优化查找（`find_with_slope`）**
- 适用于大规模缓存（≥4 个元素，`kMinCountForSlope`）
- 基于当前值分布的"斜率"预测目标位置
- 计算公式：`index = 1 + denom * (count - 2) * (value - base[1])`
- 特殊处理边界情况（接近首尾哨兵）
- 预测后进行正向或反向线性搜索修正
- 平均时间复杂度：O(1) + O(k)，其中 k 是修正步数

### 斜率维护机制

`fDenom` 缓存值在以下情况更新：
- 插入操作影响 `fKUnichar[1]` 或 `fKUnichar[count-2]`（即首尾有效元素）
- 计算公式：`fDenom = 1.0 / (fKUnichar[count-2] - fKUnichar[1])`
- 避免每次查找时重复除法运算，提升性能

### 按位取反编码

使用 `~index` 编码未找到的插入位置，这是一种紧凑的错误处理模式：
- 正返回值表示找到（返回字形 ID）
- 负返回值通过 `~result` 解码得到插入索引
- 避免使用额外的布尔标志或结构体

## 依赖关系

**内部依赖：**
- `include/core/SkTypes.h` - 基础类型定义（`SkUnichar`、`SkGlyphID`）
- `include/private/base/SkTDArray.h` - 动态数组容器
- `include/private/base/SkTo.h` - 类型转换工具

**使用场景：**
- 字体渲染流程中的字形查找
- 文本整形器（text shaper）的字符处理
- 避免重复调用 `SkTypeface::charToGlyphID()` 等昂贵操作

## 设计模式与设计决策

### 自适应算法选择
根据数据规模动态切换查找策略，平衡了小规模缓存的简单性和大规模缓存的效率。阈值 16 是通过实验确定的最佳切换点。

### 哨兵模式
在数组首尾添加哨兵元素，简化循环逻辑并消除边界检查，这是经典的算法优化技巧。

### 内联优化
将 `count()` 和 `addCharAndGlyph()` 等小函数实现在头文件中，允许编译器进行内联优化。

### 有序数组设计
保持数组始终排序，虽然增加了插入成本（O(n)），但换来了快速查找（平均 O(1)），适合读多写少的场景。

## 性能考量

### 时间复杂度
- 查找：O(1) 平均情况（斜率法），O(log n) 最坏情况
- 插入：O(n)（需要移动数组元素）
- 重置：O(1)（仅释放内存）

### 空间复杂度
O(n)，维护两个平行数组，额外存储一个 double 值。

### 优化策略
1. **缓存斜率分母**：避免重复除法，将除法转换为乘法
2. **边界快速路径**：对接近边界的查询特殊处理，减少线性搜索次数
3. **哨兵消除分支**：通过哨兵保证循环终止，消除 if 分支判断

### 适用场景
最适合字符重复率高、缓存命中率高的文本处理场景，如渲染大段文本或相似内容。对于完全随机的字符序列，性能提升有限。

## 相关文件

**核心依赖：**
- `include/core/SkTypes.h` - 类型定义
- `include/private/base/SkTDArray.h` - 容器实现
- `include/private/base/SkTo.h` - 安全转换

**使用此缓存的模块：**
- `src/core/SkTypeface*.cpp` - 字体实现
- `src/text/gpu/*` - GPU 文本渲染
- 文本整形和布局相关组件
