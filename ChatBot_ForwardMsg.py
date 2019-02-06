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
# 这个文件实现了Bot的匿名转发消息功能
# This file have realised the function of forwarding msgs annoymously.
#
# 本代码遵循MIT协议
# This program is dedicated to the public domain under the MIT license.
#
from Consts import *
from ChatBot_JoinVerify import *
from telegram.ext import CommandHandler,MessageHandler,Filters
import logging,random,itertools,os
try:
    import cPickle as pickle
except ImportError:
    import pickle
    
logging.basicConfig(format='[%(asctime)s][%(name)s][%(levelname)s]%(message)s',level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatBot_ForwardMsg(ChatBot_JoinVerify):
    def __init__(self,token,group_id,bugmanager):
        ChatBot_JoinVerify.__init__(self,token,group_id,bugmanager)
        #for joined
        self.alias={}
        #for delete msg
        self.msg_dict={}
        #for disable suc info
        if os.path.exists(DSI_USER_FILE_NAME):
            with open(DSI_USER_FILE_NAME,'rb') as f:
                self.dsi_users=pickle.load(f)
        else:
            self.dsi_users=set()
        logger.info("inited")
    #below is functions for message-forwarding
    def gen_alias(self):
        lalias=len(self.alias)
        names=set(NAMES)
        namelen=1
        while 1:
            if (lalias+3)*2<len(names): #乘二是为了让词数多的名字不一定比词数少的名字更靠后
                break
            else:
                namelen+=1
                pattern=" ".join(["%s"]*namelen)
                for i in itertools.product(NAMES,repeat=namelen):
                    names.add(pattern%i)              
        names=names.difference(self.alias.values())
        return random.sample(names,1)[0]
    def get_alias(self,userid):
        userid=int(userid)
        if userid not in self.alias:
            self.alias[userid]=self.gen_alias()
            self.msg_dict[userid]={}
        return self.alias[userid]
    def message(self,bot,update):
        msg1=update.message
        userid=msg1.from_user.id
        flag=0
        if userid in self.can_talk_users:
            flag=1
        else:
            thisuser=bot.get_chat_member(self.group_id,userid)
            if thisuser.status in ("creator","administrator","member") or thisuser.can_send_messages==True:
                self.can_talk_users.add(userid)
                flag=1
            if thisuser.status in ("creator","administrator","member","restricted"):
                self.joined_users.add(userid)
        if flag==1:
            msg2_id=self.forward_message(msg1,userid,self.group_id)
            if msg2_id is None:
                msg1.reply_text("抱歉,您的消息发送失败")
            else:
                if userid not in self.dsi_users:
                    tempmsg=msg1.reply_text("您的消息已被成功转发",disable_notification=True)
                    self.job_queue.run_once(self.delsucmsg,60,context=tempmsg) #del above msg after 60s
                self.msg_dict[userid][msg1.message_id]=msg2_id
                
        else:
            update.message.reply_text("很抱歉,您无权匿名发送消息.如果您遇到了问题,您可以用/reportbug向维护者发送问题报告.祝您身体健康,生活愉快!")
    def delsucmsg(self,bot,job):
        job.context.delete()
    def forward_message(self,msg,userid,chatid):
        """Forward a message."""
        if msg.photo:
            caption='<b>[%s]</b>'%(self.get_alias(userid))
            if msg.caption:
                caption+=msg.caption
            r=self.bot.send_photo(chatid,msg.photo[0].file_id,caption=caption,parse_mode="HTML")
        elif msg.video:
            caption='<b>[%s]</b>'%(self.get_alias(userid))
            if msg.caption:
                caption+=msg.caption
            r=self.bot.send_video(chatid,msg.video.file_id,caption=caption,parse_mode="HTML")
        elif msg.voice:
            caption='<b>[%s]</b>'%(self.get_alias(userid))
            if msg.caption:
                caption+=msg.caption
            r=self.bot.send_voice(chatid,msg.voice.file_id,caption=caption,parse_mode="HTML")
        elif msg.document:
            caption='<b>[%s]</b>'%(self.get_alias(userid))
            if msg.caption:
                caption+=msg.caption
            r=self.bot.send_document(chatid,msg.document.file_id,caption=caption,parse_mode="HTML")
        else:
            text='<b>[%s]</b>%s'%(self.get_alias(userid),msg.text_html)
            r=self.bot.send_message(chatid,text,parse_mode="HTML")
        return r.message_id
    def delmsg(self,bot,update):
        userid=update.message.from_user.id
        if update.message.reply_to_message:
            delmsgid=update.message.reply_to_message.message_id
        else:
            update.message.reply_text("请在与bot的私聊中回复您要删除的消息 /delmsg 来删除消息.")
            return
        if (userid in self.msg_dict) and (delmsgid in self.msg_dict[userid]):
            try:
                self.bot.deleteMessage(self.group_id,self.msg_dict[userid][delmsgid])
                self.msg_dict[userid].__delitem__(delmsgid)
                update.message.reply_text("这条消息已经成功删除!")
            except Exception as e:
                update.message.reply_text("抱歉,删除消息失败")
                self.bot.sendMessage(self.bugmanager,format(e))
        else:
            update.message.reply_text("您似乎不能删除本条消息,如果您遇到了问题,请用 /reportbug 报告")
    def dsi(self,bot,update):
        userid=update.message.from_user.id
        if userid not in self.dsi_users:
            self.dsi_users.add(userid)
            with open(DSI_USER_FILE_NAME,'wb') as f:
                pickle.dump(self.dsi_users,f)
        update.message.reply_text("成功转发消息以后将不会发送给您!")
        
    def undsi(self,bot,update):
        userid=update.message.from_user.id
        if userid in self.dsi_users:
            self.dsi_users.discard(userid)
            with open(DSI_USER_FILE_NAME,'wb') as f:
                pickle.dump(self.dsi_users,f)
        update.message.reply_text("成功转发消息以后会发送给您!")       
    def whoami(self,bot,update):
        userid=update.message.from_user.id
        if userid in self.alias.keys():
            update.message.reply_text("您当前的名字是%s"%(self.get_alias(userid)))
        else:
            update.message.reply_text("您当前还没有被分配名字.")
    def turnon_forwardmsg(self):
        self.dp.add_handler(CommandHandler("delmsg",self.delmsg,filters=(Filters.command & Filters.private & Filters.reply)))
        self.dp.add_handler(CommandHandler("d",self.delmsg,filters=(Filters.command & Filters.private & Filters.reply)))
        self.dp.add_handler(CommandHandler("whoami",self.whoami,filters=(Filters.command & Filters.private)))
        self.dp.add_handler(CommandHandler("dsi",self.dsi,filters=(Filters.command & Filters.private)))
        self.dp.add_handler(CommandHandler("undsi",self.undsi,filters=(Filters.command & Filters.private)))
        #forward msg should be placed at the bottom of msg handlers
        self.dp.add_handler(MessageHandler(Filters.private & (~ Filters.command),self.message),group=2)
