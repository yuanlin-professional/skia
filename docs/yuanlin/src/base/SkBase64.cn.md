# SkBase64

> 源文件: `src/base/SkBase64.h`, `src/base/SkBase64.cpp`

## 概述

SkBase64 提供 Base64 编码和解码功能,用于将二进制数据转换为 ASCII 可打印字符串。该实现支持标准 Base64 编码表和自定义编码表,主要用于数据序列化、URL 安全编码和文本协议传输场景。

## 架构位置

- **所属子系统**: 基础设施层 (Base Infrastructure)
- **层级**: 工具类 - 数据编码
- **作用域**: 为 Skia 的序列化、调试输出、测试工具提供 Base64 编解码

## 主要类与结构体

### SkBase64

纯静态工具类,提供 Base64 编码和解码方法。

**继承关系**: 无

**枚举类型**:

#### Error 枚举
| 枚举值 | 说明 |
|--------|------|
| kNoError | 解码成功 |
| kPadError | 填充字符错误或位置不正确 |
| kBadCharError | 遇到非法字符 |

## 公共 API 函数

### `static size_t Encode(const void*, size_t, void*, const char*)`
- **功能**: 将二进制数据编码为 Base64 字符串
- **参数**:
  - `src`: 源数据指针
  - `length`: 源数据字节数
  - `dst`: 目标缓冲区指针(可为 nullptr 用于查询所需大小)
  - `encode`: 自定义编码表(可为 nullptr 使用默认表)
- **返回值**: 编码后的字符串长度(字节数)
- **用法**: 通常先传 nullptr 查询大小,再分配缓冲区并真正编码

**示例**:
```cpp
const uint8_t data[] = {0x12, 0x34, 0x56};
size_t encodedSize = SkBase64::Encode(data, 3, nullptr);
std::vector<char> buffer(encodedSize);
SkBase64::Encode(data, 3, buffer.data());
// buffer 现在包含 "EjRW"
```

### `static size_t EncodedSize(size_t srcDataLength)`
- **功能**: 计算编码指定长度数据所需的缓冲区大小
- **参数**: `srcDataLength` - 源数据字节数
- **返回值**: 编码后的字节数
- **公式**: `((srcDataLength + 2) / 3) * 4`

**说明**: 每 3 字节源数据编码为 4 字节 Base64 字符,不足 3 字节的填充到 4 字节。

### `static Error Decode(const void*, size_t, void*, size_t*)`
- **功能**: 将 Base64 字符串解码为二进制数据
- **参数**:
  - `src`: Base64 字符串指针
  - `srcLength`: 字符串长度
  - `dst`: 目标缓冲区指针(可为 nullptr 用于查询所需大小)
  - `dstLength`: 输出参数,存储解码后的字节数
- **返回值**: Error 枚举值
- **用法**: 先传 nullptr 查询大小,再分配缓冲区并解码

**示例**:
```cpp
const char* encoded = "EjRW";
size_t decodedSize;
auto err = SkBase64::Decode(encoded, 4, nullptr, &decodedSize);
if (err == SkBase64::kNoError) {
    std::vector<uint8_t> buffer(decodedSize);
    SkBase64::Decode(encoded, 4, buffer.data(), &decodedSize);
    // buffer 现在包含 {0x12, 0x34, 0x56}
}
```

## 内部实现细节

### 编码算法

Base64 将每 3 个字节(24 位)分为 4 个 6 位组,每组映射到 64 字符编码表:

```
源字节:  [AAAAAAAA] [BBBBBBBB] [CCCCCCCC]
       ↓
6位组:  [AAAAAA][AABBBB][BBBBCC][CCCCCC]
       ↓
索引:   [  a  ][  b  ][  c  ][  d  ]
       ↓
Base64: [enc[a]][enc[b]][enc[c]][enc[d]]
```

**处理流程**:
```cpp
unsigned a = *src++;
unsigned b = *src++;
unsigned c = *src++;
int d = c & 0x3F;               // 低 6 位
c = (c >> 6 | b << 2) & 0x3F;   // 中间 6 位
b = (b >> 4 | a << 4) & 0x3F;   // 中间 6 位
a = a >> 2;                     // 高 6 位
*dst++ = encode[a];
*dst++ = encode[b];
*dst++ = encode[c];
*dst++ = encode[d];
```

**尾部处理**:
- 剩余 1 字节: 编码为 2 个字符 + 2 个填充符 `=`
- 剩余 2 字节: 编码为 3 个字符 + 1 个填充符 `=`

### 解码算法

反向映射 Base64 字符到 6 位值,组合为原始字节:

```
Base64: [enc[a]][enc[b]][enc[c]][enc[d]]
       ↓
索引:   [  a  ][  b  ][  c  ][  d  ]
       ↓
6位组:  [AAAAAA][AABBBB][BBBBCC][CCCCCC]
       ↓
字节:   [AAAAAAAA] [BBBBBBBB] [CCCCCCCC]
```

**解码表** (`decodeData`):
- 索引范围: `['+' - '+', 'z' - '+']` = `[0, 74]`
- 合法字符映射到 `[0, 63]`
- 填充符 `=` 映射到 `DecodePad` (-2)
- 非法字符映射到 -1

**处理流程**:
```cpp
uint8_t bytes[4];
// 读取 4 个字符,解码为 bytes[0-3]
int one = (uint8_t)(bytes[0] << 2);
int two = bytes[1];
one |= two >> 4;
two = (uint8_t)((two << 4) & 0xFF);
int three = bytes[2];
two |= three >> 2;
three = (uint8_t)((three << 6) & 0xFF);
three |= bytes[3];
dst[i++] = (unsigned char)one;
dst[i++] = (unsigned char)two;
dst[i++] = (unsigned char)three;
```

### 填充处理

**编码填充**:
```cpp
if (remainder == 1) {
    int a = *src;
    *dst++ = encode[a >> 2];
    *dst++ = encode[(a << 4) & 0x3F];
    *dst++ = encode[EncodePad];  // '='
    *dst++ = encode[EncodePad];  // '='
}
```

**解码填充检测**:
```cpp
if (byte < 2) return kPadError;  // 前两个字符不能是填充
padThree = true;
if (byte == 2) padTwo = true;
// padTwo: 只输出 1 字节
// padThree && !padTwo: 输出 2 字节
```

### 空白字符处理

解码时自动跳过空白字符(ASCII ≤ 32):
```cpp
if (srcByte <= ' ') continue;  // 空格、换行、制表符等
```

允许格式化的 Base64 字符串:
```
EjRW
YWJj
ZGVm
```

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| SkAssert.h | 断言检查 |
| cstdint | 固定宽度整数类型 |

### 被依赖的模块
- **测试工具**: 序列化和反序列化测试数据
- **调试工具**: 编码二进制数据为可打印字符串
- **网络传输**: 在文本协议中传输二进制数据

## 设计模式与设计决策

### 设计模式
1. **静态工具类**: 无状态设计,所有方法为静态
2. **两步调用模式**: 先查询大小,再分配并执行

### 设计决策

**为什么支持自定义编码表?**
- 默认表: `A-Za-z0-9+/=`
- 自定义表允许 URL 安全编码(如 `-_` 替换 `+/`)
- 64 字符编码表 + 1 个填充字符 = 65 字符

**为什么解码表用 signed char?**
- 使用负值表示特殊状态(非法字符 -1,填充 -2)
- 合法值范围 0-63 适合 uint8_t,但需要特殊值

**为什么允许空白字符?**
- 兼容多行 Base64 字符串
- 简化手动输入和格式化输出
- 符合 RFC 4648 规范建议

**为什么使用两步调用?**
- 避免强制调用者预分配固定大小缓冲区
- 允许精确分配,减少内存浪费
- 支持只查询大小的场景

## 性能考量

### 时间复杂度
- `Encode()`: O(n) n 为源数据字节数
- `Decode()`: O(m) m 为 Base64 字符串长度
- `EncodedSize()`: O(1)

### 空间效率
- **编码膨胀率**: 约 133% (每 3 字节变 4 字节)
- **解码收缩率**: 约 75% (每 4 字节变 3 字节)
- **填充开销**: 最多 2 字节

### 优化策略
1. **位运算**: 使用移位和掩码替代乘除
2. **批量处理**: 主循环每次处理 3 字节
3. **查表法**: 解码使用预计算的 decodeData 表
4. **无分支**: 在关键路径避免条件判断

### 性能特征
- 现代 CPU 上约 1-2 GB/s 编码速度
- 解码略慢,约 0.8-1.5 GB/s
- 缓存友好的顺序访问

## 相关文件
| 文件 | 关系 |
|------|------|
| tests/SkBase64Test.cpp | 单元测试 |
| tools/ | 命令行编解码工具 |

## 标准编码表

### 默认 Base64 编码表
```
索引  0-25: A-Z
索引 26-51: a-z
索引 52-61: 0-9
索引    62: +
索引    63: /
填充字符: =
```

完整字符串:
```cpp
"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
```

### 解码映射示例
| 字符 | ASCII | 索引(decodeData) | 解码值 |
|------|-------|------------------|--------|
| '+' | 43 | 0 | 62 |
| '/' | 47 | 4 | 63 |
| '0' | 48 | 5 | 52 |
| '9' | 57 | 14 | 61 |
| '=' | 61 | 18 | -2 (DecodePad) |
| 'A' | 65 | 22 | 0 |
| 'Z' | 90 | 47 | 25 |
| 'a' | 97 | 54 | 26 |
| 'z' | 122 | 79 | 51 |

## 使用示例

### 示例 1: 简单编码
```cpp
const char* text = "Hello";
size_t size = SkBase64::EncodedSize(5);
std::vector<char> encoded(size + 1);  // +1 用于 null 终止符
SkBase64::Encode(text, 5, encoded.data());
encoded[size] = '\0';
// encoded: "SGVsbG8="
```

### 示例 2: 简单解码
```cpp
const char* b64 = "SGVsbG8=";
size_t outLen;
SkBase64::Decode(b64, 8, nullptr, &outLen);
std::vector<char> decoded(outLen + 1);
SkBase64::Decode(b64, 8, decoded.data(), &outLen);
decoded[outLen] = '\0';
// decoded: "Hello"
```

### 示例 3: 自定义编码表(URL 安全)
```cpp
const char urlSafe[] =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_=";
const uint8_t data[] = {0xFF, 0xEF};
char output[8];
SkBase64::Encode(data, 2, output, urlSafe);
// output: "_-8=" (使用 - 和 _ 替代 + 和 /)
```

### 示例 4: 错误处理
```cpp
const char* invalid = "SGVs!G8=";  // 包含非法字符 '!'
size_t outLen;
auto err = SkBase64::Decode(invalid, 8, nullptr, &outLen);
if (err == SkBase64::kBadCharError) {
    // 处理非法字符错误
}
```

## 注意事项

1. **自定义编码表限制**:
   - 必须至少 65 字符
   - 第 64 个字符用作填充符
   - 自定义编码的数据无法用默认解码

2. **内存安全**:
   - 调用者负责确保缓冲区足够大
   - 建议使用 EncodedSize() 计算

3. **线程安全**: 纯函数,完全线程安全

4. **字符集**: 仅支持 ASCII,不处理 Unicode

5. **性能提示**:
   - 大数据编码时预分配缓冲区
   - 避免频繁小块编码,合并后一次处理

6. **填充检测**:
   - 填充符只能出现在末尾
   - 最多 2 个连续填充符
   - 填充符前至少 2 个数据字符
