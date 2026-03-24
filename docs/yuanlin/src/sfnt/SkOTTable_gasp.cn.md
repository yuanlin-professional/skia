# SkOTTable_gasp

> 源文件: src/sfnt/SkOTTable_gasp.h

## 概述

`SkOTTable_gasp.h` 定义了 OpenType `gasp` (Grid-fitting And Scan-conversion Procedure) 表的结构,用于控制字体在不同尺寸下的网格拟合(grid-fitting)和抗锯齿(anti-aliasing)行为。该表通过定义ppem(每em像素数)范围和对应的渲染标志,指导渲染引擎何时启用网格拟合、灰度渲染、对称处理等技术,以在各种显示尺寸下获得最佳视觉效果。

`gasp` 表在小尺寸文本清晰度和大尺寸平滑度之间提供平衡,是高质量字体渲染的关键优化机制。

## 架构位置

- **模块路径**: `src/sfnt/`
- **表标签**: `'gasp'`
- **功能**: 渲染提示控制
- **依赖**: `SkOTTableTypes.h`, `SkEndian.h`
- **影响**: 字形光栅化策略

## 主要类与结构体

### SkOTTableGridAndScanProcedure

**表头**(4字节):
```cpp
SK_OT_USHORT version;      // 版本号(0或1)
SK_OT_USHORT numRanges;    // 范围记录数量
// GaspRange gaspRange[numRanges];  // 范围数组(紧随其后)
```

**版本**:
- `version0`: 版本0,支持基础标志
- `version1`: 版本1,支持对称渲染标志

### GaspRange (范围记录)

**成员**:
```cpp
SK_OT_USHORT maxPPEM;      // 该范围的最大ppem值
union behavior flags;       // 渲染行为标志
```

### behavior (渲染标志)

#### Field 结构(位域访问)

```cpp
struct Field {
    // 位 0-7
    Gridfit;                // 启用网格拟合
    DoGray;                 // 启用灰度渲染(抗锯齿)
    SymmetricGridfit;       // 对称网格拟合(v1)
    SymmetricSmoothing;     // 对称平滑(v1)
    Reserved04-07;          // 保留
    // 位 8-15
    Reserved08-15;          // 保留
};
```

#### Raw 结构(掩码访问)

```cpp
struct Raw {
    static const GridfitMask = 0x0001;
    static const DoGrayMask = 0x0002;
    static const SymmetricGridfitMask = 0x0004;
    static const SymmetricSmoothingMask = 0x0008;
    SK_OT_USHORT value;
};
```

## 公共 API 函数

仅包含数据结构定义。

**使用示例**:
```cpp
const SkOTTableGridAndScanProcedure* gasp = /* 读取 */;
uint16_t version = SkEndian_SwapBE16(gasp->version);
uint16_t numRanges = SkEndian_SwapBE16(gasp->numRanges);

const GaspRange* ranges = (const GaspRange*)(gasp + 1);

// 查找目标ppem对应的标志
uint16_t targetPpem = 16;  // 例如16像素字体
for (int i = 0; i < numRanges; ++i) {
    uint16_t maxPpem = SkEndian_SwapBE16(ranges[i].maxPPEM);
    if (targetPpem <= maxPpem) {
        uint16_t flags = SkEndian_SwapBE16(ranges[i].flags.raw.value);

        bool useGridfit = flags & GaspRange::behavior::Raw::GridfitMask;
        bool useAntiAlias = flags & GaspRange::behavior::Raw::DoGrayMask;

        // 应用渲染策略
        break;
    }
}
```

## 内部实现细节

### 1. 范围查找

范围按 `maxPPEM` 递增排序:
```cpp
// 示例范围定义
Range 0: maxPPEM =  8,  flags = 0x0000 (无网格拟合,无灰度)
Range 1: maxPPEM = 16,  flags = 0x0001 (网格拟合,无灰度)
Range 2: maxPPEM = 50,  flags = 0x0003 (网格拟合+灰度)
Range 3: maxPPEM = 65535, flags = 0x0002 (仅灰度)
```

查找算法:
```cpp
for (int i = 0; i < numRanges; ++i) {
    if (ppem <= ranges[i].maxPPEM) {
        return ranges[i].flags;  // 找到第一个覆盖的范围
    }
}
```

### 2. 标志含义

**Gridfit (0x0001)**:
- 启用网格拟合(hinting)
- 将轮廓点对齐到像素网格
- 小尺寸文本更清晰
- 可能失真形状

**DoGray (0x0002)**:
- 启用灰度抗锯齿
- 多级灰度值平滑边缘
- 大尺寸更平滑
- 略微模糊

**SymmetricGridfit (0x0004, v1)**:
- 对称网格拟合
- 保持左右对称(如'n', 'm')
- 避免不对称失真

**SymmetricSmoothing (0x0008, v1)**:
- 对称平滑处理
- 结合对称和抗锯齿

### 3. 典型配置

**小尺寸(≤16ppem)**:
- `Gridfit=1, DoGray=0`: 清晰黑白
- 适合屏幕小字

**中等尺寸(17-50ppem)**:
- `Gridfit=1, DoGray=1`: 网格拟合+抗锯齿
- 平衡清晰和平滑

**大尺寸(>50ppem)**:
- `Gridfit=0, DoGray=1`: 仅抗锯齿
- 保持原始形状

### 4. 版本兼容

```cpp
if (version == version0) {
    // 忽略 SymmetricGridfit 和 SymmetricSmoothing
    flags &= 0x0003;
} else if (version == version1) {
    // 支持所有标志
}
```

## 依赖关系

### 直接依赖

- `src/sfnt/SkOTTableTypes.h`
- `src/base/SkEndian.h`

### 被依赖情况

- `SkScalerContext`: 字形光栅化器
- `SkTypeface`: 渲染策略查询
- TrueType hinting 引擎

## 设计模式与设计决策

### 1. 范围表设计

使用范围而非逐值定义:
- 紧凑表示
- 典型字体3-5个范围
- 快速查找

### 2. 位标志组合

灵活的标志组合:
- 独立控制各项技术
- 扩展性强
- 版本1添加新标志

### 3. 最大值范围

使用 `maxPPEM` 而非 `minPPEM`:
- 自然的顺序查找
- 最后范围用65535覆盖所有

### 4. 联合体访问

提供两种访问方式:
- `Field`: 位域,便于独立操作
- `Raw`: 掩码,便于整体判断

## 性能考量

### 1. 表大小

典型4-12字节(表头)+8-20字节(范围):
- 极小的表
- 缓存友好
- 快速加载

### 2. 查找性能

线性查找:
- O(n),n通常≤5
- 可优化为二分查找
- 实际开销可忽略

### 3. 渲染优化

正确配置可显著改善性能:
- 小字禁用灰度: 3-5x 加速
- 大字禁用网格拟合: 避免hinting开销

### 4. 缓存策略

渲染器缓存gasp查询结果:
```cpp
struct CachedFlags {
    uint16_t ppem;
    uint16_t flags;
};
```

避免重复查表。

## 相关文件

### 核心依赖

- `src/sfnt/SkOTTableTypes.h`
- `src/base/SkEndian.h`

### 渲染引擎

- `src/core/SkScalerContext.cpp`: 光栅化上下文
- `src/core/SkMask.h`: 位图格式
- TrueType hinting 实现

### 相关表

- `src/sfnt/SkOTTable_head.h`: 字体头(包含flags)
- `src/sfnt/SkOTTable_fpgm.h`: Font Program(网格拟合指令)

该表通过精细控制不同尺寸下的渲染策略,确保字体在各种场景下都能呈现最佳视觉效果,是专业字体质量的重要保障。
