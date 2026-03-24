# FuzzRRect

> 源文件: fuzz/FuzzRRect.cpp

## 概述

FuzzRRect 是一个用于模糊测试 `SkRRect` 类序列化和反序列化功能的测试模块。该文件实现了一个简单的 libFuzzer 入口点,用于测试圆角矩形对象从内存中读取数据的健壮性和稳定性。通过向 `readFromMemory` 方法输入随机或畸形的字节序列,可以发现潜在的崩溃、内存泄漏或其他安全漏洞。

## 架构位置

FuzzRRect 位于 Skia 的模糊测试子系统中,属于自动化测试和质量保证的一部分:

```
skia/
  ├── fuzz/                    # 模糊测试根目录
  │   ├── FuzzRRect.cpp       # 本文件:圆角矩形反序列化测试
  │   ├── FuzzPath.cpp        # 路径反序列化测试
  │   ├── FuzzRegionOp.cpp    # 区域操作测试
  │   └── oss_fuzz/           # OSS-Fuzz 集成测试
  ├── include/core/           # 核心 API 定义
  │   └── SkRRect.h           # 圆角矩形类声明
  └── src/core/               # 核心实现
      └── SkRRect.cpp         # 圆角矩形实现
```

该文件通过模糊测试框架(libFuzzer)对 Skia 核心图形类进行压力测试,是保证库稳定性的重要组成部分。

## 主要类与结构体

### 外部依赖类

**SkRRect**
- **头文件**: `include/core/SkRRect.h`
- **作用**: 表示圆角矩形的几何图形类
- **关键方法**:
  - `readFromMemory(const void* buffer, size_t length)`: 从内存缓冲区反序列化圆角矩形数据

### libFuzzer 入口函数

```cpp
extern "C" int LLVMFuzzerTestOneInput(const uint8_t* buf, size_t size)
```

- **参数**:
  - `buf`: 模糊测试引擎生成的随机字节序列
  - `size`: 缓冲区大小
- **返回值**: 固定返回 0,表示测试完成
- **作用**: libFuzzer 框架的标准入口点,每次测试迭代会调用该函数

## 公共 API 函数

### LLVMFuzzerTestOneInput

```cpp
int LLVMFuzzerTestOneInput(const uint8_t* buf, size_t size)
```

**功能**: 模糊测试的核心入口函数

**实现逻辑**:
1. 创建一个未初始化的 `SkRRect` 对象
2. 调用 `readFromMemory` 方法尝试从随机数据中恢复圆角矩形
3. 忽略返回值,只关注是否触发崩溃或异常行为
4. 返回 0 表示测试迭代完成

**测试目标**:
- 验证 `SkRRect::readFromMemory` 能够安全处理任意输入数据
- 检测缓冲区溢出、空指针解引用等内存安全问题
- 确保无效数据不会导致程序崩溃

## 内部实现细节

### 反序列化测试机制

该测试采用"黑盒"模糊测试策略:
- **输入**: 完全随机的字节序列
- **预期行为**: 函数应优雅地处理所有输入,无论数据是否有效
- **测试覆盖**:
  - 正常格式的序列化数据
  - 截断的数据(size 小于预期)
  - 超大数据(size 远大于预期)
  - 无效的魔数或版本号
  - 畸形的浮点数(NaN、无穷大等)

### 关键设计决策

1. **返回值忽略**
   ```cpp
   (void)rrect.readFromMemory(buf, size);
   ```
   使用 `(void)` 显式忽略返回值,因为测试的目标是发现崩溃而非验证解析正确性

2. **对象栈分配**
   ```cpp
   SkRRect rrect;
   ```
   在栈上创建对象可以自动管理内存,简化测试逻辑

3. **无断言检查**
   测试不验证返回值或对象状态,依赖模糊测试工具的崩溃检测机制

## 依赖关系

### 直接依赖

- **SkRRect** (`include/core/SkRRect.h`)
  - 提供圆角矩形的序列化/反序列化接口
  - 是测试的唯一目标类

### 间接依赖

- **libFuzzer 运行时库**
  - 提供 `LLVMFuzzerTestOneInput` 接口规范
  - 提供覆盖率引导的模糊测试引擎
  - 生成测试输入并监控程序行为

### 构建系统依赖

- 需要在 GN 构建配置中启用模糊测试支持
- 依赖 LLVM 工具链中的 Clang 编译器
- 需要链接 libFuzzer 库(-fsanitize=fuzzer)

## 设计模式与设计决策

### 设计模式

1. **测试探针模式(Test Probe)**
   - 通过最小化接口探测系统行为
   - 专注于单一功能点的健壮性测试

2. **故障注入模式(Fault Injection)**
   - 注入随机/畸形数据以触发边缘情况
   - 验证错误处理路径的完整性

### 设计决策

1. **最小化测试代码**
   - 仅 17 行代码,避免引入额外复杂性
   - 降低测试代码本身引入 bug 的风险

2. **覆盖率驱动**
   - 依赖 libFuzzer 的覆盖率反馈机制自动生成有效输入
   - 无需人工编写测试用例

3. **持续集成友好**
   - 可集成到 OSS-Fuzz 等持续模糊测试平台
   - 自动发现和报告安全漏洞

## 性能考量

### 测试效率

1. **执行速度**
   - 单次测试迭代极快(微秒级)
   - 适合高频率的模糊测试(每秒数千次迭代)

2. **内存占用**
   - 使用栈分配的对象,无堆内存分配开销
   - `SkRRect` 对象大小固定(约 52 字节)

3. **覆盖率优化**
   - libFuzzer 会优先探索未覆盖的代码路径
   - 自动保存触发新覆盖的测试用例

### 资源限制

- **输入大小**: 通常限制在几 KB 以内
- **执行时间**: 每次迭代应在毫秒级完成
- **内存限制**: 通常限制为 2GB

## 相关文件

### 核心实现
- `include/core/SkRRect.h` - 圆角矩形类声明
- `src/core/SkRRect.cpp` - 圆角矩形实现,包含 `readFromMemory` 逻辑

### 相关模糊测试
- `fuzz/FuzzPath.cpp` - 路径对象反序列化测试
- `fuzz/oss_fuzz/FuzzPathDeserialize.cpp` - 路径反序列化的 OSS-Fuzz 版本
- `fuzz/oss_fuzz/FuzzRegionDeserialize.cpp` - 区域反序列化测试

### 构建配置
- `gn/fuzz.gni` - 模糊测试目标的 GN 构建规则
- `BUILD.gn` - 包含模糊测试目标的主构建文件

### 文档
- `site/dev/testing/fuzz.md` - 模糊测试使用指南
- `docs/SkRRect_Reference.md` - SkRRect API 参考文档

### 测试基础设施
- `fuzz/Fuzz.h` - 模糊测试工具类定义
- `fuzz/FuzzCommon.h` - 模糊测试通用辅助函数
