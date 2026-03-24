# SkStroke

> 源文件
> - src/core/SkStroke.h
> - src/core/SkStroke.cpp

## 概述

`SkStroke` 是 Skia 中用于将几何形状转换为描边路径的核心工具类。它实现了路径描边(stroking)的完整算法,能够将线条、矩形、椭圆、圆角矩形和复杂路径转换为对应的描边轮廓。该类处理所有描边相关的属性,包括线宽、端点样式(cap)、连接样式(join)和斜接限制(miter limit)。

主要功能:
- 将路径转换为描边轮廓
- 处理直线、二次曲线、圆锥曲线和三次曲线的描边
- 支持多种端点和连接样式
- 优化矩形描边的特殊处理
- 递归细分曲线以达到精确近似

## 架构位置

`SkStroke` 在 Skia 渲染管线中的位置:
- **输入层**: 接收 `SkPath` 和 `SkPaint` 的描边参数
- **处理层**: 通过 `SkPathStroker` 内部类执行复杂的几何计算
- **输出层**: 生成可直接填充的 `SkPathBuilder` 路径
- **调用者**: Canvas、Path 效果、PDF 生成器等

## 主要类与结构体

### SkStroke

**继承关系**: 无基类

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fWidth` | `SkScalar` | 描边宽度 |
| `fMiterLimit` | `SkScalar` | 斜接限制 |
| `fResScale` | `SkScalar` | 分辨率缩放因子(默认1.0) |
| `fCap` | `uint8_t` | 端点样式(butt/round/square) |
| `fJoin` | `uint8_t` | 连接样式(miter/round/bevel) |
| `fDoFill` | `bool` | 是否同时填充 |

### SkPathStroker (内部类)

路径描边的核心执行类,处理复杂的几何计算。

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fRadius` | `SkScalar` | 描边半径(宽度的一半) |
| `fInvMiterLimit` | `SkScalar` | 斜接限制的倒数 |
| `fOuter` / `fInner` | `SkPathBuilder` | 外部和内部路径构建器 |
| `fCapper` | `CapProc` | 端点处理函数指针 |
| `fJoiner` | `JoinProc` | 连接处理函数指针 |
| `fRecursionDepth` | `int` | 递归深度计数器 |

### SkQuadConstruct (内部结构体)

用于构建二次曲线描边的状态容器。

**关键成员**:

| 成员 | 类型 | 说明 |
|------|------|------|
| `fQuad[3]` | `SkPoint` | 描边后的二次曲线控制点 |
| `fTangentStart` / `fTangentEnd` | `SkVector` | 起点和终点的切向量 |
| `fStartT` / `fMidT` / `fEndT` | `SkScalar` | 参数化时间点 |

## 公共 API 函数

### 构造与配置

```cpp
SkStroke();  // 默认构造
explicit SkStroke(const SkPaint&);  // 从 Paint 构造
SkStroke(const SkPaint&, SkScalar width);  // 覆盖宽度

// 设置属性
void setCap(SkPaint::Cap);
void setJoin(SkPaint::Join);
void setMiterLimit(SkScalar);
void setWidth(SkScalar);
void setDoFill(bool doFill);
void setResScale(SkScalar rs);
```

### 描边操作

```cpp
// 描边路径
void strokePath(const SkPath& path, SkPathBuilder* result) const;

// 描边矩形(优化路径)
void strokeRect(const SkRect& rect, SkPathBuilder* result,
                SkPathDirection = SkPathDirection::kCW) const;
```

## 内部实现细节

### 描边算法流程

1. **路径迭代**: 使用 `SkPath::Iter` 遍历路径的所有片段
2. **分类处理**:
   - 直线: 直接计算垂直偏移
   - 二次曲线: 检查线性度,递归细分
   - 圆锥曲线: 类似二次曲线,考虑权重
   - 三次曲线: 检查拐点,分段处理
3. **连接处理**: 在片段连接处应用 join 样式
4. **端点处理**: 在开放路径两端应用 cap 样式
5. **路径合并**: 将外部和内部路径合并为最终轮廓

### 曲线细分策略

**递归限制**:
```cpp
static const int kRecursiveLimits[] = {
    5*3,  // Tangent: 15
    24,   // Cubic: 24
    11*3, // Conic: 33
    11*3  // Quad: 33
};
```

**细分条件判断**:
1. **切线匹配**: 检查起点和终点切线是否相交
2. **距离检查**: 曲线中点到描边中点的距离是否小于阈值(`fInvResScale`)
3. **边界检查**: 曲线点是否在描边二次曲线的边界内
4. **相交测试**: 使用射线相交算法验证近似质量

### 退化情况处理

**线性退化**:
- 检查控制点是否共线(`cubic_in_line`, `quad_in_line`, `conic_in_line`)
- 如果共线但有曲率极值点,转换为折线
- 完全退化为点的情况,处理零长度线(支持 square/round cap)

**数值退化**:
- 使用 `degenerate_vector` 检查向量是否过小
- 使用 `SkIsFinite` 防止无穷大/NaN
- 使用 `sk_ieee_float_divide` 安全除法

### 特殊优化

**矩形优化** (`strokeRect`):
1. 直接计算矩形外扩(`outset`)
2. 根据 join 样式选择:
   - Miter: 直接添加矩形
   - Bevel: 添加斜角多边形
   - Round: 添加圆角矩形
3. 如果宽度小于矩形尺寸,添加内部矩形

**填充+描边** (`fDoFill`):
- 保留原始路径
- 根据绕向决定是否反转路径
- 适用于凸多边形优化

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkPath` / `SkPathBuilder` | 路径输入和输出 |
| `SkPaint` | 获取描边参数 |
| `SkGeometry` | 曲线求值和细分 |
| `SkStrokerPriv` | Cap 和 Join 处理函数 |
| `SkPathPriv` | 路径内部工具 |
| `SkPointPriv` | 点操作工具 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `SkCanvas::drawPath` | 当样式为 stroke 时调用 |
| `SkPath::stroke` | 路径自我描边 |
| PDF/SVG 导出 | 转换描边为填充路径 |
| 路径效果 | DashPathEffect 等 |

## 设计模式与设计决策

### 设计模式

1. **分治策略**: 递归细分曲线直到满足精度要求
2. **策略模式**: 使用函数指针(`CapProc`, `JoinProc`)动态选择端点/连接处理
3. **构建器模式**: `SkPathBuilder` 逐步构建最终路径
4. **模板方法**: `SkPathStroker` 定义描边流程骨架,具体曲线类型填充细节

### 设计决策

1. **双路径构建**:
   - 分别维护外部(`fOuter`)和内部(`fInner`)路径
   - 最后将内部路径反向添加到外部路径
   - 优点: 简化连接处理,避免自相交

2. **递归深度限制**:
   - 防止病态输入导致栈溢出
   - 达到限制后强制添加直线
   - 基于实际测试数据设定阈值

3. **分辨率缩放** (`fResScale`):
   - 允许根据缩放级别调整精度
   - `fInvResScale` 控制容差
   - 高缩放场景需要更精细的细分

4. **特殊形状优化**:
   - 矩形描边不使用通用算法
   - 直接计算,避免不必要的细分

5. **退化处理**:
   - 零长度线仍可绘制端点(square/round)
   - 相切点添加圆形(`fCusper`)处理尖角

## 性能考量

1. **递归开销**:
   - 限制最大递归深度
   - 使用栈上的 `SkQuadConstruct` 避免堆分配

2. **内存预留**:
   ```cpp
   fOuter.incReserve(src.countPoints() * 3);
   fInner.incReserve(src.countPoints());
   ```
   - 根据输入路径大小预估输出大小
   - 减少动态增长的重分配

3. **早期退出**:
   - 零宽度描边直接返回
   - 线性曲线直接转为直线
   - 距离检查快速拒绝

4. **数值优化**:
   - 使用 `SkScalarHalf` 预计算半值
   - 缓存 `fInvResScaleSquared` 避免重复计算
   - 平方距离比较避免开方

5. **函数指针开销**:
   - Cap 和 Join 通过函数指针调用
   - 避免虚函数开销
   - 减少条件分支

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkStrokerPriv.h` | Cap/Join 实现 |
| `src/core/SkPath.h` | 路径定义 |
| `src/core/SkPathBuilder.h` | 路径构建器 |
| `src/core/SkGeometry.h` | 曲线几何工具 |
| `include/core/SkPaint.h` | 绘制属性 |
| `src/core/SkPathEnums.h` | 路径枚举定义 |
| `src/core/SkPointPriv.h` | 点操作工具 |
