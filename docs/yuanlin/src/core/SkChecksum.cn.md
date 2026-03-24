# SkChecksum

> 源文件: src/core/SkChecksum.h, src/core/SkChecksum.cpp

## 概述

`SkChecksum` 是 Skia 提供的高性能哈希函数库,基于 wyhash 算法实现。它提供快速、高质量的 32 位和 64 位哈希函数,用于 Skia 内部的数据结构(如哈希表、缓存键生成)和跨模块使用(如 SkParagraph)。该模块还提供了便捷的哈希工具类 `SkGoodHash` 和 `SkForceDirectHash`,支持各种数据类型的哈希计算。

Skia 明确声明不保证哈希值的跨版本或跨设备稳定性,允许持续优化哈希算法。

## 架构位置

`SkChecksum` 在 Skia 架构中的位置:
- 作为基础工具库,被多个模块依赖
- 为 Skia 内部哈希表实现提供哈希函数
- 导出为 SK_SPI (Skia Private Interface),供特定外部模块使用
- 被 `SkGoodHash` 等高层工具类封装使用
- 支持字符串、POD 类型、自定义类型的哈希

## 主要类与结构体

### SkChecksum 命名空间

提供核心哈希函数的静态函数集合。

**主要函数:**

| 函数 | 签名 | 说明 |
|------|------|------|
| Mix | `uint32_t Mix(uint32_t hash)` | Murmur3 finalizer,混合低位 |
| CheapMix | `uint32_t CheapMix(uint32_t hash)` | 简化版混合,用于字体缓存 |
| Hash32 | `uint32_t Hash32(const void*, size_t, uint32_t seed=0)` | 32 位 wyhash |
| Hash64 | `uint64_t Hash64(const void*, size_t, uint64_t seed=0)` | 64 位 wyhash |

### SkGoodHash 结构体

通用哈希函数对象,支持多种类型。

**继承关系:**
- 无继承关系(仿函数)

**支持的类型:**
- 4 字节 POD 类型(使用 `Mix`)
- 其他 POD 类型(使用 `Hash32`)
- `SkString`
- `std::string`
- `std::string_view`

**模板实现:**

```cpp
template <typename K>
std::enable_if_t<std::has_unique_object_representations<K>::value && sizeof(K) == 4, uint32_t>
operator()(const K& k) const {
    return SkChecksum::Mix(*(const uint32_t*)&k);
}
```

### SkForceDirectHash 模板

强制位级哈希的工具,用于包含 NaN 的浮点类型或带填充的结构体。

**用途:**
- 处理不满足 `std::has_unique_object_representations` 的类型
- 应谨慎使用,可能导致等价对象产生不同哈希值

## 公共 API 函数

### 基础混合函数

```cpp
static inline uint32_t Mix(uint32_t hash)
```
应用 Murmur3 finalizer,改善低位混合度:
```
hash ^= hash >> 16
hash *= 0x85ebca6b
hash ^= hash >> 13
hash *= 0xc2b2ae35
hash ^= hash >> 16
```

```cpp
static inline uint32_t CheapMix(uint32_t hash)
```
简化版混合(3 步而非 5 步):
```
hash ^= hash >> 16
hash *= 0x85ebca6b
hash ^= hash >> 16
```

### 核心哈希函数

```cpp
uint32_t SK_SPI Hash32(const void* data, size_t bytes, uint32_t seed = 0)
```
计算 32 位哈希值,使用 wyhash 算法并截断到 32 位。

```cpp
uint64_t SK_SPI Hash64(const void* data, size_t bytes, uint64_t seed = 0)
```
计算 64 位哈希值,完整的 wyhash 算法。

**参数:**
- `data`: 数据指针
- `bytes`: 数据字节数
- `seed`: 哈希种子(默认 0)

**返回值:**
- 32 位或 64 位哈希值

### SkGoodHash 使用示例

```cpp
SkGoodHash hasher;

// 4 字节类型(快速路径)
int x = 42;
uint32_t h1 = hasher(x);  // 使用 Mix

// 其他 POD 类型
struct Point { float x, y; };
Point p{1.0f, 2.0f};
uint32_t h2 = hasher(p);  // 使用 Hash32

// 字符串类型
SkString str("hello");
uint32_t h3 = hasher(str);  // Hash32(str.c_str(), str.size())

std::string_view sv = "world";
uint32_t h4 = hasher(sv);   // Hash32(sv.data(), sv.size())
```

## 内部实现细节

### wyhash 算法

wyhash 是一个快速、高质量的非加密哈希函数,来自 https://github.com/wangyi-fudan/wyhash。

#### 核心操作

**128 位乘法** (`_wymum`):
```cpp
static inline void _wymum(uint64_t* A, uint64_t* B) {
#if defined(__SIZEOF_INT128__)
    __uint128_t r = *A;
    r *= *B;
    *A = (uint64_t)r;
    *B = (uint64_t)(r >> 64);
#elif defined(_MSC_VER) && defined(_M_X64)
    *A = _umul128(*A, *B, B);
#else
    // 软件实现:分解为 32 位乘法
    // ...
#endif
}
```

根据平台选择:
- GCC/Clang: 使用 `__uint128_t`
- MSVC x64: 使用 `_umul128` intrinsic
- 其他: 软件实现(4 次 32 位乘法)

**混合函数** (`_wymix`):
```cpp
static inline uint64_t _wymix(uint64_t A, uint64_t B) {
    _wymum(&A, &B);
    return A ^ B;
}
```

乘法后异或高低位。

#### 数据读取

```cpp
static inline uint64_t _wyr8(const uint8_t* p) {
    uint64_t v;
    memcpy(&v, p, 8);  // 安全的未对齐读取
    return v;
}

static inline uint64_t _wyr4(const uint8_t* p) {
    uint32_t v;
    memcpy(&v, p, 4);
    return v;
}

static inline uint64_t _wyr3(const uint8_t* p, size_t k) {
    return (((uint64_t)p[0]) << 16) | (((uint64_t)p[k >> 1]) << 8) | p[k - 1];
}
```

使用 `memcpy` 实现可移植的未对齐读取,编译器优化为直接加载。

#### 主循环

```cpp
uint64_t wyhash(const void* key, size_t len, uint64_t seed, const uint64_t* secret) {
    const uint8_t* p = (const uint8_t*)key;
    seed ^= _wymix(seed ^ secret[0], secret[1]);

    if (len <= 16) SK_LIKELY {
        // 小数据快速路径
    } else {
        size_t i = len;
        if (i > 48) SK_UNLIKELY {
            uint64_t see1 = seed, see2 = seed;
            do {
                seed = _wymix(_wyr8(p) ^ secret[1], _wyr8(p + 8) ^ seed);
                see1 = _wymix(_wyr8(p + 16) ^ secret[2], _wyr8(p + 24) ^ see1);
                see2 = _wymix(_wyr8(p + 32) ^ secret[3], _wyr8(p + 40) ^ see2);
                p += 48;
                i -= 48;
            } while (i > 48) SK_LIKELY;
            seed ^= see1 ^ see2;
        }
        // 处理剩余数据
    }
    // ...
}
```

特点:
- 小数据(≤16 字节)快速路径
- 大数据(>48 字节)使用 3 路并行处理
- 使用 `SK_LIKELY`/`SK_UNLIKELY` 宏优化分支预测

#### 秘密参数

```cpp
static const uint64_t _wyp[4] = {
    0xa0761d6478bd642full, 0xe7037ed1a0b428dbull,
    0x8ebc6af09c88c6e3ull, 0x589965cc75374cc3ull
};
```

固定的秘密参数提供雪崩效应和混合特性。

### SkGoodHash 类型特化

#### 4 字节类型快速路径

```cpp
template <typename K>
std::enable_if_t<std::has_unique_object_representations<K>::value && sizeof(K) == 4, uint32_t>
operator()(const K& k) const {
    return SkChecksum::Mix(*(const uint32_t*)&k);
}
```

对于 `int`, `float` 等 4 字节类型,直接转换为 `uint32_t` 并混合,无需 `Hash32` 调用。

#### 通用 POD 类型

```cpp
template <typename K>
std::enable_if_t<std::has_unique_object_representations<K>::value && sizeof(K) != 4, uint32_t>
operator()(const K& k) const {
    return SkChecksum::Hash32(&k, sizeof(K));
}
```

要求类型满足 `std::has_unique_object_representations`(无填充字节,无 NaN 歧义)。

#### 字符串类型

```cpp
uint32_t operator()(const SkString& k) const {
    return SkChecksum::Hash32(k.c_str(), k.size());
}
```

对字符串内容哈希,不包括终止符。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| include/core/SkString.h | SkString 哈希支持 |
| include/private/base/SkAPI.h | SK_SPI 宏定义 |
| include/private/base/SkAssert.h | 断言 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| SkTHash | 哈希表使用 SkGoodHash |
| SkResourceCache | 缓存键哈希 |
| SkParagraph | 文本布局缓存 |
| SkFontMgr | 字体缓存键 |
| 各种缓存系统 | GenID 生成 |

## 设计模式与设计决策

### 命名空间而非类

使用命名空间 `SkChecksum` 而非类:
- 所有函数都是静态的
- 避免不必要的实例化
- 清晰的 API 设计

### SFINAE 类型选择

```cpp
std::enable_if_t<std::has_unique_object_representations<K>::value && sizeof(K) == 4, uint32_t>
```

编译期类型检查:
- 确保只有安全类型使用位级哈希
- 为不同大小的类型选择不同实现
- 避免运行时开销

### 算法可替换性

明确声明不保证哈希稳定性:
- 允许升级到更优算法
- 支持平台特定优化
- 不能用于持久化或网络传输

### 种子参数设计

提供种子参数但默认为 0:
- 支持哈希函数族
- 可用于随机化防御哈希碰撞攻击
- 大多数情况使用默认值简化 API

## 性能考量

### 小数据优化

```cpp
if (len <= 16) SK_LIKELY {
    if (len >= 4) SK_LIKELY {
        a = (_wyr4(p) << 32) | _wyr4(p + ((len >> 3) << 2));
        b = (_wyr4(p + len - 4) << 32) | _wyr4(p + len - 4 - ((len >> 3) << 2));
    } else if (len > 0) SK_LIKELY {
        a = _wyr3(p, len);
        b = 0;
    } else
        a = b = 0;
}
```

针对小数据(≤16 字节):
- 避免循环开销
- 读取固定次数(最多 4 次)
- 分支预测友好

### 大数据并行

```cpp
do {
    seed = _wymix(_wyr8(p) ^ secret[1], _wyr8(p + 8) ^ seed);
    see1 = _wymix(_wyr8(p + 16) ^ secret[2], _wyr8(p + 24) ^ see1);
    see2 = _wymix(_wyr8(p + 32) ^ secret[3], _wyr8(p + 40) ^ see2);
    p += 48;
    i -= 48;
} while (i > 48) SK_LIKELY;
```

3 路并行处理:
- 利用指令级并行(ILP)
- 减少数据依赖链
- 现代 CPU 可同时执行多个 `_wymix`

### Mix 函数权衡

`Mix` vs `CheapMix`:
- `Mix`: 5 次操作,更好的雪崩效应
- `CheapMix`: 3 次操作,适用于已有良好分布的哈希值

字体缓存使用 `CheapMix`:
- 输入已经是哈希值或随机分布
- 减少 CPU 周期
- 权衡质量与速度

### 4 字节类型特化

```cpp
return SkChecksum::Mix(*(const uint32_t*)&k);
```

对于 `int` 等类型:
- 避免 `Hash32` 函数调用
- 3 次位操作即可完成
- 对小型键的哈希表性能关键

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/private/SkTHash.h | 主要使用者 | 哈希表实现 |
| src/core/SkResourceCache.h | 使用者 | 资源缓存键 |
| modules/skparagraph | 使用者 | 文本布局缓存 |
| include/core/SkString.h | 集成 | SkString 哈希支持 |
| tests/ChecksumTest.cpp | 测试 | 单元测试 |
