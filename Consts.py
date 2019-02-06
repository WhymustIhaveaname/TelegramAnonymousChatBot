#!/usr/bin/python3
# -*- coding: UTF-8 -*-
GROUP_NAME="A Group name"
TOKEN="your bot's token"
GROUP_ID=-1 #group id,should be a negtive int
BUGMANAGER=1 #where bugreports will go to
NAMES=("Alice","Bob",) #You can add more
REFRESH_TIME=20 #the hour of daily refresh
TURNON_JOIN_GROUP_VERIFY=True #False to close join group verify.NOTE:new member joined chat via other methods will be kicked by bot
DSI_USER_FILE_NAME="./dsi_user" #dsi stands for disable successfully forward msg

M_HELP="""我是%s的bot,给我发消息我会匿名转发到%s中.一些常用的命令有:
/reportbug:开始向编程者报告bug
/quitreport:报告完bug退出
/whoami:返回当前匿名名称
/delmsg 或 /d:在对bot的私聊中回复要删除的消息这条命令删除消息
/dsi:关闭成功转发提示
/undsi:打开成功转发提示
/startpc:启动一个私聊"""%(GROUP_NAME,GROUP_NAME)
M_YouAreChatMem="您已是群成员,开始发消息吧!"
