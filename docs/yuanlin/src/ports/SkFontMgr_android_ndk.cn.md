# SkFontMgr_android_ndk

> 源文件: include/ports/SkFontMgr_android_ndk.h, src/ports/SkFontMgr_android_ndk.cpp

## 概述

`SkFontMgr_android_ndk` 是 Skia 图形库为 Android NDK 平台提供的字体管理器实现。该模块通过 Android NDK Font API（从 Android 10/API 29 引入，但 API 30+ 才完全可用）来访问系统字体资源，支持字体的查找、匹配和实例化。由于 Android NDK Font API 在 Android 10 中存在 `AFont_getLocale` 的缺陷（返回空指针或无效指针），该字体管理器仅在 Android 11 (API 30) 及以上版本正常工作。

该实现能够自动枚举系统字体，解析字体变体轴（如 `wght`、`wdth`、`slnt`、`ital`），并根据语言标签（BCP-47）、字符覆盖范围和样式需求进行字体回退匹配。

## 架构位置

```
skia/
├── include/
│   └── ports/
│       └── SkFontMgr_android_ndk.h    # 公共接口
└── src/
    └── ports/
        ├── SkFontMgr_android_ndk.cpp   # 主实现
        ├── SkFontMgr_android_parser.h   # XML 解析器（依赖）
        └── SkTypeface_proxy.h           # 代理字体类型（依赖）
```

该模块位于 `ports` 层，为 Android NDK 平台提供字体管理抽象，是跨平台字体系统的一部分。

## 主要类与结构体

### SkFontMgr_android_ndk

创建 Android NDK 字体管理器的工厂函数。

**继承关系:**
- 无直接类定义（通过工厂函数返回 `SkFontMgr` 实例）

**关键函数:**
```cpp
SK_API sk_sp<SkFontMgr> SkFontMgr_New_AndroidNDK(
    bool cacheFontFiles,
    std::unique_ptr<SkFontScanner> scanner
);
```

### AndroidFontAPI

封装 Android NDK Font API 的函数指针结构体。

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `ASystemFontIterator_open` | 函数指针 | 打开系统字体迭代器 |
| `ASystemFontIterator_close` | 函数指针 | 关闭系统字体迭代器 |
| `ASystemFontIterator_next` | 函数指针 | 获取下一个字体 |
| `AFont_close` | 函数指针 | 关闭字体句柄 |
| `AFont_getFontFilePath` | 函数指针 | 获取字体文件路径 |
| `AFont_getWeight` | 函数指针 | 获取字体粗细 |
| `AFont_isItalic` | 函数指针 | 判断是否斜体 |
| `AFont_getLocale` | 函数指针 | 获取语言区域标签 |
| `AFont_getCollectionIndex` | 函数指针 | 获取 TTC 索引 |
| `AFont_getAxisCount` | 函数指针 | 获取变体轴数量 |
| `AFont_getAxisTag` | 函数指针 | 获取变体轴标签 |
| `AFont_getAxisValue` | 函数指针 | 获取变体轴值 |

### AndroidIcuAPI

封装 ICU 库的字符串大小写折叠（case folding）API。

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `u_strFoldCase` | 函数指针 | Unicode 大小写折叠 |
| `u_strFromUTF8` | 函数指针 | UTF-8 转 UTF-16 |
| `u_strToUTF8` | 函数指针 | UTF-16 转 UTF-8 |
| `fHasICU` | bool | 是否成功加载 ICU |

### SkTypeface_AndroidNDK

Android NDK 字体类型的代理实现。

**继承关系:**
- 继承自 `SkTypeface_proxy`

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fFamilyName` | SkString | 字体族名称 |
| `fExtraFamilyNames` | TArray<SkString> | 额外的字体族名称（别名） |
| `fLang` | STArray<4, SkALanguage> | 支持的语言标签列表 |
| `fAutoAxis` | AutoAxis | 自动调整的变体轴标志 |

### SkFontStyleSet_AndroidNDK

字体样式集合的 Android NDK 实现。

**继承关系:**
- 继承自 `SkFontStyleSet`

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fStyles` | TArray<sk_sp<SkTypeface_AndroidNDK>> | 样式列表 |
| `fCache` | sk_sp<TypefaceCache> | 字体实例缓存 |

### SkFontMgr_AndroidNDK

Android NDK 字体管理器的核心实现类。

**继承关系:**
- 继承自 `SkFontMgr`

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fAPI` | AndroidFontAPI | Android Font API 接口 |
| `fICU` | AndroidIcuAPI | ICU API 接口 |
| `fScanner` | std::unique_ptr<SkFontScanner> | 字体扫描器 |
| `fStyleSets` | TArray<sk_sp<SkFontStyleSet_AndroidNDK>> | 所有字体样式集 |
| `fFallbackStyleSets` | TArray<SkFontStyleSet_AndroidNDK*> | 回退字体列表 |
| `fNameToFamilyMap` | TArray<NameToFamily> | 名称到字体族的映射 |
| `fDefaultStyleSet` | sk_sp<SkFontStyleSet> | 默认字体集 |
| `fCache` | sk_sp<TypefaceCache> | 字体缓存 |

### TypefaceCache

字体实例的 LRU 缓存，支持两种查找方式：按请求（样式）和按匹配（变体轴配置）。

**继承关系:**
- 继承自 `SkRefCnt`

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fRequests` | SkLRUCache<Request, sk_sp<SkTypeface>> | 按请求的缓存 |
| `fMatches` | SkLRUCache<Match, sk_sp<SkTypeface>> | 按变体匹配的缓存 |
| `fMutex` | SkSharedMutex | 线程安全锁 |

### SkALanguage

BCP-47 语言标签解析器，将语言标签分解为语言、脚本、区域组件。

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fLanguage` | SkString | 语言代码（如 "zh"） |
| `fScript` | SkString | 脚本代码（如 "Hans"） |
| `fRegion` | SkString | 区域代码（如 "CN"） |

## 公共 API 函数

### SkFontMgr_New_AndroidNDK

```cpp
SK_API sk_sp<SkFontMgr> SkFontMgr_New_AndroidNDK(
    bool cacheFontFiles,
    std::unique_ptr<SkFontScanner> scanner
);
```

创建 Android NDK 字体管理器。

**参数:**
- `cacheFontFiles`: 是否缓存字体文件（当前未完全实现）
- `scanner`: 字体扫描器实例，用于解析字体文件

**返回值:**
- 成功返回 `SkFontMgr` 实例，如果 API 不可用（API < 30）返回 `nullptr`

**注意事项:**
- 仅在 Android 应用进程中正常工作
- 在裸可执行文件中会回退到使用旧的 `fonts.xml` 数据

## 内部实现细节

### API 动态加载

实现使用条件编译：
- 当 `__ANDROID_API__` >= 29 时，直接链接 Android NDK Font API
- 否则，使用 `dlopen` 和 `dlsym` 动态加载 `libandroid.so`

### 版本兼容性处理

- Android 10 (API 29): `AFont_getLocale` 存在 bug，返回无效指针
- Android 11+ (API 30+): 完全可用，该字体管理器仅在此版本及以上启用

### 字体变体轴自动调整

支持四个标准变体轴：
- `wght` (weight): 字重
- `wdth` (width): 字宽
- `slnt` (slant): 倾斜角度
- `ital` (italic): 斜体标志

通过 `adjustForStyle` 函数，根据请求的 `SkFontStyle` 自动调整这些轴的值。

### 字符和语言匹配

`onMatchFamilyStyleCharacter` 实现复杂的回退策略：
1. 检查指定的字体族是否支持该字符和语言
2. 遍历所有回退字体集，按样式匹配
3. 遍历所有字体，逐个检查字符覆盖和语言支持

### 大小写不敏感的名称匹配

使用 ICU 的 `u_strFoldCase` 或回退到 `towlower` 进行大小写规范化，确保字体族名称匹配不区分大小写。

### 特殊 hack 处理

1. **NotoSansSymbols-Regular-Subsetted**: 强制添加 `und-Zsym` 语言标签
2. **RobotoStatic-Regular**: 如果不包含 "Roboto" 别名，则添加该别名
3. **无 sans-serif 匹配**: 如果找不到 sans-serif，尝试使用 Roboto 作为回退

### 字体文件缓存

使用 `streamForPath` 哈希表缓存字体文件流，避免重复打开同一字体文件。

### 变体轴规范化和排序

变体轴坐标在比较前需要：
1. 规范化：将 NaN 和 -0.0 转换为 0.0
2. 排序：按轴标签和值排序
3. 用于缓存键的唯一标识

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkFontScanner` | 扫描和解析字体文件 |
| `SkFontMgr_android_parser` | 解析 Android fonts.xml 配置 |
| `SkTypeface_proxy` | 字体代理基类 |
| `SkLRUCache` | LRU 缓存实现 |
| `SkTHash` | 哈希表实现 |
| `SkSharedMutex` | 读写锁实现 |
| Android NDK Font API | 系统字体枚举和元数据 |
| ICU (libicu.so) | Unicode 大小写折叠 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| Skia 字体管理层 | 作为 Android NDK 平台的字体管理器 |
| Android 应用 | 通过 `SkFontMgr_New_AndroidNDK` 创建实例 |

## 设计模式与设计决策

### 工厂模式

通过 `SkFontMgr_New_AndroidNDK` 工厂函数创建字体管理器，隐藏实现细节。

### 代理模式

`SkTypeface_AndroidNDK` 继承 `SkTypeface_proxy`，将字体操作委托给底层的真实字体实例，同时添加 Android 特定的元数据（语言、变体、别名）。

### 策略模式

通过 `SkFontScanner` 抽象接口，允许注入不同的字体扫描策略。

### 缓存策略

- **TypefaceCache**: 两级缓存（Request 和 Match），避免重复创建字体实例
- **streamForPath**: 文件流缓存，避免重复打开文件
- **LRU 淘汰**: 自动管理内存使用

### 渐进式语言匹配

`SkALanguage::lessSpecific` 实现从具体到一般的语言标签回退：
- `zh-Hans-CN` → `zh-Hans` → `zh` → 空

### 防御性编程

- 检查 API 版本是否支持
- 动态加载 API 失败时返回 `nullptr`
- 处理各种边界条件（无字体、无匹配等）

## 性能考量

### 初始化性能

- 枚举所有系统字体（可能数百个）
- 为每个字体创建流并扫描元数据
- 构建名称到字体族的映射

优化策略：
- 使用 `streamForPath` 缓存避免重复文件 I/O
- 延迟加载字体实例（仅在需要时创建）

### 查找性能

- 名称匹配：线性搜索 `fNameToFamilyMap`（O(n)）
- 字符匹配：可能遍历所有字体（最坏 O(n*m)，n=字体数，m=每个字体族的样式数）

优化策略：
- `TypefaceCache` 缓存已创建的字体实例
- 优先搜索回退列表而非所有字体

### 内存使用

- 所有字体样式集保存在内存中
- `TypefaceCache` 使用 LRU 限制缓存大小
- 字体文件流可能被缓存（取决于 `SkFontScanner` 实现）

### 线程安全

- `TypefaceCache` 使用 `SkSharedMutex` 保护并发访问
- 读多写少场景使用共享锁优化性能

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/ports/SkFontMgr_android_ndk.h` | 公共 API 头文件 |
| `src/ports/SkFontMgr_android_ndk.cpp` | 主实现文件 |
| `src/ports/SkFontMgr_android_parser.h` | Android fonts.xml 解析器 |
| `src/ports/SkTypeface_proxy.h` | 字体代理基类 |
| `include/core/SkFontMgr.h` | 字体管理器基类 |
| `include/core/SkFontScanner.h` | 字体扫描器接口 |
| `src/core/SkLRUCache.h` | LRU 缓存实现 |
| `src/core/SkTHash.h` | 哈希表实现 |
| `src/base/SkSharedMutex.h` | 读写锁实现 |
