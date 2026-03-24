# SvgSlide

> 源文件: tools/viewer/SvgSlide.h, tools/viewer/SvgSlide.cpp

## 概述

`SvgSlide` 是 Skia Viewer 工具中用于展示和渲染 SVG 文件的幻灯片类。它继承自 `Slide` 基类,提供了加载、卸载和渲染 SVG 文档的功能。该类使用 Skia 的 SVG 模块 (`SkSVGDOM`) 来解析和渲染 SVG 文件,支持资源提供者和文本整形等高级特性。

## 架构位置

`SvgSlide` 位于 Skia 的工具层,具体在 `tools/viewer` 目录下,是 Viewer 应用程序的一部分。它作为幻灯片系统的一个具体实现,用于在 Viewer 中展示 SVG 内容。该类依赖于 Skia 的核心库、SVG 模块、资源管理模块以及文本整形模块。

```
tools/viewer/
├── Slide (基类)
└── SvgSlide (SVG幻灯片实现)
    ├── SkSVGDOM (SVG文档对象模型)
    ├── SkResources (资源提供者)
    └── SkShaper (文本整形器)
```

## 主要类与结构体

### SvgSlide 类

```cpp
class SvgSlide final : public Slide {
public:
    SvgSlide(const SkString& name, const SkString& path);
    ~SvgSlide() override;

    void load(SkScalar winWidth, SkScalar winHeight) override;
    void unload() override;
    void resize(SkScalar, SkScalar) override;
    void draw(SkCanvas*) override;

private:
    const SkString  fPath;
    sk_sp<SkSVGDOM> fDom;
};
```

**核心成员变量:**
- `fPath`: 存储 SVG 文件的路径
- `fDom`: SVG 文档对象模型的智能指针,负责 SVG 的解析和渲染

## 公共 API 函数

### 构造与析构

**SvgSlide(const SkString& name, const SkString& path)**
- 构造函数,接受幻灯片名称和 SVG 文件路径
- 初始化 `fPath` 并设置幻灯片名称 `fName`

**~SvgSlide()**
- 默认析构函数,使用编译器生成的版本

### 生命周期管理

**void load(SkScalar w, SkScalar h)**
- 加载 SVG 文件并初始化 DOM 对象
- 从文件路径创建输入流
- 设置资源提供者 (`DataURIResourceProviderProxy`) 支持 Data URI
- 配置字体管理器和文本整形工厂
- 使用 `SkSVGDOM::Builder` 构建 SVG DOM
- 设置容器大小以匹配窗口尺寸

**void unload()**
- 释放 SVG DOM 对象
- 重置 `fDom` 智能指针

**void resize(SkScalar w, SkScalar h)**
- 响应窗口大小变化
- 更新 SVG DOM 的容器大小

### 渲染

**void draw(SkCanvas* canvas)**
- 将 SVG 内容渲染到画布
- 如果 DOM 对象存在,调用其 `render()` 方法

## 内部实现细节

### SVG 加载流程

1. **流创建**: 使用 `SkStream::MakeFromFile()` 从文件路径创建输入流
2. **错误处理**: 如果文件打开失败,输出调试信息并提前返回
3. **资源提供者配置**:
   - 使用 `FileResourceProvider` 从 SVG 文件所在目录加载外部资源
   - 包装在 `DataURIResourceProviderProxy` 中以支持 Data URI
   - 设置预解码策略 (`kPreDecode`)
4. **DOM 构建**:
   - 配置字体管理器 (`ToolUtils::TestFontMgr()`)
   - 设置资源提供者
   - 使用最佳可用的文本整形工厂 (`SkShapers::BestAvailable()`)
   - 从流中解析 SVG

### 条件编译

整个实现被包裹在 `#if defined(SK_ENABLE_SVG)` 宏中,确保只有在启用 SVG 支持时才编译该代码。

## 依赖关系

### 直接依赖

- **Skia 核心**: `SkCanvas`, `SkStream`, `SkString`, `SkScalar`
- **SVG 模块**: `SkSVGDOM`, `SkSVGNode`
- **资源模块**: `skresources::FileResourceProvider`, `skresources::DataURIResourceProviderProxy`
- **文本整形**: `SkShapers::BestAvailable()`
- **工具库**: `ToolUtils::TestFontMgr()`, `SkOSPath::Dirname()`

### 模块依赖

```
SvgSlide
├── modules/svg (SVG解析和渲染)
├── modules/skresources (资源管理)
├── modules/skshaper (文本整形)
└── tools/fonts (字体工具)
```

## 设计模式与设计决策

### 设计模式

1. **Builder 模式**: 使用 `SkSVGDOM::Builder` 构建复杂的 SVG DOM 对象,支持链式调用
2. **Resource Acquisition Is Initialization (RAII)**: 使用智能指针 `sk_sp` 管理 DOM 对象生命周期
3. **Proxy 模式**: `DataURIResourceProviderProxy` 包装 `FileResourceProvider`,增加 Data URI 支持

### 设计决策

1. **延迟加载**: SVG 文件在 `load()` 时加载,而非构造时,允许更灵活的资源管理
2. **自动资源管理**: 使用 `sk_sp` 智能指针,避免手动内存管理
3. **可配置资源提供者**: 支持从文件系统和 Data URI 加载资源,增强灵活性
4. **文本整形支持**: 集成文本整形工厂,确保复杂文本正确渲染
5. **容器大小响应**: 支持窗口大小变化,SVG 可根据容器大小自适应

## 性能考量

1. **预解码策略**: 使用 `kPreDecode` 策略,在资源加载时立即解码图像,避免渲染时的延迟
2. **流式加载**: 使用流接口加载文件,支持大文件的高效处理
3. **按需渲染**: 只在 `draw()` 调用时渲染,避免不必要的计算
4. **资源释放**: 提供 `unload()` 方法显式释放资源,支持内存管理优化
5. **智能指针开销**: 使用 `sk_sp` 引用计数智能指针,有轻微的原子操作开销,但保证线程安全

## 相关文件

- **tools/viewer/Slide.h**: `SvgSlide` 的基类定义
- **modules/svg/include/SkSVGDOM.h**: SVG DOM 的核心接口
- **modules/skresources/include/SkResources.h**: 资源提供者接口
- **modules/skshaper/utils/FactoryHelpers.h**: 文本整形工厂辅助函数
- **src/utils/SkOSPath.h**: 路径操作工具
- **tools/fonts/FontToolUtils.h**: 字体工具函数
- **tools/viewer/Viewer.cpp**: Viewer 主程序,可能注册和使用该幻灯片类
