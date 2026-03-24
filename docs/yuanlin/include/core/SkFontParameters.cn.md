# SkFontParameters

> 源文件: `include/core/SkFontParameters.h`

## 概述

SkFontParameters 定义了字体参数的结构化命名空间,核心内容是 Variation::Axis 结构体,用于描述 OpenType 可变字体(Variable Fonts)的设计轴参数。每个轴通过四字符标签、数值范围和可见性标志定义字体的可变维度(如字重、字宽、倾斜角度等)。

## 架构位置

该头文件位于 Skia 核心层 (`include/core`),属于字体子系统的元数据定义模块。它为 SkFontScanner(字体扫描器)和 SkFontArguments(字体实例化参数)提供可变字体轴的标准描述格式,是 OpenType Variations 规范在 Skia 中的抽象表示。

## 类与结构体

### SkFontParameters 命名空间

**职责**: 作为字体参数相关结构的顶层命名空间,组织可变字体的参数定义。

### Variation 结构

**职责**: 封装可变字体(Variable Fonts)相关的参数结构。

### Variation::Axis 结构体

**职责**: 描述可变字体的单个设计轴(Design Axis)的元数据。

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| tag | SkFourByteTag | 四字符标签,标识轴类型(如 'wght'、'wdth') |
| min | float | 轴的最小允许值 |
| def | float | 轴的默认值(字体设计时的标准位置) |
| max | float | 轴的最大允许值(可等于 min 表示固定值) |
| flags | uint16_t | 属性标志(当前仅定义 HIDDEN 位) |

## 公共 API 函数

### Axis 构造函数

#### `constexpr Axis()`
- **功能**: 默认构造函数,创建无效的零初始化轴
- **初始值**: `{tag=0, min=0, def=0, max=0, flags=0}`

#### `constexpr Axis(SkFourByteTag tag, float min, float def, float max, bool hidden)`
- **功能**: 从完整参数创建轴描述
- **参数**:
  - `tag`: 四字符标签(如 `SkSetFourByteTag('w','g','h','t')`)
  - `min`: 最小值
  - `def`: 默认值
  - `max`: 最大值
  - `hidden`: 是否在用户界面中隐藏

### Axis 成员函数

#### `bool isHidden() const`
- **功能**: 查询轴是否建议在用户界面中隐藏
- **返回值**: 隐藏返回 true,否则返回 false
- **实现**: `return flags & HIDDEN;`
- **用途**: UI 可选择仅显示非隐藏轴供用户调整

#### `void setHidden(bool hidden)`
- **功能**: 设置轴的隐藏属性
- **参数**: `hidden` - true 设置为隐藏,false 设置为可见
- **实现**: 位操作设置或清除 HIDDEN 标志位

## 常见设计轴标签

### 注册轴(Registered Axes)
OpenType 规范定义的标准轴:

| 标签 | 四字符码 | 含义 | 典型范围 |
|------|---------|------|---------|
| wght | 'wght' | 字重(Weight) | 100-900 |
| wdth | 'wdth' | 字宽(Width) | 50-200 (百分比) |
| slnt | 'slnt' | 倾斜角度(Slant) | -90-90 (度数) |
| ital | 'ital' | 意大利斜体(Italic) | 0-1 (布尔) |
| opsz | 'opsz' | 光学尺寸(Optical Size) | 6-72 (点数) |

### 自定义轴
字体设计师可定义私有轴(通常大写标签):
```cpp
Axis customAxis('COOL', 0.0f, 0.5f, 1.0f, false);  // 自定义"酷炫"轴
```

## 使用场景

### 字体扫描
SkFontScanner 使用 Axis 报告字体支持的可变轴:
```cpp
SkFontScanner::AxisDefinitions axes;
scanner->scanInstance(stream, faceIndex, 0, &name, &style,
                      &isFixedPitch, &axes, &position);

for (const auto& axis : axes) {
    printf("轴: %c%c%c%c, 范围: [%.2f, %.2f], 默认: %.2f\n",
           (axis.tag >> 24) & 0xFF, (axis.tag >> 16) & 0xFF,
           (axis.tag >> 8) & 0xFF, axis.tag & 0xFF,
           axis.min, axis.max, axis.def);
}
```

### 用户界面构建
图形编辑器根据轴定义生成滑块控件:
```cpp
void BuildFontUI(const AxisDefinitions& axes) {
    for (const auto& axis : axes) {
        if (axis.isHidden()) continue;  // 跳过隐藏轴

        Slider* slider = new Slider(axis.min, axis.max, axis.def);
        slider->setLabel(TagToString(axis.tag));
        ui->addControl(slider);
    }
}
```

### 字体实例化
与 SkFontArguments 配合设置轴值:
```cpp
SkFontArguments args;
SkFontArguments::VariationPosition::Coordinate coords[] = {
    {'wght', 600.0f},  // 设置字重为 600
    {'wdth', 75.0f}    // 设置字宽为 75%
};
args.setVariationDesignPosition({coords, 2});

sk_sp<SkTypeface> typeface = fontMgr->makeFromStream(
    stream, args);
```

## 内部实现细节

### 标志位布局
```cpp
flags (uint16_t):
[0 位] HIDDEN (0x0001) - 用户界面隐藏标志
[1-15 位] 保留未来使用
```

### 数值范围验证
虽然结构体本身不验证,但使用方应确保:
- `min <= def <= max`
- 特殊情况:`min == max` 表示固定值轴(如命名实例)

### constexpr 设计
构造函数是 constexpr,允许编译期常量:
```cpp
constexpr Axis kWeightAxis('wght', 100, 400, 900, false);
```

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| SkFourByteTag.h | 四字符标签类型定义 |

### 被依赖的模块
| 模块 | 用途 |
|------|------|
| SkFontScanner | 扫描字体时返回轴定义数组 |
| SkFontArguments | 使用轴标签设置实例化坐标 |
| SkFontMgr | 字体管理器,处理可变字体创建 |
| UI 工具包 | 根据轴信息构建字体编辑界面 |

## 设计模式与设计决策

### 元数据模式
Axis 是纯数据结构(POD):
- 无行为逻辑,仅描述信息
- 适合序列化和 IPC 传输
- 简化字体元数据的存储

### 最小化设计
仅定义必需字段:
- 不包含轴名称字符串(需从字体表读取)
- 不包含单位信息(由标签隐含定义)
- 保持结构紧凑(24 字节)

### 扩展性
预留 15 位标志位用于未来扩展:
- 可能的扩展:轴的必需性(required/optional)
- 可能的扩展:轴的分组信息
- 可能的扩展:值的离散性(连续/离散)

### 隐藏标志的设计
`isHidden()` 反映 OpenType 规范的 HIDDEN_AXIS 标志:
- 某些轴仅供专业排版使用
- 避免普通用户界面过于复杂
- 示例:optical size 通常根据字号自动设置,不暴露给用户

## 性能考量

### 紧凑布局
结构体大小:
```cpp
sizeof(Axis) = 4(tag) + 4(min) + 4(def) + 4(max) + 2(flags) + 2(padding) = 20 字节
```
对齐后通常为 20 或 24 字节(取决于编译器)。

### 数组存储
字体通常有 1-5 个轴,使用小型数组:
```cpp
using AxisDefinitions = skia_private::STArray<4, Axis, true>;
// 小对象优化:4 个轴以内无堆分配
```

### 无虚函数
纯数据结构避免虚函数表开销,适合高频传递。

## OpenType Variations 规范对应

### 'fvar' 表映射
OpenType 字体的 'fvar' 表结构:
```
VariationAxisRecord {
    uint32 axisTag;        → Axis::tag
    Fixed  minValue;       → Axis::min
    Fixed  defaultValue;   → Axis::def
    Fixed  maxValue;       → Axis::max
    uint16 flags;          → Axis::flags
    uint16 axisNameID;     (不存储在 Axis 中)
}
```

### 命名实例
'fvar' 表的命名实例(Named Instances):
```cpp
// 命名实例"Bold"可能定义为:
Axis axes[] = {
    {'wght', 700, 700, 700, false}  // min=def=max,固定在 700
};
```

## 实际应用示例

### 检查字体是否可变
```cpp
bool IsVariableFont(const AxisDefinitions& axes) {
    for (const auto& axis : axes) {
        if (axis.min != axis.max) {
            return true;  // 至少一个轴有范围
        }
    }
    return false;
}
```

### 获取默认实例坐标
```cpp
VariationPosition GetDefaultPosition(const AxisDefinitions& axes) {
    VariationPosition pos;
    for (const auto& axis : axes) {
        pos.coordinates.push_back({axis.tag, axis.def});
    }
    return pos;
}
```

### 钳制用户输入
```cpp
float ClampAxisValue(const Axis& axis, float userValue) {
    if (userValue < axis.min) return axis.min;
    if (userValue > axis.max) return axis.max;
    return userValue;
}
```

## 平台相关说明

### 字体文件支持
- **TrueType/OpenType**: 通过 'fvar' 表定义轴
- **PostScript CFF2**: 通过 Private DICT 定义轴
- **WOFF2**: 支持可变字体的压缩格式

### 平台 API 映射
| 平台 | API | Axis 对应 |
|------|-----|----------|
| CoreText (macOS/iOS) | CTFontVariationAxes | CFDictionary 含 tag/min/max/default |
| DirectWrite (Windows) | DWRITE_FONT_AXIS_RANGE | axisTag/minValue/maxValue |
| FreeType | FT_Var_Axis | tag/minimum/def/maximum |

## 最佳实践

### UI 显示建议
```cpp
std::string GetAxisDisplayName(SkFourByteTag tag) {
    static std::map<SkFourByteTag, std::string> names = {
        {SkSetFourByteTag('w','g','h','t'), "字重"},
        {SkSetFourByteTag('w','d','t','h'), "字宽"},
        {SkSetFourByteTag('s','l','n','t'), "倾斜"},
        {SkSetFourByteTag('i','t','a','l'), "斜体"},
    };
    auto it = names.find(tag);
    return (it != names.end()) ? it->second : TagToString(tag);
}
```

### 值的插值
```cpp
float InterpolateAxis(const Axis& axis, float t) {
    // t ∈ [0, 1]
    return axis.min + t * (axis.max - axis.min);
}
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/core/SkFourByteTag.h` | 定义四字符标签类型 |
| `include/core/SkFontScanner.h` | 使用 Axis 报告字体轴信息 |
| `include/core/SkFontArguments.h` | 使用 Axis::tag 设置实例化坐标 |
| `include/core/SkTypeface.h` | 字体文件,包含轴信息 |
| `src/ports/SkFontHost_*.cpp` | 平台字体实现,解析 'fvar' 表 |
