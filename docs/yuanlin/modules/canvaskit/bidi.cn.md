# bidi.js

> 源文件: modules/canvaskit/bidi.js

## 概述

`bidi.js` 是 CanvasKit 模块中双向文本(Bidirectional Text)处理的 JavaScript 封装层。该文件将 `bidi_bindings.cpp` 提供的底层 C++ 绑定函数封装为更易用的 JavaScript API,提供友好的数据格式转换和 API 接口。

主要功能包括:获取文本的 BiDi 区域划分、执行视觉顺序到逻辑顺序的重排,以及计算代码单元的属性标志。这些功能对于正确渲染和编辑包含从左到右(LTR)和从右到左(RTL)混合文字的文本至关重要,如阿拉伯语、希伯来语、波斯语等。

## 架构位置

```
skia/
├── modules/
│   └── canvaskit/
│       ├── bidi.js              # 本文件 - JavaScript 封装
│       ├── bidi_bindings.cpp    # C++ 绑定层
│       ├── paragraph.js         # 使用 BiDi 的段落布局
│       └── WasmCommon.h         # WASM 工具
```

该文件位于 CanvasKit 文本处理栈的中间层,在 C++ 绑定和用户 API 之间提供适配和转换。

## 主要类与结构体

### BidiRegion 对象

```javascript
{
  'start': number,  // 区域起始位置(字符索引)
  'end': number,    // 区域结束位置(字符索引)
  'level': number   // BiDi 嵌套级别(奇数=RTL,偶数=LTR)
}
```

**用途**: 描述文本中的一个 BiDi 区域,表示具有相同方向的连续文本段。

### BidiIndex 对象

```javascript
{
  'index': number  // 逻辑索引
}
```

**用途**: 表示视觉顺序到逻辑顺序的映射关系。

### CodeUnitFlags 对象

```javascript
{
  'flags': number  // 代码单元属性标志位
}
```

**用途**: 表示文本中每个代码单元的属性,如是否为单词边界、行边界等。

### CanvasKit.TextDirection 枚举

```javascript
CanvasKit.TextDirection = {
  LTR: { value: 1 },  // 从左到右
  RTL: { value: 0 },  // 从右到左
}
```

**用途**: 定义文本的基础方向。

## 公共 API 函数

### CanvasKit.Bidi.getBidiRegions(text, textDirection)

**功能**: 分析文本并返回所有 BiDi 区域的数组。

**参数**:
- `text`: string - 要分析的文本
- `textDirection`: CanvasKit.TextDirection - 文本的基础方向(LTR 或 RTL)

**返回值**: Array<BidiRegion> - BiDi 区域对象的数组

**实现细节**:
```javascript
let dir = textDirection === CanvasKit.TextDirection.LTR ? 1 : 0;
let int32Array = CanvasKit.Bidi._getBidiRegions(text, dir);
return Int32ArrayToBidiRegions(int32Array);
```

1. 将 TextDirection 枚举转换为数值(1=LTR, 0=RTL)
2. 调用底层 C++ 绑定函数 `_getBidiRegions`
3. 将返回的 Int32Array 转换为 BidiRegion 对象数组

**使用示例**:
```javascript
const text = "Hello مرحبا World";
const regions = CanvasKit.Bidi.getBidiRegions(
  text,
  CanvasKit.TextDirection.LTR
);
// 返回:
// [
//   { start: 0, end: 6, level: 0 },   // "Hello "
//   { start: 6, end: 11, level: 1 },  // "مرحبا"
//   { start: 11, end: 17, level: 0 }  // " World"
// ]
```

### CanvasKit.Bidi.reorderVisual(visualRuns)

**功能**: 根据视觉顺序的 BiDi 级别数组,计算对应的逻辑顺序索引。

**参数**:
- `visualRuns`: Uint8Array 或 Array - BiDi 级别的数组

**返回值**: Array<BidiIndex> - 包含逻辑索引的对象数组

**实现细节**:
```javascript
let vPtr = copy1dArray(visualRuns, 'HEAPU8');
let int32Array = CanvasKit.Bidi._reorderVisual(vPtr, visualRuns && visualRuns.length || 0);
freeArraysThatAreNotMallocedByUsers(vPtr, visualRuns);
return Int32ArrayToBidiIndexes(int32Array);
```

1. 将 JavaScript 数组复制到 WASM 堆(`copy1dArray`)
2. 调用 C++ 绑定函数 `_reorderVisual`
3. 释放临时内存(`freeArraysThatAreNotMallocedByUsers`)
4. 将结果转换为 BidiIndex 对象数组

**应用场景**: 文本编辑器中将光标的视觉位置转换为文本的逻辑位置。

**使用示例**:
```javascript
const levels = new Uint8Array([0, 1, 1, 0]); // LTR, RTL, RTL, LTR
const mapping = CanvasKit.Bidi.reorderVisual(levels);
// 返回视觉到逻辑的映射
```

### CanvasKit.CodeUnits.compute(text)

**功能**: 计算文本中每个代码单元的属性标志。

**参数**:
- `text`: string - 要分析的文本

**返回值**: Array<CodeUnitFlags> - 代码单元标志对象的数组,长度等于文本长度

**实现细节**:
```javascript
let uint16Array = CanvasKit.CodeUnits._compute(text);
return Int16ArrayToCodeUnitsFlags(uint16Array);
```

1. 调用 C++ 绑定函数 `_compute`
2. 将返回的 Uint16Array 转换为 CodeUnitFlags 对象数组

**标志位含义**:
- 单词边界标志
- 行边界标志
- 字形簇边界标志
- 软连字符位置标志

**使用示例**:
```javascript
const text = "Hello, world!";
const flags = CanvasKit.CodeUnits.compute(text);
// flags[6].flags 会指示逗号后是否可以换行
```

## 内部实现细节

### 数组转换辅助函数

#### Int32ArrayToBidiRegions(int32Array)

**功能**: 将平坦的 Int32Array 转换为 BidiRegion 对象数组。

**输入格式**: `[start0, end0, level0, start1, end1, level1, ...]`

**输出格式**: `[{start, end, level}, {start, end, level}, ...]`

**实现**:
```javascript
function Int32ArrayToBidiRegions(int32Array) {
  if (!int32Array || !int32Array.length) {
    return [];
  }
  let ret = [];
  for (let i = 0; i < int32Array.length; i+=3) {
    let start = int32Array[i];
    let end = int32Array[i+1];
    let level = int32Array[i+2];
    ret.push({'start': start, 'end': end, 'level': level});
  }
  return ret;
}
```

**设计考虑**:
- 每3个元素为一组,遍历时步长为3
- 空数组或 null 返回空数组,避免错误
- 创建新对象,提供语义化的属性名

#### Int32ArrayToBidiIndexes(int32Array)

**功能**: 将 Int32Array 转换为 BidiIndex 对象数组。

**实现**:
```javascript
function Int32ArrayToBidiIndexes(int32Array) {
  if (!int32Array || !int32Array.length) {
    return [];
  }
  let ret = [];
  for (let i = 0; i < int32Array.length; i+=1) {
    let index = int32Array[i];
    ret.push({'index': index});
  }
  return ret;
}
```

**特点**: 每个元素对应一个索引值,步长为1。

#### Int16ArrayToCodeUnitsFlags(int16Array)

**功能**: 将 Uint16Array 转换为 CodeUnitFlags 对象数组。

**实现**:
```javascript
function Int16ArrayToCodeUnitsFlags(int16Array) {
  if (!int16Array || !int16Array.length) {
    return [];
  }
  let ret = [];
  for (let i = 0; i < int16Array.length; i+=1) {
    let index = int16Array[i];
    ret.push({'flags': index});
  }
  return ret;
}
```

### TextDirection 枚举初始化

```javascript
if (!CanvasKit['TextDirection']) {
  CanvasKit['TextDirection'] = {
    LTR: { value: 1 },
    RTL: { value: 0 },
  }
}
```

**防御性检查**: 如果 TextDirection 已存在(可能由其他模块定义),不覆盖。

**值的设计**:
- LTR = 1: 匹配 Unicode BiDi 算法中的左到右方向
- RTL = 0: 匹配右到左方向

### 内存管理

**copy1dArray**: 将 JavaScript 数组复制到 WASM 堆,返回指针。

**freeArraysThatAreNotMallocedByUsers**: 释放由 `copy1dArray` 分配的内存,但不释放用户通过 `CanvasKit.Malloc` 分配的内存。

**原因**: 避免内存泄漏,同时保留用户管理的内存。

## 依赖关系

### C++ 绑定依赖

**CanvasKit.Bidi._getBidiRegions**: C++ 函数,返回 Int32Array。

**CanvasKit.Bidi._reorderVisual**: C++ 函数,接收 WASM 指针和长度。

**CanvasKit.CodeUnits._compute**: C++ 函数,返回 Uint16Array。

### CanvasKit 工具函数

**copy1dArray**: 复制数组到 WASM 堆。

**freeArraysThatAreNotMallocedByUsers**: 释放临时内存。

### 数据流

```
JavaScript 字符串/数组
    ↓
copy1dArray (如需要)
    ↓
C++ 绑定函数
    ↓
TypedArray (Int32Array/Uint16Array)
    ↓
转换辅助函数
    ↓
JavaScript 对象数组
```

## 设计模式与设计决策

### 适配器模式

该文件充当适配器,将 C++ 的平坦数组 API 适配为 JavaScript 友好的对象数组 API。

**优点**:
- JavaScript 代码可以使用 `region.start` 而非 `array[i*3]`
- 更好的类型安全和自动补全
- 更符合 JavaScript 编程习惯

### 外观模式

提供简化的高层 API,隐藏底层的复杂性:
- 内存管理细节
- 数据格式转换
- C++ 函数调用

### 防御性编程

**空值检查**: 所有转换函数都检查输入是否为空。

**条件初始化**: TextDirection 枚举只在不存在时才创建。

### 关注点分离

- **bidi_bindings.cpp**: C++/JavaScript 互操作
- **bidi.js**: 数据格式适配和 API 封装
- **paragraph.js**: 使用 BiDi 信息进行布局

## 性能考量

### 对象创建开销

**平坦数组 vs 对象数组**:
- C++ 返回平坦数组,传输效率高
- JavaScript 转换为对象数组,便于使用
- 对象创建有开销,但提高可读性

**权衡**: 对于大量文本,考虑缓存结果或使用平坦数组。

### 内存复制

**copy1dArray**: 将数组复制到 WASM 堆,有一定开销。

**优化**: 对于频繁调用,考虑复用内存或使用 `CanvasKit.Malloc` 预分配。

### 数组迭代

转换函数使用简单的 for 循环,性能良好。现代 JavaScript 引擎会优化这类代码。

### 最佳实践

1. **缓存结果**: 对于不变的文本,缓存 BiDi 分析结果
2. **批量处理**: 一次处理多个文本块,减少函数调用开销
3. **按需计算**: 只在需要 BiDi 信息时才调用相关函数
4. **复用内存**: 对于频繁调用,考虑使用 CanvasKit.Malloc 预分配内存

## 相关文件

### C++ 绑定
- `modules/canvaskit/bidi_bindings.cpp` - C++ 绑定实现

### Skia Unicode 模块
- `modules/skunicode/include/SkUnicode.h` - Unicode 接口
- `modules/skunicode/include/SkUnicode_bidi.h` - BiDi 实现

### 使用 BiDi 的模块
- `modules/canvaskit/paragraph.js` - 段落布局,使用 BiDi 区域信息
- `modules/canvaskit/canvas.js` - Canvas API,可能使用 BiDi 进行文本渲染

### 工具函数
- `modules/canvaskit/WasmCommon.h` - WASM 通用工具
- `modules/canvaskit/helper.js` - 辅助函数(如 copy1dArray)

### 测试文件
- `modules/canvaskit/tests/bidi_test.js` - BiDi 功能测试

### 标准参考
- Unicode Bidirectional Algorithm (UAX #9)
- Unicode Standard Annex #9: https://unicode.org/reports/tr9/
