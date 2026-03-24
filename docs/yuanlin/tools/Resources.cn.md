# Resources

> 源文件：tools/Resources.h, tools/Resources.cpp

## 概述

`Resources` 是 Skia 工具库中用于加载测试资源文件的辅助模块。该模块提供了统一的接口来访问测试资源（如图像、字体、数据文件等），支持通过命令行标志配置资源目录路径，并提供了可选的自定义资源工厂机制。它是 Skia 测试基础设施的核心组件，让测试代码能够以平台无关的方式访问测试数据，广泛用于单元测试、GM（Gold Master）测试和示例程序中。

## 架构位置

`Resources` 在 Skia 架构中的位置：
- 位于 `tools/` 目录，属于测试工具基础设施
- 提供全局函数访问资源文件
- 默认资源路径：`resources/` 目录
- 支持命令行标志 `--resourcePath` 或 `-i` 覆盖路径
- 可选的自定义资源工厂（`gResourceFactory`）
- 与 `DecodeUtils`、`TestFontDataProvider` 等模块集成

## 主要类与结构体

该模块仅提供全局函数，无类定义。

**全局函数**：
```cpp
SkString GetResourcePath(const char* resource = "");
void SetResourcePath(const char*);
sk_sp<SkData> GetResourceAsData(const char* resource);
std::unique_ptr<SkStreamAsset> GetResourceAsStream(const char* resource,
                                                   bool useFileStream = false);
```

**全局变量**：
```cpp
sk_sp<SkData> (*gResourceFactory)(const char*) = nullptr;  // 可选的资源工厂
```

**命令行标志**：
```cpp
DEFINE_string2(resourcePath, i, "resources",
              "Directory with test resources: images, fonts, etc.");
```

## 公共 API 函数

### GetResourcePath
```cpp
SkString GetResourcePath(const char* resource = "")
```
- **功能**：获取资源文件的完整路径
- **参数**：相对资源路径（如 `"images/mandrill.png"`）
- **返回值**：完整路径字符串（如 `"resources/images/mandrill.png"`）
- **实现**：使用 `SkOSPath::Join()` 组合基路径和资源路径

### SetResourcePath
```cpp
void SetResourcePath(const char* path)
```
- **功能**：设置资源基路径
- **参数**：新的资源目录路径
- **用途**：在测试初始化时覆盖默认路径

### GetResourceAsData
```cpp
sk_sp<SkData> GetResourceAsData(const char* resource)
```
- **功能**：加载资源文件为 `SkData` 对象
- **参数**：相对资源路径
- **返回值**：`SkData` 智能指针，失败返回 `nullptr`
- **行为**：
  1. 如果设置了 `gResourceFactory`，优先使用工厂
  2. 否则使用 `SkData::MakeFromFileName()` 读取文件
  3. 失败时输出调试信息
  4. 如果定义了 `SK_TOOLS_REQUIRE_RESOURCES`，失败时终止程序

**重载版本**：
```cpp
inline sk_sp<SkData> GetResourceAsData(const std::string& resource)
```
接受 C++ 标准字符串参数。

### GetResourceAsStream
```cpp
std::unique_ptr<SkStreamAsset> GetResourceAsStream(const char* resource,
                                                   bool useFileStream = false)
```
- **功能**：加载资源文件为流对象
- **参数**：
  - `resource`: 相对资源路径
  - `useFileStream`: 是否使用文件流（默认使用内存流）
- **返回值**：`SkStreamAsset` 智能指针
- **两种模式**：
  - `useFileStream = true`：返回 `SkFILEStream`（直接读取文件）
  - `useFileStream = false`：返回 `SkMemoryStream`（先加载到内存）

## 内部实现细节

### 资源路径解析

**命令行标志**：
```cpp
DEFINE_string2(resourcePath, i, "resources", "Directory with test resources...");
```
- 短标志：`-i`
- 长标志：`--resourcePath`
- 默认值：`"resources"`

**路径组合**：
```cpp
SkString GetResourcePath(const char* resource) {
    return SkOSPath::Join(FLAGS_resourcePath[0], resource);
}
```
使用 `SkOSPath::Join()` 确保跨平台兼容性（Windows 使用 `\`，Unix 使用 `/`）。

### 资源加载策略

**优先级顺序**：
1. 自定义资源工厂（如果设置）
2. 从文件系统加载

**实现**：
```cpp
sk_sp<SkData> GetResourceAsData(const char* resource) {
    if (sk_sp<SkData> data = gResourceFactory
                           ? gResourceFactory(resource)
                           : SkData::MakeFromFileName(GetResourcePath(resource).c_str())) {
        return data;
    }
    SkDebugf("Resource \"%s\" not found.\n", GetResourcePath(resource).c_str());
    #ifdef SK_TOOLS_REQUIRE_RESOURCES
    SK_ABORT("missing resource");
    #endif
    return nullptr;
}
```

### 流创建策略

**文件流 vs 内存流**：
```cpp
if (useFileStream) {
    auto path = GetResourcePath(resource);
    return SkFILEStream::Make(path.c_str());  // 直接文件流
} else {
    auto data = GetResourceAsData(resource);
    return data ? std::unique_ptr<SkStreamAsset>(new SkMemoryStream(std::move(data)))
                : nullptr;  // 先加载到内存
}
```

**选择建议**：
- 文件流：适合大文件，节省内存
- 内存流：适合小文件，支持随机访问

### 自定义资源工厂

**工厂函数指针**：
```cpp
sk_sp<SkData> (*gResourceFactory)(const char*) = nullptr;
```

**用途**：
- 嵌入式系统中从内存加载资源
- 网络加载资源
- 压缩资源解压

**示例用法**：
```cpp
sk_sp<SkData> MyResourceFactory(const char* path) {
    // 自定义加载逻辑
    return LoadFromArchive(path);
}

// 设置工厂
gResourceFactory = MyResourceFactory;
```

## 依赖关系

**Skia 核心依赖**：
- `include/core/SkData.h` - 数据容器
- `include/core/SkStream.h` - 流接口
- `include/core/SkString.h` - 字符串类
- `include/private/base/SkDebug.h` - 调试宏

**工具依赖**：
- `src/utils/SkOSPath.h` - 路径操作工具
- `tools/flags/CommandLineFlags.h` - 命令行标志系统

## 设计模式与设计决策

### 单例模式（部分）
使用全局函数和全局变量管理资源路径配置。

### 工厂模式
可选的 `gResourceFactory` 提供自定义资源加载策略。

### 外观模式
统一的接口隐藏文件系统访问和路径处理的复杂性。

### 关键设计决策

**1. 全局函数而非类**
简单的资源加载无需状态管理，全局函数更简洁。

**2. 命令行标志集成**
方便测试在不同环境（CI、本地）中运行。

**3. 可选的严格模式**
`SK_TOOLS_REQUIRE_RESOURCES` 让资源缺失立即失败，避免后续错误。

**4. 工厂扩展点**
`gResourceFactory` 提供定制化能力，无需修改代码。

**5. 双流模式**
同时提供文件流和内存流，适应不同性能需求。

## 性能考量

### 内存使用

**GetResourceAsData**：
- 一次性加载整个文件到内存
- 适合小文件（< 10MB）

**GetResourceAsStream(useFileStream=true)**：
- 不预加载，按需读取
- 适合大文件

### I/O 性能

**文件流优势**：
- 流式读取，内存占用小
- 适合顺序访问

**内存流优势**：
- 支持随机访问和回退
- 避免重复 I/O

### 缓存

**无内置缓存**：
- 每次调用都重新加载
- 频繁访问同一资源时性能较低

**改进建议**：
```cpp
// 可考虑添加简单缓存
static std::unordered_map<std::string, sk_sp<SkData>> cache;
```

## 相关文件

**使用示例**：
- `tools/DecodeUtils.h` - 图像解码工具
- `tools/TestFontDataProvider.cpp` - 字体测试数据
- `gm/` - 所有 GM 测试
- `tests/` - 单元测试

**命令行标志**：
- `tools/flags/CommandLineFlags.h` - 标志系统
- `tools/flags/CommandLineFlags.cpp` - 标志实现

**路径工具**：
- `src/utils/SkOSPath.h` - 跨平台路径操作

**资源目录**：
- `resources/` - 默认资源目录
- `resources/images/` - 测试图像
- `resources/fonts/` - 测试字体

**构建配置**：
- `BUILD.gn` - 资源文件复制规则
- `infra/bots/` - CI 环境配置
