# SkSFNTHeader

> 源文件: src/sfnt/SkSFNTHeader.h

## 概述

`SkSFNTHeader.h` 定义了 SFNT (Scalable Font N Tables) 格式的文件头结构,这是 TrueType 和 OpenType 字体文件的基础容器格式。该头文件提供了字体文件的最外层结构定义,包括字体类型标识、表目录等核心元数据。SFNT 格式采用表格化组织,将字体数据分散在多个独立的表中,通过目录快速定位。

该文件支持多种字体格式:Windows TrueType (`0x00010000`)、Mac TrueType (`'true'`)、PostScript (`'typ1'`)和OpenType CFF (`'OTTO'`),是 Skia 字体解析的入口点。

## 架构位置

`SkSFNTHeader.h` 位于 Skia 的字体基础设施层:

- **模块路径**: `src/sfnt/`
- **功能**: SFNT 文件头定义
- **规范**: TrueType/OpenType Font File Format
- **依赖**:
  - `SkOTTableTypes.h`: OpenType 类型
  - `SkEndian.h`: 字节序处理
- **被使用者**: 字体加载器、字体文件解析器

## 主要类与结构体

### SkSFNTHeader (SFNT 文件头)

**成员**:
```cpp
SK_SFNT_ULONG fontType;           // 字体类型标识(4字节)
SK_SFNT_USHORT numTables;         // 表的数量
SK_SFNT_USHORT searchRange;       // (最大2次幂 <= numTables) * 16
SK_SFNT_USHORT entrySelector;     // log2(最大2次幂 <= numTables)
SK_SFNT_USHORT rangeShift;        // numTables * 16 - searchRange
```

**大小**: 12字节

### 字体类型标识

#### fontType_WindowsTrueType
标签: `0x00010000`
- 最常见的TrueType字体
- Windows和多数平台使用

#### fontType_MacTrueType
标签: `'true'` (0x74727565)
- Mac传统TrueType格式
- 向后兼容

#### fontType_PostScript
标签: `'typ1'` (0x74797031)
- Type 1 PostScript字体
- 较少见

#### fontType_OpenTypeCFF
标签: `'OTTO'` (0x4F54544F)
- OpenType with CFF轮廓
- PostScript轮廓+OpenType表

### TableDirectoryEntry (表目录项)

描述字体文件中单个表的位置和属性。

**成员**:
```cpp
SK_SFNT_ULONG tag;            // 表标签(如'head','cmap','glyf')
SK_SFNT_ULONG checksum;       // 表校验和
SK_SFNT_ULONG offset;         // 从文件开头的偏移(字节)
SK_SFNT_ULONG logicalLength;  // 表的逻辑长度(字节)
```

**大小**: 16字节

**常见表标签**:
- `'head'`: 字体头表
- `'hhea'`: 水平头表
- `'hmtx'`: 水平度量表
- `'maxp'`: 最大值表
- `'name'`: 名称表
- `'cmap'`: 字符映射表
- `'loca'`: 字形位置表
- `'glyf'`: 字形数据表
- `'post'`: PostScript信息表

## 公共 API 函数

仅包含数据结构定义,无函数实现。

**使用示例**:
```cpp
const SkSFNTHeader* header = (const SkSFNTHeader*)fontData;

// 检查字体类型
uint32_t type = SkEndian_SwapBE32(header->fontType);
if (type == SkSFNTHeader::fontType_WindowsTrueType::TAG ||
    type == SkSFNTHeader::fontType_MacTrueType::TAG) {
    // TrueType字体
}

// 遍历表目录
uint16_t numTables = SkEndian_SwapBE16(header->numTables);
const SkSFNTHeader::TableDirectoryEntry* entries =
    (const SkSFNTHeader::TableDirectoryEntry*)(header + 1);

for (uint16_t i = 0; i < numTables; ++i) {
    uint32_t tag = SkEndian_SwapBE32(entries[i].tag);
    uint32_t offset = SkEndian_SwapBE32(entries[i].offset);
    uint32_t length = SkEndian_SwapBE32(entries[i].logicalLength);
    // 读取表数据
}
```

## 内部实现细节

### 1. 二分查找优化字段

```cpp
searchRange = (最大2次幂 <= numTables) * 16
entrySelector = log2(最大2次幂 <= numTables)
rangeShift = numTables * 16 - searchRange
```

**用途**: 支持对表目录的二分查找:
```cpp
// 伪代码
maxPowerOf2 = 1 << entrySelector;  // 2^entrySelector
searchRange = maxPowerOf2 * 16;    // 搜索范围
```

加速字体表的定位。

### 2. 表校验和计算

```cpp
uint32_t calcChecksum(const uint32_t* table, uint32_t length) {
    uint32_t sum = 0;
    const uint32_t* endPtr = table + ((length + 3) / 4);
    while (table < endPtr) {
        sum += SkEndian_SwapBE32(*table++);
    }
    return sum;
}
```

**特殊处理**: `'head'` 表的校验和字段在计算时设为0。

### 3. 文件布局

```
[SkSFNTHeader 12字节]
[TableDirectoryEntry 16字节] * numTables
[4字节对齐填充]
[表数据1]
[4字节对齐填充]
[表数据2]
...
```

所有表必须4字节对齐。

### 4. 字节序处理

所有多字节字段使用大端序(Big-Endian):
```cpp
typedef uint16_t SK_SFNT_USHORT;  // 需要SkEndian_SwapBE16()
typedef uint32_t SK_SFNT_ULONG;   // 需要SkEndian_SwapBE32()
```

### 5. 静态断言

```cpp
static_assert(sizeof(SkSFNTHeader) == 12, "sizeof_SkSFNTHeader_not_12");
static_assert(sizeof(SkSFNTHeader::TableDirectoryEntry) == 16,
              "sizeof_SkSFNTHeader_TableDirectoryEntry_not_16");
```

确保结构体大小符合规范。

## 依赖关系

### 直接依赖

- `src/base/SkEndian.h`: 字节序转换
- `src/sfnt/SkOTTableTypes.h`: OpenType 类型定义

### 被依赖情况

- `SkTypeface`: 字体接口实现
- `SkFontMgr`: 字体加载
- `SkTTCFHeader.h`: TrueType集合头(引用此结构)
- 所有字体解析代码

## 设计模式与设计决策

### 1. POD 结构体

纯数据结构,可直接内存映射:
- 无构造函数
- 无虚函数
- 与文件格式完全对应

### 2. 嵌套类型定义

字体类型标识定义为嵌套struct:
```cpp
struct fontType_WindowsTrueType {
    static const SK_OT_ULONG TAG = ...;
};
```

提供类型安全的标签常量。

### 3. 紧凑布局

`#pragma pack(1)` 确保无填充:
- 精确对应文件格式
- 支持零拷贝访问

### 4. 表目录分离

表目录项定义为独立结构:
- 可变长度数组
- 便于遍历
- 清晰的职责划分

## 性能考量

### 1. 零拷贝设计

结构体可直接映射到文件:
```cpp
const SkSFNTHeader* header = (const SkSFNTHeader*)mmap(...);
```

无需反序列化。

### 2. 二分查找支持

`searchRange` 和 `entrySelector` 字段:
- 预计算二分查找参数
- O(log n) 表查找
- 典型字体20-30个表

### 3. 缓存友好

12字节头+16字节/表:
- 目录通常在单个缓存行内
- 顺序访问

### 4. 表对齐

4字节对齐要求:
- SIMD友好
- 减少未对齐访问

## 相关文件

### 核心依赖

- `src/sfnt/SkOTTableTypes.h`: 类型定义
- `src/base/SkEndian.h`: 字节序工具

### 相关头文件

- `src/sfnt/SkTTCFHeader.h`: TrueType Collection 头
- `src/sfnt/SkOTTable_head.h`: 'head'表
- `src/sfnt/SkOTTable_maxp.h`: 'maxp'表
- 其他各种表定义文件

### 字体加载

- `src/ports/SkFontHost_*.cpp`: 各平台字体接口
- `src/core/SkTypeface.cpp`: 字体抽象基类

该文件是 Skia 字体系统的基础,通过精确定义 SFNT 文件头结构,使 Skia 能够解析和加载 TrueType 和 OpenType 字体,支持跨平台的文本渲染。
