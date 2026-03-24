# FuzzPath

> 源文件: fuzz/FuzzPath.cpp

## 概述

FuzzPath 是一个用于模糊测试 `SkPath` 类序列化和反序列化功能的模块。该文件实现了 libFuzzer 入口点,通过向 `SkPath::readFromMemory` 方法输入随机字节序列,测试路径对象在处理任意数据时的稳定性和安全性。这是 Skia 质量保证体系中的关键组成部分,可以及早发现反序列化过程中的内存安全漏洞和崩溃问题。

## 架构位置

```
skia/
  ├── fuzz/                    # 模糊测试根目录
  │   ├── FuzzPath.cpp        # 本文件:路径反序列化测试
  │   ├── FuzzRRect.cpp       # 圆角矩形反序列化测试
  │   ├── FuzzPathMeasure.cpp # 路径测量测试
  │   ├── FuzzPathop.cpp      # 路径操作测试
  │   └── oss_fuzz/           # OSS-Fuzz 集成
  │       └── FuzzPathDeserialize.cpp
  ├── include/core/           # 核心 API
  │   └── SkPath.h            # 路径类声明
  └── src/core/               # 核心实现
      └── SkPath.cpp          # 路径实现
```

`SkPath` 是 Skia 中最核心的类之一,用于表示矢量图形路径,其反序列化功能的健壮性直接影响到图形渲染的安全性。

## 主要类与结构体

### 核心测试目标

**SkPath** (`include/core/SkPath.h`)
- **作用**: 表示由直线、曲线组成的矢量路径
- **关键方法**:
  - `readFromMemory(const void* buffer, size_t length)`: 从内存缓冲区反序列化路径数据
- **存储内容**:
  - 路径动词序列(moveTo、lineTo、quadTo、cubicTo、close)
  - 控制点坐标
  - 填充类型和卷绕规则
  - 边界框缓存

### libFuzzer 接口

```cpp
extern "C" int LLVMFuzzerTestOneInput(const uint8_t* buf, size_t size)
```
- **调用者**: libFuzzer 模糊测试引擎
- **调用频率**: 每秒数千至数万次
- **输入生成**: 覆盖率引导的智能变异

## 公共 API 函数

### LLVMFuzzerTestOneInput

```cpp
int LLVMFuzzerTestOneInput(const uint8_t* buf, size_t size)
```

**功能**: 模糊测试入口函数,测试路径反序列化的健壮性

**实现逻辑**:
```cpp
SkPath path;                         // 创建空路径对象
(void)path.readFromMemory(buf, size);  // 尝试从随机数据反序列化
return 0;                            // 返回表示测试完成
```

**测试目标**:
- 验证所有可能的输入都能被安全处理
- 检测缓冲区越界读取
- 发现整数溢出导致的内存问题
- 确保无效数据不会触发断言失败或崩溃

**典型测试场景**:
1. **有效路径数据**: 正常序列化后的路径
2. **截断数据**: 部分路径数据(测试边界检查)
3. **超大点数**: 声称包含大量点但实际数据不足
4. **无效动词**: 不在合法枚举范围内的动词值
5. **NaN/Inf 坐标**: 特殊浮点值导致的问题
6. **负数长度字段**: 可能导致整数溢出的长度值

## 内部实现细节

### 反序列化安全机制

`SkPath::readFromMemory` 需要实现以下安全检查:

1. **魔数验证**: 检查数据头部的魔数是否匹配
2. **版本检查**: 验证序列化版本是否受支持
3. **长度验证**: 确保声称的数据长度不超过实际缓冲区
4. **动词数量**: 检查动词数量是否合理(防止分配过大内存)
5. **点数量**: 验证点的数量与动词序列匹配
6. **浮点数有效性**: 确保坐标值是有效的浮点数

### 测试策略

该文件采用"无预期"测试策略:
- **不验证返回值**: 只要不崩溃即视为通过
- **不检查路径状态**: 反序列化失败后路径保持空是可接受的
- **依赖工具检测**: AddressSanitizer、UndefinedBehaviorSanitizer 等

### 典型漏洞模式

历史上在类似代码中发现的问题:
- **CVE-2016-XXXX**: 长度字段整数溢出导致堆溢出
- **缓冲区越界**: 未充分检查剩余字节数
- **资源耗尽**: 声称包含数百万个点的路径

## 依赖关系

### 直接依赖

- **SkPath** (`include/core/SkPath.h`)
  - 核心测试目标
  - 提供 `readFromMemory` 方法

### 编译时依赖

- **libFuzzer 运行时**
  - 提供 `LLVMFuzzerTestOneInput` 接口规范
  - 链接标志: `-fsanitize=fuzzer`

- **Sanitizer 库**
  - AddressSanitizer: 检测内存错误
  - UndefinedBehaviorSanitizer: 检测未定义行为
  - MemorySanitizer: 检测未初始化内存使用

### 测试基础设施

- **GN 构建系统**: 定义模糊测试目标
- **OSS-Fuzz**: 持续运行模糊测试的云平台
- **ClusterFuzz**: Google 内部模糊测试基础设施

## 设计模式与设计决策

### 设计模式

1. **崩溃检测模式**
   - 通过 Sanitizer 捕获内存错误
   - 不显式检查返回值或状态
   - 依赖工具报告异常

2. **简约测试模式**
   - 最小化测试代码(仅17行)
   - 避免测试代码本身引入 bug
   - 单一职责:只测试反序列化

### 设计决策

1. **返回值忽略**
   ```cpp
   (void)path.readFromMemory(buf, size);
   ```
   - 显式标记不关心返回值
   - 测试重点是"不崩溃",而非"正确解析"

2. **栈分配对象**
   ```cpp
   SkPath path;  // 栈上分配
   ```
   - 自动内存管理,简化测试
   - 避免内存泄漏

3. **无显式清理**
   - 析构函数自动释放资源
   - 无需手动管理内存

4. **注释引用文档**
   ```cpp
   // site/dev/testing/fuzz.md
   ```
   - 提供使用指南链接
   - 便于新开发者上手

## 性能考量

### 执行效率

1. **极快的测试速度**
   - 单次迭代通常在 1-10 微秒
   - 支持高吞吐量测试(每秒 10k-100k 次)

2. **内存占用**
   - `SkPath` 对象大小约 64 字节(栈)
   - 可能分配堆内存存储路径数据
   - 测试输入大小通常限制在 4KB 以内

3. **覆盖率引导**
   - libFuzzer 优先探索新代码路径
   - 自动保存触发新覆盖的测试用例(corpus)
   - 持续改进测试覆盖率

### 资源限制

典型的模糊测试配置:
- **最大输入大小**: 4KB(可配置)
- **超时时间**: 25秒/次
- **内存限制**: 2GB
- **CPU 使用**: 1个核心/测试进程

## 相关文件

### 核心实现
- `include/core/SkPath.h` - 路径类声明
- `src/core/SkPath.cpp` - 路径实现,包含序列化逻辑
- `src/core/SkPathRef.h` - 路径数据的引用计数存储

### 相关模糊测试
- `fuzz/oss_fuzz/FuzzPathDeserialize.cpp` - OSS-Fuzz 版本(更详细的测试)
- `fuzz/FuzzRRect.cpp` - 圆角矩形反序列化测试
- `fuzz/oss_fuzz/FuzzRegionDeserialize.cpp` - 区域反序列化测试
- `fuzz/oss_fuzz/FuzzImageFilterDeserialize.cpp` - 图像滤镜反序列化测试

### 路径相关测试
- `fuzz/FuzzPathMeasure.cpp` - 路径测量功能测试
- `fuzz/FuzzPathop.cpp` - 路径操作(布尔运算)测试
- `fuzz/FuzzParsePath.cpp` - SVG 路径解析测试

### 构建配置
- `gn/fuzz.gni` - 模糊测试 GN 构建规则
- `BUILD.gn` - 主构建文件中的模糊测试目标

### 文档
- `site/dev/testing/fuzz.md` - 模糊测试使用指南
- `docs/SkPath_Reference.md` - SkPath API 参考文档

### 持续集成
- `.oss-fuzz/Dockerfile` - OSS-Fuzz 构建环境
- `.oss-fuzz/project.yaml` - OSS-Fuzz 项目配置
