# SkSize

> 源文件: `include/core/SkSize.h`

## 概述
SkSize 定义了 Skia 中表示尺寸的基础数据结构，包括整数版本 SkISize 和浮点版本 SkSize。这些轻量级值类型在 Skia 的几何计算、图像处理和布局系统中无处不在，提供了类型安全且高效的尺寸表达方式。

## 架构位置
位于 Skia 核心模块 (`include/core`) 的基础层，与 SkRect、SkPoint 等几何类型并列，构成 Skia 几何系统的基石。它被图像、Surface、Canvas 等几乎所有涉及二维尺寸的组件使用。

## 主要类与结构体

### SkISize
表示整数尺寸的 POD (Plain Old Data) 结构体。

**成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fWidth | int32_t | 宽度（像素或单位） |
| fHeight | int32_t | 高度（像素或单位） |

**设计特点**:
- POD 类型，支持聚合初始化
- constexpr 构造，编译期可计算
- 位平凡（trivially copyable）

### SkSize
表示浮点尺寸的 POD 结构体。

**成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fWidth | SkScalar | 宽度（通常是 float） |
| fHeight | SkScalar | 高度（通常是 float） |

**设计特点**:
- 支持子像素精度
- 可与 SkISize 相互转换
- 提供舍入、向上/向下取整功能

## 公共 API 函数

### SkISize 函数

#### `Make(int32_t w, int32_t h)`
```cpp
static constexpr SkISize Make(int32_t w, int32_t h)
```
- **功能**: 创建指定宽高的 SkISize
- **参数**: w - 宽度, h - 高度
- **返回值**: SkISize 实例
- **特性**: constexpr 函数，编译期可求值

#### `MakeEmpty()`
```cpp
static constexpr SkISize MakeEmpty()
```
- **功能**: 创建空尺寸（0x0）
- **返回值**: {0, 0}

#### `set(int32_t w, int32_t h)`
- **功能**: 设置宽度和高度
- **参数**: 新的宽高值

#### `isZero()`
- **功能**: 检查是否为零尺寸
- **返回值**: fWidth == 0 && fHeight == 0

#### `isEmpty()`
- **功能**: 检查是否为空（任一维度 <= 0）
- **返回值**: true 表示宽或高非正数

#### `setEmpty()`
- **功能**: 将尺寸设为 0x0

#### `width()` / `height()`
- **功能**: 获取宽度/高度
- **返回值**: int32_t
- **特性**: constexpr

#### `area()`
```cpp
constexpr int64_t area() const
```
- **功能**: 计算面积
- **返回值**: int64_t，使用 64 位避免溢出
- **实现**: `SkToS64(fWidth) * SkToS64(fHeight)`

#### `equals(int32_t w, int32_t h)`
- **功能**: 比较是否等于指定宽高
- **返回值**: bool

### SkSize 函数

#### `Make(SkScalar w, SkScalar h)`
```cpp
static constexpr SkSize Make(SkScalar w, SkScalar h)
```
- **功能**: 创建浮点尺寸
- **特性**: constexpr

#### `Make(const SkISize& src)`
```cpp
static constexpr SkSize Make(const SkISize& src)
```
- **功能**: 从整数尺寸转换
- **实现**: 将 int32_t 转为 SkScalar

#### `MakeEmpty()`
- **功能**: 创建空尺寸（0.0 x 0.0）

#### `set(SkScalar w, SkScalar h)`
- **功能**: 设置浮点宽高

#### `isZero()` / `isEmpty()` / `setEmpty()`
- **功能**: 与 SkISize 相同语义

#### `width()` / `height()`
- **功能**: 获取浮点宽高
- **返回值**: SkScalar

#### `equals(SkScalar w, SkScalar h)`
- **功能**: 浮点相等比较（精确比较）

#### `toRound()` / `toCeil()` / `toFloor()`
```cpp
SkISize toRound() const;  // 四舍五入
SkISize toCeil() const;   // 向上取整
SkISize toFloor() const;  // 向下取整
```
- **功能**: 转换为整数尺寸的不同舍入模式
- **返回值**: SkISize

## 运算符重载

### 相等比较
```cpp
// SkISize
bool operator==(const SkISize& a, const SkISize& b);
bool operator!=(const SkISize& a, const SkISize& b);

// SkSize
bool operator==(const SkSize& a, const SkSize& b);
bool operator!=(const SkSize& a, const SkSize& b);
```

**实现**:
- 相等：两个维度均相等
- 不等：任一维度不等

## 核心概念

### 尺寸语义
- **非负假设**: 多数 API 假设尺寸非负，但允许负值存在
- **空尺寸**: 任一维度 ≤ 0 的尺寸被视为"空"
- **零尺寸**: 两维度均为 0 的特殊空尺寸

### isEmpty vs isZero
```cpp
SkISize a = {0, 0};     // isZero() == true, isEmpty() == true
SkISize b = {10, 0};    // isZero() == false, isEmpty() == true
SkISize c = {10, 20};   // isZero() == false, isEmpty() == false
SkISize d = {-5, 10};   // isZero() == false, isEmpty() == true (负数)
```

### 面积溢出保护
area() 使用 int64_t 避免溢出：
```cpp
SkISize huge = {50000, 50000};
int64_t area = huge.area(); // 2,500,000,000 (适合 int64_t)
// 如果用 int32_t: 50000 * 50000 会溢出
```

## 使用场景

### 图像尺寸
```cpp
SkImageInfo info = SkImageInfo::Make(
    SkISize::Make(1920, 1080),
    kRGBA_8888_SkColorType,
    kPremul_SkAlphaType
);
```

### Surface 创建
```cpp
int width = 800;
int height = 600;
auto surface = SkSurfaces::Raster(
    SkImageInfo::MakeN32Premul(width, height)
);
```

### 缩放计算
```cpp
SkSize originalSize = SkSize::Make(100.0f, 50.0f);
float scale = 1.5f;
SkSize scaledSize = SkSize::Make(
    originalSize.width() * scale,
    originalSize.height() * scale
);
```

### 舍入转换
```cpp
SkSize floatSize = SkSize::Make(123.7f, 456.3f);

SkISize rounded = floatSize.toRound();  // {124, 456}
SkISize ceiling = floatSize.toCeil();   // {124, 457}
SkISize floored = floatSize.toFloor();  // {123, 456}
```

## 内部实现细节

### POD 设计
SkISize 和 SkSize 都是 POD 类型，意味着：
- 可用 memcpy 复制
- 可用聚合初始化：`SkISize size = {100, 200};`
- 布局与 C 结构体兼容
- 无虚函数表开销

### constexpr 支持
大部分函数标记为 constexpr：
```cpp
constexpr SkISize size = SkISize::Make(10, 20);
constexpr int64_t area = size.area(); // 编译期计算
```

### SkScalar 抽象
SkSize 使用 SkScalar 而非直接使用 float：
- **当前实现**: SkScalar 通常是 float
- **历史原因**: 早期 Skia 支持 16.16 定点数
- **未来灵活性**: 理论上可切换到 double

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| `include/core/SkScalar.h` | SkScalar 类型定义 |
| `include/private/base/SkTo.h` | SkToS64 等类型转换函数 |
| `<cstdint>` | int32_t, int64_t 定义 |

### 被依赖的模块
SkSize 是基础类型，被大量模块使用：
- **SkImageInfo**: 描述图像尺寸
- **SkSurface**: Surface 尺寸
- **SkBitmap**: 位图尺寸
- **SkCanvas**: 画布尺寸
- **布局系统**: 控件尺寸计算

## 设计模式与设计决策

### 值语义
SkSize 和 SkISize 采用值语义而非引用语义：
- 轻量级（8 字节或 16 字节）
- 按值传递和返回
- 不涉及所有权问题

### 工厂方法模式
使用静态 Make 方法而非构造函数：
```cpp
SkISize size = SkISize::Make(10, 20);  // 清晰
// vs
SkISize size(10, 20);  // 也支持，但 Make 更明确
```

### 类型转换策略
提供多种舍入模式而非单一转换：
- toRound(): 最接近的整数
- toCeil(): 保守策略（放大）
- toFloor(): 激进策略（缩小）

## 性能考量

### 内存布局
```
SkISize: [int32_t width | int32_t height] = 8 bytes
SkSize:  [float width | float height] = 8 bytes
```
- 寄存器友好：可放入单个 64 位寄存器
- 缓存友好：紧凑布局

### 编译期优化
constexpr 支持允许编译期常量传播：
```cpp
constexpr SkISize HD = SkISize::Make(1920, 1080);
constexpr int64_t pixels = HD.area(); // 编译期计算
```

### 内联优化
所有成员函数都很小，容易内联：
- 零函数调用开销
- 优化器可进一步简化

## 数学特性

### 溢出安全
area() 使用 int64_t 确保：
- 最大安全尺寸: 约 92681 x 92681 (int32_t 范围)
- int64_t 可表示: 约 3,037,000,499 x 3,037,000,499

### 浮点精度
SkSize 使用 float (32 位)：
- 精度: 约 6-7 位有效数字
- 适用范围: 足够表示屏幕和打印尺寸
- 注意: 极大值时精度降低

## 边界情况

### 负尺寸
虽然罕见，但代码允许负尺寸：
```cpp
SkISize negative = {-10, -20};
negative.isEmpty(); // true (任一维度 <= 0)
```

### 零宽或零高
```cpp
SkISize zeroWidth = {0, 100};
zeroWidth.isEmpty(); // true
zeroWidth.isZero();  // false
```

### 极大尺寸
```cpp
SkISize huge = {INT32_MAX, INT32_MAX};
int64_t area = huge.area(); // 使用 64 位避免溢出
```

## 最佳实践

### 选择合适的类型
- **整数尺寸 (SkISize)**: 像素计数、纹理大小、位图维度
- **浮点尺寸 (SkSize)**: 布局计算、缩放操作、中间结果

### 验证有效性
```cpp
bool isValidSize(const SkISize& size) {
    return !size.isEmpty() && size.width() > 0 && size.height() > 0;
}
```

### 舍入策略选择
- **toRound()**: 一般用途，最小化误差
- **toCeil()**: 确保不丢失内容（如分配缓冲区）
- **toFloor()**: 确保不超出边界（如剪裁）

## 相关文件
| 文件 | 关系 |
|------|------|
| `include/core/SkRect.h` | 矩形使用 SkSize 表示尺寸 |
| `include/core/SkImageInfo.h` | 使用 SkISize 描述图像尺寸 |
| `include/core/SkSurface.h` | Surface 的宽高属性 |
| `include/core/SkPoint.h` | 位置类型，与尺寸类型互补 |
| `include/core/SkScalar.h` | SkScalar 类型定义 |
