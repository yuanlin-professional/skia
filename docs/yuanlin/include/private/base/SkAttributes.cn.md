# SkAttributes

> 源文件: `include/private/base/SkAttributes.h`

## 概述
SkAttributes 提供了一套跨平台的编译器属性宏,用于控制函数的内联行为、格式化参数检查和代码生成优化。它抽象了不同编译器(GCC、Clang、MSVC)的属性语法,为 Skia 提供统一的属性标记接口。

## 架构位置
该头文件位于 Skia 基础设施层的编译器接口子系统,属于底层工具层。它为整个 Skia 代码库提供编译器特性的统一访问方式,影响代码生成、优化和静态分析。

## 主要宏定义

### 基础属性宏

#### `SK_ATTRIBUTE(attr)`
```cpp
#if defined(__clang__) || defined(__GNUC__)
#  define SK_ATTRIBUTE(attr) __attribute__((attr))
#else
#  define SK_ATTRIBUTE(attr)
#endif
```

**说明**:
- 统一的属性语法包装器
- GCC/Clang: 使用 `__attribute__((attr))` 语法
- 其他编译器(如 MSVC): 展开为空
- 基础宏,被其他宏使用

## 内联控制宏

### SK_ALWAYS_INLINE
```cpp
#if !defined(SK_ALWAYS_INLINE)
#  if defined(SK_BUILD_FOR_WIN)
#    define SK_ALWAYS_INLINE __forceinline
#  else
#    define SK_ALWAYS_INLINE SK_ATTRIBUTE(always_inline) inline
#  endif
#endif
```

**功能**: 强制内联函数

**平台实现**:
- **Windows (MSVC)**: 使用 `__forceinline`
- **GCC/Clang**: 使用 `__attribute__((always_inline)) inline`
- **其他**: 依赖用户定义

**使用场景**:
- 性能关键的小函数
- 经过性能分析验证的热点
- 需要内联才能正确优化的模板函数

**示例**:
```cpp
SK_ALWAYS_INLINE int add(int a, int b) {
    return a + b;
}
```

**注意事项**:
- 仅在性能分析证明有益时使用
- 过度使用会增加代码大小
- 可能影响调试体验

### SK_NEVER_INLINE
```cpp
#if !defined(SK_NEVER_INLINE)
#  if defined(SK_BUILD_FOR_WIN)
#    define SK_NEVER_INLINE __declspec(noinline)
#  else
#    define SK_NEVER_INLINE SK_ATTRIBUTE(noinline)
#  endif
#endif
```

**功能**: 禁止内联函数

**平台实现**:
- **Windows (MSVC)**: 使用 `__declspec(noinline)`
- **GCC/Clang**: 使用 `__attribute__((noinline))`

**使用场景**:
- 调试辅助(保留调用栈)
- 强制函数边界用于性能分析
- 减小代码大小(冷路径)
- 避免过度内联导致的缓存抖动

**示例**:
```cpp
SK_NEVER_INLINE void debugLog(const char* msg) {
    // 调试代码,不希望内联到调用者
    fprintf(stderr, "%s\n", msg);
}
```

## 格式化检查宏

### SK_PRINTF_LIKE
```cpp
#if !defined(SK_PRINTF_LIKE)
#  define SK_PRINTF_LIKE(A, B) SK_ATTRIBUTE(format(printf, (A), (B)))
#endif
```

**功能**: 标记函数使用 printf 风格的格式字符串

**参数**:
- `A`: 格式字符串参数的位置(从 1 开始)
- `B`: 第一个可变参数的位置(从 1 开始)

**行为**:
- 编译器在编译时检查格式字符串和参数类型匹配
- 检测格式化错误(如 %d 传递字符串)
- 检测参数数量不匹配

**示例**:
```cpp
SK_PRINTF_LIKE(1, 2) void SkDebugf(const char* format, ...);
//                                  ↑位置1        ↑位置2开始

// 正确
SkDebugf("Value: %d\n", 42);

// 编译警告:类型不匹配
SkDebugf("Value: %d\n", "string");  // 警告!

// 编译警告:参数不足
SkDebugf("Values: %d %d\n", 42);    // 警告!
```

**成员函数示例**:
```cpp
class Logger {
public:
    // 注意:成员函数的 this 指针占据位置 1
    SK_PRINTF_LIKE(2, 3) void log(const char* fmt, ...);
    //                            ↑位置2       ↑位置3开始
};
```

## Sanitizer 控制宏

### SK_NO_SANITIZE
```cpp
#if !defined(SK_NO_SANITIZE)
  #if defined(__has_attribute)
    #if __has_attribute(no_sanitize)
      #define SK_NO_SANITIZE(A) SK_ATTRIBUTE(no_sanitize(A))
    #else
      #define SK_NO_SANITIZE(A)
    #endif
  #else
    #define SK_NO_SANITIZE(A)
  #endif
#endif
```

**功能**: 禁用特定 sanitizer 对函数的检查

**支持的 sanitizer**:
- `"address"`: AddressSanitizer (ASan)
- `"thread"`: ThreadSanitizer (TSan)
- `"undefined"`: UndefinedBehaviorSanitizer (UBSan)
- `"memory"`: MemorySanitizer (MSan)

**使用场景**:
- 已知的误报(false positive)
- 底层内存操作(placement new、类型双关)
- 性能关键代码(sanitizer 开销太大)

**示例**:
```cpp
SK_NO_SANITIZE("undefined")
int* cast_pointer(void* ptr) {
    // 某些指针转换可能触发 UBSan,但我们知道是安全的
    return reinterpret_cast<int*>(ptr);
}
```

**注意事项**:
- 仅在确认误报或有充分理由时使用
- 可能隐藏真实的 bug
- 应该添加注释解释原因

### SK_NO_SANITIZE_CFI
```cpp
#if defined(__clang__)
  #define SK_NO_SANITIZE_CFI SK_NO_SANITIZE("cfi")
#else
  #define SK_NO_SANITIZE_CFI
#endif
```

**功能**: 禁用控制流完整性(CFI)检查

**说明**:
- 仅 Clang 支持 CFI sanitizer
- 用于禁用虚函数调用和间接调用的完整性检查

**使用场景**:
- JIT 生成的代码
- 动态函数指针
- 与 C ABI 的互操作

## ABI 优化宏

### SK_TRIVIAL_ABI
```cpp
#if !defined(SK_TRIVIAL_ABI)
#  define SK_TRIVIAL_ABI
#endif
```

**功能**: 标记类为 trivial ABI

**说明**:
- Clang 特有的属性:`__attribute__((trivial_abi))`
- 默认未启用,定义为空
- 用户可以在构建配置中定义

**效果**:
- 允许类在寄存器中传递(即使有非平凡的析构函数)
- 提高函数调用性能
- 要求类的移动+删除等价于 memcpy+free

**限制**:
- 类不能持有指向自身的指针
- 移动+删除必须等价于 memcpy+free
- 会改变 ABI,不能用于公共 API

**参考**:
- [Clang 文档](https://clang.llvm.org/docs/AttributeReference.html#trivial-abi)
- [libc++ 设计文档](https://libcxx.llvm.org/DesignDocs/UniquePtrTrivialAbi.html)

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/private/base/SkFeatures.h | 平台特性检测 |
| include/private/base/SkLoadUserConfig.h | 用户配置加载 |

### 被依赖的模块
几乎所有 Skia 模块:
- include/core/*.h (核心 API)
- include/private/base/SkDebug.h (SkDebugf)
- src/ 下的所有实现文件
- 性能关键的内联函数

## 设计模式与设计决策

### 平台抽象
通过宏统一不同编译器的语法:
```cpp
// 用户代码
SK_ALWAYS_INLINE void foo();

// 在 MSVC 上展开为
__forceinline void foo();

// 在 GCC/Clang 上展开为
__attribute__((always_inline)) inline void foo();
```

### 条件编译策略
使用多层条件检查:
1. 检查是否已定义(允许用户覆盖)
2. 检查平台(SK_BUILD_FOR_WIN)
3. 检查编译器(__clang__, __GNUC__)
4. 检查特性支持(__has_attribute)

### 安全降级
不支持的平台降级为空操作:
- 功能性不受影响
- 仅失去优化或检查
- 保证跨平台兼容性

### 文档友好
宏名称语义清晰:
- `SK_ALWAYS_INLINE`: 明确表达意图
- `SK_PRINTF_LIKE`: 描述功能
- `SK_NO_SANITIZE`: 说明用途

## 性能考量

### 内联优化
- **SK_ALWAYS_INLINE**: 消除函数调用开销,允许更多优化
- **SK_NEVER_INLINE**: 减少代码膨胀,改善指令缓存命中率

### 编译器提示
- **SK_PRINTF_LIKE**: 零运行时开销,仅编译时检查
- **SK_NO_SANITIZE**: 消除 sanitizer 的运行时开销(在 sanitizer 构建中)

### 权衡考量
过度使用 `SK_ALWAYS_INLINE`:
- **优点**: 潜在的性能提升
- **缺点**: 代码膨胀、编译时间增加、指令缓存压力

## 使用场景

### 性能关键的内联
```cpp
class SkColor {
public:
    SK_ALWAYS_INLINE static uint8_t GetA(SkColor c) {
        return (c >> 24) & 0xFF;
    }
};
```

### 调试辅助
```cpp
SK_NEVER_INLINE void breakpoint() {
    // 在调试器中设置断点
    __asm__("int $3");
}
```

### 格式化函数
```cpp
SK_PRINTF_LIKE(1, 2)
void SkDebugf(const char format[], ...);
```

### 底层优化
```cpp
SK_NO_SANITIZE("undefined")
float fast_inverse_sqrt(float x) {
    // 著名的 Quake III 快速平方根倒数
    // 涉及类型双关,UBSan 会报告
    union { float f; uint32_t i; } conv = {x};
    conv.i = 0x5f3759df - (conv.i >> 1);
    return conv.f;
}
```

## 相关文件
| 文件 | 关系 |
|------|------|
| include/private/base/SkDebug.h | 使用 SK_PRINTF_LIKE |
| include/core/SkTypes.h | 使用内联属性 |
| include/private/base/SkAssert.h | 使用 SK_ALWAYS_INLINE |

## 注意事项

### 性能分析先行
```cpp
// 错误:没有测量就优化
SK_ALWAYS_INLINE void foo() { /* 复杂逻辑 */ }

// 正确:先分析,再优化
void foo() { /* 复杂逻辑 */ }
// 性能分析后,如果 foo 是热点且内联有益,再添加 SK_ALWAYS_INLINE
```

### 格式字符串安全
```cpp
// 错误:参数位置不对
class Logger {
    SK_PRINTF_LIKE(1, 2)  // this 是位置 1!
    void log(const char* fmt, ...);  // fmt 实际是位置 2
};

// 正确
class Logger {
    SK_PRINTF_LIKE(2, 3)
    void log(const char* fmt, ...);
};
```

### Sanitizer 禁用的谨慎使用
```cpp
// 应该添加注释解释
SK_NO_SANITIZE("address")
void custom_allocator_internal() {
    // ASan 不理解我们的自定义内存管理
    // 已经通过单元测试验证正确性
    // ...
}
```

### ABI 兼容性
`SK_TRIVIAL_ABI` 改变 ABI,不能用于公共 API:
```cpp
// 错误:公共 API
class SK_API PublicClass {
    SK_TRIVIAL_ABI  // 破坏 ABI!
    // ...
};

// 正确:私有实现
class SK_SPI InternalClass {
    SK_TRIVIAL_ABI  // OK
    // ...
};
```

## 编译器支持矩阵

| 属性 | GCC | Clang | MSVC | 其他 |
|------|-----|-------|------|------|
| SK_ATTRIBUTE | ✓ | ✓ | ✗ | ✗ |
| SK_ALWAYS_INLINE | ✓ | ✓ | ✓ | 降级 |
| SK_NEVER_INLINE | ✓ | ✓ | ✓ | 降级 |
| SK_PRINTF_LIKE | ✓ | ✓ | ✗ | ✗ |
| SK_NO_SANITIZE | ✓(8+) | ✓ | ✗ | ✗ |
| SK_NO_SANITIZE_CFI | ✗ | ✓ | ✗ | ✗ |
| SK_TRIVIAL_ABI | ✗ | ✓ | ✗ | ✗ |
