# SkBitmaskEnum

> 源文件: `src/base/SkBitmaskEnum.h`

## 概述

SkBitmaskEnum 提供类型安全的枚举位掩码操作支持,通过模板特化和运算符重载,允许枚举类型像位标志一样使用。这是对 C++11 强类型枚举(enum class)的扩展,在保持类型安全的同时支持位运算,避免显式类型转换。

## 架构位置

- **所属子系统**: 基础设施层 (Base Infrastructure)
- **层级**: 类型系统 - 枚举扩展
- **作用域**: 为 Skia 各模块提供类型安全的位标志机制

## 主要类与结构体

### sknonstd::is_bitmask_enum<T>

类型特征模板,标记枚举是否支持位运算。

**默认定义**:
```cpp
template <typename T>
struct is_bitmask_enum : std::false_type {};
```

**用法**: 为特定枚举特化为 std::true_type。

### 运算符重载

所有运算符使用 SFINAE 模式,仅对 `is_bitmask_enum<E>::value == true` 的类型启用。

## 公共 API 函数

### `template <typename E> constexpr bool Any(E e)`
- **功能**: 检查枚举值是否有任何位被设置
- **参数**: `e` - 枚举值
- **返回值**: true 表示至少一个位为 1
- **实现**: `static_cast<underlying_type>(e) != 0`
- **约束**: E 必须是位掩码枚举

### `template <typename E> constexpr E operator|(E l, E r)`
- **功能**: 按位或运算
- **参数**: `l`, `r` - 枚举值
- **返回值**: 新的枚举值,表示 l | r
- **实现**: `static_cast<E>(underlying(l) | underlying(r))`

### `template <typename E> constexpr E& operator|=(E& l, E r)`
- **功能**: 按位或赋值运算
- **参数**: `l` - 左操作数(引用), `r` - 右操作数
- **返回值**: l 的引用
- **实现**: `l = l | r`

### `template <typename E> constexpr E operator&(E l, E r)`
- **功能**: 按位与运算
- **参数**: `l`, `r` - 枚举值
- **返回值**: 新的枚举值,表示 l & r
- **实现**: `static_cast<E>(underlying(l) & underlying(r))`

### `template <typename E> constexpr E& operator&=(E& l, E r)`
- **功能**: 按位与赋值运算
- **参数**: `l` - 左操作数(引用), `r` - 右操作数
- **返回值**: l 的引用
- **实现**: `l = l & r`

### `template <typename E> constexpr E operator^(E l, E r)`
- **功能**: 按位异或运算
- **参数**: `l`, `r` - 枚举值
- **返回值**: 新的枚举值,表示 l ^ r
- **实现**: `static_cast<E>(underlying(l) ^ underlying(r))`

### `template <typename E> constexpr E& operator^=(E& l, E r)`
- **功能**: 按位异或赋值运算
- **参数`: `l` - 左操作数(引用), `r` - 右操作数
- **返回值**: l 的引用
- **实现**: `l = l ^ r`

### `template <typename E> constexpr E operator~(E e)`
- **功能**: 按位取反运算
- **参数**: `e` - 枚举值
- **返回值**: 新的枚举值,表示 ~e
- **实现**: `static_cast<E>(~underlying(e))`

## 内部实现细节

### SFINAE 机制

所有运算符使用 `std::enable_if_t` 进行约束:
```cpp
template <typename E>
std::enable_if_t<sknonstd::is_bitmask_enum<E>::value, E>
constexpr operator|(E l, E r) {
    using U = std::underlying_type_t<E>;
    return static_cast<E>(static_cast<U>(l) | static_cast<U>(r));
}
```

**工作原理**:
- 如果 `is_bitmask_enum<E>::value == false`,`std::enable_if_t` 触发替换失败
- 编译器忽略此重载,不产生编译错误
- 仅对标记的枚举启用位运算

### 底层类型转换

```cpp
using U = std::underlying_type_t<E>;
return static_cast<E>(static_cast<U>(l) | static_cast<U>(r));
```

**步骤**:
1. 获取枚举的底层类型(通常是 int 或 unsigned)
2. 转换枚举值到底层类型
3. 执行位运算
4. 转换结果回枚举类型

### constexpr 支持

所有函数声明为 `constexpr`,允许编译时计算:
```cpp
constexpr MyFlags flags = MyFlags::A | MyFlags::B;
```

编译器在编译期完成计算,无运行时开销。

## 使用方法

### 定义位掩码枚举

```cpp
enum class MyFlags {
    None  = 0,
    Read  = 1 << 0,  // 0x01
    Write = 1 << 1,  // 0x02
    Exec  = 1 << 2,  // 0x04
};

// 启用位运算
template <>
struct sknonstd::is_bitmask_enum<MyFlags> : std::true_type {};
```

### 使用位运算

```cpp
MyFlags flags = MyFlags::Read | MyFlags::Write;
flags |= MyFlags::Exec;

if (sknonstd::Any(flags & MyFlags::Read)) {
    // 有读权限
}

flags &= ~MyFlags::Write;  // 移除写权限
```

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| std::enable_if_t | SFINAE 约束 |
| std::underlying_type_t | 获取枚举底层类型 |
| std::false_type / std::true_type | 类型特征 |

### 被依赖的模块
- **SkCanvas**: 保存标志(SaveFlags)
- **SkPath**: 路径方向和填充类型标志
- **GPU 后端**: 渲染状态标志
- **各种编解码器**: 解码选项标志

## 设计模式与设计决策

### 设计模式
1. **类型特征模式**: 使用模板特化标记类型
2. **SFINAE 模式**: 条件启用重载
3. **操作符重载模式**: 自然的语法支持

### 设计决策

**为什么不直接用整数?**
- 类型安全:防止不同枚举类型混用
- 自文档化:枚举名称清晰表达意图
- 编译时检查:错误在编译期发现

**为什么需要显式启用?**
- 避免意外启用非位标志枚举
- 明确设计意图
- 允许单个代码库中混用普通枚举和位标志枚举

**为什么使用 sknonstd 命名空间?**
- 避免污染全局命名空间
- 清晰标记为 Skia 特定扩展
- 未来可能标准化(C++23 考虑类似特性)

**为什么所有运算符都是 constexpr?**
- 支持编译时计算
- 零运行时开销
- 与常量表达式兼容

**为什么提供 Any() 函数?**
- 常见用例:检查是否有任何标志设置
- 比 `flags != MyFlags::None` 更清晰
- 避免依赖 None 枚举值存在

## 性能考量

### 编译时优化
- 所有运算符为 `constexpr`,编译时计算
- 内联函数,零调用开销
- 与直接整数运算性能相同

### 运行时性能
- **位运算**: 单个 CPU 指令
- **类型转换**: 零开销(编译期擦除)
- **Any() 检查**: 单个比较指令

### 代码生成对比

**使用位掩码枚举**:
```cpp
MyFlags flags = MyFlags::A | MyFlags::B;
```

**生成汇编**(x86-64):
```asm
mov eax, 3  ; 0x01 | 0x02 = 0x03
```

**直接用整数**:
```cpp
int flags = 1 | 2;
```

**生成汇编**(x86-64):
```asm
mov eax, 3
```

完全相同的机器码。

## 相关文件
| 文件 | 关系 |
|------|------|
| include/core/SkCanvas.h | 使用 SaveLayerFlags |
| include/core/SkPath.h | 使用 PathDirection |
| src/gpu/ 下的各文件 | GPU 状态标志 |

## 使用示例

### 示例 1: 基本位运算
```cpp
enum class Options {
    None      = 0,
    UseCache  = 1 << 0,
    Verbose   = 1 << 1,
    DryRun    = 1 << 2,
};

template <>
struct sknonstd::is_bitmask_enum<Options> : std::true_type {};

Options opts = Options::UseCache | Options::Verbose;
if (sknonstd::Any(opts & Options::Verbose)) {
    SkDebugf("Verbose mode\n");
}
```

### 示例 2: 复合赋值
```cpp
Options opts = Options::None;
opts |= Options::UseCache;
opts |= Options::DryRun;
// opts == Options::UseCache | Options::DryRun
```

### 示例 3: 检查多个标志
```cpp
Options required = Options::UseCache | Options::Verbose;
if ((opts & required) == required) {
    // 两个标志都设置了
}
```

### 示例 4: 清除标志
```cpp
opts &= ~Options::Verbose;  // 移除 Verbose 标志
```

### 示例 5: 切换标志
```cpp
opts ^= Options::DryRun;  // 切换 DryRun 标志
```

### 示例 6: 编译时计算
```cpp
constexpr Options kDefaultOpts = Options::UseCache | Options::Verbose;
static_assert(sknonstd::Any(kDefaultOpts), "Must have some options");
```

### 示例 7: 完整示例
```cpp
enum class RenderFlags {
    None       = 0,
    Antialias  = 1 << 0,
    Dither     = 1 << 1,
    LinearText = 1 << 2,
};

template <>
struct sknonstd::is_bitmask_enum<RenderFlags> : std::true_type {};

void render(RenderFlags flags) {
    if (sknonstd::Any(flags & RenderFlags::Antialias)) {
        // 启用抗锯齿
    }
    if (sknonstd::Any(flags & RenderFlags::Dither)) {
        // 启用抖动
    }
}

// 使用
RenderFlags flags = RenderFlags::Antialias | RenderFlags::Dither;
render(flags);
```

## 注意事项

1. **必须显式启用**: 忘记特化 `is_bitmask_enum` 会导致编译错误
2. **底层类型**: 默认为 int,大标志集合考虑使用 `enum class : uint32_t`
3. **None 值**: 约定俗成为 0,但不是强制要求
4. **取反运算**: `~flags` 可能包含未定义的位,使用需谨慎
5. **类型安全限制**: 不同枚举类型不能混合运算
6. **constexpr**: 非 constexpr 上下文中也可使用,但无编译时优化
7. **命名空间**: 特化必须在 sknonstd 命名空间

## 最佳实践

### 枚举定义
```cpp
enum class MyFlags : uint32_t {  // 显式指定底层类型
    None   = 0,                  // 约定 None = 0
    Flag1  = 1 << 0,             // 使用位移,清晰易读
    Flag2  = 1 << 1,
    Flag3  = 1 << 2,
    // 可选:组合标志
    Common = Flag1 | Flag2,
};
```

### 特化模板
```cpp
// 紧跟枚举定义
template <>
struct sknonstd::is_bitmask_enum<MyFlags> : std::true_type {};
```

### 检查标志
```cpp
// 推荐:使用 Any()
if (sknonstd::Any(flags & MyFlags::Flag1)) { ... }

// 避免:依赖 bool 转换
if (flags & MyFlags::Flag1) { ... }  // 不编译!
```

### 初始化
```cpp
// 推荐:明确指定 None
MyFlags flags = MyFlags::None;

// 或直接赋值
MyFlags flags = MyFlags::Flag1 | MyFlags::Flag2;
```

### 函数参数
```cpp
void processFlags(MyFlags flags);  // 值传递,位标志通常小

// 可选:默认参数
void draw(MyFlags flags = MyFlags::None);
```

## 与标准库的关系

### C++11 enum class
```cpp
enum class E { A, B };  // 强类型,但不支持位运算
```

### 传统位标志
```cpp
enum E { A = 1, B = 2 };  // 支持位运算,但无类型安全
```

### SkBitmaskEnum
```cpp
enum class E { A = 1, B = 2 };
template <> struct sknonstd::is_bitmask_enum<E> : std::true_type {};
// 两者兼得:类型安全 + 位运算
```

### 未来标准化
C++23 可能引入类似的标准特性,但目前 SkBitmaskEnum 提供最佳解决方案。

## 常见错误

### 错误 1: 忘记启用
```cpp
enum class Flags { A = 1, B = 2 };
Flags f = Flags::A | Flags::B;  // 编译错误!
```

**修复**:
```cpp
template <> struct sknonstd::is_bitmask_enum<Flags> : std::true_type {};
```

### 错误 2: 直接 bool 转换
```cpp
if (flags & MyFlags::A) { ... }  // 编译错误!
```

**修复**:
```cpp
if (sknonstd::Any(flags & MyFlags::A)) { ... }
```

### 错误 3: 混合不同枚举
```cpp
Flags1 f1;
Flags2 f2;
auto f3 = f1 | f2;  // 编译错误!(类型安全)
```

这是设计意图,防止逻辑错误。

### 错误 4: 特化在错误命名空间
```cpp
template <> struct is_bitmask_enum<MyFlags> : std::true_type {};  // 错误!
```

**修复**:
```cpp
template <> struct sknonstd::is_bitmask_enum<MyFlags> : std::true_type {};
```
