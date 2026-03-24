# Swizzle

> 源文件: src/gpu/Swizzle.h, src/gpu/Swizzle.cpp

## 概述

`Swizzle` 类是 Skia GPU 模块中用于表示和操作 RGBA 颜色通道重排序（swizzle）的核心工具。在 GPU 编程中，swizzle 操作用于将颜色向量的分量按照指定规则重新排列，例如将 RGBA 转换为 BGRA，或者将某个通道复制到多个输出通道（如 "rrra" 用于灰度图像）。

该类提供了编译期常量表达式（constexpr）支持，能够在编译时进行 swizzle 组合和优化。它支持六种基本通道符号：'r', 'g', 'b', 'a'（颜色通道）以及 '0' 和 '1'（常量值）。核心设计使用 16 位整数紧凑存储 4 个通道索引（每通道 4 位），实现高效的比较、组合和应用操作。

## 架构位置

```
skia/
├── src/gpu/
│   ├── Swizzle.h           # 本模块头文件
│   ├── Swizzle.cpp         # 本模块实现
│   └── SwizzlePriv.h       # 私有构造访问器
└── src/core/
    └── SkRasterPipeline.h  # 光栅化管线（应用 swizzle）
```

`Swizzle` 类位于 `src/gpu/` 命名空间 `skgpu` 中，是 GPU 渲染管线中处理纹理格式和像素布局差异的基础工具。它不依赖于特定 GPU 后端（Ganesh 或 Graphite），而是提供跨后端的通道重排功能。该类与纹理格式、帧缓冲配置、以及 fragment shader 生成密切相关。

## 主要类与结构体

### Swizzle 类

**继承关系**: 无继承，值语义类型

**关键成员变量**:

| 成员类型 | 名称 | 说明 |
|---------|------|------|
| `uint16_t` | `fKey` | 紧凑存储的 swizzle 键值，每 4 位表示一个输出通道的源通道索引 |

**通道索引映射**:

| 字符 | 整数值 | 含义 |
|------|-------|------|
| 'r' | 0 | 红色通道 |
| 'g' | 1 | 绿色通道 |
| 'b' | 2 | 蓝色通道 |
| 'a' | 3 | Alpha 通道 |
| '0' | 4 | 常量 0.0 |
| '1' | 5 | 常量 1.0 |

**存储布局**:
```
fKey 的 16 位布局：
[15:12] = 第 3 个输出通道 (a)
[11:8]  = 第 2 个输出通道 (b)
[7:4]   = 第 1 个输出通道 (g)
[3:0]   = 第 0 个输出通道 (r)
```

### 通道重排逻辑

例如 "bgra" 的编码：
- 输出 R (位 [3:0]) = 'b' = 2
- 输出 G (位 [7:4]) = 'g' = 1
- 输出 B (位 [11:8]) = 'r' = 0
- 输出 A (位 [15:12]) = 'a' = 3
- fKey = 0x3012

## 公共 API 函数

### 构造与比较

```cpp
constexpr Swizzle()                          // 默认构造，等价于 "rgba"
explicit constexpr Swizzle(const char c[4])  // 从 4 字符字符串构造
constexpr bool operator==(const Swizzle&)    // 相等比较
constexpr bool operator!=(const Swizzle&)    // 不等比较
```

### 关键操作

#### 1. Concat - 组合 Swizzle

```cpp
static constexpr Swizzle Concat(const Swizzle& a, const Swizzle& b)
```

**功能**: 计算 `a ∘ b`，即先应用 `b` 再应用 `a`
**示例**:
```cpp
Swizzle a("bgra");  // 交换 R 和 B
Swizzle b("rgb1");  // 强制 A = 1
Swizzle c = Swizzle::Concat(a, b);  // 结果: "brg1"
```

**实现逻辑**:
- 遍历 `b` 的每个输出通道
- 如果该通道引用常量 ('0' 或 '1')，保持常量
- 否则，从 `a` 中查找对应的源通道

#### 2. invert - 反转 Swizzle

```cpp
constexpr Swizzle invert() const
```

**功能**: 计算近似逆运算
**规则**:
- 如果 swizzle 是一对一映射（无重复，无常量），则返回精确逆
- 重复通道映射到最早出现的位置
- 未映射的通道使用默认值（RGB 为 '0'，A 为 '1'）

**示例**:
```cpp
Swizzle("bgra").invert() -> "bgra"  // 精确逆
Swizzle("rrra").invert() -> "r001"  // r 映射到 0, g/b 未映射, a 映射到 3
```

#### 3. selectChannelInR - 选择单一通道

```cpp
constexpr Swizzle selectChannelInR(int i) const
```

**功能**: 提取第 `i` 个通道到 R 位置，其余设为 0
**示例**:
```cpp
Swizzle("bgra").selectChannelInR(1) -> "g000"
Swizzle("argb").selectChannelInR(3) -> "b000"
```

#### 4. applyTo - 应用到颜色值

```cpp
constexpr std::array<float, 4> applyTo(std::array<float, 4> color) const
template <SkAlphaType AlphaType>
constexpr SkRGBA4f<AlphaType> applyTo(SkRGBA4f<AlphaType> color) const
```

**功能**: 在编译时或运行时对颜色值应用 swizzle 变换
**示例**:
```cpp
Swizzle("bgra").applyTo({1.0f, 0.5f, 0.25f, 1.0f})
// 结果: {0.25f, 0.5f, 1.0f, 1.0f}
```

#### 5. apply - 应用到光栅管线

```cpp
void apply(SkRasterPipeline* pipeline) const
```

**功能**: 将 swizzle 作为操作阶段添加到光栅化管线
**优化**:
- 对常见 swizzle（rgba, bgra, aaa1 等）使用专用管线操作
- 其他情况使用通用 swizzle 操作，通过 context 传递字符映射

### 预定义 Swizzle

```cpp
static constexpr Swizzle RGBA() { return Swizzle("rgba"); }  // 恒等
static constexpr Swizzle BGRA() { return Swizzle("bgra"); }  // R<->B 交换
static constexpr Swizzle RRRA() { return Swizzle("rrra"); }  // 灰度图
static constexpr Swizzle RGB1() { return Swizzle("rgb1"); }  // 不透明
```

### 查询方法

```cpp
constexpr uint16_t asKey() const         // 获取紧凑键值
SkString asString() const                // 转换为字符串（调试用）
constexpr char operator[](int i) const   // 获取第 i 个输出通道的源字符
```

## 内部实现细节

### 编译时常量表达式优化

所有核心操作（构造、组合、反转、应用）都标记为 `constexpr`，这意味着：
1. 编译器可以在编译时计算 swizzle 组合链
2. 减少运行时开销
3. 支持模板元编程和静态断言

### ComponentIndexToFloat 实现

```cpp
constexpr float ComponentIndexToFloat(std::array<float, 4> color, size_t idx)
```

**逻辑**:
- 如果 `idx <= 3`，返回 `color[idx]`（正常通道）
- 如果 `idx == CToI('1')`，返回 1.0f
- 如果 `idx == CToI('0')`，返回 0.0f

这种实现允许在 `constexpr` 上下文中处理常量通道。

### apply 的光栅管线优化

针对常见 swizzle 使用专用管线操作：

| Swizzle | 管线操作 | 说明 |
|---------|---------|------|
| "rgba" | (无操作) | 恒等变换，直接返回 |
| "bgra" | `swap_rb` | 交换红蓝通道 |
| "aaa1" | `alpha_to_gray` | Alpha 转灰度 |
| "rgb1" | `force_opaque` | 强制不透明 |
| "a001" | `alpha_to_red` | Alpha 转红色 |
| 其他 | `swizzle` + context | 通用 swizzle 操作 |

### 通用 swizzle 的 context 编码

对于非预定义的 swizzle，`apply` 函数将 16 位的 `fKey` 扩展为 32 位字符表示（每字符 8 位），并通过 `uintptr_t` 传递给管线：

```cpp
uint32_t charBits = (IToC((fKey >> 0)  & 0xfU) << 0)  |
                    (IToC((fKey >> 4)  & 0xfU) << 8)  |
                    (IToC((fKey >> 8)  & 0xfU) << 16) |
                    (IToC((fKey >> 12) & 0xfU) << 24);
uintptr_t ctx = static_cast<uintptr_t>(charBits);
pipeline->append(SkRasterPipelineOp::swizzle, ctx);
```

这种设计利用了 `uintptr_t` 至少 4 字节的保证，避免了堆分配。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkColor.h` | 颜色类型定义 |
| `SkString.h` | 字符串表示 |
| `SkRasterPipeline.h` | 光栅管线集成 |
| `SkRasterPipelineOpList.h` | 管线操作枚举 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| GPU 纹理格式处理 | 处理不同纹理格式的通道布局差异 |
| GrFragmentProcessor | 在 shader 中生成 swizzle 代码 |
| 帧缓冲配置 | 调整颜色输出格式 |
| 图像解码 | 处理不同图像格式的通道顺序 |

## 设计模式与设计决策

### 设计模式

1. **值对象模式**: `Swizzle` 是不可变的值类型，支持拷贝和比较
2. **编译时计算模式**: 广泛使用 `constexpr` 实现零成本抽象
3. **策略模式**: 预定义常见 swizzle 作为特殊优化策略

### 设计决策

**为什么使用 16 位整数存储？**
- 4 个通道 × 4 位 = 16 位，紧凑且高效
- 支持 6 种通道选择（需要 3 位，但 4 位对齐更好）
- 可直接用作哈希键或缓存键

**为什么支持 '0' 和 '1' 常量？**
- GPU 纹理格式可能缺少某些通道（如 RGB 纹理默认 A=1）
- 允许在 swizzle 阶段插入固定值，避免额外的 shader 操作

**为什么 invert 不要求精确逆？**
- 并非所有 swizzle 都可逆（如 "rrra" 丢失了 g 和 b 信息）
- 提供"最佳努力"逆运算，用于某些优化场景
- 调用方负责验证逆运算是否满足需求

**为什么不使用虚函数？**
- `Swizzle` 需要在编译时可计算
- 值语义比继承更轻量
- 内联和 constexpr 带来更好的性能

### Concat 的结合律

Swizzle 组合满足结合律：
```cpp
Concat(a, Concat(b, c)) == Concat(Concat(a, b), c)
```

但**不满足交换律**：
```cpp
Concat(a, b) != Concat(b, a)  // 一般情况
```

## 性能考量

### 内存占用

- 单个 `Swizzle` 对象：2 字节（`uint16_t`）
- 可高效存储在缓存行中
- 支持按值传递而无性能损失

### 运算性能

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| 构造 | O(1) | 编译时计算 |
| 比较 | O(1) | 单次整数比较 |
| Concat | O(1) | 4 次位操作和查表 |
| invert | O(1) | 固定循环次数 |
| applyTo | O(1) | 4 次数组访问 |
| apply (管线) | O(1) | 添加单个管线阶段 |

### 编译时优化示例

```cpp
// 以下计算在编译时完成
constexpr Swizzle s1("bgra");
constexpr Swizzle s2("argb");
constexpr Swizzle combined = Swizzle::Concat(s1, s2);
// combined 的 fKey 值已在编译时确定
```

### 光栅管线性能

- **预定义 swizzle**: 使用专用 SIMD 操作，性能最优
- **通用 swizzle**: 需要额外的查表，但仍高效
- **避免多次 swizzle**: 应在上层合并 swizzle 链

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/Swizzle.h` | 定义 | 主头文件 |
| `src/gpu/Swizzle.cpp` | 实现 | `apply` 和 `asString` 实现 |
| `src/gpu/SwizzlePriv.h` | 辅助 | 提供私有构造函数访问器 `SwizzleCtorAccessor` |
| `src/core/SkRasterPipeline.h` | 依赖 | 光栅管线接口 |
| `src/core/SkRasterPipelineOpList.h` | 依赖 | 管线操作定义 |
| `include/core/SkColor.h` | 依赖 | 颜色类型 |
| GPU 后端代码 | 被依赖 | Ganesh 和 Graphite 的纹理/格式处理模块 |
