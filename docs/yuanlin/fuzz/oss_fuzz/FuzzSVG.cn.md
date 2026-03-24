# FuzzSVG (OSS-Fuzz)

> 源文件: fuzz/oss_fuzz/FuzzSVG.cpp

## 概述

测试 Skia 的 SVG 解析和渲染功能。SVG(可缩放矢量图形)是广泛使用的矢量图形格式,解析器需要处理复杂的 XML 和 CSS 语法。

## 架构位置

测试 `modules/svg/` 中的 SVG 模块,包括 DOM 构建、样式解析和渲染。

## 主要类与结构体

### FuzzSVG 函数

```cpp
void FuzzSVG(const uint8_t *data, size_t size)
```

执行流程:
1. 创建内存流: `SkMemoryStream(data, size)`
2. 使用 Builder 构建 SVG DOM:
   - 设置可移植字体管理器
   - 设置文本整形工厂
3. 设置容器尺寸(100x200)
4. 渲染到 128x128 的光栅 surface

### LLVMFuzzerTestOneInput

最大输入 30000 字节,平衡 SVG 复杂度和性能。

## 内部实现细节

### SVG 特性测试

- XML 解析
- CSS 样式
- 路径数据(path d 属性)
- 变换(transform)
- 渐变和图案
- 文本整形和字体

### 条件编译

```cpp
#if defined(SK_ENABLE_SVG)
```

只在启用 SVG 支持时编译。

## 依赖关系

- `modules/svg/include/SkSVGDOM.h`: SVG DOM 接口
- `modules/skshaper/`: 文本整形
- `tools/fonts/TestFontMgr.h`: 可移植字体管理

## 设计模式与设计决策

**Builder 模式**: SVG DOM 使用构建器模式配置字体和整形器。

## 性能考量

- SVG 解析是 CPU 密集型操作
- 30KB 限制防止超大文件导致超时
- 固定渲染尺寸限制内存使用

## 相关文件

- `modules/svg/src/SkSVGDOM.cpp`: DOM 实现
- `modules/svg/src/SkSVGRenderContext.cpp`: 渲染上下文

该 fuzzer 发现了多个 SVG 解析和渲染问题,是 Skia SVG 模块质量保证的关键工具。
