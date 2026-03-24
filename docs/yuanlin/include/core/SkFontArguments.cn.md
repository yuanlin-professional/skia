# SkFontArguments

> 源文件: `include/core/SkFontArguments.h`

## 概述

SkFontArguments 是 Skia 字体系统中用于指定字体实例化参数的配置结构体。它封装了字体集合索引、可变字体轴坐标、调色板选择、合成样式等参数,使得从字体文件流创建 SkTypeface 时能够精确控制字体的变体和外观。该结构是连接字体文件和字体对象的桥梁。

## 架构位置

SkFontArguments 位于 Skia 核心层 (`include/core`),属于字体子系统的参数配置层。它被 SkFontMgr、SkTypeface 工厂方法以及字体扫描器(SkFontScanner)使用,定义了字体创建时的标准参数格式。

## 主要结构体

### SkFontArguments

**职责**: 聚合字体实例化所需的所有参数,提供链式配置接口。

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fCollectionIndex | int | 字体集合中的字体索引(TTC 文件支持) |
| fVariationDesignPosition | VariationPosition | 可变字体的轴坐标数组 |
| fPalette | Palette | 彩色字体的调色板配置 |
| fSyntheticBold | std::optional<bool> | 是否合成粗体 |
| fSyntheticOblique | std::optional<bool> | 是否合成倾斜 |

### VariationPosition 结构体

**职责**: 定义可变字体在设计空间中的位置。

**内嵌结构 Coordinate**:
| 成员变量 | 类型 | 说明 |
|---------|------|------|
| axis | SkFourByteTag | 轴标签(如 'wght' 表示字重) |
| value | float | 该轴上的坐标值 |

**成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| coordinates | const Coordinate* | 坐标数组指针(不拥有所有权) |
| coordinateCount | int | 坐标数量 |

### Palette 结构体

**职责**: 指定彩色字体(COLR/CPAL 表)的调色板和颜色覆盖。

**内嵌结构 Override**:
| 成员变量 | 类型 | 说明 |
|---------|------|------|
| index | uint16_t | 调色板条目索引 |
| color | SkColor | 覆盖颜色值 |

**成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| index | int | 使用的调色板索引(字体可定义多个调色板) |
| overrides | const Override* | 颜色覆盖数组指针 |
| overrideCount | int | 覆盖数量 |

## 公共 API 函数

### 构造函数

#### `SkFontArguments()`
- **功能**: 默认构造函数,初始化为零值
- **默认值**:
  - `fCollectionIndex = 0`
  - `fVariationDesignPosition = {nullptr, 0}`
  - `fPalette = {0, nullptr, 0}`
  - `fSyntheticBold = std::nullopt`
  - `fSyntheticOblique = std::nullopt`

### 配置方法(链式调用)

#### `SkFontArguments& setCollectionIndex(int collectionIndex)`
- **功能**: 设置字体集合索引,用于 TTC/OTC/DFont 等多字体文件
- **参数**: `collectionIndex` - 字体索引(0 到 numFaces-1)
- **返回值**: 自身引用,支持链式调用
- **用途**:
  - TrueType Collection(.ttc): 包含多个独立字体
  - OpenType Collection(.otc): 多个 OpenType 字体
  - Datafork Font(.dfont): macOS 旧格式

#### `SkFontArguments& setVariationDesignPosition(VariationPosition position)`
- **功能**: 设置可变字体的轴坐标
- **参数**: `position` - 轴坐标数组(引用外部数据,不复制)
- **返回值**: 自身引用
- **注意**: 传入的坐标数组必须在 SkFontArguments 生命周期内保持有效
- **说明**:
  - 未指定的轴使用默认值
  - 字体中不存在的轴会被忽略

#### `SkFontArguments& setPalette(Palette palette)`
- **功能**: 设置彩色字体的调色板和覆盖
- **参数**: `palette` - 调色板配置(引用外部数据)
- **返回值**: 自身引用
- **说明**:
  - 超出范围的覆盖索引会被忽略
  - 后面的覆盖会覆盖前面的相同索引

#### `SkFontArguments& setSyntheticBold(std::optional<bool> bold)`
- **功能**: 设置是否合成粗体效果
- **参数**: `bold` - true 启用,false 禁用,nullopt 使用默认行为
- **返回值**: 自身引用
- **用途**: 当字体文件不包含粗体变体时合成粗体

#### `SkFontArguments& setSyntheticOblique(std::optional<bool> oblique)`
- **功能**: 设置是否合成倾斜效果
- **参数**: `oblique` - true 启用,false 禁用,nullopt 使用默认行为
- **返回值**: 自身引用
- **用途**: 当字体文件不包含斜体变体时合成倾斜

### 访问器

#### `int getCollectionIndex() const`
- **功能**: 获取字体集合索引
- **返回值**: 当前设置的索引值

#### `VariationPosition getVariationDesignPosition() const`
- **功能**: 获取可变字体轴坐标
- **返回值**: VariationPosition 结构体

#### `Palette getPalette() const`
- **功能**: 获取调色板配置
- **返回值**: Palette 结构体

#### `std::optional<bool> getSyntheticBold() const`
- **功能**: 获取合成粗体设置
- **返回值**: optional 包装的布尔值

#### `std::optional<bool> getSyntheticOblique() const`
- **功能**: 获取合成倾斜设置
- **返回值**: optional 包装的布尔值

## 使用场景

### 可变字体实例化
```cpp
// 创建特定字重和字宽的字体实例
SkFontArguments::VariationPosition::Coordinate coords[] = {
    {SkSetFourByteTag('w','g','h','t'), 650.0f},  // 字重 650
    {SkSetFourByteTag('w','d','t','h'), 80.0f}    // 字宽 80%
};

SkFontArguments args;
args.setVariationDesignPosition({coords, 2});

auto stream = SkStream::MakeFromFile("Roboto-VF.ttf");
sk_sp<SkTypeface> typeface = SkTypeface::MakeFromStream(std::move(stream), args);
```

### TTC 字体选择
```cpp
// 从 TTC 文件中选择第二个字体
SkFontArguments args;
args.setCollectionIndex(1);

auto stream = SkStream::MakeFromFile("fonts.ttc");
sk_sp<SkTypeface> typeface = SkTypeface::MakeFromStream(std::move(stream), args);
```

### 彩色字体调色板
```cpp
// 使用调色板 2 并覆盖特定颜色
SkFontArguments::Palette::Override overrides[] = {
    {0, SK_ColorRED},   // 第 0 号颜色改为红色
    {5, SK_ColorBLUE}   // 第 5 号颜色改为蓝色
};

SkFontArguments args;
args.setPalette({2, overrides, 2});

auto stream = SkStream::MakeFromFile("emoji.ttf");
sk_sp<SkTypeface> typeface = SkTypeface::MakeFromStream(std::move(stream), args);
```

### 合成样式
```cpp
// 对常规字体合成粗斜体效果
SkFontArguments args;
args.setSyntheticBold(true)
    .setSyntheticOblique(true);

auto stream = SkStream::MakeFromFile("Regular.ttf");
sk_sp<SkTypeface> typeface = SkTypeface::MakeFromStream(std::move(stream), args);
```

### 链式配置
```cpp
SkFontArguments::VariationPosition::Coordinate coords[] = {
    {SkSetFourByteTag('w','g','h','t'), 700.0f}
};

SkFontArguments args;
args.setCollectionIndex(0)
    .setVariationDesignPosition({coords, 1})
    .setSyntheticBold(false);  // 链式调用
```

## 内部实现细节

### 非拥有指针设计
VariationPosition 和 Palette 使用指针引用外部数据:
```cpp
// 调用者负责数据生命周期管理
Coordinate coords[2] = {...};
args.setVariationDesignPosition({coords, 2});  // 不复制 coords
// coords 必须在使用 args 期间保持有效
```

**设计原因**:
- 避免堆分配和复制开销
- 通常坐标数量少(1-5 个),栈分配即可
- 字体创建是短期操作,数据不需要长期持有

### std::optional 语义
合成样式使用 optional:
- `std::nullopt`: 使用平台默认行为
- `true`: 强制启用合成
- `false`: 强制禁用合成

### 参数验证
字体创建实现会验证参数:
- 集合索引超出范围 → 失败或使用索引 0
- 无效轴标签 → 忽略该坐标
- 调色板索引无效 → 使用默认调色板(索引 0)

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| SkColor.h | SkColor 类型定义 |
| SkFourByteTag.h | 四字符轴标签 |
| SkTypes.h | 基础类型定义 |
| <optional> | std::optional 支持 |

### 被依赖的模块
| 模块 | 用途 |
|------|------|
| SkTypeface | 字体对象,使用 Arguments 创建实例 |
| SkFontMgr | 字体管理器,传递参数给字体创建方法 |
| SkFontScanner | 字体扫描器,使用 Arguments 扫描特定实例 |

## 设计模式与设计决策

### 建造者模式
链式调用支持逐步配置:
```cpp
SkFontArguments()
    .setCollectionIndex(0)
    .setVariationDesignPosition(...)
    .setPalette(...)
    .setSyntheticBold(true);
```

### 零拷贝设计
避免不必要的内存分配:
- 坐标数组通常很小,栈分配足够
- 指针引用减少复制开销
- 适合短期使用场景(字体创建后即丢弃参数)

### 可选参数模式
使用 std::optional 区分"未设置"和"设置为 false":
```cpp
// 未设置:使用平台默认行为
args.setSyntheticBold(std::nullopt);

// 设置为 false:明确禁用
args.setSyntheticBold(false);
```

### 扩展性
结构体可轻松添加新字段:
- 未来可能添加:子像素定位、字形缓存提示等
- 兼容性:旧代码使用默认构造函数仍可工作

## 性能考量

### 栈分配
典型使用无堆分配:
```cpp
// 全部在栈上
SkFontArguments::VariationPosition::Coordinate coords[4];
SkFontArguments args;
args.setVariationDesignPosition({coords, 4});
```

### 延迟应用
参数仅在字体创建时解析:
```cpp
// 配置阶段:仅赋值指针,无计算
args.setVariationDesignPosition({coords, 100});

// 使用阶段:解析并应用参数
auto typeface = SkTypeface::MakeFromStream(stream, args);
```

### 参数传递
轻量级结构,按值传递开销低:
```cpp
void CreateFont(SkFontArguments args) {  // 按值传递
    // sizeof(SkFontArguments) ≈ 40 字节
}
```

## 平台相关说明

### 可变字体轴的平台支持
| 平台 | API | 支持的轴 |
|------|-----|---------|
| CoreText | CTFontCreateWithFontDescriptor | 所有注册轴 + 自定义轴 |
| DirectWrite | IDWriteFontFace5::CreateFontFace | wght/wdth/slnt/ital + 自定义 |
| FreeType | FT_Set_Var_Design_Coordinates | 完整 OpenType Variations 支持 |

### 合成样式的平台差异
- **Windows**: DirectWrite 自动合成粗体/斜体
- **macOS**: CoreText 需手动应用倾斜变换
- **FreeType**: 由 Skia 层合成(通过矩阵变换)

### 彩色字体格式
| 格式 | 调色板支持 | 说明 |
|------|-----------|------|
| COLR/CPAL (v0) | ✓ | 矢量彩色字形,多调色板 |
| COLR/CPAL (v1) | ✓ | 支持渐变和混合 |
| SBIX | ✗ | PNG 位图,无调色板概念 |
| CBDT/CBLC | ✗ | 嵌入式位图 |

## 错误处理

### 无效索引
```cpp
args.setCollectionIndex(999);  // 超出范围
// 行为:字体创建失败返回 nullptr,或回退到索引 0
```

### 无效轴坐标
```cpp
Coordinate coords[] = {
    {SkSetFourByteTag('X','Y','Z','Z'), 100.0f}  // 不存在的轴
};
args.setVariationDesignPosition({coords, 1});
// 行为:忽略无效坐标,使用字体默认值
```

### 悬空指针
```cpp
{
    Coordinate coords[] = {{...}};
    args.setVariationDesignPosition({coords, 1});
}  // coords 作用域结束
// 使用 args 创建字体 → 未定义行为(访问悬空指针)
```

## 最佳实践

### 推荐写法
```cpp
// 坐标数组与 args 在同一作用域
SkFontArguments::VariationPosition::Coordinate coords[] = {
    {SkSetFourByteTag('w','g','h','t'), 600.0f}
};
SkFontArguments args;
args.setVariationDesignPosition({coords, 1});

auto typeface = CreateTypeface(args);  // 立即使用
```

### 避免的写法
```cpp
SkFontArguments CreateArgs() {
    Coordinate coords[] = {{...}};
    SkFontArguments args;
    args.setVariationDesignPosition({coords, 1});
    return args;  // 危险:返回后 coords 失效
}
```

### 合成样式的选择
```cpp
// 优先使用真实字体变体
if (HasBoldVariant(fontFamily)) {
    // 加载 Bold.ttf
} else {
    // 合成粗体
    args.setSyntheticBold(true);
}
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/core/SkTypeface.h` | 字体对象,MakeFromStream 使用 Arguments |
| `include/core/SkFontMgr.h` | 字体管理器,makeFromStream 使用 Arguments |
| `include/core/SkFontScanner.h` | 字体扫描器,MakeFromStream 使用 Arguments |
| `include/core/SkFontParameters.h` | 可变轴定义,Coordinate 引用其标签 |
| `include/core/SkFourByteTag.h` | 四字符标签工具 |
| `include/core/SkColor.h` | 颜色定义,用于调色板覆盖 |
| `src/ports/SkFontHost_*.cpp` | 平台实现,解析并应用 Arguments |
