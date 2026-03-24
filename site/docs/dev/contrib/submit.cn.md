---
title: '如何提交补丁'
linkTitle: 'How to submit a patch'
---

## 配置 git

<!--?prettify lang=sh?-->

    git config --global user.name "Your Name"
    git config --global user.email you@example.com

## 进行更改

首先为您的更改创建一个分支 (Branch)：

<!--?prettify lang=sh?-->

    git config branch.autosetuprebase always
    git checkout -b my_feature origin/main

完成更改后，创建一个提交 (Commit)

<!--?prettify lang=sh?-->

    git add [file1] [file2] ...
    git commit

如果您的分支过期了，需要更新它：

<!--?prettify lang=sh?-->

    git pull
    python3 tools/git-sync-deps

## 添加单元测试

如果您愿意修改 Skia 代码库，最好同时添加一个测试。Skia 有一个简单的单元测试框架 (Unit Test Framework)，您可以向其中添加测试用例。

测试代码位于 'tests' 目录下。

详情请参阅[编写单元测试和渲染测试](/docs/dev/testing/tests)。

单元测试 (Unit Test) 是最佳选择，但如果您的更改涉及渲染且您无法想到自动验证结果的方法，请考虑编写 GM 测试。此外，如果您的更改在 GPU 代码中，您可能无法将其作为标准单元测试套件的一部分编写，但有一些 GPU 特定的测试路径可以扩展。

## 更新 BUILD.bazel 文件

如果您添加或删除了文件，需要更新这些文件所在目录中的 `BUILD.bazel` 文件。许多 `BUILD.bazel` 文件有一个文件列表，被分成两个使用 `split_srcs_and_hdrs` 宏的 [`filegroup`](https://bazel.build/reference/be/general#filegroup) 规则。您应该在这些文件列表中添加新文件名或删除旧文件名。

如果您的功能将被有条件地启用（例如像 GPU 后端或图像编解码器），您可能需要添加或修改 [`select`](https://bazel.build/reference/be/common-definitions#configurable-attributes) 语句来实现该目标。请参考现有规则的示例。

## 提交补丁

要使您的代码被接受到代码库中，您必须完成[个人贡献者许可协议](http://code.google.com/legal/individual-cla-v1.0.html)。您可以在线完成此操作，只需一分钟。如果您代表公司进行贡献，则必须填写[企业贡献者许可协议](http://code.google.com/legal/corporate-cla-v1.0.html)并按该页面所述方式发送。在您的 CL 中将您（或您的组织）的名称和联系信息添加到 AUTHORS 文件中。

现在您已经进行了更改并为其编写了测试，可以进行代码审查了！使用 depot tools 提交补丁并获得审查非常简单。

使用 `git-cl`，它随 [depot tools](http://sites.google.com/a/chromium.org/dev/developers/how-tos/install-depot-tools) 一起提供。如需帮助，请运行 `git cl help`。请注意，要使 `git cl` 正常工作，它需要在 <https://skia.googlesource.com/skia> 的克隆上运行。使用镜像的克隆（包括 Google 在 GitHub 上的镜像）可能会导致 `git cl` 使用问题。

### 寻找审查者

理想情况下，审查者应是熟悉您所修改代码区域的人。查看文件的 git blame 以了解还有谁编辑过它。如果不成功，另一个选择是点击 'Suggested Reviewers' 按钮来添加列出的 Skia 联系人之一。他们应该能够为您的更改添加适当的审查者。该按钮位于此处：
<img src="/docs/dev/contrib/SuggestedReviewers.png" style="display: inline-block; max-width: 75%" />

### 上传更改以供审查

Skia 使用 Gerrit 代码审查工具。Skia 的实例是 [skia-review](http://skia-review.googlesource.com)。使用 `git cl` 上传您的更改：

<!--?prettify lang=sh?-->

    git cl upload

您可能需要输入 Google 账户用户名和密码来向 Gerrit 进行身份验证。免费的 gmail 账户即可，或任何其他类型的 Google 账户。它不必与您使用 `git config --global user.email` 配置的电子邮件地址匹配，但可以匹配。

命令输出应包含一个 URL，类似于 ([https://skia-review.googlesource.com/c/4559/](https://skia-review.googlesource.com/c/4559/))，指示您的变更列表 (Changelist) 可以在哪里被审查。

### 提交试运行作业

Skia 的试运行机器人 (Trybot) 允许在代码合入仓库之前进行测试和验证。您需要有触发试运行作业的权限；如果需要权限，请联系一位提交者。将 CL 上传到 [Gerrit](https://skia-review.googlesource.com/) 后，您可以通过 Gerrit 界面或使用 `git cl try` 为 tasks.json 中列出的任何作业触发试运行作业，例如：

    git cl try -B skia.primary -b Some-Tryjob-Name

或者使用 bin/try，一个帮助选择试运行作业的 `git cl try` 小包装器。在 Skia 检出目录中：

    bin/try --list

您也可以使用正则表达式搜索：

    bin/try "Test.*Pixel.*Release"

有关测试的更多信息，请参阅[测试基础设施](/docs/dev/testing/automated_testing)。

### 请求审查

前往提供的 URL 或转到代码审查页面，选择 **Your** 下拉菜单并点击 **Changes**。选择您要提交审查的更改并点击 **Reply**。输入至少一位审查者的电子邮件地址。现在添加任何可选的备注，并通过点击 **Send** 发送您的更改以供审查。除非您将更改发送给审查者，否则没有人会知道要查看它。

_注意_：如果您在审查页面上看不到编辑命令，请点击右上角的 **Sign in**。_提示_：使用 `git-cl` 上传更改时，可以添加 -r reviewer@example.com --send-mail 在上传时直接发送电子邮件。

## 审查流程

如果您提交了一个巨大的补丁，或者在没有与相关人员讨论的情况下做了大量工作，可能很难说服任何人来审查它！

代码审查是工程流程的重要组成部分。审查者几乎总是会有建议或风格修正，重要的是不要将这些建议视为个人攻击或对您能力或想法的评价。这是一个我们共同努力以确保提交最高质量代码的过程！

您可能会收到审查者的电子邮件回复及评论。修复这些问题并通过再次上传来更新问题中的补丁集。上传将解释它正在更新当前的 CL 并要求您提供解释更改的消息。请确保在请求审查更新之前回复所有评论。

如果您需要更新已上传 CL 上的代码，只需编辑代码，在本地再次提交，然后再次运行 git cl upload，例如：

    echo "GOATS" > whitespace.txt
    git add whitespace.txt
    git commit -m 'add GOATS fix to whitespace.txt'
    git cl upload

准备好进行另一次审查时，再次使用 **Reply** 发送另一个通知（告诉审查者您对他们的每条评论做了什么处理会很有帮助）。当审查者对您的补丁满意时，他们将通过将 Code-Review 标签设置为 "+1" 来批准您的更改。

_注意_：在审查过程中，您和审查者都应使用代码审查界面进行交流，并发送备注。

一旦您的更改获得批准，您可以点击代码审查页面上的 "Submit to CQ" 按钮，它将代表您提交。

提交合入后，您应该删除包含更改的分支：

    git checkout -q origin/main
    git branch -D my_feature

## 最终测试

Skia 的主要下游用户是 Chromium，Skia 渲染输出的任何更改都可能导致 Chromium 出问题。如果您的更改以任何方式改变了渲染，您应该测试并缓解这种影响。您也许能找到一位 Skia 团队成员来帮助您，但每位贡献者都有责任避免破坏 Chrome。

### 评估对 Chromium 的影响

请记住，Skia 每天都会被滚动合入 (Roll) 到 Blink 和 Chromium 中。运行本地测试并观察金丝雀机器人 (Canary Bot) 的结果以确保没有影响。如果您提交的更改会影响布局测试 (Layout Test)，请遵循以下指南和/或与友好的 Skia-Blink 工程师合作来评估、重新基线化 (Rebaseline) 和提交您的更改。

资源：

[如何提交会改变 Blink 布局测试结果的 Skia 更改](/docs/dev/chrome/blink/)

如果您正在更改 Skia API，可能需要在 Chromium 中进行相应的更改。如果需要，请遵循以下说明：[提交需要 Chrome 更改的 Skia 更改](/docs/dev/chrome/changes/)

## 检入您的更改

### 非 Skia 提交者

如果您已经有提交者权限，可以按照以下说明将更改直接提交到 Skia 仓库。

如果您没有 https://skia.googlesource.com/skia.git 的提交者权限......首先，感谢您提交补丁！我们非常感谢这些贡献。在获得提交者的批准后，您将能够点击 "Submit to CQ" 按钮并通过提交队列 (Commit Queue) 提交您的补丁。

在特殊情况下，Skia 提交者可能会通过上传一个包含您补丁的新代码审查（可能会根据他们的判断进行一些小调整）来协助您提交更改。如果是这样，您可以将您的更改标记为 "Abandoned"，并更新一个指向新代码审查的链接。

### Skia 提交者

- 关于如何应用外部提供的补丁的技巧在[这里](../patch)
- 在提交外部贡献的补丁时，请在提交消息中注明原始贡献者的身份（并提供原始代码审查的链接）

  `git-cl` 将会把您的所有提交压缩成一个，使用您上传更改时使用的描述。

  ```
  git cl land
  ```

  或者

  ```
  git cl land -c 'Contributor Name <email@example.com>'
  ```
