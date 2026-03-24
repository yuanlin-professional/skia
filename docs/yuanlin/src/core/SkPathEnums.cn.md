# SkPathEnums

> 源文件
> - src/core/SkPathEnums.h

## 概述

`SkPathEnums.h` 定义了 Skia 路径系统的核心枚举类型和相关转换函数,包括路径凸性(`SkPathConvexity`)、首方向(`SkPathFirstDirection`)以及凸性解析控制(`SkResolveConvexity`)。这些枚举类型是路径优化和渲染决策的基础。

该文件提供了丰富的辅助函数,用于枚举值之间的转换、判断和操作,确保类型安全且高效。这些定义广泛应用于路径分析、形状识别和渲染优化等场景。

## 架构位置

`SkPathEnums` 位于 Skia 路径系统的核心类型定义层:

```
include/core/
├── SkPathTypes (公共路径类型)
│   └── SkPathDirection, SkPathFillType
└── ... (其他公共类型)

src/core/
├── SkPathEnums.h (内部枚举) ← 当前组件
├── SkPath (使用枚举)
├── SkPathData (使用枚举)
└── SkPathPriv (使用枚举)
```

类型关系:
```
SkPathDirection (公共)
    ↓
SkPathFirstDirection (内部,含 kUnknown)
    ↓
SkPathConvexity (详细凸性)
```

## 主要类与结构体

### SkPathConvexity 枚举

描述路径的凸性状态。

**枚举值**:

| 枚举值 | 说明 |
|--------|------|
| kConvex_CW | 凸,顺时针 |
| kConvex_CCW | 凸,逆时针 |
| kConvex_Degenerate | 凸,但无确定方向(退化情况) |
| kConcave | 凹 |
| kUnknown | 未知(待计算) |

**用途**:
- 渲染优化(凸路径更快)
- 路径裁剪决策
- GPU 路径缓存

### SkPathFirstDirection 枚举

描述路径第一个轮廓的方向。

**枚举值**:

| 枚举值 | 数值 | 说明 |
|--------|------|------|
| kCW | 0 | 顺时针(与 SkPathDirection::kCW 相同) |
| kCCW | 1 | 逆时针(与 SkPathDirection::kCCW 相同) |
| kUnknown | 2 | 未知方向 |

**注意**:
- 前两个值与 `SkPathDirection` 数值兼容
- 允许直接转换

### SkResolveConvexity 枚举

控制是否解析凸性。

**枚举值**:

| 枚举值 | 布尔值 | 说明 |
|--------|--------|------|
| kNo | false | 不计算凸性 |
| kYes | true | 计算并返回凸性 |

**用途**:
- 性能优化(避免不必要的计算)
- 惰性求值控制

## 公共 API 函数

### 凸性判断

```cpp
// 判断是否为凸路径
static inline bool SkPathConvexity_IsConvex(SkPathConvexity cv) {
    return cv == SkPathConvexity::kConvex_CW
        || cv == SkPathConvexity::kConvex_CCW
        || cv == SkPathConvexity::kConvex_Degenerate;
}
```

### 凸性方向反转

```cpp
// 反转凸路径的方向
static inline SkPathConvexity SkPathConvexity_OppositeConvexDirection(
    SkPathConvexity cv)
{
    SkASSERT(SkPathConvexity_IsConvex(cv));
    switch (cv) {
        case SkPathConvexity::kConvex_CW:
            cv = SkPathConvexity::kConvex_CCW;
            break;
        case SkPathConvexity::kConvex_CCW:
            cv = SkPathConvexity::kConvex_CW;
            break;
        default:
            break;  // kConvex_Degenerate 不变
    }
    return cv;
}
```

### 方向到凸性转换

```cpp
// SkPathDirection 转 SkPathConvexity
static inline SkPathConvexity SkPathDirection_ToConvexity(
    SkPathDirection dir)
{
    switch (dir) {
        case SkPathDirection::kCW:
            return SkPathConvexity::kConvex_CW;
        case SkPathDirection::kCCW:
            return SkPathConvexity::kConvex_CCW;
    }
    SkUNREACHABLE;
}

// SkPathFirstDirection 转 SkPathConvexity
static inline SkPathConvexity SkPathFirstDirection_ToConvexity(
    SkPathFirstDirection dir)
{
    switch (dir) {
        case SkPathFirstDirection::kCW:
            return SkPathConvexity::kConvex_CW;
        case SkPathFirstDirection::kCCW:
            return SkPathConvexity::kConvex_CCW;
        case SkPathFirstDirection::kUnknown:
            return SkPathConvexity::kConvex_Degenerate;
    }
    SkUNREACHABLE;
}
```

### 凸性到方向转换

```cpp
// SkPathConvexity 转 SkPathDirection(可选)
static inline std::optional<SkPathDirection> SkPathConvexity_ToDirection(
    SkPathConvexity cv)
{
    if (cv == SkPathConvexity::kConvex_CW) {
        return SkPathDirection::kCW;
    }
    if (cv == SkPathConvexity::kConvex_CCW) {
        return SkPathDirection::kCCW;
    }
    return {};  // Degenerate/Concave/Unknown
}

// SkPathConvexity 转 SkPathFirstDirection
static inline SkPathFirstDirection SkPathConvexity_ToFirstDirection(
    SkPathConvexity cv)
{
    if (cv == SkPathConvexity::kConvex_CW) {
        return SkPathFirstDirection::kCW;
    }
    if (cv == SkPathConvexity::kConvex_CCW) {
        return SkPathFirstDirection::kCCW;
    }
    return SkPathFirstDirection::kUnknown;
}
```

### 方向类型转换

```cpp
// SkPathDirection 转 SkPathFirstDirection
static inline SkPathFirstDirection SkPathDirectionToFirst(
    SkPathDirection dir)
{
    return dir == SkPathDirection::kCW
        ? SkPathFirstDirection::kCW
        : SkPathFirstDirection::kCCW;
}
```

## 内部实现细节

### 枚举值设计

**SkPathFirstDirection** 数值与 `SkPathDirection` 兼容:
```cpp
enum class SkPathDirection {
    kCW  = 0,
    kCCW = 1,
};

enum class SkPathFirstDirection {
    kCW  = 0,  // 与 SkPathDirection::kCW 相同
    kCCW = 1,  // 与 SkPathDirection::kCCW 相同
    kUnknown = 2,
};
```

这允许直接转换:
```cpp
SkPathFirstDirection dir = (SkPathFirstDirection)skPathDir;
```

### 凸性判断优化

使用逻辑或表达式:
```cpp
return cv == SkPathConvexity::kConvex_CW
    || cv == SkPathConvexity::kConvex_CCW
    || cv == SkPathConvexity::kConvex_Degenerate;
```

编译器可优化为范围检查或位运算(如果枚举值连续)。

### std::optional 返回

`SkPathConvexity_ToDirection` 返回 optional:
```cpp
std::optional<SkPathDirection> result;
if (cv == SkPathConvexity::kConvex_CW) {
    result = SkPathDirection::kCW;
}
// ...
return result;  // 可能为空
```

表示某些凸性无对应方向(Degenerate/Concave)。

### SkUNREACHABLE 宏

用于标记不可达代码:
```cpp
switch (dir) {
    case SkPathDirection::kCW: return ...;
    case SkPathDirection::kCCW: return ...;
}
SkUNREACHABLE;  // 所有枚举值已处理
```

帮助编译器优化和检测错误。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkPathTypes | SkPathDirection 定义 |
| std::optional | 可选返回值 |
| 编译器宏 | SkASSERT, SkUNREACHABLE |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| SkPath | 存储凸性 |
| SkPathData | 凸性缓存 |
| SkPathPriv | 凸性计算 |
| SkPathBuilder | 凸性跟踪 |
| 渲染管线 | 凸性查询 |

## 设计模式与设计决策

### 强类型枚举

使用 `enum class`:
```cpp
enum class SkPathConvexity { ... };
```
优点:
- 类型安全
- 避免隐式转换
- 命名空间隔离

### 内联辅助函数

所有转换函数标记为 `inline`:
```cpp
static inline SkPathConvexity SkPathDirection_ToConvexity(...);
```
- 零开销抽象
- 编译时优化
- 头文件实现

### 命名约定

函数名格式:`SourceType_Operation`:
```cpp
SkPathDirection_ToConvexity
SkPathConvexity_IsConvex
SkPathConvexity_OppositeConvexDirection
```
清晰表达功能和类型关系。

### 数值兼容性

`SkPathFirstDirection` 前两个值与 `SkPathDirection` 匹配:
- 允许直接转换
- 减少运行时开销
- 保持语义清晰

### 可选返回值

使用 `std::optional` 处理部分映射:
```cpp
std::optional<SkPathDirection> SkPathConvexity_ToDirection(...)
```
- 类型安全
- 明确语义
- 避免哨兵值

## 性能考量

### 编译时常量

枚举值在编译时已知:
- 常量传播
- 死代码消除
- 分支预测优化

### 内联优化

所有函数内联:
- 无函数调用开销
- 编译器可充分优化
- 可能完全消除

### switch 优化

编译器可将 switch 转换为:
- 跳转表(值密集)
- 二分查找(值稀疏)
- 直接计算(值连续)

### 无虚函数

枚举类型:
- 无虚函数表
- 无动态分派
- 值类型语义

### 缓存友好

枚举值紧凑:
- 小内存占用(通常1字节)
- 减少缓存污染
- 快速比较

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| include/core/SkPathTypes.h | 依赖 | SkPathDirection 定义 |
| include/core/SkPath.h | 被使用 | 路径主类 |
| src/core/SkPathData.h | 被使用 | 数据容器 |
| src/core/SkPathPriv.h | 被使用 | 私有辅助 |
| src/core/SkPathBuilder.h | 被使用 | 路径构建器 |
