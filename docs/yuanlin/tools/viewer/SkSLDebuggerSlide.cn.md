# SkSLDebuggerSlide

> 源文件: tools/viewer/SkSLDebuggerSlide.h, tools/viewer/SkSLDebuggerSlide.cpp

## 概述

`SkSLDebuggerSlide` 是 Skia Viewer 工具中的一个交互式调试器界面,专门用于调试和分析 SkSL(Skia Shading Language)着色器程序。该组件提供了一个完整的图形化调试环境,允许开发者加载调试跟踪文件、单步执行着色器代码、查看调用栈、检查变量状态,并设置断点进行调试。它集成了 ImGui 界面库,提供了友好的用户交互体验,使得复杂的着色器程序调试变得更加直观和高效。

该调试器的核心功能包括加载 JSON 格式的调试跟踪数据、提供代码单步执行控制(step、step over、step out)、实时显示变量值的变化、支持断点管理,以及可视化展示函数调用栈。通过颜色高亮和表格视图,开发者可以清晰地追踪代码执行流程,快速定位着色器程序中的问题。

## 架构位置

`SkSLDebuggerSlide` 位于 Skia 项目的 `tools/viewer` 目录下,属于开发工具层。它继承自 `Slide` 基类,这是 Viewer 工具框架中用于展示不同内容页面的抽象接口。该组件依赖于以下核心模块:

- **SkSL 跟踪系统**: 使用 `src/sksl/tracing/` 中的 `SkSLDebugTracePlayer` 和 `SkSLDebugTracePriv` 类来管理调试跟踪数据和控制执行流程
- **Viewer 框架**: 继承 `tools/viewer/Slide.h` 并遵循其生命周期管理接口
- **ImGui 界面库**: 用于渲染所有调试界面元素
- **工具支持**: 依赖 `tools/sksltrace/SkSLTraceUtils.h` 来解析跟踪文件

该组件在 Skia 工具链中扮演着开发辅助角色,主要服务于着色器开发者和图形工程师,帮助他们理解和优化 SkSL 代码的执行行为。

## 主要类与结构体

### SkSLDebuggerSlide

主调试器幻灯片类,继承自 `Slide`:

```cpp
class SkSLDebuggerSlide : public Slide {
public:
    SkSLDebuggerSlide();

    // Slide 接口实现
    void draw(SkCanvas* canvas) override;
    bool animate(double nanos) override;
    void resize(SkScalar winWidth, SkScalar winHeight) override {}
    void load(SkScalar winWidth, SkScalar winHeight) override;
    void unload() override;
    bool onMouse(SkScalar x, SkScalar y, skui::InputState state,
                 skui::ModifierKey modifiers) override { return true; }

private:
    // GUI 渲染方法
    void showRootGUI();
    void showLoadTraceGUI();
    void showDebuggerGUI();
    void showStackTraceTable();
    void showVariableTable();
    void showCodeTable();

    // 数据成员
    sk_sp<SkSL::DebugTracePriv> fTrace;
    SkSL::SkSLDebugTracePlayer fPlayer;
    bool fRefresh;
    char fTraceFile[256];

    static constexpr int kNumTopRows = 12;
};
```

**关键成员变量**:
- `fTrace`: 智能指针,指向调试跟踪数据的私有表示,包含源代码、函数信息、槽位信息等
- `fPlayer`: 调试跟踪播放器,控制代码执行流程和状态查询
- `fRefresh`: 标志位,指示是否需要刷新视图(例如滚动到当前执行行)
- `fTraceFile`: 存储跟踪文件路径的字符缓冲区,默认为 "SkSLDebugTrace.json"
- `kNumTopRows`: 常量,定义调用栈和变量表格显示的行数(12行)

### 使用的外部类型

- **SkSL::DebugTracePriv**: 存储完整的调试跟踪数据,包括源代码行、函数信息、槽位(变量)信息
- **SkSL::SkSLDebugTracePlayer**: 提供调试控制接口,如 `step()`、`stepOver()`、`stepOut()`、`run()`
- **SkSL::FunctionDebugInfo**: 函数调试信息结构,包含函数名等元数据
- **SkSL::SlotDebugInfo**: 变量槽位调试信息,包含变量名和类型信息
- **LineNumberMap**: 行号映射表,用于跟踪哪些行被执行过

## 公共 API 函数

### 构造函数

```cpp
SkSLDebuggerSlide::SkSLDebuggerSlide()
```

初始化调试器幻灯片,设置名称为 "Debugger",创建空的调试跟踪对象。

### 生命周期管理

```cpp
void load(SkScalar winWidth, SkScalar winHeight) override
```

加载幻灯片时调用,当前实现为空,未进行特殊初始化。

```cpp
void unload() override
```

卸载幻灯片时调用,重置所有调试状态:
- 重新创建空的 `fTrace` 对象
- 重置调试播放器为 `nullptr`
- 清除所有断点

### 渲染与交互

```cpp
void draw(SkCanvas* canvas) override
```

主渲染函数,每帧调用:
- 清空画布为白色背景
- 创建 ImGui 窗口 "Debugger",启用垂直滚动条
- 调用 `showRootGUI()` 渲染调试界面
- 关闭 ImGui 窗口

```cpp
bool animate(double nanos) override
```

动画更新函数,始终返回 `true` 表示需要持续重绘(因为 ImGui 需要实时响应)。

```cpp
bool onMouse(SkScalar x, SkScalar y, skui::InputState state,
             skui::ModifierKey modifiers) override
```

鼠标事件处理,始终返回 `true`,表示接受所有鼠标输入(实际由 ImGui 内部处理)。

```cpp
void resize(SkScalar winWidth, SkScalar winHeight) override
```

窗口大小调整回调,当前为空实现。

## 内部实现细节

### GUI 渲染架构

调试器采用分层 GUI 渲染架构:

1. **showRootGUI()**: 根界面,根据 `fTrace` 状态决定显示加载界面或调试界面
2. **showLoadTraceGUI()**: 文件加载界面,提供路径输入和加载按钮,处理加载错误弹窗
3. **showDebuggerGUI()**: 主调试界面,包含控制按钮和三个子表格视图
4. **showStackTraceTable()**: 调用栈表格,显示函数调用层级
5. **showVariableTable()**: 变量表格,显示当前作用域的变量名和值
6. **showCodeTable()**: 代码表格,显示源代码、行号、断点和当前执行行

### 跟踪文件加载流程

```cpp
void showLoadTraceGUI() {
    ImGui::InputText("Trace Path", fTraceFile, std::size(fTraceFile));
    bool load = ImGui::Button("Load Debug Trace");

    if (load) {
        SkFILEStream file(fTraceFile);
        if (!file.isValid()) {
            ImGui::OpenPopup("Can't Open Trace");
        } else {
            fTrace = SkSLTraceUtils::ReadTrace(&file);
            if (!fTrace) {
                ImGui::OpenPopup("Invalid Trace");
            } else {
                fPlayer.reset(fTrace);
                fPlayer.step();  // 初始执行一步
                fRefresh = true;  // 触发视图刷新
            }
        }
    }
    // 错误弹窗处理...
}
```

加载成功后,播放器执行初始步进,将视图标记为需要刷新。

### 调试控制逻辑

```cpp
void showDebuggerGUI() {
    if (ImGui::Button("Reset")) {
        fPlayer.reset(fTrace);
        fRefresh = true;
    }
    if (ImGui::Button("Step")) {
        fPlayer.step();  // 单步执行
        fRefresh = true;
    }
    if (ImGui::Button("Step Over")) {
        fPlayer.stepOver();  // 跨过函数调用
        fRefresh = true;
    }
    if (ImGui::Button("Step Out")) {
        fPlayer.stepOut();  // 跳出当前函数
        fRefresh = true;
    }
    if (ImGui::Button(fPlayer.getBreakpoints().empty() ? "Run" : "Run to Breakpoint")) {
        fPlayer.run();  // 运行到断点或结束
        fRefresh = true;
    }
    // 渲染子表格...
}
```

所有控制操作都会触发 `fRefresh` 标志,用于自动滚动代码视图到当前执行行。

### 代码视图实现

代码表格使用 ImGui 的高级特性:

- **ImGuiListClipper**: 实现虚拟滚动,仅渲染可见行,优化大文件性能
- **行号按钮**: 根据行是否可达(reachable)和是否设置断点显示不同颜色
  - 红色: 已设置断点
  - 白色半透明: 可达行(可设置断点)
  - 灰色: 不可达行(不可设置断点)
- **当前行高亮**: 使用 `ImGuiTableBgTarget_RowBg1` 和 `ImGuiCol_TextSelectedBg` 高亮当前执行行
- **自动滚动**: 当 `fRefresh` 为真时,计算中心行并调用 `ImGui::SetScrollY()` 滚动到视图中央

```cpp
if (fRefresh) {
    int linesVisible = contentRect.y / ImGui::GetTextLineHeightWithSpacing();
    int centerLine = (fPlayer.getCurrentLine() - 1) - (linesVisible / 2);
    centerLine = std::max(0, centerLine);
    ImGui::SetScrollY(clipper.ItemsHeight * centerLine);
    fRefresh = false;
}
```

### 变量表格实现

变量表格显示当前作用域的所有变量:

```cpp
int frame = fPlayer.getStackDepth() - 1;
std::vector<SkSL::SkSLDebugTracePlayer::VariableData> vars;
if (frame >= 0) {
    vars = fPlayer.getLocalVariables(frame);  // 局部变量
} else {
    vars = fPlayer.getGlobalVariables();  // 全局变量
}
```

对于每个变量:
- 显示名称(包括组件后缀,如 `.x`、`.y`)
- 显示格式化的值
- 如果变量在上一步被修改(`var.fDirty`),用绿色背景高亮

### 调用栈表格实现

调用栈从底部到顶部显示:

```cpp
std::vector<int> callStack = fPlayer.getCallStack();
for (int row = clipper.DisplayStart; row < clipper.DisplayEnd; row++) {
    int funcIdx = callStack.rbegin()[row];  // 反向迭代器,从栈顶开始
    const SkSL::FunctionDebugInfo& funcInfo = fTrace->fFuncInfo[funcIdx];
    ImGui::Text("%s", funcInfo.name.c_str());
}
```

使用反向迭代器确保栈顶函数(当前函数)显示在表格顶部。

## 依赖关系

### 直接依赖

- **include/core/SkRefCnt.h**: 引用计数智能指针 `sk_sp` 支持
- **include/core/SkCanvas.h**: 画布绘制接口
- **include/core/SkStream.h**: 文件流读取(`SkFILEStream`)
- **src/sksl/tracing/SkSLDebugTracePlayer.h**: 调试播放器核心逻辑
- **src/sksl/tracing/SkSLDebugTracePriv.h**: 调试跟踪数据结构
- **tools/viewer/Slide.h**: Viewer 框架基类
- **tools/sksltrace/SkSLTraceUtils.h**: 跟踪文件解析工具
- **imgui.h**: ImGui 界面库

### 间接依赖

- **tools/sk_app/Application.h**: Viewer 应用程序框架
- **include/private/base/SkAssert.h**: 断言宏
- **include/core/SkString.h**: 字符串格式化工具

### 数据流向

```
[跟踪文件 JSON]
    -> SkSLTraceUtils::ReadTrace()
    -> DebugTracePriv
    -> SkSLDebugTracePlayer
    -> GUI 显示
```

用户通过 ImGui 控件触发播放器操作,播放器更新内部状态,GUI 查询播放器状态并渲染。

## 设计模式与设计决策

### MVC 模式变体

- **Model**: `DebugTracePriv` 存储跟踪数据,`SkSLDebugTracePlayer` 管理执行状态
- **View**: ImGui 表格和控件负责渲染
- **Controller**: `SkSLDebuggerSlide` 协调用户输入、播放器操作和视图更新

### 状态管理

使用 `fRefresh` 标志延迟视图更新,避免每次操作都立即滚动,仅在需要时触发一次滚动计算。

### 错误处理策略

采用 ImGui 模态弹窗处理错误:
- 文件不存在: "Can't Open Trace" 弹窗
- 解析失败: "Invalid Trace" 弹窗

这种方式友好地通知用户错误,无需崩溃或复杂的错误传播机制。

### 虚拟化渲染

使用 `ImGuiListClipper` 实现所有表格的虚拟滚动:
- 仅渲染可见范围内的行
- 支持大型着色器文件(数千行)而不影响性能
- 自动处理滚动条和鼠标滚轮事件

### 颜色编码设计

通过颜色传达不同状态:
- **当前执行行**: 蓝色背景高亮
- **断点**: 红色按钮
- **可达行**: 白色半透明
- **不可达行**: 灰色
- **已修改变量**: 绿色背景

这种视觉反馈极大提升了调试效率。

### 数据驱动界面

所有显示内容都从 `fTrace` 和 `fPlayer` 查询:
- 源代码从 `fTrace->fSource` 获取
- 变量信息从 `fTrace->fSlotInfo` 获取
- 当前状态从 `fPlayer.getCurrentLine()`、`fPlayer.getCallStack()` 等获取

这使得调试器可以支持任意 SkSL 程序,无需硬编码。

## 性能考量

### 虚拟滚动优化

对于大型着色器文件(例如 1000+ 行),直接渲染所有行会导致严重性能问题。ImGuiListClipper 通过以下方式优化:

```cpp
ImGuiListClipper clipper;
clipper.Begin(fTrace->fSource.size());
while (clipper.Step()) {
    for (int row = clipper.DisplayStart; row < clipper.DisplayEnd; row++) {
        // 仅渲染可见行
    }
}
```

典型场景下,仅渲染 20-30 行,而非全部数千行,性能提升数十倍。

### 延迟刷新机制

`fRefresh` 标志确保滚动计算仅在状态改变后执行一次:

```cpp
if (fRefresh) {
    // 计算滚动位置...
    ImGui::SetScrollY(...);
    fRefresh = false;  // 防止重复计算
}
```

这避免了每帧都计算滚动位置,减少 CPU 占用。

### 字符串格式化缓存

变量值通过 `fTrace->slotValueToString()` 格式化,该方法在 `DebugTracePriv` 中实现,可能包含缓存逻辑以避免重复格式化相同的值。

### 表格大小约束

调用栈和变量表格限制为 `kNumTopRows = 12` 行高度:

```cpp
ImVec2 stackViewSize = ImVec2(contentRect.x / 3.0f,
                              ImGui::GetTextLineHeightWithSpacing() * kNumTopRows);
```

这确保即使调用栈或变量数量很大,也不会占据过多屏幕空间,保持界面平衡。

### 按钮点击优化

断点按钮使用 `ImGui::SmallButton()` 而非普通按钮,减少渲染开销和内存占用。

## 相关文件

### 核心依赖文件

- **src/sksl/tracing/SkSLDebugTracePlayer.h**: 调试播放器接口,提供 `step()`、`stepOver()`、`stepOut()`、`run()` 等核心控制方法
- **src/sksl/tracing/SkSLDebugTracePlayer.cpp**: 播放器实现,管理执行指针、断点和变量状态
- **src/sksl/tracing/SkSLDebugTracePriv.h**: 调试跟踪数据结构定义
- **tools/sksltrace/SkSLTraceUtils.h**: 提供 `ReadTrace()` 函数解析 JSON 跟踪文件

### 框架支持文件

- **tools/viewer/Slide.h**: Viewer 幻灯片基类,定义 `draw()`、`load()`、`unload()` 等接口
- **tools/sk_app/Application.h**: Viewer 应用程序主框架

### 界面库

- **imgui.h**: Dear ImGui 库,提供所有 GUI 组件和渲染逻辑

### SkSL 编译器

- **src/sksl/**: SkSL 编译器目录,生成调试跟踪数据的源头

### 使用示例

开发者在 Viewer 工具中选择 "Debugger" 幻灯片,输入跟踪文件路径(通常由 SkSL 编译器生成),点击 "Load Debug Trace" 后即可开始调试 SkSL 着色器。典型工作流程:

1. 使用带调试选项的 SkSL 编译器编译着色器,生成 `SkSLDebugTrace.json`
2. 在 Viewer 中加载该文件
3. 使用 Step/Step Over/Step Out 按钮逐步执行
4. 观察变量表格中的值变化
5. 在关键行设置断点,使用 Run to Breakpoint 快速定位问题
6. 通过调用栈表格理解函数调用关系

该工具对于复杂着色器的调试和优化至关重要,尤其是在处理多层嵌套函数调用和复杂数据流时。
