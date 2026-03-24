# SkSafeMath

> 源文件: src/base/SkSafeMath.h, src/base/SkSafeMath.cpp

## 概述

`SkSafeMath` 是 Skia 中用于检测整数运算溢出的安全数学工具类。它提供了加法、乘法、类型转换等操作的溢出安全版本，确保在运行时能够检测并处理算术溢出，防止安全漏洞和未定义行为。该类在所有平台上都进行运行时检查，是 Skia 内存安全策略的重要组成部分。

该工具类广泛用于内存分配计算、缓冲区大小计算、像素数据处理等需要保证算术安全性的场景。

## 架构位置

`SkSafeMath` 位于 Skia 基础设施层的安全计算模块中：

- **层级**: src/base（基础工具层）
- **用途**: 为 Skia 提供溢出安全的整数运算
- **应用场景**: 内存分配、缓冲区计算、像素处理

在 Skia 架构中，它是底层安全工具，被图像处理、内存管理、数据编解码等模块使用。

## 主要类与结构体

### SkSafeMath

溢出检测的数学运算类。

**继承关系**:
- 无继承关系

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fOK` | `bool` | 状态标志，记录是否发生过溢出，默认为 `true` |

## 公共 API 函数

### 构造函数

```cpp
SkSafeMath() = default;  // fOK 初始化为 true
```

### 状态查询

```cpp
bool ok() const;                    // 返回当前状态
explicit operator bool() const;     // 支持 if (safeMath) 语法
```

### size_t 运算

```cpp
size_t mul(size_t x, size_t y);     // 安全乘法
size_t add(size_t x, size_t y);     // 安全加法
```

- 若发生溢出，`fOK` 被设为 `false`
- 返回模运算结果（溢出时结果可能不正确，但会被 `fOK` 标记）

### int 运算

```cpp
int addInt(int a, int b);           // 安全加法（检测上溢和下溢）
int mulInt(int x, int y);           // 安全乘法（通过 int64_t 检测）
```

- 若发生溢出或下溢，`fOK` 被设为 `false`
- 返回原操作数之一（溢出时）

### 内存对齐

```cpp
size_t alignUp(size_t x, size_t alignment);  // 向上对齐到指定边界
```

- `alignment` 必须是 2 的幂
- 等价于 `(x + alignment - 1) & ~(alignment - 1)`
- 加法过程中检测溢出

### 类型转换

```cpp
template <typename TDst, typename TSrc>
TDst castTo(TSrc value);            // 安全类型转换
```

- 使用 `SkTFitsIn` 检查目标类型是否能容纳源值
- 若不能，`fOK` 被设为 `false`

### 静态饱和运算

```cpp
static size_t Add(size_t x, size_t y);  // 饱和加法
static size_t Mul(size_t x, size_t y);  // 饱和乘法
static size_t Align4(size_t x);         // 4 字节对齐（饱和）
```

- **饱和语义**: 溢出时返回 `SIZE_MAX`，而非设置错误标志

## 内部实现细节

### mul - size_t 乘法

根据平台选择实现：

```cpp
size_t mul(size_t x, size_t y) {
    return sizeof(size_t) == sizeof(uint64_t) ? mul64(x, y) : mul32(x, y);
}
```

#### mul32 - 32 位乘法

```cpp
uint32_t mul32(uint32_t x, uint32_t y) {
    uint64_t bx = x;
    uint64_t by = y;
    uint64_t result = bx * by;
    fOK &= result >> 32 == 0;  // 检查高 32 位是否为 0
    return (uint32_t)result;
}
```

- 扩展到 64 位进行乘法
- 检查高 32 位判断溢出

#### mul64 - 64 位乘法

```cpp
uint64_t mul64(uint64_t x, uint64_t y) {
    if (x <= UINT32_MAX && y <= UINT32_MAX) {
        return x * y;  // 快速路径
    }

    // 分解为高低 32 位
    auto hi = [](uint64_t x) { return x >> 32; };
    auto lo = [](uint64_t x) { return x & 0xFFFFFFFF; };

    uint64_t lx_ly = lo(x) * lo(y);
    uint64_t hx_ly = hi(x) * lo(y);
    uint64_t lx_hy = lo(x) * hi(y);
    uint64_t hx_hy = hi(x) * hi(y);

    uint64_t result = lx_ly;
    result = add(result, hx_ly << 32);
    result = add(result, lx_hy << 32);

    fOK &= (hx_hy + (hx_ly >> 32) + (lx_hy >> 32)) == 0;

    return result;
}
```

- 实现了 Karatsuba 风格的 64 位乘法
- 将每个 64 位数分解为高低 32 位分量
- 检查高位分量之和判断溢出

### add - size_t 加法

```cpp
size_t add(size_t x, size_t y) {
    size_t result = x + y;
    fOK &= result >= x;  // 无符号溢出检测
    return result;
}
```

- 利用无符号整数溢出后变小的特性检测

### addInt - int 加法

```cpp
int addInt(int a, int b) {
    if (b < 0 && a < INT_MIN - b) {
        fOK = false;
        return a;
    } else if (b > 0 && a > INT_MAX - b) {
        fOK = false;
        return a;
    }
    return a + b;
}
```

- 显式检查上溢和下溢边界

### mulInt - int 乘法

```cpp
int mulInt(int x, int y) {
    int64_t result = (int64_t)x * (int64_t)y;
    if (result > INT_MAX || result < INT_MIN) {
        fOK = false;
        return x;
    }
    return (int)result;
}
```

- 扩展到 64 位进行计算
- 检查是否超出 32 位有符号整数范围

### alignUp - 对齐计算

```cpp
size_t alignUp(size_t x, size_t alignment) {
    SkASSERT(alignment && !(alignment & (alignment - 1)));  // 断言 2 的幂
    return add(x, alignment - 1) & ~(alignment - 1);
}
```

- 先加上 `alignment - 1`，检测加法溢出
- 再清除低位完成对齐

### 静态饱和方法

```cpp
size_t SkSafeMath::Add(size_t x, size_t y) {
    SkSafeMath tmp;
    size_t sum = tmp.add(x, y);
    return tmp.ok() ? sum : SIZE_MAX;
}

size_t SkSafeMath::Mul(size_t x, size_t y) {
    SkSafeMath tmp;
    size_t prod = tmp.mul(x, y);
    return tmp.ok() ? prod : SIZE_MAX;
}
```

- 创建临时对象进行检查
- 溢出时返回最大值而非错误标志

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkAssert.h` | 提供断言宏 |
| `SkDebug.h` | 调试功能 |
| `SkTFitsIn.h` | 类型范围检查模板 |
| `<cstddef>` | `size_t` 类型定义 |
| `<cstdint>` | 固定宽度整数类型 |
| `<limits>` | 数值极限常量 |

### 被依赖的模块

`SkSafeMath` 作为基础安全工具，被以下模块广泛使用：

| 使用场景 | 说明 |
|---------|------|
| 内存分配 | 计算分配大小，防止整数溢出导致的堆溢出 |
| 图像处理 | 计算像素缓冲区大小（宽 × 高 × 字节） |
| 数据编解码 | 计算编码数据大小 |
| 缓冲区操作 | 计算数组索引和偏移量 |
| 字体渲染 | 计算字形缓存大小 |

## 设计模式与设计决策

### 设计模式

1. **累积错误模式**:
   - 多次运算共享同一个 `fOK` 标志
   - 任何一次溢出都会永久标记 `fOK = false`
   - 优点: 简化错误处理，避免每次运算后都检查

2. **显式转换操作符**:
   - `explicit operator bool()` 支持条件判断
   - 防止隐式转换导致的误用

3. **静态与实例方法分离**:
   - 实例方法: 累积错误检测
   - 静态方法: 饱和运算

### 设计决策

1. **运行时检查而非编译时**:
   - 原因: 输入值通常是运行时确定的
   - 代价: 每次运算都有少量性能开销

2. **溢出后的返回值策略**:
   - 实例方法: 返回模运算结果或原操作数（不保证正确性）
   - 静态方法: 返回 `SIZE_MAX`（饱和）
   - 原因: 调用者必须检查 `ok()` 或接受饱和语义

3. **累积 fOK 而非抛异常**:
   - 使用 `fOK &= condition` 累积错误
   - 原因: 异常在 Skia 中被禁用，布尔标志更轻量

4. **32 位与 64 位分离实现**:
   - 32 位平台使用 64 位扩展检测溢出（简单高效）
   - 64 位平台使用手动分解算法（避免需要 128 位类型）

5. **alignUp 断言而非检查**:
   - `alignment` 必须是 2 的幂由断言保证
   - 原因: 这是调用者的前置条件，不属于运行时可变输入

6. **castTo 模板设计**:
   - 使用 `SkTFitsIn` 进行通用类型检查
   - 支持任意整数类型之间的安全转换

## 性能考量

### 性能开销

1. **加法**: 约 1-2 个额外的 CPU 周期（比较和条件设置）
2. **乘法**:
   - 32 位: 约 3-5 个周期（类型提升和位检查）
   - 64 位（快速路径）: 约 2-3 个周期
   - 64 位（慢速路径）: 约 15-20 个周期（多次乘法和加法）

### 优化策略

1. **快速路径**: 64 位乘法对小值使用直接乘法
2. **内联**: 所有方法都在头文件中内联，减少调用开销
3. **短路评估**: `fOK &= condition` 利用短路避免不必要的计算

### 权衡考量

- **安全性 vs 性能**: 每次运算增加约 10-20% 开销，换取完全的溢出检测
- **适用场景**:
  - 必须使用: 内存分配大小计算
  - 推荐使用: 所有可能溢出的算术运算
  - 可不使用: 已知不会溢出的小值运算（如枚举值运算）

### 使用建议

1. **检查 ok() 的时机**:
   - 在分配内存前检查
   - 在访问数组前检查
   - 不必每次运算后都检查（累积模式）

2. **选择合适的 API**:
   - 需要精确控制错误处理 → 实例方法 + `ok()` 检查
   - 可接受饱和语义 → 静态方法（`Add`, `Mul`）

3. **与断言配合**:
   ```cpp
   SkSafeMath safe;
   size_t size = safe.mul(width, height);
   size = safe.mul(size, bytesPerPixel);
   SkASSERT(safe.ok());  // 调试版本检测
   if (!safe.ok()) {
       return nullptr;    // 发布版本处理
   }
   ```

4. **避免误用**:
   - 不要在溢出后继续使用计算结果（未定义行为）
   - 不要假设溢出后的返回值有意义

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/private/base/SkTFitsIn.h` | 类型范围检查模板 |
| `include/private/base/SkAssert.h` | 断言宏定义 |
| `include/private/base/SkMalloc.h` | 内存分配函数（使用 SkSafeMath） |
| `src/core/SkPixmap.cpp` | 像素映射（使用 SkSafeMath 计算缓冲区大小） |
| `src/codec/SkCodecPriv.h` | 编解码器工具（使用 SkSafeMath 计算数据大小） |
| `src/core/SkBitmap.cpp` | 位图实现（使用 SkSafeMath 分配像素内存） |
