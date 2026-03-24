# SkFontMgr

> 源文件：include/core/SkFontMgr.h, src/core/SkFontMgr.cpp

## 概述

SkFontMgr 是 Skia 字体系统的核心管理类,提供字体发现、匹配和加载的抽象接口。它管理系统中的字体族(font families)、字体样式集(font style sets),并实现 CSS3 标准的字体匹配算法。该类采用抽象基类设计,允许不同平台提供特定实现(如 Windows DirectWrite、macOS Core Text、Linux FontConfig 等)。

## 架构位置

```
Skia 字体系统
└── include/core
    ├── SkFontMgr (字体管理器抽象)
    ├── SkFontStyleSet (字体样式集)
    ├── SkTypeface (字体面)
    └── SkFontStyle (字体样式)
        └── 平台实现
            ├── SkFontMgr_win_dw.cpp (Windows DirectWrite)
            ├── SkFontMgr_mac_ct.cpp (macOS Core Text)
            ├── SkFontMgr_fontconfig.cpp (Linux FontConfig)
            └── SkFontMgr_custom.cpp (自定义字体)
```

该类是字体子系统的顶层抽象,为上层文本渲染提供统一接口。

## 主要类与结构体

### SkFontStyleSet (字体样式集)

字体族内的样式变体集合(如 Regular、Bold、Italic 等)。

**继承关系**
- 继承自 SkRefCnt (引用计数)

**关键方法**

| 方法 | 返回类型 | 说明 |
|------|---------|------|
| count() | int | 样式数量 |
| getStyle() | void | 获取指定索引的样式 |
| createTypeface() | sk_sp<SkTypeface> | 创建指定索引的字体面 |
| matchStyle() | sk_sp<SkTypeface> | 匹配最接近的样式 |

**静态工厂方法**

```cpp
static sk_sp<SkFontStyleSet> CreateEmpty()
```

创建空样式集,用于未找到字体族的情况。

**受保护方法**

```cpp
sk_sp<SkTypeface> matchStyleCSS3(const SkFontStyle& pattern)
```

实现 CSS3 字体匹配算法。

### SkFontMgr (字体管理器)

**继承关系**
- 继承自 SkRefCnt

**关键成员变量**

无公开成员,所有状态由子类管理。

## 公共 API 函数

### 字体族枚举

```cpp
int countFamilies() const
void getFamilyName(int index, SkString* familyName) const
sk_sp<SkFontStyleSet> createStyleSet(int index) const
```

遍历系统中的所有字体族。

**用法**
```cpp
for (int i = 0; i < fontMgr->countFamilies(); i++) {
    SkString name;
    fontMgr->getFamilyName(i, &name);
    // 处理字体族 name
}
```

### 字体族匹配

```cpp
sk_sp<SkFontStyleSet> matchFamily(const char familyName[]) const
```

根据名称查找字体族。

**参数**
- familyName: 字体族名称,nullptr 表示默认字体

**返回值**
- 找到: 返回样式集
- 未找到: 返回空样式集(非 nullptr)

**特性**
- 可能返回隐藏或自动激活的字体
- 不同于 createStyleSet(index),范围更广

### 字体样式匹配

```cpp
sk_sp<SkTypeface> matchFamilyStyle(const char familyName[],
                                    const SkFontStyle& style) const
```

查找最接近指定样式的字体。

**参数**
- familyName: 字体族名称
- style: 目标样式(weight/width/slant)

**返回值**
- 成功: 返回字体面
- 失败: 返回 nullptr

### 字符回退匹配

```cpp
sk_sp<SkTypeface> matchFamilyStyleCharacter(
    const char familyName[], const SkFontStyle& style,
    const char* bcp47[], int bcp47Count,
    SkUnichar character) const
```

使用系统字体回退机制查找支持特定字符的字体。

**参数**
- familyName: 优先字体族
- style: 字体样式
- bcp47: 语言代码数组(BCP 47 格式,如 "zh-CN")
- bcp47Count: 语言代码数量
- character: Unicode 字符

**BCP 47 优先级**
- bcp47[0]: 最低优先级
- bcp47[bcp47Count-1]: 最高优先级
- 无匹配时使用任意支持该字符的字体

### 从数据创建字体

```cpp
sk_sp<SkTypeface> makeFromData(sk_sp<SkData> data, int ttcIndex = 0) const
```

从内存数据创建字体。

**参数**
- data: 字体数据(TrueType/OpenType)
- ttcIndex: TTC 集合索引

**返回值**
- 成功: 返回字体面
- 失败: 返回 nullptr(数据无法识别)

### 从流创建字体

```cpp
sk_sp<SkTypeface> makeFromStream(std::unique_ptr<SkStreamAsset> stream,
                                  int ttcIndex = 0) const
sk_sp<SkTypeface> makeFromStream(std::unique_ptr<SkStreamAsset> stream,
                                  const SkFontArguments& args) const
```

从数据流创建字体。

**参数**
- stream: 字体数据流
- ttcIndex: TTC 索引
- args: 字体参数(变体坐标、调色板等)

**所有权**: 转移流的所有权

### 从文件创建字体

```cpp
sk_sp<SkTypeface> makeFromFile(const char path[], int ttcIndex = 0) const
```

从文件路径加载字体。

**参数**
- path: 文件路径
- ttcIndex: TTC 索引

**返回值**
- 成功: 返回字体面
- 失败: 返回 nullptr(文件不存在或格式错误)

### 遗留接口

```cpp
sk_sp<SkTypeface> legacyMakeTypeface(const char familyName[],
                                      SkFontStyle style) const
```

遗留字体创建接口,提供向后兼容。

### 静态工厂方法

```cpp
static sk_sp<SkFontMgr> RefEmpty()
```

返回空字体管理器,所有方法返回空结果。

## 内部实现细节

### CSS3 字体匹配算法

SkFontStyleSet::matchStyleCSS3 实现 CSS3 规范的匹配逻辑:

#### 优先级顺序

1. **宽度(Width)** - 最高优先级
2. **倾斜(Slant)** - 中等优先级
3. **重量(Weight)** - 最低优先级

#### 宽度匹配规则

```cpp
if (pattern.width <= Normal) {
    // 优先选择更窄的
    if (current.width <= pattern.width)
        score += 10 - pattern.width + current.width;
    else
        score += 10 - current.width;
} else {
    // 优先选择更宽的
    if (current.width > pattern.width)
        score += 10 + pattern.width - current.width;
    else
        score += current.width;
}
```

#### 倾斜匹配表

```cpp
static const int score[3][3] = {
    /*           Upright Italic Oblique  [current] */
    /* Upright */ {   3   ,  1   ,   2   },
    /* Italic  */ {   1   ,  3   ,   2   },
    /* Oblique */ {   1   ,  2   ,   3   },
    /* [pattern] */
};
```

#### 重量匹配规则

```cpp
if (weight == current.weight)
    score += 1000;
else if (weight < 400)
    // 优先更轻
    score += (current <= weight) ? 1000 - weight + current
                                 : 1000 - current;
else if (weight <= 500)
    // 400-500 优先更重(最多到 500)
    ...
else
    // >500 优先更重
    ...
```

### 空实现模式

SkEmptyFontMgr 和 SkEmptyFontStyleSet 提供无操作实现:

```cpp
class SkEmptyFontMgr : public SkFontMgr {
    int onCountFamilies() const override { return 0; }
    sk_sp<SkFontStyleSet> onMatchFamily(const char[]) const override {
        return SkFontStyleSet::CreateEmpty();
    }
    // ... 所有方法返回 nullptr 或空值
};
```

### 空值保护

```cpp
static sk_sp<SkFontStyleSet> emptyOnNull(sk_sp<SkFontStyleSet>&& fsset) {
    if (!fsset) {
        fsset = SkFontStyleSet::CreateEmpty();
    }
    return std::move(fsset);
}

// 使用
sk_sp<SkFontStyleSet> SkFontMgr::matchFamily(const char name[]) const {
    return emptyOnNull(this->onMatchFamily(name));
}
```

确保公共 API 永不返回 nullptr。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkTypeface | 字体面表示 |
| SkFontStyle | 字体样式(weight/width/slant) |
| SkData | 内存数据容器 |
| SkStream | 流接口 |
| SkFontArguments | 字体参数传递 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| SkFont | 获取默认字体 |
| SkTextBlob | 文本布局和渲染 |
| SkCanvas::drawText | 文本绘制 |
| Chromium | 网页文本渲染 |
| Android | 系统字体管理 |

## 设计模式与设计决策

### 设计模式

1. **抽象工厂模式**: SkFontMgr 作为字体对象的工厂
2. **策略模式**: 不同平台提供不同字体匹配策略
3. **模板方法模式**: 公共方法调用虚函数实现
4. **单例模式**: RefEmpty() 返回单例空管理器

### 设计决策

1. **为何使用虚函数而非平台宏**
   - 运行时多态,支持多个字体管理器共存
   - 便于测试和模拟
   - 清晰的接口边界

2. **返回空集而非 nullptr**
   - 避免空指针检查
   - 简化调用方代码
   - 统一错误处理

3. **CSS3 匹配算法的原因**
   - Web 标准兼容性
   - 与浏览器行为一致
   - 经过充分验证的算法

4. **字体回退机制**
   - 支持多语言文本渲染
   - 处理稀有字符
   - 遵循平台惯例

5. **引用计数管理**
   - 字体对象生命周期复杂
   - 避免手动内存管理
   - 线程安全共享

## 性能考量

### 性能特征

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| countFamilies | O(1) | 通常缓存结果 |
| matchFamily | O(n) | n = 字体族数量 |
| matchStyle | O(m) | m = 样式数量(通常 < 20) |
| makeFromData | O(k) | k = 字体文件大小 |

### 缓存策略

典型实现会缓存:
- 字体族列表
- 名称到样式集的映射
- 已创建的 SkTypeface 对象

### 性能优化

1. **延迟加载**: 仅在需要时加载字体数据
2. **哈希表查找**: 名称匹配使用哈希表
3. **字体池**: 复用已创建的字体对象
4. **预扫描**: 启动时扫描系统字体目录

### 典型开销

```
系统字体扫描: 100-500 ms (首次)
字体匹配: 0.1-1 ms
字体加载: 1-10 ms
字体创建(缓存命中): 0.01 ms
```

### 内存占用

```cpp
// 典型系统
字体管理器: ~1 KB
字体族缓存: ~100 KB (1000 字体族)
加载的字体面: ~50-200 KB 每个
```

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| include/core/SkTypeface.h | 字体面接口 |
| include/core/SkFontStyle.h | 字体样式定义 |
| src/ports/SkFontMgr_win_dw.cpp | Windows 实现 |
| src/ports/SkFontMgr_mac_ct.cpp | macOS 实现 |
| src/ports/SkFontMgr_fontconfig.cpp | Linux 实现 |
| src/ports/SkFontMgr_custom.cpp | 自定义字体实现 |
| src/ports/SkFontMgr_android.cpp | Android 实现 |
| tests/FontMgrTest.cpp | 单元测试 |
