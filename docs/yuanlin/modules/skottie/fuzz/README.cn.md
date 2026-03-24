# skottie/fuzz - 模糊测试

## 概述

`fuzz/` 目录包含 Skottie 模块的模糊测试 (Fuzz Testing) 代码。模糊测试通过向 Skottie 的 JSON 解析器输入随机或变异的数据,检测潜在的崩溃、内存错误和未定义行为。这对于确保 Skottie 在面对恶意或损坏的 Lottie 文件时的鲁棒性至关重要。

## 目录结构

```
fuzz/
├── BUILD.bazel              # Bazel 构建配置
└── FuzzSkottieJSON.cpp      # Skottie JSON 模糊测试入口
```

## 关键测试

### FuzzSkottieJSON.cpp

模糊测试入口函数,接收随机字节输入:
- 将输入数据作为 JSON 字符串传入 `Animation::Make()`
- 如果成功构建动画,执行 `seekFrame()` 和 `render()` 操作
- 验证整个流程不会崩溃或产生内存错误

该测试通常与 OSS-Fuzz 或 libFuzzer 集成,在 CI 流水线中持续运行。

## 依赖关系

```
fuzz/
  ├── skottie/include/Skottie.h (Animation::Make)
  ├── include/core (SkCanvas, SkSurface, SkData)
  └── Skia 模糊测试框架
```

## 相关文档与参考

- **Skottie 主文档**: `docs/yuanlin/modules/skottie/README.md`
- **OSS-Fuzz**: Google 开源模糊测试服务
- **单元测试**: `docs/yuanlin/modules/skottie/tests/README.md`
