# minify_sksl_tests.py - SkSL 测试代码压缩器

> 源文件: `gn/minify_sksl_tests.py`

## 概述
批量压缩 SkSL 着色器测试文件,调用 `sksl-minify` 工具将 `.rts`、`.rtcf`、`.rtb`、`.mfrag`、`.mvert` 等文件转换为压缩版本。

## 架构位置
Skia SkSL 构建工具链的一部分。

## 公共 API 函数
无,作为构建脚本执行。

## 内部实现细节
根据文件扩展名确定着色器类型(--shader、--colorfilter、--blender 等),生成 worklist 文件传给 sksl-minify。支持逐个编译和批量编译两种模式。

## 依赖关系
- `sksl-minify` 工具
- SkSL 模块文件(shared_module、public_module、rt_shader_module)

## 相关文件
- `gn/minify_sksl.py`, `gn/compile_sksl_tests.py`
