# tskit/bindings - C++ Embind 绑定层

## 概述

`bindings/` 包含将 Skia C++ API 通过 Emscripten 的 embind 机制暴露给
TypeScript/JavaScript 的绑定代码。

## 目录结构

```
bindings/
├── bindings.h       # 绑定公共头文件
├── core.cpp         # 核心 API 绑定（Canvas、Paint 等）
├── core.d.ts        # 核心 API TypeScript 类型声明
├── embind.d.ts      # embind 基础类型声明
├── extension.cpp    # 扩展 API 绑定
└── extension.d.ts   # 扩展 API TypeScript 类型声明
```

## 相关文档与参考

- Emscripten embind: https://emscripten.org/docs/porting/connecting_cpp_and_javascript/embind.html
