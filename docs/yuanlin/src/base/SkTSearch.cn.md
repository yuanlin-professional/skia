# SkTSearch

> 源文件: src/base/SkTSearch.h, src/base/SkTSearch.cpp

## 概述

`SkTSearch` 是 Skia 中提供泛型二分搜索功能的模板库。它实现了在有序数组中高效查找元素的算法,支持自定义比较函数和多种数据类型。该模块同时提供了字符串专用的搜索函数以及大小写不敏感的搜索工具类。

二分搜索算法的时间复杂度为 O(log n),使其在大型有序数据集中查找元素时非常高效。返回值设计巧妙:找到时返回索引(0...N-1),未找到时返回按位取反的插入位置,方便调用者进行插入操作。

## 架构位置

```
src/base/
├── SkTSearch.h          // 二分搜索模板接口定义
├── SkTSearch.cpp        // 字符串搜索和辅助类实现
└── (其他基础工具)
```

该模块属于 Skia 基础设施层,为上层提供高效的搜索算法支持。它被 Skia 内部的多个组件使用,特别是需要在有序数组中快速查找元素的场景。

## 主要类与结构体

### SkAutoAsciiToLC

字符串转小写辅助类,用于大小写不敏感的字符串搜索。

**继承关系:**
- 无继承关系(独立类)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fLC | char* | 指向小写字符串的指针(堆或栈存储) |
| fLength | size_t | 字符串长度 |
| fStorage | char[65] | 栈上的小字符串存储缓冲区 |

## 公共 API 函数

### 核心模板函数

| 函数签名 | 功能说明 |
|---------|---------|
| `template <typename T, typename K, typename LESS> int SkTSearch(...)` | 最通用的二分搜索模板,支持自定义比较函数 |
| `template <typename T> int SkTSearch(const T base[], int count, const T& target, size_t elemSize)` | 使用默认 `operator<` 的简化版本 |
| `template <typename T, bool (*LESS)(const T&, const T&)> int SkTSearch(T* base[], ...)` | 指针数组搜索,比较指向的对象而非指针本身 |

### 字符串搜索函数

| 函数签名 | 功能说明 |
|---------|---------|
| `int SkStrSearch(const char*const* base, int count, const char target[], size_t target_len, size_t elemSize)` | 在字符串指针数组中搜索指定字符串 |
| `int SkStrLCSearch(...)` | 大小写不敏感的字符串搜索 |

### SkAutoAsciiToLC 类方法

| 方法 | 功能说明 |
|------|---------|
| `SkAutoAsciiToLC(const char str[], size_t len)` | 构造函数,转换 ASCII 字符为小写 |
| `const char* lc() const` | 获取转换后的小写字符串 |
| `size_t length() const` | 获取字符串长度 |

## 内部实现细节

### 二分搜索算法实现

模板函数 `SkTSearch` 采用标准的二分搜索算法:

1. **搜索过程**: 维护 `lo` 和 `hi` 两个边界,每次取中点 `mid = lo + ((hi - lo) >> 1)` 进行比较
2. **元素访问**: 使用指针算术 `(const T*)((const char*)base + mid * elemSize)` 访问数组元素
3. **返回值编码**:
   - 找到元素: 返回索引值 `hi` (非负)
   - 未找到: 返回 `~hi`,表示应插入的位置(负数)

### 字符串搜索特化

`SkStrSearch` 针对字符串数组进行了特化:
- 使用 `strncmp` 进行字符串比较
- 考虑了字符串长度,确保精确匹配
- `index_into_base` 辅助函数处理指针数组的索引

### ASCII 小写转换

`SkAutoAsciiToLC` 实现了快速的 ASCII 小写转换:
- **小对象优化**: 64 字节以内使用栈存储(`fStorage`),超过则堆分配
- **选择性转换**: 仅转换 ASCII 字符(`c & 0x80 == 0`),UTF-8 字符保持不变
- **RAII 管理**: 析构函数自动释放堆内存

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| include/private/base/SkAssert.h | 断言检查 |
| include/private/base/SkMalloc.h | 内存分配函数 |
| cstring | 字符串操作函数 |
| ctype.h | 字符类型判断 |

**被依赖的模块:**

该模块作为基础工具被 Skia 内部多个组件使用,包括:
- 字体管理系统(查找字体名称)
- 资源管理器(查找资源 ID)
- 路径效果系统(查找效果名称)

## 设计模式与设计决策

### 模板特化层次结构

设计采用了多层模板特化,从最通用到最具体:
1. 完全自定义比较器版本(支持不同类型 T 和 K)
2. 函数指针比较器版本
3. 默认 `operator<` 版本
4. 指针数组特化版本

这种设计提供了灵活性,同时保持了易用性。

### 返回值编码技巧

使用按位取反(`~index`)编码插入位置是一个巧妙的设计:
- 正值表示找到,负值表示未找到
- 通过 `~index` 可以直接获取插入位置
- 避免使用额外的输出参数或返回结构体

### 小对象优化(SOO)

`SkAutoAsciiToLC` 使用 64 字节的栈缓冲区进行小对象优化:
- 大多数字符串搜索场景都是短字符串
- 避免小字符串频繁的堆分配
- 提升缓存局部性

## 性能考量

### 算法复杂度

- **时间复杂度**: O(log n) 的查找时间
- **空间复杂度**: O(1) 额外空间(不计递归栈)
- **比较次数**: 最多 log₂(n) + 1 次比较

### 优化技术

1. **位移操作**: 使用 `>> 1` 代替除以 2,提升性能
2. **指针算术**: 直接计算元素地址,避免函数调用开销
3. **内联潜力**: 小函数适合内联优化
4. **缓存友好**: 二分搜索具有良好的空间局部性

### 字符串搜索性能

- `SkAutoAsciiToLC` 的转换是一次性的,后续比较无需重复转换
- ASCII 检查(`c & 0x80`)比字符分类函数更快
- 栈缓冲区避免了小字符串的内存分配开销

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| include/private/base/SkAssert.h | 提供断言宏 |
| include/private/base/SkMalloc.h | 提供内存分配函数 |
| src/base/SkTSort.h | 相关的排序算法模板 |
| include/private/base/SkTDArray.h | 动态数组容器,常与搜索配合使用 |

## 使用示例

```cpp
// 示例 1: 基本整数数组搜索
int array[] = {1, 3, 5, 7, 9};
int index = SkTSearch(array, 5, 5, sizeof(int));
if (index >= 0) {
    // 找到元素,index = 2
} else {
    // 未找到,插入位置 = ~index
}

// 示例 2: 自定义比较器
struct Person { int age; const char* name; };
auto lessByAge = [](const Person& a, int age) { return a.age < age; };
int result = SkTSearch(persons, count, 30, sizeof(Person), lessByAge);

// 示例 3: 字符串数组搜索
const char* names[] = {"Alice", "Bob", "Charlie"};
int idx = SkStrSearch(names, 3, "Bob", sizeof(const char*));

// 示例 4: 大小写不敏感搜索
const char* lowerNames[] = {"alice", "bob", "charlie"};
int idx2 = SkStrLCSearch(lowerNames, 3, "BOB", sizeof(const char*));
```

## 注意事项

1. **有序性要求**: 输入数组必须已排序,否则结果未定义
2. **元素大小**: 必须正确指定 `elemSize` 参数
3. **比较器一致性**: 自定义比较器必须与数组的排序顺序一致
4. **字符串生命周期**: `SkAutoAsciiToLC` 返回的指针在对象销毁后失效
5. **非 Unicode 友好**: 小写转换仅处理 ASCII,不适合国际化场景
