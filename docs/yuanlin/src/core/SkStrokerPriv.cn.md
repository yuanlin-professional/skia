# SkStrokerPriv

> 源文件: src/core/SkStrokerPriv.h, src/core/SkStrokerPriv.cpp

## 概述

`SkStrokerPriv` 是 Skia 图形库中路径描边(stroke)功能的私有辅助类。它提供了描边操作中最核心的两个几何处理功能:端点帽(Cap)和连接点(Join)的绘制。该类定义了函数指针类型和工厂方法,用于根据不同的描边样式(如圆形帽、斜接连接等)选择相应的几何生成算法。这些算法将描边路径转换为具体的几何形状。

## 架构位置

`SkStrokerPriv` 位于 Skia 核心层的路径处理模块中,作为路径描边系统的底层实现组件。它为 `SkStroke` 等上层描边类提供具体的几何生成算法。

```
Skia 路径处理架构:
  应用层
    ↓ 使用 SkPaint 设置描边样式
  SkPaint (描边属性: Cap, Join, Width)
    ↓
  SkStroke (描边逻辑协调器)
    ↓ 调用几何生成
  SkStrokerPriv (几何算法实现)
    ↓ 输出到
  SkPathBuilder (构建结果路径)
```

## 主要类与结构体

### SkStrokerPriv

**继承关系:**
- 无继承关系(纯静态工具类)

**关键成员:**

该类不包含成员变量,仅定义函数指针类型和静态工厂方法。

**函数指针类型:**

| 类型名 | 签名 | 说明 |
|-------|------|------|
| `CapProc` | `void (*)(SkPathBuilder*, const SkPoint& pivot, const SkVector& normal, const SkPoint& stop, bool extendLastPt)` | 端点帽绘制函数指针 |
| `JoinProc` | `void (*)(SkPathBuilder* outer, SkPathBuilder* inner, const SkVector& beforeUnitNormal, const SkPoint& pivot, const SkVector& afterUnitNormal, SkScalar radius, SkScalar invMiterLimit, bool prevIsLine, bool currIsLine)` | 连接点绘制函数指针 |

**重要常量定义:**

| 宏定义 | 值 | 说明 |
|-------|---|------|
| `CWX(x, y)` | `-y` | 顺时针旋转 X 坐标 |
| `CWY(x, y)` | `x` | 顺时针旋转 Y 坐标 |
| `CCWX(x, y)` | `y` | 逆时针旋转 X 坐标 |
| `CCWY(x, y)` | `-x` | 逆时针旋转 Y 坐标 |
| `CUBIC_ARC_FACTOR` | `(√2-1)*4/3` | 立方贝塞尔曲线近似圆弧的控制点因子 |

## 公共 API 函数

### 工厂方法

| 函数签名 | 功能说明 |
|---------|---------|
| `static CapProc CapFactory(SkPaint::Cap)` | 根据端点帽样式返回对应的绘制函数 |
| `static JoinProc JoinFactory(SkPaint::Join)` | 根据连接点样式返回对应的绘制函数 |

### 端点帽样式

支持三种端点帽样式:
- **Butt Cap**: 平头端点,直接截断
- **Round Cap**: 圆形端点,使用圆锥曲线绘制半圆
- **Square Cap**: 方形端点,延伸半个描边宽度的矩形

### 连接点样式

支持三种连接点样式:
- **Miter Join**: 斜接连接,延长两条边直到相交
- **Round Join**: 圆角连接,使用圆弧连接
- **Bevel Join** (代码中称为 Blunt): 斜面连接,直接连接两个端点

## 内部实现细节

### 端点帽实现

**1. ButtCapper (平头帽)**
```cpp
static void ButtCapper(SkPathBuilder* sink, const SkPoint& pivot,
                       const SkVector& normal, const SkPoint& stop, bool) {
    sink->lineTo(stop.fX, stop.fY);
}
```
最简单的实现,直接连接到终止点。

**2. RoundCapper (圆形帽)**
- 计算平行于路径方向的向量
- 使用两个圆锥曲线(conic)绘制半圆
- 圆锥曲线权重为 `SK_ScalarRoot2Over2` (≈0.707),可精确表示 90° 圆弧

**3. SquareCapper (方形帽)**
- 计算平行和垂直向量
- 根据 `extendLastPt` 参数决定是否扩展最后一个点
- 绘制矩形延伸部分

### 连接点实现

**角度类型分类:**

```cpp
enum AngleType {
    kNearly180_AngleType,   // 接近 180°(几乎反向)
    kSharp_AngleType,       // 锐角
    kShallow_AngleType,     // 钝角
    kNearlyLine_AngleType   // 接近直线(0°)
};
```

通过向量点积 `dot` 判断角度类型:
- `dot ≈ 1`: 接近直线
- `dot > 0`: 钝角
- `dot < 0`: 锐角
- `dot ≈ -1`: 接近 180°

**1. MiterJoiner (斜接连接)**

核心算法:
```cpp
sinHalfAngle = sqrt((1 + dotProd) / 2)
if (sinHalfAngle < invMiterLimit) {
    // 超过斜接限制,降级为斜面连接
    goto DO_BLUNT;
}
```

对于 90° 直角特殊优化:
- 当 `dotProd == 0` 且 `invMiterLimit <= 1/√2` 时
- 直接使用 `mid = (before + after) * radius`
- 避免昂贵的三角函数计算

**2. RoundJoiner (圆角连接)**

- 使用 `SkConic::BuildUnitArc` 构建单位圆弧
- 通过矩阵变换缩放到正确的半径
- 支持顺时针和逆时针方向
- 最多使用 5 个圆锥曲线拼接完整圆弧

**3. BluntJoiner (斜面连接)**

最简单的连接方式,直接连接两个法向量端点,处理内外路径的正确连接顺序。

### 辅助函数

**is_clockwise**: 判断两个向量的旋转方向
```cpp
bool is_clockwise(const SkVector& before, const SkVector& after) {
    return before.fX * after.fY > before.fY * after.fX;  // 叉积
}
```

**HandleInnerJoin**: 处理内侧连接点
- 通过 pivot 点避免内侧出现视觉瑕疵
- 添加额外的边来填补间隙

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkPaint` | 提供 Cap 和 Join 枚举类型 |
| `SkPathBuilder` | 接收生成的几何路径 |
| `SkGeometry` | 几何计算工具 |
| `SkPointPriv` | 点和向量的旋转操作 |
| `SkMatrix` | 矩阵变换 |
| `SkConic` | 圆锥曲线构建 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `SkStroke` | 调用工厂方法获取 Cap 和 Join 处理函数 |
| `SkStrokeRec` | 间接使用,通过 SkStroke |
| 路径描边测试 | 单元测试使用 |

## 设计模式与设计决策

### 设计模式

1. **工厂方法模式**: `CapFactory` 和 `JoinFactory` 根据枚举返回函数指针
2. **策略模式**: 不同的 Cap 和 Join 实现可互换
3. **函数指针策略**: 使用函数指针避免虚函数调用开销

### 设计决策

**1. 为何使用函数指针而非虚函数?**
- 性能考虑:避免虚函数调用开销
- 描边是热路径,每个路径段都可能调用这些函数
- 函数指针可内联,虚函数难以内联

**2. 为何区分内外路径?**
- 描边产生两条轮廓线:外侧和内侧
- 连接点在两侧的处理不同
- 外侧需要填充,内侧需要避免重叠

**3. 为何使用圆锥曲线而非贝塞尔曲线?**
- 圆锥曲线可以精确表示圆弧
- 贝塞尔曲线只能近似圆弧
- 对于 90° 圆弧,一个圆锥曲线即可,贝塞尔需要多个

**4. 斜接限制的设计?**
- 防止尖锐角产生过长的斜接尖角
- 当超过限制时自动降级为斜面连接
- `invMiterLimit` 使用倒数避免除法运算

## 性能考量

### 性能优化技术

1. **特殊情况快速路径**
   - 90° 直角的特殊处理
   - 接近直线的情况直接跳过
   - 避免不必要的三角函数计算

2. **数学优化**
   - 使用 `invMiterLimit` (斜接限制的倒数)避免除法
   - 叉积判断方向比角度计算快
   - 点积判断角度范围

3. **内联优化**
   - 使用函数指针而非虚函数,便于编译器内联
   - 小型辅助函数(如 `is_clockwise`)易于内联

### 性能热点

- **MiterJoiner**: 包含平方根和条件分支,是最复杂的连接算法
- **RoundJoiner**: 需要构建多个圆锥曲线,几何计算较多
- **向量归一化**: `setLength` 操作涉及平方根运算

### 数值稳定性

1. 使用 `SkScalarNearlyZero` 进行浮点比较
2. 角度分类避免边界情况的数值误差
3. 半角正弦公式:`sin(θ/2) = √((1+cos(θ))/2)` 保证数值稳定

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkStroke.h` | 描边主类,调用此模块 |
| `src/core/SkStroke.cpp` | 描边实现 |
| `include/core/SkPaint.h` | 定义 Cap 和 Join 枚举 |
| `include/core/SkPathBuilder.h` | 路径构建器接口 |
| `src/core/SkGeometry.h` | 几何计算工具 |
| `src/core/SkPointPriv.h` | 点和向量操作 |
| `tests/StrokerTest.cpp` | 描边单元测试 |
