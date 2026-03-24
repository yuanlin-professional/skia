# SBIXSlide

> 源文件: `tools/viewer/SBIXSlide.cpp`

## 概述

SBIXSlide 是一个交互式 SBIX（Standard Bitmap Graphics）字体表调试工具。它允许用户通过拖拽控制点实时修改字体文件中的 `glyf`、`hmtx` 和 `sbix` 表的关键字段，并立即看到不同字体管理器（FreeType、Fontations、测试字体管理器）如何解释这些修改后的字体数据。

## 架构位置

属于 `tools/viewer` 模块，是低层 OpenType 字体表解析和渲染行为的调试工具。深入操作 SFNT 表结构的二进制数据。

## 主要类与结构体

### SBIXSlide
- 继承自 `ClickHandlerSlide`
- 5 个可拖拽控制点（颜色编码）:
  - `kGlyfXYMin` (黑色): glyf 表的 xMin/yMin
  - `kGlyfXYMax` (白色): glyf 表的 xMax/yMax
  - `kGlyfLSB` (绿色): 左侧轴承（仅 X 坐标有效）
  - `kGlyfFirstPoint` (蓝色): 轮廓第一个点
  - `kOriginOffset` (红色): SBIX 原点偏移

### 辅助类型
- `ShortCoordinate`: 符号+幅度表示的短坐标
- `sk_float_saturate2int16/sk_float_saturate2sm8`: 浮点到字体单位的安全转换

## 公共 API 函数

- `load(SkScalar, SkScalar)`: 加载字体文件，初始化字体管理器
- `draw(SkCanvas*)`: 修改字体数据并重新绘制字形
- `onFindClickHandler/onClick`: 拖拽控制点

## 内部实现细节

### updateSBIXData 核心函数
这是本文件最复杂的函数，直接操作字体文件的二进制数据：

1. **表定位**: 遍历 SFNT 表目录，找到 glyf、head、hhea、hmtx、loca、maxp、sbix 表
2. **SBIX 更新**: 读取/写入 strike 中指定字形的 `originOffsetX/Y`
3. **glyf 更新**: 读取/写入字形的 `xMin/yMin/xMax/yMax` 边界框
4. **轮廓点修改**: 解析 glyf Simple 字形的 flags、坐标数据，修改第一个点的位置
5. **hmtx 更新**: 修改左侧轴承值

### 字形坐标解析
手动解析 TrueType Simple 字形格式：
- 遍历 endPtsOfContours 确定点数
- 解析 flags 字节（含 Repeat 标志）
- 跟踪每个坐标的偏移和大小（0/1/2 字节）
- 正确处理 xShortVector、xIsSame 等标志位

### 多字体管理器对比
同时使用多个 `SkFontMgr` 实现渲染同一字形，对比不同解析器的行为：
- `ToolUtils::TestFontMgr()`: 测试字体管理器
- `SkFontMgr_New_Custom_Empty()`: FreeType 空字体管理器
- `SkFontMgr_New_Fontations_Empty()`: Fontations 字体管理器

## 依赖关系

- `src/sfnt/SkOTTable_*.h`: OpenType 表结构定义
- `src/sfnt/SkSFNTHeader.h`: SFNT 头部结构
- `include/core/SkFontMgr.h`: 字体管理器接口
- 条件编译: `SK_FONTMGR_FREETYPE_EMPTY_AVAILABLE`, `SK_FONTMGR_FONTATIONS_AVAILABLE`

## 设计模式与设计决策

- **即时字体修改**: 每次拖拽都复制并修改字体二进制数据，然后重新创建字体实例
- **多后端对比**: 同一修改同时在多个字体引擎中渲染，便于发现解析差异
- **UB 声明**: 代码注释明确指出存在未对齐指针的未定义行为（"Total hack"）

## 性能考量

- 每次拖拽都完整复制和解析字体数据，不适合大字体文件
- 使用 `fDirty` 标志避免不必要的更新
- 仅处理单个指定字形（kGlyphID = 2）

## 相关文件

- `src/sfnt/SkOTTable_sbix.h`: SBIX 表结构
- `src/sfnt/SkOTTable_glyf.h`: glyf 表结构
- `tools/viewer/ClickHandlerSlide.h`: 可点击基类
