# SkOTTableTypes

> 源文件: src/sfnt/SkOTTableTypes.h

## 概述

`SkOTTableTypes.h` 定义了 OpenType 字体表格处理所需的基础类型系统。该文件提供了一组类型定义和工具模板,用于处理 OpenType 字体格式中的大端序数据类型。所有以 `SK_OT_` 为前缀的类型都应被视为大端序(big endian)格式。

OpenType 字体格式使用大端序字节顺序,而不同平台可能使用不同的本地字节序。此文件通过类型定义和模板工具屏蔽了这种差异,为 Skia 的字体处理提供了统一的接口。

## 架构位置

该文件位于 Skia 字体处理架构的基础层:

- **模块**: `src/sfnt/` - OpenType/TrueType 字体格式支持
- **层次**: 基础类型定义层
- **依赖方**: 所有 SFNT 相关的表格定义文件
- **作用**: 为字体表格解析提供类型安全的数据结构

在 Skia 的字体系统中,该文件是处理字体二进制数据的基石,被所有 OpenType 表格相关的代码所依赖。

## 主要类与结构体

### 基础类型定义

```cpp
typedef uint8_t SK_OT_BYTE;         // 8位无符号整数
typedef int8_t SK_OT_CHAR;          // 8位有符号字符
typedef uint16_t SK_OT_SHORT;       // 16位有符号短整数
typedef uint16_t SK_OT_USHORT;      // 16位无符号短整数
typedef uint32_t SK_OT_ULONG;       // 32位无符号长整数
typedef uint32_t SK_OT_LONG;        // 32位有符号长整数
typedef int32_t SK_OT_Fixed;        // 16.16定点数
typedef uint16_t SK_OT_F2DOT14;     // 2.14定点数
typedef uint16_t SK_OT_FWORD;       // 字体单位(Font units)
typedef uint16_t SK_OT_UFWORD;      // 无符号字体单位
typedef uint64_t SK_OT_LONGDATETIME; // 时间戳(从1904年1月1日起的秒数)
```

### SkOTTableTAG 模板类

用于生成 OpenType 表格标签的大端序值:

```cpp
template<typename T> class SkOTTableTAG {
public:
    static const SK_OT_ULONG value = SkTEndian_SwapBE32(
        SkSetFourByteTag(T::TAG0, T::TAG1, T::TAG2, T::TAG3)
    );
};
```

**功能**:
- 将四个字符标签转换为大端序的32位整数
- 可直接与原始大端序表格数据比较
- 编译时计算,零运行时开销

### SkOTSetUSHORTBit 模板

生成特定位被置位的 `SK_OT_USHORT` 值:

```cpp
template <unsigned N> struct SkOTSetUSHORTBit {
    static_assert(N < 16, "NTooBig");
    static const uint16_t bit = 1u << N;
    static const SK_OT_USHORT value = SkTEndian_SwapBE16(bit);
};
```

**用途**: 用于创建位掩码,支持按位操作

### SkOTSetULONGBit 模板

生成特定位被置位的 `SK_OT_ULONG` 值:

```cpp
template <unsigned N> struct SkOTSetULONGBit {
    static_assert(N < 32, "NTooBig");
    static const uint32_t bit = 1u << N;
    static const SK_OT_ULONG value = SkTEndian_SwapBE32(bit);
};
```

**用途**: 用于32位标志位的设置和检查

## 公共 API 函数

该文件主要提供类型定义和编译时常量,没有运行时函数。所有功能通过类型系统和模板元编程实现:

1. **类型转换**: 通过 typedef 提供语义化的类型名称
2. **字节序转换**: 通过 `SkTEndian_SwapBE*` 函数处理大小端转换
3. **位操作**: 通过模板生成大端序位掩码

## 内部实现细节

### 字符类型处理

```cpp
#if CHAR_BIT == 8
typedef signed char SK_OT_CHAR; // 便于调试
#else
typedef int8_t SK_OT_CHAR;
#endif
```

**设计考虑**:
- 在标准8位字符系统上使用 `signed char` 以便于调试器显示
- 在非标准系统上回退到 `int8_t` 保证可移植性

### 定点数类型

- **SK_OT_Fixed**: 16.16 格式,16位整数部分和16位小数部分
- **SK_OT_F2DOT14**: 2.14 格式,2位整数部分和14位小数部分,用于表示小范围高精度值

### 时间戳格式

`SK_OT_LONGDATETIME` 使用 OpenType 规范定义的时间格式:
- 基准时间: 1904年1月1日午夜12:00
- 单位: 秒
- 类型: 64位无符号整数

### 位字段宏

`SK_OT_BYTE_BITFIELD` 宏用于定义字节级位字段,支持跨平台的位字段布局。

## 依赖关系

### 直接依赖

```
SkOTTableTypes.h
├── include/core/SkFourByteTag.h  (四字节标签工具)
├── include/core/SkTypes.h        (Skia基础类型)
└── src/base/SkEndian.h           (字节序转换工具)
```

### 被依赖方

几乎所有 `src/sfnt/` 目录下的文件都依赖此头文件:
- `SkOTTable_*.h` - 各种字体表格定义
- `SkOTUtils.h` - 字体工具函数
- 字体解析和字形处理代码

## 设计模式与设计决策

### 1. 类型安全的大端序处理

**问题**: OpenType 格式使用大端序,但需要在不同字节序的平台上工作

**解决方案**:
- 定义专用的 `SK_OT_*` 类型表示大端序数据
- 通过类型系统强制区分本地序和大端序
- 避免隐式转换导致的字节序错误

### 2. 编译时计算

**优势**:
- `SkOTTableTAG` 和 `SkOTSetUSHORTBit`/`SkOTSetULONGBit` 都在编译时计算
- 零运行时开销
- 生成的常量可直接用于内存比较

### 3. 模板元编程

通过模板实现:
- 类型安全的位操作
- 编译时验证(如 `static_assert(N < 16)`)
- 代码复用

### 4. 语义化类型命名

使用描述性名称提高代码可读性:
- `SK_OT_FWORD`: 字体单位,而非简单的 `uint16_t`
- `SK_OT_Fixed`: 定点数,而非 `int32_t`
- `SK_OT_LONGDATETIME`: 时间戳,而非 `uint64_t`

## 性能考量

### 编译时优化

1. **零运行时成本**: 所有类型转换和常量生成在编译时完成
2. **内联展开**: typedef 不产生额外的函数调用
3. **常量传播**: 编译器可以优化涉及这些类型的表达式

### 内存布局

```cpp
#pragma pack(push, 1)
```

虽然此文件本身没有使用 pragma pack,但它定义的类型被用于紧凑内存布局的结构体中,确保:
- 与 OpenType 二进制格式精确对应
- 无填充字节
- 可直接映射到文件数据

### 字节序转换开销

字节序转换函数(如 `SkTEndian_SwapBE16`)通常被编译为单条 CPU 指令(如 x86 的 `bswap`),开销极小。

## 相关文件

| 文件路径 | 说明 | 关系 |
|---------|------|------|
| `src/base/SkEndian.h` | 字节序转换工具 | 提供大小端转换函数 |
| `include/core/SkFourByteTag.h` | 四字节标签 | 提供 `SkSetFourByteTag` 宏 |
| `src/sfnt/SkOTTable_head.h` | head 表定义 | 使用本文件定义的类型 |
| `src/sfnt/SkOTTable_name.h` | name 表定义 | 使用本文件定义的类型 |
| `src/sfnt/SkOTTable_OS_2.h` | OS/2 表定义 | 使用本文件定义的类型 |
| `src/sfnt/SkPanose.h` | PANOSE 分类 | 使用本文件定义的类型 |
| `src/sfnt/SkIBMFamilyClass.h` | IBM 字体分类 | 使用本文件定义的类型 |
| `src/sfnt/SkOTUtils.h` | OpenType 工具函数 | 使用本文件定义的类型 |

该文件是 Skia SFNT 模块的基础设施,为整个字体处理子系统提供了类型安全和平台无关的数据类型支持。
