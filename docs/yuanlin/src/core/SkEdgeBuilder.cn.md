# SkEdgeBuilder

> 源文件
> - src/core/SkEdgeBuilder.h
> - src/core/SkEdgeBuilder.cpp

## 概述

`SkEdgeBuilder` 是 Skia 图形渲染管线中用于从路径数据构建边缘(Edge)数据结构的核心组件。它将 `SkPath` 或 `SkPathRaw` 中的矢量路径转换为可用于扫描线渲染的边缘列表。该类支持两种主要的边缘类型:`SkEdge`(基础边缘)和 `SkAnalyticEdge`(分析边缘),分别用于不同的抗锯齿渲染算法。

`SkEdgeBuilder` 采用抽象基类设计模式,提供了两个具体实现:`SkBasicEdgeBuilder` 和 `SkAnalyticEdgeBuilder`。它负责将路径的线段、二次曲线和三次曲线转换为扫描线算法可以处理的边缘对象,并在构建过程中对垂直边缘进行合并优化。

## 架构位置

`SkEdgeBuilder` 位于 Skia 核心渲染管线的光栅化阶段前端,是路径渲染到像素的关键桥梁:

```
SkPath/SkPathRaw (矢量路径描述)
    ↓
SkEdgeBuilder (路径→边缘转换)
    ↓
SkEdge/SkAnalyticEdge (扫描线边缘数据)
    ↓
扫描线渲染器 (像素填充)
```

该模块与以下组件紧密协作:
- **SkEdgeClipper**: 用于裁剪边缘到指定矩形区域
- **SkLineClipper**: 用于线段裁剪
- **SkGeometry**: 提供曲线分割和几何计算
- **SkEdge/SkAnalyticEdge**: 边缘的最终表示形式

## 主要类与结构体

### SkEdgeBuilder (抽象基类)

**继承关系**
```
SkEdgeBuilder (抽象基类)
    ├── SkBasicEdgeBuilder (基础边缘构建器)
    └── SkAnalyticEdgeBuilder (分析边缘构建器)
```

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fEdgeList` | `void**` | 指向边缘列表的指针,在多边形模式下指向预分配的连续内存,在通用模式下指向 fList 的头部 |
| `fList` | `SkTDArray<void*>` | 在通用模式下存储边缘指针的动态数组 |
| `fAlloc` | `SkSTArenaAlloc<512>` | 用于分配边缘对象的内存池,初始大小为 512 字节 |

**枚举类型**

| 枚举值 | 说明 |
|-------|------|
| `kNo_Combine` | 不进行边缘合并 |
| `kPartial_Combine` | 部分合并(修改最后一条边缘) |
| `kTotal_Combine` | 完全合并(删除最后一条边缘) |

### SkBasicEdgeBuilder

用于构建基础的 `SkEdge` 对象,适用于传统的抗锯齿渲染。

**关键方法**

| 方法 | 说明 |
|-----|------|
| `edgeList()` | 返回 `SkEdge**` 类型的边缘列表指针 |
| `combineVertical()` | 尝试将垂直边缘与前一条边缘合并 |

### SkAnalyticEdgeBuilder

用于构建 `SkAnalyticEdge` 对象,适用于分析抗锯齿渲染算法。

**关键方法**

| 方法 | 说明 |
|-----|------|
| `analyticEdgeList()` | 返回 `SkAnalyticEdge**` 类型的边缘列表指针 |
| `allocEdges()` | 为多边形模式预分配边缘数组 |
| `addPolyLine()` | 添加多边形线段并尝试合并 |

## 公共 API 函数

### 核心构建接口

```cpp
int buildEdges(const SkPathRaw& raw, const SkIRect* shiftedClip);
int buildEdges(const SkPath& path, const SkIRect* shiftedClip);
```
- **功能**: 从路径构建边缘列表
- **参数**:
  - `raw/path`: 源路径数据
  - `shiftedClip`: 可选的裁剪矩形(已移位到固定点坐标空间)
- **返回值**: 构建的边缘数量
- **特点**: 自动选择优化路径(多边形模式或通用模式)

### 内部虚函数接口

```cpp
virtual void addLine(const SkPoint pts[]) = 0;
virtual void addQuad(const SkPoint pts[]) = 0;
virtual void addCubic(const SkPoint pts[]) = 0;
```
- **功能**: 添加不同类型的曲线边缘
- **实现**: 由派生类具体实现
- **参数**: 包含控制点的点数组(线段 2 个点,二次曲线 3 个点,三次曲线 4 个点)

## 内部实现细节

### 边缘构建策略

`SkEdgeBuilder` 采用双重构建策略:

1. **多边形模式** (`buildPoly`):
   - 适用于仅包含线段的路径
   - 在连续内存中预分配边缘对象
   - 性能更优,无需间接寻址

2. **通用模式** (`build`):
   - 适用于包含曲线(二次、三次或圆锥曲线)的路径
   - 使用指针数组 `fList` 存储边缘
   - 支持复杂曲线的 Y 轴极值点分割

### 垂直边缘合并优化

为避免数值问题和提高性能,`SkEdgeBuilder` 会尝试合并相邻的垂直边缘:

```cpp
// 合并条件检查
1. 仅合并原始为线段的边缘(避免 crbug.com/1154864)
2. 检查是否完全垂直(fDxDy == 0 或 fDX == 0)
3. 检查 X 坐标是否相同
4. 根据缠绕方向和 Y 坐标位置决定合并方式
```

**合并类型**:
- **完全合并**: 两条边缘完全重叠但方向相反,删除前一条边缘
- **部分合并**: 两条边缘可以连接或部分重叠,修改前一条边缘的端点
- **不合并**: 无法合并的情况,添加为新边缘

### 曲线处理

**二次曲线**:
```cpp
// 在 Y 轴极值点分割二次曲线
int n = SkChopQuadAtYExtrema(pts, monoX);
for (int i = 0; i <= n; i++) {
    this->addQuad(&monoX[i * 2]);
}
```

**三次曲线**:
```cpp
// 在 Y 轴极值点分割三次曲线
int n = SkChopCubicAtYExtrema(pts, monoY);
for (int i = 0; i <= n; i++) {
    this->addCubic(&monoY[i * 3]);
}
```

**圆锥曲线**:
```cpp
// 将圆锥曲线转换为二次曲线序列
const SkPoint* quadPts = quadder.computeQuads(pts, weight, kConicTol);
for (int i = 0; i < quadder.countQuads(); ++i) {
    handle_quad(quadPts);
    quadPts += 2;
}
```

### 裁剪集成

构建过程与 `SkEdgeClipper` 和 `SkLineClipper` 紧密集成:

```cpp
SkEdgeClipper::ClipPath(raw, clip, canCullToTheRight,
    [](SkEdgeClipper* clipper, bool, void* ctx) {
        // 处理裁剪后的边缘片段
        while (auto verb = clipper->next(pts)) {
            switch (*verb) {
                case SkPathVerb::kLine:  builder->addLine(pts); break;
                case SkPathVerb::kQuad:  builder->addQuad(pts); break;
                case SkPathVerb::kCubic: builder->addCubic(pts); break;
            }
        }
    }, &rec);
```

### 凸性优化

对于凸多边形,可以优化边缘剔除策略:

```cpp
const bool canCullToTheRight = !raw.isKnownToBeConvex();
```
- 凸路径需要保留所有边缘(包括右侧超出裁剪区的边缘)
- 非凸路径可以剔除右侧边缘以提高性能

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkPath/SkPathRaw` | 提供源路径数据结构 |
| `SkEdgeClipper` | 对曲线进行裁剪处理 |
| `SkLineClipper` | 对线段进行裁剪处理 |
| `SkGeometry` | 提供曲线分割和几何计算函数 |
| `SkEdge` | 基础边缘数据结构 |
| `SkAnalyticEdge` | 分析边缘数据结构 |
| `SkPathPriv` | 路径的内部辅助函数 |
| `SkSTArenaAlloc` | 内存池分配器 |

### 被依赖的模块

| 模块 | 依赖方式 |
|------|----------|
| `SkScan` | 使用构建的边缘列表进行扫描线渲染 |
| `SkBlitter` | 与边缘配合进行像素填充 |
| `SkDraw` | 高层绘制接口使用边缘构建器 |
| `SkRasterPipelineBlitter` | 在光栅管线中使用边缘数据 |

## 设计模式与设计决策

### 模板方法模式

`SkEdgeBuilder` 使用模板方法模式定义边缘构建的整体流程:

```cpp
// 抽象基类定义算法骨架
int buildEdges(const SkPathRaw& raw, const SkIRect* clip) {
    // 1. 选择构建策略(多边形 vs 通用)
    // 2. 遍历路径片段
    // 3. 调用虚函数 addLine/addQuad/addCubic
    // 4. 返回边缘数量
}

// 派生类实现具体步骤
virtual void addLine(const SkPoint pts[]) = 0;
```

### 策略模式

通过两个派生类实现不同的边缘生成策略:
- `SkBasicEdgeBuilder`: 生成 `SkEdge` 对象
- `SkAnalyticEdgeBuilder`: 生成 `SkAnalyticEdge` 对象

### 对象池模式

使用 `SkSTArenaAlloc` 实现内存池:
```cpp
SkSTArenaAlloc<512> fAlloc;  // 512 字节初始块大小
SkEdge* edge = fAlloc.make<SkEdge>();
```

**优势**:
- 减少内存分配次数
- 提高缓存局部性
- 简化内存管理(统一释放)

### 设计决策

1. **双模式构建**: 为纯线段路径提供快速路径,避免不必要的开销
2. **垂直边缘合并**: 减少边缘数量,提高扫描线渲染效率
3. **延迟裁剪**: 在边缘构建过程中集成裁剪,避免后处理开销
4. **Y 轴单调性**: 在极值点分割曲线,确保扫描线算法的正确性
5. **固定点运算兼容**: 支持移位的裁剪矩形,与固定点渲染管线集成

## 性能考量

### 内存分配优化

1. **Arena 分配器**: 使用 512 字节的初始栈缓冲区,小规模路径无需堆分配
2. **连续内存**: 多边形模式下边缘对象连续存储,提高缓存命中率
3. **就地构造**: 使用 `make<T>()` 直接在内存池中构造对象

### 计算优化

1. **快速路径检测**:
   ```cpp
   const int count = SkPath::kLine_SegmentMask == raw.segmentMasks()
       ? this->buildPoly(raw, clip, canCullToTheRight)
       : this->build(raw, clip, canCullToTheRight);
   ```

2. **垂直边缘合并**: 减少后续扫描线处理的边缘数量

3. **凸性优化**: 凸路径可以启用右侧剔除优化

4. **数值稳定性**: 仅对原始线段应用垂直合并,避免曲线数值误差(crbug.com/1154864)

### 裁剪优化

```cpp
// 提前拒绝完全在裁剪区外的路径片段
if (quick_reject(bounds, clip)) {
    return;
}
```

### 溢出保护

```cpp
// 使用安全数学防止边缘计数溢出
SkSafeMath safe;
maxEdgeCount = safe.mul(maxEdgeCount, SkLineClipper::kMaxClippedLineSegments);
if (!safe) {
    return 0;  // 溢出时返回 0
}
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/core/SkEdge.h` | 数据结构 | 基础边缘类型定义 |
| `src/core/SkAnalyticEdge.h` | 数据结构 | 分析边缘类型定义 |
| `src/core/SkEdgeClipper.h` | 依赖 | 曲线裁剪器 |
| `src/core/SkLineClipper.h` | 依赖 | 线段裁剪器 |
| `src/core/SkGeometry.h` | 依赖 | 几何计算函数 |
| `src/core/SkPathPriv.h` | 依赖 | 路径内部辅助函数 |
| `src/core/SkScan.cpp` | 使用者 | 扫描线渲染实现 |
| `src/core/SkDraw.cpp` | 使用者 | 高层绘制接口 |
| `include/core/SkPath.h` | 输入数据 | 公共路径 API |
