# SkPathOpsTCurve - 路径操作曲线抽象接口

> 源文件:
> - `src/pathops/SkPathOpsTCurve.h`

## 概述

`SkTCurve` 是 Skia 路径操作子系统中曲线类型的抽象基类。它定义了所有曲线类型（二次、圆锥、三次）必须实现的通用接口，使得 T-sect（T 分割）算法等高层算法可以以多态方式处理不同类型的曲线。

这是一个纯虚接口类，所有方法均为纯虚函数。

## 架构位置

```
src/pathops/
  SkPathOpsTCurve.h      // 本文件 - 抽象接口
  |
  +-- SkDQuad (实现)     // 二次贝塞尔曲线
  +-- SkDConic (实现)    // 圆锥曲线
  +-- SkDCubic (实现)    // 三次贝塞尔曲线
  |
  v
  T-sect 算法             // 使用多态曲线接口
```

## 主要类与结构体

### `SkTCurve`

纯虚基类，定义曲线的通用操作接口。

**析构函数：**

```cpp
virtual ~SkTCurve() {}
```

虚析构函数确保通过基类指针正确销毁子类对象。

## 公共 API 函数

### 点访问

```cpp
virtual const SkDPoint& operator[](int n) const = 0;
virtual SkDPoint& operator[](int n) = 0;
```
访问曲线的第 n 个控制点。

### 几何属性

| 方法 | 返回类型 | 说明 |
|------|---------|------|
| `collapsed()` | `bool` | 曲线是否退化（所有点重合） |
| `controlsInside()` | `bool` | 控制点是否在端点凸包内 |
| `pointCount()` | `int` | 控制点数量（quad=3, conic=3, cubic=4） |
| `pointLast()` | `int` | 最后一个控制点索引 |

### 求值

```cpp
virtual SkDVector dxdyAtT(double t) const = 0;
virtual SkDPoint ptAtT(double t) const = 0;
```
在参数 t 处求切线向量和点坐标。

### 凸包交叉检测

```cpp
virtual bool hullIntersects(const SkDQuad&, bool* isLinear) const = 0;
virtual bool hullIntersects(const SkDConic&, bool* isLinear) const = 0;
virtual bool hullIntersects(const SkDCubic&, bool* isLinear) const = 0;
virtual bool hullIntersects(const SkTCurve&, bool* isLinear) const = 0;
```
检测本曲线的凸包是否与另一曲线的凸包相交。`isLinear` 输出参数指示是否为线性交叉。

### 射线交点

```cpp
virtual int intersectRay(SkIntersections* i, const SkDLine& line) const = 0;
```
计算与射线的交点。

### 类型查询

```cpp
virtual bool IsConic() const = 0;
```
查询是否为圆锥曲线类型。

### 工厂方法

```cpp
virtual SkTCurve* make(SkArenaAlloc&) const = 0;
```
在 arena 分配器上创建同类型的新曲线实例。

### 其他

| 方法 | 说明 |
|------|------|
| `maxIntersections()` | 返回最大可能交点数 |
| `otherPts(int oddMan, const SkDPoint* endPt[2])` | 获取除指定点外的端点 |
| `setBounds(SkDRect*)` | 设置边界框 |
| `subDivide(double t1, double t2, SkTCurve* curve)` | 细分曲线 |
| `debugInit()` | 调试初始化 |
| `dumpID(int id)` | 调试输出（仅 DEBUG_T_SECT） |
| `globalState()` | 获取全局状态（仅 SK_DEBUG） |

## 依赖关系

- `SkPathOpsPoint.h` - `SkDPoint`、`SkDVector` 类型
- `SkArenaAlloc` - arena 分配器（用于 `make()`）
- `SkIntersections` - 交点结果容器
- `SkDRect` - 双精度矩形

## 设计模式与设计决策

1. **模板方法/策略模式**：通过虚函数接口实现多态，T-sect 算法不需要知道具体曲线类型
2. **访问者模式**：`hullIntersects()` 的多个重载允许与具体曲线类型进行双分派
3. **工厂方法**：`make()` 允许在不知道具体类型的情况下创建同类实例
4. **Arena 分配**：`make()` 使用 `SkArenaAlloc` 而非堆分配，适合大量临时曲线对象的场景
5. **条件编译调试接口**：`dumpID` 和 `globalState` 仅在调试模式下存在

## 性能考量

1. **虚函数开销**：每次调用有虚函数表查找开销，但路径操作的瓶颈在于数值计算
2. **Arena 分配**：通过 arena 分配避免频繁的堆分配/释放
3. **编译期类型信息**：`IsConic()` 允许在运行时进行类型特定优化

## 相关文件

- `src/pathops/SkPathOpsPoint.h` - 双精度点类型
- `src/pathops/SkPathOpsCubic.h` - 三次曲线实现
- `src/pathops/SkPathOpsConic.h` - 圆锥曲线实现
- `src/pathops/SkPathOpsQuad.h` - 二次曲线实现
- `src/pathops/SkTSect.h` - T-sect 算法（主要使用者）
