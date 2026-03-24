# SkOpSpan

> 源文件: src/pathops/SkOpSpan.h, src/pathops/SkOpSpan.cpp

## 概述

`SkOpSpan` 是 Skia PathOps 模块中表示曲线段上参数化点的核心数据结构。该模块定义了三个关键类:`SkOpPtT`(点-参数对)、`SkOpSpanBase`(基础 span)和 `SkOpSpan`(完整 span),它们共同构成了路径操作算法中用于表示和管理曲线交点、端点以及巧合边的基础设施。

在路径布尔运算中,每个曲线段被分割为多个 span,每个 span 代表曲线上的一段区间。Span 存储了绕组数(winding number)、对立值(opposite value)等关键信息,这些信息决定了在路径操作中如何处理该段曲线。PtT 则表示参数 t 和对应的点坐标的组合,并通过链表连接同一位置的多个交点(来自不同曲线段)。

这种设计允许算法高效地查找和遍历交点,处理巧合边(coincident edges),以及计算正确的绕组值,是整个 PathOps 系统的数据核心。

## 架构位置

`SkOpSpan` 在 PathOps 架构中处于数据层的核心位置:

```
操作层 (SkPathOpsOp, SkPathOpsSimplify)
    ↓
协调层 (SkPathOpsCommon)
    ↓
核心数据结构层
    ├─ SkOpContour (轮廓)
    ├─ SkOpSegment (线段)
    └─ SkOpSpan/SkOpSpanBase (参数点) ← 当前模块
        └─ SkOpPtT (点-参数对)
    ↓
几何计算层 (SkPathOpsCurve, SkPathOpsQuad, SkPathOpsCubic)
```

该模块是路径操作算法中最细粒度的数据单元,所有算法最终都通过操作这些 span 和 ptT 来实现。

## 主要类与结构体

### SkOpPtT (点-参数对)

表示曲线上一个参数化点,存储参数 t、对应的笛卡尔坐标点,以及与之相关的 span。多个来自不同曲线段的 PtT 通过循环链表连接,表示在同一位置的交点。

**核心成员变量:**
- `double fT`: 参数 t 值 (0 到 1)
- `SkPoint fPt`: 对应的笛卡尔坐标点
- `SkOpSpanBase* fSpan`: 所属的 span
- `SkOpPtT* fNext`: 链表中的下一个 PtT
- `bool fDeleted`: 标记是否已删除
- `bool fDuplicatePt`: 标记是否存在重复点
- `bool fCoincident`: 标记是否被巧合 span 引用

**关键枚举:**
```cpp
enum {
    kIsAlias = 1,
    kIsDuplicate = 1
};
```

### SkOpSpanBase (基础 Span)

表示曲线段上的一个参数点,是 span 链表的基类。可以是中间点(SkOpSpan)或终点(t=1)。

**核心成员变量:**
- `SkOpPtT fPtT`: 主要的点-参数对
- `SkOpSegment* fSegment`: 所属的线段
- `SkOpSpanBase* fCoinEnd`: 巧合端点循环链表
- `SkOpAngle* fFromAngle`: 从该点出发的角度
- `SkOpSpan* fPrev`: 前一个 span
- `int fSpanAdds`: 交点添加计数
- `bool fAligned`: 是否对齐
- `bool fChased`: 是否已添加到追踪数组

**核心嵌套枚举:**
```cpp
enum class Collapsed {
    kNo,      // 未折叠
    kYes,     // 已折叠
    kError,   // 检测错误
};
```

### SkOpSpan (完整 Span)

继承自 SkOpSpanBase,表示非终点(t<1)的参数点,包含完整的绕组信息和巧合链表。

**核心成员变量:**
- `SkOpSpan* fCoincident`: 巧合 span 循环链表
- `SkOpAngle* fToAngle`: 到下一个点的角度
- `SkOpSpanBase* fNext`: 下一个 span
- `int fWindSum`: 累积的绕组和
- `int fOppSum`: 对立绕组和(用于二元运算)
- `int fWindValue`: 绕组值(0=已取消, 1=正常, >1=巧合)
- `int fOppValue`: 对立绕组值
- `int fTopTTry`: 指定下一次尝试的方向和 t 值
- `bool fDone`: 是否已处理
- `bool fAlreadyAdded`: 是否已添加

## 公共 API 函数

### SkOpPtT 主要方法

#### active
```cpp
const SkOpPtT* active() const
```
返回未删除的活动 PtT。如果当前 PtT 已删除,则在链表中查找同一 span 的未删除 PtT。

#### contains
```cpp
bool contains(const SkOpPtT*) const
bool contains(const SkOpSegment*, const SkPoint&) const
bool contains(const SkOpSegment*, double t) const
const SkOpPtT* contains(const SkOpSegment*) const
```
检查 PtT 循环链表中是否包含指定的 PtT、线段+点、线段+参数或线段。用于查找交点和避免重复添加。

#### addOpp
```cpp
void addOpp(SkOpPtT* opp, SkOpPtT* oppPrev)
```
将对立线段的 PtT 添加到当前链表。该方法将两个不同线段的交点通过 PtT 链表连接起来。

#### Overlaps (静态)
```cpp
static bool Overlaps(const SkOpPtT* s1, const SkOpPtT* e1,
                     const SkOpPtT* s2, const SkOpPtT* e2,
                     const SkOpPtT** sOut, const SkOpPtT** eOut)
```
判断两个 PtT 范围是否重叠,并返回重叠的起点和终点。用于巧合检测。

#### insert
```cpp
void insert(SkOpPtT* span)
```
将新的 PtT 插入到循环链表中。

#### oppPrev
```cpp
SkOpPtT* oppPrev(const SkOpPtT* opp) const
```
查找指向 opp 的前驱 PtT。用于在添加对立点时维护链表结构。

### SkOpSpanBase 主要方法

#### addOpp
```cpp
bool addOpp(SkOpSpanBase* opp)
```
添加对立 span。该方法将两个不同线段的 span 连接起来,并调用 `mergeMatches` 合并匹配的 PtT。

#### collapsed
```cpp
Collapsed collapsed(double s, double e) const
```
检查 PtT 链表是否在参数范围 [s, e] 内折叠(所有 t 值都在该范围内)。

#### contains
```cpp
bool contains(const SkOpSpanBase*) const
const SkOpPtT* contains(const SkOpSegment*) const
```
检查 PtT 链表中是否包含指定的 span 或线段。

#### insertCoinEnd
```cpp
void insertCoinEnd(SkOpSpanBase* coin)
```
将巧合端点插入循环链表。用于建立巧合边的双向链接。

#### merge
```cpp
void merge(SkOpSpan* span)
```
合并两个共享相同 t 值或点的 span。将 span 的所有 PtT 数据移动到当前 span,并消除重复项。

#### mergeMatches
```cpp
bool mergeMatches(SkOpSpanBase* opp)
```
检查 PtT 链表中是否有相同线段的多个引用,如果有则合并它们。防止同一线段有多个 span 指向 PtT 循环链表的不同元素。

#### checkForCollapsedCoincidence
```cpp
void checkForCollapsedCoincidence()
```
检查折叠的巧合。当插入操作可能将巧合运行的两端放入同一 span 时调用。

#### starter
```cpp
const SkOpSpan* starter(const SkOpSpanBase* end) const
SkOpSpan* starter(SkOpSpanBase* end)
SkOpSpan* starter(SkOpSpanBase** endPtr)
```
返回两个 span 中 t 值较小的那个(作为起始点)。第三个版本还会调整 endPtr 指向 t 值较大的 span。

#### upCast
```cpp
SkOpSpan* upCast()
const SkOpSpan* upCast() const
```
将 SkOpSpanBase 向上转换为 SkOpSpan。要求 span 不是终点(t != 1)。

### SkOpSpan 主要方法

#### computeWindSum
```cpp
int computeWindSum()
```
计算绕组和。通过查找可排序的顶部 span 来计算绕组值,最多尝试 `kMaxWindingTries` 次。

#### containsCoincidence
```cpp
bool containsCoincidence(const SkOpSegment*) const
bool containsCoincidence(const SkOpSpan*) const
```
检查巧合循环链表中是否包含指定的线段或 span。

#### insertCoincidence
```cpp
void insertCoincidence(SkOpSpan* coin)
bool insertCoincidence(const SkOpSegment*, bool flipped, bool ordered)
```
将巧合 span 插入循环链表。第一个版本直接插入 span,第二个版本根据线段和标志查找并插入。

#### clearCoincident
```cpp
bool clearCoincident()
```
清除巧合链表,将 fCoincident 指向自身。

#### release
```cpp
void release(const SkOpPtT* kept)
```
释放 span,将其从双向链表中移除,并将所有引用重定向到 kept 所属的 span。

#### setWindSum / setOppSum
```cpp
void setWindSum(int windSum)
void setOppSum(int oppSum)
```
设置绕组和或对立绕组和。如果值不一致,会设置全局状态的绕组失败标志。

#### isCanceled
```cpp
bool isCanceled() const
```
检查 span 是否被取消(windValue 和 oppValue 都为 0)。

#### isCoincident
```cpp
bool isCoincident() const
```
检查 span 是否为巧合(fCoincident 不指向自身)。

## 内部实现细节

### PtT 循环链表结构

PtT 使用单向循环链表组织,每个 PtT 通过 fNext 指针连接。在初始化时,fNext 指向自身:
```cpp
void SkOpPtT::init(SkOpSpanBase* span, double t, const SkPoint& pt, bool duplicate) {
    fNext = this;  // 初始化为自环
    // ...
}
```

当添加交点时,多个 PtT 被链接到同一个循环中,表示来自不同线段的交点在同一位置。

### Span 双向链表结构

Span 通过 fPrev 和 fNext 形成双向链表,表示曲线段上按参数 t 排序的点序列:
```
SkOpSegment → [head] ← → [span1] ← → [span2] ← → ... ← → [tail]
```

其中 head 的 t=0,tail 的 t=1。

### 巧合循环链表

巧合的 span 通过两种链表连接:
1. **fCoincident**: SkOpSpan 的巧合 span 循环链表
2. **fCoinEnd**: SkOpSpanBase 的巧合端点循环链表

这两个链表在不同层次上管理巧合关系,fCoincident 用于标记巧合的中间 span,fCoinEnd 用于标记巧合的端点。

### 合并算法

`merge` 方法实现了复杂的 PtT 合并逻辑:
1. 将 span 的第一个 PtT 插入到当前 span
2. 遍历 span 的剩余 PtT
3. 对每个 PtT,检查当前循环中是否已有相同 span 和 t 值的 PtT
4. 如果没有重复,则插入;否则跳过

这确保了合并后的 PtT 循环中没有重复项。

### 折叠检测

`collapsed` 方法检测 PtT 循环是否在参数范围内折叠:
- 遍历所有属于同一线段的 PtT
- 记录 t 值的最小值和最大值
- 如果 [min, max] 包含 [s, e],则认为折叠

使用安全计数器(100000)防止无限循环。

### 绕组值一致性检查

`setWindSum` 和 `setOppSum` 在设置值时检查一致性:
```cpp
if (fWindSum != SK_MinS32 && fWindSum != windSum) {
    this->globalState()->setWindingFailed();  // 标记失败
}
```

这确保了算法中绕组值的计算是一致的,不一致表示算法错误。

## 依赖关系

### 头文件依赖
- `include/core/SkPoint.h`: 点坐标类型
- `include/core/SkTypes.h`: Skia 核心类型
- `include/private/base/SkDebug.h`: 调试宏
- `include/private/base/SkMath.h`: 数学工具
- `src/pathops/SkPathOpsTypes.h`: PathOps 类型定义
- `include/private/base/SkTemplates.h`: 模板工具
- `src/pathops/SkOpCoincidence.h`: 巧合处理
- `src/pathops/SkOpContour.h`: 轮廓类
- `src/pathops/SkOpSegment.h`: 线段类

### 类依赖
- **SkOpSegment**: Span 所属的线段
- **SkOpAngle**: 与 span 关联的角度信息
- **SkOpContour**: 通过 segment 访问的轮廓
- **SkOpCoincidence**: 巧合检测和修复
- **SkOpGlobalState**: 全局状态和 ID 生成

## 设计模式与设计决策

### 继承设计

采用基类-派生类设计:
- `SkOpSpanBase`: 基类,可以表示终点(t=1)
- `SkOpSpan`: 派生类,表示非终点(t<1),包含额外的绕组信息

这种设计节省了内存(终点不需要 next 指针和绕组信息),同时保持了类型安全。

### 循环链表设计

使用循环链表而非数组的原因:
1. **动态插入**: 可以在任意位置高效插入新的交点
2. **遍历便利**: 可以从任意点开始遍历所有相关的 PtT
3. **空间效率**: 不需要预先分配固定大小的数组

### 双重引用设计

每个 PtT 既引用 span(通过 fSpan),span 又包含一个 PtT(fPtT):
- PtT 是轻量级的,可以在循环链表中有多个副本
- Span 是重量级的,只有一个主 PtT
- 这种设计允许从任意 PtT 快速访问 span,同时保持数据的一致性

### 懒删除策略

使用 fDeleted 标志而不是立即删除:
- 避免在遍历过程中修改链表结构
- 允许在遍历完成后批量删除
- 简化了并发或递归场景的处理

### 安全计数器

在多个循环中使用安全计数器(如 `collapsed` 中的 100000):
- 防止数据结构损坏导致的无限循环
- 在 Release 版本中提供故障保护
- 帮助调试时快速发现问题

### 调试支持

大量使用条件编译的调试代码:
- `SkDEBUGCODE()`: 只在 Debug 模式编译
- `SkOPASSERT()`: PathOps 特定的断言
- 每个对象有唯一的 fID 用于调试跟踪

## 性能考量

### 内存布局优化

成员变量按使用频率和对齐要求排列:
- 热路径变量(如 fT, fPt)在前
- 调试变量在 `SkDEBUGCODE` 宏中,Release 版本不占空间
- 布尔标志紧密排列,减少内存浪费

### 循环链表遍历优化

使用 do-while 循环减少条件判断:
```cpp
const SkOpPtT* walk = start;
do {
    // 处理
} while ((walk = walk->next()) != start);
```

### 早期退出

在 `contains` 等搜索方法中,找到目标立即返回,避免不必要的遍历。

### 引用返回

大量使用引用返回(如 `const SkPoint& pt()`)避免拷贝:
```cpp
const SkPoint& pt() const {
    return fPtT.fPt;  // 返回引用,不拷贝
}
```

### 内联候选

小型方法定义在头文件中,编译器可以内联:
- `t()`, `pt()`, `segment()` 等访问器
- `final()`, `simple()` 等状态检查

### 避免虚函数

尽管有继承关系,但不使用虚函数:
- 使用显式的 `upCast()` 进行类型转换
- 避免了虚函数表的开销
- 保持了内存布局的紧凑性

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/pathops/SkOpSegment.h/cpp` | 被依赖 | Span 所属的线段,管理 span 链表 |
| `src/pathops/SkOpAngle.h/cpp` | 依赖 | 角度信息,用于路径遍历 |
| `src/pathops/SkOpContour.h/cpp` | 依赖 | 通过 segment 访问的轮廓 |
| `src/pathops/SkOpCoincidence.h/cpp` | 依赖 | 巧合检测和修复,调用 span 的方法 |
| `src/pathops/SkPathOpsCommon.h/cpp` | 被依赖 | 使用 span 进行路径操作 |
| `src/pathops/SkPathOpsTypes.h` | 依赖 | 类型定义和常量(如 SK_MinS32) |
| `include/core/SkPoint.h` | 依赖 | 点坐标类型 |
| `src/pathops/SkPathOpsDebug.h/cpp` | 相关 | 调试和验证工具 |
| `include/private/base/SkMath.h` | 依赖 | 数学工具(如 between, zero_or_one) |
| `include/private/base/SkTemplates.h` | 依赖 | 模板工具 |
