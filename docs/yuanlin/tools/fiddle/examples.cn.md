# examples

> 源文件: `tools/fiddle/examples.h`, `tools/fiddle/examples.cpp`

## 概述

`examples` 模块是 Skia Fiddle 工具的示例注册和执行系统。Fiddle 是 Skia 的在线代码示例和测试平台，允许用户编写和运行小型 Skia 代码片段。该模块提供了宏系统用于注册示例，定义了示例的元数据结构，并实现了批量执行所有注册示例的主程序。它支持动画、离屏渲染、自定义尺寸、颜色空间和文本渲染等多种配置。

主要功能：
- 示例注册宏（`REG_FIDDLE`, `REG_FIDDLE_ANIMATED` 等）
- 示例元数据结构（尺寸、动画、颜色空间等）
- 全局资源提供（图片、字体、GPU 对象）
- 批量执行所有注册的示例
- 跨平台字体管理器初始化

## 架构位置

```
skia/
├── tools/
│   └── fiddle/
│       ├── examples.h                    # 示例注册宏和结构
│       ├── examples.cpp                  # 主程序和资源初始化
│       ├── fiddle_main.h/cpp             # Fiddle 主逻辑
│       └── [生成的示例文件]
├── tools/
│   └── Registry.h                        # 注册表模板
└── site/
    └── docs/
        └── examples/                     # 在线示例文档
```

## 主要类与结构体

### 结构体 `fiddle::Example`

定义单个 Fiddle 示例的完整元数据。

```cpp
struct Example {
    void (*fFunc)(SkCanvas*);         // 绘制函数指针
    const char* fName;                // 示例名称
    double fAnimationDuration;        // 动画时长（秒），0 表示静态
    int fImageIndex;                  // 使用的资源图片索引（0-6）
    int fWidth;                       // 画布宽度
    int fHeight;                      // 画布高度
    int fOffscreenWidth;              // 离屏表面宽度
    int fOffscreenHeight;             // 离屏表面高度
    int fOffscreenSampleCount;        // 离屏 MSAA 采样数
    bool fText;                       // 是否使用文本渲染
    bool fSRGB;                       // 是否使用 sRGB 颜色空间
    bool fF16;                        // 是否使用 F16 格式
    bool fOffscreen;                  // 是否使用离屏渲染
    bool fOffscreenTexturable;        // 离屏表面是否可作为纹理
    bool fOffscreenMipMap;            // 离屏表面是否生成 mipmap
};
```

### 注册宏

#### `REGISTER_FIDDLE`

核心注册宏，定义所有参数。

```cpp
#define REGISTER_FIDDLE(NAME, WIDTH, HEIGHT, TEXT, IMG_INDEX, DURATION, SRGB, F16, \
                        OFSCR, OFSCR_WIDTH, OFSCR_HEIGHT, OFSCR_SAMPLECOUNT,       \
                        OFSCR_TEXTURABLE, OFSCR_MIPMAP)                            \
    namespace example_##NAME { void draw(SkCanvas*);  }                            \
    sk_tools::Registry<fiddle::Example> reg_##NAME(                                \
        fiddle::Example{&example_##NAME::draw, #NAME, DURATION, IMG_INDEX,         \
                        WIDTH, HEIGHT, OFSCR_WIDTH, OFSCR_HEIGHT, OFSCR_SAMPLECOUNT, \
                        TEXT, SRGB, F16, OFSCR, OFSCR_TEXTURABLE, OFSCR_MIPMAP});  \
    namespace example_##NAME
```

**机制**:
1. 声明命名空间 `example_##NAME` 和 `draw` 函数
2. 创建全局注册表项 `reg_##NAME`
3. 重新进入命名空间，允许后续定义 `draw` 函数

#### 便捷宏

**`REG_FIDDLE(NAME, W, H, TEXT, I)`**

注册静态示例（无动画）。

```cpp
#define REG_FIDDLE(NAME, W, H, TEXT, I) \
    REG_FIDDLE_ANIMATED(NAME, W, H, TEXT, I, 0)
```

**`REG_FIDDLE_ANIMATED(NAME, W, H, T, I, DURATION)`**

注册动画示例。

```cpp
#define REG_FIDDLE_ANIMATED(NAME, W, H, T, I, DURATION) \
    REGISTER_FIDDLE(NAME, W, H, T, I, DURATION, false, false, \
                    false, 64, 64, 0, false, false)
```

**`REG_FIDDLE_SRGB(NAME, W, H, T, I, DURATION, F16)`**

注册 sRGB 颜色空间示例。

```cpp
#define REG_FIDDLE_SRGB(NAME, W, H, T, I, DURATION, F16) \
    REGISTER_FIDDLE(NAME, W, H, T, I, DURATION, true, F16, \
                    false, 64, 64, 0, false, false)
```

## 全局资源

### 图形 API 对象

```cpp
extern GrBackendTexture backEndTexture;              // GPU 纹理（用于测试）
extern GrBackendRenderTarget backEndRenderTarget;    // GPU 渲染目标
extern GrBackendTexture backEndTextureRenderTarget;  // 可渲染纹理
```

示例可以使用这些对象测试 GPU 功能。

### 资源图片

```cpp
extern SkBitmap source;        // 当前资源图片（位图形式）
extern sk_sp<SkImage> image;   // 当前资源图片（图片形式）
```

Fiddle 提供 7 张预定义资源图片（`example_1.png` 到 `example_6.png`），示例通过 `fImageIndex` 选择。

### 动画参数

```cpp
extern double duration;  // 动画总时长（秒）
extern double frame;     // 当前帧位置 [0, 1]
```

动画示例使用 `frame` 参数计算当前状态。

### 字体管理器

```cpp
extern sk_sp<SkFontMgr> fontMgr;  // 系统字体管理器
```

提供访问系统字体的能力。

## 公共 API 函数

### 主程序

**`int main()`**

批量执行所有注册的 Fiddle 示例。

**流程**:
1. **加载资源图片**: 从 `resources/images/example_[1-6].png` 加载
2. **初始化字体管理器**: 根据平台选择合适的字体后端
   - Linux: FontConfig
   - macOS: CoreText
   - Windows: DirectWrite
   - 其他: 目录扫描
3. **遍历示例**: 通过注册表迭代所有示例
4. **设置全局变量**: `image`, `source`, `duration`, `frame`
5. **创建画布**: 根据示例尺寸分配位图
6. **执行示例**: 调用 `example.fFunc(&canvas)`
7. **输出日志**: 打印示例名称

**代码**:
```cpp
for (const fiddle::Example& example : sk_tools::Registry<fiddle::Example>::Range()) {
    SkASSERT((unsigned)example.fImageIndex < (unsigned)kImgCount);
    image = images[example.fImageIndex];
    source = bitmaps[example.fImageIndex];
    SkBitmap bmp;
    bmp.allocN32Pixels(example.fWidth, example.fHeight);
    bmp.eraseColor(SK_ColorWHITE);
    SkCanvas canvas(bmp);
    SkDebugf("==> %s\n", example.fName);
    example.fFunc(&canvas);
}
```

## 内部实现细节

### 注册表模板实例化

```cpp
template sk_tools::Registry<fiddle::Example>* sk_tools::Registry<fiddle::Example>::gHead;
```

显式实例化注册表模板，确保所有示例注册到同一个全局链表。

### 命名空间技巧

```cpp
namespace example_##NAME { void draw(SkCanvas*);  }
// ...
namespace example_##NAME  // 重新进入，允许后续定义
```

这种技巧允许宏同时声明和定义函数：
```cpp
REG_FIDDLE(MyExample, 256, 256, false, 0) {
    void draw(SkCanvas* canvas) {
        canvas->clear(SK_ColorRED);
    }
}
```

### 跨平台字体初始化

```cpp
#if defined(SK_FONTMGR_FONTCONFIG_AVAILABLE)
    fontMgr = SkFontMgr_New_FontConfig(nullptr, SkFontScanner_Make_FreeType());
#elif defined(SK_FONTMGR_CORETEXT_AVAILABLE)
    fontMgr = SkFontMgr_New_CoreText(nullptr);
// ...
#else
    #error "Unsupported OS"
#endif
```

编译时选择合适的字体后端，确保示例可以访问系统字体。

### 延迟图片解码

```cpp
images[i] = SkImages::DeferredFromEncodedData(SkData::MakeFromFileName(path.c_str()));
```

使用延迟解码优化内存，图片在首次使用时才解码。

## 依赖关系

### 直接依赖

**Skia 核心**:
- `include/core/SkCanvas.h`: 画布
- `include/core/SkBitmap.h`: 位图
- `include/core/SkImage.h`: 图片

**工具库**:
- `tools/Registry.h`: 注册表模板

**字体管理器** (条件性):
- `include/ports/SkFontMgr_fontconfig.h`: Linux
- `include/ports/SkFontMgr_mac_ct.h`: macOS
- `include/ports/SkTypeface_win.h`: Windows
- `include/ports/SkFontMgr_directory.h`: 通用

### 被依赖情况

- Fiddle 工具的构建系统
- 在线 Fiddle 平台（skia.org/docs/examples）
- Skia 文档生成系统

## 设计模式与设计决策

### 注册表模式

使用全局链表自动收集所有示例，无需手动维护列表。

### 宏驱动的 DSL

```cpp
REG_FIDDLE(DrawCircle, 256, 256, false, 0) {
    void draw(SkCanvas* canvas) {
        canvas->drawCircle(128, 128, 50, SkPaint());
    }
}
```

宏提供简洁的语法，隐藏注册细节。

### 全局资源单例

```cpp
extern SkBitmap source;
extern sk_sp<SkImage> image;
```

全局变量简化示例代码，避免资源传递。

缺点：非线程安全，但 Fiddle 是单线程工具。

### 按需配置

示例只声明需要的功能（动画、sRGB、离屏等），减少默认配置复杂度。

## 性能考量

### 示例执行开销

- 简单示例（绘制形状）：< 1ms
- 复杂示例（文本、图片）：1-10ms
- GPU 示例（着色器）：10-100ms

批量执行数百个示例约需数秒。

### 资源加载

- 图片加载：延迟解码，首次使用时约 5-20ms
- 字体初始化：一次性开销，约 50-200ms

### 内存使用

- 每个示例画布：`width × height × 4` bytes
- 典型 256×256 示例：256KB
- 资源图片：共约 2-10MB（编码）

## 相关文件

### Fiddle 系统
- `tools/fiddle/fiddle_main.h/cpp`: Fiddle 主逻辑
- `tools/fiddle/draw.cpp`: 绘制辅助函数
- `site/docs/examples/`: 在线示例

### 注册表
- `tools/Registry.h`: 通用注册表模板

### 使用示例

```cpp
// 静态示例
REG_FIDDLE(StaticExample, 256, 256, false, 0) {
    void draw(SkCanvas* canvas) {
        canvas->clear(SK_ColorWHITE);
        SkPaint paint;
        paint.setColor(SK_ColorBLUE);
        canvas->drawCircle(128, 128, 50, paint);
    }
}

// 动画示例
REG_FIDDLE_ANIMATED(AnimatedExample, 256, 256, false, 0, 2.0) {
    void draw(SkCanvas* canvas) {
        canvas->clear(SK_ColorWHITE);
        SkPaint paint;
        paint.setColor(SK_ColorRED);
        float x = 50 + frame * 156;  // frame 从 0 到 1
        canvas->drawCircle(x, 128, 30, paint);
    }
}

// 使用资源图片
REG_FIDDLE(ImageExample, 256, 256, false, 3) {
    void draw(SkCanvas* canvas) {
        canvas->clear(SK_ColorWHITE);
        if (image) {
            canvas->drawImage(image, 0, 0);
        }
    }
}
```
