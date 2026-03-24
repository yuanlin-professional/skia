# SkStringUtils

> 源文件
> - src/core/SkStringUtils.h
> - src/core/SkStringUtils.cpp

## 概述

`SkStringUtils` 是 Skia 内部的字符串工具库,提供数值到字符串转换、字符串格式化、UTF-16 转换和字符串分割等实用函数。这些工具主要用于调试输出、序列化、代码生成和跨平台文本处理。该模块特别关注浮点数的跨平台一致性表示,确保在不同平台上生成相同的输出。

主要功能:
- 标量(Scalar)到字符串的十进制和十六进制转换
- 字符串缩进工具(用于格式化输出)
- UTF-16 到 UTF-8 的转换
- 字符串分割(支持多种分隔符和模式)
- 跨平台字符串比较

## 架构位置

`SkStringUtils` 在 Skia 架构中的位置:
- **层级**: 基础工具层,被其他模块调用
- **依赖**: 依赖 `SkString`、`SkUTF` 等基础模块
- **用途**: 主要用于调试、序列化、测试和代码生成
- **跨平台**: 提供统一的字符串操作接口

## 主要类与结构体

### SkScalarAsStringType (枚举)

**定义**:
```cpp
enum SkScalarAsStringType {
    kDec_SkScalarAsStringType,  // 十进制格式
    kHex_SkScalarAsStringType,  // 十六进制格式(C++风格)
};
```

### SkStrSplitMode (枚举)

**定义**:
```cpp
enum SkStrSplitMode {
    kStrict_SkStrSplitMode,    // 严格模式:保留空字符串
    kCoalesce_SkStrSplitMode   // 合并模式:跳过空字符串
};
```

**行为差异**:

| 输入 | 分隔符 | Strict 模式 | Coalesce 模式 |
|------|--------|-------------|---------------|
| `"a,b,c"` | `','` | `["a","b","c"]` | `["a","b","c"]` |
| `",,"` | `','` | `["","",""]` | `[]` |
| `"a,,b"` | `','` | `["a","","b"]` | `["a","b"]` |
| `",a,"` | `','` | `["","a",""]` | `["a"]` |

## 公共 API 函数

### Scalar 转换

```cpp
// 添加 Scalar 到字符串(十进制或十六进制)
void SkAppendScalar(SkString*, SkScalar, SkScalarAsStringType);

// 便捷函数
static inline void SkAppendScalarDec(SkString* str, SkScalar value);
static inline void SkAppendScalarHex(SkString* str, SkScalar value);
```

**输出示例**:
- 十进制: `3.14159265f`, `42`, `0.5f`
- 十六进制: `SkBits2Float(0x40490fdb)`

### 字符串格式化

```cpp
// 缩进每一行
SkString SkTabString(const SkString& string, int tabCnt);
```

**示例**:
```cpp
SkString input("line1\nline2\n");
SkString output = SkTabString(input, 2);
// 输出:
// "\t\tline1\n"
// "\t\tline2\n"
```

### UTF-16 转换

```cpp
// 从 UTF-16 创建 UTF-8 字符串
SkString SkStringFromUTF16(const uint16_t* src, size_t count);
```

### 字符串分割

```cpp
// 按分隔符分割字符串
void SkStrSplit(const char* str,
                const char* delimiters,
                SkStrSplitMode splitMode,
                skia_private::TArray<SkString>* out);

// 默认使用 Coalesce 模式
inline void SkStrSplit(const char* str,
                       const char* delimiters,
                       skia_private::TArray<SkString>* out);
```

### 跨平台字符串比较

```cpp
// 不区分大小写的字符串比较
#if defined(SK_BUILD_FOR_WIN)
    #define SK_strcasecmp   _stricmp
#else
    #define SK_strcasecmp   strcasecmp
#endif
```

## 内部实现细节

### Scalar 十进制转换

```cpp
void SkAppendScalar(SkString* str, SkScalar value, SkScalarAsStringType asType) {
    switch (asType) {
        case kDec_SkScalarAsStringType: {
            SkString tmp;
            tmp.printf("%.9g", value);  // 9位有效数字
            if (tmp.contains('.')) {
                tmp.appendUnichar('f');  // 添加浮点后缀
            }
            str->append(tmp);
            break;
        }
        // ...
    }
}
```

**设计特点**:
- 使用 `%.9g` 确保浮点数精度
- 自动添加 `f` 后缀(C++ 风格)
- 跨平台一致输出

### Scalar 十六进制转换

```cpp
case kHex_SkScalarAsStringType:
    str->appendf("SkBits2Float(0x%08x)", SkFloat2Bits(value));
    break;
```

**用途**:
- 精确表示浮点数(用于测试)
- 避免浮点精度问题
- 可直接作为 C++ 代码使用

### 字符串缩进实现

```cpp
SkString SkTabString(const SkString& string, int tabCnt) {
    if (tabCnt <= 0) return string;

    SkString tabs;
    for (int i = 0; i < tabCnt; ++i) {
        tabs.append("\t");
    }

    SkString result;
    const char* input = string.c_str();
    int nextNL = SkStrFind(input, "\n");
    while (nextNL >= 0) {
        if (nextNL > 0) {
            result.append(tabs);  // 仅为非空行添加缩进
        }
        result.append(input, nextNL + 1);
        input += nextNL + 1;
        nextNL = SkStrFind(input, "\n");
    }
    if (*input != '\0') {
        result.append(tabs);
        result.append(input);
    }
    return result;
}
```

### UTF-16 转 UTF-8

```cpp
SkString SkStringFromUTF16(const uint16_t* src, size_t count) {
    SkString ret;
    const uint16_t* stop = src + count;
    if (count > 0) {
        // 第一遍:计算 UTF-8 字节数
        size_t n = 0;
        const uint16_t* end = src + count;
        for (const uint16_t* ptr = src; ptr < end;) {
            const uint16_t* last = ptr;
            SkUnichar u = SkUTF::NextUTF16(&ptr, stop);
            size_t s = SkUTF::ToUTF8(u);
            if (n > UINT32_MAX - s) {
                end = last;  // 截断防止溢出
                break;
            }
            n += s;
        }
        // 第二遍:实际转换
        ret = SkString(n);
        char* out = ret.data();
        for (const uint16_t* ptr = src; ptr < end;) {
            out += SkUTF::ToUTF8(SkUTF::NextUTF16(&ptr, stop), out);
        }
    }
    return ret;
}
```

**设计特点**:
- 两遍扫描:先计算大小,后转换
- 防止整数溢出
- 处理不完整的代理对

### 字符串分割实现

```cpp
void SkStrSplit(const char* str,
                const char* delimiters,
                SkStrSplitMode splitMode,
                TArray<SkString>* out) {
    if (splitMode == kCoalesce_SkStrSplitMode) {
        // 跳过前导分隔符
        str += strspn(str, delimiters);
    }
    if (!*str) return;

    while (true) {
        // 查找下一个分隔符
        const size_t len = strcspn(str, delimiters);
        if (splitMode == kStrict_SkStrSplitMode || len > 0) {
            out->push_back().set(str, len);
            str += len;
        }

        if (!*str) return;

        if (splitMode == kCoalesce_SkStrSplitMode) {
            str += strspn(str, delimiters);  // 跳过所有分隔符
        } else {
            str += 1;  // 跳过单个分隔符
        }
    }
}
```

**性能优化**:
- 使用 `strcspn` 和 `strspn` C 标准库函数
- 避免重复扫描
- 原地操作,无额外内存分配

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkString` | 字符串容器 |
| `SkUTF` | UTF 编码转换 |
| `SkFloatBits` | 浮点数位操作 |
| `SkTArray` | 动态数组 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| 调试工具 | 格式化输出 |
| 序列化 | 数值到字符串转换 |
| 测试框架 | 生成测试输入 |
| 代码生成 | 生成 C++ 代码 |

## 设计模式与设计决策

### 设计决策

1. **浮点数一致性**:
   - 使用 `%.9g` 确保跨平台一致
   - 处理特殊值(NaN, Inf)
   - 十六进制模式用于精确表示

2. **两种分割模式**:
   - Strict: 适用于 CSV 等严格格式
   - Coalesce: 适用于命令行参数等场景

3. **UTF-16 安全性**:
   - 两遍扫描避免缓冲区溢出
   - 处理截断的代理对
   - UINT32_MAX 保护

4. **内联便捷函数**:
   - `SkAppendScalarDec` 等内联函数
   - 减少调用开销
   - 提高代码可读性

5. **跨平台抽象**:
   - `SK_strcasecmp` 宏适配不同平台
   - 统一接口,隐藏平台差异

## 性能考量

1. **缩进优化**:
   - 预构建 tabs 字符串
   - 仅在非空行添加缩进
   - 避免重复字符串分配

2. **UTF-16 转换**:
   - 两遍扫描权衡:
     - 优点: 精确分配,无重分配
     - 缺点: 扫描两次
   - 适用于大多数场景(字符串不太长)

3. **字符串分割**:
   - 使用 C 标准库函数(高度优化)
   - 直接操作指针,无拷贝
   - 仅在输出时分配内存

4. **Scalar 转换**:
   - 十进制: 使用 printf 格式化(成熟实现)
   - 十六进制: 直接位操作(极快)

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/core/SkString.h` | 字符串类 |
| `src/base/SkUTF.h` | UTF 编码工具 |
| `src/base/SkFloatBits.h` | 浮点数位操作 |
| `include/private/base/SkTArray.h` | 动态数组 |
