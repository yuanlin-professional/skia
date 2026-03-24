# skottie/gm - GPU/图形测试 (GM)

## 概述

`gm/` 目录包含 Skottie 模块的 GM (Golden Master / Graphics Method) 测试。GM 测试是 Skia 的标准可视化回归测试框架,用于生成参考图像并与基准进行像素级对比,确保渲染结果的一致性。

## 目录结构

```
gm/
├── BUILD.bazel              # Bazel 构建配置
├── SkottieGM.cpp            # Skottie 渲染 GM 测试
└── ExternalProperties.cpp   # 外部属性操控 GM 测试
```

## 关键测试

### SkottieGM.cpp
Skottie 的核心 GM 测试,通常:
- 加载预定义的 Lottie JSON
- 在不同时间点 seek
- 渲染到固定尺寸的画布
- 输出用于与基准比对的图像

### ExternalProperties.cpp
测试通过 `PropertyObserver` 和 `CustomPropertyManager` 外部修改动画属性后的渲染结果,验证属性操控不会导致渲染异常。

## 依赖关系

```
gm/
  ├── skottie/include (Animation, Builder)
  ├── skottie/utils (CustomPropertyManager)
  ├── Skia GM 框架 (skiagm::GM)
  └── include/core (SkCanvas, SkSurface)
```

## 相关文档与参考

- **Skottie 主文档**: `docs/yuanlin/modules/skottie/README.md`
- **单元测试**: `docs/yuanlin/modules/skottie/tests/README.md`
