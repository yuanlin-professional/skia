# SkOTTableMaximumProfile

> 源文件: src/sfnt/SkOTTable_maxp.h

## 概述

`SkOTTable_maxp.h` 是 maxp (Maximum Profile) 表的统一接口文件,通过联合体整合了 CFF 和 TrueType 两种格式的 maxp 表。该文件提供版本多态访问,允许代码根据字体类型(CFF 或 TrueType)访问相应的表结构,实现对不同字体格式的统一处理。

## 架构位置

```
Skia 字体系统
└── src/sfnt/
    ├── SkOTTable_maxp.h (统一接口) ←
    ├── SkOTTable_maxp_CFF.h (CFF 版本, 6 字节)
    └── SkOTTable_maxp_TT.h (TrueType 版本, 32 字节)
```

## 主要类与结构体

### SkOTTableMaximumProfile

```cpp
struct SkOTTableMaximumProfile {
    static const SK_OT_CHAR TAG0 = 'm';
    static const SK_OT_CHAR TAG1 = 'a';
    static const SK_OT_CHAR TAG2 = 'x';
    static const SK_OT_CHAR TAG3 = 'p';
    static const SK_OT_ULONG TAG = SkOTTableTAG<...>::value;

    union Version {
        SK_OT_Fixed version;  // 版本号字段

        // CFF 和 TrueType 版本的命名访问
        struct CFF : SkOTTableMaximumProfile_CFF { } cff;
        struct TT : SkOTTableMaximumProfile_TT { } tt;
    } version;
};
```

**标签**: `"maxp"`

## 版本识别

| 版本号 | 格式 | 大小 | 说明 |
|--------|------|------|------|
| 0.5 (0x00005000) | CFF | 6 字节 | PostScript 轮廓字体 |
| 1.0 (0x00010000) | TrueType | 32 字节 | TrueType 轮廓字体 |

## 公共 API 函数

### 典型使用模式

```cpp
// 1. 读取 maxp 表
const SkOTTableMaximumProfile* maxp =
    typeface->getTableData<SkOTTableMaximumProfile>(
        SkOTTableMaximumProfile::TAG);

// 2. 读取版本号并判断格式
uint32_t version = SkEndian_SwapBE32(maxp->version.version);

// 3. 根据版本访问相应字段
if (version == 0x00005000) {
    // CFF 字体
    const auto& cff = maxp->version.cff;
    uint16_t numGlyphs = SkEndian_SwapBE16(cff.numGlyphs);

} else if (version == 0x00010000) {
    // TrueType 字体
    const auto& tt = maxp->version.tt;
    uint16_t numGlyphs = SkEndian_SwapBE16(tt.numGlyphs);
    uint16_t maxPoints = SkEndian_SwapBE16(tt.maxPoints);
}

// 4. 访问共有字段 numGlyphs
// 两种格式的 numGlyphs 位置相同(偏移 4)
const uint16_t* numGlyphsPtr =
    reinterpret_cast<const uint16_t*>(
        reinterpret_cast<const uint8_t*>(maxp) + 4);
uint16_t numGlyphs = SkEndian_SwapBE16(*numGlyphsPtr);
```

## 内部实现细节

### 联合体内存布局

```cpp
union Version {
    SK_OT_Fixed version;   // 占 4 字节,起始位置
    struct CFF { ... } cff;   // 占 6 字节,从起始位置开始
    struct TT { ... } tt;     // 占 32 字节,从起始位置开始
};
```

**特性**:
- 所有版本共享同一内存
- 联合体大小 = 最大成员大小 = 32 字节
- 前 4 字节始终是版本号

### 版本号作为类型标识

版本号既是数据字段,也是类型标识:
```cpp
switch (SkEndian_SwapBE32(maxp->version.version)) {
    case 0x00005000:
        // 使用 maxp->version.cff
        break;
    case 0x00010000:
        // 使用 maxp->version.tt
        break;
}
```

### 共有字段 numGlyphs

两种格式的 `numGlyphs` 都在偏移 4 的位置:
- CFF: version(4) + numGlyphs(2) = 6 字节
- TT: version(4) + numGlyphs(2) + ... = 32 字节

允许统一访问字形数量。

## 依赖关系

```
SkOTTable_maxp.h
├── src/sfnt/SkOTTableTypes.h
├── src/sfnt/SkOTTable_maxp_CFF.h
└── src/sfnt/SkOTTable_maxp_TT.h
```

**被依赖方**:
- 字体加载器
- 字形索引器
- 光栅化引擎
- 字体信息查询

## 设计模式与设计决策

### 1. 联合体多态

**优势**:
- 单一指针访问两种格式
- 类型安全的版本切换
- 避免类型转换错误

**示例**:
```cpp
const SkOTTableMaximumProfile* maxp = ...;
// 直接访问,无需 reinterpret_cast
if (isCFF) {
    uint16_t num = maxp->version.cff.numGlyphs;
} else {
    uint16_t num = maxp->version.tt.numGlyphs;
}
```

### 2. 零开销抽象

联合体访问编译为直接内存访问:
```cpp
// 无额外指令,直接访问内存
uint16_t numGlyphs = maxp->version.cff.numGlyphs;
```

### 3. 向前兼容设计

联合体大小为最大成员(32字节):
- 确保任意版本都能正确访问
- 避免越界访问
- 简化内存管理

## 性能考量

### 内存占用

联合体固定占用 32 字节:
- CFF 实际使用 6 字节
- TrueType 使用全部 32 字节
- 轻微的空间浪费换取简单性

### 访问效率

```cpp
// 高效的版本检查和访问
if (version == 0x00005000) {
    // 直接内存访问,无函数调用
    uint16_t n = maxp->version.cff.numGlyphs;
}
```

### 缓存友好

32 字节的小结构:
- 易于整体缓存
- 减少缓存未命中
- 提高访问速度

## 相关文件

| 文件路径 | 说明 | 关系 |
|---------|------|------|
| `src/sfnt/SkOTTable_maxp_CFF.h` | CFF 版本定义 | 被包含的版本 |
| `src/sfnt/SkOTTable_maxp_TT.h` | TrueType 版本定义 | 被包含的版本 |
| `src/sfnt/SkOTTable_glyf.h` | 字形数据表 | 使用 numGlyphs |
| `src/sfnt/SkOTTable_loca.h` | 位置表 | 使用 numGlyphs |
| `src/ports/SkTypeface_*.cpp` | 字体接口实现 | 读取 maxp 表 |

maxp 表统一接口通过联合体设计优雅地支持 CFF 和 TrueType 两种格式,为 Skia 字体系统提供了类型安全且高效的访问方式。
