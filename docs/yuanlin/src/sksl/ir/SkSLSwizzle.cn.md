# SkSL Swizzle - 向量混洗操作

> 源文件:
> - `src/sksl/ir/SkSLSwizzle.h`
> - `src/sksl/ir/SkSLSwizzle.cpp`

## 概述

`Swizzle` 表示 SkSL IR 中的向量混洗(swizzle)操作,例如 `float3(1, 2, 3).zyx`。混洗操作允许重新排列、复制或选取向量中的分量,是 GLSL/SkSL 中最常用的向量操作之一。

该实现支持多种分量命名域(坐标域 `xyzw`、颜色域 `rgba`、纹理域 `stpq`、矩形域 `LTRB`),并包含强大的编译期优化能力,可以简化混洗链、消除恒等混洗、优化构造器上的混洗等。

## 架构位置

```
SkSL 编译器
└── IR (中间表示)
    └── 表达式 (Expression)
        └── Swizzle  <-- 本文件
            ├── SwizzleComponent (枚举命名空间)
            └── ComponentArray (固定大小数组)
```

`Swizzle` 直接继承自 `Expression`,不属于构造器层次结构。它与 `ConstructorSplat`、`ConstructorCompound` 等构造器类紧密协作,在优化过程中可能相互转换。

## 主要类与结构体

### `SwizzleComponent::Type`

枚举类型,定义了所有可能的混洗分量:

| 分量组 | 值 | 说明 |
|--------|-----|------|
| 坐标域 | X(0), Y(1), Z(2), W(3) | 标准坐标分量 |
| 颜色域 | R(4), G(5), B(6), A(7) | 颜色分量 |
| 纹理域 | S(8), T(9), P(10), Q(11) | 纹理坐标分量 |
| 矩形域 | UL(12), UT(13), UR(14), UB(15) | 矩形边界分量(Left/Top/Right/Bottom) |
| 常量 | ZERO, ONE | 零和一的常量分量 |

### `ComponentArray`

```cpp
using ComponentArray = skia_private::FixedArray<4, int8_t>;
```

固定最大容量为 4 的 `int8_t` 数组,用于存储混洗分量索引。

### `Swizzle`

| 成员 | 说明 |
|------|------|
| `fBase` | 被混洗的基础表达式 |
| `fComponents` | 混洗分量数组(1-4 个分量) |

## 公共 API 函数

### `Swizzle::Convert`

```cpp
static std::unique_ptr<Expression> Convert(const Context& context,
                                           Position pos,
                                           Position maskPos,
                                           std::unique_ptr<Expression> base,
                                           std::string_view componentString);
```

完整的混洗转换方法,执行以下步骤:

1. **长度验证**: 分量字符串不超过 4 个字符
2. **字符解析**: 将字符串转换为 `ComponentArray`
3. **域验证**: 确保所有分量来自同一命名域(不能混用 `xyzw` 和 `rgba`)
4. **基类型验证**: 基表达式必须是标量或向量
5. **分量范围检查**: 验证分量索引不超出基类型的列数
6. **ZERO/ONE 处理**: 包含常量分量时,构造一个中间向量再进行二次混洗

### `Swizzle::Make`

```cpp
static std::unique_ptr<Expression> Make(const Context& context,
                                        Position pos,
                                        std::unique_ptr<Expression> expr,
                                        ComponentArray components);
```

优化版本的混洗创建方法(不支持 ZERO/ONE 分量),包含多种优化:

1. **标量展开**: `scalar.xxx` 转换为 `half3(value)`
2. **恒等消除**: `color.rgba` 这种不改变顺序的混洗被消除
3. **混洗链合并**: `foo.argb.rggg` 合并为 `foo.arrr`
4. **展开构造器优化**: `half4(scalar).zyy` 优化为 `half3(scalar)`
5. **类型转换优化**: `half4(myFloat4).zyy` 优化为 `half3(myFloat4.zyy)`
6. **复合构造器优化**: `half4(1, 2, 3, 4).yw` 优化为 `half2(2, 4)`

### `Swizzle::MakeExact`

```cpp
static std::unique_ptr<Expression> MakeExact(const Context& context,
                                             Position pos,
                                             std::unique_ptr<Expression> expr,
                                             ComponentArray components);
```

精确创建混洗节点,不进行任何简化优化。

### `Swizzle::MaskString`

```cpp
static std::string MaskString(const ComponentArray& inComponents);
```

将分量数组转换为可读的字符串表示(如 `{X, Y, Z}` -> `"xyz"`).

### `Swizzle::IsIdentity`

```cpp
static bool IsIdentity(const ComponentArray& components);
```

判断分量数组是否为恒等映射(即 `{0, 1, 2, ...}`)。

## 内部实现细节

### 混洗域验证 (`validate_swizzle_domain`)

确保所有非常量分量属于同一命名域。四个域为:
- **坐标域** (kCoordinate): x, y, z, w
- **颜色域** (kColor): r, g, b, a
- **纹理域** (kUV): s, t, p, q
- **矩形域** (kRectangle): L, T, R, B

ZERO 和 ONE 常量分量不参与域检查。

### 构造器混洗优化 (`optimize_constructor_swizzle`)

这是最复杂的优化路径,处理如 `half4(bar.yz, half2(foo)).xwxy` 这样的情况:

1. **构建参数映射** (argMap): 将构造器的每个标量位置映射到 `{参数索引, 分量索引}`
2. **使用计数**: 统计每个构造器参数被混洗引用的次数
3. **安全性检查**: 确保有副作用的表达式恰好被引用一次,非简单表达式不被重复引用
4. **重排参数**: 根据混洗分量重新组织参数列表
5. **生成新构造器**: 用重排后的参数创建新的 `ConstructorCompound`

### ZERO/ONE 分量处理

`Convert()` 方法中处理包含 `0` 和 `1` 常量分量的混洗:

```
vector.x0y0 -> 步骤:
  1. 提取非常量分量: vector.xy
  2. 构建: float4(vector.xy, 0, 1)
  3. 最终混洗: float4(vector.xy, 0, 1).xzyw
```

这种设计确保基表达式只被求值一次。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLExpression.h` | 基类 |
| `SkSLConstructorCompound.h` | 复合构造器(优化目标) |
| `SkSLConstructorCompoundCast.h` | 复合类型转换(优化路径) |
| `SkSLConstructorScalarCast.h` | 标量类型转换(优化路径) |
| `SkSLConstructorSplat.h` | 展开构造器(标量混洗替换) |
| `SkSLLiteral.h` | 字面量(ZERO/ONE 常量) |
| `SkSLConstantFolder.h` | 常量折叠(获取常量变量值) |
| `SkSLAnalysis.h` | 分析工具(副作用检测、简单表达式判断) |
| `SkFixedArray.h` | `ComponentArray` 的底层实现 |

## 设计模式与设计决策

1. **分层 API 设计**:
   - `Convert()` 处理用户输入(字符串分量),执行完整验证
   - `Make()` 处理已规范化的分量(仅 X/Y/Z/W),执行优化
   - `MakeExact()` 不做优化,用于需要精确控制的场景

2. **积极的编译期优化**: `Make()` 包含 6 种不同的优化路径,尽可能在编译期简化混洗操作

3. **ZERO/ONE 消除策略**: 在 `Convert()` 中将含常量分量的混洗转换为纯 X/Y/Z/W 混洗加上构造器,确保后续阶段不需要处理常量分量

4. **混洗域分离**: 不同命名域不可混用,这是 GLSL 规范的要求

5. **副作用安全**: 构造器优化中严格检查表达式的副作用,确保带副作用的表达式不被消除或重复执行

## 性能考量

- **恒等混洗消除**: `color.rgba` 直接返回原表达式,零开销
- **混洗链合并**: 递归合并避免了嵌套混洗链在运行时的多次间接访问
- **编译期常量优化**: 对常量展开构造器、类型转换构造器的混洗可被完全折叠
- **构造器混洗优化**: 避免了先构造完整向量再混洗的运行时开销,直接构造目标大小的向量
- `ComponentArray` 使用固定大小数组(最多 4 元素),完全避免堆分配

## 相关文件

- `src/sksl/ir/SkSLConstructorSplat.h` -- 标量混洗被转换为展开构造器
- `src/sksl/ir/SkSLConstructorCompound.h` -- 复合构造器(混洗优化的目标和来源)
- `src/sksl/ir/SkSLConstructorCompoundCast.h` -- 类型转换构造器(混洗穿透优化)
- `src/sksl/ir/SkSLConstructorScalarCast.h` -- 标量转换(混洗优化路径)
- `src/sksl/SkSLConstantFolder.h` -- 常量折叠工具
- `src/sksl/SkSLAnalysis.h` -- 表达式分析工具
- `src/base/SkFixedArray.h` -- ComponentArray 的底层固定大小数组
