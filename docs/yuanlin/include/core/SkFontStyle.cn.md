# SkFontStyle

> 源文件: `include/core/SkFontStyle.h`

## 概述

SkFontStyle 封装字体的视觉风格三要素:字重(weight)、字宽(width)和倾斜度(slant)。通过紧凑的 32 位整数存储这些属性,为字体匹配和选择提供标准化的描述语言,是 Skia 字体系统中连接字体文件和渲染需求的关键数据结构。

## 架构位置

SkFontStyle 位于 Skia 核心层 (`include/core`),属于字体子系统的元数据定义层。它被 SkTypeface(字体文件抽象)、SkFontMgr(字体管理器)和文本渲染管线广泛使用,在字体选择算法中扮演核心角色。

## 类定义

### SkFontStyle

**职责**: 以紧凑格式表示字体风格,支持快速比较和字体匹配。

**继承关系**: 无继承,独立值类型

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fValue | int32_t | 打包的风格值,低 16 位存字重,16-23 位存字宽,24-31 位存倾斜度 |

### Weight 枚举

**职责**: 定义字体笔画粗细的标准等级。

| 枚举值 | 数值 | CSS 对应 | 常见名称 |
|--------|------|----------|----------|
| kInvisible_Weight | 0 | - | 不可见(保留值) |
| kThin_Weight | 100 | 100 | Thin/Hairline |
| kExtraLight_Weight | 200 | 200 | Extra Light/Ultra Light |
| kLight_Weight | 300 | 300 | Light |
| kNormal_Weight | 400 | 400 | Normal/Regular |
| kMedium_Weight | 500 | 500 | Medium |
| kSemiBold_Weight | 600 | 600 | Semi Bold/Demi Bold |
| kBold_Weight | 700 | 700 | Bold |
| kExtraBold_Weight | 800 | 800 | Extra Bold/Ultra Bold |
| kBlack_Weight | 900 | 900 | Black/Heavy |
| kExtraBlack_Weight | 1000 | 950 | Extra Black/Ultra Black |

**数值范围**: 实际存储时会被钳制到 [0, 1000]。

### Width 枚举

**职责**: 定义字体字符宽度比例的标准等级。

| 枚举值 | 数值 | 百分比 | 说明 |
|--------|------|--------|------|
| kUltraCondensed_Width | 1 | 50% | 超窄体 |
| kExtraCondensed_Width | 2 | 62.5% | 特窄体 |
| kCondensed_Width | 3 | 75% | 窄体 |
| kSemiCondensed_Width | 4 | 87.5% | 半窄体 |
| kNormal_Width | 5 | 100% | 正常宽度 |
| kSemiExpanded_Width | 6 | 112.5% | 半宽体 |
| kExpanded_Width | 7 | 125% | 宽体 |
| kExtraExpanded_Width | 8 | 150% | 特宽体 |
| kUltraExpanded_Width | 9 | 200% | 超宽体 |

**数值范围**: 实际存储时会被钳制到 [1, 9]。

### Slant 枚举

**职责**: 定义字体倾斜类型。

| 枚举值 | 数值 | 说明 |
|--------|------|------|
| kUpright_Slant | 0 | 直立,正常姿态 |
| kItalic_Slant | 1 | 意大利斜体,通常有特殊设计的字形 |
| kOblique_Slant | 2 | 倾斜体,通常由直立体机械倾斜生成 |

**数值范围**: 实际存储时会被钳制到 [0, 2]。

## 公共 API 函数

### 构造函数

#### `constexpr SkFontStyle(int weight, int width, Slant slant)`
- **功能**: 从三要素创建字体风格,自动钳制参数到有效范围
- **参数**:
  - `weight`: 字重(0-1000)
  - `width`: 字宽(1-9)
  - `slant`: 倾斜度枚举
- **实现**: 通过位移和加法将三值打包为 32 位整数

#### `constexpr SkFontStyle()`
- **功能**: 默认构造函数,创建 Normal 风格
- **等价于**: `SkFontStyle(400, 5, kUpright_Slant)`

### 访问器

#### `int weight() const`
- **功能**: 提取字重值
- **返回值**: 0-1000 整数
- **实现**: `fValue & 0xFFFF`(取低 16 位)

#### `int width() const`
- **功能**: 提取字宽值
- **返回值**: 1-9 整数
- **实现**: `(fValue >> 16) & 0xFF`(取 16-23 位)

#### `Slant slant() const`
- **功能**: 提取倾斜度
- **返回值**: Slant 枚举值
- **实现**: `(Slant)((fValue >> 24) & 0xFF)`(取 24-31 位)

### 比较运算符

#### `bool operator==(const SkFontStyle& rhs) const`
- **功能**: 判断两个风格是否完全相同
- **实现**: 直接比较 `fValue` 整数值

### 静态工厂方法

#### `static constexpr SkFontStyle Normal()`
- **功能**: 创建常规风格(400/5/Upright)
- **返回值**: 默认风格常量

#### `static constexpr SkFontStyle Bold()`
- **功能**: 创建粗体风格(700/5/Upright)
- **返回值**: 粗体风格常量

#### `static constexpr SkFontStyle Italic()`
- **功能**: 创建斜体风格(400/5/Italic)
- **返回值**: 斜体风格常量

#### `static constexpr SkFontStyle BoldItalic()`
- **功能**: 创建粗斜体风格(700/5/Italic)
- **返回值**: 粗斜体风格常量

## 内部实现细节

### 位打包布局
```
fValue (int32_t):
[31-24 位] Slant (0-2)
[23-16 位] Width (1-9)
[15-0  位] Weight (0-1000)
```

**设计优势**:
- 单个整数比较即可判断风格相等
- constexpr 构造支持编译期常量
- 序列化只需 4 字节
- 高效的哈希键

### 参数钳制
使用 `SkTPin` 模板确保数值合法:
```cpp
SkTPin<int>(weight, kInvisible_Weight, kExtraBlack_Weight)  // [0, 1000]
SkTPin<int>(width, kUltraCondensed_Width, kUltraExpanded_Width)  // [1, 9]
SkTPin<int>(slant, kUpright_Slant, kOblique_Slant)  // [0, 2]
```

### constexpr 支持
所有构造函数和工厂方法都是 `constexpr`,允许:
```cpp
constexpr SkFontStyle kDefaultStyle = SkFontStyle::Normal();
```

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| SkTypes.h | SK_API 宏定义 |
| SkTPin.h | 参数钳制模板函数 |

### 被依赖的模块
| 模块 | 用途 |
|------|------|
| SkTypeface | 字体文件关联的风格描述 |
| SkFontMgr | 字体管理器,通过风格匹配字体 |
| SkFont | 字体对象,可指定期望风格 |
| SkFontStyleSet | 字体家族的风格集合 |

## 设计模式与设计决策

### 值语义
SkFontStyle 是纯值类型(Plain Old Data):
- 支持按值传递和复制
- 可用作 std::map 键
- 无需析构函数
- 线程安全(不可变对象)

### 标准化设计
采用 CSS Fonts Level 3 规范的数值定义:
- 字重 100-900 对应 CSS font-weight
- 字宽 1-9 对应 CSS font-stretch 百分比
- 便于 Web 和桌面字体的互操作

### 紧凑存储
32 位整数足以表示所有信息:
- 减少内存占用
- 提高缓存命中率
- 简化序列化

### 可扩展性限制
当前设计为字宽和倾斜度预留 8 位空间:
- 字宽仅用 1-9(可扩展到 255 级)
- 倾斜度仅用 0-2(可扩展支持可变倾斜角度)
- 为未来 Variable Fonts 保留扩展空间

## 字体匹配算法

### 风格距离计算
字体匹配器计算风格差异:
```cpp
int StyleDistance(const SkFontStyle& a, const SkFontStyle& b) {
    int weightDiff = abs(a.weight() - b.weight()) / 10;  // 权重:字重差异
    int widthDiff = abs(a.width() - b.width()) * 100;    // 权重:字宽差异
    int slantDiff = (a.slant() == b.slant()) ? 0 : 1000; // 权重:倾斜度不匹配
    return weightDiff + widthDiff + slantDiff;
}
```

### 匹配优先级
CSS 规范定义的匹配规则:
1. **倾斜度**: 必须完全匹配(Italic ≠ Oblique)
2. **字宽**: 优先接近值(Condensed 匹配 SemiCondensed 优于 Expanded)
3. **字重**: 允许更大范围近似(450 可匹配 400 或 500)

### 后备策略
```cpp
SkTypeface* MatchFont(const SkFontStyle& requested) {
    // 1. 精确匹配
    if (auto tf = FindExactMatch(requested)) return tf;

    // 2. 倾斜度后备(Italic → Oblique → Upright)
    if (requested.slant() == kItalic_Slant) {
        if (auto tf = FindMatch({weight, width, kOblique_Slant})) return tf;
    }

    // 3. 字重后备(700 无法找到时尝试 600/800)
    // 4. 字宽后备(扩展到相邻等级)
    // 5. 使用家族默认字体
    return fallbackTypeface;
}
```

## 平台相关说明

### Variable Fonts 支持
现代可变字体(Variable Fonts)使用连续轴而非离散值:
```cpp
// 传统风格
SkFontStyle style(450, 5, kUpright_Slant);  // 450 字重在两个字体文件间选择

// 可变字体
SkFontArguments args;
args.setVariationDesignPosition({{"wght", 450}});  // 精确 450 字重插值
```

### 字体文件命名
字体文件名通常包含风格信息:
```
Roboto-Thin.ttf           → (100, 5, Upright)
Roboto-BoldItalic.ttf     → (700, 5, Italic)
Roboto-Condensed-Light.ttf → (300, 3, Upright)
```

### CSS 对应关系
| CSS 属性 | SkFontStyle 成员 |
|---------|-----------------|
| font-weight: bold | weight = 700 |
| font-stretch: condensed | width = 3 |
| font-style: italic | slant = kItalic_Slant |

## 性能考量

### 哈希友好
单个整数可直接用作哈希键:
```cpp
struct FontCacheKey {
    SkTypeface* typeface;
    SkFontStyle style;  // 4 字节
    float size;
};
```

### 快速比较
相等性检查是单个整数比较:
```cpp
// O(1) 复杂度
if (style1 == style2) { /* 缓存命中 */ }
```

### 紧凑性
字体缓存中大量存储风格信息:
```cpp
std::map<SkFontStyle, SkTypeface*> cache;  // 每项仅增加 4 字节开销
```

## 使用示例

### 创建和查询
```cpp
// 创建自定义风格
SkFontStyle custom(550, 4, SkFontStyle::kItalic_Slant);  // 半粗半窄斜体

// 使用预定义风格
SkFontStyle bold = SkFontStyle::Bold();

// 提取属性
if (bold.weight() >= SkFontStyle::kBold_Weight) {
    // 处理粗体
}
```

### 字体匹配
```cpp
SkFontMgr* fontMgr = SkFontMgr::RefDefault();
SkFontStyle desired(600, 5, SkFontStyle::kUpright_Slant);  // 期望 SemiBold

sk_sp<SkTypeface> typeface = fontMgr->matchFamilyStyle(
    "Roboto",
    desired
);  // 找到最接近的字体
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/core/SkTypeface.h` | 字体文件,包含 SkFontStyle 描述 |
| `include/core/SkFontMgr.h` | 字体管理器,通过风格匹配字体 |
| `include/core/SkFont.h` | 字体对象,使用风格信息 |
| `include/core/SkFontArguments.h` | 字体参数,可变字体的轴值设置 |
| `include/ports/SkFontMgr_*.h` | 平台字体管理器实现 |
| `src/core/SkFontDescriptor.h` | 字体描述符序列化 |
