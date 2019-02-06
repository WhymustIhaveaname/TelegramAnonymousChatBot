#!/usr/bin/python3
# -*- coding: UTF-8 -*-
#
# 用于实现群组的认证加群,匿名发送消息和群组成员之间匿名私信的通用机器人
# 在Consts.py中修改相应设置,填写TOKEN,GROUP_ID,BUGMANAGER等信息后即可使用
# 如果想修改bot的回复,请直接编辑源代码(把这些回复的字符串放在Consts里会降低程序可读性)
# A general bot used for group-joining-verfication and anonymous chating both in chat and between group members
# It is easy to use.You just need to modify settings and fill important information such as TOKEN,GROUP_ID,BUGMANAGER in Consts.py
# If you want to change bot replys,you have to edit this file directly because putting replys in Consts.py will make the codes hard to read
#
# 这个文件实现了入群验证功能
# This file have realised the function of joining group chat verification
#
# 本代码遵循MIT协议
# This program is dedicated to the public domain under the MIT license.
from Consts import *
if TURNON_JOIN_GROUP_VERIFY:
    from Captcha import *
from telegram import KeyboardButton,ReplyKeyboardMarkup
from telegram.ext import Updater,CommandHandler,MessageHandler,Filters
import logging,traceback

logging.basicConfig(format='[%(asctime)s][%(name)s][%(levelname)s]%(message)s',level=logging.INFO)
logger=logging.getLogger(__name__)

S_START,S_GOTCAPTCHA,S_BAN,S_WFJ=range(4)

class myUpdater(Updater):
    def start_polling(self,poll_interval=0.0, timeout=10, clean=False, bootstrap_retries=-1, read_latency=2.0, allowed_updates=None):
        Updater.start_polling(self,poll_interval,timeout,clean,bootstrap_retries,read_latency,allowed_updates)
        self.bot.send_message(GROUP_ID,"我上线啦!") #(I am online!)
    def stop(self):
        self.bot.send_message(GROUP_ID,"我去睡会儿") #(I am offline)
        Updater.stop(self)

class ChatBot_JoinVerify():
    def __init__(self,token,group_id,bugmanager):
        #
        self.updater=myUpdater(token)
        self.bot=self.updater.bot
        self.dp=self.updater.dispatcher
        self.job_queue=self.dp.job_queue
        #
        self.group_id=group_id
        self.bugmanager=bugmanager
        #for to_join
        self.user_status={}
        self.joined_users=set() # A user in joined_users will never get captcha
        #for joining
        self.lock=False
        self.joining_user=None
        self.joining_msg=None
        #for joined
        self.can_talk_users=set()
        #just for insurance
        try:
            self.bot.export_chat_invite_link(self.group_id)
            self.log("export chat link in init")
        except Exception as e:
            self.log(format(e))
        logger.info("inited")
    def log(self,msg): #for debugging.Log will be closed when running
        logger.info(msg)   
    def getstrname(user):
        return "%s(%s:%s)"%(user.name,user.full_name,user.id)
    def chatMemStatus(self,userid):
        if userid in self.joined_users:
            return 1
        status=self.bot.get_chat_member(self.group_id,userid).status
        if status in ("creator","administrator","member","restricted"):
            self.joined_users.add(userid)
            return 1
        elif status in ("left","kicked"):
            return 0
        else:
            return -1
    def turnon_joinverify(self):
        self.dp.add_handler(CommandHandler("start",self.start))
        self.dp.add_handler(CommandHandler("restart",self.start))
        self.dp.add_handler(CommandHandler("继续",self.sendCaptcha))
        self.dp.add_handler(CommandHandler("退出",self.sendByebye))
        self.dp.add_handler(CommandHandler("getlink",self.getlink,pass_job_queue=True))
        #new chatmem and left chat mem
        self.dp.add_handler(MessageHandler(Filters.status_update.new_chat_members,self.newmember))
        self.dp.add_handler(MessageHandler(Filters.status_update.left_chat_member,self.leftmember))
    #below is funcs for new-mem-joining
    def start(self,bot,update):
        userid=update.message.from_user.id
        #if user has in group
        if self.chatMemStatus(userid)>0:
            self.bot.send_message(userid,M_YouAreChatMem)
            return 1
        #if user is banning
        if userid in self.user_status:
            if self.user_status[update.message.from_user.id]==S_BAN:
                update.message.reply_text("我是不会理你的") #(I will not reply you)
                return 2
        #if everything is ok
        keyboard=[[KeyboardButton("/继续"), #(/continue)
                   KeyboardButton("/退出")]] #(/quit)
        reply_markup=ReplyKeyboardMarkup(keyboard,one_time_keyboard=True,resize_keyboard=True)
        update.message.reply_text("早上好!加我可以进入%s."%(GROUP_NAME),reply_markup=reply_markup) #(add me to join xxx chat)   
        self.user_status[update.message.from_user.id]=S_START
        return 0
    def sendCaptcha(self,bot,update):
        userid=update.message.from_user.id
        if self.chatMemStatus(userid)>0:
            self.bot.send_message(userid,M_YouAreChatMem)
            return 1
        if (userid in self.user_status) and self.user_status[userid]==S_START:
            captcha=Captcha.genCaptcha()
            update.message.reply_text(captcha["q"],reply_markup=captcha["markup"])
            self.user_status[userid]=S_GOTCAPTCHA
            return 0
        elif (userid in self.user_status) and self.user_status[userid]==S_GOTCAPTCHA:
            update.message.reply_text("您已经获得过验证问题了!请乖乖回答问题") #(It seems that you have got the captcha)
        else:
            update.message.reply_text("您的操作似乎不在控制流中,如果您想加群,请从 /start 开始,如果您遇到了问题,请用 /reportbug 报告,祝您身体健康,生活愉快!") #(It seems that your operation has been out of control flow,please start from /start)
            return 2
    def sendByebye(self,bot,update):
        userid=update.message.from_user.id
        if self.chatMemStatus(userid)>0:
            self.bot.send_message(userid,M_YouAreChatMem)
            return 1
        if (userid in self.user_status) and self.user_status[userid]==S_START:
            update.message.reply_text("再见.很高兴认识您,祝您身体健康,生活愉快!") #(Bye!)
            try:
                self.user_status.__delitem__(userid)
            except:
                self.log(traceback.format_exc())
            return 0
        else:
            update.message.reply_text("您的操作似乎不在控制流中,如果您遇到了问题,请用 /reportbug 报告.") 
                                      #(It seems that your operation has been out of control flow)
            return 2
    def joingroup(self,userid):
        if self.lock:
            self.log("%s want to join group but lock is true"%(userid))
            tempmsg="非常抱歉,有人正在加群,请等大约30s后回复 /getlink 获取邀请链接."
            self.bot.sendMessage(userid,tempmsg)
            self.user_status[userid]=S_WFJ
            return
        else:
            self.lock=True
            self.log("%s is joining the group and locked the lock"%(userid))
            self.joining_user=userid           
            tempmsg="请在一分钟内通过 %s 入群"%(self.bot.export_chat_invite_link(self.group_id)) 
            self.log("export chat link")
            self.joining_msg=self.bot.sendMessage(userid,tempmsg,disable_web_page_preview=True)
            self.job_queue.run_once(self.abortlink,60,context=userid) #即便这里执行失败abortlink也会释放锁,不会导致严重问题                 
            self.user_status.pop(userid,"NonExist") #一个人在上一次启动时获得了验证问题,重启后回答会导致元素不存在                   
    def newmember(self,bot,update):
        for mem in update.message.new_chat_members:
            if self.joining_user==mem.id:
                self.joined_users.add(mem.id)
                self.can_talk_users.add(mem.id)
            else: #if illigal user joined group
                #update invite link immediately
                if not self.bot.kick_chat_member(self.group_id,mem.id):
                    self.bot.send_message(self.bugmanager,"kick %s failed!"%(ChatBot.getstrname(mem)))
                self.bot.send_message(self.joining_user,"你被检测到将入群链接复制给他人")
                self.bot.send_message(self.bugmanager,"%s 将入群链接复制给了他人"%(self.joining_user))
            try:
                self.bot.export_chat_invite_link(self.group_id)
                self.log("export chat link in newmember")
            except:
                self.log(traceback.format_exc())
            self.joining_msg.edit_text("链接已失效")       
            self.joining_user=None
            self.joinging_msg=None
            self.lock=False
            self.log("%s joined the group and lock is released"%(mem.id))
    def leftmember(self,bot,update):
        self.joined_users.discard(update.message.left_chat_member.id)
        self.can_talk_users.discard(update.message.left_chat_member.id)
    def unban(self,bot,job):
        self.user_status.pop(job.context,"NonExist")
    def abortlink(self,bot,job):
        if self.joining_user==job.context:
            # MUST try-catch the two sentence below,or will cause death-lock when failed 
            try:
                self.bot.export_chat_invite_link(self.group_id)
                self.log("export chat link because timeout")
            except Exception as e:
                self.log(traceback.format_exc())
            try:
                self.joining_msg.edit_text("链接已失效")
            except Exception as e:
                self.log(traceback.format_exc())
            self.joining_user=None
            self.joining_msg=None
            self.lock=False
            self.log("lock released because time out")
    def getlink(self,bot,update,job_queue):
        userid=update.message.from_user.id
        if self.chatMemStatus(userid)>0:
            self.bot.send_message(userid,M_YouAreChatMem)
            return
        if (userid in self.user_status) and self.user_status[userid]==S_WFJ:
            self.joingroup(userid)
        else:
            update.message.reply_text("抱歉您需要通过验证才能获得链接")


