# SkRegion_path

> 源文件
> - src/core/SkRegion_path.cpp

## 概述

`SkRegion_path.cpp` 实现了 SkPath 到 SkRegion 的转换逻辑,以及 SkRegion 到 SkPath 的边界路径提取功能。该模块负责将矢量路径光栅化为整数坐标区域,并支持通过边界追踪算法将区域重建为路径。这是 Skia 裁剪系统的核心组件之一,连接了矢量几何 (SkPath) 和整数区域 (SkRegion) 两种表示形式。

## 架构位置

位于 SkRegion 模块的路径转换子系统:
- **调用者**: SkRegion::setPath, SkRegion::getBoundaryPath
- **依赖**: SkScan (扫描转换), SkBlitter (光栅化回调), SkPath (路径遍历)
- **层级**: SkRegion 的扩展实现,处理复杂几何转换

## 主要类与结构体

### SkRgnBuilder

路径到区域的扫描线构建器,实现 SkBlitter 接口。

**继承关系**:
```
SkBlitter
  └── SkRgnBuilder
```

**关键成员变量**:

| 变量 | 类型 | 说明 |
|------|------|------|
| fStorage | SkRegion::RunType* | 游程数据存储缓冲区 |
| fCurrScanline | Scanline* | 当前正在构建的扫描线 |
| fPrevScanline | Scanline* | 上一条扫描线 (用于合并) |
| fCurrXPtr | SkRegion::RunType* | 当前 X 坐标写入位置 |
| fTop | SkRegion::RunType | 第一个 Y 坐标 |
| fStorageCount | int | 缓冲区容量 (RunType 单位) |

### SkRgnBuilder::Scanline

内部扫描线数据结构。

**关键成员变量**:

| 变量 | 类型 | 说明 |
|------|------|------|
| fLastY | SkRegion::RunType | 扫描线的底部 Y 坐标 |
| fXCount | SkRegion::RunType | X 区间数量 (Left-Right 对数) |

**布局**:
```
Scanline: [fLastY, fXCount, Left1, Right1, Left2, Right2, ..., Sentinel]
```

### Edge

边界路径提取时使用的边数据结构。

**关键成员变量**:

| 变量 | 类型 | 说明 |
|------|------|------|
| fX | SkRegionPriv::RunType | 边的 X 坐标 |
| fY0, fY1 | SkRegionPriv::RunType | 边的起始和结束 Y 坐标 |
| fFlags | uint8_t | 链接标志 (kY0Link/kY1Link) |
| fNext | Edge* | 指向链接的下一条边 |

## 公共 API 函数

### SkRegion::setPath

```cpp
bool SkRegion::setPath(const SkPath& path, const SkRegion& clip)
```

**功能**: 将路径转换为区域,使用裁剪区域限制范围。

**参数**:
- `path`: 要转换的路径
- `clip`: 裁剪区域 (必须是矩形或矩形内部区域)

**返回**: 成功返回 true,路径为空或超出裁剪返回 false。

### SkRegion::addBoundaryPath

```cpp
bool SkRegion::addBoundaryPath(SkPathBuilder* builder) const
```

**功能**: 将区域的边界转换为路径并添加到 SkPathBuilder。

**返回**: 区域非空返回 true。

### SkRegion::getBoundaryPath

```cpp
SkPath SkRegion::getBoundaryPath() const
```

**功能**: 返回区域边界的完整路径。

## 内部实现细节

### SkRgnBuilder::init

```cpp
bool init(int maxHeight, int maxTransitions, bool pathIsInverse)
```

**功能**: 初始化构建器,分配工作缓冲区。

**参数**:
- `maxHeight`: 路径垂直跨度
- `maxTransitions`: 最大 X 转换次数 (边的数量)
- `pathIsInverse`: 是否为反向填充路径

**缓冲区大小计算**:
```cpp
size_t count = (maxHeight + 1) * (maxTransitions + 3);
if (pathIsInverse) {
    count += 10;  // 顶部和底部的空行
}
```

**反向路径处理**:
- 每条扫描线添加两个额外转换 `[L' ... normal ... R']`
- 顶部和底部添加空扫描线

### SkRgnBuilder::blitH

```cpp
void blitH(int x, int y, int width) override
```

**核心扫描线记录逻辑**:

1. **首次调用**: 初始化 fTop 和第一条扫描线
2. **Y 坐标跳跃**:
   - 完成当前扫描线 (`fCurrScanline->fXCount = ...`)
   - 尝试与前一条合并 (`collapsWithPrev()`)
   - 插入空扫描线 (如果 Y 不连续)
3. **X 区间合并**:
   - 检查 `fCurrXPtr[-1] == x` (与前一个区间相邻)
   - 相邻则扩展: `fCurrXPtr[-1] = x + width`
   - 否则添加新区间: `[x, x + width]`

### SkRgnBuilder::done

```cpp
void done()
```

**完成构建**:
- 设置最后一条扫描线的 fXCount
- 尝试最后一次合并 (`collapsWithPrev()`)

### SkRgnBuilder::collapsWithPrev

```cpp
bool collapsWithPrev()
```

**扫描线合并条件**:
```cpp
fPrevScanline->fLastY + 1 == fCurrScanline->fLastY &&
fPrevScanline->fXCount == fCurrScanline->fXCount &&
sk_memeq32(fPrevScanline->firstX(), fCurrScanline->firstX(), fXCount)
```

**优化效果**: 将垂直相邻的相同扫描线合并为单条,显著减少游程数据。

### SkRgnBuilder::copyToRgn

```cpp
void copyToRgn(SkRegion::RunType runs[]) const
```

**转换为标准游程格式**:

**输入** (Scanline 格式):
```
Scanline: [LastY, XCount, L1, R1, ..., uninitialized]
```

**输出** (RunHead 格式):
```
[Top]
[Bottom, IntervalCount, L1, R1, ..., Sentinel]
...
[Sentinel]
```

**转换过程**:
```cpp
*runs++ = fTop;
do {
    *runs++ = line->fLastY + 1;        // Bottom
    *runs++ = line->fXCount >> 1;      // IntervalCount
    memcpy(runs, line->firstX(), ...);
    runs += count;
    *runs++ = SkRegion_kRunTypeSentinel;
    line = line->nextScanline();
} while (line < stop);
*runs = SkRegion_kRunTypeSentinel;
```

### count_path_runtype_values

```cpp
static int count_path_runtype_values(const SkPath& path, int* itop, int* ibot)
```

**功能**: 预计算路径转换所需的内存和边界。

**统计信息**:
- `maxEdges`: 路径中边的数量 (直线=1, 二次=2, 三次=3)
- `*itop, *ibot`: 路径的垂直边界

**优化**: 避免动态内存分配,提前分配足够缓冲区。

### setPath 分块处理

**大坐标处理**:
```cpp
if (SkScan::PathRequiresTiling(clipBounds)) {
    static constexpr int kTileSize = 32767 >> 1;  // SkFixed 限制
    for (int64_t top = ...; top < ...; top += kTileSize) {
        for (int64_t left = ...; left < ...; left += kTileSize) {
            // 偏移到 (0, 0)
            tileClipBounds.offset(-left, -top);
            path.tryMakeOffset(-left, -top);
            // 转换为区域
            tile.setPath(*newpath, SkRegion(tileClipBounds));
            // 恢复坐标
            tile.translate(left, top);
            this->op(tile, kUnion_Op);
        }
    }
}
```

**原因**: SkFixed (16.16 定点数) 限制坐标范围为 ±32767。

### addBoundaryPath 边追踪算法

**核心步骤**:

1. **边提取**:
```cpp
for (const SkIRect& r : iter) {
    edge[0].set(r.fLeft, r.fBottom, r.fTop);    // 左边 (下→上)
    edge[1].set(r.fRight, r.fTop, r.fBottom);   // 右边 (上→下)
}
```

2. **边排序**:
```cpp
SkTQSort<Edge>(start, stop, EdgeLT());  // 按 X, 然后按 Y
```

3. **边链接** (`find_link`):
```cpp
// 查找 base->fY1 == e->fY0 的边
for (e = base + 1; ...; e++) {
    if (y1 == e->fY0) {
        base->fNext = e;
        e->fFlags |= Edge::kY0Link;
        break;
    }
}
```

4. **路径提取** (`extract_path`):
```cpp
do {
    if (prev->fX != edge->fX || prev->fY1 != edge->fY0) {
        builder->lineTo(prev->fX, prev->fY1);  // 垂直线
        builder->lineTo(edge->fX, edge->fY0);  // 水平线
    }
    prev = edge;
    edge = edge->fNext;
} while (edge != base);
builder->close();
```

**优化**: 跳过共线的边 (相同 X 且 Y 连续)。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkScan | SkScan::FillPath 路径扫描转换 |
| SkBlitter | 光栅化回调接口 |
| SkPath | 路径遍历和变换 |
| SkRegionPriv | 内部数据结构和工具 |
| SkPathPriv | 路径私有接口 |
| SkTSort | 边排序算法 |
| SkSafeMath | 安全整数运算 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| SkRegion | setPath 和 getBoundaryPath 的实现 |
| SkCanvas | 路径裁剪时调用 setPath |

## 设计模式与设计决策

### 策略模式

**SkRgnBuilder 作为 Blitter**:
- 实现 `blitH` 接口,作为扫描转换的回调
- 将通用扫描逻辑与区域构建逻辑解耦

### 模板方法模式

**路径转换流程**:
1. 预计算 (`count_path_runtype_values`)
2. 初始化 (`init`)
3. 扫描转换 (`SkScan::FillPath`)
4. 完成构建 (`done`)
5. 提取结果 (`copyToRgn`)

### 设计权衡

1. **内存预分配 vs 动态增长**:
   - 选择预分配,避免扫描过程中的重新分配
   - 代价是可能浪费内存

2. **扫描线合并 vs 存储开销**:
   - 积极合并相邻相同扫描线
   - 减少 50-90% 的游程数据 (矩形密集区域)

3. **边链接 vs 直接生成**:
   - 使用边链接算法,支持任意复杂区域
   - 比直接追踪边界更通用,但需要排序

## 性能考量

### 时间复杂度

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| setPath | O(edges + scanlines) | 扫描转换 + 扫描线合并 |
| getBoundaryPath | O(rects log rects) | 边排序主导 |
| 扫描线合并 | O(1) | 常数时间比较 |

### 内存使用

**SkRgnBuilder 缓冲区**:
```cpp
size = (maxHeight + 1) * (maxTransitions + 3) * sizeof(RunType)
```

**典型场景** (1000x1000 路径, 100 条边):
```
size ≈ 1001 * 103 * 4 = 412 KB
```

### 优化策略

1. **早期退出**: 路径为空或完全在裁剪外时快速返回
2. **矩形检测**: 转换结果为矩形时避免复杂区域
3. **扫描线合并**: `collapsWithPrev()` 显著减少存储
4. **分块处理**: 大坐标路径分块避免 SkFixed 溢出

### 特殊情况优化

**反向路径**:
- 添加虚拟边界: `[clip.left, ..., clip.right]`
- 仅在路径为反向填充时触发

**空行插入**:
```cpp
if (y - 1 > prevLastY) {
    fCurrScanline->fLastY = y - 1;
    fCurrScanline->fXCount = 0;  // 空行
}
```

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| src/core/SkRegion.cpp | SkRegion 核心实现 |
| src/core/SkRegionPriv.h | 内部数据结构 |
| src/core/SkScan.h | 扫描转换接口 |
| src/core/SkBlitter.h | 光栅化回调 |
| include/core/SkPath.h | 路径类 |
| include/core/SkPathBuilder.h | 路径构建器 |
| src/base/SkTSort.h | 排序算法 |
| src/base/SkSafeMath.h | 安全整数运算 |
