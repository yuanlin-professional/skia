# SkPathDump

> 源文件
> - src/core/SkPathDump.cpp

## 概述

`SkPathDump.cpp` 实现了 Skia 路径的调试和序列化输出功能,提供了将路径转换为可读字符串的能力。该模块支持两种输出格式:十进制浮点数和十六进制浮点数表示,主要用于调试、测试验证和路径数据导出。

核心功能包括:`SkPath::dump()` 方法将路径输出为 C++ 代码形式,`SkPathBuilder::dumpToString()` 方法将构建器状态转换为字符串。这些工具在路径分析、问题诊断和单元测试中发挥重要作用。

## 架构位置

`SkPathDump` 位于 Skia 路径系统的调试支持层:

```
include/core/
├── SkPath (路径主类)
│   └── dump() 方法
└── SkPathBuilder (路径构建器)
    └── dump() / dumpToString() 方法

src/core/
├── SkPathDump.cpp (调试输出实现) ← 当前组件
├── SkPathIter (路径迭代器)
└── SkStringUtils (字符串工具)
```

输出流程:
```
SkPath / SkPathBuilder
    ↓
SkPathIter (遍历动词和点)
    ↓
dump_iter (格式化输出)
    ↓
SkString / SkWStream
```

## 主要类与结构体

该文件不定义类,仅实现方法和辅助函数。

**全局常量**:

```cpp
char const * const gFillTypeStrs[] = {
    "Winding",
    "EvenOdd",
    "InverseWinding",
    "InverseEvenOdd",
};

constexpr float kSentinelConicWeight = -12345;
```

**辅助函数**:

| 函数 | 说明 |
|------|------|
| append_params | 格式化动词参数 |
| dump_iter | 遍历并格式化路径 |

## 公共 API 函数

### SkPath::dump

```cpp
void SkPath::dump(SkWStream* wStream, bool dumpAsHex) const;
```

**参数**:
- `wStream`: 输出流(nullptr 表示输出到 SkDebugf)
- `dumpAsHex`: true 使用十六进制,false 使用十进制

**输出格式**:
```cpp
path.setFillType(SkPathFillType::kWinding);
path.moveTo(0, 0);
path.lineTo(100, 0);
path.lineTo(100, 100);
path.close();
```

### SkPathBuilder::dumpToString

```cpp
SkString SkPathBuilder::dumpToString(DumpFormat format) const;
```

**参数**:
- `format`: `DumpFormat::kDecimal` 或 `DumpFormat::kHex`

**返回值**:
包含路径构建代码的字符串

**输出格式**:
```cpp
SkPathBuilder(SkPathFillType::kWinding)
.moveTo(0, 0)
.lineTo(100, 0)
.lineTo(100, 100)
.close()
```

### SkPathBuilder::dump

```cpp
void SkPathBuilder::dump(DumpFormat format) const;
void SkPathBuilder::dump() const;
```

直接输出到 `SkDebugf`,等价于:
```cpp
SkDebugf("%s", dumpToString(format).c_str());
```

## 内部实现细节

### append_params 函数

格式化动词的参数。

**函数签名**:

```cpp
static void append_params(SkString* str,
                          const char label[],
                          SkSpan<const SkPoint> pts,
                          SkScalarAsStringType strType,
                          bool useSemicolon,
                          SkScalar conicWeight = kSentinelConicWeight);
```

**实现逻辑**:

```cpp
static void append_params(...) {
    str->append(label);  // 如 ".moveTo"
    str->append("(");

    // 输出点坐标(交替 x, y)
    const SkScalar* values = &pts[0].fX;
    size_t count = pts.size() * 2;
    for (size_t i = 0; i < count; ++i) {
        SkAppendScalar(str, values[i], strType);
        if (i < count - 1) {
            str->append(", ");
        }
    }

    // 输出圆锥权重(如果有)
    if (conicWeight != kSentinelConicWeight) {
        str->append(", ");
        SkAppendScalar(str, conicWeight, strType);
    }

    str->append(useSemicolon ? ");" : ")");

    // 十六进制模式下追加十进制注释
    if (kHex_SkScalarAsStringType == strType) {
        str->append("  // ");
        for (size_t i = 0; i < count; ++i) {
            SkAppendScalarDec(str, values[i]);
            if (i < count - 1) {
                str->append(", ");
            }
        }
        if (conicWeight >= 0) {
            str->append(", ");
            SkAppendScalarDec(str, conicWeight);
        }
    }
    str->append("\n");
}
```

### dump_iter 函数

遍历路径迭代器并格式化输出。

**函数签名**:

```cpp
static void dump_iter(SkPathIter iter,
                      SkString* builder,
                      const char cmdPrefix[],
                      SkScalarAsStringType strType,
                      bool useSemicolon,
                      std::function<void()> postVerbProc);
```

**实现逻辑**:

```cpp
static void dump_iter(...) {
    while (auto rec = iter.next()) {
        SkString cmd(cmdPrefix);  // "path" 或 ""
        SkSpan<const SkPoint> pts;
        float cw = kSentinelConicWeight;

        switch (rec->fVerb) {
            case SkPathVerb::kMove:
                cmd.append(".moveTo");
                pts = {&rec->fPoints[0], 1};
                break;
            case SkPathVerb::kLine:
                cmd.append(".lineTo");
                pts = {&rec->fPoints[1], 1};
                break;
            case SkPathVerb::kQuad:
                cmd.append(".quadTo");
                pts = {&rec->fPoints[1], 2};
                break;
            case SkPathVerb::kConic:
                cmd.append(".conicTo");
                pts = {&rec->fPoints[1], 2};
                cw = rec->conicWeight();
                break;
            case SkPathVerb::kCubic:
                cmd.append(".cubicTo");
                pts = {&rec->fPoints[1], 3};
                break;
            case SkPathVerb::kClose:
                cmd.append(".close()");
                if (useSemicolon) {
                    cmd.append(";");
                }
                cmd.append("\n");
                builder->append(cmd.c_str());
                break;
        }

        // 非 Close 动词格式化参数
        if (pts.size()) {
            append_params(builder, cmd.c_str(), pts, strType, useSemicolon, cw);
        }

        postVerbProc();  // 回调(如刷新输出)
    }
}
```

### SkPath::dump 实现

```cpp
void SkPath::dump(SkWStream* wStream, bool dumpAsHex) const {
    SkScalarAsStringType asType = dumpAsHex
        ? kHex_SkScalarAsStringType
        : kDec_SkScalarAsStringType;

    SkString builder;
    builder.printf("path.setFillType(SkPathFillType::k%s);\n",
                   gFillTypeStrs[(int)this->getFillType()]);

    dump_iter(this->iter(), &builder, "path", asType, true, [&]() {
        if (!wStream && builder.size()) {
            // 无流时逐步输出到 SkDebugf
            SkDebugf("%s", builder.c_str());
            builder.reset();
        }
    });

    if (wStream) {
        wStream->writeText(builder.c_str());
    }
}
```

**关键设计**:
- 无流时增量输出(避免大字符串)
- 有流时批量写入

### SkPathBuilder::dumpToString 实现

```cpp
SkString SkPathBuilder::dumpToString(DumpFormat format) const {
    SkScalarAsStringType asType = format == DumpFormat::kHex
        ? kHex_SkScalarAsStringType
        : kDec_SkScalarAsStringType;

    SkString builder;
    builder.printf("SkPathBuilder(SkPathFillType::k%s)\n",
                   gFillTypeStrs[(int)this->fillType()]);

    dump_iter(this->iter(), &builder, "", asType, false, [](){});

    return builder;
}
```

**差异**:
- 构造函数风格输出
- 无分号(链式调用风格)
- 无命令前缀(直接 `.moveTo` 而非 `path.moveTo`)

### 十六进制输出示例

```cpp
path.moveTo(0x42c80000, 0x00000000);  // 100, 0
```

**用途**:
- 精确的位级表示
- 浮点数精度验证
- 跨平台数值一致性检查

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkPath | 路径对象 |
| SkPathBuilder | 路径构建器 |
| SkPathIter | 路径迭代 |
| SkString | 字符串构建 |
| SkStream | 输出流 |
| SkStringUtils | 数值格式化 |
| SkSpan | 数组视图 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| 调试工具 | 路径可视化 |
| 单元测试 | 路径验证 |
| 问题诊断 | 路径分析 |

## 设计模式与设计决策

### 回调模式

`dump_iter` 使用 `std::function` 回调:
```cpp
dump_iter(..., std::function<void()> postVerbProc);
```
- 灵活的后处理
- 支持增量输出
- 无副作用分离

### 格式化参数化

使用枚举控制输出格式:
```cpp
enum SkScalarAsStringType {
    kDec_SkScalarAsStringType,
    kHex_SkScalarAsStringType,
};
```
- 统一的格式控制
- 易于扩展新格式

### 哨兵值

使用特殊值表示无权重:
```cpp
constexpr float kSentinelConicWeight = -12345;
```
- 简化函数签名
- 避免 optional 开销

### 链式调用风格

`SkPathBuilder` 输出无分号:
```cpp
SkPathBuilder()
    .moveTo(0, 0)
    .lineTo(100, 0)
```
符合流式接口习惯。

### 增量输出

无流时逐动词输出:
```cpp
if (!wStream && builder.size()) {
    SkDebugf("%s", builder.c_str());
    builder.reset();
}
```
避免大路径内存峰值。

## 性能考量

### 仅调试使用

该模块仅用于调试:
- 不在关键路径
- 无需极致优化
- 可读性优先

### 增量输出优化

无流模式逐步输出:
- 减少内存占用
- 避免大字符串分配
- 适合巨大路径

### 字符串预分配

`SkString` 内部优化:
- 小字符串栈分配
- 大字符串自动扩展

### Lambda 捕获

回调使用引用捕获:
```cpp
[&]() { ... }
```
避免不必要的拷贝。

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| include/core/SkPath.h | 实现 | dump 方法声明 |
| include/core/SkPathBuilder.h | 实现 | dump/dumpToString 声明 |
| include/core/SkPathIter.h | 使用 | 路径迭代器 |
| include/core/SkStream.h | 使用 | 输出流 |
| src/core/SkStringUtils.h | 使用 | 数值格式化 |
| include/core/SkSpan.h | 使用 | 数组视图 |
