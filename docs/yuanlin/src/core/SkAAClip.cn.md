# SkAAClip

> 源文件
> - src/core/SkAAClip.h
> - src/core/SkAAClip.cpp

## 概述

`SkAAClip` 是 Skia 中用于表示抗锯齿裁剪区域的核心类。与传统的基于区域（`SkRegion`）的裁剪不同，`SkAAClip` 能够存储每个像素的部分 alpha 覆盖率信息，从而实现更平滑的裁剪边缘。该类使用游程长度编码（Run-Length Encoding, RLE）来高效存储抗锯齿数据，特别适合处理路径和复杂形状的裁剪。

`SkAAClip` 的主要功能包括：
- 从矩形、路径、区域创建抗锯齿裁剪
- 支持裁剪操作（交集、差集）
- 提供高效的查询和遍历接口
- 与 `SkBlitter` 系统集成，用于实际的像素绘制

## 架构位置

`SkAAClip` 位于 Skia 的核心渲染管线中，处于以下层次：

```
应用层 API (SkCanvas)
    ↓
裁剪系统 (SkAAClip, SkRegion)
    ↓
光栅化系统 (SkScan, SkBlitter)
    ↓
像素缓冲区
```

该类是裁剪子系统的关键组件，与路径扫描转换器（`SkScan`）和像素填充器（`SkBlitter`）紧密协作。

## 主要类与结构体

### SkAAClip

**继承关系**：无基类，独立类

**关键成员变量**：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fBounds` | `SkIRect` | 裁剪区域的边界矩形 |
| `fRunHead` | `RunHead*` | 指向游程数据的指针，使用引用计数管理 |

### SkAAClip::RunHead

内部结构体，存储游程编码数据。

**关键成员变量**：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fRefCnt` | `std::atomic<int32_t>` | 引用计数，支持数据共享 |
| `fRowCount` | `int32_t` | Y 方向的行数 |
| `fDataSize` | `size_t` | 游程数据的字节大小 |

**数据布局**：
```
[RunHead][YOffset数组][游程数据]
```

每个 `YOffset` 包含：
- `fY`：相对 Y 坐标
- `fOffset`：该行游程数据的偏移量

游程数据格式为 `[count, alpha]` 对，每对占 2 字节。

### SkAAClip::Builder

内部构建器类，用于从路径或裁剪操作构建 `SkAAClip`。

**关键功能**：
- 逐行收集抗锯齿数据
- 合并相同的连续行以压缩数据
- 执行裁剪操作（交集、差集）

### SkAAClipBlitter

**继承关系**：继承自 `SkBlitter`

**关键成员变量**：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fBlitter` | `SkBlitter*` | 实际执行绘制的底层 blitter |
| `fAAClip` | `const SkAAClip*` | 抗锯齿裁剪数据 |
| `fAAClipBounds` | `SkIRect` | 裁剪边界的缓存 |
| `fRuns` | `int16_t*` | 游程缓冲区 |
| `fAA` | `SkAlpha*` | alpha 值缓冲区 |

## 公共 API 函数

### 构造与析构

| 函数 | 说明 |
|------|------|
| `SkAAClip()` | 默认构造函数，创建空裁剪 |
| `SkAAClip(const SkAAClip&)` | 拷贝构造函数，共享底层数据 |
| `~SkAAClip()` | 析构函数，释放引用计数 |
| `operator=(const SkAAClip&)` | 赋值操作符 |

### 查询函数

| 函数 | 说明 |
|------|------|
| `isEmpty()` | 判断裁剪区域是否为空 |
| `getBounds()` | 获取边界矩形 |
| `isRect()` | 判断是否为不带抗锯齿的纯矩形 |
| `quickContains(const SkIRect&)` | 快速判断矩形是否完全被包含 |

### 设置函数

| 函数 | 说明 |
|------|------|
| `setEmpty()` | 设置为空裁剪 |
| `setRect(const SkIRect&)` | 从矩形创建裁剪 |
| `setPath(const SkPath&, const SkIRect&, bool)` | 从路径创建抗锯齿裁剪 |
| `setRegion(const SkRegion&)` | 从区域创建裁剪 |

### 裁剪操作

| 函数 | 说明 |
|------|------|
| `op(const SkIRect&, SkClipOp)` | 与矩形执行裁剪操作 |
| `op(const SkRect&, SkClipOp, bool)` | 与浮点矩形执行裁剪操作 |
| `op(const SkAAClip&, SkClipOp)` | 与另一个抗锯齿裁剪执行操作 |

支持的 `SkClipOp` 包括：
- `kIntersect`：交集
- `kDifference`：差集

### 其他操作

| 函数 | 说明 |
|------|------|
| `translate(int dx, int dy, SkAAClip*)` | 平移裁剪区域 |
| `copyToMask(SkMaskBuilder*)` | 将数据扩展到完整的遮罩中（用于调试） |

## 内部实现细节

### 游程编码格式

`SkAAClip` 使用紧凑的游程编码存储抗锯齿数据：

1. **Y 方向压缩**：连续相同的扫描行只存储一次
2. **X 方向编码**：每行使用 `[count, alpha]` 对编码
   - `count`：连续像素数（最大 255）
   - `alpha`：覆盖率（0-255）

示例：一行 10 个像素 `[0,0,0,128,128,255,255,255,0,0]` 编码为：
```
[3,0] [2,128] [3,255] [2,0]
```

### 构建过程

`Builder` 类负责构建裁剪数据：

1. **收集阶段**：通过 `Builder::Blitter` 接收扫描转换器的输出
2. **压缩阶段**：合并连续相同的行
3. **修剪阶段**：
   - `trimBounds()`：调整边界到实际数据范围
   - `trimTopBottom()`：移除顶部和底部的空行
   - `trimLeftRight()`：移除左右边缘的零列

### 裁剪操作实现

`Builder::operateY()` 和 `Builder::operateX()` 实现了裁剪操作：

- **Y 方向**：同时遍历两个裁剪的行，根据 Y 坐标对齐
- **X 方向**：逐像素处理游程，根据操作类型计算新的 alpha 值
  - 交集：`alpha = alpha_A × alpha_B / 255`
  - 差集：`alpha = alpha_A × (255 - alpha_B) / 255`

### 引用计数机制

`RunHead` 使用原子引用计数实现数据共享：
- 拷贝 `SkAAClip` 时增加引用计数，不复制数据
- 析构时减少引用计数，计数为 0 时释放内存
- 支持多线程安全的共享

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkPath` | 从路径创建裁剪 |
| `SkRegion` | 从区域创建裁剪 |
| `SkScan` | 路径扫描转换 |
| `SkBlitter` | 像素填充接口 |
| `SkMask` | 遮罩数据结构 |
| `SkRect` / `SkIRect` | 矩形操作 |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| `SkCanvas` | 使用 `SkAAClip` 实现软件渲染的裁剪 |
| `SkDraw` | 在绘制时应用抗锯齿裁剪 |
| `SkAAClipBlitter` | 将裁剪应用到 blitter 管线 |

## 设计模式与设计决策

### 写时复制（COW）模式

通过引用计数实现的隐式数据共享：
- 拷贝操作非常轻量（只增加引用计数）
- 修改操作会先释放旧数据
- 降低内存占用，提高性能

### 构建器模式

使用独立的 `Builder` 类构建裁剪数据：
- 分离构建逻辑和数据存储
- 支持增量构建
- 构建完成后生成不可变的 `RunHead`

### 迭代器模式

提供多个内部迭代器类：
- `Iter`：遍历 Y 方向的行
- `RowIter`：遍历单行的游程
- 支持高效的两个裁剪的同步遍历

### 策略模式

`AlphaProc` 函数指针实现不同的 alpha 合成策略：
- 交集操作使用乘法
- 差集操作使用减法
- 易于扩展新的裁剪操作

## 性能考量

### 内存优化

1. **游程编码**：将稀疏的抗锯齿数据压缩到原始大小的很小一部分
2. **行合并**：连续相同的行共享数据，Y 方向也实现压缩
3. **引用计数**：避免不必要的数据复制

### 计算优化

1. **边界裁剪**：
   - 操作前先检查边界，避免不必要的计算
   - `quickContains()` 快速判断包含关系

2. **分支优化**：
   - 在 `blitH()` 等函数中，先处理简单情况（全透明、全不透明）
   - 只在必要时展开完整的游程

3. **缓存友好**：
   - 数据紧凑存储，减少缓存未命中
   - 游程格式适合顺序访问

### 模糊器保护

代码中包含 `#if defined(SK_BUILD_FOR_FUZZER)` 检查：
- 限制操作范围，防止模糊测试时的资源耗尽
- 例如限制 Y 方向范围不超过 100,000

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkAAClip.h` | 类声明和公共接口 |
| `src/core/SkAAClip.cpp` | 实现代码 |
| `src/core/SkBlitter.h` | Blitter 基类接口 |
| `src/core/SkScan.h` | 扫描转换接口 |
| `include/core/SkPath.h` | 路径类 |
| `include/core/SkRegion.h` | 区域类 |
| `src/core/SkMask.h` | 遮罩数据结构 |
| `tests/AAClipTest.cpp` | 单元测试（推断） |
