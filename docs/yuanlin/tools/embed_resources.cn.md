# embed_resources - 资源嵌入 C++ 代码生成器

> 源文件: `tools/embed_resources.py`

## 概述

`embed_resources.py` 将二进制资源文件转换为嵌入式的 C++ 代码,生成包含只读数据数组的 `.cpp` 文件。编译链接后可通过 `SkEmbeddedHeader` 结构体在运行时访问这些资源。

## 架构位置

属于 Skia 构建工具链,用于将字体、图片等资源嵌入可执行文件。

## 公共 API 函数

- **`main()`**: 解析参数,读取输入文件,生成 C++ 源代码

## 内部实现细节

- 生成的结构: `SkEmbeddedResource {data, size}` 和 `SkEmbeddedHeader {entries, count}`
- 支持自定义对齐(`--align`)和导出名称(`--name`)
- 数据以十六进制字节数组形式输出,每行 32 字节
- 导出符号使用 `extern "C"` 确保 C 链接

## 依赖关系

- Python 标准库: `argparse`

## 设计模式与设计决策

- **编译时嵌入**: 将资源编译为 C++ 代码避免运行时文件访问
- **对齐控制**: 支持 SIMD 等场景需要的数据对齐

## 性能考量

生成的代码在运行时零开销访问资源数据。

## 相关文件

- `tools/ResourceFactory.h` - 资源工厂接口
