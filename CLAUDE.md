# 项目指令

## 源码文档整理标准

当用户要求"整理某个源文件的文档"时，输出到 `docs/yuanlin/` 对应路径，文件名为 `{OriginalName}.cn.md`，按以下结构组织：

### 标准章节结构

1. **标题行**: `# {ClassName/ModuleName} 函数实现参考`
2. **源码引用** (blockquote):
   - `> 源码: \`src/path/to/File.cpp\` (总行数)`
   - `> 头文件: \`src/path/to/File.h\``
3. **类型速查** (`## 类型速查`):
   - 按职责分组（自身类型 / 几何数学 / 操作策略 / 渲染上下文 / 着色器 / 纹理资源 / 容器工具）
   - 每组用表格 `| 类型 | 含义 |` 列出所有非基础类型
   - 覆盖 .h 和 .cpp 中出现的所有非 naive 类型（排除 int/bool/string 等基本类型）
4. **架构位置** (`## {ClassName} 在 Skia 工程中的架构位置`):
   - 表格说明归属/接口/上游/下游
   - mermaid flowchart 展示调用链
5. **架构总览** (`## 架构总览`):
   - mermaid classDiagram 展示核心类字段和方法
6. **函数实现** (按功能分组编号 `## N. {组名}`):
   - 每个函数: `### N.M \`functionName()\` (line X-Y)`
   - 优先使用 mermaid flowchart 可视化逻辑分支
   - 简单函数可用表格或文字描述
   - 每个函数节后加 `---` 分隔
7. **附录** (`## 附录: {主题}`):
   - 状态机图 (stateDiagram-v2)
   - 类型关系图
   - 其他补充图表

### 范例参考

黄金标准: `docs/yuanlin/src/gpu/ganesh/ClipStack.cn.md`

### 注意事项

- 所有图表使用 mermaid 语法
- 中文撰写，类型名/函数名/枚举值保留英文原名
- 每个 `##` 章节之间用 `---` 分隔
- 函数标注行号范围便于对照源码
