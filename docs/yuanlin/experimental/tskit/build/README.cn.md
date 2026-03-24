# tskit/build - 构建输出目录

## 概述

`build/` 包含 tskit 编译过程中生成的中间文件和输出文件。

## 目录结构

```
build/
└── externs.js       # Google Closure Compiler 外部声明文件
```

## 关键文件

- **externs.js**: 为 Closure Compiler 定义的外部符号声明，确保代码压缩时
  不会错误地重命名这些符号。

## 相关文档与参考

- Closure Compiler: https://developers.google.com/closure/compiler
