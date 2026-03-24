# GMSlide

> 源文件: tools/viewer/GMSlide.h, tools/viewer/GMSlide.cpp

## 概述

`GMSlide` 是 Skia Viewer 工具中的一个适配器类,用于将 GM(Golden Master)测试用例转换为可在 Viewer 中展示的 Slide。GM 是 Skia 的标准测试图形单元,而 Slide 是 Viewer 应用程序中的可视化展示单元。`GMSlide` 充当了两者之间的桥梁,使得成千上万的 GM 测试可以在交互式的 Viewer 环境中浏览和调试。

该类通过封装 `skiagm::GM` 对象,提供了 Slide 接口所需的所有功能,包括绘制、动画、用户交互和控件管理。它确保 GM 测试能够以正确的模式运行,并将其输出适配到 Viewer 的渲染管线中。

## 架构位置

`GMSlide` 位于 Skia 项目的工具层(tools),具体在 viewer 子系统中:

```
skia/
├── gm/                          # GM 测试用例库
│   └── gm.h                     # GM 基类定义
├── tools/
│   └── viewer/
│       ├── Slide.h              # Slide 基类接口
│       ├── GMSlide.h            # GMSlide 声明
│       ├── GMSlide.cpp          # GMSlide 实现
│       └── Viewer.cpp           # Viewer 主应用
└── include/core/                # Skia 核心 API
```

该类是 Viewer 架构中的适配器组件,使得测试框架(GM)能够无缝集成到可视化工具(Viewer)中。

## 主要类与结构体

### GMSlide 类

```cpp
class GMSlide : public Slide {
public:
    explicit GMSlide(std::unique_ptr<skiagm::GM> gm);
    ~GMSlide() override;

    // Slide 接口实现
    SkISize getDimensions() const override;
    void gpuTeardown() override;
    void setSurfaceProps(SkSurfaceProps*) override;
    void draw(SkCanvas* canvas) override;
    bool animate(double nanos) override;
    bool onChar(SkUnichar c) override;
    bool onGetControls(SkMetaData*) override;
    void onSetControls(const SkMetaData&) override;

private:
    std::unique_ptr<skiagm::GM> fGM;  // 被封装的 GM 对象
};
```

**成员变量**:
- `fGM`: 独占所有权的 GM 对象指针,存储实际的测试图形实例

**继承关系**:
- 继承自 `Slide` 基类,实现其虚函数接口

## 公共 API 函数

### 构造与析构

```cpp
explicit GMSlide(std::unique_ptr<skiagm::GM> gm);
```
- 接收一个 GM 对象的独占指针
- 设置 GM 为 `kSample_Mode` 模式
- 构造 Slide 名称为 "GM_" + GM 名称的格式

```cpp
~GMSlide() override = default;
```
- 使用编译器生成的默认析构函数
- 自动释放 `fGM` 的内存

### 尺寸查询

```cpp
SkISize getDimensions() const override;
```
- 返回 GM 测试用例的画布尺寸
- 直接委托给 `fGM->getISize()`

### 渲染管理

```cpp
void draw(SkCanvas* canvas) override;
```
- 执行 GM 的绘制操作
- 首先调用 `gpuSetup` 进行 GPU 初始化
- 如果设置成功,调用 `fGM->draw()` 进行实际绘制

```cpp
void setSurfaceProps(SkSurfaceProps*) override;
```
- 允许 GM 修改 Surface 属性
- 委托给 `fGM->modifySurfaceProps()`

### GPU 资源管理

```cpp
void gpuTeardown() override;
```
- 清理 GM 相关的 GPU 资源
- 委托给 `fGM->gpuTeardown()`

### 动画支持

```cpp
bool animate(double nanos) override;
```
- 传递时间戳给 GM 以支持动画
- 返回值指示是否需要重绘

### 用户交互

```cpp
bool onChar(SkUnichar c) override;
```
- 处理键盘输入事件
- 委托给 `fGM->onChar()`

### 控件系统

```cpp
bool onGetControls(SkMetaData*) override;
```
- 获取 GM 的可配置控件信息
- 用于在 UI 中显示交互式控件

```cpp
void onSetControls(const SkMetaData&) override;
```
- 应用用户通过控件设置的参数
- 更新 GM 的内部状态

## 内部实现细节

### 模式设置

在构造函数中,GMSlide 将 GM 设置为 `kSample_Mode`:

```cpp
fGM->setMode(skiagm::GM::kSample_Mode);
```

这个模式表示 GM 作为交互式样例运行,而非自动化测试。

### 错误处理

在 `draw()` 方法中,实现了简单但有效的错误处理:

```cpp
auto result = fGM->gpuSetup(canvas, &msg);
if (result != skiagm::GM::DrawResult::kOk) {
    return;  // 如果 GPU 设置失败,提前返回
}
```

这确保了只有在 GPU 准备就绪时才进行绘制。

### 委托模式

几乎所有的 GMSlide 方法都采用委托模式,直接转发调用到内部的 `fGM` 对象:

```cpp
bool animate(double nanos) override {
    return fGM->animate(nanos);
}

bool onChar(SkUnichar c) override {
    return fGM->onChar(c);
}
```

这种设计使得 GMSlide 成为一个轻量级的适配器,不添加额外的逻辑复杂度。

### 命名约定

GMSlide 使用统一的命名约定:

```cpp
fName.printf("GM_%s", fGM->getName().c_str());
```

在 Viewer 中,所有 GM 测试的名称都以 "GM_" 前缀开头,便于识别和过滤。

## 依赖关系

### 直接依赖

- `gm/gm.h`: GM 基类定义
- `tools/viewer/Slide.h`: Slide 基类接口
- `include/core/SkCanvas.h`: 画布绘制接口
- `include/core/SkSurfaceProps.h`: Surface 属性配置
- `include/core/SkString.h`: 字符串操作
- `include/core/SkMetaData.h`: 元数据存储

### 间接依赖

- `include/core/SkSize.h`: 尺寸定义
- `include/core/SkTypes.h`: 基础类型定义

### 依赖方向

```
GMSlide 依赖 -> GM (组合关系)
GMSlide 继承 -> Slide (继承关系)
Viewer 使用 -> GMSlide (聚合关系)
```

## 设计模式与设计决策

### 适配器模式

GMSlide 是适配器模式的典型应用:
- **目标接口**: `Slide`
- **被适配者**: `skiagm::GM`
- **适配器**: `GMSlide`

这种模式允许 GM 测试(原本设计用于自动化测试)在不修改其代码的情况下,能够在交互式 Viewer 中使用。

### 委托模式

所有功能实现都委托给内部的 GM 对象,GMSlide 不添加额外的业务逻辑。这保持了代码的简洁性和可维护性。

### 智能指针所有权

使用 `std::unique_ptr<skiagm::GM>` 确保:
- 清晰的所有权语义(GMSlide 独占 GM 对象)
- 自动内存管理
- 移动语义支持(构造时使用 `std::move`)

### 接口隔离

GMSlide 只暴露 Slide 接口,隐藏了 GM 的具体实现细节。外部代码只需要知道这是一个 Slide,而无需了解底层的 GM 机制。

### 明确的生命周期管理

- 构造时接管 GM 对象的所有权
- 析构时自动释放 GM 资源
- `gpuTeardown()` 提供显式的 GPU 资源清理点

## 性能考量

### 零拷贝设计

GMSlide 使用移动语义和指针传递,避免了大对象的拷贝:

```cpp
GMSlide::GMSlide(std::unique_ptr<skiagm::GM> gm) : fGM(std::move(gm))
```

### 按需设置

GPU 资源的设置在每次 `draw()` 调用时进行,而非构造时。这允许:
- 延迟资源分配
- 适应上下文切换(例如,在不同 GPU 后端之间切换)
- 更灵活的资源管理

### 快速路径优化

在 `draw()` 中,如果 GPU 设置失败,立即返回而不进行绘制:

```cpp
if (result != skiagm::GM::DrawResult::kOk) {
    return;  // 快速失败路径
}
```

### 最小化虚函数开销

虽然继承自 Slide 基类,但所有虚函数调用都是单层委托,没有多级虚函数链,保持了调用效率。

## 相关文件

### 核心相关

- `tools/viewer/Slide.h`: 定义了 Slide 基类接口
- `gm/gm.h`: 定义了 GM 测试框架
- `tools/viewer/Viewer.cpp`: 使用 GMSlide 的主应用程序

### 其他 Slide 实现

- `tools/viewer/SKPSlide.h`: 用于显示 SKP 文件的 Slide
- `tools/viewer/ImageSlide.h`: 用于显示图像的 Slide
- `tools/viewer/SkottieSlide.h`: 用于显示 Lottie 动画的 Slide

### 测试用例

Skia 包含数百个 GM 测试用例,所有这些都可以通过 GMSlide 在 Viewer 中查看:
- `gm/aarectmodes.cpp`
- `gm/alphagradients.cpp`
- `gm/beziers.cpp`
- 等等...

这些 GM 文件通过 GMSlide 适配器,统一成为 Viewer 中的可视化内容。
