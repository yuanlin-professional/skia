# SkOTTable_fvar

> 源文件: src/sfnt/SkOTTable_fvar.h

## 概述

`SkOTTable_fvar.h` 定义了 OpenType 字体的 `fvar` (Font Variations) 表的内存布局结构。该表是可变字体(Variable Fonts)的核心组件,存储了字体的变化轴(variation axes)和预定义实例(named instances)信息。可变字体允许单个字体文件包含多个字重、宽度等样式变化,通过插值生成任意中间样式,显著减少字体文件数量和总体积。

该头文件使用紧凑的结构体定义,精确映射 OpenType 规范中的 `fvar` 表格式,支持 Skia 解析和访问可变字体的元数据。

## 架构位置

`SkOTTable_fvar.h` 位于 Skia 的字体表定义层:

- **模块路径**: `src/sfnt/`
- **功能**: OpenType 表结构定义
- **规范**: OpenType Font Variations (OpenType 1.8+)
- **依赖**:
  - `SkOTTableTypes.h`: OpenType 类型定义
  - `SkEndian.h`: 字节序处理
- **被使用者**:
  - `SkTypeface`: 字体接口
  - `SkFontMgr`: 字体管理器
  - 字体解析器

## 主要类与结构体

### SkOTTableFontVariations (fvar 表头)

**表标签**: `'fvar'`

**成员**:
```cpp
SK_OT_USHORT majorVersion;        // 主版本号(通常为1)
SK_OT_USHORT minorVersion;        // 次版本号(通常为0)
SK_OT_USHORT offsetToAxesArray;   // 变化轴数组偏移
SK_OT_USHORT reserved;            // 保留字段(必须为0)
SK_OT_USHORT axisCount;           // 变化轴数量
SK_OT_USHORT axisSize;            // 每个轴记录的大小(v1.0中为0x0014,即20字节)
SK_OT_USHORT instanceCount;       // 预定义实例数量
SK_OT_USHORT instanceSize;        // 每个实例记录的大小
                                  // = axisCount * sizeof(Fixed) + (4 | 6)
```

**大小**: 16字节

### VariationAxisRecord (变化轴记录)

描述单个变化轴的属性。

**成员**:
```cpp
SK_OT_ULONG axisTag;        // 轴标签(如'wght'=字重,'wdth'=宽度)
SK_OT_Fixed minValue;       // 最小值(16.16定点数)
SK_OT_Fixed defaultValue;   // 默认值
SK_OT_Fixed maxValue;       // 最大值
SK_OT_USHORT flags;         // 标志(v1.0中必须为0)
SK_OT_USHORT axisNameID;    // 名称表ID,指向轴的描述名称
```

**常见轴标签**:
- `'wght'`: Weight (字重), 范围如100-900
- `'wdth'`: Width (宽度), 范围如50-200
- `'slnt'`: Slant (倾斜), 范围如-15到0
- `'ital'`: Italic (斜体), 0或1
- `'opsz'`: Optical Size (光学尺寸)

### InstanceRecord<AxisCount> (实例记录模板)

描述预定义的命名实例(如"Bold", "Light"等)。

**成员**:
```cpp
SK_OT_USHORT subfamilyNameID;           // 子族名称ID(如"Bold")
SK_OT_USHORT flags;                     // 标志(必须为0)
SK_OT_Fixed coordinates[AxisCount];     // 每个轴的坐标值
SK_OT_USHORT postScriptNameID;          // PostScript名称ID(可选)
```

**模板参数**: `AxisCount` 必须与表头中的 `axisCount` 匹配

**记录大小**: `4 + AxisCount * 4 + (0 | 2)` 字节
- 不含postScriptNameID: 4字节
- 含postScriptNameID: 6字节

## 公共 API 函数

该文件仅包含数据结构定义,无函数实现。

**访问方式**:
```cpp
const SkOTTableFontVariations* fvar = /* 从字体文件读取 */;
const VariationAxisRecord* axes =
    (const VariationAxisRecord*)((const uint8_t*)fvar + SkEndian_SwapBE16(fvar->offsetToAxesArray));

for (int i = 0; i < SkEndian_SwapBE16(fvar->axisCount); ++i) {
    uint32_t tag = SkEndian_SwapBE32(axes[i].axisTag);
    float minVal = SkFixedToFloat(SkEndian_SwapBE32(axes[i].minValue));
    float defVal = SkFixedToFloat(SkEndian_SwapBE32(axes[i].defaultValue));
    float maxVal = SkFixedToFloat(SkEndian_SwapBE32(axes[i].maxValue));
    // 处理变化轴
}
```

## 内部实现细节

### 1. 内存布局

使用 `#pragma pack(push, 1)` 确保紧凑布局,无填充字节:
```cpp
#pragma pack(push, 1)
struct SkOTTableFontVariations {
    // 16字节表头
    // 紧接着是变化轴数组和实例数组(通过偏移访问)
};
#pragma pack(pop)
```

### 2. 大端字节序

所有多字节字段使用大端序(Big-Endian),需要字节序转换:
```cpp
uint16_t axisCount = SkEndian_SwapBE16(fvar->axisCount);
uint32_t axisTag = SkEndian_SwapBE32(axis->axisTag);
```

### 3. 静态断言验证

```cpp
static_assert(offsetof(SkOTTableFontVariations, instanceSize) == 14,
              "SkOTTableFontVariations_instanceSize_not_at_14");
static_assert(sizeof(SkOTTableFontVariations) == 16,
              "sizeof_SkOTTableFontVariations_not_16");
```

确保结构体大小和字段偏移符合 OpenType 规范。

### 4. 可变长度数据

表头后紧跟可变长度数组:
```
[表头 16字节]
[变化轴数组 axisCount * 20字节]
[实例数组 instanceCount * instanceSize字节]
```

通过 `offsetToAxesArray` 定位数组起始位置。

### 5. 实例大小计算

```cpp
instanceSize = axisCount * sizeof(SK_OT_Fixed)  // 每轴4字节
             + 4                                 // subfamilyNameID + flags
             + (postScriptNameID存在 ? 2 : 0);  // 可选字段
```

## 依赖关系

### 直接依赖

- `src/base/SkEndian.h`: 字节序转换宏
- `src/sfnt/SkOTTableTypes.h`: OpenType类型定义(`SK_OT_USHORT`, `SK_OT_FIXED`等)

### 被依赖情况

- `SkTypeface` 实现类: 查询可变轴信息
- `SkFontMgr`: 字体枚举和选择
- 字体变体合成代码

## 设计模式与设计决策

### 1. POD 结构体

纯数据结构(Plain Old Data):
- 无构造函数
- 无虚函数
- 可直接从文件映射

### 2. 模板实例记录

`InstanceRecord<AxisCount>` 使用模板参数:
- 编译时确定数组大小
- 类型安全
- 零运行时开销

### 3. 嵌套类型定义

常量和标签定义为嵌套类型:
```cpp
static const SK_OT_CHAR TAG0 = 'f';
static const SK_OT_ULONG TAG = ...;
```

便于类型安全的标签匹配。

### 4. 紧凑布局

`#pragma pack(1)` 确保:
- 与字体文件格式精确对应
- 无浪费的填充字节
- 可直接内存映射

## 性能考量

### 1. 零拷贝访问

结构体可直接映射到文件内存:
- 无需反序列化
- 读取时才转换字节序
- 内存占用最小

### 2. 缓存友好

紧凑的16字节表头:
- 单个缓存行可容纳
- 顺序访问变化轴数组

### 3. 预定义实例优化

命名实例提供常用样式的快速访问:
- 无需插值计算
- 直接使用预设坐标
- 减少字体合成开销

## 相关文件

### 核心依赖

- `src/sfnt/SkOTTableTypes.h`: 类型定义
- `src/sfnt/SkOTTable_name.h`: 名称表(用于解析nameID)
- `src/base/SkEndian.h`: 字节序工具

### 相关表定义

- `src/sfnt/SkOTTable_avar.h`: 轴变化表
- `src/sfnt/SkOTTable_STAT.h`: 样式属性表
- `src/sfnt/SkOTTable_gvar.h`: 字形变化表

### 字体变体相关

- `include/core/SkFontArguments.h`: 字体变体参数
- `src/ports/SkTypeface_*.cpp`: 各平台的字体实现

该文件是 Skia 支持可变字体的基础,通过精确定义 OpenType `fvar` 表结构,使 Skia 能够解析和使用现代可变字体技术,为用户提供灵活的字体样式选择能力。
