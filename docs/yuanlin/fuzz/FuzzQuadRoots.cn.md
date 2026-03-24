# FuzzQuadRoots

> 源文件: fuzz/FuzzQuadRoots.cpp

## 概述

FuzzQuadRoots 是一个专门用于模糊测试二次方程求根算法的模块。该文件测试 `SkQuads::RootsReal` 函数在处理各种浮点数输入时的健壮性和正确性,包括极端值、特殊浮点数(NaN、无穷大)以及可能导致数值不稳定的参数组合。通过严格的断言检查,确保求根算法返回有限、有效且不重复的根。

## 架构位置

FuzzQuadRoots 位于 Skia 的模糊测试子系统中,专注于数学基础库的可靠性测试:

```
skia/
  ├── fuzz/                        # 模糊测试根目录
  │   ├── FuzzQuadRoots.cpp       # 本文件:二次方程求根测试
  │   ├── FuzzCubicRoots.cpp      # 三次方程求根测试
  │   └── Fuzz.h                  # 模糊测试工具类
  ├── src/base/                    # 数学基础库
  │   ├── SkQuads.h/cpp           # 二次方程工具
  │   ├── SkCubics.h/cpp          # 三次方程工具
  │   └── SkUtils.h               # 通用工具函数
  └── include/private/base/        # 私有基础设施
      ├── SkAssert.h              # 断言宏
      └── SkFloatingPoint.h       # 浮点数工具
```

该模块测试的是 Skia 内部使用的数学算法,这些算法广泛应用于路径求交、曲线细分等核心图形操作。

## 主要类与结构体

### 测试辅助函数

**fuzz_quad_real_roots**
```cpp
void fuzz_quad_real_roots(double A, double B, double C)
```
- **参数**: 二次方程 Ax² + Bx + C = 0 的系数
- **作用**: 验证求根算法的正确性和健壮性
- **关键检查**:
  - 根的数量在合法范围内 [0, 2]
  - 所有根都是有限数值(非 NaN 或无穷大)
  - 两个不同的根不会重复(使用 ULP 比较)

### 核心依赖类

**SkQuads** (`src/base/SkQuads.h`)
- **静态方法**: `RootsReal(double A, double B, double C, double roots[2])`
- **功能**: 求解二次方程的实数根
- **返回值**: 实数根的数量(0、1 或 2)

## 公共 API 函数

### DEF_FUZZ(QuadRoots, fuzz)

```cpp
DEF_FUZZ(QuadRoots, fuzz)
```

**功能**: 模糊测试的主入口函数,通过宏定义注册到测试框架

**实现流程**:
1. 从模糊器获取三个随机双精度浮点数 A, B, C
2. 调用 `fuzz_quad_real_roots` 进行测试验证
3. (可选)输出调试信息用于复现失败的测试用例

**调用示例**:
```bash
# 使用 Skia 模糊测试工具运行
fuzz -t api -n QuadRoots
```

## 内部实现细节

### 求根算法验证逻辑

```cpp
static void fuzz_quad_real_roots(double A, double B, double C) {
    double roots[2];
    const int numSolutions = SkQuads::RootsReal(A, B, C, roots);

    // 检查1: 根的数量必须合法
    SkASSERT_RELEASE(numSolutions >= 0 && numSolutions <= 2);

    // 检查2: 所有根必须是有限数值
    for (int i = 0; i < numSolutions; i++) {
        SkASSERT_RELEASE(std::isfinite(roots[i]));
    }

    // 检查3: 双根情况下不应重复
    if (numSolutions == 2) {
        SkASSERT_RELEASE(!sk_doubles_nearly_equal_ulps(roots[0], roots[1]));
    }
}
```

### 关键验证点

1. **有限性检查**
   - 拒绝 NaN(Not-a-Number)
   - 拒绝 ±∞(无穷大)
   - 确保结果可用于后续计算

2. **唯一性检查**
   - 使用 ULP(Unit in the Last Place)比较算法
   - 避免将极接近的数值误判为不同的根
   - 防止算法退化到无法区分重根

3. **重要注释**
   ```cpp
   // 不建议添加"将根代入方程验证结果为零"的断言
   // 因为浮点数精度问题会导致误报
   ```
   这是对浮点数数值稳定性的深刻理解

### 测试数据生成

```cpp
double A, B, C;
fuzz->next(&A);  // 生成完全随机的双精度浮点数
fuzz->next(&B);
fuzz->next(&C);
```

**涵盖的测试场景**:
- 正常系数(小整数、常见浮点数)
- 极端值(接近 DBL_MAX、DBL_MIN)
- 特殊值(±0、次正规数)
- 病态输入(NaN、无穷大)
- 数值不稳定组合(A ≈ 0 退化为线性方程)

## 依赖关系

### 直接依赖

- **SkQuads** (`src/base/SkQuads.h`)
  - 提供二次方程求根算法
  - 核心测试目标

- **Fuzz** (`fuzz/Fuzz.h`)
  - 模糊测试框架接口
  - 提供随机数生成和输入管理

- **SkFloatingPoint** (`include/private/base/SkFloatingPoint.h`)
  - 提供 `sk_doubles_nearly_equal_ulps` 浮点比较函数
  - 提供浮点数工具函数

### 间接依赖

- **SkAssert** (`include/private/base/SkAssert.h`)
  - 提供 `SkASSERT_RELEASE` 宏
  - 在发布版本也保留的关键断言

- **C++ 标准库**
  - `<cmath>`: `std::isfinite` 检查有限性
  - `<array>`: `std::size` 获取数组大小

## 设计模式与设计决策

### 设计模式

1. **属性测试(Property-Based Testing)**
   - 不验证特定输入的特定输出
   - 验证通用属性:有限性、唯一性、数量范围

2. **预言者模式(Oracle Pattern)**
   - 使用数学属性作为"预言者"验证结果
   - 避免重新实现算法导致的测试失效

### 设计决策

1. **使用双精度浮点数**
   ```cpp
   double A, B, C;  // 不是 float
   ```
   - 避免单精度的数值误差过大
   - 更好地测试算法的精度处理

2. **发布版断言**
   ```cpp
   SkASSERT_RELEASE(...)  // 不是 SkASSERT
   ```
   - 在优化构建中仍然检查关键不变量
   - 防止隐藏的数值错误进入生产环境

3. **避免过度验证**
   - 不检查根是否满足方程(浮点误差大)
   - 专注于算法承诺的基本保证

4. **调试支持**
   ```cpp
   // 可选的调试输出(默认注释)
   // SkDebugf("A %16e (0x%lx) B %16e (0x%lx) C %16e (0x%lx)\n", ...);
   ```
   - 便于复现失败的测试用例
   - 在发现问题时可快速启用

## 性能考量

### 测试效率

1. **快速验证**
   - 求根算法时间复杂度 O(1)
   - 单次测试迭代在纳秒级完成
   - 支持每秒数百万次测试

2. **内存占用**
   - 仅使用栈内存(3个double输入 + 2个double输出)
   - 无堆分配或动态内存管理

3. **覆盖率优化**
   - 模糊器会优先探索触发不同代码路径的输入
   - 自动发现边界条件和特殊情况

### 数值稳定性

该测试隐式验证了算法的数值稳定性:
- **避免灾难性抵消**: 求根公式的减法精度损失
- **处理退化情况**: A ≈ 0 时的线性方程
- **防止溢出**: 大系数导致的中间计算溢出

## 相关文件

### 核心实现
- `src/base/SkQuads.h` - 二次方程工具类声明
- `src/base/SkQuads.cpp` - RootsReal 算法实现
- `src/base/SkCubics.h/cpp` - 三次方程工具(类似功能)

### 相关测试
- `fuzz/oss_fuzz/FuzzQuadRoots.cpp` - OSS-Fuzz 版本的二次方程测试
- `fuzz/oss_fuzz/FuzzCubicRoots.cpp` - 三次方程求根测试
- `tests/PathOpsQuadIntersectionTest.cpp` - 二次曲线求交单元测试

### 使用场景
- `src/pathops/SkPathOpsQuad.cpp` - 路径操作中的二次曲线处理
- `src/core/SkGeometry.cpp` - 几何计算模块
- `src/pathops/SkIntersections.cpp` - 曲线求交算法

### 测试基础设施
- `fuzz/Fuzz.h` - 模糊测试工具类
- `fuzz/FuzzCommon.h` - 通用辅助函数
- `include/private/base/SkFloatingPoint.h` - 浮点数工具

### 文档
- `site/dev/testing/fuzz.md` - 模糊测试使用指南
- `docs/dev/design/pathops.md` - 路径操作设计文档(使用求根算法)
