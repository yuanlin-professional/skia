# SkFontMgr_directory

> 源文件: `include/ports/SkFontMgr_directory.h`

## 概述

`SkFontMgr_directory` 提供了一个工厂函数，用于创建基于目录扫描的自定义字体管理器。该管理器会扫描指定目录中的字体文件，并使用 FreeType 引擎进行渲染。这是一个跨平台的字体加载解决方案，适用于需要从自定义路径加载字体的应用场景。

## 架构位置

该头文件位于 `include/ports/` 目录，属于 Skia 的平台移植层(Ports Layer)。它提供了字体管理系统的平台无关实现，作为 Skia 字体架构的可选后端之一，与平台原生字体管理器(如 DirectWrite、CoreText)并列。

## 公共 API 函数

### `SkFontMgr_New_Custom_Directory`

```cpp
SK_API sk_sp<SkFontMgr> SkFontMgr_New_Custom_Directory(const char* dir);
```

- **功能**: 创建一个扫描指定目录并加载字体文件的自定义字体管理器
- **参数**:
  - `dir`: C 风格字符串，指向包含字体文件的目录路径。路径格式遵循平台规范(Unix 使用 `/`，Windows 支持 `\` 或 `/`)
- **返回值**: `sk_sp<SkFontMgr>` 智能指针，管理新创建的字体管理器对象。如果目录无效或无法访问，行为由实现定义
- **所有权**: 返回的智能指针使用引用计数管理生命周期，调用者无需手动释放

## 内部实现细节

### 目录扫描机制

虽然头文件未暴露实现细节，但基于 Skia 的通用模式，实现通常包括：

1. **递归扫描**: 遍历目录(可能包括子目录)，识别字体文件扩展名(`.ttf`, `.otf`, `.ttc`, `.woff`, `.woff2` 等)
2. **FreeType 解析**: 使用 FreeType 库打开每个字体文件，提取元数据(字体族名、样式、权重等)
3. **字体匹配索引**: 构建内部索引，支持按字体族名、样式(粗体/斜体)、权重匹配字体

### 字体缓存策略

- **延迟加载**: 扫描时只读取元数据，实际字体数据在首次使用时加载
- **文件监视**: 标准实现通常不监视文件系统变化，目录内容在管理器创建时固定

### FreeType 集成

返回的 `SkFontMgr` 实例内部持有 FreeType 库的上下文(`FT_Library`)，所有字体渲染通过 FreeType 进行。这确保了跨平台的渲染一致性，但依赖 FreeType 库的可用性。

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `SkFontMgr` | 字体管理器基类，定义字体匹配和创建接口 |
| `SkRefCnt` | 引用计数基础设施 |
| `sk_sp<T>` | Skia 智能指针，管理对象生命周期 |
| FreeType 库 | 底层字体解析和渲染引擎(链接时依赖) |
| 平台文件系统 API | 目录遍历和文件访问 |

### 被依赖的模块

典型使用场景：
- **自定义字体嵌入**: 应用需要加载内嵌的字体资源，不依赖系统字体
- **跨平台一致性**: 确保所有平台使用相同的字体文件，避免渲染差异
- **沙盒环境**: 运行在受限环境(如容器、Web 服务器)中的应用
- **测试框架**: 单元测试需要可预测的字体集合

## 设计模式与设计决策

### 工厂模式

使用全局工厂函数而非构造函数：
- **封装实现**: 调用者无需了解具体的 `SkFontMgr` 子类名称
- **多态返回**: 返回基类指针，实现细节完全隐藏
- **命名一致性**: 与 Skia 其他工厂函数(`SkFontMgr_New_GDI`, `SkFontMgr_New_DirectWrite`)保持一致

### 不可变配置

目录路径在创建时指定，之后不可更改：
- **简化设计**: 避免运行时重新扫描的复杂性
- **线程安全**: 不可变配置天然线程安全
- **缺点**: 需要动态加载字体时，需要创建新的管理器实例

### 单一职责

该工厂函数只负责目录扫描，不处理：
- **字体回退**: 回退逻辑由更高层的 `SkFontMgr` 实现
- **系统字体集成**: 不与平台原生字体混合(除非手动配置字体回退链)

## 性能考量

### 初始化开销

目录扫描和字体元数据解析发生在 `SkFontMgr_New_Custom_Directory` 调用时：
- **文件数量**: 包含数百个字体的目录可能导致明显的初始化延迟(数十到数百毫秒)
- **优化建议**: 在应用启动时异步创建，或缓存管理器实例

### 内存占用

每个字体文件的元数据(字体族名、样式信息)会缓存在内存中：
- **估算**: 每个字体约 1-2 KB 元数据
- **实际字体数据**: FreeType 按需加载，未使用的字体不占用内存

### 查找性能

字体匹配使用哈希表或平衡树索引：
- **时间复杂度**: O(log n) 或 O(1)
- **适用规模**: 适合数百到数千字体的中小规模字体集

## 平台相关说明

### 路径分隔符

- **Windows**: 支持反斜杠(`\`)和正斜杠(`/`)
- **Unix/Linux/macOS**: 使用正斜杠(`/`)
- **建议**: 使用正斜杠以保持跨平台兼容性

### 文件权限

- **Linux**: 需要对目录和字体文件有读权限
- **macOS**: 沙盒应用可能需要用户授权访问目录
- **Windows**: 通常无特殊权限要求

### 文件系统编码

- **UTF-8**: 现代 Linux 和 macOS 默认
- **Windows**: 路径字符串应使用 UTF-8 编码，内部转换为 UTF-16

### FreeType 可用性

该实现依赖 FreeType 库：
- **嵌入式系统**: 需要确保 FreeType 已编译并链接
- **静态链接**: 某些平台需要静态链接 FreeType

## 使用示例

```cpp
// 创建管理器
sk_sp<SkFontMgr> fontMgr = SkFontMgr_New_Custom_Directory("/usr/share/fonts/custom");

// 匹配字体
sk_sp<SkTypeface> typeface = fontMgr->matchFamilyStyle("Arial", SkFontStyle::Bold());

// 用于绘制
SkFont font(typeface, 16.0f);
canvas->drawString("Hello", 0, 0, font, paint);
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/core/SkFontMgr.h` | 字体管理器基类定义 |
| `include/ports/SkFontMgr_data.h` | 基于内存数据的字体管理器 |
| `include/ports/SkFontMgr_empty.h` | 空字体管理器(无内置字体) |
| `src/ports/SkFontMgr_custom_directory.cpp` | 实现文件(源代码树) |
| `include/core/SkTypeface.h` | 字体面对象，管理器创建的产物 |
| `include/core/SkFont.h` | 高层字体 API，使用 Typeface |
