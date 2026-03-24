# SkPathEffectBase

> 源文件
> - src/core/SkPathEffectBase.h

## 概述

`SkPathEffectBase` 是 Skia 路径效果系统的内部基类,扩展了公共 `SkPathEffect` 接口,添加了内部使用的虚函数和辅助功能。该类采用双层继承设计,将公共API和内部实现分离,既保持了ABI稳定性,又提供了灵活的扩展机制。

主要功能包括:定义路径过滤的虚接口、支持点绘制模式、提供虚线识别接口、计算快速边界等。该类是所有具体路径效果实现的真正基类,但对外部用户不可见。

## 架构位置

`SkPathEffectBase` 位于 Skia 路径效果系统的内部层:

```
include/core/
└── SkPathEffect (公共基类)

src/core/
├── SkPathEffectBase.h (内部基类) ← 当前组件
└── effects/
    ├── SkDashPathEffect (虚线效果)
    ├── SkDiscretePathEffect (离散效果)
    └── ... (其他效果)
```

继承层次:
```
SkFlattenable
    ↑
SkPathEffect (公共基类)
    ↑
SkPathEffectBase (内部基类)
    ↑
    ├── SkDashPathEffect
    ├── SkDiscretePathEffect
    └── ... (具体效果)
```

## 主要类与结构体

### SkPathEffectBase 类

**继承关系**:
```
SkPathEffect
    ↑
SkPathEffectBase
```

**关键方法分类**:

| 方法类型 | 说明 |
|---------|------|
| 虚函数接口 | 子类必须实现的效果逻辑 |
| 点模式支持 | 将路径转换为点序列 |
| 虚线识别 | 检测是否为虚线效果 |
| 边界计算 | 快速估算效果后的边界 |
| 工具函数 | 类型转换辅助 |

### PointData 结构体

描述点绘制模式的数据。

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fFlags | uint32_t | 绘制标志 |
| fPoints | SkPoint* | 点坐标数组 |
| fNumPoints | int | 点数量 |
| fSize | SkVector | 点大小 |
| fClipRect | SkRect | 裁剪矩形(可选) |
| fPath | SkPath | 印章路径(可选) |
| fFirst | SkPath | 首点几何(可选) |
| fLast | SkPath | 末点几何(可选) |

**标志枚举**:

```cpp
enum PointFlags {
    kCircles_PointFlag = 0x01,  // 绘制圆形点
    kUsePath_PointFlag = 0x02,  // 使用路径印章
    kUseClip_PointFlag = 0x04,  // 应用裁剪矩形
};
```

### DashInfo 结构体

虚线效果参数。

**成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fIntervals | SkSpan<const SkScalar> | 线段/间隙长度数组 |
| fPhase | SkScalar | 起始相位偏移 |

## 公共 API 函数

### 核心虚函数

```cpp
// 应用路径效果(子类必须实现)
virtual bool onFilterPath(SkPathBuilder* dst,
                          const SkPath& src,
                          SkStrokeRec* rec,
                          const SkRect* cullRect,
                          const SkMatrix& ctm) const = 0;

// 是否需要CTM(默认false)
virtual bool onNeedsCTM() const { return false; }
```

### 点模式支持

```cpp
// 检测是否可转换为点序列
bool asPoints(PointData* results,
              const SkPath& src,
              const SkStrokeRec& rec,
              const SkMatrix& mx,
              const SkRect* cullR) const;

// 子类重写此方法支持点模式
virtual bool onAsPoints(PointData* results,
                        const SkPath& src,
                        const SkStrokeRec& rec,
                        const SkMatrix& mx,
                        const SkRect* cullR) const {
    return false;  // 默认不支持
}
```

### 虚线识别

```cpp
// 检测是否为虚线效果
virtual std::optional<DashInfo> asADash() const {
    return {};  // 默认不是虚线
}
```

### 边界计算

```cpp
// 计算效果后的快速边界
// bounds 既是输入也是输出
// 返回 false 表示无法计算
virtual bool computeFastBounds(SkRect* bounds) const = 0;
```

### 序列化

```cpp
// 获取扁平化类型
SkFlattenable::Type getFlattenableType() const override {
    return kSkPathEffect_Type;
}

// 反序列化
static sk_sp<SkPathEffect> Deserialize(
    const void* data,
    size_t size,
    const SkDeserialProcs* procs = nullptr);

// 注册内置效果
static void RegisterFlattenables();
```

### 类型转换辅助

```cpp
// 转换为 SkPathEffectBase*
static inline SkPathEffectBase* as_PEB(SkPathEffect* effect) {
    return static_cast<SkPathEffectBase*>(effect);
}

static inline const SkPathEffectBase* as_PEB(const SkPathEffect* effect) {
    return static_cast<const SkPathEffectBase*>(effect);
}

static inline const SkPathEffectBase* as_PEB(const sk_sp<SkPathEffect>& effect) {
    return static_cast<SkPathEffectBase*>(effect.get());
}

static inline sk_sp<SkPathEffectBase> as_PEB_sp(sk_sp<SkPathEffect> effect) {
    return sk_sp<SkPathEffectBase>(
        static_cast<SkPathEffectBase*>(effect.release())
    );
}
```

## 内部实现细节

### asPoints 委托

```cpp
bool SkPathEffectBase::asPoints(
    PointData* results,
    const SkPath& src,
    const SkStrokeRec& rec,
    const SkMatrix& mx,
    const SkRect* rect) const
{
    return this->onAsPoints(results, src, rec, mx, rect);
}
```

### PointData 构造和析构

```cpp
PointData::PointData()
    : fFlags(0)
    , fPoints(nullptr)
    , fNumPoints(0)
{
    fSize.set(SK_Scalar1, SK_Scalar1);
    // fClipRect 由子类初始化(如果设置 kUseClip 标志)
}

PointData::~PointData() {
    delete[] fPoints;  // 释放点数组
}
```

### points() 辅助方法

```cpp
SkSpan<SkPoint> PointData::points() {
    return {fPoints, (size_t)fNumPoints};
}
```

提供现代 C++ 风格的 Span 访问。

### RegisterFlattenables 实现

```cpp
void SkPathEffectBase::RegisterFlattenables() {
    SK_REGISTER_FLATTENABLE(SkComposePathEffect);
    SK_REGISTER_FLATTENABLE(SkSumPathEffect);
    // 其他效果在各自文件中注册
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkPathEffect | 公共基类 |
| SkPath | 路径对象 |
| SkPathBuilder | 输出路径 |
| SkStrokeRec | 描边信息 |
| SkMatrix | 变换矩阵 |
| SkRect | 矩形 |
| SkPoint | 点坐标 |
| SkSpan | 数组视图 |
| SkFlattenable | 序列化基类 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| SkDashPathEffect | 虚线效果 |
| SkDiscretePathEffect | 离散效果 |
| Sk1DPathEffect | 一维路径效果 |
| Sk2DPathEffect | 二维路径效果 |
| SkCornerPathEffect | 圆角效果 |
| 其他效果实现 | 继承基类 |

## 设计模式与设计决策

### 双层继承设计

分离公共API和内部实现:
```
SkPathEffect (公共接口,ABI稳定)
    ↑
SkPathEffectBase (内部接口,可自由变更)
```

优点:
- 保持ABI兼容性
- 内部可灵活扩展
- 清晰的职责分离

### 模板方法模式

基类定义算法框架,子类实现具体步骤:
```cpp
bool filterPath(...) const {
    return onFilterPath(...);  // 调用子类实现
}
```

### 策略模式

不同效果实现不同策略:
- SkDashPathEffect: 虚线策略
- SkDiscretePathEffect: 离散策略
- 可运行时替换

### NVI(非虚接口)惯用法

公共接口非虚,虚函数为 protected/private:
```cpp
// 公共非虚接口
bool asPoints(...) const;

// 私有虚接口
virtual bool onAsPoints(...) const;
```

### 可选返回值

使用 `std::optional` 表示可能失败:
```cpp
virtual std::optional<DashInfo> asADash() const;
```

### 静态转换辅助

提供类型安全的向下转换:
```cpp
static inline SkPathEffectBase* as_PEB(SkPathEffect* effect);
```

## 性能考量

### 虚函数开销

- 仅在必要时使用虚函数
- 公共接口可内联
- 编译器可能去虚化

### 快速边界

`computeFastBounds` 避免完整路径处理:
- 用于快速裁剪判定
- 保守估算足够
- 大幅提升性能

### 点模式优化

`asPoints` 允许特殊化绘制:
- 避免完整路径生成
- 直接绘制点原语
- GPU 友好

### 虚线识别

`asADash` 允许特殊优化:
- GPU 虚线硬件支持
- 避免通用路径效果开销

### 内联 as_PEB

类型转换函数标记为 `inline`:
- 零开销抽象
- 编译时解析

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| include/core/SkPathEffect.h | 继承 | 公共基类 |
| include/core/SkPath.h | 依赖 | 路径对象 |
| include/core/SkPathBuilder.h | 依赖 | 路径构建 |
| src/core/SkStrokeRec.h | 依赖 | 描边信息 |
| include/core/SkMatrix.h | 依赖 | 变换矩阵 |
| src/effects/SkDashPathEffect.h | 子类 | 虚线效果 |
| src/effects/SkDiscretePathEffect.h | 子类 | 离散效果 |
| include/core/SkFlattenable.h | 继承 | 序列化基类 |
