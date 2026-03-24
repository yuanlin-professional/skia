# Fuzz - 模糊测试核心数据读取器

> 源文件:
> - `fuzz/Fuzz.h`
> - `fuzz/Fuzz.cpp`

## 概述

`Fuzz` 类是 Skia 模糊测试框架的核心数据读取器，它将原始字节流转换为各种 C++ 类型的值，供 fuzzer 函数使用。该类提供了一套精心设计的 API，确保跨平台的确定性行为，同时支持范围约束和枚举类型的安全读取。此外，本模块还定义了 `Fuzzable` 结构体和 `DEF_FUZZ` 宏，用于注册模糊测试用例。

## 架构位置

```
OSS-Fuzz / libFuzzer
    ↓ (提供原始字节)
Fuzz (核心数据读取器)  <── 本模块
    ↓ (提供类型化数据)
├── FuzzCommon (图形对象生成)
├── FuzzCanvasHelpers (Canvas 操作生成)
└── 各种 DEF_FUZZ 注册的 fuzzer
```

`Fuzz` 类是整个模糊测试基础设施的最底层组件，所有 fuzzer 都通过它获取输入数据。

## 主要类与结构体

### `Fuzz` 类

不可复制的模糊数据读取器，封装了一个 `const uint8_t*` 数据缓冲区和读取位置。

| 成员 | 类型 | 描述 |
|------|------|------|
| `fData` | `const uint8_t*` | 模糊数据缓冲区指针 |
| `fSize` | `size_t` | 缓冲区总大小 |
| `fNextByte` | `size_t` | 当前读取位置 |

### `Fuzzable` 结构体

描述一个可模糊测试的目标：
- `name` (`const char*`): fuzzer 名称
- `fn` (`void (*)(Fuzz*)`): fuzzer 函数指针

## 公共 API 函数

| 函数 | 描述 |
|------|------|
| `Fuzz(data, size)` | 构造函数，接受原始字节数据 |
| `size()` | 返回数据总字节数 |
| `exhausted()` | 判断是否已读完所有数据 |
| `deplete()` | 将读取位置设为末尾，标记数据耗尽 |
| `remainingSize()` | 返回剩余未读字节数 |
| `remainingData()` | 返回剩余数据的指针 |
| `next(T*)` | 从数据中读取 `sizeof(T)` 字节到指针指向的变量 |
| `next(Arg*, Args...)` | 变参版本，一次读取多个值 |
| `nextRange(T*, min, max)` | 读取值并钳制到 [min, max] 范围 |
| `nextEnum(T*, max)` | 读取枚举值并钳制到 [0, max] 范围 |
| `nextN(T*, int n)` | 读取 n 个连续的 T 类型值 |
| `nextBool()` | 读取一个布尔值 |
| `nextRange(float*, min, max)` | 浮点值范围读取的特化版本 |
| `signalBug()` | 发送 SIGSEGV 信号通知 fuzzer 发现了 bug |

### `DEF_FUZZ` 宏

```cpp
#define DEF_FUZZ(name, f)
    void fuzz_##name(Fuzz*);
    sk_tools::Registry<Fuzzable> register_##name({#name, fuzz_##name});
    void fuzz_##name(Fuzz* f)
```

声明并注册一个 fuzzer 函数到全局注册表。

## 内部实现细节

### next(T*) 的设计哲学

使用指针参数而非返回值（`T next()` vs `void next(T*)`），原因是不同编译器对函数参数的求值顺序不同：
- GCC: 从左到右
- Clang: 从右到左

使用 `fuzz->next(&a)` 后接 `fuzz->next(&b)` 确保了跨平台的确定性字节消耗顺序。

### nextBytes 的容错处理

当请求的数据超过剩余数据时：
```cpp
void Fuzz::nextBytes(void* n, size_t size) {
    if ((fNextByte + size) > fSize) {
        sk_bzero(n, size);              // 先清零
        memcpy(n, fData + fNextByte, fSize - fNextByte);  // 复制可用部分
        fNextByte = fSize;              // 标记耗尽
        return;
    }
    memcpy(n, fData + fNextByte, size);
    fNextByte += size;
}
```

不足的字节用零填充，确保即使数据不足也不会崩溃。

### bool 值的安全读取

为了避免 UBSAN 警告（bool 只能合法持有 0 或 1），使用 `(n & 1) == 1` 将字节转换为布尔值。

### 浮点范围读取

`nextRange(float*, min, max)` 对非正常浮点值（NaN、Inf）回退为 `max`，然后使用 `fmod` 将值映射到 [min, max] 范围。

### SkRegion 的特化读取

`next(SkRegion*)` 委托给 `FuzzCommon.h` 中的 `FuzzNiceRegion(this, region, 10)`，最多生成 10 个矩形区域操作。

## 依赖关系

- **Skia 基础**: `SkData`、`SkTypes`、`SkMalloc`、`SkTFitsIn`
- **Skia 类型**: `SkRegion`、`SkImageFilter`
- **注册机制**: `tools/Registry.h`（全局 fuzzer 注册表）
- **模糊工具**: `FuzzCommon`（SkRegion 特化依赖）

## 设计模式与设计决策

- **流式读取**: 类似 `SkReadBuffer`，顺序消耗字节数据，读取位置单调递增
- **优雅降级**: 数据不足时零填充而非崩溃，确保 fuzzer 能探索更多路径
- **枚举安全**: `nextEnum` 使用底层整数类型绕过 UBSAN 对枚举值范围的检查
- **全局注册表**: `DEF_FUZZ` 宏通过静态初始化将 fuzzer 注册到全局 `Registry`，支持运行时按名称查找
- **不可复制语义**: 防止意外复制导致的读取位置不一致

## 性能考量

- `nextBytes` 使用 `memcpy` 进行批量数据读取，效率高
- `nextN` 逐个调用 `next`，对于大量小对象可能不如批量 `memcpy` 高效，但确保了类型安全
- `signalBug` 使用 `raise(SIGSEGV)` 直接触发信号，这是 fuzzer 发现 bug 时的标准通知方式
- 数据耗尽检查 (`exhausted()`) 是 O(1) 操作，可在循环中频繁调用

## 相关文件

- `fuzz/FuzzCommon.h` - 基础模糊工具函数
- `fuzz/FuzzCanvasHelpers.h` - Canvas 模糊测试辅助
- `tools/Registry.h` - 全局注册表模板
- `fuzz/oss_fuzz/` - OSS-Fuzz 集成入口
