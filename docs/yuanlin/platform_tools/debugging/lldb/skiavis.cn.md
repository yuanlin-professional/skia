# skiavis

> 源文件: platform_tools/debugging/lldb/skiavis.py

## 概述

`skiavis.py` 是 Skia 提供的 LLDB 调试器可视化辅助脚本,专门为 VSCode 的 CodeLLDB 调试器扩展设计。该脚本提供了在调试会话中将 Skia 对象(如 `SkPath`)可视化为 SVG 图形的能力,显著提升了图形代码的调试体验。通过在 VSCode 调试界面直接渲染 SVG,开发者可以实时查看路径数据的视觉表示,而无需运行完整的图形渲染流程。

该脚本利用 CodeLLDB 的 HTML 显示功能和 Skia 的 `SkParsePath::ToSVGString()` API,实现了从调试器表达式到可视化图形的无缝转换。

## 架构位置

```
skia/
├── platform_tools/
│   └── debugging/
│       └── lldb/
│           └── skiavis.py          # 本文件
├── include/utils/
│   └── SkParsePath.h               # SVG 路径转换 API
├── src/utils/
│   └── SkParsePath.cpp             # SVG 路径转换实现
└── .vscode/
    └── launch.json                 # VSCode 调试配置(可能包含 initCommands)
```

该文件位于 `platform_tools/debugging/lldb/` 目录,作为开发工具链的一部分,不参与 Skia 库的编译或运行时。

## 主要类与结构体

该脚本没有定义类或结构体,只包含函数和导入语句。

**导入模块**:
- `lldb`: LLDB 调试器 Python API
- `debugger`: CodeLLDB 提供的调试器交互模块(用于显示 HTML)

## 公共 API 函数

### `show_path(path)`

**功能**: 将 `SkPath` 对象可视化为 SVG 图形并在 VSCode 调试界面显示

**参数**:
- `path` (str): 包含路径表达式的字符串,如变量名 `'fPath'` 或完整表达式 `'myObject->getPath()'`

**返回值**: 无(通过副作用在调试器中显示 HTML)

**实现流程**:
1. 使用 `debugger.evaluate()` 在调试器上下文中执行表达式:
   ```python
   pathStr = debugger.evaluate('SkParsePath::ToSVGString(' + path +
                               ', SkParsePath::PathEncoding::Absolute)')
   ```
   - 调用 Skia 的 `SkParsePath::ToSVGString()` 将 `SkPath` 转换为 SVG 路径字符串
   - 使用绝对坐标编码(Absolute)

2. 构造最小 SVG 文档:
   ```python
   svg = '<svg><path d="' + pathStr + '"/></svg>'
   ```

3. 在 VSCode 调试面板显示 HTML:
   ```python
   debugger.display_html(svg)
   ```

**用法示例**:
在 VSCode 调试控制台(LLDB prompt)输入:
```
?/py skiavis.show_path('fPath')
```

或在 Watch 窗口中:
```
?/py skiavis.show_path('this->fPath')
```

**适用场景**:
- 调试路径绘制算法
- 验证路径变换结果
- 检查路径裁剪和布尔运算
- 快速可视化复杂路径数据

## 内部实现细节

### CodeLLDB 集成

**debugger.evaluate()**:
- 在当前调试上下文(帧)中执行 C++ 表达式
- 返回表达式的字符串表示形式
- 要求表达式必须有效且可在当前作用域访问

**debugger.display_html()**:
- CodeLLDB 特有的功能,在 VSCode 的调试控制台渲染 HTML
- 支持基本 SVG 渲染,包括路径、形状、变换等
- 不支持 JavaScript 或复杂 CSS

### SkParsePath API

**`SkParsePath::ToSVGString(const SkPath& path, PathEncoding encoding)`**:
- 将 SkPath 的内部表示转换为 SVG 路径数据字符串
- `PathEncoding::Absolute`: 使用绝对坐标(M, L, C 等命令)
- 返回符合 SVG 规范的 `d` 属性字符串

**路径命令映射**:
- `SkPath::moveTo()` → `M x y`
- `SkPath::lineTo()` → `L x y`
- `SkPath::cubicTo()` → `C x1 y1 x2 y2 x y`
- `SkPath::close()` → `Z`

### 加载机制

**手动加载**:
在 LLDB prompt 输入:
```
command script import /path/to/skia/platform_tools/debugging/lldb/skiavis.py
```

**自动加载**:
在 `.vscode/launch.json` 的 `configurations` 中添加:
```json
{
    "initCommands": [
        "command script import ${workspaceFolder}/platform_tools/debugging/lldb/skiavis.py"
    ]
}
```

**注意事项**:
- CodeLLDB 的 LLDB 实例不会自动执行 `~/.lldbinit`
- 必须通过 `initCommands` 或手动执行 `command script import`
- 该脚本依赖 CodeLLDB 特有的 `debugger` 模块,无法在命令行 LLDB 中使用

## 依赖关系

### 外部依赖
- **lldb**: LLDB Python API(调试器环境自带)
- **debugger**: CodeLLDB VSCode 扩展提供的模块

### Skia 依赖
- **SkParsePath::ToSVGString()**: Skia 的 SVG 路径转换函数

### 工具依赖
- **VSCode**: 编辑器
- **CodeLLDB 扩展**: VSCode 的 LLDB 调试器扩展(作者 vadimcn)

### 依赖图
```
VSCode CodeLLDB 扩展
    ↓
skiavis.py (本脚本)
    ↓
LLDB Python API + debugger 模块
    ↓
被调试的 Skia 进程 (SkParsePath::ToSVGString)
```

## 设计模式与设计决策

### 1. 表达式求值模式
使用调试器的表达式求值功能调用目标进程的函数,避免数据提取和序列化的复杂性。

### 2. 薄包装层
脚本本身只是薄包装,实际的路径处理由 Skia 代码完成,确保可视化结果与实际运行时行为一致。

### 3. 最小 SVG
生成最简单的 SVG 标记,依赖浏览器的默认样式(黑色描边,无填充)。

### 4. 用户友好的 API
提供简单的字符串参数而非复杂的对象操作,降低使用门槛。

### 5. 特定环境优化
专为 CodeLLDB 设计,不追求跨调试器兼容性,换取更好的集成体验。

### 6. 声明式文档
通过详细注释说明使用方法和限制,弥补脚本本身缺少运行时帮助的问题。

## 性能考量

### 1. 按需执行
只在用户显式调用时执行,无后台开销。

### 2. 表达式求值开销
`debugger.evaluate()` 在目标进程中执行代码,涉及:
- 暂停所有线程
- 编译表达式(JIT)
- 执行函数调用
- 序列化返回值

对于复杂路径,`ToSVGString()` 可能需要几毫秒。

### 3. HTML 渲染
SVG 渲染由 VSCode 的 webview 处理,与调试器主线程异步执行,不阻塞调试会话。

### 4. 内存影响
生成的 SVG 字符串驻留在目标进程内存中,但通常很小(<100KB)。

### 5. 潜在优化
- 缓存最近显示的路径,避免重复求值
- 提供简化选项(降低路径精度)以加快渲染

## 相关文件

### 核心实现
- `platform_tools/debugging/lldb/skiavis.py`: 本文件

### Skia API
- `include/utils/SkParsePath.h`: SVG 路径转换声明
- `src/utils/SkParsePath.cpp`: SVG 路径转换实现
- `include/core/SkPath.h`: SkPath 类定义

### 调试配置
- `.vscode/launch.json`: VSCode 调试配置(可能包含 initCommands)
- `~/.lldbinit`: 命令行 LLDB 配置(不适用于 CodeLLDB)

### 相关工具
- `platform_tools/debugging/gdb/`: GDB 的类似可视化脚本(如果存在)
- `tools/debugger/`: Skia 的图形调试工具(独立应用)

### 文档资源
- [CodeLLDB Data Visualization](https://github.com/vadimcn/vscode-lldb/wiki/Data-visualization): 官方文档
- [LLDB Python API](https://lldb.llvm.org/python_api.html): LLDB 脚本参考

### 使用示例
- Skia 开发者可在任何使用 SkPath 的代码中使用此脚本,如:
  - `src/core/SkPath.cpp`: 路径操作实现
  - `src/core/SkPathMeasure.cpp`: 路径测量
  - `src/core/SkStroke.cpp`: 路径描边

### 扩展可能
- **show_matrix()**: 可视化 SkMatrix 变换
- **show_rect()**: 显示 SkRect 边界
- **show_region()**: 可视化 SkRegion 区域
- **show_picture()**: 渲染 SkPicture 记录的绘制命令

## 使用限制

### 1. 平台限制
- **仅支持 VSCode + CodeLLDB**: 不适用于命令行 LLDB、Xcode LLDB 或 GDB
- **需要图形环境**: 纯终端 SSH 会话无法显示 SVG

### 2. 对象类型限制
- **仅支持 SkPath**: 无法直接可视化 SkCanvas、SkPicture 等其他对象
- **需要有效路径**: 空路径或无效路径可能显示为空白

### 3. 表达式限制
- **必须可在当前帧求值**: 变量必须在作用域内且可访问
- **不支持副作用**: 如果表达式修改状态,可能影响调试准确性

### 4. 性能限制
- **复杂路径可能缓慢**: 包含数千条命令的路径可能需要数秒渲染
- **暂停所有线程**: 求值期间目标进程完全停止

### 5. 显示限制
- **简单样式**: 使用浏览器默认样式,无法自定义颜色、宽度
- **固定视口**: SVG 大小由浏览器决定,可能需要缩放查看全图

## 未来增强

### 建议功能
1. **多对象可视化**: 支持一次显示多个路径或形状
2. **交互式查看**: 添加缩放、平移、网格等控件
3. **样式配置**: 支持自定义颜色、描边宽度、填充
4. **动画支持**: 显示路径动画或变换序列
5. **差异比较**: 并排显示两个路径的差异
6. **性能分析**: 显示路径复杂度指标(命令数、边界框等)

### 实现考虑
- 需要 CodeLLDB 扩展的持续支持
- 可能需要更复杂的 HTML/CSS/JavaScript
- 平衡功能丰富性与脚本简洁性
