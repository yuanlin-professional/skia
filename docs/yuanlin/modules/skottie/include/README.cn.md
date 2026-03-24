# skottie/include - 公开 API 头文件

## 概述

`include/` 目录包含 Skottie 模块的所有公开 API 头文件。这些头文件定义了客户端与 Skottie 交互的完整接口,包括动画创建与播放、属性观察与操控、外部图层注入、插槽管理以及文本排版配置。

此目录是 Skottie 模块唯一面向外部暴露的接口层。所有使用 `SK_API` 宏导出的类和函数都在这里声明。内部实现细节位于 `src/` 目录中,客户端不应直接依赖。

## 目录结构

```
include/
├── BUILD.bazel            # Bazel 构建配置
├── Skottie.h              # 核心 API 入口
├── SkottieProperty.h      # 属性系统
├── ExternalLayer.h        # 外部图层接口
├── SlotManager.h          # 插槽管理
└── TextShaper.h           # 文本排版器
```

## 关键类与函数

### Skottie.h - 核心 API

这是 Skottie 的主入口头文件。定义了以下核心类:

**`Animation`** - 动画实例类
- `Make(data, length)` / `Make(stream)` / `MakeFromFile(path)`: 静态工厂方法(简单创建)
- `seekFrame(t)`: 根据帧索引跳转(如 0.0=第一帧, 1.0=第二帧, 0.5=两帧之间)
- `seekFrameTime(t)`: 根据时间(秒)跳转
- `seek(t)`: [已弃用] 归一化跳转 [0..1]
- `render(canvas, dst, flags)`: 将当前帧渲染到 SkCanvas
- `duration()`: 动画总时长(秒)
- `fps()`: 帧率
- `inPoint()` / `outPoint()`: 入点/出点(帧索引单位)
- `size()`: 动画画布尺寸
- `version()`: Lottie 版本字符串

**`Animation::Builder`** - 构建器类
- `setResourceProvider(rp)`: 设置外部资源加载器
- `setFontManager(fm)`: 设置字体管理器
- `setPropertyObserver(po)`: 设置属性观察回调
- `setLogger(logger)`: 设置日志接收器
- `setMarkerObserver(mo)`: 设置标记观察器
- `setPrecompInterceptor(pi)`: 设置预合成拦截器
- `setExpressionManager(em)`: 设置 AE 表达式管理器
- `setTextShapingFactory(sf)`: 设置文本排版工厂
- `make(stream)` / `make(data, length)` / `makeFromFile(path)`: 构建动画
- `getSlotManager()`: 获取插槽管理器句柄
- `getLayerInfo()`: 获取图层信息列表
- `getStats()`: 获取构建统计信息

**`Logger`** - 日志类
- `log(Level, message, json)`: 接收解析警告/错误

**`ExpressionManager`** - 表达式管理器
- `createNumberExpressionEvaluator(expr)`: 创建数值表达式求值器
- `createStringExpressionEvaluator(expr)`: 创建字符串表达式求值器
- `createArrayExpressionEvaluator(expr)`: 创建数组表达式求值器

**`MarkerObserver`** - 标记观察器
- `onMarker(name, t0, t1)`: 接收 AE 合成标记

**`Builder::Flags`**:
- `kDeferImageLoading`: 延迟图像加载(按需加载)
- `kPreferEmbeddedFonts`: 优先使用嵌入字体(字形路径)

### SkottieProperty.h - 属性系统

**`PropertyObserver`** - 属性观察器(核心扩展点)
- `onColorProperty(name, handle)`: 发现颜色属性
- `onOpacityProperty(name, handle)`: 发现不透明度属性
- `onTextProperty(name, handle)`: 发现文本属性
- `onTransformProperty(name, handle)`: 发现变换属性
- `onEnterNode(name, type)`: 进入节点
- `onLeavingNode(name, type)`: 离开节点

**属性句柄类型**:
- `ColorPropertyHandle`: 颜色操控 (SkColor)
- `OpacityPropertyHandle`: 不透明度操控 (float)
- `TextPropertyHandle`: 文本操控 (TextPropertyValue)
- `TransformPropertyHandle`: 变换操控 (TransformPropertyValue)

**`TextPropertyValue`** - 文本属性值:
- `fTypeface` / `fText` / `fTextSize` / `fHAlign` / `fVAlign`
- `fFillColor` / `fStrokeColor` / `fStrokeWidth`
- `fBox` / `fLineHeight` / `fResize` / `fLineBreak`
- `fDecorator`: 可选字形修饰器

**`GlyphDecorator`** - 文本字形修饰:
- `onDecorate(canvas, textInfo)`: 在文本图层之上绘制自定义装饰

### ExternalLayer.h - 外部图层

**`ExternalLayer`** - 外部渲染图层
- `render(canvas, t)`: 渲染外部内容(t 相对于图层入点的秒数)

**`PrecompInterceptor`** - 预合成拦截
- `onLoadPrecomp(id, name, size)`: 替换预合成图层为外部内容

### SlotManager.h - 插槽管理

**`SlotManager`** - 运行时插槽值管理器
- `setColorSlot(id, color)` / `getColorSlot(id)`: 颜色插槽
- `setImageSlot(id, asset)` / `getImageSlot(id)`: 图像插槽
- `setScalarSlot(id, value)` / `getScalarSlot(id)`: 标量插槽
- `setVec2Slot(id, v)` / `getVec2Slot(id)`: 二维向量插槽
- `setTextSlot(id, text)` / `getTextSlot(id)`: 文本插槽
- `getSlotInfo()`: 获取所有插槽 ID 信息

### TextShaper.h - 文本排版

**`Shaper`** - 文本排版器(实现 AE 文本语义)
- `Shape(text, desc, point, fontMgr, factory)`: 点文本排版
- `Shape(text, desc, box, fontMgr, factory)`: 框文本排版

**枚举类型**:
- `VAlign`: 垂直对齐 (Top/TopBaseline/HybridTop/HybridCenter/HybridBottom/VisualTop/VisualCenter/VisualBottom)
- `ResizePolicy`: 自适应策略 (None/ScaleToFit/DownscaleToFit)
- `LinebreakPolicy`: 换行策略 (Paragraph/Explicit)
- `Direction`: 文本方向 (LTR/RTL)
- `Capitalization`: 大写转换 (None/UpperCase)

## 依赖关系

```
Skottie.h
  ├── SkRefCnt.h, SkScalar.h, SkSize.h, SkString.h, SkTypes.h
  ├── skresources/SkResources.h  (ResourceProvider, ImageAsset)
  ├── ExternalLayer.h            (ExternalLayer, PrecompInterceptor)
  ├── SkottieProperty.h          (PropertyObserver, PropertyHandle)
  └── SlotManager.h              (SlotManager)

SkottieProperty.h
  ├── SkColor.h, SkMatrix.h, SkPaint.h, SkPoint.h, SkRect.h
  ├── SkTypeface.h, SkTextUtils.h
  ├── TextShaper.h               (Shaper 枚举类型)
  └── sksg/SkSGPaint.h           (Color), sksg/SkSGOpacityEffect.h

TextShaper.h
  ├── SkFont.h, SkPoint.h
  ├── SkTextUtils.h
  └── skunicode/SkUnicode.h
```

## 设计模式分析

- **惰性句柄 (LazyHandle)**: `PropertyObserver` 使用 `LazyHandle<T>` = `std::function<std::unique_ptr<T>()>`。只有在客户端确实需要操控某个属性时才创建句柄,避免不必要的对象分配。
- **类型擦除**: `PropertyHandle<ValueT, NodeT>` 模板对外隐藏了内部节点类型,提供统一的 `get()/set()` 接口。
- **值语义**: `TextPropertyValue` 和 `TransformPropertyValue` 使用值语义(结构体),支持比较运算符,方便变更检测。

## 相关文档与参考

- **skottie 主文档**: `docs/yuanlin/modules/skottie/README.md`
- **sksg 模块**: `modules/sksg/include/` - 场景图节点头文件
- **skresources 模块**: `modules/skresources/include/SkResources.h` - 资源加载
- **Lottie 编辑器**: [lottiefiles.com/editor](https://lottiefiles.com/) - 在线预览/编辑工具
