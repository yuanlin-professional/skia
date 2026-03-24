# TextBlobTools

> 源文件：tools/text/gpu/TextBlobTools.h, tools/text/gpu/TextBlobTools.cpp

## 概述

TextBlobTools 是用于访问 GPU 文本 blob（sktext::gpu::TextBlob）内部结构的测试工具类。该模块提供了访问通常封装的内部数据的接口，专门用于单元测试和调试。

主要功能：
- 访问 TextBlob 的第一个 SubRun
- 用于测试 GPU 文本渲染管线
- 检查内部数据结构状态

该工具类仅包含静态方法，不可实例化。

## 架构位置

- **角色**：测试辅助工具
- **访问对象**：sktext::gpu::TextBlob、sktext::gpu::AtlasSubRun
- **使用者**：GPU 文本渲染单元测试
- **命名空间**：sktext::gpu

## 主要类与结构体

### TextBlobTools

```cpp
class TextBlobTools final {
public:
    static const AtlasSubRun* FirstSubRun(const TextBlob*);

private:
    TextBlobTools();  // 不可实例化
};
```

## 公共 API 函数

### FirstSubRun

```cpp
static const AtlasSubRun* FirstSubRun(const TextBlob* blob);
```

获取 TextBlob 的第一个 AtlasSubRun。

**参数**：
- `blob` - GPU TextBlob 指针（不能为空）

**返回值**：
- 第一个 SubRun 的指针
- 如果 SubRun 列表为空，返回 `nullptr`

**实现**：
```cpp
SkASSERT(blob);
if (blob->fSubRuns->fSubRuns.isEmpty()) {
    return nullptr;
}
return blob->fSubRuns->fSubRuns.front().testingOnly_atlasSubRun();
```

## 内部实现细节

### 友元访问

TextBlob Tools 可能通过友元声明访问 TextBlob 的私有成员：
```cpp
blob->fSubRuns->fSubRuns
```

### testingOnly_atlasSubRun()

调用 SubRun 的测试专用方法获取 AtlasSubRun：
```cpp
.testingOnly_atlasSubRun()
```

这是一个约定，测试专用方法使用 `testingOnly_` 前缀。

### 空检查

使用断言确保输入有效：
```cpp
SkASSERT(blob);
```

然后检查 SubRuns 是否为空：
```cpp
if (blob->fSubRuns->fSubRuns.isEmpty()) {
    return nullptr;
}
```

## 依赖关系

### 文本 GPU 系统
- `src/text/gpu/TextBlob.h` - GPU 文本 blob
- `src/text/gpu/SubRunContainer.h` - SubRun 容器
- `src/text/gpu/AtlasSubRun.h` - Atlas SubRun

## 设计模式与设计决策

### 静态工具类
类仅包含静态方法，私有构造函数防止实例化：
```cpp
private:
    TextBlobTools();
```

### 测试友好设计
提供访问内部状态的接口，专门用于测试。

### 最小接口
仅暴露测试需要的最小功能。

### final 类
声明为 `final` 防止继承，明确设计意图。

### 命名约定
`testingOnly_` 前缀清晰标识测试专用 API。

## 性能考量

- 静态方法无对象创建开销
- 直接访问内部数据，无抽象层
- 仅用于测试，生产代码不应使用

## 相关文件

- `src/text/gpu/TextBlob.h` - GPU 文本 blob 定义
- `src/text/gpu/SubRunContainer.h` - SubRun 容器
- `src/text/gpu/AtlasSubRun.h` - Atlas SubRun 接口
- GPU 文本渲染测试文件
