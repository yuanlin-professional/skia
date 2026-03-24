# SkottieUtils - Skottie 动画工具集

> 源文件: [`modules/skottie/utils/SkottieUtils.h`](../../../modules/skottie/utils/SkottieUtils.h), [`modules/skottie/utils/SkottieUtils.cpp`](../../../modules/skottie/utils/SkottieUtils.cpp)

## 概述

SkottieUtils 提供了一组用于 Skottie（Lottie 动画渲染器）的实用工具类，主要包括自定义属性管理器（CustomPropertyManager）和外部动画预合成拦截器（ExternalAnimationPrecompInterceptor）。这些工具简化了在运行时动态操纵 Lottie 动画属性（颜色、不透明度、变换、文本）以及嵌套外部动画的流程。

## 架构位置

位于 Skottie 模块的 utils 子目录中：

- **上层使用者**: 应用程序代码、Viewer 工具、动画编辑器
- **核心依赖**: Skottie 动画库（Animation、PropertyObserver、MarkerObserver）
- **资源层**: skresources::ResourceProvider（外部动画加载用）

## 主要类与结构体

### `CustomPropertyManager` 类

属性管理器，实现按名称分组的属性一对多映射管理。

```cpp
class CustomPropertyManager final {
public:
    enum class Mode {
        kCollapseProperties,   // 按本地节点名称分组
        kNamespacedProperties, // 包含祖先节点名称（无分组）
    };
    explicit CustomPropertyManager(Mode = Mode::kNamespacedProperties, const char* prefix = nullptr);
};
```

支持四种属性类型的 get/set 操作：
- **颜色属性** (`Color`): `getColorProps()`, `getColor()`, `setColor()`
- **不透明度属性** (`Opacity`): `getOpacityProps()`, `getOpacity()`, `setOpacity()`
- **变换属性** (`Transform`): `getTransformProps()`, `getTransform()`, `setTransform()`
- **文本属性** (`Text`): `getTextProps()`, `getText()`, `setText()`

### `MarkerInfo` 结构体
动画标记信息，包含标记名称和时间范围 [t0, t1]。

### `ExternalAnimationPrecompInterceptor` 类
预合成拦截器，将匹配指定名称前缀的预合成层替换为外部 Lottie 动画。

### `PropertyInterceptor` 内部类
PropertyObserver 的实现，在动画构建时拦截属性声明，按键名分组存储到 PropMap 中。支持节点路径追踪（onEnterNode/onLeavingNode）。

### `MarkerInterceptor` 内部类
MarkerObserver 的实现，收集动画中的所有标记信息。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `getColorProps()` / `getColor()` / `setColor()` | 颜色属性的列出/读取/设置 |
| `getOpacityProps()` / `getOpacity()` / `setOpacity()` | 不透明度属性操作 |
| `getTransformProps()` / `getTransform()` / `setTransform()` | 变换属性操作 |
| `getTextProps()` / `getText()` / `setText()` | 文本属性操作 |
| `getColorHandle()` / `getOpacityHandle()` / `getTransformHandle()` / `getTextHandle()` | 获取指定索引的属性句柄 |
| `markers()` | 获取所有标记信息 |
| `getPropertyObserver()` | 获取用于 Animation::Builder 的属性观察者 |
| `getMarkerObserver()` | 获取用于 Animation::Builder 的标记观察者 |

## 内部实现细节

### 属性键名构建
`acceptKey()` 方法根据模式生成键名：
- `kCollapseProperties`: 直接使用节点名称，同名属性会被分组
- `kNamespacedProperties`: 使用完整的节点路径（如 "Layer.Shape.Fill.Color"），每个属性独立

属性名称必须以指定前缀开头（默认 "$"），不匹配的属性被忽略。

### 外部动画嵌套
ExternalAnimationPrecompInterceptor 的工作流程：
1. `onLoadPrecomp` 被调用时，检查预合成名称是否以指定前缀开头
2. 通过 ResourceProvider 加载外部动画数据
3. 使用 Animation::Builder 构建嵌套动画，递归传递 PrecompInterceptor
4. 封装为 ExternalAnimationLayer，在 render 时调用嵌套动画的 seekFrameTime + render

### 模板化实现
使用 `PropMap<T>` 和 `PropGroup<T>` 模板避免四种属性类型的代码重复。get/set/getProps/getHandle 都是模板方法。

## 依赖关系

- `modules/skottie/include/SkottieProperty.h` - 属性句柄和值类型
- `modules/skottie/include/ExternalLayer.h` - 外部层接口
- `modules/skottie/include/Skottie.h` - Animation 类
- `modules/skresources/include/SkResources.h` - 资源提供者

## 设计模式与设计决策

### 观察者模式
通过 PropertyObserver 和 MarkerObserver 接口在动画构建时拦截属性声明，实现了构建与管理的解耦。

### 一对多属性映射
setter 将值应用到同组中的所有属性句柄，getter 返回组中第一个句柄的值。这假设同组内所有属性具有相同的值。

### 前缀过滤
只有以指定前缀开头的属性才会被管理，允许选择性地暴露可操纵的属性。

## 性能考量

- PropMap 使用 unordered_map 提供 O(1) 键查找
- set 操作遍历组内所有句柄，复杂度与组大小成正比
- 外部动画递归使用相同的 PrecompInterceptor，支持多级嵌套但需注意循环引用

## 相关文件

- `modules/skottie/include/SkottieProperty.h` - 属性句柄定义
- `modules/skottie/include/Skottie.h` - 动画构建器
- `modules/skottie/utils/TextEditor.h` - 基于属性管理的文本编辑器
