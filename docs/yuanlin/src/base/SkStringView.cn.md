# SkStringView

> 源文件: src/base/SkStringView.h

## 概述

`SkStringView` 是 Skia 中对 C++17 `std::string_view` 的扩展工具模块,在 `skstd` 命名空间下提供了 C++20 和 C++23 标准中新增的字符串视图工具函数。这些函数在 C++17 环境中也能使用,为 Skia 代码库提供了向后兼容的现代字符串操作接口。

该模块实现了 `starts_with`、`ends_with` 和 `contains` 等便捷函数,避免了手动进行字符串前缀、后缀和子串查找的繁琐代码。所有函数都是 `constexpr`,支持编译期计算。

## 架构位置

```
src/base/
├── SkStringView.h       // 字符串视图扩展工具
└── (其他基础工具)
    ↓
src/core/
├── SkString.h           // Skia 字符串类
└── (各种使用字符串的模块)
```

该模块是基础设施层的轻量级工具,为 Skia 内部提供现代 C++ 字符串操作接口,特别是在需要字符串前缀/后缀匹配的场景中。

## 主要类与结构体

**无类定义**,模块仅提供命名空间 `skstd` 下的独立函数。

## 公共 API 函数

### C++20 风格函数

| 函数签名 | 功能说明 |
|---------|---------|
| `bool starts_with(string_view str, string_view prefix)` | 检查字符串是否以指定前缀开始 |
| `bool starts_with(string_view str, char c)` | 检查字符串是否以指定字符开始 |
| `bool ends_with(string_view str, string_view suffix)` | 检查字符串是否以指定后缀结束 |
| `bool ends_with(string_view str, char c)` | 检查字符串是否以指定字符结束 |

### C++23 风格函数

| 函数签名 | 功能说明 |
|---------|---------|
| `bool contains(string_view str, string_view needle)` | 检查字符串是否包含指定子串 |
| `bool contains(string_view str, char c)` | 检查字符串是否包含指定字符 |

**所有函数都是 `constexpr` 和 `inline`,支持编译期计算和内联优化。**

## 内部实现细节

### starts_with 实现

**字符串前缀检查**:
```cpp
inline constexpr bool starts_with(std::string_view str, std::string_view prefix) {
    if (prefix.length() > str.length()) {
        return false;  // 前缀比字符串长,不可能匹配
    }
    return prefix.length() == 0 || !memcmp(str.data(), prefix.data(), prefix.length());
}
```

**关键优化**:
- 空前缀总是返回 `true`(符合标准语义)
- 使用 `memcmp` 进行高效的内存比较
- 早期返回避免不必要的比较

**字符前缀检查**:
```cpp
inline constexpr bool starts_with(std::string_view str, char c) {
    return !str.empty() && str.front() == c;
}
```

### ends_with 实现

**字符串后缀检查**:
```cpp
inline constexpr bool ends_with(std::string_view str, std::string_view suffix) {
    if (suffix.length() > str.length()) {
        return false;
    }
    return suffix.length() == 0 ||
           !memcmp(str.data() + str.length() - suffix.length(),
                   suffix.data(), suffix.length());
}
```

**指针算术**:
- `str.data() + str.length() - suffix.length()` 定位到后缀起始位置
- 从后向前比较 `suffix.length()` 个字节

**字符后缀检查**:
```cpp
inline constexpr bool ends_with(std::string_view str, char c) {
    return !str.empty() && str.back() == c;
}
```

### contains 实现

**子串查找**:
```cpp
inline constexpr bool contains(std::string_view str, std::string_view needle) {
    return str.find(needle) != std::string_view::npos;
}
```

直接复用 `std::string_view::find` 的高效实现(通常使用 Boyer-Moore 或类似算法)。

**字符查找**:
```cpp
inline constexpr bool contains(std::string_view str, char c) {
    return str.find(c) != std::string_view::npos;
}
```

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| cstring | memcmp 函数 |
| string_view (C++17) | std::string_view 类型 |

**被依赖的模块:**

该模块作为基础工具被 Skia 内部多个组件使用:
- 文件路径处理(检查扩展名)
- 配置解析(检查参数前缀)
- 字符串工具函数
- 命令行参数处理

## 设计模式与设计决策

### 向后兼容设计

模块的主要目的是在 C++17 环境中提供 C++20/23 的功能:
- 使用独立的 `skstd` 命名空间避免与标准库冲突
- 未来升级到 C++20/23 时可以逐步迁移
- 保持与标准库相同的函数签名和语义

### 函数重载设计

每个函数都提供两个重载版本:
1. **字符串版本**: 处理通用的字符串前缀/后缀/子串
2. **字符版本**: 优化的单字符检查

这种设计提供了更好的性能和易用性。

### constexpr 支持

所有函数都声明为 `constexpr`,允许:
```cpp
constexpr bool isHeader = skstd::ends_with("file.h", ".h");  // 编译期计算
```

这在模板元编程和编译期常量场景中非常有用。

### 内联优化

所有函数都是 `inline`,建议编译器内联:
- 消除函数调用开销
- 允许进一步优化(如常量折叠)
- 头文件实现避免链接问题

## 性能考量

### 算法复杂度

| 函数 | 时间复杂度 | 空间复杂度 |
|------|-----------|-----------|
| starts_with(str, prefix) | O(min(n, m)) | O(1) |
| ends_with(str, suffix) | O(min(n, m)) | O(1) |
| contains(str, needle) | O(n×m) 平均更优 | O(1) |
| starts_with(str, c) | O(1) | O(1) |
| ends_with(str, c) | O(1) | O(1) |
| contains(str, c) | O(n) | O(1) |

其中 n 是字符串长度,m 是模式长度。

### 性能优化技术

1. **早期返回**: 长度检查避免无效比较
2. **memcmp 优化**: 利用 libc 的高度优化实现
3. **内联**: 消除函数调用开销
4. **字符特化**: 单字符检查使用 O(1) 算法

### 性能对比

与手动实现相比:
```cpp
// 手动实现
bool starts = str.size() >= prefix.size() &&
              str.substr(0, prefix.size()) == prefix;  // 可能分配内存

// 使用 skstd
bool starts = skstd::starts_with(str, prefix);  // 零分配
```

`skstd` 版本避免了 `substr` 的潜在内存分配。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| src/core/SkString.h | Skia 字符串类,可转换为 string_view |
| src/utils/SkOSPath.h | 路径工具,使用 ends_with 检查扩展名 |
| src/core/SkReadBuffer.h | 序列化,使用字符串前缀判断 |

## 使用示例

```cpp
#include "src/base/SkStringView.h"
#include <string_view>

// 示例 1: 检查文件扩展名
std::string_view filename = "image.png";
if (skstd::ends_with(filename, ".png")) {
    // 处理 PNG 文件
}

// 示例 2: 检查命令行参数
std::string_view arg = "--verbose";
if (skstd::starts_with(arg, "--")) {
    // 处理长选项
} else if (skstd::starts_with(arg, '-')) {
    // 处理短选项
}

// 示例 3: 路径分隔符检查
std::string_view path = "/usr/local/bin/";
if (skstd::ends_with(path, '/')) {
    // 路径已有尾部斜杠
}

// 示例 4: 子串查找
std::string_view url = "https://example.com";
if (skstd::contains(url, "://")) {
    // 包含协议分隔符
}

// 示例 5: 编译期常量
constexpr std::string_view ext = ".cpp";
constexpr bool isCpp = skstd::ends_with("source.cpp", ext);
static_assert(isCpp, "Should be C++ file");

// 示例 6: 字符检查
std::string_view name = "Alice";
if (skstd::starts_with(name, 'A')) {
    // 名字以 A 开头
}

// 示例 7: 空字符串边界情况
std::string_view empty = "";
bool result1 = skstd::starts_with(empty, "");     // true
bool result2 = skstd::starts_with(empty, "a");    // false
bool result3 = skstd::starts_with("abc", "");     // true

// 示例 8: 多条件判断
std::string_view mime = "image/png";
if (skstd::starts_with(mime, "image/") &&
    (skstd::ends_with(mime, "/png") ||
     skstd::ends_with(mime, "/jpeg"))) {
    // 支持的图像格式
}

// 示例 9: 与 SkString 配合
SkString skStr("test.txt");
std::string_view view(skStr.c_str(), skStr.size());
if (skstd::ends_with(view, ".txt")) {
    // 处理文本文件
}

// 示例 10: 大小写敏感注意
std::string_view mixed = "Test";
bool match1 = skstd::starts_with(mixed, "Test");  // true
bool match2 = skstd::starts_with(mixed, "test");  // false
```

## 注意事项

1. **大小写敏感**: 所有函数都是大小写敏感的,需要大小写不敏感比较需自行转换
2. **空字符串语义**: 空前缀/后缀总是匹配,符合标准库行为
3. **字符串视图生命周期**: 确保 `string_view` 指向的数据在使用期间有效
4. **非拥有语义**: `string_view` 不拥有数据,避免悬垂指针
5. **memcmp 限制**: 对于包含 null 字符的字符串可能有意外行为
6. **命名空间**: 使用 `skstd::` 而非 `std::`,注意命名空间
7. **C++17 要求**: 需要 C++17 或更高版本的编译器

## 迁移到标准库

当 Skia 升级到 C++20/23 时,可以逐步迁移:

```cpp
// 当前 (C++17)
#include "src/base/SkStringView.h"
bool result = skstd::starts_with(str, prefix);

// 未来 (C++20+)
#include <string_view>
bool result = str.starts_with(prefix);  // 成员函数
```

## 扩展建议

如果需要更多字符串工具,可以考虑添加:
- `trim`, `ltrim`, `rtrim`: 去除空白字符
- `split`: 字符串分割
- `join`: 字符串连接
- `replace`: 字符串替换
- 大小写转换和比较

但 Skia 倾向于保持该模块的最小化,避免重新发明轮子。

## 设计哲学

该模块体现了 Skia 的实用主义:
- **最小化**: 仅提供高频使用的功能
- **标准对齐**: 与标准库保持一致
- **向后兼容**: 支持较旧的 C++ 标准
- **零成本抽象**: 性能与手写代码相当
