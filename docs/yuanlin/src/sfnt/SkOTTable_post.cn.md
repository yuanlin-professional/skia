# SkOTTable_post

> 源文件: src/sfnt/SkOTTable_post.h

## 概述

`SkOTTable_post.h` 定义了 OpenType `post` (PostScript) 表的结构,存储字体的PostScript相关信息,包括斜体角度、下划线位置和厚度、是否等宽、内存需求等。该表主要用于PostScript打印输出和字体转换场景,同时也提供了一些通用的字体属性信息。虽然现代图形系统较少直接使用PostScript,但该表仍是OpenType规范的必需组成部分。

`post` 表的版本决定了字形名称的存储方式,版本1.0包含标准Mac字形名称,版本2.0支持自定义名称,版本3.0不存储字形名称,版本4.0用于AAT字体。

## 架构位置

- **模块路径**: `src/sfnt/`
- **表标签**: `'post'`
- **功能**: PostScript信息和字体属性
- **依赖**: `SkOTTableTypes.h`, `SkEndian.h`
- **用途**: 打印、字形命名、等宽判断

## 主要类与结构体

### SkOTTablePostScript

**表头**(32字节):
```cpp
Format format;                  // 版本号
SK_OT_Fixed italicAngle;        // 斜体角度(度,16.16定点数)
SK_OT_FWORD underlinePosition;  // 下划线位置(FUnit)
SK_OT_FWORD underlineThickness; // 下划线厚度(FUnit)
SK_OT_ULONG isFixedPitch;       // 是否等宽(0=否,非0=是)
SK_OT_ULONG minMemType42;       // Type 42最小内存需求
SK_OT_ULONG maxMemType42;       // Type 42最大内存需求
SK_OT_ULONG minMemType1;        // Type 1最小内存需求
SK_OT_ULONG maxMemType1;        // Type 1最大内存需求
```

### Format (版本枚举)

```cpp
enum Value : SK_OT_Fixed {
    version1   = 0x00010000,  // 版本1.0:标准Mac字形名称
    version2   = 0x00020000,  // 版本2.0:自定义字形名称
    version2_5 = 0x00025000,  // 版本2.5:偏移数组(TrueType GX)
    version3   = 0x00030000,  // 版本3.0:无字形名称
    version4   = 0x00040000   // 版本4.0:AAT字体
};
```

## 公共 API 函数

仅包含数据结构定义。

**使用示例**:
```cpp
const SkOTTablePostScript* post = /* 读取 */;

// 读取斜体角度
int32_t italicAngleFixed = SkEndian_SwapBE32(post->italicAngle);
float italicAngle = SkFixedToFloat(italicAngleFixed);  // 转换为浮点度数
// 例如: -12.0度表示向右倾斜12度

// 读取下划线参数
int16_t underlinePos = SkEndian_SwapBE16(post->underlinePosition);
int16_t underlineThick = SkEndian_SwapBE16(post->underlineThickness);
// 转换为像素:pos_pixels = underlinePos * fontSize / unitsPerEm

// 判断是否等宽
bool isMonospace = SkEndian_SwapBE32(post->isFixedPitch) != 0;

// 检查版本
uint32_t version = SkEndian_SwapBE32(post->format.value);
if (version == SkOTTablePostScript::Format::version2) {
    // 版本2:读取自定义字形名称...
} else if (version == SkOTTablePostScript::Format::version3) {
    // 版本3:无字形名称数据
}
```

## 内部实现细节

### 1. 斜体角度

**格式**: 16.16定点数,单位为度
**解释**:
- 0.0: 正常直立
- 负值: 向右倾斜(常规斜体,如-12.0)
- 正值: 向左倾斜(少见)

**计算倾斜**:
```cpp
float angle = SkFixedToFloat(italicAngle);
float skewX = tan(angle * π / 180.0);  // 水平倾斜量
```

### 2. 下划线参数

**坐标系**: FUnit(字体单位)
**转换到像素**:
```cpp
float underlinePosPixels = underlinePosition * fontSize / unitsPerEm;
float underlineThickPixels = underlineThickness * fontSize / unitsPerEm;
```

**典型值**:
- `underlinePosition`: -100到-200 FUnit(基线下方)
- `underlineThickness`: 50-100 FUnit

### 3. 等宽判断

```cpp
bool isMonospace = (isFixedPitch != 0);
```

**影响**:
- 文本布局优化
- 对齐计算简化
- 缓存策略

等宽字体所有字形具有相同的前进宽度。

### 4. 内存需求字段

**用途**: PostScript下载字体时的内存预估

**Type 42**: TrueType格式封装在PostScript中
**Type 1**: PostScript Type 1字体

现代系统通常忽略这些字段。

### 5. 版本差异

**版本1.0**:
- 包含标准258个Mac字形名称
- 无额外数据

**版本2.0**:
- 表头后跟:
  - `uint16_t numGlyphs`
  - `uint16_t glyphNameIndex[numGlyphs]`
  - `Pascal字符串数组`

**版本3.0**:
- 仅表头(32字节)
- 无字形名称数据
- 最常用版本

**版本4.0**:
- AAT(Apple Advanced Typography)专用
- 包含字形类别映射

## 依赖关系

### 直接依赖

- `src/sfnt/SkOTTableTypes.h`
- `src/base/SkEndian.h`

### 被依赖情况

- `SkTypeface`: 斜体角度查询
- `SkPaint`: 下划线渲染
- PDF生成器: PostScript字体嵌入
- 字形命名工具

## 设计模式与设计决策

### 1. 固定表头

32字节固定大小表头:
- 快速读取核心信息
- 可变长度数据(字形名称)分离

### 2. 多版本支持

通过版本号扩展功能:
- 向后兼容
- 按需包含数据
- 版本3最精简

### 3. 定点数精度

斜体角度使用16.16定点:
- 精度充足(约0.00002度)
- 避免浮点兼容性问题
- 紧凑存储

### 4. 布尔值约定

`isFixedPitch` 使用uint32:
- 0 = false
- 非0 = true
- 兼容多种约定

## 性能考量

### 1. 表头缓存

32字节表头:
- 单次读取
- 缓存在`SkTypeface`中
- 无重复解析

### 2. 字形名称优化

版本3跳过名称数据:
- 减小字体文件
- 加快加载速度
- 现代系统不需要名称

### 3. 等宽优化

`isFixedPitch` 标志支持:
- 文本布局O(n)而非O(n)度量查询
- 简化对齐计算
- 缓存友好

### 4. 内存占用

最小表(版本3): 32字节
最大表(版本2,大字体): 32字节 + 2 + numGlyphs*2 + 名称字符串

## 相关文件

### 核心依赖

- `src/sfnt/SkOTTableTypes.h`
- `src/base/SkEndian.h`

### 相关表

- `src/sfnt/SkOTTable_name.h`: 名称表(字体名称)
- `src/sfnt/SkOTTable_head.h`: 字体头(unitsPerEm等)
- `src/sfnt/SkOTTable_hhea.h`: 水平头(排版度量)

### Skia接口

- `include/core/SkTypeface.h`: 字体接口
- `include/core/SkPaint.h`: 绘制属性(下划线)
- `include/core/SkFontMetrics.h`: 字体度量

### PDF/PostScript

- PDF生成器: 字体嵌入
- PostScript输出: 字体信息

该表虽然主要服务于PostScript场景,但其中的斜体角度、下划线参数和等宽标志对现代文本渲染仍然重要,是字体元数据的关键组成部分。
