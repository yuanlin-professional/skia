# SkSLSlide

> 源文件: tools/viewer/SkSLSlide.h, tools/viewer/SkSLSlide.cpp

## 概述

`SkSLSlide` 是 Skia Viewer 工具中的交互式 SkSL(Skia Shading Language)着色器编辑和测试环境。该组件提供了一个完整的着色器开发工作区,包含多行代码编辑器、实时编译和预览、uniform 参数调整、子着色器选择、几何形状切换、调试跟踪导出等功能。它支持 ShaderToy 风格的 uniform 变量(iResolution/iTime/iMouse),使得移植和测试着色器更加便捷。

该类使用 ImGui 构建了功能丰富的用户界面,允许开发者实时编辑 SkSL 代码并立即看到渲染结果。支持多种测试场景:填充整个画布、绘制圆形、圆角矩形、胶囊形状或文本。提供了调试跟踪功能,可以生成指定像素的 SkSL 执行跟踪,用于深度调试着色器逻辑。集成了备份机制,防止编译器崩溃导致代码丢失。

## 架构位置

`SkSLSlide` 位于 Skia 项目的 `tools/viewer` 目录下:

```
Slide (基础幻灯片接口)
  └─> SkSLSlide (SkSL 着色器实验室)
```

依赖的核心模块:
- **include/effects/SkRuntimeEffect.h**: SkSL 运行时编译和执行
- **include/sksl/SkSLDebugTrace.h**: SkSL 调试跟踪
- **tools/sksltrace/SkSLTraceUtils.h**: 跟踪文件读写工具
- **imgui.h**: ImGui 界面库
- **tools/viewer/Slide.h**: 幻灯片基类

## 主要类与结构体

### SkSLSlide

```cpp
class SkSLSlide : public Slide {
public:
    SkSLSlide();

    void draw(SkCanvas* canvas) override;
    bool animate(double nanos) override;
    void resize(SkScalar winWidth, SkScalar winHeight) override;
    void load(SkScalar winWidth, SkScalar winHeight) override;
    void unload() override;
    bool onMouse(SkScalar x, SkScalar y, skui::InputState state,
                 skui::ModifierKey modifiers) override;

private:
    bool rebuild();

    SkString fSkSL;                              // 用户代码
    bool fCodeIsDirty;                           // 代码是否需要重新编译
    sk_sp<SkRuntimeEffect> fEffect;              // 编译后的着色器效果
    skia_private::AutoTMalloc<char> fInputs;     // uniform 数据缓冲区
    skia_private::TArray<sk_sp<SkShader>> fChildren;  // 子着色器数组
    float fSeconds;                              // 动画时间(秒)

    enum Geometry {
        kFill, kCircle, kRoundRect, kCapsule, kText,
    };
    int fGeometry;                               // 当前几何形状
    SkV3 fResolution;                            // iResolution uniform
    SkV4 fMousePos;                              // iMouse uniform
    int fTraceCoord[2];                          // 调试跟踪坐标
    bool fShadertoyUniforms;                     // 是否启用 ShaderToy uniform

    skia_private::TArray<std::pair<const char*, sk_sp<SkShader>>> fShaders;  // 预设着色器
};
```

**关键成员变量**:
- `fSkSL`: 用户编辑的 SkSL 源代码
- `fCodeIsDirty`: 脏标志,标记代码修改后需要重新编译
- `fEffect`: 编译成功后的 `SkRuntimeEffect` 对象
- `fInputs`: 动态分配的 uniform 数据缓冲区,大小等于 `fEffect->uniformSize()`
- `fChildren`: 子着色器数组,用于 `uniform shader` 参数
- `fSeconds`: 从启动到当前的秒数,赋值给 `iTime` uniform
- `fGeometry`: 选择的测试几何形状(填充/圆形/圆角矩形/胶囊/文本)
- `fResolution`: 窗口分辨率,赋值给 `iResolution` uniform
- `fMousePos`: 鼠标状态,赋值给 `iMouse` uniform(格式兼容 ShaderToy)
- `fTraceCoord`: 调试跟踪的目标像素坐标
- `fShadertoyUniforms`: 是否自动添加 ShaderToy 风格的 uniform 声明
- `fShaders`: 预设的着色器列表(渐变、图像等),用于子着色器选择

## 公共 API 函数

### 构造函数

```cpp
SkSLSlide::SkSLSlide()
```

初始化默认着色器代码:
```cpp
fSkSL = "uniform shader child;\n"
        "\n"
        "half4 main(float2 p) {\n"
        "    return child.eval(p);\n"
        "}\n";
fCodeIsDirty = true;
```

简单的透传着色器,演示子着色器用法。

### 生命周期

```cpp
void load(SkScalar winWidth, SkScalar winHeight) override
```

加载预设着色器:
```cpp
fShaders.push_back(std::make_pair("Null", nullptr));
fShaders.push_back(std::make_pair("Linear Gradient", linearShader));
fShaders.push_back(std::make_pair("Radial Gradient", radialShader));
fShaders.push_back(std::make_pair("Sweep Gradient", sweepShader));
fShaders.push_back(std::make_pair("Mandrill", imageShader));
fResolution = { winWidth, winHeight, 1.0f };
```

提供线性/径向/扫描渐变和图像纹理作为子着色器选项。

```cpp
void unload() override
```

清理所有资源:
```cpp
fEffect.reset();
fInputs.reset();
fChildren.clear();
fShaders.clear();
```

### 渲染与动画

```cpp
void draw(SkCanvas* canvas) override
```

核心渲染函数,执行以下流程:
1. 清空画布为白色
2. 构建 ImGui 编辑界面(代码编辑器、uniform 控件、子着色器选择等)
3. 如果代码脏,调用 `rebuild()` 重新编译
4. 如果请求调试跟踪,创建跟踪着色器并裁剪渲染区域
5. 根据选择的几何形状绘制着色器
6. 如果生成了跟踪,导出到文件

```cpp
bool animate(double nanos) override
```

更新时间 uniform:
```cpp
fSeconds = static_cast<float>(nanos * 1E-9);
return true;  // 持续重绘
```

```cpp
void resize(SkScalar winWidth, SkScalar winHeight) override
```

更新分辨率 uniform:
```cpp
fResolution = { winWidth, winHeight, 1.0f };
```

```cpp
bool onMouse(...) override
```

始终返回 true,表示接受鼠标输入(ImGui 内部处理)。

## 内部实现细节

### 着色器编译流程

```cpp
bool SkSLSlide::rebuild() {
    // 1. 添加 ShaderToy uniform(可选)
    SkString sksl;
    if (fShadertoyUniforms) {
        sksl = "uniform float3 iResolution;\n"
               "uniform float  iTime;\n"
               "uniform float4 iMouse;\n";
    }
    sksl.append(fSkSL);

    // 2. 备份代码到文件,防止编译器崩溃丢失
    constexpr char kBackupFile[] = "sksl.bak";
    FILE* backup = fopen(kBackupFile, "w");
    if (backup) {
        fwrite(fSkSL.c_str(), 1, fSkSL.size(), backup);
        fclose(backup);
    }

    // 3. 编译着色器
    auto [effect, errorText] = SkRuntimeEffect::MakeForShader(sksl);

    // 4. 编译成功后删除备份
    if (backup) {
        std::remove(kBackupFile);
    }

    // 5. 处理错误
    if (!effect) {
        Viewer::ShaderErrorHandler()->compileError(sksl.c_str(), errorText.c_str());
        return false;
    }

    // 6. 重新分配 uniform 缓冲区
    size_t oldSize = fEffect ? fEffect->uniformSize() : 0;
    fInputs.realloc(effect->uniformSize());
    if (effect->uniformSize() > oldSize) {
        memset(fInputs.get() + oldSize, 0, effect->uniformSize() - oldSize);
    }

    // 7. 调整子着色器数组大小
    fChildren.resize_back(effect->children().size());

    fEffect = effect;
    fCodeIsDirty = false;
    return true;
}
```

**关键设计**:
- 备份机制防止编译器断言导致的代码丢失
- 扩展 uniform 缓冲区时,新空间清零
- 保留旧数据,避免用户调整的 uniform 值丢失

### ImGui 界面构建

**代码编辑器**:
```cpp
ImGuiInputTextFlags flags = ImGuiInputTextFlags_CallbackResize;
ImVec2 boxSize(-1.0f, ImGui::GetTextLineHeight() * 30);
if (ImGui::InputTextMultiline("Code", fSkSL.data(), fSkSL.size() + 1, boxSize, flags,
                              InputTextCallback, &fSkSL)) {
    fCodeIsDirty = true;
}
```

使用 `CallbackResize` 支持动态扩展 `SkString`,回调函数处理内存重新分配。

**Uniform 控件**:
```cpp
for (const SkRuntimeEffect::Uniform& v : fEffect->uniforms()) {
    char* data = fInputs.get() + v.offset;

    // 跳过自动管理的 ShaderToy uniform
    if (v.name == "iResolution" || v.name == "iTime" || v.name == "iMouse") {
        memcpy(data, &相应变量, sizeof(...));
        continue;
    }

    // 根据类型生成控件
    switch (v.type) {
        case SkRuntimeEffect::Uniform::Type::kFloat:
        case SkRuntimeEffect::Uniform::Type::kFloat2:
        case SkRuntimeEffect::Uniform::Type::kFloat3:
        case SkRuntimeEffect::Uniform::Type::kFloat4: {
            int rows = ((int)v.type - (int)SkRuntimeEffect::Uniform::Type::kFloat) + 1;
            float* f = reinterpret_cast<float*>(data);
            for (int c = 0; c < v.count; ++c, f += rows) {
                SkString name = v.isArray()
                        ? SkStringPrintf("%s[%d]", v.name.data(), c)
                        : SkString(v.name);
                ImGui::DragScalarN(name.c_str(), ImGuiDataType_Float, f, rows, 1.0f);
            }
            break;
        }
        // ... 类似处理矩阵和整数类型
    }
}
```

动态生成 ImGui 滑块,支持标量、向量、矩阵和数组 uniform。

**子着色器选择**:
```cpp
for (const SkRuntimeEffect::Child& c : fEffect->children()) {
    // 查找当前选择的着色器
    auto curShader = std::find_if(fShaders.begin(), fShaders.end(), ...);

    if (ImGui::BeginCombo(std::string(c.name).c_str(), curShader->first)) {
        for (const auto& namedShader : fShaders) {
            if (ImGui::Selectable(namedShader.first, ...)) {
                fChildren[c.index] = namedShader.second;
            }
        }
        ImGui::EndCombo();
    }
}
```

下拉菜单选择预设着色器作为子着色器输入。

### 鼠标状态管理

实现 ShaderToy 兼容的鼠标 uniform:
```cpp
ImVec2 mousePos = ImGui::GetMousePos();
if (ImGui::IsMouseDown(0)) {
    fMousePos.x = mousePos.x;
    fMousePos.y = mousePos.y;
}
if (ImGui::IsMouseClicked(0)) {
    fMousePos.z = mousePos.x;
    fMousePos.w = mousePos.y;
}
// z 和 w 的符号表示鼠标状态
fMousePos.z = std::abs(fMousePos.z) * (ImGui::IsMouseDown(0) ? 1 : -1);
fMousePos.w = std::abs(fMousePos.w) * (ImGui::IsMouseClicked(0) ? 1 : -1);
```

**iMouse 格式**(ShaderToy 标准):
- `.xy`: 当前鼠标位置(按下时更新)
- `.zw`: 点击位置,符号表示状态(正=按下,负=释放)

### 调试跟踪

生成指定像素的执行跟踪:
```cpp
if (writeTrace || writeDump) {
    SkIPoint traceCoord = {fTraceCoord[0], fTraceCoord[1]};
    SkRuntimeEffect::TracedShader traced = SkRuntimeEffect::MakeTraced(
        std::move(shader), traceCoord);
    shader = std::move(traced.shader);
    debugTrace = std::move(traced.debugTrace);

    // 裁剪到 4x4 区域,减少跟踪开销
    SkM44 canvasMatrix = canvas->getLocalToDevice();
    canvas->resetMatrix();
    auto r = SkRect::MakeXYWH(fTraceCoord[0] - 1, fTraceCoord[1] - 1, 4, 4);
    canvas->clipRect(r, SkClipOp::kIntersect);
    canvas->setMatrix(canvasMatrix);
}

// 渲染后导出跟踪
if (debugTrace && writeTrace) {
    SkFILEWStream traceFile("SkSLDebugTrace.json");
    SkSLTraceUtils::WriteTrace(*debugTrace, &traceFile);
}
if (debugTrace && writeDump) {
    SkFILEWStream dumpFile("SkSLDebugTrace.dump.txt");
    debugTrace->dump(&dumpFile);
}
```

**优化策略**:
- 裁剪到 4x4 区域(目标像素周围),大幅减少跟踪开销
- 在设备空间裁剪,避免变换影响

### 几何形状绘制

```cpp
switch (fGeometry) {
    case kFill:
        canvas->drawPaint(p);
        break;
    case kCircle:
        canvas->drawCircle({ 256, 256 }, 256, p);
        break;
    case kRoundRect:
        canvas->drawRoundRect({ 0, 0, 512, 512 }, 64, 64, p);
        break;
    case kCapsule:
        canvas->drawRoundRect({ 0, 224, 512, 288 }, 32, 32, p);
        break;
    case kText: {
        SkFont font = ToolUtils::DefaultFont();
        font.setSize(96);
        canvas->drawSimpleText("Hello World", ..., font, p);
    } break;
}
```

不同几何形状测试着色器在不同绘制场景下的行为。

## 依赖关系

### 直接依赖

- **include/effects/SkRuntimeEffect.h**: SkSL 运行时编译
  - `MakeForShader()`: 编译着色器
  - `makeShader()`: 创建着色器实例
  - `MakeTraced()`: 创建跟踪着色器
- **include/sksl/SkSLDebugTrace.h**: 调试跟踪接口
- **tools/sksltrace/SkSLTraceUtils.h**: 跟踪文件IO
- **imgui.h**: ImGui 界面库
- **tools/Resources.h**: 资源加载
- **tools/DecodeUtils.h**: 图像解码
- **tools/fonts/FontToolUtils.h**: 字体工具

## 设计模式与设计决策

### 脏标志模式

使用 `fCodeIsDirty` 延迟编译:
```cpp
if (ImGui::InputTextMultiline(...)) {
    fCodeIsDirty = true;  // 标记脏
}
if (fCodeIsDirty || !fEffect) {
    this->rebuild();  // 按需重新编译
}
```

避免每次按键都编译,仅在渲染前编译一次。

### 数据驱动 UI

根据 `SkRuntimeEffect` 的 uniform 元数据动态生成 UI:
```cpp
for (const SkRuntimeEffect::Uniform& v : fEffect->uniforms()) {
    // 根据 v.type、v.count、v.isArray() 生成控件
}
```

支持任意 SkSL 着色器,无需硬编码 UI。

### 崩溃恢复机制

编译前备份代码:
```cpp
FILE* backup = fopen("sksl.bak", "w");
fwrite(fSkSL.c_str(), 1, fSkSL.size(), backup);
fclose(backup);

auto [effect, errorText] = SkRuntimeEffect::MakeForShader(sksl);

std::remove("sksl.bak");  // 成功后删除
```

如果编译器断言,用户可以从 `sksl.bak` 恢复代码。

### ShaderToy 兼容性

提供 ShaderToy 风格的 uniform:
```cpp
uniform float3 iResolution;  // 分辨率
uniform float  iTime;        // 时间
uniform float4 iMouse;       // 鼠标状态
```

简化从 ShaderToy 移植着色器的过程。

## 性能考量

### 延迟编译

仅在代码脏时重新编译,避免无效开销。

### 跟踪裁剪优化

调试跟踪时裁剪到 4x4 区域:
```cpp
auto r = SkRect::MakeXYWH(fTraceCoord[0] - 1, fTraceCoord[1] - 1, 4, 4);
canvas->clipRect(r, SkClipOp::kIntersect);
```

将跟踪开销从全屏降低到 16 像素,大幅提升性能。

### Uniform 缓冲区复用

编译后保留旧 uniform 值:
```cpp
if (effect->uniformSize() > oldSize) {
    memset(fInputs.get() + oldSize, 0, effect->uniformSize() - oldSize);
}
```

仅清零新增部分,保留用户调整的值。

## 相关文件

### SkSL 系统

- **include/effects/SkRuntimeEffect.h**: 运行时着色器
- **include/sksl/SkSLDebugTrace.h**: 调试跟踪
- **src/sksl/**: SkSL 编译器
- **tools/sksltrace/SkSLTraceUtils.h**: 跟踪工具

### Viewer 集成

- **tools/viewer/Slide.h**: 幻灯片基类
- **tools/viewer/Viewer.h**: Viewer 主应用
- **tools/viewer/SkSLDebuggerSlide.h**: 调试器幻灯片(配合使用)

### 使用场景

该组件用于:
1. **SkSL 开发**: 实时编辑和测试着色器
2. **算法原型**: 快速验证图形算法
3. **教学演示**: 演示着色器编程概念
4. **调试**: 生成执行跟踪,定位 bug
5. **ShaderToy 移植**: 测试移植的着色器

典型工作流程:
1. 在代码编辑器中编写 SkSL 着色器
2. 调整 uniform 参数,观察实时效果
3. 切换几何形状,测试不同绘制场景
4. 如果遇到问题,输入像素坐标并生成调试跟踪
5. 在 SkSLDebuggerSlide 中加载跟踪文件,逐步调试

该组件是 SkSL 开发的核心工具,提供了生产级的着色器开发环境。
