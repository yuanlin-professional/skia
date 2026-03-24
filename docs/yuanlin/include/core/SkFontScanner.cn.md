# SkFontScanner

> 源文件: `include/core/SkFontScanner.h`

## 概述

SkFontScanner 是 Skia 字体系统中用于扫描和解析字体文件元数据的抽象接口类。它负责从字体数据流中提取字体族数量、字体实例、风格参数、可变轴定义等关键信息,为字体管理器和字体选择算法提供基础数据。该接口通过多态机制支持不同平台的字体格式(TrueType、OpenType、PostScript 等)。

## 架构位置

SkFontScanner 位于 Skia 核心层 (`include/core`),是字体子系统的底层解析接口。它位于字体管理器(SkFontMgr)和平台字体实现(FreeType/CoreText/DirectWrite)之间,定义了跨平台的字体元数据提取标准协议。

## 主要类与结构体

### SkFontScanner

**职责**: 定义字体文件扫描的抽象接口,解析字体元数据而不创建完整字体对象。

**继承关系**: `SkNoncopyable` → `SkFontScanner`

**类型别名**:
| 别名 | 定义 | 说明 |
|------|------|------|
| AxisDefinitions | `STArray<4, SkFontParameters::Variation::Axis, true>` | 可变字体的轴定义数组,小对象优化(4 个以内无堆分配) |
| VariationPosition | `STArray<4, SkFontArguments::VariationPosition::Coordinate, true>` | 命名实例的轴坐标数组 |

## 公共 API 函数

### `virtual ~SkFontScanner() = default`
- **功能**: 虚析构函数,支持多态删除
- **说明**: 确保派生类正确清理资源

### `virtual bool scanFile(SkStreamAsset* stream, int* numFaces) const = 0`
- **功能**: 扫描字体文件,获取包含的字体面(face)数量
- **参数**:
  - `stream`: 字体数据流(TTC 可能包含多个字体)
  - `numFaces`: 输出参数,返回字体面数量
- **返回值**: 成功返回 true,文件格式无效返回 false
- **说明**: TrueType Collection(TTC) 文件可包含多个独立字体
- **用例**: 判断是否需要遍历多个 faceIndex

### `virtual bool scanFace(SkStreamAsset* stream, int faceIndex, int* numInstances) const = 0`
- **功能**: 扫描特定字体面,获取包含的命名实例(named instance)数量
- **参数**:
  - `stream`: 字体数据流
  - `faceIndex`: 字体面索引(0 到 numFaces-1)
  - `numInstances`: 输出参数,返回命名实例数量
- **返回值**: 成功返回 true,索引无效返回 false
- **说明**: 可变字体可定义多个预设实例(如 Bold、Light)
- **用例**: 构建字体选择菜单时列出所有预设风格

### `virtual bool scanInstance(...) const = 0`
- **功能**: 扫描特定字体实例,提取完整元数据
- **参数**:
  - `stream`: 字体数据流
  - `faceIndex`: 字体面索引
  - `instanceIndex`: 实例索引(0 为默认实例,1+ 为命名实例)
  - `name`: 输出参数,实例名称(如 "Roboto Bold")
  - `style`: 输出参数,字体风格(字重/字宽/倾斜度)
  - `isFixedPitch`: 输出参数,是否为等宽字体
  - `axes`: 输出参数,可变轴定义数组(可为 nullptr 跳过)
  - `position`: 输出参数,实例的轴坐标(可为 nullptr 跳过)
- **返回值**: 成功返回 true,参数无效返回 false
- **说明**:
  - instanceIndex=0 对应默认实例(使用轴的默认值)
  - instanceIndex>0 对应命名实例(使用预设坐标)
- **用例**: 构建字体详情界面或选择最佳匹配字体

### `virtual sk_sp<SkTypeface> MakeFromStream(std::unique_ptr<SkStreamAsset>, const SkFontArguments&) const = 0`
- **功能**: 从数据流创建 SkTypeface 字体对象
- **参数**:
  - `stream`: 字体数据流(所有权转移)
  - `args`: 字体参数(faceIndex、轴坐标、调色板等)
- **返回值**: 创建的 SkTypeface 智能指针,失败返回 nullptr
- **说明**: 这是 Scanner 的便捷方法,某些实现可能不支持

### `virtual SkFourByteTag getFactoryId() const = 0`
- **功能**: 返回扫描器的工厂标识符
- **返回值**: 四字符标签,如 'ftyp' 表示 FreeType
- **用途**: 序列化时识别字体后端类型

## 使用场景

### 字体管理器初始化
```cpp
void EnumerateFonts(SkFontScanner* scanner, SkStreamAsset* stream) {
    int numFaces;
    if (!scanner->scanFile(stream, &numFaces)) {
        return;  // 无效字体文件
    }

    for (int faceIdx = 0; faceIdx < numFaces; ++faceIdx) {
        int numInstances;
        scanner->scanFace(stream, faceIdx, &numInstances);

        for (int instIdx = 0; instIdx <= numInstances; ++instIdx) {
            SkString name;
            SkFontStyle style;
            bool isFixedPitch;
            scanner->scanInstance(stream, faceIdx, instIdx,
                                  &name, &style, &isFixedPitch, nullptr, nullptr);
            RegisterFont(name, style, isFixedPitch);
        }
    }
}
```

### 可变字体检查
```cpp
bool IsVariableFont(SkFontScanner* scanner, SkStreamAsset* stream) {
    SkFontScanner::AxisDefinitions axes;
    scanner->scanInstance(stream, 0, 0, nullptr, nullptr, nullptr, &axes, nullptr);

    for (const auto& axis : axes) {
        if (axis.min != axis.max) {
            return true;  // 至少一个轴有范围
        }
    }
    return false;
}
```

### 命名实例列表
```cpp
std::vector<std::string> GetNamedInstances(SkFontScanner* scanner,
                                           SkStreamAsset* stream) {
    std::vector<std::string> instances;

    int numInstances;
    scanner->scanFace(stream, 0, &numInstances);

    for (int i = 1; i <= numInstances; ++i) {  // 跳过默认实例(0)
        SkString name;
        scanner->scanInstance(stream, 0, i, &name, nullptr, nullptr, nullptr, nullptr);
        instances.push_back(name.c_str());
    }

    return instances;
}
```

## 内部实现细节

### 扫描层次结构
```
字体文件
  └─ 字体面 0 (faceIndex=0)
      ├─ 默认实例 (instanceIndex=0)
      ├─ 命名实例 1 (instanceIndex=1, 如 "Bold")
      └─ 命名实例 2 (instanceIndex=2, 如 "Light")
  └─ 字体面 1 (faceIndex=1)
      └─ ...
```

### 平台实现差异

#### FreeType 实现
```cpp
class SkFontScanner_FreeType : public SkFontScanner {
    bool scanFile(SkStreamAsset* stream, int* numFaces) const override {
        FT_Face face;
        FT_Open_Args args = ...;
        FT_Error err = FT_Open_Face(library, &args, -1, &face);
        if (!err) {
            *numFaces = face->num_faces;
            FT_Done_Face(face);
            return true;
        }
        return false;
    }
    // ... 其他方法通过 FT_Get_MM_Var 等 API 实现
};
```

#### CoreText 实现
```cpp
class SkFontScanner_CoreText : public SkFontScanner {
    bool scanInstance(...) const override {
        CGFontRef cgFont = CGFontCreateWithDataProvider(provider);
        CFArrayRef variations = CGFontCopyVariationAxes(cgFont);
        // 转换为 SkFontParameters::Variation::Axis 数组
        CFRelease(cgFont);
        return true;
    }
};
```

### 数据流复用
扫描方法不消耗流,允许重复调用:
```cpp
// 流需支持 rewind() 或 duplicate()
stream->rewind();
scanner->scanInstance(stream, 0, 0, ...);
stream->rewind();
scanner->scanInstance(stream, 0, 1, ...);
```

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| SkFontArguments.h | 字体参数结构(faceIndex、轴坐标) |
| SkFontParameters.h | 可变轴定义结构 |
| SkRefCnt.h | sk_sp 智能指针 |
| SkTypes.h | 基础类型定义 |
| SkFixed.h | 定点数支持(部分字体格式使用) |
| SkNoncopyable.h | 禁止拷贝的基类 |
| SkTArray.h | 小型数组容器 |

### 被依赖的模块
| 模块 | 用途 |
|------|------|
| SkFontMgr | 字体管理器,使用 Scanner 枚举系统字体 |
| SkTypeface_*.cpp | 平台字体实现,提供 Scanner 具体子类 |
| 字体工具 | 字体验证和分析工具 |

## 设计模式与设计决策

### 接口隔离原则
分离扫描(只读元数据)和创建(生成对象)职责:
- 扫描操作轻量级,适合批量枚举
- 创建操作重量级,仅在需要时执行

### 三层扫描 API
逐级细化的查询接口:
1. `scanFile`: 文件级别(有多少字体?)
2. `scanFace`: 字体级别(有多少实例?)
3. `scanInstance`: 实例级别(详细元数据)
- 允许调用者按需获取信息,避免过度解析

### 输出参数模式
使用指针参数输出多个值:
- 避免返回复杂结构体
- 允许调用者传 nullptr 跳过不需要的信息
```cpp
// 仅需要风格,不需要轴信息
scanner->scanInstance(stream, 0, 0, &name, &style, nullptr, nullptr, nullptr);
```

### 抽象工厂关联
`getFactoryId()` 支持字体后端的识别:
```cpp
if (scanner->getFactoryId() == SkSetFourByteTag('f','t','2',' ')) {
    // 使用 FreeType 特定优化
}
```

## 性能考量

### 懒加载
扫描仅解析必要的字体表:
- 不加载字形轮廓数据
- 不构建字形缓存
- 典型扫描耗时 < 10ms/字体

### 缓存友好
小对象优化(STArray<4>):
```cpp
// 4 个轴以内无堆分配,减少内存碎片
AxisDefinitions axes;  // 栈分配,约 100 字节
```

### 流重用
避免重复打开文件:
```cpp
auto stream = SkStream::MakeFromFile("font.ttf");
scanner->scanFile(stream.get(), &numFaces);
stream->rewind();  // 重置位置,无需重新打开文件
scanner->scanFace(stream.get(), 0, &numInstances);
```

## 平台相关说明

### 字体格式支持
| 格式 | FreeType | CoreText | DirectWrite |
|------|----------|----------|-------------|
| TrueType | ✓ | ✓ | ✓ |
| OpenType | ✓ | ✓ | ✓ |
| PostScript Type 1 | ✓ | ✓ | ✗ |
| TrueType Collection | ✓ | ✓ | ✓ |
| Variable Fonts | ✓ | ✓ | ✓ |

### 命名实例的平台差异
- **Windows**: DirectWrite 自动生成实例(无需 'fvar' 命名实例表)
- **macOS**: CoreText 严格遵循 'fvar' 表
- **FreeType**: 支持命名实例和自定义坐标

## 错误处理

### 返回值语义
- `true`: 操作成功,输出参数有效
- `false`:
  - 文件格式不支持
  - 索引超出范围
  - 数据损坏或截断

### 防御性编程
```cpp
int numFaces;
if (scanner->scanFile(stream, &numFaces) && numFaces > 0) {
    for (int i = 0; i < numFaces; ++i) {
        // 安全访问
    }
}
```

## 实际应用示例

### 构建字体选择器
```cpp
void PopulateFontMenu(SkFontScanner* scanner, const char* fontPath) {
    auto stream = SkStream::MakeFromFile(fontPath);

    int numFaces;
    scanner->scanFile(stream.get(), &numFaces);

    for (int face = 0; face < numFaces; ++face) {
        int numInstances;
        scanner->scanFace(stream.get(), face, &numInstances);

        for (int inst = 0; inst <= numInstances; ++inst) {
            SkString name;
            SkFontStyle style;

            stream->rewind();
            scanner->scanInstance(stream.get(), face, inst,
                                  &name, &style, nullptr, nullptr, nullptr);

            menu->addItem(name.c_str(), style.weight());
        }
    }
}
```

### 等宽字体过滤
```cpp
std::vector<SkString> FindMonospaceFonts(SkFontScanner* scanner,
                                         const std::vector<const char*>& paths) {
    std::vector<SkString> monoFonts;

    for (const char* path : paths) {
        auto stream = SkStream::MakeFromFile(path);

        SkString name;
        bool isFixedPitch;
        if (scanner->scanInstance(stream.get(), 0, 0,
                                   &name, nullptr, &isFixedPitch, nullptr, nullptr)) {
            if (isFixedPitch) {
                monoFonts.push_back(name);
            }
        }
    }

    return monoFonts;
}
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/core/SkFontMgr.h` | 字体管理器,使用 Scanner 枚举字体 |
| `include/core/SkTypeface.h` | 字体对象,Scanner 可创建其实例 |
| `include/core/SkFontArguments.h` | 字体参数,传递给 MakeFromStream |
| `include/core/SkFontParameters.h` | 可变轴定义,由 scanInstance 输出 |
| `include/core/SkFontStyle.h` | 字体风格,由 scanInstance 输出 |
| `src/ports/SkFontHost_FreeType.cpp` | FreeType 实现 |
| `src/ports/SkFontHost_mac.cpp` | CoreText 实现 |
| `src/ports/SkFontHost_win.cpp` | DirectWrite 实现 |
