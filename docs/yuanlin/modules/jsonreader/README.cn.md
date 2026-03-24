# jsonreader - JSON 读取器模块

## 概述

`modules/jsonreader` 是 Skia 的高性能 JSON 解析器模块,提供了一个快速但可能非完全兼容标准的 JSON 解析实现。该模块被 Skia 的多个子系统使用,特别是 skottie (Lottie 动画) 模块,用于解析 Lottie JSON 动画文件。

解析器的核心设计特点是使用固定大小 (64 位) 的不可变 `Value` 记录来表示所有 JSON 值。这种紧凑的设计使得值可以高效地存储和传递,同时通过门面类型 (Facade Types) 提供类型安全的访问接口。所有内存分配通过 `SkArenaAlloc` 竞技场分配器完成,极大减少了内存碎片和分配开销。

已知的设计折中包括:使用单精度浮点数表示数字 (而非双精度)、不进行字符串转义处理 (目前无使用者需要此功能)。这些选择是为了最大化解析速度而做的合理妥协。

`Value` 类型系统支持六种 JSON 类型: Null、Bool、Number (int32 或 float)、String (短字符串内联或外部存储)、Array 和 Object。短字符串 (7字节以内) 直接内联存储在 Value 的 8 字节空间中,避免额外的内存分配。Object 支持 `operator[]` 进行键查找,Array 和 Object 都支持迭代器遍历。

`DOM` 类是解析入口,接受 JSON 字符串,解析后返回根 `Value`。它内部持有 `SkArenaAlloc`,管理所有解析产生的内存。

## 架构图

```
+----------------------------------+
|           DOM (解析入口)          |
|  DOM(const char*, size_t)        |
|  root() --> const Value&         |
|  write(SkWStream*) --> 序列化    |
|  [内部持有 SkArenaAlloc]         |
+----------------------------------+
              |
              v
+----------------------------------+
|     Value (64位不可变记录)        |
|  Tag (低3位): 类型标识            |
|  +-- NullValue                   |
|  +-- BoolValue    (inline)       |
|  +-- NumberValue  (int32/float)  |
|  +-- StringValue  (inline/ptr)   |
|  +-- ArrayValue   (ptr->数组)    |
|  +-- ObjectValue  (ptr->成员)    |
+----------------------------------+
              |
     +--------+--------+
     |                  |
     v                  v
+----------+    +------------+
| VectorValue  | Member       |
| (Array/Obj   | { StringValue|
|  的公共基)   |   fKey;      |
| size/begin/  |   Value      |
| end/[]       |   fValue; }  |
+--------------+  +-----------+

内存布局 (小端序):
+---+---+---+---+---+---+---+---+
|TAG|     payload (7 bytes)      |  ShortString (内联)
+---+---+---+---+---+---+---+---+
|TAG|   (unused)  |  int32/float |  Number/Bool (内联)
+---+---+---+---+---+---+---+---+
|TAG|     pointer (61 bits)      |  String/Array/Object (64位指针)
+---+---+---+---+---+---+---+---+
```

## 目录结构

```
modules/jsonreader/
+-- BUILD.gn             # GN 构建配置
+-- BUILD.bazel          # Bazel 构建配置
+-- jsonreader.gni       # GNI 源文件列表
+-- SkJSONReader.h       # 公共 API (Value 类型系统 + DOM)
+-- SkJSONReader.cpp     # 解析器实现
```

## 关键类与函数

| 类/函数 | 文件 | 说明 |
|---------|------|------|
| `DOM` | `SkJSONReader.h` | JSON 解析入口,持有 SkArenaAlloc 管理所有内存 |
| `DOM::root()` | `SkJSONReader.h` | 返回解析后的根 Value |
| `DOM::write()` | `SkJSONReader.h` | 将 DOM 序列化写入 SkWStream |
| `Value` | `SkJSONReader.h` | 64位不可变值记录,所有 JSON 类型的基类 |
| `Value::getType()` | `SkJSONReader.h` | 返回值的 JSON 类型 |
| `Value::is<T>()` | `SkJSONReader.h` | 类型检查: `v.is<ArrayValue>()` |
| `Value::as<T>()` | `SkJSONReader.h` | 无保护类型转换 (需先 is 检查) |
| `Value::operator[](key)` | `SkJSONReader.h` | 流式键查找: `v["foo"]["bar"]` |
| `NullValue` | `SkJSONReader.h` | null 值 |
| `BoolValue` | `SkJSONReader.h` | 布尔值,`**bv` 取值 |
| `NumberValue` | `SkJSONReader.h` | 数字值 (int32 或 float),`**nv` 返回 double |
| `StringValue` | `SkJSONReader.h` | 字符串值,begin()/end()/size()/str() |
| `ArrayValue` | `SkJSONReader.h` | JSON 数组,支持 size()/begin()/end()/operator[] |
| `ObjectValue` | `SkJSONReader.h` | JSON 对象,支持 operator[](key) 键查找 |
| `ObjectValue::writable()` | `SkJSONReader.h` | 按键获取可写值引用 |
| `Member` | `SkJSONReader.h` | 对象成员 { StringValue fKey; Value fValue; } |

## 依赖关系

- **Skia Core**: `SkTypes`, `SkString`, `SkData`, `SkStream`
- **Skia 内部**: `SkArenaAlloc` (竞技场分配器), `SkNoncopyable`, `SkParse`, `SkUTF`
- **被依赖**: `modules/skottie` (Lottie 动画 JSON 解析), 其他需要 JSON 解析的 Skia 模块

## 设计模式分析

1. **门面模式 (Facade)**: `Value` 是不透明的 64 位记录,通过 `NullValue`/`BoolValue`/`NumberValue`/`StringValue`/`ArrayValue`/`ObjectValue` 等门面类型提供类型安全的访问接口。

2. **享元模式 (Flyweight)**: 所有值共享固定的 8 字节大小,短字符串内联存储避免额外分配。`SkArenaAlloc` 进一步减少了内存分配开销。

3. **空对象模式**: 查找不存在的键时返回 `NullValue` 而非 nullptr,避免空指针检查,支持链式查找 `v["a"]["b"]["c"]`。

4. **标记指针 (Tagged Pointer)**: 在 64 位平台上,利用指针的低 3 位存储类型标签,在 Value 的 8 字节空间中同时容纳类型信息和指针数据。

5. **竞技场分配 (Arena Allocation)**: `DOM` 内部使用 `SkArenaAlloc` 一次性分配所有解析产生的字符串和数组/对象数据,DOM 析构时统一释放。

## 数据流

```
JSON 字符串 (const char*, size_t)
       |
       v
DOM 构造函数
  - 词法分析 (token 识别)
  - 递归下降解析
  - SkArenaAlloc 分配存储
       |
       v
DOM::root() --> const Value&
       |
       +-- v.is<ObjectValue>() ? v.as<ObjectValue>()["key"]
       |
       +-- v.is<ArrayValue>() ? for (auto& item : v.as<ArrayValue>())
       |
       +-- v.is<NumberValue>() ? *v.as<NumberValue>() --> double
       |
       +-- v.is<StringValue>() ? v.as<StringValue>().str() --> string_view
       |
       v
DOM::write(stream) --> JSON 序列化输出
```

## 相关文档与参考

- Lottie 动画模块 (主要使用者): `modules/skottie/`
- SkArenaAlloc: `src/base/SkArenaAlloc.h`
- JSON 规范: https://www.json.org/
