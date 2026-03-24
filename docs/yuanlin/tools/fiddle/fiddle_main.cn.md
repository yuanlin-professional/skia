# fiddle_main - Fiddle 在线绘图工具主框架

> 源文件:
> - [tools/fiddle/fiddle_main.h](../../../tools/fiddle/fiddle_main.h)
> - [tools/fiddle/fiddle_main.cpp](../../../tools/fiddle/fiddle_main.cpp)

## 概述

fiddle_main 定义了 Skia Fiddle（在线代码片段运行器）的全局接口和环境。它声明了 Fiddle 脚本可访问的全局变量（画布、图像、字体管理器、动画参数）和绘图选项（DrawOptions），支持 GPU、光栅、PDF、SKP 等多种输出格式。该头文件故意使用全局变量来简化 Fiddle 代码编写。

## 架构位置

位于 `tools/fiddle/` 目录下，是 Skia Fiddle 在线编辑器的核心框架。连接用户提交的绘图代码与 Skia 渲染引擎。

## 主要类与结构体

### `DrawOptions`
绘图配置选项，控制输出格式和资源参数。
- `size` - 输出尺寸
- `raster/gpu/pdf/skp` - 输出格式开关
- `srgb/f16` - 色彩空间选项
- `fMipMapping` - 纹理 Mipmap 设置
- `fOffScreenWidth/Height` - 离屏渲染目标尺寸

### 全局变量
- `backEndTexture` / `backEndRenderTarget` / `backEndTextureRenderTarget` - GPU 后端资源
- `source` / `image` - 源图像
- `duration` / `frame` - 动画参数
- `fontMgr` - 字体管理器

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `GetDrawOptions()` | 获取绘图配置（由 Fiddle 脚本定义） |
| `draw(SkCanvas*)` | 用户绘图函数入口点 |
| `create_direct_context(...)` | 创建 GPU 上下文（有 EGL/Mesa/null 等实现） |

## 内部实现细节

- 头文件故意污染全局命名空间，应作为最后一个 include。
- F16 模式仅在 sRGB 色彩空间下有效。
- GPU 上下文创建有多种平台实现（EGL、Mesa、null fallback）。

## 依赖关系

- **Skia 核心**：SkCanvas、SkSurface、SkDocument、SkFontMgr、SkPictureRecorder
- **GPU**：GrDirectContext、GrGLInterface、GrBackendTexture

## 设计模式与设计决策

- **全局变量设计**：简化 Fiddle 代码编写，使用者无需理解复杂的上下文管理。
- **多后端支持**：通过 DrawOptions 的布尔开关选择输出格式。

## 性能考量

- Fiddle 执行环境为沙箱，性能不是首要考虑。

## 相关文件

- `tools/fiddle/fiddle_main.cpp` - Fiddle 主程序实现
- Fiddle 在线服务端
