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
# 本文件是继承关系中最上层的文件
# This is the top level class in the inherit hierarchy
#
# 本代码遵循MIT协议
# This program is dedicated to the public domain under the MIT license.
#
from Consts import *
from ChatBot_ForwardMsg import *
from telegram import KeyboardButton,ReplyKeyboardMarkup,InlineKeyboardButton,InlineKeyboardMarkup
from telegram.ext import Updater,CommandHandler,MessageHandler,Filters,CallbackQueryHandler,ConversationHandler,DispatcherHandlerStop
from datetime import time as datetime_time
import logging,time,random,traceback,itertools,sys,os
# Enable logging
logging.basicConfig(format='[%(asctime)s][%(name)s][%(levelname)s]%(message)s',level=logging.INFO)
logger = logging.getLogger(__name__)

GETTINGNAME,GETTINGMSG,REPORTINGBUG=range(4,7)
        
class ChatBot(ChatBot_ForwardMsg):
    def __init__(self,token,group_id,bugmanager):
        ChatBot_ForwardMsg.__init__(self,token,group_id,bugmanager)
        #for private chat
        self.pc_addingfriend={}
        self.pc_dict={}
    def start_withoutjoinverify(self,bot,update):
        update.message.reply_text("早上好!加我并且入群后可以通过我匿名发送消息,或者与群成员匿名私聊.通过 /help 命令查看帮助.")
#below is general functions useful for all class
    def button(self,bot,update,job_queue):
        data=update.callback_query.data.split(":")
        msg=update.callback_query.message
        #if this is a captcha return
        if data[0]=="captcha":
            if data[1]=="r":
                msg.edit_text("恭喜您回答正确!")
                self.joingroup(msg.chat.id)
            else:
                msg.edit_text("你竟然答错了,等一分钟再 /restart 重试吧.")
                self.user_status[msg.chat.id]=S_BAN
                job_queue.run_once(self.unban,60,context=msg.chat.id)
            return
        elif data[0]=="privitechat":
            fromid=int(data[2])
            toid=msg.chat.id
            if data[1]=="agree":
                msg_text="<b>%s</b> 同意了您的聊天请求,回复这条消息的内容会被转发至 <b>%s</b>"%(self.get_alias(toid),self.get_alias(toid))
                temp_msg=self.bot.sendMessage(fromid,msg_text,parse_mode="HTML")
                msg_2_text="你同意了 <b>%s</b> 的聊天请求,回复这条消息的内容会被转发至 <b>%s</b>"%(self.get_alias(fromid),self.get_alias(fromid))
                temp_msg_2=self.bot.sendMessage(toid,msg_2_text,parse_mode="HTML")
                self.pc_dict["%s:%d"%(fromid,temp_msg.message_id)]=toid
                self.pc_dict["%s:%d"%(toid,temp_msg_2.message_id)]=fromid
                msg.edit_reply_markup()
            else:
                self.bot.sendMessage(data[2],"%s 拒绝了您的聊天请求"%(self.get_alias(msg.chat.id)))
                msg.edit_reply_markup() #reset markup
                msg.reply_text("你拒绝了 %s 的聊天请求"%(self.get_alias(fromid)))
#below is funcs for chatting between group members
    def getUseridFromAlias(self,alias):
        for k in self.alias:
            if self.alias[k]==alias:
                return k
        else:
            return None
    def startPC(self,bot,update,args):
        userid=update.message.from_user.id
        if len(args)==0:
            update.message.reply_text("请输入对方的alias,不要带方括号")
            return GETTINGNAME
        peerid=self.getUseridFromAlias(" ".join(args))
        if peerid==None:
            update.message.reply_text("似乎找不到这个人,请您再输入一次,不要带方括号,或者用 /cancelpc 退出")
            return GETTINGNAME
        else:
            self.pc_addingfriend[userid]=peerid
            update.message.reply_text("你想对对方说什么?")
            return GETTINGMSG
    def cancelPC(self,bot,update):
        userid=update.message.from_user.id
        self.pc_addingfriend.pop(userid,"NonExist")
        update.message.reply_text("您退出了一日匿名好友流程")
        return ConversationHandler.END
    def getPeerName(self,bot,update):
        userid=update.message.from_user.id
        peerid=self.getUseridFromAlias(update.message.text)
        if peerid==None:
            update.message.reply_text("似乎找不到这个人,请您重新输入或者用 /cancelpc 退出")
            return GETTINGNAME
        else:
            self.pc_addingfriend[userid]=peerid
            update.message.reply_text("你想对对方说什么?")
            return GETTINGMSG
    def getPCVerifyMsg(self,bot,update):
        userid=update.message.from_user.id
        peerid=self.pc_addingfriend[userid]
        try:
            keyboard=[[InlineKeyboardButton("同意",callback_data="privitechat:agree:%s"%(userid)),
                       InlineKeyboardButton("拒绝",callback_data="privitechat:deny:%s"%(userid))]]
            markup=InlineKeyboardMarkup(keyboard)
            self.bot.sendMessage(peerid,'%s 想与您私聊,他(她)说:"%s"'%(self.get_alias(userid),update.message.text),reply_markup=markup)
            update.message.reply_text("请求已发送,请等待对方同意")
        except:
            update.message.reply_text("抱歉,有错误发生,请重试")
            logger.warning(traceback.format_exc())
        self.cancelPC(bot,update)
        return ConversationHandler.END
    def pc_message(self,bot,update):
        msg1=update.message
        userid=msg1.from_user.id
        try:
            peerid=self.pc_dict["%s:%d"%(userid,msg1.reply_to_message.message_id)]
        except KeyError:
            msg1.reply_text("抱歉,发送私聊消息失败")
            return
        msg2_id=self.forward_message(msg1,userid,peerid)
        if msg2_id is None:
            msg1.reply_text("抱歉,您给 %s 的消息发送失败"%(self.get_alias(peerid)))
        else:
            tempmsg=msg1.reply_text("您给 %s 的消息已被成功转发"%(self.get_alias(peerid)),disable_notification=True)
            self.pc_dict["%s:%d"%(peerid,msg2_id)]=userid
            self.job_queue.run_once(self.delsucmsg,60,context=tempmsg) #del above msg after 60s
        raise DispatcherHandlerStop #pretent another handler from forwarding this msg to group chat
#below is miscellaneous funcs
    def reportbug(self,bot,update):
        update.message.reply_text("请在下面描述您遇到的问题,还可以发送图片和语音,可以发送多条消息,之后用 /quitreport 退出")
        self.bot.sendMessage(self.bugmanager,"%s 正在报告错误"%(ChatBot.getstrname(update.message.from_user)))
        return REPORTINGBUG
    def forwardbug(self,bot,update):
        msg1=update.message
        userid=msg1.from_user.id
        msg2_id=self.forward_message(msg1,userid,self.bugmanager)
        if msg2_id:
            self.pc_dict["%s:%d"%(self.bugmanager,msg2_id)]=userid
            msg1.reply_text("您刚才的消息已被提交至异常处理工")
        raise DispatcherHandlerStop
    def quitreport(self,bot,update):
        update.message.reply_text("感谢您的错误报告!我们会尽快作出改进")
        self.bot.sendMessage(self.bugmanager,"%s 的错误报告结束"%(ChatBot.getstrname(update.message.from_user)))
        return ConversationHandler.END
    def help(self,bot,update):
        update.message.reply_text(M_HELP)
    def refresh_kernel(self):
        self.joined_users.clear()
        self.can_talk_users.clear()
        self.alias.clear()
        self.msg_dict.clear()
        self.pc_addingfriend.clear()
        self.pc_dict.clear()
    def refresh(self,bot,update):
        userid=update.message.from_user.id
        status=self.bot.get_chat_member(self.group_id,userid).status
        if status in ("creator","administrator"):
            self.refresh_kernel()
            update.message.reply_text("successfully refreshed!")
            self.bot.send_message(self.group_id,"匿名列表已被管理员刷新")
        else:
            update.message.reply_text("您无权进行此操作!")
            self.bot.send_message(self.bugmanager,"%s tried to use refresh"%(ChatBot.getstrname(update.message.from_user)))
    def dailyrefresh(self,bot,job):
        try:
            self.refresh_kernel()
        except Exception as e:
            self.bot.send_message(self.bugmanager,"daily refresh failed:%s"%(format(e)))
        else:
            self.bot.send_message(self.group_id,"匿名列表已每日自动刷新")
    def printchatid(bot,update):
        update.message.reply_text(update.message.chat.id)
    def printuserid(bot,update):
        update.message.reply_text(update.message.from_user.id)
    def ping(bot,update):
        update.message.reply_text("I am alive!")
    def error(self,bot,update,error):
        print('Update "%s" caused error "%s"', update, error)
    def groupalert(self,bot,update):
        update.message.reply_text("请在对bot的私聊中使用本命令而不是在群里@机器人")
    def turnon_groupalert(self): #There always some freshbird @bot in group chat so I have to alert them
        self.dp.add_handler(CommandHandler('startpc',self.groupalert,filters=Filters.group))
        self.dp.add_handler(CommandHandler('whoami',self.groupalert,filters=Filters.group))
        self.dp.add_handler(CommandHandler('dsi',self.groupalert,filters=Filters.group))
        self.dp.add_handler(CommandHandler('undsi',self.groupalert,filters=Filters.group))
        self.dp.add_handler(CommandHandler('reportbug',self.groupalert,filters=Filters.group))
        self.dp.add_handler(CommandHandler('d',self.groupalert,filters=Filters.group))
        self.dp.add_handler(CommandHandler('delmsg',self.groupalert,filters=Filters.group))
    def main(self):
        if TURNON_JOIN_GROUP_VERIFY:
            self.turnon_joinverify()
        else:
            self.dp.add_handler(CommandHandler("start",self.start_withoutjoinverify))
                       
        self.dp.add_handler(CommandHandler("help",self.help,filters=(Filters.command & Filters.private)))
        self.dp.add_handler(CommandHandler("printchatid",ChatBot.printchatid))
        self.dp.add_handler(CommandHandler("printuserid",ChatBot.printuserid))
        self.dp.add_handler(CommandHandler("ping",ChatBot.ping,filters=(Filters.command & Filters.private)))
        self.dp.add_handler(CallbackQueryHandler(self.button,pass_job_queue=True))
        
        self.dp.add_handler(CommandHandler("refresh",self.refresh,filters=(Filters.command & Filters.private)))
        self.job_queue.run_daily(self.dailyrefresh,datetime_time(REFRESH_TIME))
        #for reportbug
        rb_handler=ConversationHandler(
            entry_points=[CommandHandler('reportbug',self.reportbug,filters=(Filters.command & Filters.private))],
            states={
                REPORTINGBUG:[MessageHandler(Filters.private & (~ Filters.command),self.forwardbug)]
            },
            fallbacks=[CommandHandler('quitreport',self.quitreport,filters=(Filters.command & Filters.private))]
        )
        self.dp.add_handler(rb_handler,group=0)
        #for private chat
        pc_handler=ConversationHandler(
            entry_points=[CommandHandler('startpc',self.startPC,filters=(Filters.command & Filters.private),pass_args=True)],
            states={
                GETTINGNAME:[MessageHandler(Filters.private & Filters.text,self.getPeerName)],
                GETTINGMSG:[MessageHandler(Filters.private & Filters.text,self.getPCVerifyMsg)]
            },
            fallbacks=[CommandHandler('cancelpc',self.cancelPC,filters=(Filters.command & Filters.private))]
        )
        self.dp.add_handler(pc_handler,group=2)
        self.dp.add_handler(MessageHandler(Filters.private & Filters.reply & (~ Filters.command),self.pc_message))

        self.turnon_forwardmsg()
        self.turnon_groupalert()
        self.dp.add_error_handler(self.error)
        self.updater.start_polling()
        self.updater.idle()
if __name__=="__main__":
    c=ChatBot(TOKEN,GROUP_ID,BUGMANAGER)
    c.main()
