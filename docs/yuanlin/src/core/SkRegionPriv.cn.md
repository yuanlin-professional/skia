# SkRegionPriv

> 源文件
> - src/core/SkRegionPriv.h

## 概述

`SkRegionPriv` 是 SkRegion 模块的私有辅助头文件,定义了 SkRegion 内部使用的数据结构、常量和工具函数。该文件包含游程编码 (Run-Length Encoding) 的核心数据结构 `RunHead`,以及用于遍历和验证区域数据的内部接口。作为私有 API,它向 Skia 内部模块暴露 SkRegion 的实现细节,但不对外部用户开放。

## 架构位置

`SkRegionPriv` 位于 SkRegion 模块的私有实现层:
- **使用者**: SkRegion.cpp, SkRegion_path.cpp, SkScan (内部模块)
- **依赖**: SkRegion (公共头文件), SkMalloc, SkMath, SkTo
- **层级**: SkRegion 内部实现细节,不属于公共 API

## 主要类与结构体

### SkRegionPriv

纯静态工具类,提供私有工具方法。

**继承关系**:
```
SkRegionPriv (纯静态类,无继承)
```

**关键常量**:

| 常量 | 值 | 说明 |
|------|-----|------|
| kRunTypeSentinel | 0x7FFFFFFF | 游程数组哨兵值 (INT32_MAX) |

**类型别名**:

| 别名 | 实际类型 | 说明 |
|------|---------|------|
| RunType | SkRegion::RunType | 游程数据类型 (int32_t) |
| RunHead | SkRegion::RunHead | 游程头结构体 |

### SkRegion::RunHead

管理复杂区域的游程编码数据头。

**关键成员变量**:

| 变量 | 类型 | 说明 |
|------|------|------|
| fRefCnt | std::atomic&lt;int32_t&gt; | 引用计数 (支持写时复制) |
| fRunCount | int32_t | 游程数组总长度 |
| fYSpanCount | int32_t | Y 方向扫描线数量 (不含哨兵) |
| fIntervalCount | int32_t | X 方向区间总数 (矩形总数) |

## 公共 API 函数

### SkRegionPriv 工具方法

```cpp
static void VisitSpans(const SkRegion& rgn, const std::function<void(const SkIRect&)>& visitor)
```

**功能**: 遍历区域的所有扫描线段,按 Y → X 顺序调用访问函数。

**保证**:
- 矩形按 Y 坐标升序
- 同一 Y 坐标的矩形按 X 坐标升序
- 传递的矩形高度可能为 1 (单扫描线)

```cpp
#ifdef SK_DEBUG
static void Validate(const SkRegion& rgn)
#endif
```

调试版本的区域验证函数,检查游程数据完整性。

### RunHead 静态工厂方法

```cpp
static RunHead* Alloc(int count)
```

**功能**: 分配指定游程数量的 RunHead。

**参数**:
- `count`: 游程数组长度 (至少 `kRectRegionRuns` = 7)

**返回**: 分配的 RunHead 指针,失败返回 nullptr。

```cpp
static RunHead* Alloc(int count, int ySpanCount, int intervalCount)
```

**功能**: 分配并初始化元数据的 RunHead。

**验证**:
- `ySpanCount > 0` (至少一个扫描线)
- `intervalCount > 1` (至少一个矩形)

### RunHead 实例方法

```cpp
int getYSpanCount() const
int getIntervalCount() const
```

获取扫描线数量和区间数量。

```cpp
RunType* writable_runs()
const RunType* readonly_runs() const
```

访问游程数组 (位于 RunHead 后面的内存)。

```cpp
RunHead* ensureWritable()
```

**功能**: 确保 RunHead 可写,必要时执行写时复制。

**实现**:
```cpp
if (fRefCnt > 1) {
    // 分配新的 RunHead
    RunHead* writable = Alloc(fRunCount, fYSpanCount, fIntervalCount);
    memcpy(writable->writable_runs(), this->readonly_runs(), ...);
    // 减少原引用计数,必要时释放
    if (--fRefCnt == 0) {
        sk_free(this);
    }
    return writable;
}
return this;
```

```cpp
RunType* findScanline(int y) const
```

**功能**: 查找包含指定 Y 坐标的扫描线。

**返回**: 指向扫描线起始位置的指针 `[Bottom, IntervalCount, ...]`。

**假设**: Y 坐标已验证在区域边界内。

```cpp
static RunType* SkipEntireScanline(const RunType runs[])
```

**功能**: 跳过整条扫描线,返回下一条扫描线的起始位置。

**布局**:
```
[Bottom, IntervalCount, [Left1, Right1], ..., Sentinel] → 下一条扫描线
```

```cpp
void computeRunBounds(SkIRect* bounds)
```

**功能**: 从游程数组计算区域边界和元数据。

**计算内容**:
- `bounds`: 区域包围盒
- `fYSpanCount`: 扫描线数量
- `fIntervalCount`: 区间总数

## 内部实现细节

### RunHead 内存布局

**结构**:
```
+-------------------+
| RunHead           |
|  - fRefCnt        |  4 字节
|  - fRunCount      |  4 字节
|  - fYSpanCount    |  4 字节
|  - fIntervalCount |  4 字节
+-------------------+
| RunType[] (fRunCount) |
+-------------------+
```

**对齐**: 自然对齐 (4 字节)

### Alloc 分配计算

```cpp
const int64_t size = sk_64_mul(count, sizeof(RunType)) + sizeof(RunHead);
if (count < 0 || !SkTFitsIn<int32_t>(size)) {
    SK_ABORT("Invalid Size");
}
```

**溢出检查**:
- 使用 64 位中间值避免溢出
- 验证结果可表示为 int32_t

### findScanline 二分查找

**算法** (线性搜索):
```cpp
const RunType* runs = this->readonly_runs();
runs += 1;  // 跳过 Top
for (;;) {
    int bottom = runs[0];
    if (y < bottom) {
        break;
    }
    runs = SkipEntireScanline(runs);
}
return runs;
```

**复杂度**: O(n),其中 n 为扫描线数量。

**优化空间**: 可改为二分查找 O(log n),但实际区域扫描线数量通常较小。

### computeRunBounds 实现

**遍历逻辑**:
```cpp
RunType* runs = this->writable_runs();
bounds->fTop = *runs++;  // 读取 Top

int ySpanCount = 0;
int intervalCount = 0;
int left = SK_MaxS32;
int rite = SK_MinS32;

do {
    int bot = *runs++;
    ySpanCount += 1;

    int intervals = *runs++;
    if (intervals > 0) {
        RunType L = runs[0];
        left = std::min(left, L);

        runs += intervals * 2;
        RunType R = runs[-1];
        rite = std::max(rite, R);

        intervalCount += intervals;
    }
    runs += 1;  // 跳过 X-哨兵
} while (*runs < SkRegion_kRunTypeSentinel);

fYSpanCount = ySpanCount;
fIntervalCount = intervalCount;
bounds->setLTRB(left, top, rite, bot);
```

### VisitSpans 实现

**矩形区域**:
```cpp
if (rgn.isRect()) {
    visitor(rgn.getBounds());
}
```

**复杂区域**:
```cpp
const int32_t* p = rgn.fRunHead->readonly_runs();
int32_t top = *p++;
int32_t bot = *p++;
do {
    int pairCount = *p++;
    if (pairCount == 1) {
        // 单区间,直接生成矩形
        visitor({ p[0], top, p[1], bot });
        p += 2;
    } else if (pairCount > 1) {
        // 多区间,逐行生成
        for (int y = top; y < bot; ++y) {
            for (int i = 0; i < pairCount; ++i) {
                visitor({ p[i*2], y, p[i*2+1], y+1 });
            }
        }
        p += pairCount * 2;
    }
    // 跳过 X-哨兵,读取下一个 Bottom
    p += 1;
    top = bot;
    bot = *p++;
} while (!SkRegionValueIsSentinel(bot));
```

**优化**:
- `pairCount == 1` 时生成单个高矩形,避免逐行迭代
- `pairCount > 1` 时才逐行展开

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkRegion | 公共头文件 (类定义) |
| SkMalloc | 内存分配 (sk_malloc_throw, sk_free) |
| SkMath | 数学工具 (sk_64_mul) |
| SkTo | 安全类型转换 (SkToInt, SkTFitsIn) |
| std::atomic | 原子引用计数 |
| std::functional | 函数对象 (VisitSpans) |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| SkRegion.cpp | 核心实现 |
| SkRegion_path.cpp | 路径转换实现 |
| SkScan | 扫描转换 (间接使用) |

## 设计模式与设计决策

### 引用计数 (Reference Counting)

**std::atomic<int32_t> fRefCnt**:
- 线程安全的引用计数
- 支持多个 SkRegion 共享同一份游程数据

**写时复制 (Copy-on-Write)**:
- `ensureWritable()` 检查引用计数
- `fRefCnt > 1` 时复制数据

### Opaque Pointer (不透明指针)

**RunHead 在公共 API 中是不透明的**:
- `SkRegion` 仅存储 `RunHead*`
- 内部结构对外隐藏

### 内存池化 (Memory Pooling)

**不使用内存池**:
- 每次分配都通过 `sk_malloc_throw`
- 简化内存管理,避免池化复杂性

**权衡**: 牺牲分配速度换取简单性和内存回收及时性。

### 设计权衡

1. **线性搜索 vs 二分查找**:
   - `findScanline` 使用线性搜索
   - 原因: 实际扫描线数量通常较小 (< 100)

2. **内联 vs 函数调用**:
   - `SkipEntireScanline` 声明为 static 但未内联
   - 避免头文件膨胀

3. **验证 vs 性能**:
   - `Validate` 仅在 DEBUG 模式启用
   - Release 模式无额外开销

## 性能考量

### 内存访问模式

**游程数据紧凑性**:
- 所有数据连续存储
- 缓存友好,减少 cache miss

**引用计数原子性**:
- `std::atomic` 确保线程安全
- 代价: 每次引用计数操作需要内存屏障

### 时间复杂度

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| Alloc | O(1) | 单次分配 |
| ensureWritable | O(n) | 需要复制时 |
| findScanline | O(h) | h = 扫描线数量 |
| SkipEntireScanline | O(1) | 指针跳跃 |
| computeRunBounds | O(n) | 遍历所有游程 |
| VisitSpans | O(r) | r = 矩形总数 |

### 优化策略

**VisitSpans 优化**:
- 单区间扫描线生成高矩形,避免逐行迭代
- 减少函数调用次数

**内存对齐**:
- RunHead 自然对齐 (4 字节)
- 无额外填充字节

**引用计数优化**:
- 拷贝构造仅增加引用计数
- 延迟到写入时才复制数据

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| include/core/SkRegion.h | 公共 SkRegion API |
| src/core/SkRegion.cpp | 核心实现 |
| src/core/SkRegion_path.cpp | 路径转换实现 |
| include/private/base/SkMalloc.h | 内存分配接口 |
| include/private/base/SkMath.h | 数学工具 |
| include/private/base/SkTo.h | 类型转换工具 |
