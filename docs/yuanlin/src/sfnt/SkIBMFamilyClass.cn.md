# SkIBMFamilyClass

> 源文件: src/sfnt/SkIBMFamilyClass.h

## 概述

`SkIBMFamilyClass.h` 定义了 IBM 字体家族分类系统,这是一个用于字体分类的两字节编码方案。该分类系统最初由 IBM 开发,后被 OpenType 规范采纳,用于 OS/2 表的 `sFamilyClass` 字段。分类系统通过主类别(Family Class)和子类别(Subclass)对字体进行细粒度分类,帮助字体匹配和替换算法做出更精确的决策。

## 架构位置

```
Skia 字体系统
└── src/sfnt/ (OpenType 字体支持)
    ├── SkOTTableTypes.h (基础类型)
    ├── SkIBMFamilyClass.h (IBM 字体分类) ←
    └── SkOTTable_OS_2_*.h (OS/2 表各版本)
```

**定位**: 字体元数据和分类支持层

## 主要类与结构体

### SkIBMFamilyClass (主结构)

```cpp
struct SkIBMFamilyClass {
    enum class Class : SK_OT_BYTE {
        NoClassification = 0,      // 无分类
        OldstyleSerifs = 1,        // 老式衬线
        TransitionalSerifs = 2,    // 过渡衬线
        ModernSerifs = 3,          // 现代衬线
        ClarendonSerifs = 4,       // 克拉伦登衬线
        SlabSerifs = 5,            // 平板衬线
        FreeformSerifs = 7,        // 自由衬线
        SansSerif = 8,             // 无衬线
        Ornamentals = 9,           // 装饰体
        Scripts = 10,              // 手写体
        Symbolic = 12,             // 符号字体
    } familyClass;

    SubClass familySubClass;  // 子类别联合体
};
```

**大小**: 2 字节(1字节主类 + 1字节子类)

### SubClass 联合体

根据主类别(`familyClass`)的不同,子类别有不同的含义:

#### OldstyleSerifs (老式衬线子类)

```cpp
enum class OldstyleSerifs : SK_OT_BYTE {
    NoClassification = 0,
    IBMRoundedLegibility = 1,  // IBM 圆角易读体
    Garalde = 2,               // 加拉尔德体
    Venetian = 3,              // 威尼斯体
    ModifiedVenetian = 4,      // 改进威尼斯体
    DutchModern = 5,           // 荷兰现代体
    DutchTraditional = 6,      // 荷兰传统体
    Contemporary = 7,          // 当代体
    Calligraphic = 8,          // 书法体
    Miscellaneous = 15,        // 杂类
};
```

#### SansSerif (无衬线子类)

```cpp
enum class SansSerif : SK_OT_BYTE {
    NoClassification = 0,
    IBMNeoGrotesqueGothic = 1,     // IBM 新怪诞哥特体
    Humanist = 2,                   // 人文主义
    LowXRoundGeometric = 3,         // 低 x 高度圆形几何
    HighXRoundGeometric = 4,        // 高 x 高度圆形几何
    NeoGrotesqueGothic = 5,         // 新怪诞哥特体
    ModifiedNeoGrotesqueGothic = 6, // 改进新怪诞哥特体
    TypewriterGothic = 9,           // 打字机哥特体
    Matrix = 10,                    // 矩阵体
    Miscellaneous = 15,             // 杂类
};
```

#### Scripts (手写体子类)

```cpp
enum class Scripts : SK_OT_BYTE {
    NoClassification = 0,
    Uncial = 1,           // 安色尔体
    Brush_Joined = 2,     // 毛笔连写
    Formal_Joined = 3,    // 正式连写
    Monotone_Joined = 4,  // 单调连写
    Calligraphic = 5,     // 书法体
    Brush_Unjoined = 6,   // 毛笔不连写
    Formal_Unjoined = 7,  // 正式不连写
    Monotone_Unjoined = 8,// 单调不连写
    Miscellaneous = 15,   // 杂类
};
```

#### Symbolic (符号字体子类)

```cpp
enum class Symbolic : SK_OT_BYTE {
    NoClassification = 0,
    MixedSerif = 3,          // 混合衬线
    OldstyleSerif = 6,       // 老式衬线
    NeoGrotesqueSansSerif = 7, // 新怪诞无衬线
    Miscellaneous = 15,      // 杂类
};
```

### 其他主类别子类

- **TransitionalSerifs**: DirectLine, Script, Miscellaneous
- **ModernSerifs**: Italian, Script, Miscellaneous
- **ClarendonSerifs**: Clarendon, Modern, Traditional, Newspaper, StubSerif, Monotone, Typewriter, Miscellaneous
- **SlabSerifs**: Monotone, Humanist, Geometric, Swiss, Typewriter, Miscellaneous
- **FreeformSerifs**: Modern, Miscellaneous
- **Ornamentals**: Engraver, BlackLetter, Decorative, ThreeDimensional, Miscellaneous

## 公共 API 函数

该文件为纯数据结构定义,典型用法:

```cpp
// 从 OS/2 表读取分类
const SkOTTableOS2* os2 = ...;
const SkIBMFamilyClass& familyClass = os2->sFamilyClass;

// 检查主类别
if (familyClass.familyClass == SkIBMFamilyClass::Class::SansSerif) {
    // 检查子类别
    auto subclass = familyClass.familySubClass.sansSerif;
    if (subclass == SkIBMFamilyClass::SubClass::SansSerif::Humanist) {
        // 处理人文主义无衬线字体
    }
}

// 用于字体匹配
bool isSerifFont(const SkIBMFamilyClass& fc) {
    return fc.familyClass >= SkIBMFamilyClass::Class::OldstyleSerifs &&
           fc.familyClass <= SkIBMFamilyClass::Class::FreeformSerifs;
}
```

## 内部实现细节

### 内存布局

```cpp
#pragma pack(push, 1)  // 无填充字节

static_assert(sizeof(SkIBMFamilyClass) == 2,
    "sizeof_SkIBMFamilyClass_not_2");
```

**结构**:
- 第1字节: `familyClass` (主类别)
- 第2字节: `familySubClass` (子类别)

### 联合体设计

`SubClass` 是联合体,所有子类枚举共享同一内存:
- 根据 `familyClass` 的值解释第二字节
- 节省空间(仅需1字节存储子类)
- 类型安全访问

### 保留值

多个分类中保留了 6 和 11-14 号值供未来使用,体现了良好的扩展性设计。

## 依赖关系

```
SkIBMFamilyClass.h
└── src/sfnt/SkOTTableTypes.h (SK_OT_BYTE 类型定义)
```

**被依赖方**:
- `src/sfnt/SkOTTable_OS_2_*.h` - OS/2 表各版本
- 字体匹配算法
- 字体替换逻辑

## 设计模式与设计决策

### 1. 两级分类体系

**设计**: 主类(10种) + 子类(每类最多15种)
**优势**:
- 仅用 2 字节表达 150+ 种分类
- 层次清晰,便于理解
- 支持粗粒度和细粒度匹配

### 2. 枚举类(enum class)

使用 C++11 的 `enum class`:
- 强类型,避免隐式转换
- 防止命名冲突
- 提高代码可读性

### 3. 联合体子类

**优势**:
- 紧凑存储(1字节)
- 根据上下文解释
- 类型安全访问

**权衡**:
- 需要根据主类别判断子类含义
- 错误使用可能导致语义错误

### 4. Miscellaneous 统一值

所有子类的"杂类"都是 15:
- 统一的回退值
- 便于检测未分类字体
- 保持一致性

## 性能考量

### 内存占用

仅 2 字节,极其紧凑:
- 适合大量字体的内存缓存
- 最小化磁盘 I/O
- 提高缓存命中率

### 访问效率

直接字节访问,无需解析:
```cpp
uint8_t mainClass = static_cast<uint8_t>(fc.familyClass);
```

单条 CPU 指令即可完成。

### 比较操作

```cpp
// 高效的分类检查
bool isSerif = familyClass.familyClass <= SkIBMFamilyClass::Class::FreeformSerifs
    && familyClass.familyClass != SkIBMFamilyClass::Class::NoClassification;
```

简单的整数比较,分支预测友好。

## 相关文件

| 文件路径 | 说明 | 关系 |
|---------|------|------|
| `src/sfnt/SkOTTable_OS_2_V0.h` | OS/2 表 V0 | 使用此分类 |
| `src/sfnt/SkOTTable_OS_2_V1.h` | OS/2 表 V1 | 使用此分类 |
| `src/sfnt/SkOTTable_OS_2_V2.h` | OS/2 表 V2 | 使用此分类 |
| `src/sfnt/SkPanose.h` | PANOSE 分类系统 | 互补的分类方案 |
| `src/core/SkFontMgr_*.cpp` | 字体管理器 | 使用分类进行匹配 |
| `src/ports/SkTypeface_*.cpp` | 字体接口实现 | 读取和解析分类 |

IBM 字体家族分类系统提供了一个紧凑而精确的字体分类方案,是字体匹配算法的重要输入,帮助系统在缺少指定字体时选择最合适的替代字体。
