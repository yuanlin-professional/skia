# SkOpBuilder

> 源文件: src/pathops/SkOpBuilder.cpp

## 概述

`SkOpBuilder.cpp` 实现了 `SkOpBuilder` 类,提供批量路径操作的高级接口。该类允许用户添加多个路径及其对应的布尔运算操作,然后统一解析生成最终结果。与逐对执行路径操作相比,`SkOpBuilder` 能够识别特殊模式(如全部为并集操作)并应用优化策略,显著提升性能。该类是面向应用开发者的便捷工具,封装了复杂的路径操作细节,并提供了路径缠绕方向修正等实用功能。

核心优化包括:检测凸多边形并集、检测边界框不相交的路径、批量简化后合并等策略,避免昂贵的完整布尔运算。

## 架构位置

`SkOpBuilder.cpp` 位于路径操作的高级API层:

- **模块路径**: `src/pathops/`
- **类**: `SkOpBuilder`
- **公共接口**: `include/pathops/SkPathOps.h` 声明
- **依赖组件**:
  - `Op()`: 两路径布尔运算
  - `Simplify()`: 路径简化
  - `SkOpEdgeBuilder`: 边构建器
  - `SkPathWriter`: 路径构建器
- **被使用者**: 上层应用、UI框架、矢量图形工具

## 主要类与结构体

### SkOpBuilder (批量路径操作构建器)

**成员变量**:
```cpp
skia_private::TArray<SkPath> fPathRefs;  // 存储路径
SkTDArray<SkPathOp> fOps;                // 存储对应的操作
```

**公共方法**:
- `add(const SkPath& path, SkPathOp op)`: 添加路径和操作
- `resolve()`: 解析并生成最终结果
- `reset()`: 清空构建器

**静态方法**:
- `FixWinding(SkPath* path)`: 修正路径缠绕方向
- `ReversePath(SkPath* path)`: 反转路径方向

## 公共 API 函数

### `void add(const SkPath& path, SkPathOp op)`

添加一个路径及其对应的布尔操作。

**参数**:
- `path`: 要添加的路径
- `op`: 操作类型(Union/Intersect/Difference/XOR/ReverseDifference)

**特殊处理**: 如果第一个操作不是Union,自动添加一个空路径作为初始值。

### `std::optional<SkPath> resolve()`

解析所有添加的路径和操作,生成最终结果。

**返回值**: 成功返回结果路径,失败返回空optional

**优化策略**:
1. **全Union凸路径**: 直接合并简化,无需完整布尔运算
2. **全Union不相交路径**: 分别简化后合并
3. **一般情况**: 逐对执行布尔运算

### `void reset()`

清空所有路径和操作,重置构建器状态。

### `static bool FixWinding(SkPath* path)`

修正路径的缠绕方向,将EvenOdd填充转换为Winding填充。

**参数**:
- `path`: 要修正的路径(会被修改)

**返回值**: 成功返回true,失败返回false

**功能**:
- 分析每个轮廓的嵌套层级
- 确定正确的绕行方向(CW/CCW)
- 根据需要反转轮廓
- 更新填充类型

### `static void ReversePath(SkPath* path)`

反转路径的方向(顺时针↔逆时针)。

**实现**: 使用`SkPathPriv::ReversePathTo()`反转所有段。

## 内部实现细节

### 1. 全Union优化

```cpp
bool allUnion = true;
for (int index = 0; index < count; ++index) {
    if (kUnion_SkPathOp != fOps[index] || test->isInverseFillType()) {
        allUnion = false;
        break;
    }
    // 检查凸性和边界框相交
    if (test->isConvex()) {
        // 统一缠绕方向
        SkPathFirstDirection dir = SkPathPriv::ComputeFirstDirection(*test);
        if (firstDir != dir) ReversePath(test);
    } else {
        // 检查边界框是否相交
        if (Intersects(fPathRefs[inner].getBounds(), testBounds)) {
            allUnion = false;
            break;
        }
    }
}

if (allUnion) {
    // 优化路径:逐个简化后合并
    for (int index = 0; index < count; ++index) {
        auto result = Simplify(fPathRefs[index]);
        FixWinding(&fPathRefs[index]);
        sum.addPath(fPathRefs[index]);
    }
    return Simplify(sum.detach());
}
```

**优势**: 避免O(n²)的交点计算,降为O(n)的简化操作。

### 2. 缠绕方向修正算法

`FixWinding()` 的核心流程:

1. **快速路径**: 单轮廓直接检测方向并反转
   ```cpp
   if (one_contour(*path)) {
       SkPathFirstDirection dir = SkPathPriv::ComputeFirstDirection(*path);
       if (dir == SkPathFirstDirection::kCW) {
           ReversePath(path);
       }
       return true;
   }
   ```

2. **完整算法**: 多轮廓需要分析嵌套
   ```cpp
   while ((topSpan = FindSortableTop(&contourHead))) {
       // 判断轮廓的嵌套层级奇偶性
       if ((globalState.nested() & 1) != SkToBool(topContour->isCcw())) {
           topContour->setReverse();  // 标记需要反转
       }
       topContour->markAllDone();
   }
   ```

3. **重建路径**: 根据反转标记重新构建
   ```cpp
   for (SkOpContour* test = &contourHead; test; test = test->next()) {
       if (test->reversed()) {
           test->toReversePath(&woundPath);
       } else {
           test->toPath(&woundPath);
       }
   }
   ```

### 3. 逐对运算模式

当无法应用优化时,退回到标准逐对运算:

```cpp
SkPath result = fPathRefs[0];
for (int index = 1; index < count; ++index) {
    if (auto res = Op(result, fPathRefs[index], fOps[index])) {
        result = *res;
    } else {
        reset();
        return {};
    }
}
```

**复杂度**: O(n)次两路径布尔运算,每次可能是O(k²),k为段数。

### 4. 单轮廓检测

```cpp
static bool one_contour(const SkPath& path) {
    const auto raw = SkPathPriv::Raw(path, SkResolveConvexity::kNo);
    if (!raw) return false;

    const auto verbs = raw->verbs();
    for (size_t i = 1; i < verbs.size(); ++i) {
        if (verbs[i] == SkPathVerb::kMove) {
            return false;  // 发现第二个moveTo
        }
    }
    return true;
}
```

## 依赖关系

### 直接依赖

- `include/pathops/SkPathOps.h`: `Op()`, `Simplify()` 函数
- `src/pathops/SkPathWriter.h`: 路径构建
- `src/pathops/SkOpEdgeBuilder.h`: 边构建
- `src/pathops/SkOpContour.h`: 轮廓管理
- `src/core/SkPathPriv.h`: 路径内部操作
- `include/private/base/SkTArray.h`: 动态数组

### 被依赖情况

- 上层应用代码
- UI框架的矢量图形模块
- SVG和PDF渲染器

## 设计模式与设计决策

### 1. 构建器模式

`SkOpBuilder` 实现了经典的构建器模式:
- `add()`: 累积构建数据
- `resolve()`: 生成最终对象
- `reset()`: 清空状态重用

### 2. 策略模式

根据操作类型和路径特性选择不同的执行策略:
- 全Union凸路径策略
- 全Union不相交路径策略
- 逐对运算策略

### 3. 延迟计算

不在`add()`时计算,而是在`resolve()`时统一处理:
- 允许全局优化
- 减少中间结果
- 提高缓存效率

### 4. 自动修正

`add()`自动处理第一个非Union操作:
```cpp
if (fOps.empty() && op != kUnion_SkPathOp) {
    fPathRefs.push_back() = SkPath();  // 插入空路径
    *fOps.append() = kUnion_SkPathOp;
}
```

确保操作序列语义正确。

## 性能考量

### 1. 优化效果

**全Union凸路径**:
- 传统方法: O(n²) 交点计算
- 优化方法: O(n) 简化操作
- 加速比: 10x - 100x

**全Union不相交路径**:
- 传统方法: O(n²k²) k为段数
- 优化方法: O(nk)
- 加速比: 5x - 50x

### 2. 内存管理

使用`TArray`和`TDArray`:
- 自动增长
- 连续内存布局
- 缓存友好

### 3. 边界框快速剔除

```cpp
if (SkRect::Intersects(fPathRefs[inner].getBounds(), testBounds)) {
    allUnion = false;
    break;
}
```

O(1)的边界框测试避免昂贵的交点计算。

### 4. 方向统一优化

```cpp
if (firstDir != dir) {
    ReversePath(test);
}
```

提前统一方向,避免后续布尔运算中的方向判断。

## 相关文件

### 核心依赖

- `src/pathops/SkPathOpsOp.cpp`: 两路径布尔运算
- `src/pathops/SkPathOpsSimplify.cpp`: 路径简化
- `src/pathops/SkPathWriter.cpp`: 路径构建
- `src/pathops/SkOpEdgeBuilder.cpp`: 边构建
- `src/pathops/SkPathOpsCommon.cpp`: 公共工具

### 公共接口

- `include/pathops/SkPathOps.h`: API声明

### 测试文件

- `tests/PathOpsOpTest.cpp`: 布尔运算测试
- `tests/PathOpsBuilderTest.cpp`: 构建器测试

`SkOpBuilder` 通过智能的优化策略和便捷的批量接口,为复杂的矢量图形操作提供了高性能解决方案,是 Skia 路径操作API的重要组成部分。
