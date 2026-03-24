# SkPathOps

> 源文件: `include/pathops/SkPathOps.h`

## 概述
SkPathOps 提供了对 Skia 路径进行布尔运算和几何简化的公共 API。该模块实现了差集、交集、并集、异或等逻辑操作,以及路径简化、填充规则转换等几何算法,是 Skia 2D 图形处理的核心工具之一,广泛用于复杂图形的构造和优化。

## 架构位置
该文件位于 Skia 的 PathOps 子系统公共接口层,属于核心 2D 图形处理模块。它提供的功能独立于渲染后端,纯粹在 CPU 上进行路径几何计算,位于应用层和底层渲染器之间,为上层图形 API (如 SkCanvas) 提供支持。

## 主要类型与枚举

### SkPathOp
路径布尔运算类型枚举。

**枚举值**:
| 运算 | 说明 | 几何意义 |
|------|------|----------|
| kDifference_SkPathOp | 差集 | A - B (从第一个路径减去第二个) |
| kIntersect_SkPathOp | 交集 | A ∩ B (两个路径的公共区域) |
| kUnion_SkPathOp | 并集 | A ∪ B (两个路径的合并区域) |
| kXOR_SkPathOp | 异或 | A ⊕ B (排除公共区域的合并) |
| kReverseDifference_SkPathOp | 反向差集 | B - A (从第二个路径减去第一个) |

**应用场景**:
- **Difference**: 镂空效果,如在矩形中挖出圆形
- **Intersect**: 裁剪效果,获取重叠部分
- **Union**: 合并形状,创建复杂轮廓
- **XOR**: 对称差集,创建中空效果
- **ReverseDifference**: 反向镂空

## 公共 API 函数

### `Op` (推荐)
```cpp
std::optional<SkPath> SK_API Op(const SkPath& one,
                                 const SkPath& two,
                                 SkPathOp op);
```
- **功能**: 对两个路径执行布尔运算
- **参数**:
  - `one`: 第一个操作数 (差集中的被减数)
  - `two`: 第二个操作数 (差集中的减数)
  - `op`: 布尔运算类型
- **返回值**: 成功返回包含结果路径的 `optional`,失败返回空 `optional`
- **特点**:
  - 结果由非重叠轮廓构成
  - 曲线降阶优化 (三次→二次→直线)
  - 自动处理自交和退化情况

**使用示例**:
```cpp
SkPath rect = SkPath::Rect({0, 0, 100, 100});
SkPath circle = SkPath::Circle(50, 50, 40);

// 创建圆角矩形镂空
if (auto result = Op(rect, circle, kDifference_SkPathOp)) {
    canvas->drawPath(*result, paint);
}
```

### `Op` (已弃用)
```cpp
static inline bool Op(const SkPath& one, const SkPath& two,
                      SkPathOp op, SkPath* result);
```
- **功能**: 旧版本的 Op 函数,通过输出参数返回结果
- **返回值**: 成功返回 true,失败返回 false
- **状态**: 标记为 DEPRECATED,建议使用返回 `optional` 的版本
- **迁移**: `if (Op(a, b, op, &result))` → `if (auto res = Op(a, b, op)) result = *res;`

### `Simplify` (推荐)
```cpp
std::optional<SkPath> SK_API Simplify(const SkPath& path);
```
- **功能**: 简化路径,移除重叠轮廓,保持填充区域不变
- **参数**: `path` - 待简化的路径
- **返回值**: 简化后的路径,失败返回空 `optional`
- **优化**:
  - 合并共线段
  - 三次贝塞尔曲线降阶为二次曲线
  - 二次曲线降阶为直线
  - 移除零长度段和退化轮廓

**使用场景**:
- 减少路径复杂度以提升渲染性能
- 清理手绘路径的冗余点
- 为布尔运算准备路径

**示例**:
```cpp
SkPath complexPath = loadFromSvg();  // 可能包含重叠轮廓
if (auto simplified = Simplify(complexPath)) {
    // 简化后的路径更高效
    canvas->drawPath(*simplified, paint);
}
```

### `Simplify` (已弃用)
```cpp
static inline bool Simplify(const SkPath& path, SkPath* result);
```
- **功能**: 旧版本的 Simplify 函数
- **状态**: DEPRECATED,使用返回 `optional` 的版本

### `TightBounds` (已弃用)
```cpp
[[deprecated]]
static inline bool TightBounds(const SkPath& path, SkRect* result);
```
- **功能**: 计算路径的紧密边界框
- **状态**: 已弃用,使用 `SkPath::computeTightBounds()` 替代
- **迁移**: `TightBounds(path, &rect)` → `rect = path.computeTightBounds()`

### `AsWinding` (推荐)
```cpp
std::optional<SkPath> SK_API AsWinding(const SkPath& path);
```
- **功能**: 将任意填充规则的路径转换为 Winding 填充规则
- **参数**: `path` - 通常使用 EvenOdd 填充的路径
- **返回值**: Winding 填充的等价路径
- **限制**: 不保证检测所有自交情况,复杂路径可能结果不精确

**填充规则对比**:
- **EvenOdd**: 奇偶规则,交叉奇数次为内部
- **Winding**: 环绕规则,考虑方向,非零环绕数为内部

**使用场景**:
- 与不支持 EvenOdd 的图形 API 互操作
- 统一填充规则以简化渲染逻辑

### `AsWinding` (已弃用)
```cpp
static inline bool AsWinding(const SkPath& path, SkPath* result);
```
- **功能**: 旧版本的 AsWinding 函数
- **状态**: DEPRECATED

## 高级 API: SkOpBuilder

### SkOpBuilder 类
用于优化多个路径的批量布尔运算。

**核心方法**:

#### `add`
```cpp
void add(const SkPath& path, SkPathOp _operator);
```
- **功能**: 添加路径和对应的运算符到构建器
- **参数**:
  - `path`: 要添加的路径
  - `_operator`: 与之前结果的运算类型
- **行为**: 第一次添加时,结果为空路径与该路径的运算

**示例**:
```cpp
SkOpBuilder builder;
builder.add(pathA, kUnion_SkPathOp);       // result = ∅ ∪ A = A
builder.add(pathB, kUnion_SkPathOp);       // result = A ∪ B
builder.add(pathC, kDifference_SkPathOp);  // result = (A ∪ B) - C
```

#### `resolve` (推荐)
```cpp
std::optional<SkPath> resolve();
```
- **功能**: 计算所有累积操作的最终结果并重置构建器
- **返回值**: 结果路径,失败返回空 `optional`
- **副作用**: 构建器重置为初始状态,可复用

#### `resolve` (已弃用)
```cpp
bool resolve(SkPath* result);
```
- **状态**: DEPRECATED,使用返回 `optional` 的版本

**优势**:
- **批量优化**: 多个 Union 操作可优化为单次合并
- **减少中间结果**: 避免多次调用 `Op` 产生的临时路径
- **性能提升**: 特别适合合并大量小路径

**典型应用**:
```cpp
// 合并多个圆形创建复杂形状
SkOpBuilder builder;
for (const auto& circle : circles) {
    builder.add(circle, kUnion_SkPathOp);
}
if (auto result = builder.resolve()) {
    canvas->drawPath(*result, paint);
}
```

### 私有辅助方法
```cpp
private:
    static bool FixWinding(SkPath* path);
    static void ReversePath(SkPath* path);
    void reset();
```
- **FixWinding**: 修正路径方向以确保正确的填充
- **ReversePath**: 反转路径方向
- **reset**: 清空构建器状态

**成员变量**:
```cpp
skia_private::TArray<SkPath> fPathRefs;  // 存储路径
SkTDArray<SkPathOp> fOps;                // 存储对应操作
```

## 内部实现细节

### 算法概述
PathOps 使用基于扫描线的算法:
1. **分解**: 将贝塞尔曲线分解为单调段
2. **求交**: 计算所有路径段的交点
3. **图构建**: 构建有向图表示路径拓扑
4. **标记**: 根据填充规则标记内部/外部
5. **轮廓提取**: 提取符合运算规则的轮廓
6. **重建**: 将段重新组合为简化路径

### 曲线降阶
自动降阶优化:
```cpp
// 三次曲线 → 二次曲线
if (cubicIsNearlyQuadratic(cubic)) {
    convertToQuadratic(cubic, &quadratic);
}

// 二次曲线 → 直线
if (quadraticIsNearlyLinear(quadratic)) {
    convertToLine(quadratic, &line);
}
```

### 容错处理
对退化情况的处理:
- **零长度段**: 自动移除
- **共线点**: 合并为单个点
- **自交**: 分裂为简单轮廓
- **微小间隙**: 根据容差合并

## 性能考量

### 复杂度分析
- **Op**: O(n log n + m log m + k),其中 n、m 为路径段数,k 为交点数
- **Simplify**: O(n log n),n 为路径段数
- **AsWinding**: O(n),线性时间转换

### 性能优化建议
1. **预简化**: 运算前先 `Simplify` 减少段数
2. **批量合并**: 多个 Union 使用 `SkOpBuilder`
3. **避免重复**: 缓存常用的布尔运算结果
4. **精度控制**: 复杂路径可能需要调整容差

### 内存占用
- **临时内存**: 交点和图构建需要 O(n²) 最坏情况
- **结果路径**: 通常比输入小 (得益于简化)
- **SkOpBuilder**: 存储所有输入路径,适合批量操作

## 使用场景

### 场景 1: 复杂形状构造
```cpp
// 创建月牙形
SkPath outerCircle = SkPath::Circle(50, 50, 40);
SkPath innerCircle = SkPath::Circle(60, 50, 40);
auto crescent = Op(outerCircle, innerCircle, kDifference_SkPathOp);
```

### 场景 2: 文字镂空
```cpp
SkPath textPath = getTextPath("SKIA");
SkPath background = SkPath::Rect({0, 0, 200, 100});
auto cutout = Op(background, textPath, kDifference_SkPathOp);
```

### 场景 3: 裁剪区域计算
```cpp
SkPath clip1 = getClipRegion1();
SkPath clip2 = getClipRegion2();
auto intersection = Op(clip1, clip2, kIntersect_SkPathOp);
canvas->clipPath(*intersection);
```

### 场景 4: 合并多个形状
```cpp
SkOpBuilder builder;
for (const auto& shape : shapes) {
    builder.add(shape, kUnion_SkPathOp);
}
auto merged = builder.resolve();
```

## 错误处理

### 失败情况
返回空 `optional` 的原因:
- 输入路径无效或退化
- 数值不稳定导致无法收敛
- 内存分配失败
- 路径过于复杂 (交点数过多)

### 健壮性处理
```cpp
auto result = Op(pathA, pathB, op);
if (!result) {
    // 降级方案 1: 简化输入后重试
    auto simplifiedA = Simplify(pathA);
    auto simplifiedB = Simplify(pathB);
    if (simplifiedA && simplifiedB) {
        result = Op(*simplifiedA, *simplifiedB, op);
    }
}

if (!result) {
    // 降级方案 2: 使用原始路径
    result = pathA;
}

canvas->drawPath(*result, paint);
```

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/core/SkPath.h | 路径表示和操作 |
| include/core/SkTypes.h | 基础类型定义 |
| include/private/base/SkTArray.h | 动态数组容器 |
| include/private/base/SkTDArray.h | 模板动态数组 |
| std::optional | 可选返回值 |

### 被依赖的模块
- SkCanvas: 使用布尔运算实现复杂裁剪
- SkPath: 内部调用 PathOps 进行路径简化
- SVG 渲染器: 处理 SVG 路径的布尔运算
- PDF 渲染器: 优化路径表示

## 相关文件
| 文件 | 关系 |
|------|------|
| include/core/SkPath.h | 路径对象定义 |
| src/pathops/SkPathOpsTypes.h | PathOps 内部类型 |
| src/pathops/SkOpBuilder.cpp | SkOpBuilder 实现 |
| src/pathops/SkOpAngle.h | 角度计算 |
| src/pathops/SkPathOpsCubic.h | 三次曲线处理 |
| tests/PathOpsTest.cpp | 单元测试 |

## 最佳实践

1. **使用现代 API**: 优先使用返回 `optional` 的函数
2. **检查返回值**: 始终处理失败情况
3. **预简化路径**: 复杂路径先 `Simplify` 再运算
4. **批量合并**: 多个 Union 用 `SkOpBuilder`
5. **避免深度嵌套**: 多层布尔运算逐步计算并简化
6. **性能测试**: 复杂场景进行性能分析

## 调试技巧

### 可视化中间结果
```cpp
void debugPathOp(const SkPath& a, const SkPath& b, SkPathOp op) {
    // 绘制输入
    canvas->drawPath(a, paintA);
    canvas->drawPath(b, paintB);

    // 绘制结果
    if (auto result = Op(a, b, op)) {
        canvas->drawPath(*result, paintResult);
    } else {
        SkDebugf("PathOp failed\n");
    }
}
```

### 检查路径有效性
```cpp
bool isPathValid(const SkPath& path) {
    // 检查边界
    SkRect bounds = path.getBounds();
    if (!bounds.isFinite()) return false;

    // 检查轮廓数
    if (path.countVerbs() == 0) return false;

    return true;
}
```

## 常见陷阱

1. **忽略返回值**: 不检查 `optional` 导致空解引用
2. **过度精度要求**: 微小差异导致意外失败
3. **填充规则混淆**: EvenOdd 和 Winding 结果差异
4. **性能预期**: 复杂路径运算可能耗时数百毫秒
5. **内存峰值**: 大量交点可能导致内存激增

## 总结
SkPathOps 提供了强大而灵活的路径几何运算能力,是 Skia 2D 图形处理的核心模块。理解其 API 设计、性能特性和最佳实践,对于构建高效的矢量图形应用至关重要。现代 API 使用 `std::optional` 提供更安全的错误处理,而 `SkOpBuilder` 则为批量操作提供了优化路径。
