# Uniform

> 源文件: src/gpu/graphite/Uniform.h

## 概述

`Uniform` 是 Skia Graphite 架构中表示着色器 uniform 变量定义的基础类。该类封装了 uniform 的名称、类型、数组大小以及语义标志，为 uniform 数据管理和着色器代码生成提供元数据。`Uniform` 被广泛用于 `ShaderCodeDictionary`、`UniformManager` 和着色器生成流程中。

## 架构位置

```
Graphite Uniform 系统：
  ├── Uniform（uniform 定义）★
  ├── UniformManager（数据写入）
  ├── UniformDataBlock（数据块）
  └── ShaderCodeDictionary（着色器字典）
```

## 主要类与结构体

### Uniform 类

```cpp
class Uniform {
public:
    enum class When : uint8_t { kAlways, kSometimes };

    constexpr Uniform(const char* name, SkSLType type, int count = 0);
    constexpr Uniform(const char* name, SkSLType type, int count, When when);

    const char* name() const;
    SkSLType type() const;
    int count() const;  // 0 表示非数组
    bool isPaintColor() const;
    When when() const;

private:
    const char* fName;
    SkSLType fType;
    int fCount;
    When fWhen;
};
```

## 公共 API 函数

### 构造函数

```cpp
constexpr Uniform(const char* name, SkSLType type, int count = 0);
```

创建 uniform 定义，`count` 为 0 表示非数组。

```cpp
constexpr Uniform(const char* name, SkSLType type, int count, When when);
```

指定 uniform 的使用条件（总是或有时）。

### 访问器

```cpp
const char* name() const;  // uniform 名称
SkSLType type() const;  // SkSL 类型（float、vec2、mat4等）
int count() const;  // 数组大小（0表示非数组）
When when() const;  // 使用条件
```

### isPaintColor

```cpp
bool isPaintColor() const;
```

检查是否为特殊的 `paintColor` uniform（用于去重优化）。

## 内部实现细节

### 内存布局

```cpp
class Uniform {
    const char* fName;  // 指向静态字符串（8字节）
    SkSLType fType;     // 枚举（1字节）
    int fCount;         // 数组大小（4字节）
    When fWhen;         // 枚举（1字节）
};  // 约16字节（考虑对齐）
```

### When 枚举

```cpp
enum class When : uint8_t {
    kAlways,     // 总是使用
    kSometimes   // 条件使用（如可选特性）
};
```

### paintColor 检测

```cpp
bool Uniform::isPaintColor() const {
    return strcmp(fName, "paintColor") == 0;
}
```

## 依赖关系

### 内部依赖

| 依赖类 | 用途 |
|--------|------|
| `SkSLType` | SkSL 类型枚举 |

### 被依赖情况

| 依赖者 | 用途 |
|--------|------|
| `UniformManager` | 写入 uniform 数据 |
| `ShaderCodeDictionary` | 存储 uniform 定义 |
| `ShaderInfo` | 生成 uniform 声明 |
| `RenderStep` | 定义步骤 uniform |

## 设计模式与设计决策

### 不可变值对象

一旦创建，uniform 定义不可更改，确保线程安全。

### constexpr 构造函数

支持编译时常量，减少运行时开销：
```cpp
constexpr Uniform kColorUniform("color", SkSLType::kFloat4);
```

### 语义标志

`isPaintColor()` 标记特殊 uniform，用于优化（去重）。

### 关键设计决策

1. **轻量级**: 仅16字节，可按值传递
2. **静态字符串**: name 指向静态字符串，无需拷贝
3. **编译时创建**: constexpr 支持编译时数组初始化
4. **语义识别**: `paintColor` 等特殊 uniform 有专门处理

## 性能考量

### 内存占用

- 单个 uniform 约16字节
- 名称为静态字符串指针，无动态分配

### 编译时优化

```cpp
static constexpr Uniform kUniforms[] = {
    {"matrix", SkSLType::kFloat4x4},
    {"color", SkSLType::kFloat4},
};
```

编译器可将数组放入只读数据段。

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `src/gpu/graphite/UniformManager.h` | Uniform 数据写入 |
| `src/gpu/graphite/ShaderCodeDictionary.h` | Uniform 存储 |
| `src/gpu/graphite/ShaderInfo.h` | Uniform 声明生成 |
| `src/sksl/SkSLDefines.h` | SkSL 类型定义 |
