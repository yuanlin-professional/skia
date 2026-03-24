# SkParsePath

> 源文件: include/utils/SkParsePath.h, src/utils/SkParsePath.cpp

## 概述

`SkParsePath` 是 Skia 图形库中的 SVG 路径解析和序列化工具类,提供在 SVG 路径字符串与 `SkPath` 对象之间进行双向转换的功能。该模块完整实现了 W3C SVG 1.1 路径数据规范,支持所有标准 SVG 路径命令,包括移动、直线、曲线、弧线和闭合操作。

核心功能包括:从 SVG 字符串解析生成 `SkPath` 对象,以及将 `SkPath` 导出为 SVG 字符串(支持绝对和相对坐标编码)。该模块广泛应用于 SVG 渲染、矢量图形导入导出、路径序列化等场景,是 Skia SVG 支持的关键组件之一。

## 架构位置

`SkParsePath` 位于 Skia 的实用工具层,作为 SVG 路径处理的核心模块:

```
SVG 渲染器 / 矢量图形编辑器
   ↓
SkParsePath (工具层 - include/utils, src/utils)
   ↓
├── SkPathBuilder (路径构建器)
├── SkParse (基础字符串解析)
├── SkGeometry (几何计算)
└── SkPath (路径对象)
```

相关模块:
- SVG DOM 解析器使用该类解析 `<path>` 元素
- 矢量图形导入工具
- 路径调试和可视化工具

## 主要类与结构体

### SkParsePath

纯静态工具类,提供 SVG 路径字符串与 `SkPath` 对象的转换方法。

**继承关系**: 无继承关系,纯静态工具类

**关键成员变量**: 无(所有方法为静态方法)

### PathEncoding (枚举)

控制 SVG 路径输出的坐标编码方式。

| 枚举值 | 说明 |
|--------|------|
| Absolute | 使用绝对坐标(大写命令:M, L, C 等) |
| Relative | 使用相对坐标(小写命令:m, l, c 等) |

## 公共 API 函数

### FromSVGString

```cpp
static std::optional<SkPath> FromSVGString(const char str[]);
```

从 SVG 路径字符串解析生成 `SkPath` 对象。支持所有标准 SVG 路径命令。

**参数**:
- `str`: SVG 路径数据字符串(如 "M 10 10 L 20 20 Z")

**返回值**: 解析成功返回包含 `SkPath` 的 `std::optional`,失败返回空的 `std::optional`

**支持的 SVG 命令**:
- `M/m`: MoveTo (移动到)
- `L/l`: LineTo (直线到)
- `H/h`: Horizontal LineTo (水平线)
- `V/v`: Vertical LineTo (垂直线)
- `C/c`: Cubic Bezier Curve (三次贝塞尔曲线)
- `S/s`: Smooth Cubic Bezier (平滑三次贝塞尔)
- `Q/q`: Quadratic Bezier Curve (二次贝塞尔曲线)
- `T/t`: Smooth Quadratic Bezier (平滑二次贝塞尔)
- `A/a`: Arc (椭圆弧)
- `Z/z`: ClosePath (闭合路径)

**示例**:
```cpp
auto path = SkParsePath::FromSVGString("M 0 0 L 100 100 Z");
if (path) {
    // 使用解析后的路径
}
```

### FromSVGString (已弃用版本)

```cpp
static bool FromSVGString(const char str[], SkPath* outPath);
```

已弃用的旧版本 API,使用输出参数而非返回值。新代码应使用返回 `std::optional` 的版本。

### ToSVGString

```cpp
static SkString ToSVGString(const SkPath& path,
                            PathEncoding = PathEncoding::Absolute);
```

将 `SkPath` 对象转换为 SVG 路径字符串。

**参数**:
- `path`: 要序列化的路径对象
- `encoding`: 坐标编码方式(绝对或相对)

**返回值**: SVG 路径数据字符串

**示例**:
```cpp
SkPath path;
path.moveTo(10, 10);
path.lineTo(20, 20);
path.close();

SkString svg = SkParsePath::ToSVGString(path);
// svg = "M10 10L20 20Z"
```

## 内部实现细节

### 解析状态机

`FromSVGString` 使用状态机实现解析:

```cpp
char op = '\0';          // 当前命令
char previousOp = '\0';  // 前一个命令(用于平滑曲线)
bool relative = false;   // 是否相对坐标
SkPoint c = {0, 0};      // 当前点
SkPoint lastc = {0, 0};  // 最后一个控制点
SkPoint first = {0, 0};  // 路径起点
```

**主循环逻辑**:
1. 跳过空白
2. 读取命令字符或数字
3. 如果是命令字符,更新 `op` 和 `relative` 标志
4. 根据 `op` 解析对应参数
5. 调用 `SkPathBuilder` 方法添加路径段
6. 更新当前点和控制点

### 字符分类辅助函数

```cpp
static inline bool is_between(int c, int min, int max)
static inline bool is_ws(int c)      // 空白字符
static inline bool is_digit(int c)   // 数字字符
static inline bool is_sep(int c)     // 分隔符(空白或逗号)
static inline bool is_lower(int c)   // 小写字母
static inline int to_upper(int c)    // 转大写
```

### 坐标解析辅助函数

```cpp
static const char* find_points(const char str[], SkPoint value[], int count,
                               bool isRelative, SkPoint* relative)
```

解析多个点坐标,自动处理相对/绝对坐标转换。

```cpp
static const char* find_scalar(const char str[], SkScalar* value,
                               bool isRelative, SkScalar relative)
```

解析单个标量值,处理相对坐标。

```cpp
static const char* find_flag(const char str[], bool* value)
```

解析 SVG 标志值(0 或 1),用于弧线命令。

### 平滑曲线处理

`S` 和 `T` 命令实现平滑曲线:

```cpp
case 'S':  // Smooth Cubic Bezier
    data = find_points(data, &points[1], 2, relative, &c);
    points[0] = c;
    if (previousOp == 'C' || previousOp == 'S') {
        // 根据前一个控制点计算反射点
        points[0].fX -= lastc.fX - c.fX;
        points[0].fY -= lastc.fY - c.fY;
    }
    builder.cubicTo(points[0], points[1], points[2]);
```

如果前一个命令是 `C` 或 `S`,则通过反射最后一个控制点生成第一个控制点。

### 弧线解析

弧线命令 `A` 最复杂,需要解析7个参数:

```cpp
case 'A': {
    SkPoint radii;       // 椭圆半径
    SkScalar angle;      // 旋转角度
    bool largeArc;       // 大弧标志
    bool sweep;          // 顺时针标志
    // ... 解析参数
    builder.arcTo(radii, angle,
                  (SkPathBuilder::ArcSize) largeArc,
                  (SkPathDirection) !sweep,
                  points[0]);
}
```

### SVG 字符串生成

`ToSVGString` 使用 `SkPath::Iter` 遍历路径段:

```cpp
const auto append_command = [&](char cmd, const SkPoint pts[], size_t count) {
    cmd += 32 * rel_selector;  // 相对编码时转小写
    stream.write(&cmd, 1);

    for (size_t i = 0; i < count; ++i) {
        const auto pt = pts[i] - current_point;  // 计算相对坐标
        stream.writeScalarAsText(pt.fX);
        stream.write(" ", 1);
        stream.writeScalarAsText(pt.fY);
    }

    current_point = pts[count - 1] * rel_selector;
};
```

### Conic 到 Quad 的转换

Skia 的圆锥曲线不是标准 SVG,需转换为二次贝塞尔曲线:

```cpp
case SkPathVerb::kConic: {
    const SkScalar tol = SK_Scalar1 / 1024;  // 容差
    SkAutoConicToQuads quadder;
    const SkPoint* quadPts = quadder.computeQuads(
        pts.data(), rec->conicWeight(), tol);
    for (int i = 0; i < quadder.countQuads(); ++i) {
        append_command('Q', &quadPts[i*2 + 1], 2);
    }
}
```

使用 `SkAutoConicToQuads` 将圆锥曲线分解为多个二次曲线。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkPath | 路径对象表示 |
| SkPathBuilder | 构建路径的构建器模式 |
| SkParse | 基础字符串解析(FindScalar 等) |
| SkGeometry | 圆锥曲线转换(SkAutoConicToQuads) |
| SkStream | 字符串流输出 |
| SkString | 字符串类 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| SVG 渲染器 | 解析 `<path>` 元素的 `d` 属性 |
| 矢量图形导入器 | 从 SVG 文件导入路径 |
| 路径编辑器 | 提供路径的文本表示 |
| 序列化工具 | 将路径保存为 SVG 格式 |
| 测试框架 | 从字符串构造测试路径 |

## 设计模式与设计决策

### 返回 std::optional 而非布尔值

现代 C++ API 使用 `std::optional<SkPath>`:

**优点**:
- 返回值包含结果,无需输出参数
- 更符合函数式编程风格
- 编译器可优化移动语义

**使用模式**:
```cpp
if (auto path = FromSVGString(str)) {
    // 使用 *path
}
```

### 构建器模式

使用 `SkPathBuilder` 而非直接操作 `SkPath`:

**优点**:
- 构建过程更高效(延迟验证)
- 支持链式调用
- 最终通过 `detach()` 生成不可变 `SkPath`

### 状态机与 goto

解析器使用 `goto` 实现状态跳转:

```cpp
goto skipLeading;
do {
    count++;
    // ...
skipLeading:
    // ...
} while (true);
```

虽然 `goto` 通常被避免,但在解析器中用于实现清晰的状态机是合理的。

### 错误传播机制

解析函数返回 `nullptr` 表示失败:

```cpp
data = find_points(data, points, 1, relative, &c);
if (!data) {
    // 在主循环中检测到 nullptr,返回空 optional
}
```

主循环在每次迭代开始时检查:
```cpp
for (;;) {
    if (!data) {
        return {};  // 提前退出
    }
    // ...
}
```

### 相对坐标的统一处理

相对和绝对坐标在解析层统一转换为绝对坐标:

```cpp
if (isRelative) {
    for (int index = 0; index < count; index++) {
        value[index].fX += relative->fX;
        value[index].fY += relative->fY;
    }
}
```

`SkPathBuilder` 始终接收绝对坐标,简化后续处理。

### 输出优化

`ToSVGString` 使用 `SkDynamicMemoryWStream`:

- 避免频繁的字符串拼接
- 一次性分配足够内存
- 最后复制到 `SkString`

## 性能考量

### 单次遍历解析

解析器采用单次遍历策略:
- 不回溯
- 不缓冲整个输入
- 每个字符最多被检查一次

### 初始化安全

为避免 MSAN 警告,预初始化临时变量:

```cpp
SkPoint points[3] = {};  // 零初始化
SkScalar scratch = 0;
```

即使解析失败未填充所有元素,也不会产生未定义行为。

### 字符串流的高效输出

```cpp
SkDynamicMemoryWStream stream;
// 写入操作...
SkString str;
str.resize(stream.bytesWritten());
stream.copyTo(str.data());
```

避免多次重新分配和复制,一次性完成缓冲区到字符串的转换。

### Conic 转换的容差控制

```cpp
const SkScalar tol = SK_Scalar1 / 1024;
```

使用固定的容差(1/1024),平衡精度和生成的二次曲线数量。

### 相对编码的计算优化

```cpp
current_point = pts[count - 1] * rel_selector;
```

使用乘法器(0 或 1)而非条件判断:
- `rel_selector = encoding == PathEncoding::Relative ? 1 : 0`
- 避免分支预测失败

## 相关文件

| 文件路径 | 说明 |
|----------|------|
| include/utils/SkParsePath.h | 公共 API 头文件 |
| src/utils/SkParsePath.cpp | 实现文件 |
| include/core/SkPath.h | 路径对象 |
| include/core/SkPathBuilder.h | 路径构建器 |
| include/utils/SkParse.h | 基础解析工具 |
| src/core/SkGeometry.h | 几何计算工具 |
| include/core/SkStream.h | 流接口 |
| include/core/SkString.h | 字符串类 |
