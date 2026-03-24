# SkCallableTraits

> 源文件: src/utils/SkCallableTraits.h

## 概述

`SkCallableTraits.h` 是 Skia 图形库中实现的类型萃取(type traits)工具,用于在编译时提取可调用对象(callable)的元信息,包括返回类型、参数个数和参数类型。这是一个纯模板元编程的头文件,利用 C++ 模板特化技术实现了对各种可调用类型的统一处理。

该工具支持函数、函数指针、成员函数指针、函数对象(functor)等各种可调用类型,是 Skia 实现回调机制和泛型编程的重要基础设施。

## 架构位置

该头文件位于 Skia 的实用工具模块中:

```
src/
  └── utils/
      ├── SkCallableTraits.h  # 可调用类型萃取(本文件)
      ├── SkMetaUtils.h       # 其他元编程工具
      └── ...
```

作为模板元编程工具,它位于 Skia 架构的底层,为上层的泛型代码提供类型信息提取能力。

## 主要类与结构体

### `sk_base_callable_traits<R, Args...>`

基础萃取结构体,定义了可调用类型的核心属性:

```cpp
template <typename R, typename... Args>
struct sk_base_callable_traits {
    using return_type = R;
    static constexpr std::size_t arity = sizeof...(Args);

    template <std::size_t N>
    struct argument {
        static_assert(N < arity, "");
        using type = typename std::tuple_element<N, std::tuple<Args...>>::type;
    };
};
```

**成员**:
- `return_type`: 返回值类型
- `arity`: 参数个数(编译期常量)
- `argument<N>::type`: 第 N 个参数的类型

### `SkCallableTraits<T>`

主模板,通过递归继承机制提取类型信息:

```cpp
template <typename T>
struct SkCallableTraits : SkCallableTraits<decltype(&T::operator())> {};
```

该模板适用于函数对象(如 lambda、functor),通过提取 `operator()` 的类型来获取可调用信息。

### 特化版本

针对不同的可调用类型,提供了大量的模板特化:

1. **普通函数**: `R(Args...)`
2. **函数指针**: `R(*)(Args...)`
3. **成员函数指针**: `R(T::*)(Args...)`
4. **带 cv 限定符**: `const`, `volatile`, `const volatile`
5. **带引用限定符**: `&`, `&&`
6. **noexcept 函数**: `noexcept`(C++17)
7. **变参函数**: `...`

## 公共 API 函数

### 使用示例

```cpp
// 1. 提取普通函数类型信息
int add(int a, int b) { return a + b; }

using Traits = SkCallableTraits<decltype(add)>;
static_assert(std::is_same_v<Traits::return_type, int>);
static_assert(Traits::arity == 2);
static_assert(std::is_same_v<Traits::argument<0>::type, int>);

// 2. 提取 lambda 类型信息
auto lambda = [](float x, double y) -> bool { return x < y; };

using LambdaTraits = SkCallableTraits<decltype(lambda)>;
static_assert(std::is_same_v<LambdaTraits::return_type, bool>);
static_assert(LambdaTraits::arity == 2);
static_assert(std::is_same_v<LambdaTraits::argument<0>::type, float>);

// 3. 提取成员函数类型信息
struct Foo {
    void method(int x) const;
};

using MethodTraits = SkCallableTraits<decltype(&Foo::method)>;
static_assert(std::is_same_v<MethodTraits::return_type, void>);
static_assert(MethodTraits::arity == 1);
```

## 内部实现细节

### 宏展开技术

为了避免手动编写大量重复的模板特化代码,该文件使用了复杂的宏系统:

```cpp
#define SK_CALLABLE_TRAITS__COMMA ,

// 生成变参和非变参版本
#define SK_CALLABLE_TRAITS__VARARGS(quals, _) \
    SK_CALLABLE_TRAITS__INSTANCE(quals,) \
    SK_CALLABLE_TRAITS__INSTANCE(quals, SK_CALLABLE_TRAITS__COMMA ...)
```

这些宏通过嵌套展开,自动生成了数十个模板特化版本。

### 支持的函数类型组合

通过宏嵌套,代码覆盖了以下组合:

1. **cv 限定符**: 4 种(`无`, `const`, `volatile`, `const volatile`)
2. **引用限定符**: 3 种(`无`, `&`, `&&`)
3. **noexcept**: 2 种(有/无,C++17+)
4. **变参**: 2 种(有/无 `...`)

总共生成约 **48 种**特化版本(4 × 3 × 2 × 2)。

### 参数类型提取

参数类型提取利用 `std::tuple_element`:

```cpp
template <std::size_t N>
struct argument {
    using type = typename std::tuple_element<N, std::tuple<Args...>>::type;
};
```

这种方法将参数包 `Args...` 包装成 `std::tuple`,然后通过索引提取特定位置的类型。

### 成员变量指针支持

特殊处理成员变量指针:

```cpp
template <typename T, typename R>
struct SkCallableTraits<R T::*> : sk_base_callable_traits<
    typename std::add_lvalue_reference<R>::type
> {};
```

将成员变量指针视为返回该变量引用的可调用对象(arity = 0)。

## 依赖关系

### 标准库依赖

```cpp
#include <type_traits>  // std::tuple_element, std::add_lvalue_reference
#include <tuple>        // std::tuple
```

### 编译器特性依赖

- **C++11**: 变参模板、`constexpr`、`decltype`
- **C++17**: `__cpp_noexcept_function_type`(可选)

在不支持 noexcept 类型系统的编译器上,相关的特化会被禁用。

## 设计模式与设计决策

### 1. 模板元编程模式

使用**模板特化**和**SFINAE**(Substitution Failure Is Not An Error)实现类型萃取:
- 编译时计算,零运行时开销
- 类型安全,编译器检查
- 支持泛型编程

### 2. 宏元编程

使用宏生成重复代码:
- **优点**: 减少代码量,避免手动维护
- **缺点**: 降低代码可读性,调试困难
- **权衡**: 在可维护性和代码规模之间的平衡

### 3. 渐进式功能支持

通过条件编译支持不同 C++ 标准:

```cpp
#ifdef __cpp_noexcept_function_type
  // 支持 noexcept 类型
#else
  // 降级处理
#endif
```

这确保了在不同编译器和标准版本下的兼容性。

### 4. 单一职责原则

该工具只负责类型信息提取,不涉及:
- 运行时行为
- 对象存储
- 生命周期管理

保持了工具的专注性和可复用性。

## 性能考量

### 编译时性能

1. **编译时间**: 大量的模板特化会增加编译时间,但影响有限(通常 < 100ms)
2. **模板实例化**: 每次使用 `SkCallableTraits<T>` 会实例化对应的特化版本
3. **优化建议**: 避免在头文件中频繁使用,尽量在实现文件中使用

### 运行时性能

- **零开销**: 所有计算都在编译期完成,没有运行时开销
- **内联友好**: 编译器可以完全优化掉类型萃取代码
- **无内存占用**: 不产生任何运行时数据结构

### 实际应用示例

```cpp
// 泛型回调包装器
template <typename Func>
class CallbackWrapper {
    using Traits = SkCallableTraits<Func>;
    using ReturnType = typename Traits::return_type;

    static constexpr bool hasReturn = !std::is_void_v<ReturnType>;

    ReturnType invoke(Func f) {
        if constexpr (Traits::arity == 0) {
            return f();
        } else {
            // 处理其他情况
        }
    }
};
```

## 相关文件

### Skia 内部使用

该工具在 Skia 内部被多个模块使用:

1. **回调系统**: `src/core/SkCallback.h`
2. **函数式工具**: `src/utils/SkFunctional.h`
3. **事件处理**: `src/core/SkEventTracer.h`

### 类似工具

C++17/20 标准库提供了部分类似功能:
- `std::invoke_result` (C++17): 获取调用结果类型
- `std::is_invocable` (C++17): 检查是否可调用

但 `SkCallableTraits` 提供了更细粒度的参数信息提取。

### 扩展可能

未来可能的扩展方向:
- 支持协程(C++20)
- 支持概念(Concepts, C++20)
- 优化编译时性能

## 使用场景

### 1. 泛型回调注册

```cpp
template <typename Callback>
void registerCallback(Callback cb) {
    using Traits = SkCallableTraits<Callback>;
    static_assert(Traits::arity == 2, "Callback must take 2 arguments");
    // ...
}
```

### 2. 类型安全的函数适配器

```cpp
template <typename Func>
auto adapt(Func f) {
    using Traits = SkCallableTraits<Func>;
    if constexpr (Traits::arity == 1) {
        return [f](auto x, auto) { return f(x); };  // 忽略第二个参数
    } else {
        return f;
    }
}
```

### 3. 编译时接口验证

```cpp
template <typename T>
concept HasProcessMethod = requires(T t) {
    { t.process(int{}) } -> std::same_as<bool>;
};

template <typename T>
void checkInterface() {
    using Traits = SkCallableTraits<decltype(&T::process)>;
    static_assert(std::is_same_v<typename Traits::return_type, bool>);
}
```

该工具展示了 Skia 在模板元编程方面的深厚功力,为实现高性能、类型安全的泛型代码提供了坚实的基础。
