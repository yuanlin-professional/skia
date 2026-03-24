# SkOTTableMaximumProfile_TT

> 源文件: src/sfnt/SkOTTable_maxp_TT.h

## 概述

`SkOTTable_maxp_TT.h` 定义了 TrueType 字体的 maxp (Maximum Profile) 表结构。maxp 表存储字体的资源使用上限,包括字形数量、轮廓点数、TrueType 指令资源等。这些信息帮助光栅化引擎预分配足够的内存,避免运行时溢出。TrueType maxp 表包含 14 个字段,远比 CFF 版本复杂。

## 架构位置

```
Skia 字体系统
└── src/sfnt/
    ├── SkOTTable_maxp.h (maxp 表统一接口)
    ├── SkOTTable_maxp_CFF.h (CFF 版本)
    └── SkOTTable_maxp_TT.h (TrueType 版本) ←
```

## 主要类与结构体

### SkOTTableMaximumProfile_TT

```cpp
struct SkOTTableMaximumProfile_TT {
    SK_OT_Fixed version;  // 版本号 = 1.0
    static const SK_OT_Fixed VERSION = SkTEndian_SwapBE32(0x00010000);

    SK_OT_USHORT numGlyphs;             // 字形数量
    SK_OT_USHORT maxPoints;             // 简单字形最大点数
    SK_OT_USHORT maxContours;           // 简单字形最大轮廓数
    SK_OT_USHORT maxCompositePoints;    // 复合字形最大点数
    SK_OT_USHORT maxCompositeContours;  // 复合字形最大轮廓数
    MaxZones maxZones;                  // 使用的区域数
    SK_OT_USHORT maxTwilightPoints;     // Twilight 区域点数
    SK_OT_USHORT maxStorage;            // Storage 区域大小
    SK_OT_USHORT maxFunctionDefs;       // 函数定义数
    SK_OT_USHORT maxInstructionDefs;    // 指令定义数
    SK_OT_USHORT maxStackElements;      // 栈深度
    SK_OT_USHORT maxSizeOfInstructions; // 字形指令最大字节数
    SK_OT_USHORT maxComponentElements;  // 复合字形最大组件数
    SK_OT_USHORT maxComponentDepth;     // 复合字形最大嵌套层数
};
```

**大小**: 32 字节

### MaxZones (区域枚举)

```cpp
struct MaxZones {
    enum Value : SK_OT_USHORT {
        DoesNotUseTwilightZone = SkTEndian_SwapBE16(1),  // 不使用 Twilight 区
        UsesTwilightZone = SkTEndian_SwapBE16(2),        // 使用 Twilight 区
    } value;
};
```

**说明**: Twilight Zone 是 TrueType 提示系统的临时工作区

## 字段详解

### 字形相关

- **numGlyphs**: 字体包含的字形总数,包括 .notdef
- **maxPoints**: 所有简单字形中点数最多的字形的点数
- **maxContours**: 所有简单字形中轮廓数最多的字形的轮廓数

### 复合字形相关

- **maxCompositePoints**: 所有复合字形展开后的最大点数
- **maxCompositeContours**: 所有复合字形展开后的最大轮廓数
- **maxComponentElements**: 复合字形中最多的组件数
- **maxComponentDepth**: 复合字形的最大嵌套层数

### TrueType 指令相关

- **maxZones**: 区域使用情况 (1 或 2)
- **maxTwilightPoints**: Twilight Zone 中的点数
- **maxStorage**: Storage 区域大小 (32位值数组)
- **maxFunctionDefs**: FDEF 定义的函数数量
- **maxInstructionDefs**: IDEF 定义的指令数量
- **maxStackElements**: 执行栈最大深度
- **maxSizeOfInstructions**: 单个字形指令字节数上限

## 公共 API 函数

```cpp
// 读取 maxp 表
const SkOTTableMaximumProfile_TT* maxp =
    typeface->getTableData<SkOTTableMaximumProfile_TT>(TAG);

// 获取字形数量
uint16_t numGlyphs = SkEndian_SwapBE16(maxp->numGlyphs);

// 检查是否使用 Twilight Zone
bool usesTwilight = SkEndian_SwapBE16(maxp->maxZones.value) ==
    SkOTTableMaximumProfile_TT::MaxZones::UsesTwilightZone;

// 预分配缓冲区
uint16_t maxPoints = SkEndian_SwapBE16(maxp->maxPoints);
allocatePointBuffer(maxPoints);
```

## 内部实现细节

### 内存布局验证

```cpp
static_assert(offsetof(SkOTTableMaximumProfile_TT, maxComponentDepth) == 30,
    "SkOTTableMaximumProfile_TT_maxComponentDepth_not_at_30");
static_assert(sizeof(SkOTTableMaximumProfile_TT) == 32,
    "sizeof_SkOTTableMaximumProfile_TT_not_32");
```

### 版本标识

版本号 1.0 (0x00010000) 标识 TrueType 格式:
- 区别于 CFF 的 0.5 版本
- 包含完整的 TrueType 资源信息

## 依赖关系

```
SkOTTable_maxp_TT.h
├── src/base/SkEndian.h
└── src/sfnt/SkOTTableTypes.h
```

**被依赖方**:
- `SkOTTable_maxp.h` - maxp 表统一接口
- TrueType 光栅化引擎
- 字形加载器
- 提示引擎

## 设计模式与设计决策

### 资源预分配

maxp 表的主要目的是支持资源预分配:
```cpp
// 光栅化引擎初始化
void initRasterizer(const maxp_TT* maxp) {
    pointBuffer = malloc(maxp->maxPoints * sizeof(Point));
    storageArea = malloc(maxp->maxStorage * sizeof(int32_t));
    stack = malloc(maxp->maxStackElements * sizeof(int32_t));
}
```

### 复合字形处理

复合字形字段支持高效处理:
- **maxComponentDepth**: 防止递归溢出
- **maxComponentElements**: 预分配组件数组
- **maxCompositePoints**: 预分配展开后的点缓冲区

### TrueType 指令系统

提示相关字段支持完整的 TrueType 指令执行:
- 函数和指令定义上限
- Storage 和栈大小
- Twilight Zone 支持

## 性能考量

### 预分配策略

maxp 表实现零运行时分配:
```cpp
// 一次性分配,避免重复 malloc
initializeFromMaxp(maxp);
// 后续字形加载使用预分配缓冲区,无需动态分配
```

### 内存权衡

32 字节的表大小换来:
- 运行时零分配开销
- 无需溢出检查
- 简化错误处理

### 字形加载优化

```cpp
// 无需动态分配或边界检查
assert(glyphNumPoints <= maxp->maxPoints);
memcpy(pointBuffer, glyphPoints, glyphNumPoints * sizeof(Point));
```

## 相关文件

| 文件路径 | 说明 | 关系 |
|---------|------|------|
| `src/sfnt/SkOTTable_maxp.h` | maxp 表统一接口 | 包含此版本 |
| `src/sfnt/SkOTTable_maxp_CFF.h` | CFF 版本 | 对应的 CFF 版本 |
| `src/sfnt/SkOTTable_glyf.h` | 字形数据表 | 使用 maxp 信息 |
| `src/sfnt/SkOTTable_loca.h` | 位置索引表 | 使用 numGlyphs |

TrueType maxp 表是字体光栅化的关键元数据,通过预声明资源上限实现高效的内存管理和错误预防。
