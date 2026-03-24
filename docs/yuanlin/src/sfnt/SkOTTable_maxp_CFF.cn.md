# SkOTTableMaximumProfile_CFF

> 源文件: src/sfnt/SkOTTable_maxp_CFF.h

## 概述

`SkOTTable_maxp_CFF.h` 定义了 CFF (Compact Font Format) 字体的 maxp (Maximum Profile) 表结构。CFF 是 PostScript 轮廓字体格式,maxp 表存储字体中的字形数量。与 TrueType 版本相比,CFF 版本的 maxp 表极其简单,仅包含版本号和字形数量两个字段,因为 CFF 字体不需要 TrueType 字形提示所需的额外资源信息。

## 架构位置

```
Skia 字体系统
└── src/sfnt/
    ├── SkOTTable_maxp.h (maxp 表统一接口)
    ├── SkOTTable_maxp_CFF.h (CFF 版本) ←
    └── SkOTTable_maxp_TT.h (TrueType 版本)
```

## 主要类与结构体

### SkOTTableMaximumProfile_CFF

```cpp
struct SkOTTableMaximumProfile_CFF {
    SK_OT_Fixed version;  // 版本号
    static const SK_OT_Fixed VERSION = SkTEndian_SwapBE32(0x00005000);  // 0.5

    SK_OT_USHORT numGlyphs;  // 字形数量
};
```

**字段说明**:
- **version**: 固定为 0x00005000 (0.5),标识 CFF 格式
- **numGlyphs**: 字体中的字形总数

**大小**: 6 字节 (4 + 2)

## 公共 API 函数

```cpp
// 读取 maxp 表并检查是否为 CFF 格式
const SkOTTableMaximumProfile_CFF* maxp =
    typeface->getTableData<SkOTTableMaximumProfile_CFF>(TAG);

// 检查版本
if (SkEndian_SwapBE32(maxp->version) == 0x00005000) {
    // CFF 字体
    uint16_t numGlyphs = SkEndian_SwapBE16(maxp->numGlyphs);
}
```

## 内部实现细节

### 版本标识

版本号 0.5 (0x00005000) 是 CFF 字体的标识:
- TrueType 使用 1.0 (0x00010000)
- CFF 使用 0.5 (0x00005000)

### 内存布局验证

```cpp
static_assert(offsetof(SkOTTableMaximumProfile_CFF, numGlyphs) == 4,
    "SkOTTableMaximumProfile_CFF_numGlyphs_not_at_4");
static_assert(sizeof(SkOTTableMaximumProfile_CFF) == 6,
    "sizeof_SkOTTableMaximumProfile_CFF_not_6");
```

## 依赖关系

```
SkOTTable_maxp_CFF.h
├── src/base/SkEndian.h (字节序转换)
└── src/sfnt/SkOTTableTypes.h (基础类型)
```

**被依赖方**:
- `SkOTTable_maxp.h` - maxp 表统一接口
- CFF/PostScript 字体处理代码

## 设计模式与设计决策

### 最小化设计

CFF maxp 表仅包含必要信息:
- CFF 字形数据是自描述的
- 不需要 TrueType 的提示资源上限
- 极简设计减少开销

### 与 TrueType 的对比

| 字段 | CFF | TrueType |
|------|-----|----------|
| 版本 | 0.5 | 1.0 |
| numGlyphs | ✓ | ✓ |
| maxPoints | ✗ | ✓ |
| maxContours | ✗ | ✓ |
| 提示相关 | ✗ | ✓ (10+ 字段) |
| 大小 | 6 字节 | 32 字节 |

## 性能考量

### 内存效率

仅 6 字节,极其紧凑:
- 减少磁盘 I/O
- 快速加载和解析
- 缓存友好

### 访问速度

简单结构,直接访问:
```cpp
uint16_t numGlyphs = SkEndian_SwapBE16(maxp->numGlyphs);  // O(1)
```

## 相关文件

| 文件路径 | 说明 | 关系 |
|---------|------|------|
| `src/sfnt/SkOTTable_maxp.h` | maxp 表统一接口 | 包含此版本 |
| `src/sfnt/SkOTTable_maxp_TT.h` | TrueType 版本 | 对应的 TT 版本 |
| `src/sfnt/SkOTTableTypes.h` | 基础类型 | 类型定义 |

CFF maxp 表体现了 CFF 字体格式的简洁设计哲学,通过最小化元数据降低开销。
