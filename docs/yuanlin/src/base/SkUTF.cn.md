# SkUTF

> 源文件: src/base/SkUTF.h, src/base/SkUTF.cpp

## 概述

`SkUTF` 是 Skia 中处理 Unicode 文本编码的核心模块,提供了 UTF-8、UTF-16 和 UTF-32 三种编码格式之间的转换和操作功能。该模块实现了完整的 Unicode 字符解析、验证、编码和解码功能,是 Skia 文本处理系统的基础设施。

模块采用命名空间 `SkUTF` 组织函数,所有函数都是无状态的纯函数,便于在多线程环境中使用。它严格遵循 Unicode 标准,能够检测和处理各种非法编码序列。

## 架构位置

```
src/base/
├── SkUTF.h              // UTF 编码处理接口
├── SkUTF.cpp            // UTF 编码实现
└── (其他基础设施)
    ↓
src/core/
└── (文本渲染系统)       // 使用 UTF 功能处理文本
```

该模块位于 Skia 基础层,为文本渲染、字体系统、文本布局等上层模块提供 Unicode 编码支持。

## 主要类与结构体

### 类型定义

```cpp
typedef int32_t SkUnichar;  // Unicode 码点类型
```

### 命名空间 SkUTF

所有功能都封装在 `SkUTF` 命名空间中,不使用类结构,而是提供纯函数接口。

**关键常量:**

| 常量 | 值 | 说明 |
|------|---|------|
| kMaxBytesInUTF8Sequence | 4 | UTF-8 序列的最大字节数 |

## 公共 API 函数

### 编码验证与计数

| 函数签名 | 功能说明 |
|---------|---------|
| `int CountUTF8(const char* utf8, size_t byteLength)` | 统计 UTF-8 序列中的 Unicode 码点数量,非法返回 -1 |
| `int CountUTF16(const uint16_t* utf16, size_t byteLength)` | 统计 UTF-16 序列中的 Unicode 码点数量 |
| `int CountUTF32(const int32_t* utf32, size_t byteLength)` | 统计 UTF-32 序列中的 Unicode 码点数量 |

### 码点解析

| 函数签名 | 功能说明 |
|---------|---------|
| `SkUnichar NextUTF8(const char** ptr, const char* end)` | 从 UTF-8 序列中解析下一个码点,非法返回 -1 |
| `SkUnichar NextUTF8WithReplacement(const char** ptr, const char* end)` | 解析 UTF-8 码点,遇到非法字符返回替换字符 U+FFFD |
| `SkUnichar NextUTF16(const uint16_t** ptr, const uint16_t* end)` | 从 UTF-16 序列中解析下一个码点 |
| `SkUnichar NextUTF32(const int32_t** ptr, const int32_t* end)` | 从 UTF-32 序列中解析下一个码点 |

### 编码转换

| 函数签名 | 功能说明 |
|---------|---------|
| `size_t ToUTF8(SkUnichar uni, char utf8[4])` | 将 Unicode 码点编码为 UTF-8,返回字节数 |
| `size_t ToUTF16(SkUnichar uni, uint16_t utf16[2])` | 将 Unicode 码点编码为 UTF-16,返回码元数 |
| `int UTF8ToUTF16(uint16_t dst[], int dstCapacity, const char src[], size_t srcByteLength)` | UTF-8 转 UTF-16,返回所需码元数 |
| `int UTF16ToUTF8(char dst[], int dstCapacity, const uint16_t src[], size_t srcLength)` | UTF-16 转 UTF-8,返回所需字节数 |

### 辅助工具函数

| 函数签名 | 功能说明 |
|---------|---------|
| `bool IsLeadingSurrogateUTF16(uint16_t c)` | 判断是否为 UTF-16 高代理项(0xD800-0xDBFF) |
| `bool IsTrailingSurrogateUTF16(uint16_t c)` | 判断是否为 UTF-16 低代理项(0xDC00-0xDFFF) |

## 内部实现细节

### UTF-8 解码算法

**字节类型判断** (`utf8_byte_type`):
- 返回 -1: 非法字节
- 返回 0: 继续字节(0x80-0xBF)
- 返回 1: ASCII 字节(0x00-0x7F)
- 返回 2-4: 多字节序列的首字节

**解码状态机**:
```cpp
// 伪代码示例
int c = *p;
int hic = c << 24;
if (hic < 0) {  // 多字节序列
    while (hic << 1 < 0) {
        // 读取继续字节
        c = (c << 6) | (nextByte & 0x3F);
    }
}
```

### UTF-16 代理对处理

UTF-16 使用代理对(surrogate pairs)表示 U+10000 以上的码点:

**解码公式**:
```
unicode = (high << 10) + low - ((0xD800 << 10) + 0xDC00 - 0x10000)
```

**编码公式**:
```cpp
utf16[0] = (uint16_t)((0xD800 - 64) + (uni >> 10));  // 高代理项
utf16[1] = (uint16_t)(0xDC00 | (uni & 0x3FF));      // 低代理项
```

### 对齐检查

函数使用模板辅助函数确保指针对齐:
```cpp
template <typename T>
static constexpr bool is_align2(T x) { return 0 == (x & 1); }

template <typename T>
static constexpr bool is_align4(T x) { return 0 == (x & 3); }
```

### 错误处理策略

- **NextUTF8**: 遇到非法字符返回 -1,指针移至末尾
- **NextUTF8WithReplacement**: 遇到非法字符返回 U+FFFD(替换字符)
- **Count函数**: 遇到非法序列立即返回 -1

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| include/private/base/SkAPI.h | 导出符号宏定义(SK_SPI) |
| include/private/base/SkTFitsIn.h | 类型范围检查工具 |
| cstdint | 固定宽度整数类型 |
| cstddef | size_t 类型定义 |

**被依赖的模块:**

| 模块 | 使用场景 |
|------|---------|
| src/core/SkTextBlob.cpp | 文本块处理 |
| src/core/SkTypeface.cpp | 字体类型处理 |
| src/ports/SkFontHost_*.cpp | 平台字体接口 |
| modules/skshaper/ | 文本整形器 |

## 设计模式与设计决策

### 函数式设计

所有函数都是无状态的纯函数,没有全局变量或单例模式,这带来了:
- **线程安全**: 可以在多线程环境中并发调用
- **可测试性**: 易于单元测试
- **可组合性**: 函数可以自由组合使用

### 指针推进模式

解码函数采用"指针推进"模式:
```cpp
const char* ptr = utf8String;
while (ptr < end) {
    SkUnichar c = SkUTF::NextUTF8(&ptr, end);
    // 处理码点 c
}
```

这种设计简化了迭代逻辑,避免手动计算字符边界。

### 容量查询模式

编码转换函数支持两阶段调用:
1. **第一阶段**: `dst = nullptr`,返回所需空间大小
2. **第二阶段**: 分配足够空间后进行实际转换

这避免了预先分配过大缓冲区或多次尝试。

### 严格验证策略

模块采用严格的验证策略:
- 拒绝 overlong encoding(冗余编码)
- 拒绝无效的代理对序列
- 拒绝超出 Unicode 范围的码点(> U+10FFFF)

## 性能考量

### 优化技术

1. **快速 ASCII 路径**: UTF-8 的 ASCII 字符(< 0x80)只需一次检查即可识别
2. **位操作**: 使用位掩码和移位代替条件分支
3. **内联友好**: 小函数设计适合编译器内联
4. **对齐检查**: 提前检测未对齐指针,避免后续异常

### 性能特征

**UTF-8 解码**:
- ASCII 字符: O(1)
- 多字节字符: O(字节数),最多 4 次迭代

**UTF-16 解码**:
- BMP 字符: O(1)
- 代理对: O(1),两次读取

**批量转换**:
- UTF8ToUTF16: O(n),n 为源字节数
- UTF16ToUTF8: O(n),n 为源码元数

### 内存访问模式

- **顺序访问**: 所有解码都是顺序读取,缓存友好
- **无回溯**: 验证失败时不回退,直接终止
- **边界检查**: 每次访问前检查边界,防止越界

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| include/private/base/SkAPI.h | 符号导出宏 |
| include/private/base/SkTFitsIn.h | 范围检查工具 |
| src/core/SkString.h | 字符串类,使用 UTF-8 |
| src/core/SkTextBlob.h | 文本块,存储 UTF 编码文本 |
| modules/skshaper/include/SkShaper.h | 文本整形,依赖 UTF 功能 |

## 使用示例

```cpp
// 示例 1: 统计 UTF-8 字符串的码点数
const char* utf8Str = "你好世界";
int count = SkUTF::CountUTF8(utf8Str, strlen(utf8Str));

// 示例 2: 遍历 UTF-8 字符串
const char* ptr = utf8Str;
const char* end = utf8Str + strlen(utf8Str);
while (ptr < end) {
    SkUnichar codepoint = SkUTF::NextUTF8(&ptr, end);
    if (codepoint < 0) break;  // 错误处理
    // 处理 codepoint
}

// 示例 3: 编码 Unicode 码点为 UTF-8
SkUnichar uni = 0x4E2D;  // '中'
char utf8Buffer[4];
size_t bytes = SkUTF::ToUTF8(uni, utf8Buffer);

// 示例 4: UTF-8 转 UTF-16
const char* src = "Hello";
int needed = SkUTF::UTF8ToUTF16(nullptr, 0, src, strlen(src));
uint16_t* dst = new uint16_t[needed];
SkUTF::UTF8ToUTF16(dst, needed, src, strlen(src));

// 示例 5: 检查 UTF-16 代理项
uint16_t c = 0xD800;
if (SkUTF::IsLeadingSurrogateUTF16(c)) {
    // 处理高代理项
}
```

## 注意事项

1. **指针生命周期**: `Next*` 函数会修改指针参数,确保不丢失原始指针
2. **错误返回**: 返回 -1 表示错误,务必检查返回值
3. **字节长度 vs 字符数**: UTF-8/UTF-16 的字节长度不等于字符数
4. **对齐要求**: UTF-16/UTF-32 需要 2/4 字节对齐
5. **缓冲区大小**: 转换函数返回的是所需大小,不包括 null 终止符
6. **替换字符**: `NextUTF8WithReplacement` 用于容错解析,不能用于严格验证
