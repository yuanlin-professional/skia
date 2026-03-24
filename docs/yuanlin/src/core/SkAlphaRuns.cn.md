# SkAlphaRuns

> 源文件
> - src/core/SkAlphaRuns.h
> - src/core/SkAlphaRuns.cpp

## 概述

`SkAlphaRuns` 是 Skia 图形库中用于存储和管理游程编码（Run-Length-Encoded）的 alpha 覆盖值的稀疏数组类。它主要用于反走样渲染中的超采样覆盖值管理，通过稀疏存储的方式高效地将多个路径组合到同一个缓冲区中。

## 架构位置

`SkAlphaRuns` 位于 Skia 核心渲染流水线的光栅化层，具体在扫描线渲染器（scanline rasterizer）中使用。它是 `SkBlitter` 系统的底层支持组件，为反走样渲染提供高效的 alpha 值累加机制。

```
Skia Core
  └── Rasterization
      └── Scanline Rendering
          └── SkAlphaRuns (游程编码的 alpha 缓冲)
              └── 被 SkBlitter 及其派生类使用
```

## 主要类与结构体

### SkAlphaRuns

**继承关系**
- 无继承关系（独立类）

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fRuns` | `int16_t*` | 游程长度数组，存储每个 alpha 值对应的连续像素数量 |
| `fAlpha` | `uint8_t*` | alpha 值数组，存储 0-255 的覆盖值 |
| `fWidth` | `int` | 扫描线宽度（仅在调试模式下） |

## 公共 API 函数

### 核心方法

**reset(int width)**
- **功能**: 重新初始化扫描线，准备处理新的扫描行
- **参数**: `width` - 扫描线的像素宽度
- **行为**: 将整个扫描线设置为单个游程，alpha 值为 0

**add(int x, U8CPU startAlpha, int middleCount, U8CPU stopAlpha, U8CPU maxValue, int offsetX)**
- **功能**: 向缓冲区插入一个游程，支持起始、中间和结束 alpha 值
- **参数**:
  - `x`: 游程起始 x 坐标
  - `startAlpha`: 起始像素的 alpha 增量（如果 > 0）
  - `middleCount`: 中间完整覆盖的像素数量
  - `stopAlpha`: 结束像素的 alpha 增量（如果 > 0）
  - `maxValue`: 中间像素的 alpha 增量值
  - `offsetX`: 当前偏移量，用于优化连续调用
- **返回**: 下次调用应使用的新 offsetX 值
- **特性**: 自动处理 alpha 值溢出，最大值为 255

**empty() const**
- **功能**: 检查扫描线是否为空（只包含一个 alpha 为 0 的游程）
- **返回**: 如果扫描线为空返回 true

### 静态工具方法

**Break(int16_t runs[], uint8_t alpha[], int x, int count)**
- **功能**: 在指定位置拆分游程，为后续累加操作做准备
- **示例**: `A4B4` 在位置 2、长度 5 处拆分后变为 `A2A2B3B1`
- **用途**: 允许 `add()` 方法对子游程进行累加操作

**BreakAt(int16_t runs[], uint8_t alpha[], int x)**
- **功能**: 在指定位置将一个游程切分为两个相同 alpha 值的短游程
- **用途**: 被 `RectClipBlitter` 用于裁剪 RLE 编码以匹配裁剪矩形

**CatchOverflow(int alpha)**
- **功能**: 将 0-256 范围的 alpha 值安全转换为 0-255
- **实现**: `alpha - (alpha >> 8)` 优雅地处理 256 溢出情况
- **返回**: 标准化的 0-255 alpha 值

## 内部实现细节

### 游程编码格式

`SkAlphaRuns` 使用两个并行数组实现游程编码：
- `fRuns[i]` 存储游程长度（正值表示连续像素数量，0 表示结束）
- `fAlpha[i]` 存储对应的 alpha 值

编码示例：
```
像素序列: AAAABBBB
编码结果: fRuns = [4, 4, 0], fAlpha = [valueA, valueB, ...]
```

### Alpha 累加机制

`add()` 方法的核心特性：
1. **溢出保护**: 使用 `alpha - (alpha >> 8)` 将 256 截断为 255
2. **稀疏更新**: 只在需要的位置拆分游程，避免全量更新
3. **连续性优化**: 通过 offsetX 参数避免重复遍历已处理区域

### 内存布局

```
扫描线宽度 = 8 像素
初始状态:   fRuns[0] = 8, fRuns[8] = 0, fAlpha[0] = 0
添加后:     fRuns = [2, 3, 3, 0], fAlpha = [20, 255, 180]
表示:       2个20% + 3个100% + 3个70%覆盖的像素
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkColor.h` | SkAlpha 类型定义 |
| `include/core/SkTypes.h` | 基本类型定义（U8CPU） |
| `include/private/base/SkCPUTypes.h` | CPU 类型抽象 |
| `include/private/base/SkDebug.h` | SkASSERT 宏 |
| `include/private/base/SkTo.h` | 类型转换工具（SkToU8, SkToS16, SkToS32） |
| `src/core/SkMemset.h` | 内存操作优化（调试模式） |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `SkBlitter` | 使用 SkAlphaRuns 存储扫描线 alpha 值 |
| `SkAntiHairlineBlitter` | 反走样线条渲染 |
| `SkARGB32_Blitter` | 32 位颜色混合 |
| `SkScanlineDecoder` | 图像解码中的扫描线处理 |
| `SkAnalyticEdgeRasterizer` | 分析式边缘光栅化 |

## 设计模式与设计决策

### 游程编码（RLE）模式
- **动机**: 扫描线渲染中经常出现大量连续相同 alpha 值的像素
- **优势**: 相比逐像素存储，节省内存并提高缓存效率
- **实现**: 使用长度+值的双数组表示，访问模式友好

### 稀疏数组模式
- **动机**: 多个路径可能在同一扫描线的不同区域贡献 alpha 值
- **优势**: 只需在关键位置拆分游程，支持增量更新
- **实现**: `Break` 方法按需拆分，`add` 方法局部累加

### 原地修改策略
- **特点**: 所有操作都直接修改内部缓冲区，无额外分配
- **优势**: 零动态内存分配，性能可预测
- **权衡**: 调用者需管理缓冲区生命周期

## 性能考量

### 优化点

1. **内联热点函数**
   - `add()` 使用 `SK_ALWAYS_INLINE` 强制内联
   - 频繁调用的扫描线处理路径被充分优化

2. **避免除法运算**
   - `CatchOverflow` 使用位移代替除法
   - 整数运算保证性能稳定

3. **缓存友好的内存布局**
   - 并行数组提供良好的空间局部性
   - 顺序访问模式利于预取

4. **早期退出**
   - `empty()` 快速检查避免无用处理
   - offsetX 参数跳过已处理区域

### 性能特征

| 操作 | 时间复杂度 | 说明 |
|------|-----------|------|
| reset | O(1) | 只设置少量值 |
| add | O(k) | k 为当前游程数，通常很小 |
| Break | O(k) | k 为需要拆分的游程数 |
| empty | O(1) | 常量时间检查 |

### 内存使用

- **固定开销**: `2 * sizeof(void*) + sizeof(int)` (debug 模式)
- **缓冲区大小**: 由调用者分配，典型为 `width * (sizeof(int16_t) + sizeof(uint8_t))`
- **最坏情况**: 每个像素都是一个游程（实际极少发生）

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/core/SkBlitter.h` | 使用者 | Blitter 使用 SkAlphaRuns 存储扫描线 |
| `src/core/SkScan.h` | 使用者 | 扫描转换使用 SkAlphaRuns |
| `src/core/SkAnalyticEdge.h` | 协作者 | 分析式边缘生成 alpha 游程 |
| `src/core/SkEdge.h` | 协作者 | 传统边缘生成 alpha 游程 |
| `src/core/SkMemset.h` | 依赖 | 内存操作优化 |
| `include/private/base/SkTo.h` | 依赖 | 类型安全转换 |
