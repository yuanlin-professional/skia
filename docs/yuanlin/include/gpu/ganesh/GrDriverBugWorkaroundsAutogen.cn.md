# GrDriverBugWorkaroundsAutogen

> 源文件: `include/gpu/ganesh/GrDriverBugWorkaroundsAutogen.h`

## 概述
这是一个自动生成的头文件,定义了 GPU 驱动程序缺陷的解决方案宏列表。该文件通过宏定义的方式为各种已知的 GPU 驱动程序缺陷提供统一的命名和管理接口,使 Skia 能够在运行时动态应对不同平台和硬件的兼容性问题。

## 架构位置
该文件位于 Ganesh GPU 后端的核心层,属于 GPU 驱动兼容性子系统。它由 `build_workaround_header.py` 脚本自动生成,不应手动编辑。这些 workaround 定义被 Ganesh 的各个渲染路径和资源管理模块使用,以确保在存在驱动程序缺陷的硬件上正确运行。

## 宏定义结构

### GPU_DRIVER_BUG_WORKAROUNDS 宏
这是一个宏列表生成器,通过传入 `GPU_OP` 宏参数来批量定义所有已知的驱动程序缺陷解决方案。

**设计模式**: X-Macro 模式,允许在单一位置定义所有 workaround,然后在不同上下文中重用这些定义。

**使用方式**:
```cpp
#define GPU_OP(TYPE, NAME) // 自定义处理逻辑
GPU_DRIVER_BUG_WORKAROUNDS(GPU_OP)
#undef GPU_OP
```

## 已知驱动程序缺陷列表

### ADD_AND_TRUE_TO_LOOP_CONDITION
- **缺陷描述**: 在循环条件中添加 `&& true`,解决某些 GPU 驱动的着色器编译器优化问题
- **影响范围**: 着色器编译

### DISABLE_BLEND_EQUATION_ADVANCED
- **缺陷描述**: 禁用高级混合方程式功能
- **影响范围**: 混合模式渲染,主要影响高级图形效果

### DISABLE_DISCARD_FRAMEBUFFER
- **缺陷描述**: 禁用帧缓冲丢弃操作
- **影响范围**: 帧缓冲管理,可能影响性能优化

### DISABLE_DUAL_SOURCE_BLENDING_SUPPORT
- **缺陷描述**: 禁用双源混合支持,解决某些驱动对片段着色器输出的处理问题
- **影响范围**: 高级混合功能

### DISABLE_TEXTURE_STORAGE
- **缺陷描述**: 禁用纹理存储功能,改用传统的纹理分配方式
- **影响范围**: 纹理内存管理

### DISALLOW_LARGE_INSTANCED_DRAW
- **缺陷描述**: 限制大规模实例化绘制的使用
- **影响范围**: 实例化渲染性能

### EMULATE_ABS_INT_FUNCTION
- **缺陷描述**: 模拟整数绝对值函数,解决 GLSL 内置函数缺陷
- **影响范围**: 着色器数学运算

### FLUSH_ON_FRAMEBUFFER_CHANGE
- **缺陷描述**: 在帧缓冲切换时强制刷新 GPU 命令
- **影响范围**: 渲染目标切换性能

### FORCE_UPDATE_SCISSOR_STATE_WHEN_BINDING_FBO0
- **缺陷描述**: 绑定默认帧缓冲时强制更新裁剪状态
- **影响范围**: 窗口系统渲染目标管理

### GL_CLEAR_BROKEN
- **缺陷描述**: GL 清除操作存在缺陷,需要替代实现
- **影响范围**: 帧缓冲清除操作

### MAX_FRAGMENT_UNIFORM_VECTORS_32
- **缺陷描述**: 将片段着色器 uniform 向量数量限制为 32
- **影响范围**: 着色器 uniform 资源限制

### MAX_MSAA_SAMPLE_COUNT_4
- **缺陷描述**: 将多重采样抗锯齿样本数限制为 4
- **影响范围**: MSAA 质量设置

### PACK_PARAMETERS_WORKAROUND_WITH_PACK_BUFFER
- **缺陷描述**: 使用 pack buffer 解决参数打包问题
- **影响范围**: 像素传输操作

### REMOVE_POW_WITH_CONSTANT_EXPONENT
- **缺陷描述**: 移除常量指数的幂运算,使用替代实现
- **影响范围**: 着色器数学优化

### REWRITE_DO_WHILE_LOOPS
- **缺陷描述**: 重写 do-while 循环为其他形式
- **影响范围**: 着色器控制流

### UNBIND_ATTACHMENTS_ON_BOUND_RENDER_FBO_DELETE
- **缺陷描述**: 删除绑定的渲染帧缓冲前解绑附件
- **影响范围**: 帧缓冲对象生命周期管理

### UNFOLD_SHORT_CIRCUIT_AS_TERNARY_OPERATION
- **缺陷描述**: 将短路逻辑运算展开为三元运算符
- **影响范围**: 着色器逻辑运算优化

## 设计模式与设计决策

### X-Macro 模式
使用 X-Macro 模式允许在单一位置维护所有 workaround 定义,确保一致性并简化添加新 workaround 的流程。通过传递不同的 `GPU_OP` 宏实现,可以生成:
- 枚举值
- 结构体成员
- 初始化列表
- 字符串名称映射

### 自动生成策略
文件由 Python 脚本生成,确保从权威数据源(可能是 Chromium 项目)同步最新的驱动程序缺陷信息,减少人工维护错误。

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| Chromium GPU 项目 | workaround 定义的权威来源 |

### 被依赖的模块
| 模块 | 用途 |
|------|------|
| GrDriverBugWorkarounds 类 | 使用这些宏定义成员变量和初始化逻辑 |
| GrContextOptions | 配置 workaround 启用/禁用 |
| GrCaps | 根据硬件能力决定启用哪些 workaround |
| 着色器编译器 | 根据 workaround 调整着色器生成策略 |

## 使用示例

典型的使用模式:
```cpp
// 定义 workaround 结构体
struct GrDriverBugWorkarounds {
    #define GPU_OP(TYPE, NAME) bool NAME = false;
    GPU_DRIVER_BUG_WORKAROUNDS(GPU_OP)
    #undef GPU_OP
};

// 生成字符串映射
const char* workaroundNames[] = {
    #define GPU_OP(TYPE, NAME) #NAME,
    GPU_DRIVER_BUG_WORKAROUNDS(GPU_OP)
    #undef GPU_OP
};
```

## 版本控制与同步

该文件包含版权声明表明来源于 Chromium 项目 (2018),使用 BSD 许可证。Skia 通过定期运行 `build_workaround_header.py` 脚本从上游同步最新的 workaround 定义,确保与 Chrome 浏览器使用相同的兼容性策略。

## 注意事项

1. **不要手动编辑**: 文件头部明确标注 "DO NOT EDIT!",所有修改应通过修改生成脚本或上游数据源实现
2. **大小写约定**: 使用大写字母加下划线的枚举常量风格(TYPE)和小写字母加下划线的标识符风格(NAME)
3. **向后兼容性**: 新增 workaround 应添加到列表末尾,避免破坏现有代码的枚举值顺序
