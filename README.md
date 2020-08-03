# PkuPhyChatBot
一款用于实现电报匿名群组的机器人, 在 Consts.py 中补全 GROUP_ID, BUGMANAGER 和 TOKEN 等关键消息后, 再在 Captcha.py 中填写验证问题库后即可用于您自己的匿名群组.

Features:
---------
    * 支持验证加群, 回答问题才能加群, 对回答问题后将链接转给别人, 重复加群, 从其他渠道获得链接加群等情况进行了仔细考虑, 确保加群的安全性. 如果要关闭此功能请直接修改源码.
    * 发送给 bot 的消息 bot 会匿名转发至大群中, 所谓匿名转发是指给每个人随机分配一个名字之后用此名字转发. 名字库可在 Consts.py 中编辑, 发言人数过多时程序会自动用多个名字组合出不重的名字. 匿名名称每天会清空, 清空时间可在 Consts.py 中设置.
    * 支持由 bot 转发的私聊, 使用 startpc 功能开启一次私聊, 对方同意后双方即可实现由 bot 中继的匿名聊天, 双方只知道对方在群里的代号而不知到对方是谁, 此种聊天有效性一天, 会随着匿名名称的清空而清空.
    * 友好的 reportbug 界面, 可以转发文字图片语音, 方便 bug 报告, 之后管理员只要回复 bot 转发的 bug 报告即可进行回复.
    * 轻量级的代码, 用了最少的库, 方便大家使用
    * 实现了 printuserid, printchatid 分别打印 userid 和 chatid 方便填写 Consts.py. 实现了 ping 来测试 bot 是否活着, 实现了 refresh 来由管理员手动重置匿名列表.
    
Donation:
---------
    * btc:3P4qND9E4pu4T8JnXNXUUPEszWDMqN1C5W
    * xmr:43hQcAFbKtNRiH8ACAFwoNURardECFhpGUxKLKNzB7hRCttk7wXWrPZ5fxYgRCM6uZjGPUn9S6qEoWk4qUVdg8krHRuXwwo
