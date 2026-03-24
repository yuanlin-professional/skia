# SkRegion

> 源文件
> - include/core/SkRegion.h
> - src/core/SkRegion.cpp

## 概述

`SkRegion` 是 Skia 中用于表示二维整数坐标区域的核心类,主要用于裁剪 (clipping) 操作。它能够高效地表示和操作任意形状的区域,支持空区域、单个矩形和复杂多矩形区域三种表示形式。通过游程编码 (Run-Length Encoding) 压缩存储,SkRegion 在保持高效内存使用的同时,提供了丰富的集合运算 (并集、交集、差集等) 和查询接口。

## 架构位置

`SkRegion` 位于 Skia 核心图形基础层:
- **使用者**: SkCanvas (裁剪栈), SkDraw (光栅化), SkPath (路径转区域)
- **依赖**: SkIRect, SkPath, SkRRect
- **层级**: 基础几何类,介于基本类型 (SkIRect) 和复杂几何 (SkPath) 之间

## 主要类与结构体

### SkRegion

表示整数坐标系上的二维区域。

**继承关系**:
```
SkRegion (不继承任何类,独立类)
  - 支持 trivially relocatable (可平凡迁移)
```

**关键成员变量**:

| 变量 | 类型 | 说明 |
|------|------|------|
| fBounds | SkIRect | 区域的包围盒 |
| fRunHead | RunHead* | 指向游程数据的指针 (复杂区域) |

**特殊值**:
- **空区域**: `fRunHead = emptyRunHeadPtr()` (特殊标记值 -1)
- **矩形区域**: `fRunHead = kRectRunHeadPtr` (nullptr)
- **复杂区域**: `fRunHead` 指向实际游程数据

### SkRegion::RunHead

管理复杂区域的游程编码数据。

**关键成员变量**:

| 变量 | 类型 | 说明 |
|------|------|------|
| fRefCnt | std::atomic&lt;int32_t&gt; | 引用计数 (支持写时复制) |
| fRunCount | int32_t | 游程数组长度 |
| fYSpanCount | int32_t | Y 方向扫描线数量 |
| fIntervalCount | int32_t | X 方向区间总数 |

### SkRegion::Iterator

遍历区域中的所有矩形。

**关键成员变量**:

| 变量 | 类型 | 说明 |
|------|------|------|
| fRgn | const SkRegion* | 被迭代的区域 |
| fRuns | const RunType* | 当前游程位置 |
| fRect | SkIRect | 当前矩形 |
| fDone | bool | 是否完成迭代 |

### SkRegion::Cliperator

遍历区域与裁剪矩形的交集。

### SkRegion::Spanerator

遍历指定扫描线上的水平线段。

## 公共 API 函数

### 构造与拷贝

```cpp
SkRegion()                              // 构造空区域
SkRegion(const SkRegion& region)        // 拷贝构造 (写时复制)
SkRegion(const SkIRect& rect)           // 从矩形构造
~SkRegion()                             // 析构函数
```

### 查询方法

```cpp
bool isEmpty() const                    // 是否为空
bool isRect() const                     // 是否为单矩形
bool isComplex() const                  // 是否为复杂区域
const SkIRect& getBounds() const        // 获取包围盒
int computeRegionComplexity() const     // 计算复杂度 (区间数)
```

### 设置方法

```cpp
bool setEmpty()                         // 设为空
bool setRect(const SkIRect& rect)       // 设为矩形
bool setRects(const SkIRect rects[], int count)  // 从矩形数组构造
bool setRegion(const SkRegion& src)     // 拷贝赋值
bool setPath(const SkPath& path, const SkRegion& clip)  // 从路径构造
```

### 集合运算

```cpp
enum Op {
    kDifference_Op,         // A - B
    kIntersect_Op,          // A ∩ B
    kUnion_Op,              // A ∪ B
    kXOR_Op,                // A ⊕ B (对称差)
    kReverseDifference_Op,  // B - A
    kReplace_Op             // = B
};

bool op(const SkIRect& rect, Op op)
bool op(const SkRegion& rgn, Op op)
bool op(const SkRegion& rgna, const SkRegion& rgnb, Op op)
```

### 查询包含关系

```cpp
bool contains(int32_t x, int32_t y) const       // 点是否在区域内
bool contains(const SkIRect& rect) const        // 矩形是否完全包含
bool contains(const SkRegion& rgn) const        // 区域是否完全包含
bool intersects(const SkIRect& rect) const      // 是否相交
bool intersects(const SkRegion& other) const
```

### 快速判断

```cpp
bool quickContains(const SkIRect& r) const      // 快速判断包含 (仅矩形区域)
bool quickReject(const SkIRect& rect) const     // 快速判断不相交
```

### 几何变换

```cpp
void translate(int dx, int dy)                  // 平移
void translate(int dx, int dy, SkRegion* dst) const
```

### 路径转换

```cpp
bool addBoundaryPath(SkPathBuilder* path) const  // 转换为路径
SkPath getBoundaryPath() const
```

### 序列化

```cpp
size_t writeToMemory(void* buffer) const
size_t readFromMemory(const void* storage, size_t length)
```

## 内部实现细节

### 游程编码格式

**布局**:
```
[Top]
[Bottom, IntervalCount, [Left1, Right1], [Left2, Right2], ..., Sentinel]
...
[Y-Sentinel]
```

**示例** (矩形 {10, 20, 30, 40}):
```
[20]           // Top
[40, 1, 10, 30, 0x7FFFFFFF]  // Bottom, 1个区间, Left, Right, X-哨兵
[0x7FFFFFFF]   // Y-哨兵
```

### 写时复制机制

**引用计数管理**:
```cpp
bool setRegion(const SkRegion& src) {
    fRunHead = src.fRunHead;
    if (this->isComplex()) {
        fRunHead->fRefCnt++;  // 增加引用计数
    }
}
```

**写入时复制**:
```cpp
RunHead* ensureWritable() {
    if (fRefCnt > 1) {
        // 复制数据并减少原引用计数
        RunHead* writable = Alloc(...);
        memcpy(writable->writable_runs(), this->readonly_runs(), ...);
        if (--fRefCnt == 0) {
            sk_free(this);
        }
        return writable;
    }
    return this;
}
```

### 集合运算实现

**operate 函数核心逻辑**:

1. **扫描线合并**: 同时遍历两个区域的扫描线
2. **区间求交**: 使用 `spanRec` 计算两个扫描线的区间交集
3. **根据操作类型过滤**:
   - Difference: 保留 A 独有部分 (inside == 1)
   - Intersect: 保留交集 (inside == 3)
   - Union: 保留所有 (inside == 1, 2, 3)
   - XOR: 保留非交集 (inside == 1, 2)

**优化**:
- **快速路径**: 矩形与矩形运算直接计算
- **空区域检测**: 提前返回
- **边界检查**: 通过 bounds 快速排除不相交情况

### setPath 实现

**核心流程**:

1. **路径遍历**: 使用 `count_path_runtype_values` 计算边数和边界
2. **分块处理**: 大坐标范围时分块 (32767x32767) 处理,避免 SkFixed 溢出
3. **扫描转换**: 调用 `SkScan::FillPath` 将路径光栅化到 `SkRgnBuilder`
4. **游程构建**: `SkRgnBuilder::blitH` 记录每个水平线段
5. **合并优化**: 相邻相同扫描线自动合并

**SkRgnBuilder 机制**:
- 动态构建游程数组
- 使用 `collapsWithPrev()` 合并连续相同扫描线
- 最终调用 `copyToRgn()` 生成标准游程格式

### getBoundaryPath 实现

**算法步骤**:

1. **边提取**: 每个矩形生成左边 (上→下) 和右边 (下→上)
2. **边排序**: 按 X 坐标排序,相同 X 按 Y 排序
3. **边链接**: 通过 `find_link()` 连接 Y 坐标匹配的边
4. **路径提取**: `extract_path()` 遍历边链生成闭合路径

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkIRect | 矩形表示 |
| SkPath | 路径转换 |
| SkScan | 路径扫描转换 |
| SkBlitter | 光栅化回调 |
| SkRegionPriv | 内部工具函数 |
| SkBuffer | 序列化支持 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| SkCanvas | 裁剪栈管理 |
| SkDraw | 光栅化裁剪 |
| SkAAClip | 抗锯齿裁剪 |
| SkPath | 路径裁剪 |

## 设计模式与设计决策

### 写时复制 (Copy-on-Write)

**优点**:
- 拷贝操作 O(1) 时间复杂度
- 节省内存,多个 SkRegion 共享数据

**实现**:
- 引用计数 + `ensureWritable()` 检查

### 三态表示

**状态类型**:
1. **Empty**: `fRunHead = -1`, `fBounds.isEmpty()`
2. **Rect**: `fRunHead = nullptr`, `fBounds` 包含矩形
3. **Complex**: `fRunHead` 指向游程数据

**优点**:
- 矩形区域零额外内存开销
- 常见情况 (矩形裁剪) 极快

### 迭代器模式

提供三种迭代器:
- **Iterator**: 遍历所有矩形
- **Cliperator**: 遍历与裁剪矩形的交集
- **Spanerator**: 遍历指定扫描线的水平段

### 设计权衡

1. **整数坐标**: 避免浮点精度问题,适合像素级操作
2. **游程编码**: 空间效率 vs 随机访问性能
3. **写时复制**: 内存节省 vs 原子操作开销

## 性能考量

### 内存效率

- **空区域**: 16 字节 (fBounds + fRunHead)
- **矩形区域**: 16 字节 (无额外分配)
- **复杂区域**: ~40 字节固定开销 + 游程数据

### 操作复杂度

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| isEmpty/isRect | O(1) | 检查指针值 |
| contains(point) | O(log h + w) | 二分查找扫描线 + 线性扫区间 |
| op(rect, rect) | O(1) | 快速路径 |
| op(complex, complex) | O(n + m) | n, m 为区间数 |
| setPath | O(edges) | 扫描转换开销 |

### 优化策略

1. **快速路径**: `quickContains`, `quickReject` 仅检查 bounds
2. **矩形特化**: 矩形运算避免游程编码
3. **扫描线合并**: 相同扫描线自动合并,减少存储
4. **引用计数**: 避免不必要的内存拷贝

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| include/core/SkRegion.h | 公共 API 头文件 |
| src/core/SkRegion.cpp | 核心实现 |
| src/core/SkRegion_path.cpp | 路径转换实现 |
| src/core/SkRegionPriv.h | 内部数据结构 |
| src/core/SkScan.h | 扫描转换接口 |
| src/core/SkBlitter.h | 光栅化回调 |
| include/core/SkPath.h | 路径类 |
