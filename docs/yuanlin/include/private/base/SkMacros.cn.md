# SkMacros 预处理器宏工具模块

> 源文件: `include/private/base/SkMacros.h`

## 概述
SkMacros 提供了 Skia 中常用的预处理器宏工具,包括宏拼接、字符串化、唯一名称生成、位域枚举运算符重载、内存泄漏标记等功能。该模块是 Skia 宏编程的基础设施。

## 架构位置
位于 Skia 基础工具层 (private/base),为整个代码库提供元编程支持。被几乎所有模块使用,特别是需要宏展开和代码生成的场景。

## 核心宏定义

### 宏拼接

#### `SK_MACRO_CONCAT`
```cpp
#define SK_MACRO_CONCAT(X, Y)  SK_MACRO_CONCAT_IMPL_PRIV(X, Y)
#define SK_MACRO_CONCAT_IMPL_PRIV(X, Y)  X ## Y
```
- **功能**: 拼接两个宏参数为单个符号
- **用途**: 动态构造标识符
- **示例**:
  ```cpp
  #define PREFIX foo
  SK_MACRO_CONCAT(PREFIX, 123)  // 展开为 foo123
  ```
- **实现**: 两级宏确保参数先展开再拼接

#### `SK_MACRO_APPEND_LINE`
```cpp
#define SK_MACRO_APPEND_LINE(name)  SK_MACRO_CONCAT(name, __LINE__)
```
- **功能**: 将行号附加到名称后
- **用途**: 生成唯一的局部名称
- **示例**:
  ```cpp
  // 在第 42 行
  int SK_MACRO_APPEND_LINE(temp);  // 展开为 temp42
  ```

#### `SK_MACRO_APPEND_COUNTER`
```cpp
#define SK_MACRO_APPEND_COUNTER(name)  SK_MACRO_CONCAT(name, __COUNTER__)
```
- **功能**: 将编译器计数器附加到名称后
- **用途**: 生成多个唯一名称 (比行号更可靠)
- **`__COUNTER__`**: 每次使用递增的编译器内置宏

### 字符串化

#### `SK_MACRO_STRINGIFY`
```cpp
#define SK_MACRO_STRINGIFY(X)  SK_MACRO_STRINGIFY_IMPL_PRIV(X)
#define SK_MACRO_STRINGIFY_IMPL_PRIV(X)  #X
```
- **功能**: 将宏参数转换为字符串字面量
- **用途**: 将宏值嵌入错误信息或日志
- **示例**:
  ```cpp
  #define VERSION 123
  SK_MACRO_STRINGIFY(VERSION)    // "VERSION" (直接字符串化)
  SK_MACRO_STRINGIFY(__LINE__)   // "42" (先展开再字符串化)
  ```
- **实现**: 两级宏确保参数先展开

### 内存布局控制

#### `SK_BEGIN_REQUIRE_DENSE` / `SK_END_REQUIRE_DENSE`
```cpp
#if defined(__clang__)
    #define SK_BEGIN_REQUIRE_DENSE \
        _Pragma("GCC diagnostic push") \
        _Pragma("GCC diagnostic error \"-Wpadded\"")
    #define SK_END_REQUIRE_DENSE \
        _Pragma("GCC diagnostic pop")
#else
    #define SK_BEGIN_REQUIRE_DENSE
    #define SK_END_REQUIRE_DENSE
#endif
```
- **功能**: 要求结构体内存布局紧密无填充
- **用途**: 确保哈希键、序列化数据等紧凑
- **实现**: Clang 上启用 `-Wpadded` 警告并升级为错误
- **示例**:
  ```cpp
  SK_BEGIN_REQUIRE_DENSE
  struct HashKey {
      uint32_t a;
      uint32_t b;  // 编译器不能在中间插入填充
  };
  SK_END_REQUIRE_DENSE
  ```
- **限制**: 仅 Clang 支持,其他编译器宏展开为空

### 内存泄漏标记

#### `SK_INTENTIONALLY_LEAKED`
```cpp
#if defined(__clang__) && defined(__has_feature)
    #if __has_feature(leak_sanitizer) || __has_feature(address_sanitizer)
        extern "C" {
            void __lsan_ignore_object(const void *p);
        }
        #define SK_INTENTIONALLY_LEAKED(X)  __lsan_ignore_object(X)
    #else
        #define SK_INTENTIONALLY_LEAKED(X)  ((void)0)
    #endif
#else
    #define SK_INTENTIONALLY_LEAKED(X)  ((void)0)
#endif
```
- **功能**: 标记故意泄漏的内存,避免 Leak Sanitizer 误报
- **用途**: 全局单例、程序结束时不需要释放的资源
- **实现**: 调用 LSAN 的忽略接口
- **示例**:
  ```cpp
  GlobalResource* g_resource = new GlobalResource();
  SK_INTENTIONALLY_LEAKED(g_resource);
  ```

### 初始化辅助

#### `SK_INIT_TO_AVOID_WARNING`
```cpp
#define SK_INIT_TO_AVOID_WARNING  = 0
```
- **功能**: 初始化变量以避免"可能未初始化"警告
- **用途**: 编译器无法确定变量一定被赋值的场景
- **示例**:
  ```cpp
  int value SK_INIT_TO_AVOID_WARNING;
  if (condition) {
      value = 10;
  } else {
      value = 20;
  }
  // 编译器可能警告 value 未初始化,即使逻辑上一定会被赋值
  ```

## 位域枚举宏

### `SK_MAKE_BITFIELD_OPS`
```cpp
#define SK_MAKE_BITFIELD_OPS(X) \
    inline X operator ~(X a) { ... } \
    inline X operator |(X a, X b) { ... } \
    inline X& operator |=(X& a, X b) { ... } \
    inline X operator &(X a, X b) { ... } \
    inline X& operator &=(X& a, X b) { ... }
```
- **功能**: 为 C 风格枚举定义位运算符
- **用途**: 将枚举用作位标志
- **示例**:
  ```cpp
  enum Flags {
      kFlag1 = 1 << 0,
      kFlag2 = 1 << 1,
      kFlag3 = 1 << 2,
  };
  SK_MAKE_BITFIELD_OPS(Flags)

  Flags f = kFlag1 | kFlag2;
  f &= ~kFlag1;
  ```
- **实现**: 通过底层类型 `std::underlying_type_t<X>` 进行转换

### `SK_DECL_BITFIELD_OPS_FRIENDS`
```cpp
#define SK_DECL_BITFIELD_OPS_FRIENDS(X) \
    friend X operator ~(X a); \
    friend X operator |(X a, X b); \
    // ...
```
在类内部声明友元运算符。

### `SK_MAKE_BITFIELD_CLASS_OPS`
```cpp
#define SK_MAKE_BITFIELD_CLASS_OPS(X) \
    [[maybe_unused]] constexpr SkTFlagsMask<X> operator~(X a) { ... } \
    [[maybe_unused]] constexpr X operator|(X a, X b) { ... } \
    [[maybe_unused]] constexpr bool operator&(X a, X b) { ... } \
    // ... 更多运算符
```
- **功能**: 为 `enum class` 定义类型安全的位运算
- **特殊性**:
  - `operator&` 返回 `bool` 而非枚举类型
  - `operator~` 返回 `SkTFlagsMask<X>` 支持掩码操作
- **用途**: 现代 C++ 的枚举类位标志
- **示例**:
  ```cpp
  enum class Options {
      kNone   = 0,
      kOption1 = 1 << 0,
      kOption2 = 1 << 1,
  };
  SK_MAKE_BITFIELD_CLASS_OPS(Options)

  Options opts = Options::kOption1 | Options::kOption2;
  if (opts & Options::kOption1) { ... }  // 返回 bool
  ```

### `SkTFlagsMask` 模板类
```cpp
template<typename TFlags> class SkTFlagsMask {
public:
    constexpr explicit SkTFlagsMask(TFlags value);
    constexpr explicit SkTFlagsMask(int value);
    constexpr int value() const { return fValue; }
private:
    const int fValue;
};
```
- **功能**: 包装位掩码,支持类型安全的掩码组合
- **用途**: `~` 运算符的返回类型
- **示例**:
  ```cpp
  auto mask = ~Options::kOption1;  // SkTFlagsMask<Options>
  auto combined = mask | Options::kOption2;
  ```

### `SK_DECL_BITFIELD_CLASS_OPS_FRIENDS`
在类内部声明友元运算符 (enum class 版本)。

## 内部实现细节

### 两级宏展开
```cpp
#define SK_MACRO_CONCAT(X, Y)  SK_MACRO_CONCAT_IMPL_PRIV(X, Y)
#define SK_MACRO_CONCAT_IMPL_PRIV(X, Y)  X ## Y
```
- **第一级**: 展开参数中的宏
- **第二级**: 执行 `##` 拼接操作
- **必要性**: 如果只有一级,参数不会先展开

### `[[maybe_unused]]` 属性
```cpp
[[maybe_unused]] constexpr X operator|(X a, X b) { ... }
```
- 避免未使用函数的警告
- 某些运算符可能在特定代码中未使用

### `constexpr` 运算符
位域枚举运算符声明为 `constexpr`,支持编译期计算:
```cpp
constexpr Options opts = Options::kOption1 | Options::kOption2;
```

### 类型安全的 `&` 运算符
```cpp
constexpr bool operator&(X a, X b) {
    return SkToBool(static_cast<int>(a) & static_cast<int>(b));
}
```
- 返回 `bool` 而非枚举类型
- 符合"测试标志"的语义
- 调用 `SkToBool` 确保转换为布尔值

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| `SkTo.h` | 提供 SkToBool 类型转换 |
| `<type_traits>` | std::underlying_type_t |

### 被依赖的模块
- 枚举定义 (几乎所有模块)
- 单元测试框架
- 代码生成工具
- 调试和诊断代码

## 设计模式与设计决策

### 元编程友好
提供丰富的宏工具支持代码生成和自动化。

### 类型安全的位标志
通过模板和运算符重载实现类型安全的位操作,避免错误的枚举组合。

### 条件编译的静态检查
`SK_BEGIN_REQUIRE_DENSE` 仅在支持的编译器上启用,其他平台优雅降级。

### `__COUNTER__` 优于 `__LINE__`
`SK_MACRO_APPEND_COUNTER` 更可靠:
- 多次使用在同一行也能生成不同名称
- 宏展开后计数器值固定

## 性能考量

### 编译期宏展开
所有宏在预处理阶段展开,无运行时开销。

### constexpr 运算符
位域枚举运算符可在编译期求值,优化为常量。

### 内联运算符
所有位运算符声明为 `inline`,鼓励编译器内联优化。

## 使用示例

### 生成唯一名称
```cpp
#define UNIQUE_VAR(prefix) SK_MACRO_APPEND_COUNTER(prefix)

int UNIQUE_VAR(temp);  // temp0
int UNIQUE_VAR(temp);  // temp1
int UNIQUE_VAR(temp);  // temp2
```

### 宏值字符串化
```cpp
#define VERSION_MAJOR 2
#define VERSION_MINOR 5
#define VERSION_STRING \
    SK_MACRO_STRINGIFY(VERSION_MAJOR) "." SK_MACRO_STRINGIFY(VERSION_MINOR)

const char* version = VERSION_STRING;  // "2.5"
```

### C 风格枚举位标志
```cpp
enum RenderFlags {
    kAntiAlias  = 1 << 0,
    kDither     = 1 << 1,
    kLinearText = 1 << 2,
};
SK_MAKE_BITFIELD_OPS(RenderFlags)

RenderFlags flags = kAntiAlias | kDither;
flags &= ~kAntiAlias;
if (flags & kDither) { ... }
```

### Enum Class 位标志
```cpp
enum class DrawOptions {
    kNone           = 0,
    kAntiAlias      = 1 << 0,
    kPreserveAlpha  = 1 << 1,
};
SK_MAKE_BITFIELD_CLASS_OPS(DrawOptions)

DrawOptions opts = DrawOptions::kAntiAlias | DrawOptions::kPreserveAlpha;
if (opts & DrawOptions::kAntiAlias) { ... }  // 返回 bool
opts &= ~DrawOptions::kPreserveAlpha;
```

### 紧密结构体
```cpp
SK_BEGIN_REQUIRE_DENSE
struct CacheKey {
    uint32_t id;
    uint16_t width;
    uint16_t height;
    // 编译器不能插入填充
};
SK_END_REQUIRE_DENSE

static_assert(sizeof(CacheKey) == 8, "Key must be packed");
```

### 标记故意泄漏
```cpp
static Config* GetGlobalConfig() {
    static Config* config = new Config();
    SK_INTENTIONALLY_LEAKED(config);
    return config;
}
```

### 避免未初始化警告
```cpp
int GetValue(bool useDefault) {
    int result SK_INIT_TO_AVOID_WARNING;
    if (useDefault) {
        result = 42;
    } else {
        result = ComputeValue();
    }
    return result;
}
```

## 局限性与注意事项

### `SK_BEGIN_REQUIRE_DENSE` 限制
- 仅 Clang 支持
- GCC 的 `#pragma GCC diagnostic pop` 在某些版本上不工作
- 其他编译器无检查

### `__COUNTER__` 非标准
`__COUNTER__` 是 GCC/Clang/MSVC 扩展,不是 C++ 标准的一部分。

### 位域运算符的歧义
```cpp
enum class Flags { kA = 1, kB = 2 };
SK_MAKE_BITFIELD_CLASS_OPS(Flags)

Flags f = Flags::kA | Flags::kB;  // OK
int i = static_cast<int>(f);      // 需要显式转换
```

### 宏调试困难
宏展开错误可能导致难以理解的编译错误。

## 相关文件
| 文件 | 关系 |
|------|------|
| `SkTo.h` | 提供类型转换工具 |
| 各种枚举定义 | 使用位域宏 |
| 测试框架 | 使用唯一名称生成 |

## 历史与演进
- 2018 年统一整理宏定义
- 添加 enum class 的类型安全支持
- 引入 `SK_INTENTIONALLY_LEAKED` 支持 Sanitizer
- 持续改进跨编译器兼容性
