# TestFontDataProvider

> 源文件：tools/TestFontDataProvider.h, tools/TestFontDataProvider.cpp

## 概述

`TestFontDataProvider` 是 Skia 工具库中用于管理和迭代字体测试数据的类。该类从 Google Fonts 测试数据 CIPD（Chrome Infrastructure Package Deployment）包中读取字体和语言样本信息，提供了基于正则表达式的过滤功能，允许测试框架有选择地加载特定字体和语言的测试样本。它主要用于字体渲染和文本整形（text shaping）的自动化测试，确保 Skia 在多种字体和语言环境下的正确性。

## 架构位置

`TestFontDataProvider` 在 Skia 架构中的位置：

- 位于 `tools/` 目录，属于测试工具基础设施
- 依赖 JSON 解析器 (`modules/jsonreader/SkJSONReader.h`)
- 从 CIPD 包 `googlefonts_testdata` 读取测试数据
- 使用 C++ 标准库的 `<regex>` 进行过滤
- 配合 `skiatest` 命名空间的命令行标志系统
- 为字体测试提供数据源和迭代器接口

该类是 Skia 字体测试基础设施的核心组件，支持大规模多语言字体测试。

## 主要类与结构体

### LangSample 结构体

表示单个语言的测试样本：
```cpp
struct LangSample {
    SkString langTag;        // 语言标签（如 "en", "zh-CN", "ar"）
    SkString sampleShort;    // 短文本样本
    SkString sampleLong;     // 长文本样本
};
```

**用途**：
- 提供各语言的典型文本用于渲染测试
- 短样本用于快速测试
- 长样本用于完整的文本整形和布局测试

### TestSet 结构体

表示单个字体的完整测试集：
```cpp
struct TestSet {
    SkString fontName;                  // 字体名称
    SkString fontFilename;              // 字体文件路径
    std::vector<LangSample> langSamples; // 该字体支持的语言样本列表
};
```

**用途**：
- 封装单个字体的所有测试信息
- 通过迭代器逐个提供给测试用例

### TestFontDataProvider 类

**核心成员变量**：
```cpp
std::regex fFontFilter;                      // 字体名称过滤正则表达式
std::regex fLangFilter;                      // 语言标签过滤正则表达式
size_t fFontsIndex;                          // 当前迭代位置
std::unique_ptr<skjson::DOM> fJsonDom;      // JSON 文档对象模型
const skjson::ArrayValue* fFonts;           // 字体数组引用
const skjson::ObjectValue* fSamples;        // 语言样本对象引用
```

**公共方法**：
```cpp
TestFontDataProvider(const std::string& fontFilterRegexp,
                     const std::string& langFilterRegexp);

bool next(TestSet* testSet);  // 获取下一个测试集
void rewind();                // 重置到开始位置
```

## 公共 API 函数

### 构造函数

**TestFontDataProvider()**
```cpp
TestFontDataProvider(const std::string& fontFilterRegexp,
                     const std::string& langFilterRegexp)
```
- **功能**：创建测试数据提供器并加载 JSON 数据
- **参数**：
  - `fontFilterRegexp`: 字体名称过滤的正则表达式（如 `".*"` 匹配所有，`"Noto.*"` 匹配 Noto 系列）
  - `langFilterRegexp`: 语言标签过滤的正则表达式（如 `"en|zh.*"` 匹配英文和中文）
- **流程**：
  1. 构造正则表达式对象
  2. 从 `third_party/externals/googlefonts_testdata/data/raster_test.json` 读取数据
  3. 解析 JSON 文档
  4. 验证字体数量（期望 51 个字体）
  5. 提取 `fonts` 数组和 `samples` 对象

### 迭代器方法

**next()**
```cpp
bool next(TestSet* testSet)
```
- **功能**：获取下一个匹配过滤条件的测试集
- **参数**：输出参数，填充测试集数据
- **返回值**：有更多数据返回 `true`，已完成返回 `false`
- **流程**：
  1. 遍历字体数组
  2. 对每个字体应用正则表达式过滤
  3. 如果匹配，提取字体信息和语言样本
  4. 将字体文件路径前缀补全为绝对路径
  5. 返回填充后的测试集

**rewind()**
```cpp
void rewind()
```
- **功能**：重置迭代器到开始位置
- **实现**：将 `fFontsIndex` 设为 0

### 配置函数（skiatest 命名空间）

**SetFontTestDataDirectory()**
```cpp
void skiatest::SetFontTestDataDirectory()
```
- **功能**：设置字体测试数据目录
- **命令行标志**：`--fontTestDataPath`
- **默认路径**：`third_party/externals/googlefonts_testdata/data/`
- **用途**：覆盖默认的 CIPD 包位置

## 内部实现细节

### JSON 数据结构

测试数据 JSON 文件的结构：
```json
{
  "fonts": [
    {
      "name": "Noto Sans",
      "path": "NotoSans-Regular.ttf",
      "languages": ["en", "de", "fr", ...]
    },
    ...
  ],
  "samples": {
    "en": {
      "short_sample": "Hello World",
      "long_sample": "The quick brown fox..."
    },
    "zh-CN": {
      "short_sample": "你好世界",
      "long_sample": "中文长文本样本..."
    },
    ...
  }
}
```

### 路径处理

**prefixWithTestDataPath()**
```cpp
SkString prefixWithTestDataPath(SkString suffix) {
    return SkOSPath::Join(gFontTestDataBasePath, suffix.c_str());
}
```
- 将相对路径转换为绝对路径
- 使用全局原子变量 `gFontTestDataBasePath` 存储基路径

**prefixWithFontsPath()**
```cpp
SkString prefixWithFontsPath(SkString suffix) {
    SkString fontsPath = prefixWithTestDataPath(SkString("fonts"));
    return SkOSPath::Join(fontsPath.c_str(), suffix.c_str());
}
```
- 构造字体文件的完整路径
- 组合基路径、`fonts` 子目录和文件名

### 语言样本提取

**getLanguageSamples()**
```cpp
std::vector<LangSample> getLanguageSamples(const skjson::ArrayValue* languages)
```
- **功能**：从 JSON 中提取语言样本
- **流程**：
  1. 遍历字体支持的语言列表
  2. 对每个语言应用正则表达式过滤
  3. 从 `samples` 对象查找对应语言标签
  4. 提取 `short_sample` 和 `long_sample`
  5. 构造 `LangSample` 对象
- **断言**：至少返回一个样本（`SkASSERT_RELEASE`）

### 正则表达式过滤

**字体过滤**：
```cpp
std::smatch match;
std::string fontNameStr(fontName->str());
if (std::regex_match(fontNameStr, match, fFontFilter)) {
    // 匹配成功，处理该字体
}
```

**语言过滤**：
```cpp
std::string langTagStr(langTag->str());
if (std::regex_match(langTagStr, match, fLangFilter)) {
    // 匹配成功，添加该语言样本
}
```

**过滤效果**：
- 允许灵活的测试配置
- 减少测试时间（只测试特定字体或语言）
- 支持调试特定场景

### 数据验证

**字体数量检查**：
```cpp
constexpr size_t kExpectNumFonts = 51;
if (fFonts->size() != kExpectNumFonts) {
    SkDebugf("Unable to access all %zu test fonts (got %zu)...\n",
             kExpectNumFonts, fFonts->size());
}
```
- 确保 CIPD 包完整下载和解压
- 版本更新时需要同步修改 `kExpectNumFonts`

## 依赖关系

**Skia 核心依赖**：
- `include/core/SkString.h` - 字符串类
- `include/core/SkData.h` - 数据容器
- `include/private/base/SkDebug.h` - 调试宏

**JSON 解析依赖**：
- `modules/jsonreader/SkJSONReader.h` - JSON 解析器
- `skjson::DOM` - JSON 文档对象模型
- `skjson::ObjectValue`, `skjson::ArrayValue`, `skjson::StringValue` - JSON 节点类型

**路径处理依赖**：
- `src/utils/SkOSPath.h` - 跨平台路径操作

**命令行标志依赖**：
- `tools/flags/CommandLineFlags.h` - 命令行参数解析

**标准库依赖**：
- `<regex>` - 正则表达式
- `<string>` - 标准字符串
- `<vector>` - 动态数组
- `<atomic>` - 原子变量

## 设计模式与设计决策

### 迭代器模式
提供 `next()` 和 `rewind()` 方法，实现顺序访问测试数据集合。

### 策略模式
通过正则表达式实现灵活的过滤策略，允许运行时配置。

### 外观模式
隐藏 JSON 解析和路径处理的复杂性，提供简单的迭代接口。

### 单例模式（部分）
使用全局原子变量 `gFontTestDataBasePath` 存储数据路径。

### 关键设计决策

**1. 正则表达式过滤**
- 提供强大的过滤能力，无需修改代码
- 支持复杂的匹配模式（如 `"Noto.*(Arabic|Hebrew).*"`）

**2. 懒加载设计**
- 仅在需要时读取文件
- 构造函数失败不会抛出异常，而是返回空迭代器

**3. 命令行标志支持**
- 允许 CI/CD 环境覆盖默认路径
- 支持本地开发和生产环境的不同配置

**4. 分离的语言样本**
- 语言样本独立于字体存储
- 多个字体可共享相同语言的样本数据

**5. 短样本与长样本**
- 短样本用于快速冒烟测试
- 长样本用于完整的文本整形和布局测试

**6. 路径规范化**
- 统一使用绝对路径，避免工作目录依赖
- 使用 `SkOSPath::Join()` 确保跨平台兼容性

## 性能考量

### JSON 解析性能

**一次性解析**：
- 构造函数中解析整个 JSON 文件
- 后续迭代仅访问内存中的数据结构
- 对于 51 个字体的数据集，解析时间可忽略

**内存使用**：
- 整个 JSON 文档保留在内存中
- 典型大小：数百 KB
- 对于测试场景，内存开销可接受

### 正则表达式性能

**编译一次，使用多次**：
```cpp
fFontFilter(fontFilterRegexp), fLangFilter(langFilterRegexp)
```
- 构造函数中编译正则表达式
- 每次匹配的开销较小

**复杂度**：
- 简单模式（如 `".*"`）匹配极快
- 复杂模式可能有一定开销，但对 51 个字体不明显

### I/O 性能

**文件读取**：
```cpp
sk_sp<SkData> jsonTestData = SkData::MakeFromFileName(testDataLocation.c_str());
```
- 一次性读取整个 JSON 文件
- 小文件，I/O 延迟可忽略

**字体文件加载**：
- 仅返回路径，不实际加载字体
- 实际加载由测试代码负责

### 优化建议

1. **缓存匹配结果**：如果需要多次重复迭代，可缓存过滤后的结果
2. **预编译正则表达式**：对于常用模式，可提供预定义的过滤器
3. **按需加载 JSON**：如果数据集变得很大，可考虑流式解析
4. **索引优化**：为频繁查询的字段建立索引（当前规模不需要）

## 相关文件

**字体测试基础设施**：
- `tests/FontTest.cpp` - 字体相关单元测试
- `tests/TextBlobTest.cpp` - 文本 Blob 测试
- `tests/GlyphRunTest.cpp` - 字形运行测试

**CIPD 数据包**：
- `third_party/externals/googlefonts_testdata/` - 测试数据根目录
- `third_party/externals/googlefonts_testdata/data/fonts/` - 字体文件
- `third_party/externals/googlefonts_testdata/data/raster_test.json` - 元数据文件

**工具脚本**：
- `bin/fetch-fonts-testdata` - 下载和更新测试数据的脚本

**JSON 解析器**：
- `modules/jsonreader/SkJSONReader.h` - JSON 解析接口
- `modules/jsonreader/SkJSONReader.cpp` - 解析实现

**命令行标志系统**：
- `tools/flags/CommandLineFlags.h` - 标志定义和解析
- `tools/flags/CommandLineFlags.cpp` - 标志实现

**构建配置**：
- `BUILD.gn` - GN 构建配置，定义测试数据依赖

**使用示例**：
- `tests/` 目录下使用 `TestFontDataProvider` 的测试用例
- 通常与 `DEF_TEST` 宏结合使用

**相关类**：
- `SkTypeface` - 字体接口
- `SkFont` - 字体配置
- `SkTextBlob` - 文本 Blob
- `SkShaper` - 文本整形器
