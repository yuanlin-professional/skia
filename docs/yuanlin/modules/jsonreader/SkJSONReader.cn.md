# SkJSONReader - Skia JSON 解析器

> 源文件: [`modules/jsonreader/SkJSONReader.h`](../../modules/jsonreader/SkJSONReader.h), [`modules/jsonreader/SkJSONReader.cpp`](../../modules/jsonreader/SkJSONReader.cpp)

## 概述

SkJSONReader 是 Skia 内部的一个快速 JSON 解析器，位于 `skjson` 命名空间中。该解析器采用 DOM（文档对象模型）方式解析 JSON 数据，将 JSON 文本解析为不可变的值树结构。其设计目标是高性能解析，为此做了一些有意识的妥协，例如使用单精度浮点数以及部分字符串转义功能的简化。

该模块被 Skottie（Lottie 动画渲染器）等 Skia 子系统广泛使用，用于解析 JSON 格式的动画描述文件。

## 架构位置

SkJSONReader 位于 Skia 的模块层（modules），作为一个独立的 JSON 读取器模块存在。在整体架构中：

- **上层使用者**: Skottie 动画模块、测试工具等
- **同层模块**: 与 skparagraph、skottie、svg 等模块并列
- **底层依赖**: 依赖 Skia 核心库中的 SkArenaAlloc、SkStream 等基础设施

## 主要类与结构体

### `Value` 类
核心值类型，固定 64 位大小，8 字节对齐。所有 JSON 值都通过该类型表示，内部使用标签（tag）低 3 位区分类型。

```cpp
class alignas(8) Value {
public:
    enum class Type { kNull, kBool, kNumber, kString, kArray, kObject };
    Type getType() const;
    template <typename T> bool is() const;
    template <typename T> const T& as() const;
    template <typename T> operator const T*() const; // 安全转换
    SkString toString() const;
    const Value& operator[](const char* key) const; // 流式键查找
};
```

内部标签编码方案：
- `kShortString = 0b000` (内联存储)
- `kNull = 0b001`
- `kBool = 0b010` (内联存储)
- `kInt = 0b011` (内联存储)
- `kFloat = 0b100` (内联存储)
- `kString = 0b101` (指针指向外部存储)
- `kArray = 0b110` (指针指向外部存储)
- `kObject = 0b111` (指针指向外部存储)

### `NullValue` 类
表示 JSON null 值。

### `BoolValue` 类
表示 JSON 布尔值，通过 `operator*()` 获取布尔值。

### `NumberValue` 类
表示 JSON 数值，支持 int32 和 float 两种内部表示。通过 `operator*()` 获取 double 值。

### `VectorValue<T, vtype>` 模板类
数组和对象值的基类，提供 `size()`、`begin()`、`end()`、`operator[]` 等容器操作。外部存储布局为 `[size_t n][REC_0]...[REC_n-1]`。

### `StringValue` 类
表示 JSON 字符串，支持两种存储模式：
- 短字符串（<=6 字符）：内联存储在 Value 的 8 字节空间内
- 长字符串（>6 字符）：使用 VectorValue 外部存储

### `ArrayValue` 类
表示 JSON 数组，继承自 `VectorValue<Value, Type::kArray>`。

### `ObjectValue` 类
表示 JSON 对象，继承自 `VectorValue<Member, Type::kObject>`。支持通过 `operator[]` 按键查找，以及通过 `writable()` 获取可写引用。

### `Member` 结构体
对象的键值对结构，包含 `StringValue fKey` 和 `Value fValue`。

### `DOM` 类
顶层文档对象模型，负责解析整个 JSON 文档并持有内存分配器和根节点。

```cpp
class DOM final : public SkNoncopyable {
public:
    DOM(const char*, size_t);
    const Value& root() const;
    void write(SkWStream*) const;
};
```

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `Value::getType()` | 返回值的 JSON 类型 |
| `Value::is<T>()` | 检查值是否为指定门面类型 |
| `Value::as<T>()` | 无保护地转换为指定门面类型（需先确认类型正确） |
| `Value::operator const T*()` | 安全转换，类型不匹配返回 nullptr |
| `Value::toString()` | 将值序列化为 JSON 字符串 |
| `Value::operator[](const char*)` | 流式键查找，支持链式调用如 `v["foo"]["bar"]` |
| `NumberValue::operator*()` | 获取数值（返回 double） |
| `BoolValue::operator*()` | 获取布尔值 |
| `StringValue::size()` | 获取字符串长度 |
| `StringValue::begin()/end()` | 获取字符串的起止指针 |
| `StringValue::str()` | 获取 std::string_view |
| `ArrayValue::size()` | 获取数组元素数量 |
| `ObjectValue::operator[](const char*)` | 按键查找值，未找到返回 NullValue |
| `ObjectValue::writable(const char*, SkArenaAlloc&)` | 获取可写引用，键不存在时自动添加 |
| `DOM::DOM(const char*, size_t)` | 解析 JSON 文本构造 DOM |
| `DOM::root()` | 获取根节点 |
| `DOM::write(SkWStream*)` | 将 DOM 写出为 JSON |

## 内部实现细节

### 值的内存布局
Value 固定为 8 字节，使用最低 3 位作为类型标签。32 位系统上指针存储在高 4 字节中；64 位系统上指针与标签共享整个 8 字节空间（利用指针低位对齐为 0 的特性）。

### DOMParser 解析器
内部解析器采用手写递归下降/goto 跳转风格，灵感来自 rapidjson、sajson 和 pjson。解析流程：
1. 使用 `g_token_flags` 256 字节查找表加速字符分类
2. `matchString` 实现快速字符串匹配，支持转义字符解码
3. `matchFast32OrFloat` 实现优化的数字解析，优先尝试 int32，溢出时回退到 float
4. 使用值栈（fValueStack）和作用域索引（fScopeIndex）追踪嵌套结构
5. 作用域索引为正表示对象作用域，为负表示数组作用域，为零表示顶层

### FastString 优化
短字符串（<=6 字符）通过 `initFastShortString` 实现 8 字节批量加载优化。利用字符串前面必有 `"` 前缀的特点，从 `src - 1` 位置读取 8 字节，然后通过位掩码清除标签字节和尾部字节。

### 序列化（Write 函数）
使用非递归的栈式遍历实现 JSON 输出，通过特殊的 NullValue 标签指针区分数组闭合、对象闭合、列表分隔符和键分隔符。

### 字符串转义
`unescapeString` 支持标准 JSON 转义序列（`\"`, `\\`, `\/`, `\b`, `\f`, `\n`, `\r`, `\t`）以及 Unicode 转义（`\uXXXX`），将 Unicode 码点转换为 UTF-8 编码。

## 依赖关系

- `include/core/SkTypes.h` - 基本类型定义
- `include/private/base/SkNoncopyable.h` - 不可复制基类
- `src/base/SkArenaAlloc.h` - 竞技场内存分配器（所有解析结果的内存来源）
- `include/core/SkStream.h` - 流式输出（序列化用）
- `include/core/SkString.h` - Skia 字符串类
- `include/core/SkData.h` - 数据块
- `include/utils/SkParse.h` - 十六进制解析（Unicode 转义用）
- `src/base/SkUTF.h` - UTF-8 编码工具

## 设计模式与设计决策

### 门面模式（Facade Pattern）
Value 是统一的 64 位记录，通过 `is<T>()` 和 `as<T>()` 模板方法转换为具体的门面类型（NullValue、BoolValue、NumberValue 等）。这避免了虚函数开销，同时保持了类型安全。

### 竞技场分配
所有解析产生的数据（长字符串、数组、对象）都通过 SkArenaAlloc 分配，DOM 销毁时统一释放。这消除了逐个 delete 的开销，对解析大型 JSON 文档非常高效。

### 小对象优化
短字符串（<=6 字符）直接存储在 Value 的 8 字节空间内，避免额外的堆分配。数值类型（int32、float、bool）也全部内联存储。

### 仅小端支持
当前实现仅支持小端（Little-Endian）架构，大端架构会触发 static_assert 编译错误。这简化了位操作逻辑。

### 非严格解析
解析器有意选择为"快速但可能不完全符合规范"的设计。已知的妥协包括单精度浮点数和简化的字符串处理。

## 性能考量

1. **固定大小值**: 所有 Value 都是 8 字节，消除了动态分配和指针追踪的开销。
2. **查找表加速**: 使用 256 字节的 `g_token_flags` 查找表，一次查表即可判断字符类别，避免多重条件分支。
3. **快速数字解析**: 优先使用手写的快速整数/浮点数解析路径，仅在溢出或遇到指数时回退到 `strtof`。
4. **批量字符串加载**: `FastString::initFastShortString` 通过单次 8 字节 memcpy 和位掩码操作完成短字符串初始化。
5. **竞技场内存管理**: 所有解析产物都在 SkArenaAlloc 中分配（初始块 4096 字节），避免频繁的 malloc/free。
6. **内联字符串比较**: `inline_strcmp` 是一个简化版的字符串比较，避免调用标准库函数的开销。
7. **非递归序列化**: Write 函数使用显式栈代替递归，避免深层嵌套时的函数调用开销。
8. **对象查找策略**: ObjectValue 的 `find` 方法从尾部向前搜索，保证在存在重复键时返回最后一个值。

## 相关文件

- `modules/skottie/src/SkottieJson.h` / `.cpp` - Skottie 中对 JSON 解析结果的封装
- `src/base/SkArenaAlloc.h` - 竞技场分配器实现
- `include/core/SkStream.h` - 流接口定义
- `include/utils/SkParse.h` - 解析工具函数
