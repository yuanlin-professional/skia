# SkRandom

> 源文件: src/base/SkRandom.h

## 概述

`SkRandom` 是 Skia 中实现的伪随机数生成器（PRNG），采用 Marsaglia 的"乘进位法"（Multiply-With-Carry）算法，也称为"万能之母"（Mother of All）算法。它提供了高质量的随机数生成，具有很长的周期，所有位都得到良好的随机化。与标准库的 `rand()` 不同，`SkRandom` 维护自己的内部状态，支持多个独立实例并行使用而互不干扰。

该类专为图形学应用设计，提供了多种便捷的随机数生成方法，包括整数、浮点数、定点数、布尔值等，特别优化了 [0, 1) 范围的随机浮点数生成。

## 架构位置

`SkRandom` 位于 Skia 基础设施层的数学工具模块中：

- **层级**: src/base（基础工具层）
- **用途**: 为 Skia 提供高质量的伪随机数生成
- **应用场景**: 测试数据生成、抖动（dithering）、随机采样、模糊测试

在 Skia 架构中，它是一个独立的工具类，被测试框架、图像处理、路径操作等模块使用。

## 主要类与结构体

### SkRandom

伪随机数生成器类。

**继承关系**:
- 无继承关系

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fK` | `uint32_t` | 第一个乘进位状态变量 |
| `fJ` | `uint32_t` | 第二个乘进位状态变量 |

## 公共 API 函数

### 构造与初始化

```cpp
SkRandom();                          // 默认构造（种子为 0）
explicit SkRandom(uint32_t seed);    // 指定种子构造
SkRandom(const SkRandom& rand);      // 拷贝构造
SkRandom& operator=(const SkRandom& rand);  // 拷贝赋值
void setSeed(uint32_t seed);         // 重置种子
```

### 基础随机数生成

#### nextU - 生成 uint32_t

```cpp
uint32_t nextU();
```

返回 32 位无符号随机整数（[0, 2³² - 1]）。

**核心算法**:
```cpp
fK = kKMul * (fK & 0xFFFF) + (fK >> 16);
fJ = kJMul * (fJ & 0xFFFF) + (fJ >> 16);
return (((fK << 16) | (fK >> 16)) + fJ);
```

#### nextS - 生成 int32_t

```cpp
int32_t nextS();
```

返回 32 位有符号随机整数（[INT_MIN, INT_MAX]）。

**实现**: `(int32_t)nextU()`

### 浮点数生成

#### nextF - 生成 [0, 1) 浮点数

```cpp
float nextF();
```

返回 [0, 1) 范围内的均匀分布浮点数。

**实现**:
```cpp
uint32_t floatint = 0x3F800000 | (nextU() >> 9);  // [1.0, 2.0) 的 IEEE754 表示
float f = SkBits2Float(floatint) - 1.0f;          // 减 1 得 [0, 1)
return f;
```

**原理**:
- IEEE 754 单精度浮点数格式: `符号(1位) | 指数(8位) | 尾数(23位)`
- `0x3F800000` = 1.0 的浮点表示（指数 = 127）
- 取随机数的高 23 位作为尾数，构造 [1.0, 2.0) 的浮点数
- 减 1 得到 [0, 1)

#### nextRangeF - 生成 [min, max) 浮点数

```cpp
float nextRangeF(float min, float max);
```

返回 [min, max) 范围内的均匀分布浮点数。

**实现**: `min + nextF() * (max - min)`

### 整数生成

#### nextBits - 生成指定位数的整数

```cpp
uint32_t nextBits(unsigned bitCount);
```

返回最多 `bitCount` 位的随机无符号整数。

**参数**: `0 < bitCount <= 32`

**实现**: `nextU() >> (32 - bitCount)`

#### nextRangeU - 生成 [min, max] 无符号整数

```cpp
uint32_t nextRangeU(uint32_t min, uint32_t max);
```

返回 [min, max] 范围内的均匀分布无符号整数（闭区间）。

**实现**:
```cpp
uint32_t range = max - min + 1;
if (range == 0) {
    return nextU();  // 满范围
}
return min + nextU() % range;
```

#### nextULessThan - 生成 [0, count) 无符号整数

```cpp
uint32_t nextULessThan(uint32_t count);
```

返回 [0, count) 范围内的均匀分布无符号整数（半开区间）。

**实现**: `nextRangeU(0, count - 1)`

### SkScalar 生成（定点数/浮点数）

#### nextUScalar1 - 生成 [0, 1) SkScalar

```cpp
SkScalar nextUScalar1();
```

返回 [0, 1) 范围的 SkScalar（通常是 float）。

**实现**: `SkFixedToScalar(nextUFixed1())`

#### nextRangeScalar - 生成 [min, max) SkScalar

```cpp
SkScalar nextRangeScalar(SkScalar min, SkScalar max);
```

返回 [min, max) 范围的 SkScalar。

#### nextSScalar1 - 生成 [-1, 1) SkScalar

```cpp
SkScalar nextSScalar1();
```

返回 [-1, 1) 范围的 SkScalar。

**实现**: `SkFixedToScalar(nextSFixed1())`

### 布尔值生成

#### nextBool - 生成布尔值

```cpp
bool nextBool();
```

返回 true 或 false（50% 概率）。

**实现**: `nextU() >= 0x80000000`

#### nextBiasedBool - 生成有偏布尔值

```cpp
bool nextBiasedBool(SkScalar fractionTrue);
```

返回 true 的概率为 `fractionTrue`。

**参数**: `0 <= fractionTrue <= 1`

**实现**: `nextUScalar1() <= fractionTrue`

## 内部实现细节

### 初始化算法

```cpp
void init(uint32_t seed) {
    fK = NextLCG(seed);
    if (0 == fK) {
        fK = NextLCG(fK);  // 确保非零
    }
    fJ = NextLCG(fK);
    if (0 == fJ) {
        fJ = NextLCG(fJ);  // 确保非零
    }
    SkASSERT(0 != fK && 0 != fJ);
}

static uint32_t NextLCG(uint32_t seed) {
    return kMul * seed + kAdd;
}
```

**要点**:
- 使用线性同余生成器（LCG）初始化状态
- 确保 `fK` 和 `fJ` 都非零（乘进位法要求）
- LCG 常数来自《Numerical Recipes in C》

### 乘进位算法（MWC）

```cpp
uint32_t nextU() {
    fK = kKMul * (fK & 0xFFFF) + (fK >> 16);
    fJ = kJMul * (fJ & 0xFFFF) + (fJ >> 16);
    return (((fK << 16) | (fK >> 16)) + fJ);
}
```

**原理**:

乘进位法维护两个 32 位状态 `fK` 和 `fJ`，每个状态分为高 16 位（进位）和低 16 位（值）：

1. **更新 fK**:
   - 低 16 位乘以 `kKMul`（30345）
   - 加上高 16 位（进位）
   - 结果的低 16 位是新值，高 16 位是新进位

2. **更新 fJ**: 同理，使用 `kJMul`（18000）

3. **组合输出**:
   - 将 `fK` 的高低 16 位交换
   - 加上 `fJ`

**特性**:
- 周期极长（约 2⁶⁰）
- 所有位都得到良好随机化
- 快速计算（仅乘法和位运算）

### SkFixed 辅助方法（私有）

#### nextUFixed1 - 生成 [0, 1) 定点数

```cpp
SkFixed nextUFixed1() { return nextU() >> 16; }
```

- SkFixed 是 16.16 定点数格式
- 取随机数的高 16 位作为小数部分

#### nextSFixed1 - 生成 [-1, 1) 定点数

```cpp
SkFixed nextSFixed1() { return nextS() >> 15; }
```

- 有符号右移 15 位得到 [-32768, 32767]
- 作为 16.16 定点数即 [-1, 0.999969]

### 常数定义

```cpp
// LCG 常数（初始化用）
enum {
    kMul = 1664525,
    kAdd = 1013904223
};

// MWC 常数
enum {
    kKMul = 30345,
    kJMul = 18000,
};
```

**来源**: 《Numerical Recipes in C》（1992 年版第 284 页）

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkAssert.h` | 断言宏 |
| `SkFixed.h` | 定点数类型和转换 |
| `src/base/SkFloatBits.h` | 浮点数位操作（`SkBits2Float`） |
| `<cstdint>` | 固定宽度整数类型 |

### 被依赖的模块

`SkRandom` 作为随机数工具，被以下模块使用：

| 使用场景 | 说明 |
|---------|------|
| 单元测试 | 生成测试数据 |
| Fuzz 测试 | 生成随机输入进行模糊测试 |
| 抖动（Dithering） | 图像处理中的随机噪声 |
| 随机采样 | 路径简化、点云采样 |
| 基准测试 | 生成随机性能测试数据 |

## 设计模式与设计决策

### 设计模式

1. **值类型**:
   - 可拷贝、可赋值
   - 轻量级（仅 8 字节）
   - 适合栈分配

2. **确定性随机**:
   - 相同种子产生相同序列
   - 可重现的测试结果

### 设计决策

1. **乘进位法而非梅森旋转**:
   - 优点: 代码简单，速度快，周期足够长
   - 缺点: 周期比梅森旋转短（2⁶⁰ vs 2¹⁹⁹³⁷）
   - 原因: 图形学应用不需要密码学强度的随机性

2. **维护独立状态**:
   - 每个实例独立，不依赖全局状态
   - 优点: 线程安全，可并行使用多个实例
   - 缺点: 相比全局 `rand()` 需要传递对象

3. **浮点数生成优化**:
   - 使用位操作而非除法生成 [0, 1) 浮点数
   - 优点: 快速，均匀分布
   - 精度: 23 位尾数（float 的全部精度）

4. **确保状态非零**:
   - 初始化时强制 `fK` 和 `fJ` 非零
   - 原因: 零状态会导致退化序列

5. **提供多种便捷方法**:
   - 不同数值类型的随机数生成
   - 不同范围的随机数生成
   - 原因: 简化常见用法

6. **定点数支持**:
   - 提供 SkFixed 和 SkScalar 方法
   - 原因: 历史兼容性（Skia 曾广泛使用定点数）

7. **使用 % 实现范围映射**:
   - `nextRangeU` 使用模运算
   - 缺点: 对非 2 的幂范围有轻微偏差
   - 优点: 简单快速
   - 权衡: 偏差在图形学中可忽略

## 性能考量

### 性能特征

| 操作 | 延迟 | 说明 |
|------|------|------|
| `nextU()` | 约 3-5 ns | 2 次乘法 + 位运算 |
| `nextF()` | 约 5-7 ns | `nextU()` + 位操作 |
| `nextRangeU()` | 约 10-15 ns | `nextU()` + 取模 |
| `nextBool()` | 约 4 ns | `nextU()` + 比较 |

### 与其他 PRNG 的比较

| PRNG | 速度 | 周期 | 质量 | 状态大小 |
|------|------|------|------|---------|
| `SkRandom` (MWC) | 快 | 2⁶⁰ | 高 | 8 字节 |
| `std::minstd_rand` (LCG) | 极快 | 2³¹ | 中 | 4 字节 |
| `std::mt19937` (梅森旋转) | 中 | 2¹⁹⁹³⁷ | 极高 | 2500 字节 |
| `std::rand()` | 快 | 实现定义 | 低 | 实现定义 |

### 优化建议

1. **复用实例**:
   - 避免频繁创建销毁
   - 栈分配或作为成员变量

2. **选择合适的方法**:
   - 需要整数 → `nextU()` 或 `nextRangeU()`
   - 需要 [0, 1) 浮点数 → `nextF()`（最快）
   - 需要布尔值 → `nextBool()`

3. **避免不必要的范围映射**:
   - 若可接受全范围，直接用 `nextU()`
   - 模运算有一定开销

### 随机性质量

- **均匀性**: 优秀，所有位都均匀
- **周期**: 约 2⁶⁰（足够长，约 10¹⁸）
- **维度**: 高维均匀性良好
- **预测性**: 可预测（不适合密码学）

### 使用建议

1. **适用场景**:
   - 图形渲染（抖动、噪声）
   - 测试数据生成
   - 游戏逻辑（非关键随机性）
   - 模拟和采样

2. **不适用场景**:
   - 密码学（使用 `std::random_device`）
   - 需要极长周期的模拟（使用梅森旋转）
   - 多线程共享（每个线程独立实例）

3. **最佳实践**:
   ```cpp
   // 创建独立实例
   SkRandom rand(seed);

   // 生成随机点
   float x = rand.nextF();
   float y = rand.nextF();

   // 生成随机索引
   int index = rand.nextULessThan(count);

   // 随机决策
   if (rand.nextBool()) {
       // ...
   }
   ```

4. **种子选择**:
   - 测试: 使用固定种子确保可重现
   - 生产: 使用时间或随机设备作为种子
   ```cpp
   SkRandom rand(static_cast<uint32_t>(time(nullptr)));
   ```

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/private/base/SkFixed.h` | 定点数类型定义 |
| `src/base/SkFloatBits.h` | 浮点数位操作工具 |
| `tests/SkRandomTest.cpp` | 单元测试（验证随机性） |
| `tools/SkRandomScalerContext.cpp` | 使用随机数的字体渲染测试 |
| 《Numerical Recipes in C》 | 算法来源的参考书 |
