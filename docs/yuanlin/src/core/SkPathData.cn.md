# SkPathData

> 源文件
> - src/core/SkPathData.h
> - src/core/SkPathData.cpp

## 概述

`SkPathData` 是 Skia 路径系统的核心不可变数据容器,负责存储路径的几何数据(点、动词、圆锥权重)以及相关元数据(边界、分段掩码)。该类是 Skia 2.0+ 路径架构的基础,支持高效的数据共享和缓存。

作为引用计数的不可变对象,`SkPathData` 确保多个 `SkPath` 实例可以安全共享相同的几何数据,避免不必要的数据拷贝。该类还集成了数据验证、边界计算、形状识别等功能,为上层路径操作提供可靠的数据基础。

## 架构位置

`SkPathData` 位于 Skia 路径系统的核心层:

```
include/core/
├── SkPath (公共路径接口)
└── SkPathTypes (路径类型定义)

src/core/
├── SkPathData (路径数据容器) ← 当前组件
├── SkPathPriv (路径私有辅助)
├── SkPathBuilder (路径构建器)
└── SkPathRaw (原始数据视图)
```

数据流:
```
SkPathBuilder → SkPathData → SkPath
     ↓              ↓            ↓
   构建         存储共享      公共接口
```

## 主要类与结构体

### SkPathData 类

**继承关系**:
```
SkNVRefCnt<SkPathData> (非虚引用计数基类)
    ↑
SkPathData
```

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fPoints | SkSpan<SkPoint> | 路径点数组(紧凑存储) |
| fVerbs | SkSpan<SkPathVerb> | 动词数组 |
| fConics | SkSpan<float> | 圆锥曲线权重数组 |
| fBounds | SkRect | 路径边界矩形 |
| fUniqueID | uint32_t | 唯一标识符(用于缓存) |
| fConvexity | std::atomic<uint8_t> | 凸性(惰性计算) |
| fSegmentMask | uint8_t | 分段类型掩码 |
| fType | SkPathIsAType | 特殊形状类型 |
| fIsA | SkPathIsAData | 形状元数据(方向、起点) |
| fGenIDChangeListeners | SkIDChangeListener::List | GenID 监听器列表 |

**内存布局**:
```
[SkPathData对象]
[SkPoint数据]
[float圆锥权重数据]
[SkPathVerb数据]
```
所有数据在单次分配中紧凑存储。

## 公共 API 函数

### 工厂方法

```cpp
// 空路径数据(单例)
static sk_sp<SkPathData> Empty();

// 从缓冲区创建(验证输入)
static sk_sp<SkPathData> Make(
    SkSpan<const SkPoint> pts,
    SkSpan<const SkPathVerb> verbs,
    SkSpan<const float> conics = {});

// 变换创建
static sk_sp<SkPathData> MakeTransform(
    const SkPathRaw& src,
    const SkMatrix& matrix);

// 标准形状
static sk_sp<SkPathData> Rect(
    const SkRect&,
    SkPathDirection = SkPathDirection::kDefault,
    unsigned startIndex = 0);

static sk_sp<SkPathData> Oval(
    const SkRect&,
    SkPathDirection = SkPathDirection::kDefault,
    unsigned startIndex = 1);

static sk_sp<SkPathData> RRect(
    const SkRRect&,
    SkPathDirection,
    unsigned startIndex);

static sk_sp<SkPathData> Polygon(
    SkSpan<const SkPoint> pts,
    bool isClosed);

static sk_sp<SkPathData> Line(SkPoint a, SkPoint b);
```

### 数据访问

```cpp
// 几何数据
SkSpan<const SkPoint> points() const;
SkSpan<const SkPathVerb> verbs() const;
SkSpan<const float> conics() const;

// 元数据
const SkRect& bounds() const;
uint8_t segmentMask() const;
uint32_t uniqueID() const;
bool empty() const;
```

### 几何查询

```cpp
// 凸性判断
bool isConvex() const;

// 形状识别
std::optional<std::array<SkPoint, 2>> asLine() const;
std::optional<SkPathRectInfo> asRect() const;
std::optional<SkPathOvalInfo> asOval() const;
std::optional<SkPathRRectInfo> asRRect() const;
```

### 变换和操作

```cpp
// 应用变换(返回新对象)
sk_sp<SkPathData> makeTransform(const SkMatrix&) const;
sk_sp<SkPathData> makeOffset(SkVector) const;

// 点包含测试
bool contains(SkPoint, SkPathFillType) const;

// 紧凑边界
SkRect computeTightBounds() const;
```

### GenID 监听

```cpp
// 添加 GenID 变更监听器
void addGenIDChangeListener(sk_sp<SkIDChangeListener>) const;

// 获取监听器数量
int genIDChangeListenerCount() const;
```

### 比较操作

```cpp
// 相等比较(逐点、逐动词比较)
friend bool operator==(const SkPathData& a, const SkPathData& b);
friend bool operator!=(const SkPathData& a, const SkPathData& b);
```

## 内部实现细节

### 数据验证

`valid_path_data` 函数执行严格的输入验证:

1. **动词序列规则**:
   - 必须以 kMove 开始(除非为空)
   - Move 后不能紧跟 Move
   - Close 后只能跟 Move
   - 所有动词值必须合法

2. **点数匹配**:
   ```
   Move  → 1点
   Line  → 1点
   Quad  → 2点
   Conic → 2点 + 1权重
   Cubic → 3点
   Close → 0点
   ```

3. **权重验证**: 所有圆锥权重必须 ≥0 且有限

### 内存分配策略

使用自定义分配器实现单次分配:

```cpp
SkPathData::SkPathData(size_t npts, size_t nvbs, size_t ncns) {
    // 计算总大小
    size_t total = sizeof(SkPathData)
                 + npts * sizeof(SkPoint)
                 + ncns * sizeof(float)
                 + nvbs * sizeof(SkPathVerb);

    // 单次分配,数据紧随对象
    void* storage = ::operator new(total);

    // 设置 Span 指向分配的内存
    auto data = reinterpret_cast<std::byte*>(this + 1);
    fPoints = {(SkPoint*)data, npts};
    data += fPoints.size_bytes();
    fConics = {(float*)data, ncns};
    data += fConics.size_bytes();
    fVerbs = {(SkPathVerb*)data, nvbs};
}
```

### UniqueID 生成

使用原子计数器生成全局唯一 ID:

```cpp
static uint32_t next_pathdata_unique_id() {
    static std::atomic<int32_t> nextID{1};
    uint32_t id;
    do {
        id = nextID.fetch_add(1, std::memory_order_relaxed);
        // 保留高2位用于 FillType
        id <<= 2;
        id >>= 2;
    } while (id == 0);  // 避免 ID 为 0
    return id;
}
```

### 凸性惰性计算

凸性使用原子变量存储,支持线程安全的惰性计算:

```cpp
SkPathConvexity SkPathData::getResolvedConvexity() const {
    auto convexity = fConvexity.load(std::memory_order_relaxed);
    if (convexity == SkPathConvexity::kUnknown) {
        // 计算并缓存
        convexity = SkPathPriv::ComputeConvexity(fPoints, fVerbs, fConics);
        fConvexity.store(convexity, std::memory_order_relaxed);
    }
    return convexity;
}
```

### 标准形状优化

特殊形状使用优化的构造路径:

```cpp
sk_sp<SkPathData> SkPathData::Oval(const SkRect& r, SkPathDirection dir, unsigned index) {
    // 使用 SkPathRawShapes 快速构造
    SkPathRawShapes::Oval raw(r, dir, index);
    auto path = MakeNoCheck(raw.points(), raw.verbs(), raw.conics(), ...);

    // 设置形状元数据
    path->setupIsA(SkPathIsAType::kOval, dir, index);
    return path;
}
```

### 变换处理

`makeTransform` 的优化策略:

1. **恒等变换**: 直接返回 `sk_ref_sp(this)`
2. **非透视变换**: 直接映射点,保留动词
3. **透视变换**: 通过 `SkPathBuilder` 处理(可能增加动词)
4. **形状保持**: 轴对齐矩形变换后可保持 IsA 信息

### 边界计算

`finishInit` 中的边界计算:

```cpp
bool SkPathData::finishInit(std::optional<SkRect> bounds, ...) {
    if (bounds.has_value()) {
        // 使用提供的边界(已验证有限性)
        fBounds = bounds.value().makeSorted();
    } else {
        // 计算边界并验证有限性
        if (auto r = SkPathPriv::TrimmedBounds(fPoints, fVerbs)) {
            fBounds = r.value();
        } else {
            return false;  // 非有限点
        }
    }
    return true;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkNVRefCnt | 引用计数基类 |
| SkPathPriv | 几何计算辅助 |
| SkPathRawShapes | 标准形状构造 |
| SkPathBuilder | 透视变换处理 |
| SkMatrix | 几何变换 |
| SkRRect | 圆角矩形 |
| SkIDChangeListener | GenID 监听器 |
| SkSafeMath | 安全算术运算 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| SkPath | 持有 SkPathData 实例 |
| SkPathBuilder | 生成 SkPathData |
| SkPathEffect | 路径效果处理 |
| 渲染管线 | 访问路径几何 |
| 缓存系统 | 使用 uniqueID |

## 设计模式与设计决策

### 不可变对象模式

`SkPathData` 一旦创建即不可修改:
- 所有公共接口返回 const 数据
- 变换操作返回新实例
- 支持安全的多线程共享
- 简化缓存和优化

### 写时复制(COW)

通过引用计数实现隐式共享:
```cpp
sk_sp<SkPathData> data1 = SkPathData::Rect(...);
SkPath path1(data1);  // 共享数据
SkPath path2(data1);  // 仍共享
// 修改需创建新 SkPathData
```

### 工厂方法模式

所有构造通过静态工厂方法:
- 隐藏构造细节
- 统一的验证和初始化
- 支持返回 nullptr 表示失败
- 便于实现单例(Empty)

### 惰性求值

凸性等昂贵计算延迟到首次访问:
```cpp
bool SkPathData::isConvex() const {
    return SkPathConvexity_IsConvex(
        this->getResolvedConvexity()  // 惰性计算
    );
}
```

### 数据局部性优化

单次分配紧凑存储:
- 减少内存碎片
- 提高缓存命中率
- 简化析构逻辑

### 类型安全的形状识别

使用 `std::optional` 和强类型:
```cpp
std::optional<SkPathOvalInfo> asOval() const;
// 而非: bool asOval(SkPathOvalInfo* out);
```

## 性能考量

### 内存效率

1. **紧凑布局**: 单次分配避免指针跳转
2. **空路径单例**: 避免重复分配空对象
3. **引用计数**: 避免不必要的数据拷贝

### 计算优化

1. **快速路径**: `asLine` 仅检查大小和动词
2. **边界缓存**: 边界在构造时计算并存储
3. **分段掩码**: O(1) 查询路径包含的曲线类型

### 变换优化

1. **恒等检测**: `makeTransform` 先检查恒等矩阵
2. **直接映射**: 非透视变换直接映射点
3. **形状保持**: 尽可能保留 IsA 优化信息

### 线程安全

1. **不可变性**: 避免锁开销
2. **原子凸性**: 使用 relaxed 原子操作
3. **监听器列表**: 线程安全的 add 操作

### 数值稳定性

1. **边界排序**: `makeSorted()` 处理 NaN
2. **有限性检查**: 构造时验证所有坐标
3. **安全算术**: 使用 `SkSafeMath` 避免溢出

### 空间优化

1. **位域**: fSegmentMask 使用 uint8_t
2. **枚举**: fType 和 fConvexity 紧凑存储
3. **可选分配**: 空路径不分配缓冲区

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| include/core/SkPath.h | 被使用 | 公共路径接口 |
| src/core/SkPathPriv.h | 使用 | 几何计算辅助 |
| src/core/SkPathBuilder.h | 配合 | 路径构建器 |
| src/core/SkPathRaw.h | 使用 | 原始数据视图 |
| src/core/SkPathEnums.h | 使用 | 枚举定义 |
| src/core/SkPathRawShapes.h | 使用 | 标准形状构造 |
| include/core/SkMatrix.h | 依赖 | 变换操作 |
| include/core/SkRRect.h | 依赖 | 圆角矩形 |
| include/private/SkIDChangeListener.h | 依赖 | GenID 监听 |
| src/base/SkSafeMath.h | 依赖 | 安全算术 |
