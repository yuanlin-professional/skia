# FuzzParsePath

> 源文件: fuzz/FuzzParsePath.cpp

## 概述

FuzzParsePath 是一个用于模糊测试 SVG 路径字符串解析器的模块。该文件通过生成随机的、符合 SVG 路径语法的字符串(包括各种边缘情况和畸形输入),测试 `SkParsePath::FromSVGString` 函数的健壮性。解析器需要正确处理各种空白字符、数值格式、命令组合以及语法错误,确保不会因为恶意或格式错误的输入而崩溃。

## 架构位置

```
skia/
  ├── fuzz/                          # 模糊测试根目录
  │   ├── FuzzParsePath.cpp         # 本文件:SVG 路径解析测试
  │   ├── FuzzPath.cpp              # 路径二进制反序列化测试
  │   └── Fuzz.h                    # 模糊测试工具类
  ├── include/utils/                 # 工具 API
  │   └── SkParsePath.h             # SVG 路径解析器
  ├── src/utils/                     # 工具实现
  │   └── SkParsePath.cpp           # 解析器实现
  └── include/core/                  # 核心类
      ├── SkPath.h                  # 路径类
      └── SkString.h                # 字符串类
```

SVG 路径字符串是 Web 和矢量图形中广泛使用的格式,解析器的健壮性对安全性至关重要。

## 主要类与结构体

### Legal 结构体

```cpp
static const struct Legal {
    char fSymbol;    // 路径命令字符(M, L, C, Q等)
    int fScalars;    // 该命令需要的标量参数数量
} gLegal[] = {
    { 'M', 2 },  // MoveTo
    { 'H', 1 },  // Horizontal LineTo
    { 'V', 1 },  // Vertical LineTo
    { 'L', 2 },  // LineTo
    { 'Q', 4 },  // Quadratic Bezier
    { 'T', 2 },  // Smooth Quadratic
    { 'C', 6 },  // Cubic Bezier
    { 'S', 4 },  // Smooth Cubic
    { 'A', 4 },  // Arc (实际需要7个参数,特殊处理)
    { 'Z', 0 },  // ClosePath
};
```

### 全局常量

**gWhiteSpace**
```cpp
static const char gWhiteSpace[] = {
    0, 0, 0, 0, 0, 0, 0, 0,  // 主要是无空白
    ' ', ' ', ' ', ' ',      // 空格(较高权重)
    0x09, 0x0D, 0x0A         // 制表符、回车、换行
};
```
- 偏向于无空白或普通空格
- 包含 SVG 规范允许的所有空白字符

**gEasy**
```cpp
static bool gEasy = false;
```
- 调试标志,启用后生成易读的路径字符串
- 正常测试时为 false,生成复杂输入

## 公共 API 函数

### MakeRandomParsePathPiece

```cpp
SkString MakeRandomParsePathPiece(Fuzz* fuzz)
```

**功能**: 生成单个随机的 SVG 路径命令片段

**实现逻辑**:

1. **选择命令**
   ```cpp
   uint8_t legalIndex;
   fuzz->nextRange(&legalIndex, 0, (int)std::size(gLegal) - 1);
   const Legal& legal = gLegal[legalIndex];
   ```

2. **添加前导空白**
   ```cpp
   gEasy ? atom.append("\n") : add_white(fuzz, &atom);
   ```

3. **命令字符大小写**
   ```cpp
   char symbol = legal.fSymbol | (b ? 0x20 : 0);  // 大写或小写
   ```
   - 大写: 绝对坐标
   - 小写: 相对坐标

4. **生成参数重复**
   ```cpp
   uint8_t reps;
   fuzz->nextRange(&reps, 1, 3);  // 1-3 次重复
   ```

5. **生成坐标参数**
   ```cpp
   for (int rep = 0; rep < reps; ++rep) {
       for (int index = 0; index < legal.fScalars; ++index) {
           SkScalar coord;
           fuzz->nextRange(&coord, 0.0f, 100.0f);
           atom.appendScalar(coord);
       }
   }
   ```

6. **特殊处理椭圆弧(A命令)**
   ```cpp
   if ('A' == legal.fSymbol && 1 == index) {
       SkScalar s;
       fuzz->nextRange(&s, -720.0f, 720.0f);  // 旋转角度
       atom.appendScalar(s);
       atom.appendU32(b);  // large-arc-flag
       atom.appendU32(b);  // sweep-flag
   }
   ```

### DEF_FUZZ(ParsePath, fuzz)

```cpp
DEF_FUZZ(ParsePath, fuzz)
```

**功能**: 模糊测试 SVG 路径解析器

**实现流程**:

1. **生成完整路径字符串**
   ```cpp
   SkString spec;
   uint8_t count;
   fuzz->nextRange(&count, 0, 40);  // 0-40 个命令
   for (uint8_t i = 0; i < count; ++i) {
       spec.append(MakeRandomParsePathPiece(fuzz));
   }
   ```

2. **输出调试信息**
   ```cpp
   SkDebugf("SkParsePath::FromSVGString(%s, &path);\n", spec.c_str());
   ```

3. **执行解析**
   ```cpp
   if (!SkParsePath::FromSVGString(spec.c_str())) {
       SkDebugf("Could not decode path\n");
   }
   ```

## 内部实现细节

### 空白字符生成

**add_white**
```cpp
static void add_white(Fuzz* fuzz, SkString* atom)
```
- 随机添加 0-2 个空白字符
- 大部分时间不添加空白(提高测试效率)
- 测试解析器的空白处理

**add_some_white**
```cpp
static void add_some_white(Fuzz* fuzz, SkString* atom)
```
- 连续调用 10 次 `add_white`
- 生成大量空白的极端情况

### 逗号生成

**add_comma**
```cpp
static void add_comma(Fuzz* fuzz, SkString* atom)
```
- 随机决定是否添加逗号分隔符
- 逗号前后可能有空白
- 测试有无逗号的兼容性

### 测试覆盖

1. **命令类型**:
   - 所有 SVG 路径命令(M, L, H, V, C, S, Q, T, A, Z)
   - 大小写变体(绝对/相对坐标)

2. **数值格式**:
   - 整数和浮点数
   - 正负数
   - 科学记数法(隐式,通过 `appendScalar`)

3. **空白处理**:
   - 无空白
   - 单个空格
   - 多个空格
   - 制表符、换行符

4. **分隔符**:
   - 逗号分隔
   - 空格分隔
   - 无分隔符(紧凑格式)

5. **边缘情况**:
   - 空字符串
   - 仅包含空白
   - 未闭合的命令
   - 参数数量不匹配

## 依赖关系

### 直接依赖

- **SkParsePath** (`include/utils/SkParsePath.h`)
  - `FromSVGString`: 核心解析函数
  - 返回 `std::optional<SkPath>`

- **SkString** (`include/core/SkString.h`)
  - 字符串构建和操作

### 间接依赖

- **SkPath** (`include/core/SkPath.h`)
  - 解析结果的目标类型

- **SVG 规范**
  - 定义路径命令语法

## 设计模式与设计决策

### 设计模式

1. **生成器模式**
   - `MakeRandomParsePathPiece` 生成基本单元
   - 组合多个单元形成完整测试用例

2. **结构化模糊测试**
   - 不生成完全随机的字节序列
   - 生成符合语法结构的字符串(但可能语义错误)

### 设计决策

1. **参数范围限制**
   ```cpp
   fuzz->nextRange(&coord, 0.0f, 100.0f);
   ```
   - 避免极端坐标导致数值溢出
   - 专注于解析逻辑而非数值稳定性

2. **命令数量限制**
   ```cpp
   fuzz->nextRange(&count, 0, 40);
   ```
   - 防止过长字符串导致超时
   - 40 个命令足以覆盖大部分解析路径

3. **调试输出**
   ```cpp
   SkDebugf("SkParsePath::FromSVGString(%s, &path);\n", spec.c_str());
   ```
   - 便于复现失败的测试用例
   - 可直接复制到代码中调试

4. **椭圆弧特殊处理**
   - Arc 命令参数复杂(x-radius, y-radius, rotation, large-arc-flag, sweep-flag, x, y)
   - 单独生成布尔标志和旋转角度

## 性能考量

### 测试效率

1. **字符串构建**
   - 使用 `SkString` 的高效追加操作
   - 避免频繁的内存分配

2. **命令数量限制**
   - 防止解析超时
   - 平衡覆盖率和速度

3. **参数重复**
   - 1-3 次重复增加测试密度
   - 不会导致过长字符串

### 解析器性能

- **时间复杂度**: O(n),其中 n 是字符串长度
- **内存占用**: 与生成的路径复杂度成正比
- **错误处理**: 早期检测语法错误避免无效计算

## 相关文件

### 核心实现
- `include/utils/SkParsePath.h` - SVG 路径解析器声明
- `src/utils/SkParsePath.cpp` - 解析器实现
- `src/utils/SkParse.cpp` - 底层数值解析

### 相关测试
- `fuzz/oss_fuzz/FuzzParsePath.cpp` - OSS-Fuzz 版本
- `tests/ParsePathTest.cpp` - 单元测试
- `fuzz/FuzzPath.cpp` - 路径二进制反序列化

### 使用场景
- `modules/svg/src/SkSVGPath.cpp` - SVG 路径元素
- `tools/viewer/SvgSlide.cpp` - 查看器中的 SVG 支持
- `modules/skottie/src/SkottieShape.cpp` - Lottie 动画路径

### 测试基础设施
- `fuzz/Fuzz.h` - 模糊测试工具类
- `site/dev/testing/fuzz.md` - 模糊测试指南

### 规范文档
- W3C SVG 1.1 规范 - 路径数据语法
- SVG 2 规范 - 路径命令定义
