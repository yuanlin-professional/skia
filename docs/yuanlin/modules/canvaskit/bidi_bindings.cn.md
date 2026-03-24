# bidi_bindings.cpp

> 源文件: modules/canvaskit/bidi_bindings.cpp

## 概述

`bidi_bindings.cpp` 是 CanvasKit 模块中用于支持双向文本(Bidirectional Text)处理的 C++ 绑定文件。该文件通过 Emscripten 将 Skia 的 Unicode BiDi 库暴露给 JavaScript,使 Web 应用能够正确处理包含从左到右(LTR)和从右到左(RTL)文字混合的文本,如阿拉伯语、希伯来语等。

该模块提供了三个核心功能:获取文本的 BiDi 区域划分、视觉顺序重排序,以及计算代码单元的属性标志。这些功能是正确渲染和编辑复杂文本的基础。

## 架构位置

```
skia/
├── modules/
│   ├── canvaskit/
│   │   ├── bidi_bindings.cpp    # 本文件 - BiDi C++ 绑定
│   │   ├── bidi.js              # BiDi JavaScript 封装
│   │   └── WasmCommon.h         # WASM 通用工具
│   └── skunicode/
│       ├── include/
│       │   ├── SkUnicode.h      # Unicode 基础接口
│       │   └── SkUnicode_bidi.h # BiDi 实现接口
│       └── src/
│           └── SkUnicode_bidi.cpp # BiDi 实现
```

该文件是 CanvasKit 文本处理系统的一部分,依赖 Skia 的 skunicode 模块提供 Unicode 和 BiDi 功能。

## 主要类与结构体

### BidiPlaceholder

```cpp
class BidiPlaceholder { };
```

**用途**: 空占位符类,用于在 Emscripten 绑定中创建 `Bidi` JavaScript 命名空间。该类本身不包含任何成员,仅作为类函数的容器。

### CodeUnitsPlaceholder

```cpp
class CodeUnitsPlaceholder { };
```

**用途**: 空占位符类,用于创建 `CodeUnits` JavaScript 命名空间,提供代码单元相关的功能。

### SkUnicode::BidiRegion

虽然定义在 `SkUnicode.h` 中,但在本文件中大量使用:

```cpp
struct BidiRegion {
    uint16_t start;  // 区域起始位置
    uint16_t end;    // 区域结束位置
    SkBidiIterator::Level level;  // BiDi 嵌套级别
};
```

**作用**: 描述文本中的一个 BiDi 区域,包含起始位置、结束位置和 BiDi 级别(奇数为 RTL,偶数为 LTR)。

## 公共 API 函数

### Bidi._getBidiRegions(jtext, dir)

**功能**: 分析文本并返回所有 BiDi 区域的划分信息。

**参数**:
- `jtext`: JSString - UTF-16 编码的文本
- `dir`: int - 文本的基础方向(1 = LTR, 0 = RTL)

**返回值**: JSArray - 包含 BiDi 区域信息的平坦数组,每3个元素为一组(start, end, level)

**实现流程**:
1. 将 JSString 转换为 `std::u16string`
2. 获取文本指针和字符数
3. 根据 dir 参数确定基础方向
4. 调用 `SkUnicode::forEachBidiRegion` 遍历所有 BiDi 区域
5. 将每个区域的 start、end、level 推入结果数组
6. 返回 JavaScript 数组

**使用场景**:
```javascript
// 分析包含英文和阿拉伯文的文本
const text = "Hello مرحبا World";
const regions = CanvasKit.Bidi._getBidiRegions(text, 1); // LTR
// 返回: [0, 5, 0, 6, 12, 1, 13, 18, 0]
// 表示三个区域:
// - [0,5): 级别0 (LTR) "Hello "
// - [6,12): 级别1 (RTL) "مرحبا"
// - [13,18): 级别0 (LTR) "World"
```

### Bidi._reorderVisual(runLevels, levelsCount)

**功能**: 根据 BiDi 级别数组计算从视觉顺序到逻辑顺序的映射。

**参数**:
- `runLevels`: WASMPointerU8 - 指向 BiDi 级别数组的 WASM 指针
- `levelsCount`: int - 级别数组的长度

**返回值**: JSArray - 包含逻辑索引的数组,表示视觉顺序对应的逻辑位置

**实现细节**:
1. 将 WASM 指针转换为 `SkUnicode::BidiLevel*` 类型
2. 创建输出向量并分配空间
3. 调用 `SkUnicode::reorderVisual` 执行重排序算法
4. 将结果转换为 JavaScript 数组返回

**应用场景**:
在文本编辑器中,当用户在可视位置点击时,需要将可视坐标转换为文本的逻辑位置以确定插入点。

**示例**:
```javascript
// 假设有三个文本块的级别: [0, 1, 0] (中间的是 RTL)
// 视觉顺序可能是: 块0, 块2的反向, 块1
const levels = new Uint8Array([0, 1, 0]);
const mapping = CanvasKit.Bidi._reorderVisual(levelsPtr, 3);
// 返回视觉到逻辑的映射
```

### CodeUnits._compute(jtext)

**功能**: 计算文本中每个代码单元的属性标志,用于断字、分词等文本处理。

**参数**:
- `jtext`: JSString - UTF-16 编码的文本

**返回值**: JSArray - 包含每个代码单元的标志位的 uint16 数组

**标志位含义** (定义在 `SkUnicode::CodeUnitFlags`):
- 是否为单词边界
- 是否为行边界
- 是否为软连字符位置
- 是否为字形簇边界
- 等等

**实现过程**:
1. 将 JSString 转换为 UTF-16 字符数组
2. 分配标志数组,大小与文本长度相同
3. 调用 `SkUnicode::computeCodeUnitFlags` 计算标志
4. 将标志数组转换为 JavaScript 数组返回

**使用场景**:
```javascript
const text = "Hello world";
const flags = CanvasKit.CodeUnits._compute(text);
// 每个字符位置的标志指示该位置是否可以换行、断字等
```

## 内部实现细节

### Unicode 实例管理

```cpp
static sk_sp<SkUnicode> getBidiUnicode() {
    static SkUnicode* unicode = SkUnicodes::Bidi::Make().release();
    return sk_ref_sp(unicode);
}
```

**设计特点**:
- **单例模式**: 使用静态变量确保 SkUnicode 实例只创建一次
- **延迟初始化**: 第一次调用时创建实例
- **智能指针管理**: 使用 `sk_sp` 进行引用计数管理,防止内存泄漏
- **线程安全**: 静态局部变量在 C++11 后保证线程安全的初始化

**性能优势**: 避免重复创建昂贵的 Unicode 数据结构。

### 字符串编码处理

**UTF-16 转换**:
```cpp
std::u16string textStorage = jtext.as<std::u16string>();
const char16_t* text = textStorage.data();
```

- JavaScript 字符串使用 UTF-16 编码
- Skia 的 BiDi 接口接受 `uint16_t*` 或 `char16_t*`
- 通过 Emscripten 的类型转换机制自动处理编码

### 数组转换辅助函数

**JSArrayFromBidiRegions**:
```cpp
void JSArrayFromBidiRegions(JSArray& array, std::vector<SkUnicode::BidiRegion>& regions) {
    for (auto region : regions) {
        array.call<void>("push", region.start);
        array.call<void>("push", region.end);
        array.call<void>("push", (int32_t)region.level);
    }
}
```

**设计考虑**:
- 使用平坦数组而非对象数组减少 JavaScript 对象创建开销
- 每个区域用3个连续元素表示,便于批量处理
- 在 JavaScript 端进一步封装为对象数组(由 `bidi.js` 完成)

### Lambda 表达式的使用

在 `_getBidiRegions` 中:
```cpp
getBidiUnicode()->forEachBidiRegion(
    (const uint16_t*)text, textCount, direction,
    [&](uint16_t start, uint16_t end, SkBidiIterator::Level level) {
        regions.emplace_back(start, end, level);
    }
);
```

**优点**:
- 回调函数内联,避免函数调用开销
- 可以捕获外部变量(如 `regions`)
- 代码清晰,易于理解

### 编译时条件检查

```cpp
#if defined(SK_UNICODE_BIDI_IMPLEMENTATION)
#include "modules/skunicode/include/SkUnicode_bidi.h"
#else
#error "SkUnicode bidi component is required but missing"
#endif
```

**目的**: 确保编译时包含了 BiDi 实现,否则产生编译错误,防止运行时失败。

## 依赖关系

### 核心依赖

**SkUnicode 模块**:
- `SkUnicode` - Unicode 处理基类
- `SkUnicode_bidi.h` - BiDi 功能的具体实现
- `SkBidiIterator` - BiDi 迭代器

**Emscripten**:
- `<emscripten/bind.h>` - JavaScript 绑定宏和类型
- `emscripten::val` - JavaScript 值封装
- `typed_memory_view` - 类型化内存视图

**标准库**:
- `<string>` - 字符串处理
- `<vector>` - 动态数组

### 数据流

```
JavaScript 文本
    ↓
JSString (Emscripten)
    ↓
std::u16string
    ↓
char16_t* / uint16_t*
    ↓
SkUnicode BiDi 算法
    ↓
std::vector<BidiRegion> / std::vector<int32_t>
    ↓
JSArray
    ↓
JavaScript 数组
```

### 模块间关系

- **bidi.js** 依赖本文件提供的 C++ 绑定函数
- **paragraph.js** 使用 BiDi 信息进行复杂文本布局
- **canvas.js** 在文本渲染时可能查询 BiDi 属性

## 设计模式与设计决策

### 单例模式

`getBidiUnicode()` 函数实现了线程安全的单例模式,确保 Unicode 数据结构只初始化一次,提高性能。

### 工厂模式

`SkUnicodes::Bidi::Make()` 是工厂方法,根据编译配置创建合适的 BiDi 实现。

### 适配器模式

整个文件作为适配器,将 Skia 的 C++ BiDi API 适配为 JavaScript 友好的接口:
- 处理类型转换
- 管理内存
- 转换数据格式

### 命名空间隔离

使用 `BidiPlaceholder` 和 `CodeUnitsPlaceholder` 创建 JavaScript 命名空间,避免全局污染:
```javascript
CanvasKit.Bidi.getBidiRegions(...)
CanvasKit.CodeUnits.compute(...)
```

### 分离关注点

- **本文件**: 负责 C++ 和 JavaScript 的绑定
- **bidi.js**: 负责 JavaScript API 的封装和易用性
- **SkUnicode**: 负责 BiDi 算法的实际实现

## 性能考量

### 内存分配优化

**预分配向量大小**:
```cpp
flags.resize(textCount);
```
预先分配所需的内存,避免动态扩容带来的多次重新分配。

**移动语义**:
使用 `emplace_back` 而非 `push_back` 减少不必要的拷贝。

### 数据传输优化

**平坦数组**: 使用平坦的数值数组而非对象数组传输数据,减少序列化开销。

**批量操作**: 一次性计算所有 BiDi 区域,而非多次调用。

### 算法效率

**Unicode BiDi 算法**: Skia 使用 Unicode 标准的 BiDi 算法,时间复杂度为 O(n),其中 n 是文本长度。

**缓存 Unicode 实例**: 单例模式避免重复初始化 Unicode 数据表(如字符属性表),这些表可能占用数兆字节内存。

### 最佳实践

1. **复用结果**: 如果文本内容不变,缓存 BiDi 区域计算结果
2. **增量更新**: 对于编辑操作,考虑只重新计算受影响的区域
3. **延迟计算**: 只在需要渲染或编辑时才计算 BiDi 信息
4. **批量处理**: 一次处理多个文本块,利用 CPU 缓存局部性

## 相关文件

### JavaScript 封装
- `modules/canvaskit/bidi.js` - BiDi 的 JavaScript 友好封装

### Skia Unicode 实现
- `modules/skunicode/include/SkUnicode.h` - Unicode 接口定义
- `modules/skunicode/include/SkUnicode_bidi.h` - BiDi 实现接口
- `modules/skunicode/src/SkUnicode_bidi.cpp` - BiDi 算法实现

### 相关模块
- `modules/canvaskit/paragraph.js` - 段落布局,使用 BiDi 信息
- `modules/canvaskit/WasmCommon.h` - WASM 通用类型和工具

### 测试文件
- `modules/canvaskit/tests/bidi_test.js` - BiDi 功能测试

### Unicode 标准参考
- Unicode Bidirectional Algorithm (UAX #9)
- Unicode Line Breaking Algorithm (UAX #14)
