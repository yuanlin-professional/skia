# SkOTTableOS2_V0

> 源文件: src/sfnt/SkOTTable_OS_2_V0.h

## 概述

`SkOTTable_OS_2_V0.h` 定义了 OpenType 字体 OS/2 表的版本 0 结构。这是最早的 OS/2 表版本,包含字体的基本度量信息、字重、字宽、字符范围等元数据。版本 0 比后续版本更简单,缺少代码页范围等高级特性。需要注意的是,版本 0 和版本 VA(Apple 版本)的版本号都是 0,只能通过表大小区分(V0 为 78 字节,VA 为 68 字节)。

## 架构位置

```
Skia 字体系统
└── src/sfnt/
    ├── SkOTTable_OS_2.h (统一接口)
    ├── SkOTTable_OS_2_VA.h (Apple 版本)
    ├── SkOTTable_OS_2_V0.h (版本 0) ←
    ├── SkOTTable_OS_2_V1.h (版本 1)
    └── ...
```

## 主要类与结构体

### SkOTTableOS2_V0 (主结构)

```cpp
struct SkOTTableOS2_V0 {
    SK_OT_USHORT version;  // 版本号 = 0
    static const SK_OT_USHORT VERSION = SkTEndian_SwapBE16(0);

    SK_OT_SHORT xAvgCharWidth;     // 平均字符宽度
    WeightClass usWeightClass;     // 字重
    WidthClass usWidthClass;       // 字宽
    Type fsType;                   // 字体类型
    // 上标/下标度量
    // 家族分类
    // PANOSE
    SK_OT_ULONG ulCharRange[4];    // 字符范围 (128位)
    SK_OT_CHAR achVendID[4];       // 厂商 ID
    Selection fsSelection;         // 选择标志
    SK_OT_USHORT usFirstCharIndex; // 首字符索引
    SK_OT_USHORT usLastCharIndex;  // 末字符索引
    // 版本0特有字段
    SK_OT_SHORT sTypoAscender;     // 上升高度
    SK_OT_SHORT sTypoDescender;    // 下降高度
    SK_OT_SHORT sTypoLineGap;      // 行间距
    SK_OT_USHORT usWinAscent;      // Windows 上升
    SK_OT_USHORT usWinDescent;     // Windows 下降
};
```

**大小**: 78 字节

### WeightClass / WidthClass / Type / Selection

这些子结构与 V1 版本相同,提供字重、字宽、类型和样式标志。

### ulCharRange vs UnicodeRange

**注意**: V0 使用 `ulCharRange[4]` 而非命名联合体 `UnicodeRange`,但语义相同:
- 128 位标志位
- 标识支持的 Unicode 字符范围
- 与后续版本的 `ulUnicodeRange` 对应

## 公共 API 函数

```cpp
// 读取 OS/2 V0 表
const SkOTTableOS2_V0* os2 = ...;

// 获取字重
uint16_t weight = SkEndian_SwapBE16(os2->usWeightClass.value);

// 检查字符范围 (原始位操作)
bool supportsCJK = os2->ulCharRange[1] &
    SkEndian_SwapBE32(1u << (59 - 32)); // Bit 59: CJK Unified Ideographs

// 获取度量
int16_t ascender = SkEndian_SwapBE16(os2->sTypoAscender);
```

## 内部实现细节

### 与 VA 版本的区分

```cpp
// SkOTTableOS2_VA::VERSION 和 SkOTTableOS2_V0::VERSION 都是 0
// 唯一区分方式: 表大小
// VA: 68 字节, V0: 78 字节
```

**识别逻辑**:
```cpp
if (version == 0) {
    if (tableSize == 68) {
        // 使用 SkOTTableOS2_VA
    } else if (tableSize == 78) {
        // 使用 SkOTTableOS2_V0
    }
}
```

### 内存布局

```cpp
#pragma pack(push, 1)
static_assert(sizeof(SkOTTableOS2_V0) == 78,
    "sizeof_SkOTTableOS2_V0_not_78");
```

### 与 V1 的差异

V0 **缺少**的字段:
- `ulCodePageRange`: 代码页范围支持(V1 新增)

V0 **包含**的字段:
- 其他核心字段与 V1 基本相同

## 依赖关系

```
SkOTTable_OS_2_V0.h
├── src/base/SkEndian.h
├── src/sfnt/SkIBMFamilyClass.h
├── src/sfnt/SkOTTableTypes.h
└── src/sfnt/SkPanose.h
```

## 设计模式与设计决策

### 1. 版本号歧义处理

**问题**: V0 和 VA 版本号都是 0
**解决**: 通过表大小区分

### 2. 字符范围表示

V0 使用简单数组 `ulCharRange[4]`,后续版本改为命名联合体 `UnicodeRange`,提供更好的类型安全和可读性。

### 3. 向上兼容

V0 包含的字段在后续版本中保持不变,确保向上兼容性。

## 性能考量

### 直接内存映射

78 字节的紧凑结构,易于:
- 整表缓存
- 快速访问
- 减少内存占用

### 位操作

字符范围检查需要手动位操作,不如后续版本的命名常量方便,但性能相同。

## 相关文件

| 文件路径 | 说明 | 关系 |
|---------|------|------|
| `src/sfnt/SkOTTable_OS_2.h` | OS/2 表统一接口 | 包含此版本 |
| `src/sfnt/SkOTTable_OS_2_VA.h` | Apple 版本 | 同版本号,不同大小 |
| `src/sfnt/SkOTTable_OS_2_V1.h` | 版本 1 | 后续版本 |
| `src/sfnt/SkPanose.h` | PANOSE 分类 | 字段依赖 |
| `src/sfnt/SkIBMFamilyClass.h` | IBM 分类 | 字段依赖 |

OS/2 表版本 0 是历史较早的版本,主要见于旧版字体文件,现代字体通常使用 V2 或更高版本。
