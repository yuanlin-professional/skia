# skottie/tests - 单元测试

## 概述

`tests/` 目录包含 Skottie 模块的单元测试。这些测试覆盖了 Skottie 的主要功能,包括图像加载、文本渲染、音频图层、属性观察、关键帧动画、文本排版和 AE 表达式等方面。测试使用 Skia 的标准测试框架 (`DEF_TEST` 宏)编写。

## 目录结构

```
tests/
├── BUILD.bazel              # Bazel 构建配置
├── Image.cpp                # 图像加载和渲染测试
├── Text.cpp                 # 文本图层和文本属性测试
├── AudioLayer.cpp           # 音频图层事件触发测试
├── PropertyObserver.cpp     # PropertyObserver 回调测试
├── Keyframe.cpp             # 关键帧解析和插值测试
├── Shaper.cpp               # Shaper 文本排版测试
└── Expression.cpp           # AE 表达式求值测试
```

## 关键测试

### Image.cpp
- 测试 `ImageAsset` 的加载机制
- 测试延迟加载 (`kDeferImageLoading`) 行为
- 验证图像帧在 seek 时正确获取

### Text.cpp
- 测试 `TextPropertyValue` 的属性设置和获取
- 测试文本动画器的逐字符/逐词/逐行模式
- 验证文本排版结果的正确性

### PropertyObserver.cpp
- 测试 `PropertyObserver` 的回调时机
- 验证 `onEnterNode` / `onLeavingNode` 配对
- 测试 `PropertyHandle` 的 `get()` / `set()` 操作

### Keyframe.cpp
- 测试常量/线性/贝塞尔关键帧插值
- 测试边界条件 (超出范围、单帧)
- 验证 `KeyframeAnimator::getLERPInfo()` 的正确性

### Shaper.cpp
- 测试点文本和框文本排版
- 测试垂直/水平对齐
- 测试自适应缩放 (`ScaleToFit` / `DownscaleToFit`)
- 测试换行策略和 Unicode 处理

### Expression.cpp
- 测试 `ExpressionManager` 集成
- 测试数值/字符串/数组表达式求值器

## 依赖关系

```
tests/
  ├── skottie/include (完整公开 API)
  ├── skresources (测试用 ResourceProvider)
  ├── Skia 测试框架 (DEF_TEST, REPORTER_ASSERT)
  └── skjson (测试用 JSON 数据)
```

## 相关文档与参考

- **Skottie 主文档**: `docs/yuanlin/modules/skottie/README.md`
- **GM 测试**: `docs/yuanlin/modules/skottie/gm/README.md`
- **模糊测试**: `docs/yuanlin/modules/skottie/fuzz/README.md`
