# SkMSAN - MemorySanitizer 集成工具
> 源文件: `src/base/SkMSAN.h`

## 概述
SkMSAN 模块提供了与 LLVM MemorySanitizer (MSAN) 集成的工具函数。MSAN 是一个用于检测未初始化内存读取的动态分析工具。该模块通过封装 MSAN 的底层 API，允许 Skia 代码在必要时标记内存状态、断言内存已初始化，或故意隐藏已知的误报，从而在保持代码正确性的同时提升 MSAN 检测的实用性。

## 架构位置
SkMSAN 位于 Skia 基础调试工具模块（src/base）中，属于编译器工具集成层。它为整个 Skia 代码库提供统一的 MSAN 交互接口，特别是在处理底层位操作、SIMD 代码、以及外部库交互时，需要明确内存初始化状态的场景。

## 公共 API 函数

### `void sk_msan_assert_initialized(const void* begin, const void* end)`
- **功能**: 断言指定内存区域已被完全初始化
- **参数**:
  - begin: 内存区域起始地址
  - end: 内存区域结束地址（不包含）
- **行为**:
  - 在 MSAN 构建中：调用 `__msan_check_mem_is_initialized`
  - 非 MSAN 构建：无操作（编译器优化掉）
- **用途**: 将未初始化内存的责任上推到调用者
- **失败后果**: MSAN 报告错误并终止程序（如果检测到未初始化）

### `void sk_msan_mark_initialized(const void* begin, const void* end, const char* skbug)`
- **功能**: 欺骗 MSAN，告知指定内存已初始化（即使实际未初始化）
- **参数**:
  - begin: 内存区域起始地址
  - end: 内存区域结束地址
  - skbug: bug 跟踪字符串（必须非空，通常为 "skbug.com/12345"）
- **行为**:
  - 在 MSAN 构建中：调用 `__msan_unpoison`
  - 非 MSAN 构建：无操作
- **警告**: **这可以隐藏严重问题，每次使用都应引用一个 bug**
- **断言**: skbug 参数必须非空且非空字符串

## 内部实现细节

### MSAN 接口声明
```cpp
extern "C" {
    void __msan_check_mem_is_initialized(const volatile void*, size_t);
    void __msan_unpoison(const volatile void*, size_t);
}
```

**为何重新声明**:
- 避免包含完整的 `msan_interface.h`
- 减少编译依赖
- 只声明 Skia 需要的两个函数
- `extern "C"` 确保链接器能找到 MSAN 运行时库的符号

### 条件编译检查
```cpp
#if defined(__has_feature)
    #if __has_feature(memory_sanitizer)
        // 调用 MSAN API
    #endif
#endif
```

**检测逻辑**:
1. 检查编译器是否支持 `__has_feature`（Clang 特性）
2. 检查是否启用了 `memory_sanitizer` 特性
3. 仅在 MSAN 构建中调用 MSAN API

**非 MSAN 构建**: 函数体为空，编译器优化为无操作

### 地址计算
```cpp
(const char*)end - (const char*)begin
```
- 将 void* 转换为 char* 以计算字节数
- end 是不包含的边界（类似 STL 迭代器风格）

### 参数验证断言
```cpp
SkASSERT(skbug && 0 != strcmp(skbug, ""));
```
确保 `sk_msan_mark_initialized` 调用时提供了有效的 bug 引用：
- skbug 不为 nullptr
- skbug 不为空字符串
- 强制代码审查者意识到这是一个已知问题

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/private/base/SkAssert.h | 参数验证断言 |
| <cstddef> | size_t 类型定义 |
| <string.h> | strcmp 函数 |
| MSAN 运行时库 | 链接时提供 __msan_* 符号（仅 MSAN 构建） |

### 被依赖的模块
- SIMD 代码（skvx）
- 位操作相关代码
- 与外部库交互的接口层
- 底层内存管理代码
- 性能关键路径（故意不初始化某些字段）

## 设计模式与设计决策

### 封装 MSAN API
而非直接使用 `__msan_check_mem_is_initialized`：
- **优点**:
  - 统一的接口风格（指针对而非指针+大小）
  - 自动处理非 MSAN 构建
  - 强制 bug 引用（sk_msan_mark_initialized）
  - 未来可以切换实现

### 必需的 bug 引用
`sk_msan_mark_initialized` 强制提供 bug 字符串：
- **目的**: 记录为何需要这个 hack
- **好处**:
  - 便于代码审查
  - 追踪技术债务
  - 当 bug 修复后可以搜索并移除
- **实施**: 断言确保非空

### 内联函数而非宏
使用 `static inline` 函数而非宏：
- 类型安全
- 作用域控制
- 调试器友好
- 避免宏展开的副作用

### 零开销抽象
在非 MSAN 构建中：
- 函数体为空
- 编译器优化为无操作（零指令）
- 不影响发布版性能

## 使用场景

### 场景 1: 断言输入已初始化
```cpp
void processPixels(const uint32_t* pixels, size_t count) {
    // 确保调用者传入的像素数据已初始化
    sk_msan_assert_initialized(pixels, pixels + count);
    // ... 处理像素
}
```
**目的**: 将责任转移到调用者，明确合约

### 场景 2: SIMD 加载未对齐数据
```cpp
void loadVector(const float* data) {
    // SIMD 加载可能读取超出范围的填充字节
    // 这些填充字节未初始化，但不会被实际使用
    __m128 vec = _mm_loadu_ps(data);
    // 标记整个向量已初始化，避免误报
    sk_msan_mark_initialized(&vec, &vec + 1, "skbug.com/12345");
}
```

### 场景 3: 位域和填充
```cpp
struct MyStruct {
    uint32_t a : 24;
    uint32_t padding : 8;  // 填充位，未初始化
};

void serialize(const MyStruct& s) {
    // 写入整个结构到文件，包括未初始化的填充
    sk_msan_mark_initialized(&s, &s + 1, "skbug.com/67890");
    file.write(&s, sizeof(s));
}
```

### 场景 4: 性能优化的部分初始化
```cpp
struct Cache {
    bool valid;
    ExpensiveData data;  // 仅在 valid == true 时初始化
};

Cache cache;
cache.valid = false;
// data 未初始化，但不会被读取
sk_msan_mark_initialized(&cache.data, &cache.data + 1, "skbug.com/11111");
```

## 警告与陷阱

### 过度使用的危险
`sk_msan_mark_initialized` 隐藏真正的 bug：
```cpp
// 危险示例
int* ptr = new int[10];
// 忘记初始化
sk_msan_mark_initialized(ptr, ptr + 10, "skbug.com/fake");  // 隐藏 bug！
// 后续使用 ptr 导致未定义行为
```

### 何时使用
仅在以下情况使用 `sk_msan_mark_initialized`：
1. 确认是 MSAN 误报（如 SIMD 填充）
2. 有明确的 bug 跟踪
3. 注释解释原因
4. 计划修复（即使是长期计划）

### 边界计算错误
```cpp
// 错误
sk_msan_assert_initialized(ptr, ptr + count * sizeof(T));  // 错误！应该是元素数
// 正确
sk_msan_assert_initialized(ptr, ptr + count);
```

### volatile 修饰符
MSAN API 使用 `const volatile void*`：
- **volatile**: 防止编译器优化掉内存访问
- Skia 的封装隐藏了这个细节

## 性能考量

### MSAN 构建的性能影响
启用 MSAN 后，程序运行速度降低约：
- **2-3 倍**: 典型情况
- **10 倍**: 最坏情况（大量内存操作）

原因：
- 每次内存读取需要检查影子内存（shadow memory）
- 影子内存 1 字节对应实际内存 1 字节
- 额外的条件分支和内存访问

### sk_msan_assert_initialized 的开销
在 MSAN 构建中：
- 遍历整个内存区域
- 检查每个字节的影子内存
- O(n) 时间复杂度

建议：
- 不要在紧密循环中调用
- 在函数入口处批量检查

### sk_msan_mark_initialized 的开销
在 MSAN 构建中：
- 清除影子内存区域
- O(n) 时间复杂度
- 通常比 assert 版本快（不需要条件检查）

### 非 MSAN 构建
**零开销**：
- 空函数被内联
- 优化器删除函数调用
- 不影响发布版性能

## 相关文件
| 文件 | 关系 |
|------|------|
| include/private/base/SkAssert.h | 提供 SkASSERT 宏 |
| src/base/SkVx.h | SIMD 代码中使用 MSAN 工具 |
| src/core/SkRasterPipeline.cpp | 管线阶段的内存初始化检查 |
| src/opts/*.cpp | 优化代码路径（SIMD、手写汇编） |
| src/codec/*.cpp | 编解码器与外部库交互 |
| third_party/ | 外部库可能有误报 |
| BUILD.gn | MSAN 构建配置 |

## 最佳实践

### 使用 sk_msan_assert_initialized
```cpp
void myFunction(const Data* input, size_t count) {
    // 在函数入口处断言
    sk_msan_assert_initialized(input, input + count);
    // ... 使用 input
}
```

### 使用 sk_msan_mark_initialized
```cpp
// 1. 添加详细注释
// 2. 引用具体的 bug
// 3. 解释为何是安全的
void loadSIMD(const float* data) {
    // Load 4 floats, but SIMD instruction reads 16 bytes which may include
    // padding. The padding bytes are never used, but MSAN doesn't know that.
    // See skbug.com/12345 for removing this workaround.
    __m128 vec = _mm_loadu_ps(data);
    sk_msan_mark_initialized(&vec, &vec + 1, "skbug.com/12345");
}
```

### 运行 MSAN 测试
```bash
# 使用 MSAN 构建
gn gen out/msan --args='is_debug=true sanitizer="MSAN"'
ninja -C out/msan

# 运行测试
out/msan/dm --config msan
```
