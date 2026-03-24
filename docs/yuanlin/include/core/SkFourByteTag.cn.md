# SkFourByteTag

> 源文件: `include/core/SkFourByteTag.h`

## 概述

SkFourByteTag 定义了四字节标签(FourCC - Four Character Code)类型及其构造函数,用于在 Skia 字体系统中表示 OpenType 字体表名称、可变字体轴标识符等标准化标记。通过将四个 ASCII 字符打包为 32 位整数,提供了紧凑、高效且人类可读的标识符系统。

## 架构位置

该文件位于 Skia 核心层 (`include/core`),是字体子系统的基础类型定义。它被字体参数(SkFontParameters)、字体参数(SkFontArguments)和底层字体解析代码广泛使用,是 OpenType 规范在 Skia 中的标准表示。

## 类型定义

### SkFourByteTag

**定义**: `using SkFourByteTag = uint32_t;`

**职责**: 32 位无符号整数类型别名,用于存储四字符标签。

**字节序**: 大端序(Big-Endian),第一个字符在最高字节。

**典型用途**:
- OpenType 字体表标识符(如 'head', 'hhea', 'name')
- 可变字体轴标签(如 'wght', 'wdth', 'slnt')
- 字体格式标识符(如 'ttcf' 表示 TrueType Collection)

## 公共 API 函数

### `constexpr SkFourByteTag SkSetFourByteTag(char a, char b, char c, char d)`

- **功能**: 从四个字符构造四字节标签
- **参数**:
  - `a`: 第一个字符(最高字节)
  - `b`: 第二个字符
  - `c`: 第三个字符
  - `d`: 第四个字符(最低字节)
- **返回值**: 32 位无符号整数,按大端序编码字符
- **constexpr**: 支持编译期常量计算
- **实现**:
  ```cpp
  return (((uint32_t)a << 24) |  // 字符 a 在最高字节
          ((uint32_t)b << 16) |  // 字符 b 在次高字节
          ((uint32_t)c << 8)  |  // 字符 c 在次低字节
          (uint32_t)d);          // 字符 d 在最低字节
  ```

## 使用示例

### 创建标签
```cpp
// OpenType 字体表标签
constexpr SkFourByteTag kHeadTag = SkSetFourByteTag('h', 'e', 'a', 'd');
constexpr SkFourByteTag kNameTag = SkSetFourByteTag('n', 'a', 'm', 'e');

// 可变字体轴标签
constexpr SkFourByteTag kWeightAxis = SkSetFourByteTag('w', 'g', 'h', 't');
constexpr SkFourByteTag kWidthAxis  = SkSetFourByteTag('w', 'd', 't', 'h');
constexpr SkFourByteTag kSlantAxis  = SkSetFourByteTag('s', 'l', 'n', 't');
constexpr SkFourByteTag kItalicAxis = SkSetFourByteTag('i', 't', 'a', 'l');

// 字体格式魔数
constexpr SkFourByteTag kTTCFTag = SkSetFourByteTag('t', 't', 'c', 'f');  // TTC 头部
constexpr SkFourByteTag kTrueTag = SkSetFourByteTag('t', 'r', 'u', 'e');  // TrueType
```

### 运行时标签操作
```cpp
// 从标签提取字符
void PrintTag(SkFourByteTag tag) {
    char chars[5] = {
        (char)((tag >> 24) & 0xFF),
        (char)((tag >> 16) & 0xFF),
        (char)((tag >> 8)  & 0xFF),
        (char)(tag & 0xFF),
        '\0'
    };
    printf("Tag: '%s' (0x%08X)\n", chars, tag);
}

// 标签比较
if (tag == SkSetFourByteTag('w', 'g', 'h', 't')) {
    // 处理字重轴
}
```

### 可变字体轴配置
```cpp
SkFontArguments::VariationPosition::Coordinate coords[] = {
    {SkSetFourByteTag('w', 'g', 'h', 't'), 650.0f},  // 字重 650
    {SkSetFourByteTag('w', 'd', 't', 'h'), 80.0f},   // 字宽 80%
    {SkSetFourByteTag('s', 'l', 'n', 't'), -10.0f}   // 倾斜 -10 度
};
```

### 字体表枚举
```cpp
// 查询字体是否包含特定表
bool HasTable(SkTypeface* typeface, const char* tableName) {
    SkFourByteTag tag = SkSetFourByteTag(
        tableName[0], tableName[1], tableName[2], tableName[3]);

    size_t size = typeface->getTableSize(tag);
    return size > 0;
}

if (HasTable(typeface, "COLR")) {
    // 字体支持彩色字形
}
```

## 内部实现细节

### 字节序布局
```
SkSetFourByteTag('w', 'g', 'h', 't'):

内存布局(大端序):
[31-24位] 'w' (0x77)
[23-16位] 'g' (0x67)
[15-8 位] 'h' (0x68)
[7-0  位] 't' (0x74)

结果: 0x77676874
```

### 平台无关性
虽然不同平台字节序不同,但 SkFourByteTag 使用显式位移,确保跨平台一致性:
- 小端机器(x86/ARM):内存中为 `74 68 67 77`,但逻辑值一致
- 大端机器(部分 MIPS/PowerPC):内存中为 `77 67 68 74`
- 比较和传输时无需字节序转换

### constexpr 优势
编译期计算,零运行时开销:
```cpp
// 编译器直接替换为 0x77676874
constexpr SkFourByteTag kWeightAxis = SkSetFourByteTag('w', 'g', 'h', 't');

// 等价于
constexpr SkFourByteTag kWeightAxis = 0x77676874;
```

## 常见标签参考

### OpenType 字体表标签
| 标签 | 说明 | 内容 |
|------|------|------|
| 'head' | 字体头部 | 版本、字体边界框、单位等 |
| 'hhea' | 水平度量头部 | 行高、最大宽度等 |
| 'maxp' | 最大值表 | 字形数量、复杂度限制 |
| 'name' | 命名表 | 字体名称、版权信息 |
| 'OS/2' | OS/2 和 Windows 度量 | 字重、字宽、Unicode 范围 |
| 'post' | PostScript 信息 | 下划线位置、字形名称 |
| 'cmap' | 字符映射 | Unicode 到字形 ID 映射 |
| 'glyf' | 字形数据 | TrueType 字形轮廓 |
| 'loca' | 字形位置 | 字形数据偏移量 |
| 'CFF ' | 紧凑字体格式 | PostScript 字形轮廓 |
| 'fvar' | 字体变体 | 可变字体轴定义 |
| 'gvar' | 字形变体 | 可变字形增量 |
| 'COLR' | 彩色表 | 彩色字形图层 |
| 'CPAL' | 调色板 | 彩色字形调色板 |

### 注册可变轴标签(OpenType Variations)
| 标签 | 名称 | 范围 | 说明 |
|------|------|------|------|
| 'wght' | Weight | 1-1000 | 字重(100=Thin, 400=Normal, 700=Bold) |
| 'wdth' | Width | 1-200 | 字宽(百分比,100=正常) |
| 'slnt' | Slant | -90-90 | 倾斜角度(度数) |
| 'ital' | Italic | 0-1 | 意大利斜体(0=直立,1=斜体) |
| 'opsz' | Optical Size | 6-72+ | 光学尺寸(点数) |

### 字体格式魔数
| 标签 | 格式 |
|------|------|
| 'ttcf' | TrueType Collection 头部魔数 |
| 'true' | TrueType 字体魔数 |
| 'typ1' | PostScript Type 1 字体 |
| 'OTTO' | OpenType with CFF 轮廓 |
| 0x00010000 | TrueType 字体(版本 1.0) |

## 依赖关系

### 依赖的模块
无外部依赖,仅依赖 C++ 标准库 `<cstdint>`。

### 被依赖的模块
| 模块 | 用途 |
|------|------|
| SkFontParameters.h | 轴标签定义 |
| SkFontArguments.h | 轴坐标结构 |
| SkTypeface | 字体表查询(getTableSize/getTableData) |
| SkFontScanner | 字体扫描器,使用标签解析字体 |
| 底层字体实现 | FreeType/CoreText/DirectWrite 字体表访问 |

## 设计决策

### 为何使用四字符标签
- **OpenType 标准**: 规范要求使用 4 字节标签
- **可读性**: 'wght' 比 0x77676874 更易理解
- **紧凑性**: 32 位整数,适合整数比较和哈希
- **历史兼容**: TrueType/PostScript 的长期惯例

### 为何使用类型别名
```cpp
using SkFourByteTag = uint32_t;
```
而非强类型类:
- **透明性**: 可直接与整数比较和传递
- **性能**: 无包装开销
- **简洁性**: 避免显式转换

### constexpr 函数
支持编译期计算:
- 标签通常是常量,编译期计算避免运行时开销
- 允许在模板参数和 switch-case 中使用

## 性能考量

### 编译期优化
```cpp
// 完全编译期计算,无运行时开销
switch (tag) {
    case SkSetFourByteTag('w', 'g', 'h', 't'):
        // 编译器将 'w','g','h','t' 替换为 0x77676874
        break;
}
```

### 整数比较
标签比较是单次整数比较,非常高效:
```cpp
// O(1) 整数比较
if (tag == kWeightAxis) { ... }

// 比字符串比较快得多
if (strcmp(str, "wght") == 0) { ... }  // O(n) 字符比较
```

### 哈希友好
可直接用作哈希表键:
```cpp
std::unordered_map<SkFourByteTag, float> axisValues;
axisValues[SkSetFourByteTag('w', 'g', 'h', 't')] = 600.0f;
```

## 错误处理

### 无效字符
```cpp
// 小心空字符和非 ASCII 字符
SkFourByteTag invalid1 = SkSetFourByteTag('w', 'g', 'h', '\0');  // 截断标签
SkFourByteTag invalid2 = SkSetFourByteTag('中', '文', 'x', 'x');  // 多字节字符被截断

// 空格填充(OpenType 约定)
SkFourByteTag os2Tag = SkSetFourByteTag('O', 'S', '/', '2');  // 正确
```

### 大小写敏感
```cpp
// 标签大小写敏感!
SkSetFourByteTag('W', 'G', 'H', 'T') ≠ SkSetFourByteTag('w', 'g', 'h', 't')
```

### 字节序陷阱
```cpp
// 错误:直接赋值十六进制
SkFourByteTag wrong = 0x77676874;  // 在小端机器上字符顺序错误

// 正确:使用构造函数
SkFourByteTag correct = SkSetFourByteTag('w', 'g', 'h', 't');  // 跨平台正确
```

## 实际应用示例

### 查询字体支持的轴
```cpp
std::vector<SkFourByteTag> GetSupportedAxes(SkTypeface* typeface) {
    std::vector<SkFourByteTag> axes;

    SkFontParameters::Variation::Axis axisInfo[20];
    int count = typeface->getVariationDesignParameters(axisInfo, 20);

    for (int i = 0; i < count; ++i) {
        axes.push_back(axisInfo[i].tag);
    }

    return axes;
}
```

### 标签到字符串转换
```cpp
std::string TagToString(SkFourByteTag tag) {
    char chars[5] = {
        (char)((tag >> 24) & 0xFF),
        (char)((tag >> 16) & 0xFF),
        (char)((tag >> 8)  & 0xFF),
        (char)(tag & 0xFF),
        '\0'
    };
    return std::string(chars);
}

// 用法
printf("轴: %s\n", TagToString(SkSetFourByteTag('w', 'g', 'h', 't')).c_str());
// 输出: 轴: wght
```

### 读取字体表数据
```cpp
std::unique_ptr<uint8_t[]> ReadFontTable(SkTypeface* typeface,
                                         SkFourByteTag tag) {
    size_t size = typeface->getTableSize(tag);
    if (size == 0) return nullptr;

    auto data = std::make_unique<uint8_t[]>(size);
    size_t bytesRead = typeface->getTableData(tag, 0, size, data.get());

    return (bytesRead == size) ? std::move(data) : nullptr;
}

// 读取 'name' 表
auto nameTable = ReadFontTable(typeface, SkSetFourByteTag('n', 'a', 'm', 'e'));
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/core/SkFontParameters.h` | 使用 SkFourByteTag 定义轴标签 |
| `include/core/SkFontArguments.h` | 使用 SkFourByteTag 设置轴坐标 |
| `include/core/SkTypeface.h` | 字体对象,使用标签查询字体表 |
| `include/core/SkFontScanner.h` | 字体扫描器,解析标签标识的数据 |
| `src/sfnt/SkOTTable*.h` | OpenType 表结构定义 |
