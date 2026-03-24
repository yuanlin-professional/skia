# FuzzCommon - 模糊测试通用图形对象生成器

> 源文件:
> - `fuzz/FuzzCommon.h`
> - `fuzz/FuzzCommon.cpp`

## 概述

FuzzCommon 提供了一组用于模糊测试（fuzzing）的通用工具函数，能够从模糊数据中生成各种 Skia 图形对象，包括路径（SkPath）、圆角矩形（SkRRect）、矩阵（SkMatrix）、区域（SkRegion）以及运行时效果（SkRuntimeEffect）的有效输入。这些工具函数是 Skia 模糊测试基础设施的核心构建块，被多个具体的 fuzzer 共享使用。

## 架构位置

```
Skia 模糊测试基础设施
├── Fuzz (核心模糊数据读取器)
├── FuzzCommon (通用图形对象生成器)  <── 本模块
├── FuzzCanvasHelpers (Canvas 操作生成器)
└── 各种具体 fuzzer (DEF_FUZZ 注册)
```

FuzzCommon 是模糊测试层的中间件，依赖底层的 `Fuzz` 类读取数据，向上为各种具体 fuzzer 提供图形对象生成能力。

## 主要类与结构体

本模块不定义类或结构体，仅提供一组自由函数。

## 公共 API 函数

| 函数 | 描述 |
|------|------|
| `FuzzNicePath(Fuzz*, SkPathBuilder*, int maxOps)` | 生成一个"友好"的路径（排除 NaN 和无穷大）|
| `FuzzNicePath(Fuzz*, int maxOps)` | 便利重载，返回 `SkPath` |
| `FuzzEvilPath(Fuzz*, int last_verb)` | 生成一个"恶意"路径（允许所有浮点值）|
| `FuzzNiceRRect(Fuzz*, SkRRect*)` | 生成一个有效的圆角矩形 |
| `FuzzNiceMatrix(Fuzz*, SkMatrix*)` | 生成一个"友好"的变换矩阵 |
| `FuzzNiceRegion(Fuzz*, SkRegion*, int maxN)` | 生成一个区域对象 |
| `FuzzCreateValidInputsForRuntimeEffect(...)` | 为 SkRuntimeEffect 创建有效的 uniform 和子效果输入 |

## 内部实现细节

### "Nice" vs "Evil" 路径生成

- **FuzzNicePath**: 使用 `fuzz_nice_float` 过滤掉 NaN、无穷大和超大浮点值（>1.0e35），确保生成的路径坐标合理。支持 32 种操作（moveTo、lineTo、quadTo、conicTo、cubicTo、arcTo、addRect、addOval 等），并限制点数上限为 100,000 以防止指数级增长
- **FuzzEvilPath**: 直接使用原始模糊字节作为浮点值，允许 NaN 和无穷大，用于测试 Skia 对异常输入的健壮性

### 矩阵生成策略

`FuzzNiceMatrix` 生成五种类型的矩阵：
1. **单位矩阵** (type 0)
2. **平移矩阵** (type 1): 平移范围 [-4000, 4000]
3. **平移+缩放** (type 2): 缩放 [-400, 400]，平移 [-4000, 4000]
4. **仿射矩阵** (type 3): 6 个参数
5. **透视矩阵** (type 4): 9 个参数

### 圆角矩形生成

生成有效的 `SkRRect`：先生成排序后的矩形，然后为四个角各生成归一化的半径（X 半径为宽度的 0~50%，Y 半径为高度的 0~50%），确保 `isValid()` 验证通过。

### 运行时效果输入生成

`FuzzCreateValidInputsForRuntimeEffect` 为 `SkRuntimeEffect` 生成：
- **Uniform 数据**: 零初始化后填充递增的 int 或 float 值（0, 1, 2, ...）
- **子效果**: 根据类型创建简单的有效子效果：
  - Shader -> 红色纯色着色器
  - ColorFilter -> 蓝色调制混合滤镜
  - Blender -> 算术混合器

### 路径操作的安全限制

FuzzNicePath 中包含多重安全措施：
- `maxOps` 参数限制最大操作数
- 点数超过 100,000 时提前返回
- 递归调用 `FuzzNicePath` 时使用 `maxOps-1` 防止无限递归
- `valid_weight` 确保圆锥曲线权重为正数

## 依赖关系

- **核心模糊工具**: `Fuzz` 类（数据读取）
- **Skia 图形原语**: `SkPath`、`SkPathBuilder`、`SkRRect`、`SkMatrix`、`SkRegion`
- **效果系统**: `SkRuntimeEffect`、`SkColorFilter`、`SkBlenders`
- **内部工具**: `SkPathPriv`（路径内部操作，如 `ReverseAddPath`）
- **容器**: `skia_private::TArray`

## 设计模式与设计决策

- **分层抽象**: "Nice" 函数在模糊数据之上添加值域约束，"Evil" 函数直接使用原始数据，为不同测试场景提供灵活性
- **递归深度控制**: 通过 `maxOps` 参数和递归时递减防止路径操作的无限递归
- **防爆炸保护**: 多处检查路径点数上限，防止变换操作导致路径大小指数级增长
- **模板变参函数**: `fuzz_nice_float` 使用参数包展开，支持一次调用生成多个浮点值

## 性能考量

- 路径点数限制（100,000）防止了内存和时间的无限消耗
- `fuzz_nice_float` 中的值域检查是轻量级操作，不会成为瓶颈
- `FuzzEvilPath` 使用 `uint8_t` 作为操作码以减小"模糊字节足迹"，提高模糊测试效率
- 变换操作前检查 `countPoints()` 避免对大路径执行变换导致的超时

## 相关文件

- `fuzz/Fuzz.h` - 模糊数据读取器核心类
- `fuzz/FuzzCanvasHelpers.h` - Canvas 模糊测试辅助函数
- `include/core/SkPath.h` - 路径定义
- `include/core/SkPathBuilder.h` - 路径构建器
- `include/core/SkMatrix.h` - 矩阵定义
- `include/effects/SkRuntimeEffect.h` - 运行时效果
