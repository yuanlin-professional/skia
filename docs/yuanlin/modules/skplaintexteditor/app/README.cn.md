# skplaintexteditor/app - 编辑器应用程序

## 概述

`modules/skplaintexteditor/app/` 目录包含基于 `Editor` 类构建的文本编辑器示例应用程序。`editor_application.cpp` 是一个完整的交互式纯文本编辑器,展示了如何将 Editor 模块与 Skia 的窗口系统集成。

该应用处理键盘和鼠标事件,将其转换为 Editor 的操作调用(文本插入、删除、光标移动、文本选择等),并持续将编辑器状态渲染到窗口画布上。

## 目录结构

```
app/
+-- editor_application.cpp  # 编辑器应用入口与事件处理
```

## 相关文档与参考

- Editor API: `modules/skplaintexteditor/include/editor.h`
- 模块概述: `modules/skplaintexteditor/README.md`
