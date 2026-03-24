# CanvasKit Font - 字体与文本渲染 JavaScript 绑定

> 源文件: `modules/canvaskit/font.js`

## 概述

font.js 为 CanvasKit 提供了字体相关的 JavaScript 高级绑定，涵盖文本绘制、字形查询、字体管理、文本路径布局（TextBlob on Path）等功能。该文件是 JavaScript 字符串/字体操作与 Skia C++ 字体引擎之间的桥梁，处理了 UTF-8 编码转换、字形 ID 数组的 WASM 内存管理以及沿路径布局文本的复杂几何计算。

## 架构位置

该文件属于 CanvasKit 的 JavaScript 绑定层，通过 `_extraInitializations` 机制注册。它扩展了 Canvas、Font、FontMgr、Typeface、TextBlob 等多个类的原型。

```
用户代码
  └── font.js 公共 API
        ├── Canvas.drawText / drawGlyphs
        ├── Font.getGlyphBounds / getGlyphIDs / getGlyphWidths / getGlyphIntercepts
        ├── FontMgr.FromData
        ├── Typeface.MakeTypefaceFromData / getGlyphIDs
        ├── TextBlob.MakeFromText / MakeOnPath / MakeFromRSXform / MakeFromGlyphs
        └── MallocGlyphIDs
              └── C++ Emscripten 绑定
                    └── Skia C++ (SkFont, SkFontMgr, SkTypeface, SkTextBlob)
```

## 主要类与结构体

本文件不定义新类，而是扩展以下已有类的原型：

### Canvas 扩展
- `drawText()` - 文本绘制
- `drawGlyphs()` - 字形级绘制

### Font 扩展
- `getGlyphBounds()` - 字形边界
- `getGlyphIDs()` - 字符到字形映射
- `getGlyphWidths()` - 字形宽度
- `getGlyphIntercepts()` - 字形与水平线的交点

### FontMgr 扩展
- `FromData()` - 从字体数据创建 FontMgr

### Typeface 扩展
- `MakeTypefaceFromData()` - 从字体数据创建 Typeface
- `getGlyphIDs()` - Typeface 级字形查询

### TextBlob 扩展
- `MakeFromText()` - 从字符串创建
- `MakeOnPath()` - 沿路径布局文本
- `MakeFromRSXform()` - 从旋转-缩放变换创建
- `MakeFromRSXformGlyphs()` - 从字形和变换创建
- `MakeFromGlyphs()` - 从字形数组创建

## 公共 API 函数

### `Canvas.prototype.drawText(str, x, y, paint, font)`
- **功能**：在指定位置绘制文本字符串
- **实现**：UTF-8 编码 -> WASM 堆分配 -> `_drawSimpleText` -> 释放

### `Canvas.prototype.drawGlyphs(glyphs, positions, x, y, font, paint)`
- **功能**：在指定位置绘制字形数组
- **验证**：`glyphs.length * 2 <= positions.length`（每个字形需要 x,y 两个坐标）
- **内存**：使用 HEAPU16（字形 ID）和 HEAPF32（位置）

### `Font.prototype.getGlyphBounds(glyphs, paint, optionalOutputArray)`
- **功能**：获取每个字形的边界矩形（left, top, right, bottom）
- **返回**：Float32Array，长度为 `glyphs.length * 4`
- **优化**：支持 `optionalOutputArray` 避免每次分配新数组

### `Font.prototype.getGlyphIDs(str, numGlyphIDs, optionalOutputArray)`
- **功能**：将字符串转换为字形 ID 数组
- **实现**：UTF-8 编码，去掉 null 终止符长度，返回 Uint16Array

### `Font.prototype.getGlyphWidths(glyphs, paint, optionalOutputArray)`
- **功能**：获取每个字形的推进宽度
- **返回**：Float32Array，每个字形一个宽度值

### `Font.prototype.getGlyphIntercepts(glyphs, positions, top, bottom)`
- **功能**：获取字形轮廓与水平带的交点坐标

### `FontMgr.FromData(...fontDataArrays)`
- **功能**：从一个或多个字体数据 ArrayBuffer 创建 FontMgr
- **参数**：支持多个 ArrayBuffer 参数或单个数组参数
- **内存**：字体数据拷贝到 WASM 堆，FontMgr 获取所有权

### `Typeface.MakeTypefaceFromData(fontData)`
- **功能**：从 ArrayBuffer 创建 Typeface
- **兼容**：`MakeFreeTypeFaceFromData` 作为旧名称别名保留

### `TextBlob.MakeOnPath(str, path, font, initialOffset)`
- **功能**：沿路径布局文本
- **算法**：
  1. 获取字形 ID 和宽度
  2. 使用 `ContourMeasureIter` 遍历路径轮廓
  3. 计算每个字形沿路径的位置和切线方向
  4. 构建 RSXform（旋转-缩放-位移变换）数组
  5. 调用 `MakeFromRSXform` 创建最终 TextBlob
- **边界处理**：路径长度不足时截断字符串

### `TextBlob.MakeFromRSXform(str, rsxForms, font)`
- **功能**：使用 RSXform 变换数组创建文本块

### `TextBlob.MakeFromGlyphs(glyphs, font)`
- **功能**：从字形 ID 数组创建文本块

### `CanvasKit.MallocGlyphIDs(numGlyphIDs)`
- **功能**：分配 Uint16Array 类型的字形 ID 缓冲区
- **说明**：辅助函数，确保使用正确的类型（当前为 16 位）

## 内部实现细节

### UTF-8 编码处理

所有字符串操作都经过 Emscripten 的 UTF-8 工具：
```javascript
var strLen = lengthBytesUTF8(str);
var strPtr = CanvasKit._malloc(strLen + 1);  // +1 for null terminator
stringToUTF8(str, strPtr, strLen + 1);
```

### 内存管理模式

两种模式处理 WASM 堆内存：
1. **临时分配**：函数内 `_malloc` -> 使用 -> `_free`（如 drawText）
2. **用户管理**：`freeArraysThatAreNotMallocedByUsers()` 仅释放非 Malloc 分配的数组

### 可选输出数组

多个函数支持 `optionalOutputArray` 参数：
```javascript
if (optionalOutputArray) {
    optionalOutputArray.set(result);
    CanvasKit._free(ptr);
    return optionalOutputArray;
}
var rv = TypedArray.from(result);
CanvasKit._free(ptr);
return rv;
```

### MakeOnPath 几何计算

沿路径布局的核心算法：
1. 逐字形累加距离 `dist += width/2`
2. 当距离超过当前轮廓长度时切换到下一轮廓
3. 使用 `getPosTan` 获取路径上的位置 (cx, cy) 和切线 (cosT, sinT)
4. 计算调整后的位置使字形居中于路径点
5. 构建 RSXform：`[cosT, sinT, adjustedX, adjustedY]`

## 依赖关系

- **Emscripten 工具**：`lengthBytesUTF8`、`stringToUTF8`
- **CanvasKit 内部**：`copy1dArray`、`freeArraysThatAreNotMallocedByUsers`、`wasMalloced`、`nullptr`
- **C++ 绑定**：`_drawSimpleText`、`_drawGlyphs`、`_getGlyphWidthBounds`、`_getGlyphIDs`、`_getGlyphIntercepts`、`_MakeTypefaceFromData`、`_fromData`、`_MakeFromText`、`_MakeFromRSXform`、`_MakeFromRSXformGlyphs`、`_MakeFromGlyphs`
- **CanvasKit API**：`ContourMeasureIter`、`Malloc`

## 设计模式与设计决策

1. **可选输出数组**：避免频繁的 TypedArray 分配，对动画循环中的性能至关重要。

2. **字形 ID 类型抽象**：`MallocGlyphIDs` 封装了当前 16 位字形 ID 的类型选择，为未来可能的 32 位迁移预留了修改点。

3. **MakeOnPath 纯 JS 实现**：沿路径布局完全在 JavaScript 侧实现，利用已有的 ContourMeasure API，避免了额外的 C++ 绑定。

4. **向后兼容**：`MakeFreeTypeFaceFromData` 作为已弃用名称保留，确保旧代码不会立即崩溃。

## 性能考量

- 每次 `drawText` 调用涉及一次 UTF-8 编码和两次 WASM 堆操作（malloc/free）
- `getGlyphBounds` / `getGlyphWidths` 支持预分配输出数组，避免 GC 压力
- `MakeOnPath` 的 `ContourMeasure` 迭代器在使用后手动 `delete()`，防止 WASM 内存泄漏
- 字形 ID 使用 HEAPU16（2 字节/ID），位置使用 HEAPF32（4 字节/值）
- `FontMgr.FromData` 中字体数据拷贝到 WASM 堆后由 C++ 管理，避免双重释放

## 相关文件

- `modules/canvaskit/externs.js` - Font、TextBlob、Typeface 等外部声明
- `modules/canvaskit/canvaskit_bindings.cpp` - C++ 字体绑定
- `modules/canvaskit/interface.js` - CanvasKit 通用接口
- `modules/canvaskit/util.js` - nullptr 常量定义
