# SkFontMgr_custom_directory

> 源文件
> - src/ports/SkFontMgr_custom_directory.cpp

## 概述

`SkFontMgr_custom_directory` 是基于目录扫描的字体管理器实现，通过递归扫描指定目录及其子目录来加载字体文件。该模块是 `SkFontMgr_Custom` 框架的具体实现，适用于从文件系统目录加载字体的场景，如嵌入式 Linux 系统、测试环境、自定义字体目录等。

核心特点：
- **递归目录扫描**：自动扫描所有子目录
- **多格式支持**：支持 `.ttf`、`.ttc`、`.otf`、`.pfb` 字体格式
- **TTC 和可变字体支持**：完整解析字体集合和可变字体实例
- **自动分组**：按家族名称自动组织字体
- **回退机制**：目录为空时创建空 typeface 防止崩溃

该模块常用于测试、开发环境和简单的字体管理需求。

## 架构位置

```
SkFontMgr (抽象基类)
    ↓
SkFontMgr_Custom (自定义管理器基类)
    ↓
DirectorySystemFontLoader (本模块 - 目录加载策略)
    ↓
SkFontScanner (FreeType扫描器)
    ↓
文件系统目录 (.ttf, .ttc, .otf, .pfb)
```

## 主要类与结构体

### DirectorySystemFontLoader
实现 `SkFontMgr_Custom::SystemFontLoader` 接口的目录扫描器。

**主要成员：**
- `fBaseDirectory`: 基础目录路径

**核心方法：**
- `loadSystemFonts()`: 加载系统字体
- `load_directory_fonts()`: 递归加载目录中的字体（静态方法）
- `find_family()`: 查找或创建字体家族（静态方法）

## 公共 API 函数

### SkFontMgr_New_Custom_Directory()
```cpp
sk_sp<SkFontMgr> SkFontMgr_New_Custom_Directory(const char* dir);
```
创建基于目录的字体管理器。

**参数：**
- `dir`: 要扫描的根目录路径

**返回值：** 字体管理器智能指针

**使用示例：**
```cpp
sk_sp<SkFontMgr> fontMgr = SkFontMgr_New_Custom_Directory("/usr/share/fonts");
```

## 内部实现细节

### 字体加载流程

#### loadSystemFonts() 方法
按顺序扫描四种字体格式：
1. `.ttf` (TrueType Font)
2. `.ttc` (TrueType Collection)
3. `.otf` (OpenType Font)
4. `.pfb` (PostScript Type 1 Font Binary)

如果没有找到任何字体，创建包含 `SkTypeface_Empty` 的空家族作为回退。

#### load_directory_fonts() 递归扫描
```cpp
static void load_directory_fonts(const SkFontScanner* scanner,
                                 const SkString& directory, const char* suffix,
                                 SkFontMgr_Custom::Families* families)
```

**扫描过程：**
1. 使用 `SkOSFile::Iter` 遍历当前目录中指定后缀的文件
2. 对每个文件：
   - 打开文件流
   - 使用 `scanner->scanFile()` 检测 face 数量
   - 对每个 face 使用 `scanner->scanFace()` 检测实例数量
   - 对每个实例使用 `scanner->scanInstance()` 提取元数据
   - 创建 `SkTypeface_File` 并添加到对应家族
3. 递归处理所有子目录（跳过以 `.` 开头的隐藏目录）

#### 字体索引编码
```cpp
(instanceIndex << 16) + faceIndex
```
将实例索引和 face 索引编码为单个整数：
- 低 16 位：face 索引（TTC 文件中的字体索引）
- 高 16 位：实例索引（可变字体实例索引，0 表示默认实例）

#### find_family() 家族查找
线性搜索已加载的家族，按名称匹配。如果不存在，返回 nullptr，调用者负责创建新家族。

### 错误处理

所有扫描和解析错误都被静默处理：
```cpp
if (!scanner->scanFile(stream.get(), &numFaces)) {
    // SkDebugf("---- failed to open <%s> as a font\n", filename.c_str());
    continue;
}
```

错误调试输出被注释掉，避免在正常使用时产生噪音，但可以根据需要启用。

### 空目录处理

如果目录完全为空或没有有效字体：
```cpp
if (families->empty()) {
    SkFontStyleSet_Custom* family = new SkFontStyleSet_Custom(SkString());
    families->push_back().reset(family);
    family->appendTypeface(sk_make_sp<SkTypeface_Empty>());
}
```
创建包含空 typeface 的匿名家族，确保字体管理器始终可用。

## 依赖关系

### Skia 内部依赖
| 模块 | 用途 |
|------|------|
| `SkFontMgr_Custom` | 自定义字体管理器基类 |
| `SkFontScanner` | 字体文件扫描接口 |
| `SkTypeface_File` | 文件字体 typeface |
| `SkTypeface_Empty` | 空 typeface 回退 |
| `SkOSFile::Iter` | 跨平台目录遍历 |
| `SkOSPath::Join` | 跨平台路径拼接 |
| `SkStream` | 文件流读取 |

## 设计模式与设计决策

### 1. 策略模式（Strategy Pattern）
`DirectorySystemFontLoader` 作为策略实现，注入到 `SkFontMgr_Custom` 中，实现了字体加载逻辑的可插拔性。

### 2. 模板方法模式（Template Method Pattern）
`load_directory_fonts()` 作为递归的模板方法，对每种字体格式重复相同的扫描逻辑。

### 3. 惰性错误处理
遇到无效文件时继续处理而非中断，最大化可用字体数量。

### 4. 防御式编程
空目录时创建空 typeface，确保系统始终有可用的回退对象。

### 5. 扫描后缀分离
将扫描逻辑抽象为接受后缀参数的函数，便于扩展支持新格式。

### 6. 递归目录遍历
自动发现子目录中的字体，用户只需指定根目录。

## 性能考量

### 1. 启动时扫描
所有字体在构造函数中一次性加载，启动时间取决于字体数量：
- 100 个字体文件：约 100-500ms
- 1000 个字体文件：约 1-5 秒

### 2. 线性家族搜索
每个字体都需要搜索现有家族，时间复杂度 O(n*m)，n 是文件数，m 是家族数。

### 3. 文件系统 I/O
每个文件都需要打开和部分读取（解析元数据），I/O 是主要瓶颈。

### 4. 递归开销
深层目录结构会增加递归调用开销，但通常影响不大。

### 5. 优化建议
- **预构建索引**：对大型字体目录，可预先构建字体索引文件
- **并行扫描**：使用线程池并行扫描不同子目录
- **增量更新**：监控文件系统变化，增量更新字体列表
- **缓存元数据**：缓存 scanner 提取的元数据

### 6. 内存占用
- 每个字体文件：约 200 字节（路径 + 元数据）
- 1000 个字体：约 200KB

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/ports/SkFontMgr_custom.h` | 自定义字体管理器基类 |
| `src/ports/SkFontMgr_custom.cpp` | 自定义字体管理器实现 |
| `include/ports/SkFontMgr_directory.h` | 目录字体管理器公共 API |
| `src/ports/SkTypeface_FreeType.h` | FreeType typeface 基类 |
| `src/core/SkOSFile.h` | 跨平台文件系统操作 |
| `src/utils/SkOSPath.h` | 跨平台路径操作 |
| `include/core/SkFontScanner.h` | 字体扫描器接口 |
| `src/ports/SkFontMgr_custom_embedded.cpp` | 嵌入式数据字体管理器 |
| `src/ports/SkFontMgr_custom_empty.cpp` | 空字体管理器 |
