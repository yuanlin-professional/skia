# FontCollection - 字体集合管理器

> 源文件: `modules/skparagraph/src/FontCollection.cpp`

## 概述

FontCollection 是 Skia 段落排版模块（skparagraph）中的字体管理核心组件。它统一管理多个 SkFontMgr（字体管理器）实例，提供按优先级查询字体族、匹配字体样式、处理 Unicode 回退（fallback）和 Emoji 回退等功能。FontCollection 还内置了字体面（typeface）缓存和段落缓存，以提升重复查询的性能。

## 架构位置

FontCollection 位于 `skia::textlayout` 命名空间内，是段落构建流程的基础依赖。ParagraphBuilder 需要一个 FontCollection 实例来创建段落。FontCollection 持有并协调多个 SkFontMgr 实例，按优先级顺序进行字体匹配。

**关系链**: `ParagraphBuilder` -> `FontCollection` -> `SkFontMgr` (Dynamic / Asset / Test / Default)

## 主要类与结构体

### `FontCollection`
主类，管理四个层级的字体管理器和字体缓存。

### `FontCollection::FaceCache`（内部结构体）
字体面缓存，使用哈希映射存储已查找过的字体结果。

### `FaceCache::FamilyKey`（内部结构体）
缓存键类型，由以下字段组成：
- `fFamilyNames`: 字体族名称列表
- `fFontStyle`: 字体样式（粗细、宽度、倾斜）
- `fFontArguments`: 可选的字体参数（如 variable font 轴值）
- 提供 `operator==` 和自定义 `Hasher`

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `FontCollection()` / `~FontCollection()` | 构造和析构，默认启用字体回退 |
| `getFontManagersCount()` | 返回当前可用字体管理器数量 |
| `setAssetFontManager(sk_sp<SkFontMgr>)` | 设置资源字体管理器（嵌入的字体资源） |
| `setDynamicFontManager(sk_sp<SkFontMgr>)` | 设置动态字体管理器（运行时注册的字体） |
| `setTestFontManager(sk_sp<SkFontMgr>)` | 设置测试字体管理器 |
| `setDefaultFontManager(...)` | 设置默认字体管理器（三个重载），用于最终回退 |
| `findTypefaces(...)` | 按字体族名和样式查找字体，支持可选的 FontArguments |
| `defaultFallback(SkUnichar, ...)` | 查找能渲染指定 Unicode 字符的回退字体 |
| `defaultEmojiFallback(...)` | 查找 Emoji 回退字体 |
| `defaultFallback()` | 返回默认回退字体 |
| `disableFontFallback()` / `enableFontFallback()` | 控制字体回退功能开关 |
| `clearCaches()` | 清空段落缓存和字体面缓存 |

## 内部实现细节

### 字体管理器优先级（`getFontManagerOrder`）
返回字体管理器的查询顺序：
1. **Dynamic** - 动态注册的字体（最高优先级）
2. **Asset** - 应用内嵌字体资源
3. **Test** - 测试用字体
4. **Default** - 系统默认字体（仅在启用回退时使用）

### 字体查找流程（`findTypefaces`）
1. 先查询 FaceCache，命中则直接返回
2. 遍历请求的字体族名列表，依次通过 `matchTypeface` 在所有字体管理器中查找
3. 若找到且有 FontArguments，则通过 `CloneTypeface` 应用变量字体参数
4. 若未找到任何匹配，回退到默认字体族名列表
5. 若仍未找到，使用 `legacyMakeTypeface` 进行最后的尝试
6. 将结果写入 FaceCache

### 平台特定 Emoji 处理
- **macOS/iOS**: 直接通过名称 "Apple Color Emoji" 查找
- **其他平台**: 使用 BCP47 locale "und-Zsye" 进行字符匹配

### 字体匹配（`matchTypeface`）
遍历所有可用字体管理器，调用 `matchFamily` 获取字体样式集，然后使用 `matchStyle` 匹配具体样式。

### Unicode 字符回退流程（`defaultFallback(SkUnichar, ...)`）
1. 遍历所有可用的字体管理器（按优先级顺序）
2. 构建 BCP47 locale 数组（如果提供了 locale，加入数组）
3. 使用第一个字体族名作为 familyName 提示
4. 调用 `matchFamilyStyleCharacter` 在管理器中查找能渲染该 Unicode 字符的字体
5. 如果找到且提供了 FontArguments，调用 `CloneTypeface` 应用变量字体参数
6. 返回第一个匹配的字体，如果所有管理器都未找到则返回 nullptr

### Emoji 回退流程（`defaultEmojiFallback`）
Apple 平台特殊处理：
1. macOS/iOS: 直接通过 `fDefaultFontManager->matchFamilyStyle` 查找 "Apple Color Emoji"
2. 其他平台: 使用 BCP47 locale "und-Zsye" 进行字符级匹配
3. 两种路径都使用 `matchFamilyStyleCharacter` 按 Emoji 起始码点查找

### FaceCache 哈希策略
FamilyKey 的哈希函数组合了：
- 所有字体族名的 std::hash
- 字体样式权重的 hash
- 字体样式倾斜度的 hash
- FontArguments 的 optional hash
使用 XOR 进行混合，虽然分布性不如 Jenkins hash，但对于字体查询场景足够。

## 依赖关系

- **SkFontMgr**: Skia 核心字体管理器接口
- **SkTypeface**: Skia 字体面类型
- **SkTHash**: 高效哈希映射容器
- **ParagraphCache**: 段落排版结果缓存（FontCollection 持有实例）
- **SkShapers::HB::PurgeCaches**: HarfBuzz 缓存清理接口
- **FontArguments**: 变量字体参数支持

## 设计模式与设计决策

1. **多级字体管理器策略**: 四个字体管理器层级允许应用灵活控制字体优先级——动态字体优先于内嵌资源，测试字体用于单元测试隔离。
2. **双层缓存**: FaceCache 缓存字体查找结果，ParagraphCache 缓存段落排版结果，分别优化不同层级的重复计算。
3. **回退机制**: `defaultFallback` 使用 `matchFamilyStyleCharacter` 按 Unicode 字符查找能渲染该字符的字体，确保多语言文本的完整渲染。
4. **平台条件编译**: Emoji 回退逻辑通过 `SK_BUILD_FOR_MAC` / `SK_BUILD_FOR_IOS` 宏区分平台，在 Apple 平台使用专用 Emoji 字体名。

## 性能考量

- **FaceCache 哈希缓存**: 避免重复的字体族查找，字体查询是相对昂贵的操作
- **默认字体族名列表**: 支持多个默认字体名称，按序尝试直到找到可用字体
- **clearCaches 联动清理**: 同时清理段落缓存、字体面缓存和 HarfBuzz 缓存，确保一致性
- **延迟初始化**: 字体管理器仅在被设置后才参与查询，避免不必要的初始化开销

## 相关文件

- `modules/skparagraph/include/FontCollection.h` - FontCollection 头文件
- `modules/skparagraph/include/ParagraphCache.h` - ParagraphCache 的公共声明
- `modules/skparagraph/include/FontArguments.h` - 字体参数类型
- `modules/skshaper/include/SkShaper_harfbuzz.h` - HarfBuzz 塑形器接口
- `include/core/SkTypeface.h` - SkTypeface 核心接口

## 使用注意事项

1. FontCollection 至少需要设置一个字体管理器才能工作
2. `setDefaultFontManager` 有三个重载，最完整的版本同时设置管理器和默认字体族名列表
3. `clearCaches()` 会同时清除字体面缓存、段落缓存和 HarfBuzz 缓存
4. 默认字体族名由 `DEFAULT_FONT_FAMILY` 宏定义（通常为 "Roboto"）
5. 禁用字体回退（`disableFontFallback`）后，仅使用 Dynamic、Asset 和 Test 字体管理器
6. FontCollection 实例可在多个 ParagraphBuilder 之间共享
7. `findTypefaces` 的结果会被缓存，若需要刷新需调用 `clearCaches()`

### 线程安全
FontCollection 本身不保证线程安全。ParagraphCache 内部有互斥锁保护，但 FontCollection 的其他操作（如 setAssetFontManager）应在单线程中进行。

### 字体管理器类型选择指南
| 管理器类型 | 适用场景 | 设置方法 |
|-----------|---------|---------|
| Dynamic | 运行时动态加载的字体 | `setDynamicFontManager` |
| Asset | 应用内嵌字体资源 | `setAssetFontManager` |
| Test | 单元测试隔离环境 | `setTestFontManager` |
| Default | 系统字体（最后回退） | `setDefaultFontManager` |

### 字体查找失败的回退链
当 `findTypefaces` 无法找到请求的字体时，依次尝试：
1. 用请求的族名在所有管理器中查找
2. 用默认族名列表在所有管理器中查找
3. 使用 `legacyMakeTypeface(nullptr, fontStyle)` 在所有管理器中获取任意匹配
4. 如果所有步骤都失败，返回空列表
