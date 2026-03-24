# SkFontConfigInterfaceDirect - FontConfig 直接接口

> 源文件:
> - `src/ports/SkFontConfigInterface_direct.h`
> - `src/ports/SkFontConfigInterface_direct.cpp`

## 概述

`SkFontConfigInterfaceDirect` 是 Skia 在 Linux/Unix 平台上直接使用 FontConfig 库进行字体匹配和加载的实现。它通过 FontConfig API 根据字体族名和样式查找系统字体，并提供流式访问字体文件的能力。

该实现处理了 FontConfig 的线程安全问题、度量兼容字体替换、字体等价类匹配等复杂场景，确保字体匹配行为与浏览器预期一致。

## 架构位置

```
SkFontConfigInterface (include/ports/)   // 抽象接口
  |
  v
SkFontConfigInterfaceDirect (src/ports/)  // 本类
  |
  v
FontConfig (libfontconfig)                // 系统字体配置库
```

## 主要类与结构体

### `SkFontConfigInterfaceDirect`

继承自 `SkFontConfigInterface`。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fFC` | `FcConfig* const` | FontConfig 配置实例（拥有所有权） |

### `FontIdentity` (基类定义)

```cpp
struct FontIdentity {
    uint32_t fID;
    int32_t fTTCIndex;
    SkString fString;   // 字体文件路径
    SkFontStyle fStyle;
};
```

支持二进制序列化/反序列化（`writeToMemory` / `readFromMemory`）。

### `FCLocker` (内部)

处理 FontConfig 线程安全的 RAII 锁：
- FontConfig 在版本 2.13.93 之前不是线程安全的
- `FontConfigThreadSafeVersion = 21393`
- 低于此版本时使用全局互斥锁

### `FontEquivClass` (内部)

字体等价类枚举，用于度量兼容字体替换：

| 等价类 | 包含字体 |
|--------|---------|
| `SANS` | Arial, Arimo, Liberation Sans |
| `SERIF` | Times New Roman, Tinos, Liberation Serif |
| `MONO` | Courier New, Cousine, Liberation Mono |
| `PGOTHIC` | MS PGothic, Noto Sans CJK JP, IPAPGothic |
| `SIMSUN` | Simsun (宋体), Noto Serif CJK SC |
| `SIMHEI` | Simhei (黑体), Noto Sans CJK SC |
| 等 | ... |

## 公共 API 函数

### 构造函数

```cpp
explicit SkFontConfigInterfaceDirect(FcConfig* fc);
```

接受一个 FontConfig 实例，取得所有权。若为 nullptr，每次方法调用使用当前配置。

### `matchFamilyName()`

```cpp
bool matchFamilyName(const char familyName[],
                     SkFontStyle requested,
                     FontIdentity* outFontIdentifier,
                     SkString* outFamilyName,
                     SkFontStyle* outStyle) override;
```

根据字体族名和样式查找匹配字体。

### `openStream()`

```cpp
SkStreamAsset* openStream(const FontIdentity&) override;
```

打开字体文件为流。

## 内部实现细节

### 字体样式映射

`skfontstyle_from_fcpattern()` 和 `fcpattern_from_skfontstyle()` 在 Skia 字体样式和 FontConfig 样式之间进行双向映射：

**权重映射（SkFontStyle <-> FC_WEIGHT）：**
- `kThin_Weight(100)` <-> `FC_WEIGHT_THIN`
- `kNormal_Weight(400)` <-> `FC_WEIGHT_REGULAR`
- `kBold_Weight(700)` <-> `FC_WEIGHT_BOLD`
- 使用分段线性插值（`map_ranges`）

**宽度映射（SkFontStyle <-> FC_WIDTH）：**
- `kUltraCondensed_Width(1)` <-> `FC_WIDTH_ULTRACONDENSED`
- `kNormal_Width(5)` <-> `FC_WIDTH_NORMAL`

**倾斜映射：**
- `kUpright_Slant` <-> `FC_SLANT_ROMAN`
- `kItalic_Slant` <-> `FC_SLANT_ITALIC`
- `kOblique_Slant` <-> `FC_SLANT_OBLIQUE`

### 度量兼容字体替换

`GetFontEquivClass()` 将字体名映射到等价类。`IsMetricCompatibleReplacement()` 判断两个字体是否在视觉和度量级别可互换。

这用于防止 FontConfig 返回度量不兼容的替代字体（例如，请求 Arial 时只接受 Arimo 或 Liberation Sans 等度量兼容替代品）。

### 回退字体策略

`IsFallbackFontAllowed()` 判断是否允许回退到通用字体。仅在请求空名称或通用名称（"sans"、"serif"、"monospace"）时允许回退。

### FontIdentity 序列化

`FontIdentity::writeToMemory()` / `readFromMemory()` 实现二进制序列化：
- 格式：ID(4) + TTCIndex(4) + strLen(4) + weight(4) + width(4) + slant(1) + string(变长) + pad(对齐到4)

## 依赖关系

### 系统依赖

- `libfontconfig`：系统字体配置库
- `<unistd.h>`：POSIX 文件操作

### Skia 内部

- `SkFontConfigInterface`：抽象基类
- `SkFontStyle`：字体样式
- `SkStream`：文件流
- `SkMutex`：互斥锁
- `SkBuffer`：二进制读写缓冲区

## 设计模式与设计决策

1. **条件锁**：根据 FontConfig 版本决定是否使用互斥锁，新版本无需锁
2. **等价类硬编码**：字体等价类使用硬编码映射表而非依赖 FontConfig 的匹配强度信息
3. **CJK 字体覆盖**：等价类表覆盖了大量 CJK 字体的等价关系（MS Gothic <-> Noto Sans CJK 等）
4. **保守匹配**：默认不允许回退，仅接受精确匹配或度量兼容替代

## 性能考量

1. **FCLocker 条件锁**：新版 FontConfig 无锁开销
2. **等价类查找**：线性遍历查找表（约 50 条目），注释建议热点时可改用哈希表
3. **FontConfig 查询缓存**：依赖 FontConfig 自身的缓存机制
4. **二进制序列化**：`FontIdentity` 序列化使用紧凑的二进制格式，最小化 IPC 开销

### matchFamilyName 内部流程

```
输入: familyName + SkFontStyle
  |
  v
fcpattern_from_skfontstyle()  -> 创建 FcPattern
  |
  v
FcConfigSubstitute()          -> 应用 FontConfig 替换规则
FcDefaultSubstitute()         -> 应用默认值
  |
  v
FcFontSort()                  -> 获取匹配字体列表
  |
  v
MatchFont()                   -> 从列表中选择最佳匹配
  |  包含等价类检查 (IsMetricCompatibleReplacement)
  |  包含回退策略 (IsFallbackFontAllowed)
  |  包含文件可访问性检查 (isAccessible)
  v
输出: FontIdentity + familyName + SkFontStyle
```

### openStream 实现

`openStream()` 通过 `FontIdentity::fString` 中存储的文件路径打开字体文件。对于 TTC 文件，`FontIdentity::fTTCIndex` 指定集合中的字体索引。

### MatchFont 选择策略

`MatchFont()` 从 FontConfig 返回的排序字体列表中选择匹配：

1. 检查候选字体的 `FC_FILE` 和 `FC_FONT_WRAPPER` 属性
2. 验证字体文件是否可访问（`isAccessible`）
3. 检查是否为度量兼容替代品
4. 若请求的是具体字体名称且候选不是度量兼容的，跳过
5. 返回第一个通过所有检查的字体

### FontConfig 版本兼容

该实现需要处理三个 FontConfig 时代：

| 版本范围 | 线程安全性 | 处理方式 |
|---------|-----------|---------|
| < 2.10.91 | 线程对抗 | 全局互斥锁 |
| 2.10.91 - 2.13.92 | 已知问题 | 全局互斥锁 |
| >= 2.13.93 | 线程安全 | 无锁 |

### SFNT 字体格式过滤

当定义了 `SK_FONT_CONFIG_INTERFACE_ONLY_ALLOW_SFNT_FONTS` 时，仅接受 TrueType 和 CFF 格式的字体文件，过滤掉 Type1 等旧格式。

## 相关文件

- `include/ports/SkFontConfigInterface.h` - 抽象接口
- `src/ports/SkFontMgr_fontconfig.cpp` - FontConfig 字体管理器
- `src/base/SkBuffer.h` - 二进制缓冲区
- `src/base/SkAutoMalloc.h` - 自动内存管理
- `include/core/SkFontStyle.h` - 字体样式
