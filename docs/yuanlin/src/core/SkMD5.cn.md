# SkMD5

> 源文件: src/core/SkMD5.h, src/core/SkMD5.cpp

## 概述

`SkMD5` 是 Skia 中实现 MD5 哈希算法的类,符合 RFC 1321 标准。该类继承自 `SkWStream`,支持流式处理输入数据,计算 128 位 (16 字节) 的消息摘要。MD5 在 Skia 中主要用于资源缓存的键生成、数据完整性校验等场景。

## 架构位置

`SkMD5` 位于 Skia 工具层的哈希计算模块:
- 继承自 `SkWStream`,支持流式写入接口
- 用于生成缓存键、文件校验和
- 支持增量更新和一次性完成计算
- 提供十六进制字符串输出格式

## 主要类与结构体

### 核心类

| 类名 | 父类 | 说明 |
|------|------|------|
| SkMD5 | SkWStream | MD5 哈希计算器 |
| SkMD5::Digest | - | 128 位摘要结果 |

### 关键成员变量

**SkMD5**:
| 成员变量 | 类型 | 说明 |
|---------|------|------|
| byteCount | uint64_t | 已处理字节数 (modulo 2^64) |
| state[4] | uint32_t | ABCD 状态寄存器 |
| buffer[64] | uint8_t | 输入缓冲区 (512 位块) |

**SkMD5::Digest**:
| 成员变量 | 类型 | 说明 |
|---------|------|------|
| data[16] | uint8_t | 128 位摘要数据 |

## 公共 API 函数

### 构造与流式输入

```cpp
// 构造函数,初始化状态
SkMD5();

// 流式写入数据 (继承自 SkWStream)
bool write(const void* buffer, size_t size) final;

// 查询已写入字节数
size_t bytesWritten() const final;
```

### 完成计算

```cpp
// 计算并返回最终摘要
Digest finish();
```

调用 `finish()` 后,对象状态可选择性清零 (如果定义了 `SK_MD5_CLEAR_DATA`)。

### 摘要输出

```cpp
// Digest 类方法
SkString toHexString() const;          // 大写十六进制
SkString toLowercaseHexString() const; // 小写十六进制

// 摘要比较
bool operator==(Digest const& other) const;
bool operator!=(Digest const& other) const;
```

## 内部实现细节

### 初始化

```cpp
SkMD5::SkMD5() : byteCount(0) {
    // RFC 1321 魔数
    this->state[0] = 0x67452301;
    this->state[1] = 0xefcdab89;
    this->state[2] = 0x98badcfe;
    this->state[3] = 0x10325476;
}
```

### 数据处理流程

```cpp
bool SkMD5::write(const void* buf, size_t inputLength) {
    const uint8_t* input = reinterpret_cast<const uint8_t*>(buf);
    unsigned int bufferIndex = (unsigned int)(this->byteCount & 0x3F);
    unsigned int bufferAvailable = 64 - bufferIndex;

    if (inputLength >= bufferAvailable) {
        // 填满缓冲区并处理
        sk_careful_memcpy(&this->buffer[bufferIndex], input, bufferAvailable);
        transform(this->state, this->buffer);

        // 处理完整的 64 字节块
        for (inputIndex + 63 < inputLength; inputIndex += 64) {
            transform(this->state, &input[inputIndex]);
        }
    }

    // 缓存剩余数据
    sk_careful_memcpy(&this->buffer[bufferIndex], &input[inputIndex], ...);
    this->byteCount += inputLength;
    return true;
}
```

### 填充与完成

```cpp
Digest SkMD5::finish() {
    // 计算比特数
    uint8_t bits[8];
    encode(bits, this->byteCount << 3);

    // 填充到 56 mod 64
    unsigned int bufferIndex = (unsigned int)(this->byteCount & 0x3F);
    unsigned int paddingLength = (bufferIndex < 56)
        ? (56 - bufferIndex)
        : (120 - bufferIndex);

    static const uint8_t PADDING[64] = {0x80, 0, 0, ...};
    this->write(PADDING, paddingLength);

    // 追加原始长度
    this->write(bits, 8);

    // 输出摘要
    Digest digest;
    encode(digest.data, this->state);
    return digest;
}
```

填充格式: `10000000 ... 0 [原始长度 64 位]`

### 核心变换函数

```cpp
static void transform(uint32_t state[4], const uint8_t block[64]) {
    uint32_t a = state[0], b = state[1], c = state[2], d = state[3];
    uint32_t storage[16];
    const uint32_t* X = decode(storage, block);

    // 4 轮操作,每轮 16 次
    // Round 1: F 函数
    operation(F(), a, b, c, d, X[0], 7, 0xd76aa478);
    // ...

    // Round 2: G 函数
    // Round 3: H 函数
    // Round 4: I 函数

    state[0] += a;
    state[1] += b;
    state[2] += c;
    state[3] += d;
}
```

### 辅助函数

**F/G/H/I 函数**:
```cpp
struct F { uint32_t operator()(uint32_t x, uint32_t y, uint32_t z) {
    return ((y ^ z) & x) ^ z;  // 优化版本
}};

struct G { uint32_t operator()(uint32_t x, uint32_t y, uint32_t z) {
    return (x & z) | (y & (~z));
}};

struct H { uint32_t operator()(uint32_t x, uint32_t y, uint32_t z) {
    return x ^ y ^ z;
}};

struct I { uint32_t operator()(uint32_t x, uint32_t y, uint32_t z) {
    return y ^ (x | (~z));
}};
```

**循环左移**:
```cpp
static inline uint32_t rotate_left(uint32_t x, uint8_t n) {
    return (x << n) | (x >> (32 - n));
}
```

**操作模板**:
```cpp
template <typename T>
static inline void operation(T operation, uint32_t& a, uint32_t b,
                             uint32_t c, uint32_t d, uint32_t x,
                             uint8_t s, uint32_t t) {
    a = b + rotate_left(a + operation(b, c, d) + x + t, s);
}
```

### 编码/解码

**小端编码**:
```cpp
static void encode(uint8_t output[16], const uint32_t input[4]) {
    for (size_t i = 0, j = 0; i < 4; i++, j += 4) {
        output[j  ] = (uint8_t) (input[i]        & 0xff);
        output[j+1] = (uint8_t)((input[i] >>  8) & 0xff);
        output[j+2] = (uint8_t)((input[i] >> 16) & 0xff);
        output[j+3] = (uint8_t)((input[i] >> 24) & 0xff);
    }
}
```

**小端解码**:
```cpp
static const uint32_t* decode(uint32_t storage[16], const uint8_t input[64]) {
#if defined(SK_CPU_LENDIAN) && defined(SK_CPU_FAST_UNALIGNED_ACCESS)
    return reinterpret_cast<const uint32_t*>(input);  // 零拷贝
#else
    // 拷贝并转换
    for (size_t i = 0, j = 0; j < 64; i++, j += 4) {
        storage[i] = ((uint32_t)input[j]) |
                     (((uint32_t)input[j+1]) << 8) |
                     (((uint32_t)input[j+2]) << 16) |
                     (((uint32_t)input[j+3]) << 24);
    }
    return storage;
#endif
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkStream | 流式输入接口 |
| SkString | 字符串输出 |
| SkUtils | 内存操作工具 |
| SkMalloc | 内存分配 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| SkResourceCache | 使用 MD5 生成缓存键 |
| SkPicture | 序列化数据校验 |

## 设计模式与设计决策

### 1. 流式接口
继承 `SkWStream` 支持标准流操作:
```cpp
SkMD5 md5;
md5.write(data1, size1);
md5.write(data2, size2);
SkMD5::Digest digest = md5.finish();
```

### 2. 不可变摘要
`Digest` 结构体仅包含数据和比较/输出方法,不可修改:
```cpp
struct Digest {
    uint8_t data[16];
    bool operator==(Digest const& other) const;
    SkString toHexString() const;
};
```

### 3. 条件编译优化
```cpp
#if defined(SK_MD5_CLEAR_DATA)
    memset(this, 0, sizeof(*this));  // 清除敏感数据
#endif
```

### 4. 平台优化
```cpp
#if defined(SK_CPU_LENDIAN) && defined(SK_CPU_FAST_UNALIGNED_ACCESS)
    return reinterpret_cast<const uint32_t*>(input);  // 小端且支持非对齐访问
#else
    // 通用路径
#endif
```

## 性能考量

### 1. 块处理优化
每次处理完整的 64 字节块,减少循环开销:
```cpp
for (; inputIndex + 63 < inputLength; inputIndex += 64) {
    transform(this->state, &input[inputIndex]);
}
```

### 2. 零拷贝解码
小端平台支持非对齐访问时直接转换:
```cpp
return reinterpret_cast<const uint32_t*>(input);
```

### 3. 内联函数
关键函数标记为 `inline`:
```cpp
static inline uint32_t rotate_left(uint32_t x, uint8_t n);
```

### 4. 位运算优化
F 函数使用等价但更快的位运算:
```cpp
// 标准: (x & y) | ((~x) & z)
// 优化: ((y ^ z) & x) ^ z
```

### 5. 模板特化
使用模板避免虚函数调用:
```cpp
template <typename T>
static inline void operation(T operation, ...)
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/core/SkStream.h | 基类 | 流式接口 |
| include/core/SkString.h | 依赖 | 字符串输出 |
| src/base/SkUtils.h | 依赖 | 内存工具 |
| src/core/SkResourceCache.h | 使用者 | 缓存键生成 |
