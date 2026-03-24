
---
title: "多仓库 Chromium 试运行机器人"
linkTitle: "Multiple repo Chromium trybots"

---


当一个拟议的 Skia 更改需要在 Chromium 或 Blink 中进行相应更改时，在本地创建 Chromium 和 Blink 的更改并使用拟议的 Skia 更改进行测试通常很有帮助。这经常发生在 Skia API 更改和影响 Blink 布局测试 (Layout Test) 的更改中。虽然在本地操作很简单，但这里解释了如何在 Chromium 试运行机器人 (Trybot) 上执行此操作。

仅 Skia 更改
-----------------
如果 Skia 补丁已经在 Gerrit 上，且没有相关的 Chromium 更改，那么只需运行 Chromium 试运行机器人即可。这将应用 Skia 补丁并运行机器人。

Skia 和 Chromium 同时更改
-------------------------
如果 Skia 补丁已经在 Gerrit 上，且有相关的 Chromium 更改，那么在 Chromium CL 中将以下内容添加到 \<chromium>/src/DEPS 的 'hooks' 数组中。

      {
        'name': 'fetch_custom_patch',
        'pattern': '.',
        'action': [ 'git', '-C', 'src/third_party/skia/',
                    'fetch', 'https://skia.googlesource.com/skia', 'refs/changes/13/10513/13',
        ],
      },
      {
        'name': 'apply_custom_patch',
        'pattern': '.',
        'action': ['git', '-C', 'src/third_party/skia/',
                   '-c', 'user.name=Custom Patch', '-c', 'user.email=custompatch@example.com',
                   'cherry-pick', 'FETCH_HEAD',
        ],
      },

将 'refs/changes/XX/YYYY/ZZ' 修改为适当的值（其中 YYYY 是数字变更编号，ZZ 是补丁集编号，XX 是数字变更编号的最后两位数字）。这可以在 Gerrit 的 'Download' 链接中看到。

如果这是针对 Skia 以外的项目，请更新检出目录和获取源。请注意，这可以多次使用以应用多个问题。

使用此方法的示例可以在 https://crrev.com/2786433004/#ps1 看到。

要在本地测试，运行 `gclient runhooks` 来更新 Skia 源代码。请注意，如果 `third_party/skia` 中的本地 Skia 补丁不是干净的（例如，您已经应用了某些补丁），那么 `gclient runhooks` 将无法成功运行。在这种情况下，请在 `gclient runhooks` 之前在 `third_party/skia` 中运行 `git reset --hard`。

任意更改
-----------------
如果补丁针对的文件无法使用上述方法，则仍然可以通过将以下内容添加到 \<chromium>/src/DEPS 的 'hooks' 数组中（紧在 'gyp' 钩子之前）来手动修补文件。

      {
        'name': 'apply_custom_patch',
        'pattern': '.',
        'action': ['python3',
                   '-c', 'from distutils.dir_util import copy_tree; copy_tree("src/patch/", "src/");'
        ],
      },

然后，将所有"代码树外"的文件复制到 \<chromium>/src/patch/ 中，使用与 Chromium 相同的目录结构。当运行 `gclient runhooks` 时，\<chromium>/src/patch/ 中的文件将被复制到 \<chromium>/src/ 中并覆盖相应文件。例如，如果更改 \<skia>/include/core/SkPath.h，请将修改后的 SkPath.h 的副本放在 \<chromium>/src/patch/third_party/skia/include/core/SkPath.h。

使用此方法的示例可以在 https://crrev.com/1866773002/#ps20001 看到。


测试补丁
-------------
在本地提交 \<chromium>/src/DEPS 或 \<chromium>/src/patch/ 更改后，可以按照通常的方式使用 `git cl upload`。请务必在问题描述中添加 `COMMIT=false` 以避免意外检入。
