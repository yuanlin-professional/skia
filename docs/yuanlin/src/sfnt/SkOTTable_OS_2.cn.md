# SkOTTableOS2

> 源文件: src/sfnt/SkOTTable_OS_2.h

## 概述

`SkOTTable_OS_2.h` 是 OpenType 字体 OS/2 表的统一接口文件,通过联合体(union)整合了 OS/2 表的所有版本(VA, V0, V1, V2, V3, V4)。该文件不直接定义表结构,而是提供了一个版本多态的访问接口,允许代码根据实际版本号访问相应的表结构,实现了优雅的版本管理机制。

## 架构位置

```
Skia 字体系统
└── src/sfnt/
    ├── SkOTTable_OS_2.h (统一接口) ←
    ├── SkOTTable_OS_2_VA.h (Apple 版本, 68 字节)
    ├── SkOTTable_OS_2_V0.h (版本 0, 78 字节)
    ├── SkOTTable_OS_2_V1.h (版本 1, 86 字节)
    ├── SkOTTable_OS_2_V2.h (版本 2, 96 字节)
    ├── SkOTTable_OS_2_V3.h (版本 3, 96 字节)
    └── SkOTTable_OS_2_V4.h (版本 4, 96 字节)
```

**定位**: 版本抽象层,提供统一的访问接口

## 主要类与结构体

### SkOTTableOS2 (主结构)

```cpp
struct SkOTTableOS2 {
    inline static constexpr SK_OT_CHAR TAG0 = 'O';
    inline static constexpr SK_OT_CHAR TAG1 = 'S';
    inline static constexpr SK_OT_CHAR TAG2 = '/';
    inline static constexpr SK_OT_CHAR TAG3 = '2';
    inline static constexpr SK_OT_ULONG TAG =
        SkOTTableTAG<SkOTTableOS2>::value;

    union Version {
        SK_OT_USHORT version;  // 版本号字段

        // 所有版本的命名访问
        struct VA : SkOTTableOS2_VA { } vA;  // Apple 版本
        struct V0 : SkOTTableOS2_V0 { } v0;  // 版本 0
        struct V1 : SkOTTableOS2_V1 { } v1;  // 版本 1
        struct V2 : SkOTTableOS2_V2 { } v2;  // 版本 2
        struct V3 : SkOTTableOS2_V3 { } v3;  // 版本 3
        struct V4 : SkOTTableOS2_V4 { } v4;  // 版本 4
    } version;
};
```

**设计要点**:
- 标签: `"OS/2"` (注意斜杠)
- 联合体包含所有版本
- 共享起始的 `version` 字段

### 版本大小断言

```cpp
static_assert(sizeof(SkOTTableOS2::Version::VA) == 68,
    "sizeof_SkOTTableOS2__VA_not_68");
static_assert(sizeof(SkOTTableOS2::Version::V0) == 78,
    "sizeof_SkOTTableOS2__V0_not_78");
static_assert(sizeof(SkOTTableOS2::Version::V1) == 86,
    "sizeof_SkOTTableOS2__V1_not_86");
static_assert(sizeof(SkOTTableOS2::Version::V2) == 96,
    "sizeof_SkOTTableOS2__V2_not_96");
static_assert(sizeof(SkOTTableOS2::Version::V3) == 96,
    "sizeof_SkOTTableOS2__V3_not_96");
static_assert(sizeof(SkOTTableOS2::Version::V4) == 96,
    "sizeof_SkOTTableOS2__V4_not_96");
```

**作用**: 编译时验证各版本结构体大小的正确性

## 版本演进

| 版本 | 大小 | 主要特性 |
|------|------|----------|
| VA | 68 字节 | Apple 原始 TrueType 版本 |
| V0 | 78 字节 | 标准 TrueType 版本,增加度量字段 |
| V1 | 86 字节 | 添加代码页范围 (ulCodePageRange) |
| V2 | 96 字节 | 添加 x高度和大写字母高度 |
| V3 | 96 字节 | fsType 位 0-3 互斥 |
| V4 | 96 字节 | 定义 fsSelection 位 7-9 |

## 公共 API 函数

### 典型使用模式

```cpp
// 1. 读取 OS/2 表
const SkOTTableOS2* os2 =
    typeface->getTableData<SkOTTableOS2>(SkOTTableOS2::TAG);

// 2. 读取版本号
uint16_t ver = SkEndian_SwapBE16(os2->version.version);

// 3. 根据版本访问字段
switch (ver) {
    case 0: {
        // 需要根据大小区分 VA 和 V0
        if (tableSize == 68) {
            const auto& vA = os2->version.vA;
            // 访问 VA 版本字段
        } else {
            const auto& v0 = os2->version.v0;
            // 访问 V0 版本字段
        }
        break;
    }
    case 1: {
        const auto& v1 = os2->version.v1;
        uint16_t weight = SkEndian_SwapBE16(v1.usWeightClass.value);
        break;
    }
    case 2:
    case 3:
    case 4: {
        const auto& v4 = os2->version.v4;
        // V2/V3/V4 大小相同,可访问共同字段
        break;
    }
}

// 4. 访问所有版本共有的字段
// 假设知道至少是 V1
const auto& v1 = os2->version.v1;
uint16_t weight = SkEndian_SwapBE16(v1.usWeightClass.value);
```

## 内部实现细节

### 联合体内存布局

```cpp
union Version {
    SK_OT_USHORT version;  // 占2字节,起始位置
    struct VA { ... } vA;  // 占68字节,从起始位置开始
    struct V0 { ... } v0;  // 占78字节,从起始位置开始
    struct V1 { ... } v1;  // 占86字节,从起始位置开始
    struct V2 { ... } v2;  // 占96字节,从起始位置开始
    struct V3 { ... } v3;  // 占96字节,从起始位置开始
    struct V4 { ... } v4;  // 占96字节,从起始位置开始
};
```

**关键特性**:
- 所有版本共享同一内存
- 联合体大小 = 最大成员大小 = 96 字节
- 前 2 字节始终是版本号

### 版本号歧义处理

**问题**: VA 和 V0 的版本号都是 0

**解决方案**:
```cpp
if (version == 0) {
    size_t tableSize = getTableSize();
    if (tableSize == 68) {
        // 使用 vA
    } else if (tableSize >= 78) {
        // 使用 v0
    }
}
```

### constexpr 标签定义

使用 `inline static constexpr` (C++17):
- 编译时常量
- 无需外部定义
- 内联到使用处

## 依赖关系

```
SkOTTable_OS_2.h
├── src/sfnt/SkOTTable_OS_2_V0.h
├── src/sfnt/SkOTTable_OS_2_V1.h
├── src/sfnt/SkOTTable_OS_2_V2.h
├── src/sfnt/SkOTTable_OS_2_V3.h
├── src/sfnt/SkOTTable_OS_2_V4.h
└── src/sfnt/SkOTTable_OS_2_VA.h
```

**被依赖方**:
- 字体加载器
- 字体匹配算法
- 字体度量计算
- 字符集检测

## 设计模式与设计决策

### 1. 联合体多态

**优势**:
- 单一指针访问所有版本
- 类型安全的版本切换
- 避免类型转换错误

**权衡**:
- 需要显式版本检查
- 内存大小为最大版本

### 2. 版本透明访问

通过联合体,代码可以:
```cpp
const SkOTTableOS2* os2 = ...;
// 直接访问,无需 reinterpret_cast
const auto& v4 = os2->version.v4;
```

### 3. 编译时验证

`static_assert` 确保:
- 结构体大小正确
- 防止意外的内存布局变化
- 早期发现定义错误

### 4. TAG 定义方式

使用 `constexpr` 而非宏:
- 类型安全
- 命名空间隔离
- 支持模板参数

## 性能考量

### 零开销抽象

联合体访问是零开销的:
```cpp
// 编译为直接内存访问,无额外指令
uint16_t weight = os2->version.v1.usWeightClass.value;
```

### 版本检查开销

版本分支通常可被编译器优化:
```cpp
// 如果版本在编译时已知,分支被消除
if constexpr (KnownVersion == 4) {
    const auto& v4 = os2->version.v4;
}
```

### 内存占用

联合体大小为 96 字节(最大成员):
- 现代系统可忽略的开销
- 简化内存管理
- 避免动态分配

## 相关文件

| 文件路径 | 说明 | 关系 |
|---------|------|------|
| `src/sfnt/SkOTTable_OS_2_*.h` | 各版本定义 | 被包含的版本 |
| `src/ports/SkTypeface_*.cpp` | 字体接口实现 | 使用此接口读取表 |
| `src/core/SkFontMgr_*.cpp` | 字体管理器 | 使用 OS/2 数据匹配字体 |
| `src/core/SkFontDescriptor.cpp` | 字体描述符 | 提取字重、字宽等信息 |
| `src/sfnt/SkOTUtils.cpp` | OpenType 工具 | 使用 OS/2 表数据 |

该文件通过联合体设计优雅地解决了 OS/2 表多版本管理的问题,为 Skia 字体系统提供了统一而类型安全的访问接口。
