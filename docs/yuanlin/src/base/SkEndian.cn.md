# SkEndian - 字节序转换工具
> 源文件: `src/base/SkEndian.h`

## 概述
SkEndian 模块提供了处理大端（Big-Endian）和小端（Little-Endian）字节序的完整工具集。它包含了 16 位、32 位和 64 位整数的字节序交换函数，以及编译期常量版本和向量化批处理版本。该模块确保 Skia 在不同字节序的平台上能正确处理二进制数据，是跨平台兼容性的关键组件。

## 架构位置
SkEndian 位于 Skia 基础工具模块（src/base）中，是最底层的平台抽象层之一。它为文件格式解析（PNG、JPEG 等）、网络传输、字体文件读取、以及所有需要处理跨平台二进制数据的模块提供字节序转换服务。

## 主要宏定义与函数

### 平台检测宏
```cpp
SK_CPU_LENDIAN  // 小端架构（x86、ARM）
SK_CPU_BENDIAN  // 大端架构（某些 MIPS、PowerPC）
```

**编译期保证**: 必须定义且只能定义其中之一，否则编译错误。

### 字节序交换函数

#### `uint16_t SkEndianSwap16(uint16_t value)`
- **功能**: 交换 16 位整数的两个字节
- **示例**: `0x1234 -> 0x3412`
- **实现**: `(value >> 8) | ((value & 0xFF) << 8)`
- **特点**: 声明为 `inline`，零运行时开销

#### `uint32_t SkEndianSwap32(uint32_t value)`
- **功能**: 翻转 32 位整数的四个字节
- **示例**: `0x12345678 -> 0x78563412`
- **特点**: 声明为 `constexpr`，可在编译期计算
- **实现**: 位掩码和移位操作组合

#### `uint64_t SkEndianSwap64(uint64_t value)`
- **功能**: 翻转 64 位整数的八个字节
- **示例**: `0x1122334455667788 -> 0x8877665544332211`
- **实现**: 8 个字节的独立移位和组合

### 编译期常量版本

#### `template<uint16_t N> struct SkTEndianSwap16`
- **功能**: 编译期计算 16 位字节序交换
- **用法**: `SkTEndianSwap16<0x1234>::value`
- **优点**: 结果在编译期计算，零运行时成本
- **应用**: 定义字节序相关的常量

类似的还有 `SkTEndianSwap32<N>` 和 `SkTEndianSwap64<N>`。

### 向量化批处理函数

#### `void SkEndianSwap16s(uint16_t array[], int count)`
- **功能**: 批量交换数组中所有 16 位整数的字节序
- **参数**:
  - array: 待处理的数组
  - count: 数组元素数量
- **实现**: 循环调用 SkEndianSwap16
- **断言**: 确保 count == 0 或 array != nullptr

#### `void SkEndianSwap32s(uint32_t array[], int count)`
- **功能**: 批量交换 32 位整数数组
- **参数**: 同上
- **应用场景**: 处理像素数据、颜色表等

#### `void SkEndianSwap64s(uint64_t array[], int count)`
- **功能**: 批量交换 64 位整数数组
- **参数**: 同上
- **应用场景**: 处理时间戳、64 位颜色值等

### 条件交换宏

根据当前平台字节序，这些宏会被定义为实际交换或空操作：

#### 小端平台（SK_CPU_LENDIAN）
```cpp
#define SkEndian_SwapBE16(n)  SkEndianSwap16(n)   // 大端 -> 本地，需要交换
#define SkEndian_SwapLE16(n)  static_cast<uint16_t>(n)  // 小端 -> 本地，无需交换
```

#### 大端平台（SK_CPU_BENDIAN）
```cpp
#define SkEndian_SwapBE16(n)  static_cast<uint16_t>(n)  // 大端 -> 本地，无需交换
#define SkEndian_SwapLE16(n)  SkEndianSwap16(n)   // 小端 -> 本地，需要交换
```

类似的宏还有 32 位和 64 位版本。

### 字节提取移位量宏

用于从 32 位字中提取各个字节：

#### 小端平台
```cpp
#define SkEndian_Byte0Shift 0   // 最低字节在 bit 0
#define SkEndian_Byte1Shift 8
#define SkEndian_Byte2Shift 16
#define SkEndian_Byte3Shift 24  // 最高字节在 bit 24
```

#### 大端平台
```cpp
#define SkEndian_Byte0Shift 24  // 最低字节在 bit 24
#define SkEndian_Byte1Shift 16
#define SkEndian_Byte2Shift 8
#define SkEndian_Byte3Shift 0   // 最高字节在 bit 0
```

**用途**: 通过 `(word >> SkEndian_Byte0Shift) & 0xFF` 提取特定字节

### 位域字节序宏

```cpp
SK_UINT8_BITFIELD_LENDIAN  // 8位位域使用小端
SK_UINT8_BITFIELD_BENDIAN  // 8位位域使用大端
```

**SK_UINT8_BITFIELD 宏**:
- **功能**: 定义 8 个 1 位位域成员，顺序根据字节序自动调整
- **参数**: f0-f7，8 个位域字段名
- **小端**: 按 f0, f1, ..., f7 顺序定义
- **大端**: 按 f7, f6, ..., f0 顺序定义
- **应用**: OpenType/TrueType 字体表结构、网络协议头部

## 内部实现细节

### 位操作优化
现代编译器会将字节序交换识别为特殊模式，生成单条指令：
- **x86**: `bswap` (32/64位), `xchg` 的变体 (16位)
- **ARM**: `rev` (32位), `rev16` (16位), `rev64` (64位)
- **优化级别**: 通常需要 -O2 或更高

### constexpr 的编译期计算
`SkEndianSwap32` 声明为 `constexpr`，允许：
```cpp
constexpr uint32_t magicBE = SkEndianSwap32(0x12345678);
```
编译器在编译期完成计算，生成的代码直接包含结果值。

### 模板元编程技术
`SkTEndianSwap32<N>` 使用模板特化：
```cpp
template<uint32_t N> struct SkTEndianSwap32 {
    static const uint32_t value = /* 字节交换表达式 */;
};
```
利用 C++ 模板在编译期进行值计算。

### 向量化批处理的性能考量
虽然当前实现是简单循环：
```cpp
while (--count >= 0) {
    *array = SkEndianSwap32(*array);
    array += 1;
}
```
但编译器可以将其向量化（SIMD），一次处理多个元素。

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/private/base/SkAssert.h | 参数验证断言 |
| include/private/base/SkFeatures.h | 平台特性检测（SK_CPU_LENDIAN 等） |

### 被依赖的模块
- 图片编解码器（PNG, JPEG, WebP 等）
- 字体文件解析器（TrueType, OpenType）
- 网络传输模块
- 文件序列化系统
- GPU 纹理数据打包
- 颜色格式转换

## 设计模式与设计决策

### 宏与内联函数混合使用
- **宏**: 用于条件编译（SkEndian_SwapBE16 等）
- **内联函数**: 用于类型安全的实际转换
- **模板**: 用于编译期常量计算

这种混合策略兼顾了：
- 类型安全（函数）
- 编译期优化（宏和模板）
- 可读性（有意义的函数名）

### 静态断言保护
使用预处理器 `#error` 确保平台字节序定义正确：
```cpp
#if defined(SK_CPU_LENDIAN) && defined(SK_CPU_BENDIAN)
    #error "can't have both LENDIAN and BENDIAN defined"
#endif
```
在编译最早期捕获配置错误。

### 零成本抽象原则
所有转换函数都是零成本抽象：
- 内联消除函数调用开销
- 编译器识别模式生成单条指令
- 条件宏在编译期决策，无运行时判断

### 向量化友好设计
批处理函数设计为编译器易于向量化的形式：
- 简单的顺序循环
- 无数据依赖
- 固定步长访问

## 性能考量

### 硬件加速
在支持的平台上，字节序交换是单条指令：
- **周期数**: 通常 1 个周期（与加法相同）
- **吞吐量**: 每周期可执行多条（现代 CPU）
- **延迟隐藏**: 可与其他指令并行

### 批处理优化机会
`SkEndianSwap32s` 的循环可被向量化：
- **SSE/AVX**: 一次处理 4/8 个 32 位整数
- **NEON**: 一次处理 4 个 32 位整数
- **自动向量化**: 编译器通常能自动实现

### 大小端统一处理的开销
即使在本地字节序平台，仍需调用转换函数（虽然是空操作）：
- **好处**: 代码统一，不易出错
- **坏处**: 轻微的函数调用和类型转换开销
- **实际影响**: 内联后通常为零

### 适用场景
需要字节序转换的典型场景：
1. **文件格式**: 大多数文件格式（PNG、JPEG）使用大端
2. **网络协议**: 网络字节序为大端
3. **跨平台数据**: 确保不同架构间数据一致性
4. **GPU 纹理**: 某些纹理格式有字节序要求

## 相关文件
| 文件 | 关系 |
|------|------|
| include/private/base/SkFeatures.h | 定义 SK_CPU_LENDIAN/BENDIAN 宏 |
| src/codec/SkPngCodec.cpp | PNG 文件是大端格式 |
| src/codec/SkJpegCodec.cpp | JPEG marker 是大端 |
| src/ports/SkFontHost_*.cpp | 字体文件使用大端 |
| src/core/SkStream.cpp | 流读取中的字节序处理 |
| src/sfnt/SkOTTable_*.h | OpenType 表结构使用位域宏 |
| src/gpu/ganesh/GrSurfaceProxy.cpp | 纹理数据字节序 |
