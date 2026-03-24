# TextEditor - Skottie 文本编辑器

> 源文件: [`modules/skottie/utils/TextEditor.h`](../../../modules/skottie/utils/TextEditor.h), [`modules/skottie/utils/TextEditor.cpp`](../../../modules/skottie/utils/TextEditor.cpp)

## 概述

TextEditor 是一个基于 Skottie GlyphDecorator API 构建的所见即所得（WYSIWYG）文本编辑器示例实现。它允许用户在 Lottie 动画中直接编辑文本内容，支持光标显示、文本选择、字符插入和删除等基本编辑操作。

该编辑器通过 GlyphDecorator 接口在字形渲染阶段绘制光标和选区，并通过 TextPropertyHandle 修改文本内容。

## 架构位置

位于 Skottie 工具层：

- **上层调用者**: Viewer 工具、演示应用
- **核心接口**: skottie::GlyphDecorator（文本装饰器基类）
- **数据操作**: skottie::TextPropertyHandle（文本属性句柄）
- **输入处理**: skui::InputState、skui::ModifierKey

## 主要类与结构体

### `TextEditor` 类
继承自 `skottie::GlyphDecorator`，实现文本编辑功能。

```cpp
class TextEditor final : public skottie::GlyphDecorator {
public:
    TextEditor(std::unique_ptr<skottie::TextPropertyHandle>&&,
               std::vector<std::unique_ptr<skottie::TextPropertyHandle>>&&);
    void toggleEnabled();
    void setEnabled(bool);
    void onDecorate(SkCanvas*, const TextInfo&) override;
    bool onMouseInput(SkScalar x, SkScalar y, skui::InputState, skui::ModifierKey);
    bool onCharInput(SkUnichar c);
    void setCursorWeight(float w);
};
```

### `GlyphData` 内部结构体
存储字形的设备空间包围盒和 UTF-8 簇索引，用于鼠标点击时的字形定位。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `toggleEnabled()` | 切换编辑模式的启用/禁用 |
| `setEnabled(bool)` | 设置编辑模式状态 |
| `onDecorate(canvas, textInfo)` | GlyphDecorator 回调，绘制光标和选区 |
| `onMouseInput(x, y, state, modKey)` | 处理鼠标输入（选择文本） |
| `onCharInput(c)` | 处理字符输入 |
| `setCursorWeight(w)` | 设置光标笔画粗细 |

## 内部实现细节

### 光标绘制
光标是一个标准化的 I 形路径（宽 0.2，高 0.75，相对于字体大小），以 2Hz 频率闪烁。使用双色描边（外白内黑）确保在任何背景上都有足够对比度。光标定位在当前字符的右侧，底部对齐基线。

### 文本选择
- 鼠标按下时记录选区起点（最近字形）
- 鼠标拖动时更新选区终点
- 选区以半透明蓝色矩形绘制在选中字形的 bounds 上
- 选区可以反向（起点 > 终点）

### 字符输入映射
由于自然编辑快捷键被 Viewer 工具拦截，使用替代绑定：
- `]` - 光标右移
- `[` - 光标左移
- `\` - 删除（前一个字符或选区）
- `|` - 提交更改并退出编辑模式
- 其他字符 - 插入

### UTF-8 导航
`next_utf8()` 和 `prev_utf8()` 实现 UTF-8 安全的光标移动，正确跳过多字节序列。`prev_utf8` 通过向前探测最多 4 个字节来定位前一个字符的起始位置。

### 依赖属性同步
`updateDeps()` 将文本更改同步到所有依赖的 TextPropertyHandle，支持多个文本层共享同一文本内容。

## 依赖关系

- `modules/skottie/include/SkottieProperty.h` - TextPropertyHandle、GlyphDecorator
- `include/core/SkCanvas.h` - 绘制光标和选区
- `include/core/SkPath.h` / `SkPathBuilder.h` - 光标路径
- `src/base/SkUTF.h` - UTF-8 导航
- `tools/skui/InputState.h` - 输入状态枚举

## 设计模式与设计决策

### 装饰器模式
通过实现 GlyphDecorator 接口，在不修改文本渲染流程的前提下叠加编辑 UI（光标、选区）。

### 启用/禁用状态管理
启用时将自身设为文本属性的 decorator，禁用时清除。这确保了在非编辑模式下零性能开销。

### 双色光标
使用白色外描边 + 黑色内描边的双层绘制策略，保证在浅色和深色背景上都可见。

## 性能考量

- `closestGlyph()` 使用 O(n) 线性搜索，适合典型的短文本场景
- 每次 onDecorate 调用时重建 fGlyphData，避免缓存失效问题
- 光标闪烁使用 steady_clock 计时，无需额外定时器

## 相关文件

- `modules/skottie/include/SkottieProperty.h` - GlyphDecorator 和 TextPropertyHandle 定义
- `modules/skottie/utils/SkottieUtils.h` - CustomPropertyManager（获取 TextPropertyHandle）
- `tools/skui/InputState.h` - 输入状态枚举定义
