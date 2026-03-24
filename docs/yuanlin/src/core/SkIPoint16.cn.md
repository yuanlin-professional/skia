# SkIPoint16

> 源文件
> - src/core/SkIPoint16.h

## 概述

`SkIPoint16` 是 Skia 的轻量级 16 位整数坐标点结构体,用于存储空间受限场景下的二维整数坐标。相比标准的 `SkIPoint`(使用 32 位整数),`SkIPoint16` 将内存占用减半至 4 字节,特别适合需要存储大量点坐标的场景,如字形子像素位置编码、小尺寸几何图形的顶点数据等。

该结构体提供了与 `SkIPoint` 类似的接口,支持构造、访问和设置操作,并通过 `SkToS16()` 函数保证值在 16 位范围内的安全性(Debug 模式下断言检查)。

## 架构位置

`SkIPoint16` 位于 Skia 基础类型层:

- **层级**: 底层数据结构,无依赖其他 Skia 模块
- **使用场景**:
  - 字形度量数据(`SkGlyph` 中的 `fLeft`, `fTop` 等)
  - 紧凑的几何顶点存储
  - 小范围坐标编码(如 atlas 纹理坐标)
- **替代类型**:
  - `SkIPoint`: 32 位整数点(更大范围)
  - `SkPoint`: 浮点数点(支持亚像素精度)
- **转换要求**: 值必须在 [-32768, 32767] 范围内

## 主要类与结构体

### SkIPoint16

POD 结构体(Plain Old Data),无虚函数和构造函数。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fX | int16_t | X 轴坐标(-32768 到 32767) |
| fY | int16_t | Y 轴坐标(-32768 到 32767) |

## 公共 API 函数

### 工厂方法

```cpp
static constexpr SkIPoint16 Make(int x, int y)
```

创建 `SkIPoint16` 实例,使用 `SkToS16()` 转换参数并在 Debug 模式下检查范围。

### 访问器

```cpp
int16_t x() const { return fX; }
int16_t y() const { return fY; }
```

获取 X 和 Y 坐标值。

### 修改器

```cpp
void set(int x, int y)
```

设置坐标值,同样使用 `SkToS16()` 确保安全转换。

## 内部实现细节

### SkToS16 转换

```cpp
// 定义在 include/private/base/SkTo.h
template <typename T>
constexpr int16_t SkToS16(T value) {
    SkASSERT(value >= -32768 && value <= 32767);
    return static_cast<int16_t>(value);
}
```

功能:
- **Debug 检查**: 断言值在 16 位有符号整数范围内
- **Release 直接转换**: 生产环境无额外开销
- **截断行为**: 超出范围时行为未定义(依赖编译器)

### 常量表达式支持

```cpp
static constexpr SkIPoint16 Make(int x, int y)
```

使用 `constexpr` 允许编译期计算:
```cpp
constexpr SkIPoint16 origin = SkIPoint16::Make(0, 0);  // 编译期常量
```

优点:
- 零运行时开销
- 可用于模板参数
- 优化器友好

### 内存布局

```cpp
struct SkIPoint16 {
    int16_t fX;  // 偏移 0, 2 字节
    int16_t fY;  // 偏移 2, 2 字节
};  // 总大小 4 字节,对齐 2 字节
```

- **紧凑布局**: 无填充字节
- **缓存友好**: 4 字节可以装入单个 DWORD
- **数组存储**: 1000 个点仅占用 4KB(vs SkIPoint 的 8KB)

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkTypes | 基础类型定义 |
| SkTo | 安全类型转换(`SkToS16`) |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| SkGlyph | 字形边界框坐标(`fLeft`, `fTop`) |
| SkGlyphDigest | 字形摘要中的边界信息 |
| Atlas 管理器 | 纹理坐标编码 |
| 路径剖分器 | 小范围几何顶点 |

## 设计模式与设计决策

### POD 设计

为什么使用 POD 结构而非类:
- **聚合初始化**: `SkIPoint16 p = {10, 20};`
- **内存布局保证**: 可以安全地用于跨语言接口
- **编译器优化**: 更容易内联和优化
- **零开销抽象**: 无虚函数表指针

### 命名约定一致性

遵循 Skia 的命名模式:
- `SkIPoint`: 32 位整数点
- `SkIPoint16`: 16 位整数点
- `SkPoint`: 浮点数点
- `SkPoint3`: 三维浮点数点

### 设计决策: 不提供算术运算符

为什么不重载 `operator+`, `operator-` 等:
- **溢出风险**: 16 位加法容易溢出
- **明确意图**: 强制开发者考虑范围问题
- **避免误用**: 如果需要运算,应先转换到更大类型

### 设计决策: 使用 SkToS16 而非构造函数检查

为什么在 `Make()` 和 `set()` 中使用 `SkToS16`:
- **统一转换逻辑**: 所有类型转换使用相同机制
- **条件编译**: Debug 检查,Release 无开销
- **可读性**: 明确表示"转换到 16 位"

### 设计决策: 公开成员变量

为什么 `fX` 和 `fY` 是 public:
- **POD 语义**: 允许聚合初始化
- **性能**: 避免访问器调用(虽然会被内联)
- **简洁性**: 小型结构体无需封装
- **C 兼容性**: 可以在 C 语言中使用(如果需要)

## 性能考量

### 内存占用

对比不同点类型:
- `SkIPoint16`: 4 字节
- `SkIPoint`: 8 字节
- `SkPoint`: 8 字节
- `SkPoint3`: 12 字节

应用场景:
- **字形缓存**: 1000 个字形可节省 4KB
- **网格顶点**: 10000 顶点可节省 40KB
- **缓存行利用**: 更多点可装入 L1 缓存

### 范围限制

16 位有符号整数范围: **[-32768, 32767]**

适用场景:
- 小尺寸设备(如移动设备)的像素坐标
- 相对偏移量(如字形左上角偏移)
- Atlas 纹理坐标(2048×2048 以内)

不适用场景:
- 大分辨率显示器绝对坐标(4K = 3840×2160)
- 需要精确子像素定位的场景(使用 `SkPoint`)

### 对齐与打包

```cpp
struct CompactGlyph {
    SkPackedGlyphID id;      // 4 字节
    SkIPoint16 offset;       // 4 字节
};  // 总大小 8 字节,无填充
```

vs 使用 `SkIPoint`:
```cpp
struct NormalGlyph {
    SkPackedGlyphID id;      // 4 字节
    // 4 字节填充(对齐到 8 字节)
    SkIPoint offset;         // 8 字节
};  // 总大小 16 字节
```

`SkIPoint16` 减少了结构体填充。

### SIMD 潜力

虽然 `SkIPoint16` 本身不支持 SIMD,但紧凑布局有利于批量操作:
```cpp
// 4 个 SkIPoint16 可装入 128 位 SIMD 寄存器
__m128i points = _mm_loadu_si128(reinterpret_cast<const __m128i*>(array));
```

可以使用 SIMD 指令批量处理坐标变换。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/core/SkPoint.h | 相关类型 | 浮点数点 |
| include/private/base/SkTo.h | 依赖 | SkToS16 转换函数 |
| include/core/SkTypes.h | 依赖 | int16_t 等基础类型 |
| src/core/SkGlyph.h | 使用者 | 字形边界框坐标 |
| src/gpu/AtlasTypes.h | 使用者 | GPU Atlas 坐标 |
