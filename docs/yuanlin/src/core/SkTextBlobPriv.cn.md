# SkTextBlobPriv

> 源文件: src/core/SkTextBlobPriv.h

## 概述

`SkTextBlobPriv.h` 定义了 `SkTextBlob` 的内部实现细节和私有接口。`SkTextBlob` 是 Skia 高性能文本渲染的核心数据结构,将多个文本运行(runs)及其字形、位置、字体等数据紧凑地存储在连续内存中。该文件暴露了运行记录(`RunRecord`)的布局、迭代器(`SkTextBlobRunIterator`)以及序列化接口,供 Skia 内部模块使用。

## 架构位置

文本块私有接口位于 Skia 核心文本系统的实现层:

- **上层**: `SkTextBlob` 公共 API、`SkTextBlobBuilder`
- **用途**: 文本运行存储、快速渲染、序列化
- **使用者**: `SkCanvas`、渲染后端、序列化系统

## 主要类与结构体

### SkTextBlobPriv

**静态工具类**:

| 方法 | 功能 |
|------|------|
| `static void Flatten(const SkTextBlob&, SkWriteBuffer&)` | 序列化文本块 |
| `static sk_sp<SkTextBlob> MakeFromBuffer(SkReadBuffer&)` | 反序列化文本块 |
| `static bool HasRSXForm(const SkTextBlob&)` | 检查是否包含旋转缩放变换 |

### RunRecord

**文本运行记录**,存储单个文本运行的所有数据。

**继承关系**:
- 无继承,POD-like 结构

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fFont` | `SkFont` | 字体对象 |
| `fCount` | `uint32_t` | 字形数量 |
| `fOffset` | `SkPoint` | 运行偏移 |
| `fFlags` | `uint32_t` | 标志(定位模式、是否最后、是否扩展) |

**Flags 枚举**:

| 标志 | 值 | 说明 |
|------|----|----|
| `kPositioning_Mask` | `0x03` | 位 0-1: 定位模式 |
| `kLast_Flag` | `0x04` | 最后一个运行 |
| `kExtended_Flag` | `0x08` | 包含文本/聚类信息 |

### SkTextBlobRunIterator

**运行迭代器**,用于遍历文本块中的所有运行。

**GlyphPositioning 枚举**:

| 枚举值 | 数值 | 说明 |
|--------|------|------|
| `kDefault_Positioning` | 0 | 默认字形前进量(0 个标量) |
| `kHorizontal_Positioning` | 1 | 水平定位(1 个标量/字形) |
| `kFull_Positioning` | 2 | 完整定位(2 个标量/字形) |
| `kRSXform_Positioning` | 3 | 旋转缩放变换(4 个标量/字形) |

**关键成员变量**:

| 成员 | 类型 | 说明 |
|------|------|------|
| `fCurrentRun` | `const RunRecord*` | 当前运行指针 |

## 公共 API 函数

### RunRecord 方法

| 方法 | 功能描述 |
|------|---------|
| `RunRecord(uint32_t, uint32_t, const SkPoint&, const SkFont&, GlyphPositioning)` | 构造运行记录 |
| `uint32_t glyphCount() const` | 获取字形数量 |
| `const SkPoint& offset() const` | 获取偏移 |
| `const SkFont& font() const` | 获取字体 |
| `GlyphPositioning positioning() const` | 获取定位模式 |
| `SkGlyphID* glyphBuffer() const` | 获取字形缓冲区 |
| `SkScalar* posBuffer() const` | 获取位置缓冲区 |
| `SkPoint* pointBuffer() const` | 获取点缓冲区(别名) |
| `SkRSXform* xformBuffer() const` | 获取变换缓冲区(别名) |
| `uint32_t textSize() const` | 获取文本大小(扩展运行) |
| `uint32_t* clusterBuffer() const` | 获取聚类缓冲区(扩展运行) |
| `char* textBuffer() const` | 获取文本缓冲区(扩展运行) |
| `bool isLastRun() const` | 是否最后一个运行 |
| `static size_t StorageSize(...)` | 计算存储大小 |
| `static const RunRecord* First(const SkTextBlob*)` | 获取第一个运行 |
| `static const RunRecord* Next(const RunRecord*)` | 获取下一个运行 |

### SkTextBlobRunIterator 方法

| 方法 | 功能描述 |
|------|---------|
| `explicit SkTextBlobRunIterator(const SkTextBlob*)` | 构造迭代器 |
| `bool done() const` | 是否完成 |
| `void next()` | 移动到下一个运行 |
| `uint32_t glyphCount() const` | 当前运行字形数 |
| `const SkGlyphID* glyphs() const` | 当前运行字形 |
| `const SkScalar* pos() const` | 当前运行位置 |
| `const SkPoint* points() const` | 当前运行点(别名) |
| `const SkRSXform* xforms() const` | 当前运行变换(别名) |
| `const SkPoint& offset() const` | 当前运行偏移 |
| `const SkFont& font() const` | 当前运行字体 |
| `GlyphPositioning positioning() const` | 当前运行定位模式 |
| `unsigned scalarsPerGlyph() const` | 每字形标量数 |
| `uint32_t* clusters() const` | 当前运行聚类 |
| `uint32_t textSize() const` | 当前运行文本大小 |
| `char* text() const` | 当前运行文本 |
| `bool isLCD() const` | 是否 LCD 渲染 |

## 内部实现细节

### 内存布局

**基础文本块布局**:
```
+-----------------------------------------------------------------------------+
| SkTextBlob | RunRecord | Glyphs[] | Pos[] | RunRecord | Glyphs[] | Pos[] | ...
+-----------------------------------------------------------------------------+
```

**扩展文本块布局**:
```
+-------------------------------------------------------------------------+
| ... | RunRecord | Glyphs[] | Pos[] | TextSize | Clusters[] | Text[] | ...
+-------------------------------------------------------------------------+
```

### RunRecord 实现

**数据紧凑排列**:
```cpp
// RunRecord 后立即是字形数据
SkGlyphID* glyphBuffer() const {
    static_assert(SkIsAlignPtr(sizeof(RunRecord)), "");
    return reinterpret_cast<SkGlyphID*>(const_cast<RunRecord*>(this) + 1);
}

// 字形数据后是位置数据(对齐到 4 字节)
SkScalar* posBuffer() const {
    return reinterpret_cast<SkScalar*>(
        reinterpret_cast<uint8_t*>(this->glyphBuffer()) +
        SkAlign4(fCount * sizeof(SkGlyphID))
    );
}
```

### 定位模式

| 模式 | 标量数/字形 | 数据类型 | 用途 |
|------|------------|---------|------|
| `kDefault` | 0 | 无 | 使用字体默认前进量 |
| `kHorizontal` | 1 | `SkScalar[]` | 自定义水平位置 |
| `kFull` | 2 | `SkPoint[]` | 完全控制 X/Y 位置 |
| `kRSXform` | 4 | `SkRSXform[]` | 旋转+缩放+平移 |

### 扩展运行

包含额外的文本和聚类信息,用于:
- 文本搜索和选择
- 辅助功能
- 双向文本处理

**检测扩展运行**:
```cpp
bool isExtended() const {
    return fFlags & kExtended_Flag;
}

uint32_t textSize() const {
    return isExtended() ? *this->textSizePtr() : 0;
}
```

**数据布局**:
```
位置数据后:
1. uint32_t textSize
2. uint32_t clusters[glyphCount]
3. char text[textSize]
```

### 运行遍历

```cpp
const RunRecord* RunRecord::Next(const RunRecord* run) {
    size_t size = StorageSize(
        run->glyphCount(),
        run->textSize(),
        run->positioning(),
        &safeMath
    );
    return reinterpret_cast<const RunRecord*>(
        reinterpret_cast<const uint8_t*>(run) + size
    );
}
```

### 存储大小计算

```cpp
static size_t StorageSize(uint32_t glyphCount,
                          uint32_t textSize,
                          GlyphPositioning positioning,
                          SkSafeMath* safe) {
    size_t size = sizeof(RunRecord);
    size = safe->add(size, safe->mul(glyphCount, sizeof(SkGlyphID)));
    size = safe->alignUp(size, sizeof(SkScalar));

    size_t posCount = PosCount(glyphCount, positioning, safe);
    size = safe->add(size, safe->mul(posCount, sizeof(SkScalar)));

    if (textSize > 0) {  // 扩展运行
        size = safe->add(size, sizeof(uint32_t));  // textSize
        size = safe->add(size, safe->mul(glyphCount, sizeof(uint32_t)));  // clusters
        size = safe->add(size, textSize);  // text
    }
    return size;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `SkTextBlob` | 公共 API |
| `SkFont` | 字体信息 |
| `SkReadBuffer`/`SkWriteBuffer` | 序列化 |
| `SkSafeMath` | 安全的整数运算 |

### 被依赖的模块

| 模块 | 关系 |
|-----|------|
| `SkCanvas::onDrawTextBlob()` | 使用迭代器遍历运行 |
| `SkTextBlobBuilder` | 使用 `RunRecord` 构建文本块 |
| GPU 后端 | 解析运行数据进行渲染 |
| 序列化系统 | 使用 `Flatten`/`MakeFromBuffer` |

## 设计模式与设计决策

### 设计模式

1. **迭代器模式**: `SkTextBlobRunIterator` 提供遍历接口
2. **内存池模式**: 所有数据在连续内存中
3. **类型安全别名**: `pointBuffer()`/`xformBuffer()` 为 `posBuffer()` 的类型安全视图

### 设计决策

**为什么使用连续内存布局?**
- 提高缓存局部性
- 减少内存分配次数
- 便于序列化和复制

**为什么限制参数数量?**
支持 0-2 个参数,因为:
- 大多数场景足够
- 保持数据紧凑
- 避免复杂的变长数据处理

**扩展运行的权衡**
- 仅在需要时包含文本/聚类
- 节省大多数情况下的内存
- 增加少许复杂度

**定位模式的层次**
```
Default (0 标量) < Horizontal (1 标量) < Full (2 标量) < RSXform (4 标量)
```
- 提供性能-功能的权衡
- 默认模式最快,RSXform 最灵活

**为什么使用标志位而非虚函数?**
- 保持 POD-like 结构
- 避免虚表开销
- 便于序列化

## 性能考量

### 优化策略

1. **紧凑布局**: 最小化内存占用
2. **对齐**: 字形/位置数据对齐以提高访问速度
3. **预计算大小**: 构建时一次性分配
4. **缓存友好**: 连续遍历,减少缓存未命中

### 性能特性

**内存占用**:
```
基础运行 = sizeof(RunRecord)         // ~32 字节
          + glyphCount * 2           // 字形 ID
          + posCount * 4             // 位置数据
          + 对齐填充

扩展运行 = 基础运行
          + 4                        // textSize
          + glyphCount * 4           // clusters
          + textSize                 // text
```

**遍历性能**:
- 指针算术,无虚函数调用
- 线性内存访问,缓存友好
- 典型遍历: ~1-2 周期/运行

### 使用建议

**选择定位模式**:
- 简单文本: `kDefault`
- 数字/表格: `kHorizontal`
- 艺术字: `kFull`
- 旋转文本: `kRSXform`

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `include/core/SkTextBlob.h` | 公共 API |
| `src/core/SkTextBlob.cpp` | 实现 |
| `src/core/SkTextBlobBuilder.cpp` | 构建器 |
| `include/core/SkFont.h` | 字体定义 |
| `src/core/SkReadBuffer.h` | 序列化输入 |
| `src/core/SkWriteBuffer.h` | 序列化输出 |
