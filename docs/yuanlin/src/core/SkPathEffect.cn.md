# SkPathEffect

> 源文件
> - include/core/SkPathEffect.h
> - src/core/SkPathEffect.cpp

## 概述

`SkPathEffect` 是 Skia 路径效果系统的抽象基类,定义了在路径绘制前对其进行几何变换的接口。路径效果可以实现虚线、箭头、波浪线等各种特殊绘制效果,是 Skia 绘制管线中的重要组件。

该类采用可扁平化设计,支持序列化和反序列化,可用于跨进程传输绘制状态。Skia 提供了多种内置路径效果实现,也支持用户自定义效果。

## 架构位置

`SkPathEffect` 位于 Skia 核心绘制层的效果子系统:

```
include/core/
├── SkPaint (绘制属性)
├── SkPathEffect (路径效果基类) ← 当前组件
├── SkPath (路径对象)
└── SkFlattenable (序列化基类)

src/core/
├── SkPathEffect.cpp (基础实现)
├── SkPathEffectBase.h (内部基类)
└── effects/
    ├── SkDashPathEffect (虚线效果)
    ├── SkDiscretePathEffect (离散效果)
    └── ... (其他效果实现)
```

绘制流程:
```
SkPath (原始路径)
    ↓
SkPathEffect::filterPath (应用效果)
    ↓
SkPath (变换后路径)
    ↓
SkCanvas::drawPath (绘制)
```

## 主要类与结构体

### SkPathEffect 类

**继承关系**:
```
SkFlattenable (序列化基类)
    ↑
SkPathEffect
    ↑
    ├── SkDashPathEffect
    ├── SkDiscretePathEffect
    ├── SkComposePathEffect
    ├── SkSumPathEffect
    └── ... (其他效果)
```

**关键方法**:

| 方法类型 | 方法签名 | 说明 |
|---------|---------|------|
| 工厂方法 | MakeSum / MakeCompose | 创建组合效果 |
| 核心接口 | filterPath | 应用效果到路径 |
| 查询接口 | needsCTM | 是否需要坐标变换矩阵 |
| 序列化 | Deserialize | 从数据反序列化 |

### SkComposePathEffect 类

组合路径效果,串联应用两个效果。

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fPE0 | sk_sp<SkPathEffect> | 外层效果 |
| fPE1 | sk_sp<SkPathEffect> | 内层效果 |

**语义**: `result = outer(inner(path))`

### SkSumPathEffect 类

求和路径效果,并联应用两个效果。

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fPE0 | sk_sp<SkPathEffect> | 第一个效果 |
| fPE1 | sk_sp<SkPathEffect> | 第二个效果 |

**语义**: `result = first(path) + second(path)`

## 公共 API 函数

### 工厂方法

```cpp
// 创建求和效果(并联)
static sk_sp<SkPathEffect> MakeSum(
    sk_sp<SkPathEffect> first,
    sk_sp<SkPathEffect> second);

// 创建组合效果(串联)
static sk_sp<SkPathEffect> MakeCompose(
    sk_sp<SkPathEffect> outer,
    sk_sp<SkPathEffect> inner);
```

**MakeSum**:
- 对路径同时应用两个效果
- 结果是两个效果输出的并集
- 如果某个参数为空,返回另一个

**MakeCompose**:
- 先应用 inner,再对结果应用 outer
- 如果某个参数为空,返回另一个
- 支持效果链式组合

### 核心接口

```cpp
// 应用效果到路径
bool filterPath(SkPathBuilder* dst,
                const SkPath& src,
                SkStrokeRec* rec,
                const SkRect* cullR,
                const SkMatrix& ctm) const;

// 简化版本(无裁剪矩形和CTM)
bool filterPath(SkPathBuilder* dst,
                const SkPath& src,
                SkStrokeRec* rec) const;
```

**参数**:
- `dst`: 输出路径构建器
- `src`: 输入路径
- `rec`: 描边记录(可修改)
- `cullR`: 裁剪矩形(可选)
- `ctm`: 当前变换矩阵

**返回值**:
- true: 成功应用效果
- false: 无法应用效果(使用原路径)

### 查询接口

```cpp
// 是否需要坐标变换矩阵
bool needsCTM() const;

// 获取类型标识
static SkFlattenable::Type GetFlattenableType();
```

### 序列化

```cpp
// 从数据反序列化路径效果
static sk_sp<SkPathEffect> Deserialize(
    const void* data,
    size_t size,
    const SkDeserialProcs* procs = nullptr);
```

## 内部实现细节

### filterPath 委托

```cpp
bool SkPathEffect::filterPath(
    SkPathBuilder* dst,
    const SkPath& src,
    SkStrokeRec* rec) const
{
    // 调用完整版本,传递空裁剪和恒等矩阵
    return this->filterPath(dst, src, rec, nullptr, SkMatrix::I());
}

bool SkPathEffect::filterPath(
    SkPathBuilder* dst,
    const SkPath& src,
    SkStrokeRec* rec,
    const SkRect* bounds,
    const SkMatrix& ctm) const
{
    // 委托给内部虚函数
    return as_PEB(this)->onFilterPath(dst, src, rec, bounds, ctm);
}
```

### needsCTM 实现

```cpp
bool SkPathEffect::needsCTM() const {
    return as_PEB(this)->onNeedsCTM();
}
```

默认实现返回 false,需要 CTM 的效果需重写 `onNeedsCTM()`。

### SkComposePathEffect 实现

```cpp
bool SkComposePathEffect::onFilterPath(
    SkPathBuilder* builder,
    const SkPath& src,
    SkStrokeRec* rec,
    const SkRect* cullRect,
    const SkMatrix& ctm) const
{
    SkPath tmp;
    const SkPath* ptr = &src;

    // 先应用内层效果
    if (fPE1->filterPath(builder, src, rec, cullRect, ctm)) {
        tmp = builder->detach();
        ptr = &tmp;
    }

    // 再应用外层效果
    return fPE0->filterPath(builder, *ptr, rec, cullRect, ctm);
}
```

### SkSumPathEffect 实现

```cpp
bool SkSumPathEffect::onFilterPath(
    SkPathBuilder* builder,
    const SkPath& src,
    SkStrokeRec* rec,
    const SkRect* cullRect,
    const SkMatrix& ctm) const
{
    // 两个效果都调用,即使第一个成功也继续
    bool filteredFirst = fPE0->filterPath(builder, src, rec, cullRect, ctm);
    bool filteredSecond = fPE1->filterPath(builder, src, rec, cullRect, ctm);

    // 任意一个成功即视为成功
    return filteredFirst || filteredSecond;
}
```

### 快速边界计算

```cpp
bool SkComposePathEffect::computeFastBounds(SkRect* bounds) const {
    // 内层先计算,自动更新 bounds
    // 然后外层基于更新后的 bounds 计算
    return as_PEB(fPE1)->computeFastBounds(bounds) &&
           as_PEB(fPE0)->computeFastBounds(bounds);
}

bool SkSumPathEffect::computeFastBounds(SkRect* bounds) const {
    // Sum 的顺序:PE0 先修改 bounds
    return as_PEB(fPE0)->computeFastBounds(bounds) &&
           as_PEB(fPE1)->computeFastBounds(bounds);
}
```

### 扁平化

```cpp
void SkPairPathEffect::flatten(SkWriteBuffer& buffer) const {
    buffer.writeFlattenable(fPE0.get());
    buffer.writeFlattenable(fPE1.get());
}

sk_sp<SkFlattenable> SkComposePathEffect::CreateProc(SkReadBuffer& buffer) {
    sk_sp<SkPathEffect> pe0(buffer.readPathEffect());
    sk_sp<SkPathEffect> pe1(buffer.readPathEffect());
    return SkComposePathEffect::Make(std::move(pe0), std::move(pe1));
}
```

### 工厂智能指针处理

```cpp
static sk_sp<SkPathEffect> Make(
    sk_sp<SkPathEffect> outer,
    sk_sp<SkPathEffect> inner)
{
    // 处理空指针情况
    if (!outer) return inner;
    if (!inner) return outer;

    // 创建组合效果
    return sk_sp<SkPathEffect>(
        new SkComposePathEffect(outer, inner)
    );
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkFlattenable | 序列化基类 |
| SkPath | 输入路径 |
| SkPathBuilder | 输出路径 |
| SkStrokeRec | 描边信息 |
| SkMatrix | 坐标变换 |
| SkRect | 边界矩形 |
| SkReadBuffer / SkWriteBuffer | 序列化工具 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| SkPaint | 持有路径效果 |
| SkDraw | 绘制时应用效果 |
| 效果子类 | 继承实现具体效果 |
| GPU 渲染器 | GPU 路径效果 |
| 序列化系统 | 跨进程传输 |

## 设计模式与设计决策

### 策略模式

`SkPathEffect` 封装路径变换算法:
- `SkPaint` 持有效果策略
- 绘制时动态应用
- 支持运行时替换

### 模板方法模式

基类定义算法框架:
```cpp
bool filterPath(...) const {
    return as_PEB(this)->onFilterPath(...);  // 调用子类实现
}
```

### 装饰器模式

`SkComposePathEffect` 装饰其他效果:
```cpp
outer(inner(path))
```
支持任意深度的效果嵌套。

### 组合模式

`SkSumPathEffect` 组合多个效果:
```cpp
first(path) + second(path)
```

### 不可变对象

路径效果一旦创建即不可修改:
- 线程安全
- 可缓存
- 简化生命周期

### 智能指针管理

使用 `sk_sp<SkPathEffect>`:
- 自动引用计数
- 避免内存泄漏
- 支持共享所有权

### 空对象处理

工厂方法优雅处理空指针:
```cpp
if (!outer) return inner;  // 而非抛异常
```

## 性能考量

### 虚函数开销

- 仅在需要时调用虚函数
- 内联 `as_PEB` 转换
- 编译器可能去虚化

### 临时对象优化

`SkComposePathEffect` 仅在需要时创建临时路径:
```cpp
SkPath tmp;
const SkPath* ptr = &src;

if (fPE1->filterPath(...)) {
    tmp = builder->detach();  // 仅当第一个效果成功
    ptr = &tmp;
}
```

### 快速边界

`computeFastBounds` 允许快速裁剪:
- 避免完整路径变换
- 用于加速绘制判定

### 引用计数优化

- `sk_sp` 使用侵入式引用计数
- 避免额外分配
- 原子操作最小化

### 序列化缓存

注册的效果可高效序列化:
```cpp
SK_REGISTER_FLATTENABLE(SkComposePathEffect);
SK_REGISTER_FLATTENABLE(SkSumPathEffect);
```

### 条件计算

`SkSumPathEffect` 总是调用两个效果:
```cpp
// 不短路,确保两个效果都执行
bool filteredFirst = fPE0->filterPath(...);
bool filteredSecond = fPE1->filterPath(...);
```

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| include/core/SkFlattenable.h | 继承 | 序列化基类 |
| src/core/SkPathEffectBase.h | 内部 | 内部基类定义 |
| include/core/SkPath.h | 使用 | 路径对象 |
| include/core/SkPathBuilder.h | 使用 | 路径构建器 |
| include/core/SkPaint.h | 被使用 | 绘制属性 |
| src/core/SkStrokeRec.h | 依赖 | 描边记录 |
| include/core/SkMatrix.h | 依赖 | 变换矩阵 |
| src/core/SkReadBuffer.h | 依赖 | 序列化读取 |
| src/core/SkWriteBuffer.h | 依赖 | 序列化写入 |
| src/effects/SkDashPathEffect.cpp | 子类 | 虚线效果实现 |
