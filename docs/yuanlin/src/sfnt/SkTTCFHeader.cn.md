# SkTTCFHeader

> 源文件: src/sfnt/SkTTCFHeader.h

## 概述

`SkTTCFHeader.h` 定义了 TrueType Collection (TTC) 文件的头部结构。TTC 格式允许多个字体(通常是同一字族的不同样式,如常规、粗体、斜体)共享同一个文件,通过共享公共表数据(如字形数据)显著减少文件大小。该文件定义了 TTC 文件的外层容器结构,包括版本信息、字体偏移数组和可选的数字签名信息。

TTC 格式广泛应用于包含多个字重或样式的字体家族,通过表共享机制,可将文件大小减少30-50%。Skia 通过该结构解析 TTC 文件并定位到具体的字体实例。

## 架构位置

`SkTTCFHeader.h` 位于 Skia 的字体容器定义层:

- **模块路径**: `src/sfnt/`
- **功能**: TrueType Collection 头定义
- **规范**: TrueType/OpenType Font File Format
- **依赖**:
  - `SkOTTableTypes.h`: OpenType 类型
  - `SkSFNTHeader.h`: SFNT 头(单个字体)
- **被使用者**: 字体加载器、字体管理器

## 主要类与结构体

### SkTTCFHeader (TTC 文件头)

**表标签**: `'ttcf'` (0x74746366)

**成员**:
```cpp
SK_SFNT_ULONG ttcTag;       // 必须为'ttcf'
SK_OT_Fixed version;        // 版本号(1.0或2.0)
SK_OT_ULONG numOffsets;     // 字体数量
// SK_OT_ULONG offset[numOffsets];  // 每个字体的偏移数组(紧随其后)
```

**大小**: 12字节(不含偏移数组)

**版本**:
```cpp
static const SK_OT_Fixed version_1 = 0x00010000;  // 版本1.0
static const SK_OT_Fixed version_2 = 0x00020000;  // 版本2.0(支持数字签名)
```

### Version2Ext (版本2扩展)

仅当 `version == version_2` 时存在,位于偏移数组之后。

**成员**:
```cpp
SK_OT_ULONG dsigType;        // 数字签名类型
SK_OT_ULONG dsigLength;      // DSIG表长度(字节)
SK_OT_ULONG dsigOffset;      // DSIG表偏移(从文件开头)
```

**数字签名类型**:

#### dsigType_None
标签: `0x00000000`
- 无数字签名

#### dsigType_Format1
标签: `'DSIG'` (0x44534947)
- Format 1 数字签名
- 用于字体真实性验证

## 公共 API 函数

仅包含数据结构定义,无函数实现。

**使用示例**:
```cpp
// 读取TTC文件头
const SkTTCFHeader* ttcHeader = (const SkTTCFHeader*)fileData;

// 验证标签
uint32_t tag = SkEndian_SwapBE32(ttcHeader->ttcTag);
if (tag != SkTTCFHeader::TAG) {
    // 不是TTC文件
    return false;
}

// 获取版本和字体数量
uint32_t version = SkEndian_SwapBE32(ttcHeader->version);
uint32_t numFonts = SkEndian_SwapBE32(ttcHeader->numOffsets);

// 读取偏移数组
const uint32_t* offsets = (const uint32_t*)(ttcHeader + 1);
for (uint32_t i = 0; i < numFonts; ++i) {
    uint32_t offset = SkEndian_SwapBE32(offsets[i]);
    // offset 指向单个字体的SkSFNTHeader
    const SkSFNTHeader* fontHeader =
        (const SkSFNTHeader*)((const uint8_t*)fileData + offset);
    // 解析单个字体
}

// 版本2:读取数字签名信息(如果存在)
if (version == SkTTCFHeader::version_2) {
    const SkTTCFHeader::Version2Ext* ext =
        (const SkTTCFHeader::Version2Ext*)&offsets[numFonts];
    uint32_t dsigType = SkEndian_SwapBE32(ext->dsigType);
    if (dsigType == SkTTCFHeader::Version2Ext::dsigType_Format1::TAG) {
        // 验证数字签名
    }
}
```

## 内部实现细节

### 1. 文件布局

```
[SkTTCFHeader 12字节]
[uint32_t offset[numOffsets]]  // 每个字体的偏移
[Version2Ext 12字节]            // 仅版本2.0
[字体1的SkSFNTHeader+表...]
[字体2的SkSFNTHeader+表...]
...
[DSIG表(如果存在)]
```

### 2. 表共享机制

多个字体可共享同一个表:
```
字体1 (Regular):
  - 'head', 'hhea', 'name'[自有]
  - 'glyf', 'loca'[共享]

字体2 (Bold):
  - 'head', 'hhea', 'name'[自有]
  - 'glyf', 'loca'[共享]  // 指向相同数据
```

**共享表的好处**:
- 字形数据通常占字体文件的80%以上
- 多字重可共享基本字形
- CJK字体尤其受益(数万字形)

### 3. 偏移数组

偏移数组紧随头部:
```cpp
const uint32_t* offsets = (const uint32_t*)(ttcHeader + 1);
uint32_t fontOffset = SkEndian_SwapBE32(offsets[fontIndex]);
```

每个偏移指向一个完整的 `SkSFNTHeader`,该字体的表目录从该位置开始。

### 4. 版本兼容性

```cpp
uint32_t version = SkEndian_SwapBE32(ttcHeader->version);
if (version == SkTTCFHeader::version_1) {
    // 无数字签名扩展
} else if (version == SkTTCFHeader::version_2) {
    // 可能有数字签名
    const Version2Ext* ext = ...;
}
```

解析器必须处理两种版本。

### 5. 字节序

所有多字节字段使用大端序:
```cpp
ttcTag = SkEndian_SwapBE32(ttcTag);
version = SkEndian_SwapBE32(version);
numOffsets = SkEndian_SwapBE32(numOffsets);
```

### 6. 静态断言

```cpp
static_assert(sizeof(SkTTCFHeader) == 12, "sizeof_SkTTCFHeader_not_12");
```

确保结构体大小正确。

## 依赖关系

### 直接依赖

- `src/sfnt/SkOTTableTypes.h`: OpenType 类型定义
- `src/sfnt/SkSFNTHeader.h`: 单个字体头结构
- `src/base/SkEndian.h`: 字节序转换

### 被依赖情况

- `SkTypeface`: 字体接口
- `SkFontMgr`: 字体加载和枚举
- 各平台的字体实现(`SkTypeface_*`)

## 设计模式与设计决策

### 1. 容器模式

TTC 作为多个字体的容器:
- 统一的外层格式
- 每个字体保持独立的SFNT结构
- 透明的表共享

### 2. 版本扩展

通过版本号支持向后兼容的扩展:
- 版本1: 基础TTC功能
- 版本2: 添加数字签名
- 未来版本可继续扩展

### 3. POD 结构

纯数据结构,支持零拷贝:
- 可直接内存映射
- 无运行时开销
- 与文件格式完全对应

### 4. 嵌套类型定义

标签和版本常量定义为嵌套类型:
```cpp
struct dsigType_Format1 {
    static const SK_OT_ULONG TAG = ...;
};
```

类型安全且命名空间清晰。

## 性能考量

### 1. 文件大小优化

**典型节省**:
- 无TTC: 5MB + 6MB + 5MB = 16MB (Regular + Bold + Italic)
- TTC: 10MB (共享字形数据)
- 节省率: 37.5%

**CJK字体更显著**:
- 无TTC: 50MB * 3 = 150MB
- TTC: 70MB
- 节省率: 53%

### 2. 加载性能

**优势**:
- 单次打开文件
- 共享表无需重复读取
- 内存映射时共享物理页

**劣势**:
- 需要索引字体
- 额外的间接层

### 3. 缓存友好

12字节头部:
- 单个缓存行
- 偏移数组顺序访问

### 4. 零拷贝

结构体可直接映射:
```cpp
const SkTTCFHeader* header = (const SkTTCFHeader*)mmap(...);
```

无需反序列化。

## 相关文件

### 核心依赖

- `src/sfnt/SkOTTableTypes.h`: 类型定义
- `src/sfnt/SkSFNTHeader.h`: 单字体头
- `src/base/SkEndian.h`: 字节序工具

### 相关表定义

- 所有 `SkOTTable_*.h` 文件(可共享的表)

### 字体加载

- `src/ports/SkFontHost_*.cpp`: 平台字体接口
- `src/core/SkTypeface.cpp`: 字体基类

### 测试

- `tests/FontHostTest.cpp`: 字体加载测试

该文件是 Skia 支持 TrueType Collection 的基础,通过定义 TTC 容器格式,使 Skia 能够高效加载和管理包含多个字体的集合文件,在减少磁盘空间和内存占用的同时,保持字体访问的性能。
