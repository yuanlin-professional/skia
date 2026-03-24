# SkFontMgr_fontconfig

> 源文件: include/ports/SkFontMgr_fontconfig.h, src/ports/SkFontMgr_fontconfig.cpp

## 概述

SkFontMgr_fontconfig 是 Skia 图形库为 Linux 和其他使用 FontConfig 的系统提供的字体管理器实现。它通过 FontConfig 库与系统字体配置交互，支持字体查询、样式匹配、字符回退和字体枚举。该实现处理 FontConfig 特有的弱引用、样式合成（伪粗体和矩阵变换）、系统根路径（sysroot）和线程安全问题，为 Linux 桌面应用提供标准的字体访问接口。

## 架构位置

该模块位于 Skia 的平台适配层（ports），专门为 FontConfig 系统提供字体管理：

```
skia/
├── include/ports/
│   └── SkFontMgr_fontconfig.h          # 公共接口
└── src/ports/
    ├── SkFontMgr_fontconfig.cpp        # 实现（1020 行）
    └── SkTypeface_proxy.h              # 代理 typeface 基类
```

该模块依赖系统安装的 FontConfig 库（libfontconfig）。

## 主要类与结构体

### 核心类

| 类名 | 继承关系 | 作用 |
|------|---------|------|
| `SkTypeface_fontconfig` | `SkTypeface_proxy` | 封装 FontConfig 模式的代理 typeface |
| `SkFontMgr_fontconfig` | `SkFontMgr` | FontConfig 字体管理器主类 |
| `StyleSet` | `SkFontStyleSet` | 字体家族样式集合 |
| `FCLocker` | - | FontConfig 线程安全锁（按版本条件加锁）|

### 关键成员变量

**SkTypeface_fontconfig:**
| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fPattern` | `SkAutoFcPattern` (mutable) | FontConfig 模式，包含字体元数据 |
| `fOriginalRealStyle` | `SkFontStyle` | 实际字体的原始样式（用于变体克隆）|

**SkFontMgr_fontconfig:**
| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fFC` | `SkAutoFcConfig` (mutable) | FontConfig 配置实例 |
| `fSysroot` | `SkString` | 系统根路径（用于沙箱环境）|
| `fFamilyNames` | `sk_sp<SkDataTable>` | 缓存的字体家族名称列表 |
| `fScanner` | `std::unique_ptr<SkFontScanner>` | 字体扫描器 |
| `fTFCache` | `SkTypefaceCache` | Typeface 缓存 |

**StyleSet:**
| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fFontMgr` | `sk_sp<SkFontMgr_fontconfig>` | 父字体管理器引用 |
| `fFontSet` | `SkAutoFcFontSet` | FontConfig 字体集合 |

## 公共 API 函数

### 工厂函数

```cpp
SK_API sk_sp<SkFontMgr> SkFontMgr_New_FontConfig(
    FcConfig* fc,
    std::unique_ptr<SkFontScanner> scanner
);
```

创建 FontConfig 字体管理器，参数说明：
- **fc**: FontConfig 配置实例，nullptr 则使用新的默认配置
- **scanner**: 字体扫描器实例（必须提供）

注意：该函数会获取 `fc` 的所有权，在析构时调用 `FcConfigDestroy`。

### SkFontMgr 接口实现

```cpp
// 字体家族枚举
int onCountFamilies() const override;
void onGetFamilyName(int index, SkString* familyName) const override;
sk_sp<SkFontStyleSet> onCreateStyleSet(int index) const override;
sk_sp<SkFontStyleSet> onMatchFamily(const char familyName[]) const override;

// 字体匹配
sk_sp<SkTypeface> onMatchFamilyStyle(const char familyName[],
                                     const SkFontStyle& style) const override;
sk_sp<SkTypeface> onMatchFamilyStyleCharacter(const char familyName[],
                                              const SkFontStyle& style,
                                              const char* bcp47[], int bcp47Count,
                                              SkUnichar character) const override;

// 从数据创建 typeface
sk_sp<SkTypeface> onMakeFromData(sk_sp<SkData>, int ttcIndex) const override;
sk_sp<SkTypeface> onMakeFromStreamArgs(std::unique_ptr<SkStreamAsset>,
                                       const SkFontArguments&) const override;
sk_sp<SkTypeface> onMakeFromFile(const char path[], int ttcIndex) const override;
```

## 内部实现细节

### FontConfig 线程安全处理

FontConfig 在 2.10.91 之前非线程安全，2.13.93 之前存在已知问题。`FCLocker` 实现版本检测和条件加锁：

```cpp
class FCLocker {
    inline static constexpr int FontConfigThreadSafeVersion = 21393;  // 2.13.93

    static void lock() SK_NO_THREAD_SAFETY_ANALYSIS {
        if (FcGetVersion() < FontConfigThreadSafeVersion) {
            f_c_mutex().acquire();  // 全局互斥锁
        }
    }
    static void unlock() SK_NO_THREAD_SAFETY_ANALYSIS {
        if (FcGetVersion() < FontConfigThreadSafeVersion) {
            f_c_mutex().release();
        }
    }
public:
    FCLocker() { lock(); }   // RAII 构造时加锁
    ~FCLocker() { unlock(); }  // 析构时解锁
};
```

所有 FontConfig API 调用必须在 `FCLocker` 作用域内执行。

### 弱引用处理

FontConfig 模式中的 `FC_FAMILY` 和 `FC_POSTSCRIPT_NAME` 可以有弱绑定（weak binding），影响匹配优先级。`is_weak` 函数通过创建临时字体集测试绑定强度：

```cpp
static SkWeakReturn is_weak(FcPattern* pattern, const char object[], int id) {
    // 1. 提取指定 ID 的值
    SkAutoFcPattern minimal(FcPatternFilter(pattern, requestedObjectOnly));

    // 2. 创建两个测试模式：
    //    - 强模式：相同值 + nomatchlang
    //    - 弱模式：不同值 + matchlang
    SkAutoFcFontSet fontSet;
    FcFontSetAdd(fontSet, strong.release());
    FcFontSetAdd(fontSet, weak.release());

    // 3. 添加 matchlang 到测试模式
    FcPatternAddLangSet(minimal, FC_LANG, weakLangSet);

    // 4. 执行匹配
    SkAutoFcPattern match(FcFontSetMatch(config, fontSets, ...));

    // 5. 检查匹配结果的语言
    // 如果匹配到 matchlang，则值是弱绑定
    return FcLangEqual == FcLangSetHasLang(matchLangSet, "matchlang")
                        ? kIsWeak_WeakReturn : kIsStrong_WeakReturn;
}
```

`remove_weak` 函数移除最后一个强绑定值之后的所有弱绑定值，确保家族名称匹配的准确性。

### 样式转换

#### FontConfig → Skia

```cpp
static SkFontStyle skfontstyle_from_fcpattern(FcPattern* pattern) {
    // 权重映射（避免 FcWeightToOpenType 2.12.4 之前的 bug）
    static constexpr MapRanges weightRanges[] = {
        { FC_WEIGHT_THIN,       SkFS::kThin_Weight },       // 100
        { FC_WEIGHT_EXTRALIGHT, SkFS::kExtraLight_Weight }, // 200
        { FC_WEIGHT_LIGHT,      SkFS::kLight_Weight },      // 300
        ...
        { FC_WEIGHT_EXTRABLACK, SkFS::kExtraBlack_Weight }, // 950
    };
    SkScalar weight = map_ranges(get_int(pattern, FC_WEIGHT, FC_WEIGHT_REGULAR),
                                 weightRanges, std::size(weightRanges));

    // 宽度和倾斜类似处理
    ...
}
```

使用线性插值处理中间值，确保平滑映射。

#### Skia → FontConfig

```cpp
static void fcpattern_from_skfontstyle(SkFontStyle style, FcPattern* pattern) {
    int weight = map_ranges(style.weight(), weightRanges, std::size(weightRanges));
    int width = map_ranges(style.width(), widthRanges, std::size(widthRanges));
    int slant = ... // 映射 Upright/Italic/Oblique

    FcPatternAddInteger(pattern, FC_WEIGHT, weight);
    FcPatternAddInteger(pattern, FC_WIDTH , width);
    FcPatternAddInteger(pattern, FC_SLANT , slant);
}
```

### 样式合成处理

FontConfig 通过 `FC_EMBOLDEN` 和 `FC_MATRIX` 支持合成样式：

```cpp
void onFilterRec(SkScalerContextRec* rec) const override {
    // 应用 FC_MATRIX（仅用于轮廓字体）
    const FcMatrix* fcMatrix = get_matrix(fPattern, FC_MATRIX);
    bool fcOutline = get_bool(fPattern, FC_OUTLINE, true);
    if (fcOutline && fcMatrix) {
        // FontConfig 矩阵：列主序，右手坐标系（y 向上）
        // Skia 矩阵：列主序，左手坐标系（y 向下）
        SkMatrix fm;
        fm.setAll(fcMatrix->xx, -fcMatrix->xy, 0,
                 -fcMatrix->yx,  fcMatrix->yy, 0,
                  0,             0,            1);
        // 预乘到现有变换
        SkMatrix sm = rec->getMatrixFrom2x2();
        sm.preConcat(fm);
        rec->fPost2x2[0][0] = sm.getScaleX();
        ...
    }

    // 应用 FC_EMBOLDEN
    if (get_bool(fPattern, FC_EMBOLDEN)) {
        rec->fFlags |= SkScalerContext::kEmbolden_Flag;
    }
}
```

### Sysroot 支持

FontConfig 2.11.0+ 支持 sysroot（沙箱根路径），但早期实现有 bug。代码实现兼容策略：

```cpp
bool FontAccessible(FcPattern* font) const {
    const char* filename = get_string(font, FC_FILE, nullptr);

    // 优先尝试 sysroot 路径
    if (!fSysroot.isEmpty()) {
        SkString resolvedFilename = fSysroot;
        resolvedFilename += filename;
        if (sk_exists(resolvedFilename.c_str(), kRead_SkFILE_Flag)) {
            // 使用 SkFontScanner 验证文件可读性
            auto file = SkData::MakeFromFileName(resolvedFilename.c_str());
            return file && fScanner->scanFile(...);
        }
    }

    // 回退到非 sysroot 路径（支持用户添加的本地字体）
    if (sk_exists(filename, kRead_SkFILE_Flag)) {
        ...
    }
    return false;
}
```

### 字体匹配流程

#### 家族样式匹配

```cpp
sk_sp<SkTypeface> onMatchFamilyStyle(const char familyName[],
                                     const SkFontStyle& style) const override {
    FCLocker lock;

    // 1. 创建查询模式
    SkAutoFcPattern pattern;
    FcPatternAddString(pattern, FC_FAMILY, (const FcChar8*)familyName);
    fcpattern_from_skfontstyle(style, pattern);

    // 2. 应用配置替换和默认值
    FcConfigSubstitute(fFC, pattern, FcMatchPattern);
    FcDefaultSubstitute(pattern);

    // 3. 移除弱家族名称（如果指定了家族）
    FcPattern* matchPattern;
    SkAutoFcPattern strongPattern(nullptr);
    if (familyName) {
        strongPattern.reset(FcPatternDuplicate(pattern));
        remove_weak(strongPattern, FC_FAMILY);
        matchPattern = strongPattern;
    } else {
        matchPattern = pattern;
    }

    // 4. 执行匹配
    FcResult result;
    SkAutoFcPattern font(FcFontMatch(fFC, pattern, &result));

    // 5. 验证匹配结果
    if (!font || !FontFamilyNameMatches(font, matchPattern) || !FontAccessible(font)) {
        return nullptr;
    }

    return createTypefaceFromFcPattern(std::move(font));
}
```

#### 字符回退匹配

```cpp
sk_sp<SkTypeface> onMatchFamilyStyleCharacter(..., SkUnichar character) const override {
    FCLocker lock;

    // 1. 创建查询模式（家族名使用弱绑定）
    SkAutoFcPattern pattern;
    FcValue familyNameValue;
    familyNameValue.type = FcTypeString;
    familyNameValue.u.s = reinterpret_cast<const FcChar8*>(familyName);
    FcPatternAddWeak(pattern, FC_FAMILY, familyNameValue, FcFalse);

    // 2. 添加字符集要求
    SkAutoFcCharSet charSet;
    FcCharSetAddChar(charSet, character);
    FcPatternAddCharSet(pattern, FC_CHARSET, charSet);

    // 3. 添加语言标签（BCP-47）
    if (bcp47Count > 0) {
        SkAutoFcLangSet langSet;
        for (int i = bcp47Count; i --> 0;) {
            FcLangSetAdd(langSet, (const FcChar8*)bcp47[i]);
        }
        FcPatternAddLangSet(pattern, FC_LANG, langSet);
    }

    // 4. 执行匹配
    FcResult result;
    SkAutoFcPattern font(FcFontMatch(fFC, pattern, &result));

    // 5. 验证字体包含该字符
    if (!font || !FontContainsCharacter(font, character) || !FontAccessible(font)) {
        return nullptr;
    }

    return createTypefaceFromFcPattern(std::move(font));
}
```

### Typeface 缓存

使用双重缓存策略：

```cpp
sk_sp<SkTypeface> createTypefaceFromFcPattern(SkAutoFcPattern pattern) const {
    SkAutoMutexExclusive ama(fTFCacheMutex);

    // 1. 查找缓存（需要持有 FCLocker）
    sk_sp<SkTypeface> face = [&]() {
        FCLocker lock;
        sk_sp<SkTypeface> face = fTFCache.findByProcAndRef(FindByFcPattern, pattern);
        if (face) {
            pattern.reset();  // 在 FCLocker 作用域内释放
        }
        return face;
    }();

    // 2. 未命中则创建
    if (!face) {
        face = SkTypeface_fontconfig::Make(std::move(pattern), fSysroot, fScanner.get());
        if (face) {
            fTFCache.add(face);
        }
    }

    return face;
}
```

缓存查找使用 `FcPatternEqual` 比较模式内容。

### 字体家族枚举

`GetFamilyNames` 遍历系统和应用字体集：

```cpp
static sk_sp<SkDataTable> GetFamilyNames(FcConfig* fcconfig) {
    FCLocker lock;
    SkTDArray<const char*> names;

    // 遍历 FcSetSystem 和 FcSetApplication
    static const FcSetName fcNameSet[] = { FcSetSystem, FcSetApplication };
    for (int setIndex = 0; setIndex < std::size(fcNameSet); ++setIndex) {
        FcFontSet* allFonts = FcConfigGetFonts(fcconfig, fcNameSet[setIndex]);

        for (int fontIndex = 0; fontIndex < allFonts->nfont; ++fontIndex) {
            FcPattern* current = allFonts->fonts[fontIndex];
            // 提取所有 FC_FAMILY 值
            for (int id = 0; ; ++id) {
                FcChar8* fcFamilyName;
                FcResult result = FcPatternGetString(current, FC_FAMILY, id, &fcFamilyName);
                if (FcResultNoId == result) break;
                if (FcResultMatch != result) continue;

                // 去重添加
                const char* familyName = reinterpret_cast<const char*>(fcFamilyName);
                if (familyName && !FindName(names, familyName)) {
                    *names.append() = familyName;
                }
            }
        }
    }

    return SkDataTable::MakeCopyArrays(...);
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| FontConfig (libfontconfig) | 系统字体配置和查询 |
| `SkFontScanner` | 字体文件元数据扫描 |
| `SkTypeface_proxy` | 代理模式基类 |
| `SkFontDescriptor` | 字体描述符序列化 |
| `SkTypefaceCache` | Typeface 缓存管理 |
| `SkOSFile` | 文件系统操作 |

### 被依赖的模块

该模块通过工厂函数被上层字体管理系统使用，在 Linux 桌面环境中作为默认字体管理器。

## 设计模式与设计决策

### 设计模式

1. **工厂模式**: `SkFontMgr_New_FontConfig` 工厂函数
2. **代理模式**: `SkTypeface_fontconfig` 封装实际 typeface 并应用 FontConfig 属性
3. **缓存模式**: Typeface 缓存减少重复加载
4. **RAII**: `FCLocker` 自动管理锁生命周期
5. **策略模式**: 通过 `SkFontScanner` 支持不同扫描策略

### 设计决策

1. **独立配置**: 使用独立的 FcConfig 实例而非全局默认配置，避免冲突
2. **线程安全**: 运行时检测 FontConfig 版本，条件加锁
3. **弱引用处理**: 主动移除弱绑定，确保家族名称匹配准确性
4. **Sysroot 兼容**: 支持沙箱环境，同时兼容本地字体
5. **样式合成**: 保留 FontConfig 的伪粗体和矩阵变换信息
6. **可访问性验证**: 使用 `SkFontScanner` 验证字体文件可读性
7. **CSS 映射**: 不进行 CSS 通用家族映射（与 Mac 实现不同）

### 平台特定考虑

- **Linux 桌面**: 标准 FontConfig 配置路径（~/.fonts, /usr/share/fonts 等）
- **沙箱环境**: 通过 sysroot 支持容器和沙箱
- **版本兼容**: 兼容 FontConfig 2.10.91+ 的多个版本

## 性能考量

### 性能优化

1. **家族名称缓存**: 启动时枚举一次，存储在 `fFamilyNames`
2. **Typeface 缓存**: 避免重复解析相同模式
3. **懒加载**: 仅在需要时才加载字体数据
4. **模式过滤**: 使用 `FcPatternFilter` 提取最小模式，加速比较
5. **锁粒度**: 仅在必要时持有 FCLocker，缩短临界区

### 内存优化

- **共享模式**: 多个操作共享 FcPattern 实例（mutable 成员）
- **字符串复用**: `SkDataTable` 高效存储家族名称
- **引用计数**: 自动管理 FontConfig 对象生命周期

### 潜在瓶颈

1. **全局锁**: FontConfig < 2.13.93 时所有调用串行化
2. **弱引用检测**: `is_weak` 需要创建临时字体集和匹配，开销较大
3. **文件系统访问**: `FontAccessible` 验证涉及文件 I/O
4. **枚举开销**: `GetFamilyNames` 在大字体集上较慢

### 优化建议

- 升级到 FontConfig 2.13.93+ 避免全局锁
- 缓存弱引用检测结果
- 使用异步字体加载
- 延迟家族名称枚举

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/ports/SkFontMgr_fontconfig.h` | 公共接口定义 |
| `src/ports/SkFontMgr_fontconfig.cpp` | 实现文件（1020 行）|
| `src/ports/SkTypeface_proxy.h` | 代理 typeface 基类 |
| `src/core/SkFontDescriptor.h` | 字体描述符 |
| `src/core/SkTypefaceCache.h` | Typeface 缓存 |
| `src/core/SkOSFile.h` | 文件系统操作 |
| `include/core/SkFontMgr.h` | 字体管理器抽象基类 |
| `include/core/SkFontScanner.h` | 字体扫描器接口 |
| FontConfig `<fontconfig/fontconfig.h>` | FontConfig C API |
