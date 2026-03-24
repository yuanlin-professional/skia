# TestFontCollection - 测试用字体集合

> 源文件: [`modules/skparagraph/utils/TestFontCollection.h`](../../../modules/skparagraph/utils/TestFontCollection.h), [`modules/skparagraph/utils/TestFontCollection.cpp`](../../../modules/skparagraph/utils/TestFontCollection.cpp)

## 概述

TestFontCollection 是 Skia 段落排版模块（skparagraph）中用于测试目的的字体集合类。它继承自 `FontCollection`，能够从指定目录加载字体文件，并通过 `TypefaceFontProvider` 注册到字体管理系统中。该类简化了测试环境中字体资源的管理，支持跨平台的字体加载（FreeType、Core Text、DirectWrite）。

## 架构位置

TestFontCollection 位于 skparagraph 模块的 utils 子目录中，属于测试基础设施：

- **上层使用者**: skparagraph 模块的单元测试和基准测试
- **父类**: `FontCollection`（skparagraph 的字体集合抽象）
- **底层依赖**: 平台特定的字体加载器（FreeType/CoreText/DirectWrite）、`TypefaceFontProvider`

## 主要类与结构体

### `TestFontCollection` 类

```cpp
class TestFontCollection : public FontCollection {
public:
    TestFontCollection(const std::string& resourceDir, bool testOnly = false, bool loadFonts = true);
    size_t fontsFound() const { return fFontsFound; }
    bool addFontFromFile(const std::string& path, const std::string& familyName = "");
private:
    std::string fResourceDir;    // 字体资源目录路径
    size_t fFontsFound;          // 已找到的字体族数量
    sk_sp<TypefaceFontProvider> fFontProvider;  // 字体提供器
    std::string fDirs;           // 缓存已加载的目录路径
};
```

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `TestFontCollection(resourceDir, testOnly, loadFonts)` | 构造函数，从 resourceDir 加载字体 |
| `fontsFound()` | 返回已发现的字体族数量 |
| `addFontFromFile(path, familyName)` | 从文件手动添加单个字体 |

### 构造函数参数
- `resourceDir`: 字体文件所在目录的路径
- `testOnly`: 若为 true，将字体提供器设为 TestFontManager；否则设为 AssetFontManager
- `loadFonts`: 若为 true（默认），自动遍历目录加载所有字体文件

## 内部实现细节

### 构造流程
1. 检查 `fDirs` 是否与新的 `resourceDir` 相同（缓存机制），相同则跳过
2. 创建新的 `TypefaceFontProvider` 实例
3. 若 `loadFonts` 为 true，使用 `SkOSFile::Iter` 遍历资源目录中的所有文件
4. 对每个文件调用 `addFontFromFile` 加载
5. 记录 `fFontsFound`（通过 `fFontProvider->countFamilies()` 获取）
6. 根据 `testOnly` 参数将提供器设置为测试或资产字体管理器
7. 禁用字体回退（`disableFontFallback()`），确保测试的确定性

### 跨平台字体加载
`addFontFromFile` 通过条件编译支持三个平台：
- **FreeType** (`SK_TYPEFACE_FACTORY_FREETYPE`): 使用 `SkTypeface_FreeType::MakeFromStream`
- **Core Text** (`SK_TYPEFACE_FACTORY_CORETEXT`): 使用 `SkTypeface_Mac::MakeFromStream`
- **DirectWrite** (`SK_TYPEFACE_FACTORY_DIRECTWRITE`): 使用 `DWriteFontTypeface::MakeFromStream`

加载后的字体通过 `fFontProvider->registerTypeface` 注册，可选指定族名。

## 依赖关系

- `modules/skparagraph/include/FontCollection.h` - 父类 FontCollection
- `modules/skparagraph/include/TypefaceFontProvider.h` - 字体提供器
- `modules/skparagraph/src/ParagraphImpl.h` - 段落实现（间接依赖）
- `include/core/SkStream.h` - 文件流读取
- `src/core/SkOSFile.h` - 文件系统操作
- `src/core/SkFontDescriptor.h` - 字体描述符
- `src/ports/SkTypeface_FreeType.h` / `SkTypeface_mac_ct.h` / `SkTypeface_win_dw.h` - 平台特定字体工厂

## 设计模式与设计决策

### 目录缓存
使用 `fDirs` 成员变量缓存已加载的目录路径，避免对相同目录的重复加载。然而需要注意该缓存检查存在一个细微问题：`fDirs` 在构造函数末尾才被赋值，而检查在开头进行。对于新构造的对象，`fDirs` 为空字符串，因此只有传入空字符串的 `resourceDir` 才会命中缓存。

### 禁用字体回退
在构造函数中调用 `disableFontFallback()` 确保测试中的字体解析行为完全可预测——不会因为系统安装了不同的字体而导致测试结果不一致。

### 平台抽象
通过预处理宏实现平台字体工厂的选择，使同一套测试代码可以在所有支持的平台上运行。

## 性能考量

- 批量加载模式下遍历目录中所有文件，适合测试场景但不适合生产环境
- 使用 `SkFILEStream::Make` 直接从文件创建流，避免不必要的内存复制
- `TypefaceFontProvider` 的注册操作是 O(1) 的

## 相关文件

- `modules/skparagraph/include/FontCollection.h` - 字体集合基类
- `modules/skparagraph/include/TypefaceFontProvider.h` - 字体提供器
- `modules/skparagraph/src/ParagraphImpl.h` - 段落实现
- `tools/Resources.h` - 测试资源路径工具
