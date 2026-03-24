# project-config - Chrome-Infra 项目级配置

## 概述

`project-config/` 目录包含 Chrome 基础设施服务的项目级配置文件。这些配置定义了 Skia 项目在 LUCI 系统中的基本属性、构建桶和引用分支。

## 目录结构

```
project-config/
├── project.cfg          # 项目基本信息
├── cr-buildbucket.cfg   # Buildbucket 桶配置
├── refs.cfg             # 引用分支配置
└── README.md            # 原始说明文档
```

## 关键文件

### project.cfg
定义项目名称和访问权限：
- 项目名称："Skia, 2D graphics library"
- 访问权限：公开（`group:all`）

### cr-buildbucket.cfg
定义 cr-buildbucket 服务的桶配置。桶用于组织和管理构建任务，CQ（Commit Queue）使用这些桶来调度 Try Job。

定义的桶包括：
- `master.client.skia` - 主客户端桶
- `master.client.skia.android` - Android 客户端桶
- `master.client.skia.compile` - 编译桶
- `master.client.skia.fyi` - FYI（仅供参考）桶

每个桶定义了：
- READER - 读取权限（所有人）
- SCHEDULER - 调度权限（Try Job 访问组、CQ 服务账户）
- WRITER - 写入权限（Skia 主控服务账户）

### refs.cfg
定义 LUCI 系统监控的 Git 引用分支：
- `refs/heads/master` - 主分支，配置路径指向 `infra/branch-config`

## 依赖关系

- LUCI 配置系统（luci-config）
- cr-buildbucket 服务

## 相关文档与参考

- [LUCI Config 文档](https://luci-config.appspot.com/)
- [Buildbucket 配置模式](http://luci-config.appspot.com/schemas/projects:buildbucket.cfg)
