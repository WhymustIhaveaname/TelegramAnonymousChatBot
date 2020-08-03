#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# -------------------------------------------------------------------
# 用于实现群组的认证加群,匿名发送消息和群组成员之间匿名私信的通用机器人
# 在 Consts.py 中修改相应设置, 填写 TOKEN, GROUP_ID, BUGMANAGER 等信息后即可使用
# 如果想修改 bot 的回复, 请直接编辑源代码(把这些回复的字符串放在Consts里会降低程序可读性)
# --------------------------------------------------------------------

from Consts import *
from Captcha import *
from telegram import KeyboardButton,ReplyKeyboardMarkup
from telegram.ext import Updater,CommandHandler,MessageHandler,Filters,CallbackQueryHandler
import time,sys,traceback,math,numpy
try:
    import cPickle as pickle
except ImportError:
    import pickle

LOGFILE=sys.argv[0].split(".")
LOGFILE[-1]="log"
LOGFILE=".".join(LOGFILE)
LOGLEVEL={0:"DEBUG",1:"INFO",2:"WARN",3:"ERR",4:"FATAL"}
S_START,S_GOTCAPTCHA,S_BAN,S_WFJ=range(4)

def getstrname(user):
    return "%s(%s:%s)"%(user.name,user.full_name,user.id)

class myUpdater(Updater):
    def start_polling(self,poll_interval=0.0, timeout=10, clean=False, bootstrap_retries=-1, read_latency=2.0, allowed_updates=None):
        Updater.start_polling(self,poll_interval,timeout,clean,bootstrap_retries,read_latency,allowed_updates)
        self.bot.send_message(GROUP_ID,"我上线啦!") #(I am online!)
    def stop(self):
        self.bot.send_message(GROUP_ID,"我去睡会儿") #(I am offline)
        Updater.stop(self)

class ChatBot_BasicEcho():
    """起名永远是复杂的, 这个类实现了一些基础的回话功能, 包括:
           help, printchatid, printuserid, ping
       同时它还实现了一些有用的方法以供继承, 包括:
           log, error"""
    def __init__(self,token,bugmanager):
        self.updater=myUpdater(token,use_context=True)
        self.bot=self.updater.bot
        self.dp=self.updater.dispatcher
        self.job_queue=self.dp.job_queue
        self.bugmanager=bugmanager
        self.log("ChatBot_BasicEcho inited")

    def dump_kernel(self,update,context):
        if update.message.from_user.id==BUGMANAGER:
            return 0
        else:
            self.log("%s just used dump_kernel"%(getstrname(update.message.from_user),),l=2,tg=True)
            update.message.reply_text("您无权使用此命令, 您刚才的行为将被报告. 但是请您放心, 这条命令\
只是用于调试程序内部的锁和多线程, 并不是用来记录大家的发言的")
            return 1

    def log(self,msg,l=1,end="\n",logfile=None,tg=False,notprint=False):
        st=traceback.extract_stack()[-2]
        lstr=LOGLEVEL[l]
        now_str="%s%03d"%(time.strftime("%y/%m/%d %H:%M:%S",time.localtime()),math.modf(time.time())[0]*1000)
        if l<3:
            tempstr="%s [%s,%s:%d] %s%s"%(now_str,lstr,st.name,st.lineno,str(msg),end)
        else:
            tempstr="%s [%s,%s:%d] %s:\n%s%s"%(now_str,lstr,st.name,st.lineno,str(msg),traceback.format_exc(limit=5),end)
        if not notprint:
            print(tempstr,end="")
        if l>=1:
            if logfile==None:
                logfile=LOGFILE
            with open(logfile,"a") as f:
                f.write(tempstr)
        if l>=3 or tg:
            self.bot.sendMessage(BUGMANAGER,tempstr,disable_web_page_preview=True
                ,disable_notification=True,parse_mode='HTML')

    def turnon_basicecho(self):
        self.dp.add_handler(CommandHandler("help",self.help,filters=(Filters.command & Filters.private)))
        self.dp.add_handler(CommandHandler("help",self.help_group,filters=(Filters.command & Filters.group)))
        self.dp.add_handler(CommandHandler("ping",self.ping,filters=(Filters.command & Filters.private)))
        self.dp.add_handler(CommandHandler("ping",self.ping_group,filters=(Filters.command & Filters.group)))
        self.dp.add_handler(CommandHandler("printchatid",self.printchatid))
        self.dp.add_handler(CommandHandler("printuserid",self.printuserid))
        self.dp.add_handler(CommandHandler("dump_kernel",self.dump_kernel))
        self.dp.add_error_handler(self.error)

    def extract_update(self,update):
        msg="%s from %s"%(update.effective_message.text,getstrname(update.effective_user))
        return msg

    def error(self,update,context):
        self.log('Update "%s" caused error "%s"'%(self.extract_update(update),context.error),l=3)

    def help(self,update,context):
        update.message.reply_text(M.HELP)

    def help_group(self,update,context):
        re_msg=update.message.reply_text("请不要在群里给机器人发命令, 这是一个不好的习惯, 很刷屏的!")
        def del_ping_msg(context):
            update.message.delete()
            re_msg.delete()
        self.job_queue.run_once(del_ping_msg,60)

    def printchatid(self,update,context):
        update.message.reply_text(update.message.chat.id)
    
    def printuserid(self,update,context):
        update.message.reply_text(update.message.from_user.id)
    
    def ping(self,update,context):
        update.message.reply_text("I am alive!")

    def ping_group(self,update,context):
        re_msg=update.message.reply_text("请不要在群里给机器人发命令, 这是一个不好的习惯, 很刷屏的!")
        def del_ping_msg(context):
            update.message.delete()
            re_msg.delete()
        self.job_queue.run_once(del_ping_msg,60)

class ChatBot_JoinVerify(ChatBot_BasicEcho):
    def __init__(self,token,bugmanager,group_id):
        ChatBot_BasicEcho.__init__(self,token,bugmanager)

        self.group_id=group_id
        #for to_join
        self.user_status={}
        self.joined_users=set() # A user in joined_users will never get captcha
        #for joining
        self.lock=False
        self.joining_user=None
        self.joining_msg=None
        #just for insurance
        try:
            templink=self.bot.export_chat_invite_link(self.group_id)
            templink=templink.split("/")[-1]
            self.log("export chat link: in init %s"%(templink),tg=True)
        except:
            self.log("export chat link in init failed",l=3)

        self.log("ChatBot_JoinVerify inited")

    def refresh_kernel(self,context):
        self.user_status.clear()
        self.joined_users.clear()
        self.log("refreshed JoinVerify",tg=True)
        #self.can_talk_users.clear()
        #self.alias.clear()
        #self.msg_dict.clear()

    def dump_kernel(self,update,context):
        re_code=ChatBot_BasicEcho.dump_kernel(self,update,context)
        if re_code==0:
            self.log("<b>user_status:</b> %s\n<b>lock:</b> %s\n<b>joining_user:</b> %s"\
                %(self.user_status,self.lock,self.joining_user),tg=True)
        return re_code

    def chatMemStatus(self,userid):
        """1 for joined, 0 for left or kicked, -1 for error"""
        #if userid in self.joined_users:
        #    return 1
        status=self.bot.get_chat_member(self.group_id,userid).status
        if status in ("creator","administrator","member","restricted"):
            self.joined_users.add(userid)
            return 1
        elif status in ("left","kicked"):
            return 0
        else:
            return -1
    
    def turnon_joinverify(self):
        self.dp.add_handler(CommandHandler("start",self.start,filters=(Filters.command & Filters.private)))
        self.dp.add_handler(CommandHandler("restart",self.start,filters=(Filters.command & Filters.private)))
        self.dp.add_handler(CommandHandler("continue",self.sendCaptcha,filters=(Filters.command & Filters.private)))
        self.dp.add_handler(CommandHandler("quit",self.sendByebye,filters=(Filters.command & Filters.private)))
        self.dp.add_handler(CommandHandler("getlink",self.getlink,pass_job_queue=True,filters=(Filters.command & Filters.private)))
        #new chatmem and left chat mem
        self.dp.add_handler(MessageHandler(Filters.status_update.new_chat_members,self.newmember))
        self.dp.add_handler(MessageHandler(Filters.status_update.left_chat_member,self.leftmember))
        self.dp.add_handler(CallbackQueryHandler(self.button))
        UPDATE_HOUR=20
        from datetime import time as datetime_time
        self.job_queue.run_daily(self.refresh_kernel,datetime_time(UPDATE_HOUR))

    #below is funcs for new-mem-joining
    def start(self,update,context):
        userid=update.message.from_user.id
        #if user has in group
        if self.chatMemStatus(userid)>0:
            self.bot.send_message(userid,M.YouAreChatMem)
        #if user is banning
        elif (userid in self.user_status) and self.user_status[update.message.from_user.id]==S_BAN:
            update.message.reply_text("我是不会理你的") #(I will not reply you)
        #if everything is ok
        else:
            keyboard=[[KeyboardButton("/continue"),KeyboardButton("/quit")]]
            reply_markup=ReplyKeyboardMarkup(keyboard,one_time_keyboard=True,resize_keyboard=True)
            update.message.reply_text("早上好! 加我可以进入 %s."%(GROUP_NAME,),reply_markup=reply_markup) #(add me to join xxx chat)   
            self.user_status[update.message.from_user.id]=S_START
    
    def sendCaptcha(self,update,context):
        userid=update.message.from_user.id
        if self.chatMemStatus(userid)>0:
            self.bot.send_message(userid,M.YouAreChatMem)
        elif (userid in self.user_status) and self.user_status[userid]==S_START:
            captcha=Captcha.genCaptcha()
            update.message.reply_text(captcha["q"],reply_markup=captcha["markup"])
            self.user_status[userid]=S_GOTCAPTCHA
            self.log("send captcha to %s"%(getstrname(update.message.from_user),),tg=True)
        elif (userid in self.user_status) and self.user_status[userid]==S_GOTCAPTCHA:
            update.message.reply_text("您已经获得过验证问题了! 请乖乖回答问题") #(It seems that you have got the captcha)
        else:
            update.message.reply_text("您的操作似乎不在控制流中, 如果您想加群, 请从 /start 开始, 如果您遇到了问题, 请用 /reportbug 报告, 祝您身体健康, 生活愉快!")
                                      #(It seems that your operation has been out of control flow,please start from /start)
    
    def sendByebye(self,update,context):
        userid=update.message.from_user.id
        if self.chatMemStatus(userid)>0:
            self.bot.send_message(userid,M.YouAreChatMem)
        elif (userid in self.user_status) and self.user_status[userid]==S_START:
            update.message.reply_text("再见. 很高兴认识您, 祝您身体健康, 生活愉快!") #(Bye!)
            try:
                self.user_status.__delitem__(userid)
            except:
                self.log("",l=3)
        else:
            update.message.reply_text("您的操作似乎不在控制流中, 如果您遇到了问题, 请用 /reportbug 报告.") 
                                      #(It seems that your operation has been out of control flow)
    
    def button(self,update,context):
        data=update.callback_query.data.split(":")
        msg=update.callback_query.message
        #if this is a captcha
        if data[0]=="captcha":
            if data[1]=="r":
                #答对则转给 joingroup 处理
                msg.edit_text("恭喜您回答正确!")
                self.log("%d answered captcha correctly"%(msg.chat.id),tg=True)
                self.joingroup(msg.chat.id)
            else:
                #打错则加入 S_BAN 并设置1分钟后 unban
                msg.edit_text("你竟然答错了,等一分钟再 /restart 重试吧.")
                self.user_status[msg.chat.id]=S_BAN
                self.log("%d failed to answer captcha"%(msg.chat.id),tg=True)
                self.job_queue.run_once(self.unban,60,context=msg.chat.id)

    def unban(self,context):
        """unban a user"""
        self.user_status.pop(context.job.context,"NonExist")

    def joingroup(self,userid):
        if self.lock:
            self.log("%s want to join group but lock is true"%(userid),tg=True)
            tempmsg="非常抱歉, 有人正在加群, 请等大约30s后回复 /getlink 获取邀请链接."
            self.bot.sendMessage(userid,tempmsg)
            self.user_status[userid]=S_WFJ
            return
        else:
            self.lock=True
            self.log("locked the lock: %s is joining the group"%(userid),tg=True)
            self.joining_user=userid           
            tempmsg="请在一分钟内通过 %s 入群"%(self.bot.export_chat_invite_link(self.group_id)) 
            self.log("export chat link: somebody is joining group",tg=True)
            self.joining_msg=self.bot.sendMessage(userid,tempmsg,disable_web_page_preview=True)
            self.job_queue.run_once(self.abortlink,60,context=userid) #即便这里执行失败abortlink也会释放锁,不会导致严重问题                 
            self.user_status.pop(userid,"NonExist")                 
    
    def abortlink(self,context):
        try:
            assert self.joining_user==context.job.context
        except:
            return
        # MUST try-catch the two sentence below,or will cause death-lock when failed 
        try:
            self.bot.export_chat_invite_link(self.group_id)
            self.log("export chat link: timeout but no one join",tg=True)
        except:
            self.log("",l=3)
        try:
            self.joining_msg.edit_text("链接已失效")
        except:
            self.log("",l=3)
        self.joining_user=None
        self.joining_msg=None
        self.lock=False
        self.log("unlocked the lock: timeout but no one join")

    def getlink(self,update,context):
        userid=update.message.from_user.id
        if self.chatMemStatus(userid)>0:
            self.bot.send_message(userid,M.YouAreChatMem)
        elif (userid in self.user_status) and self.user_status[userid]==S_WFJ:
            self.joingroup(userid)
        else:
            update.message.reply_text("抱歉您需要通过验证才能获得链接")

    def newmember(self,update,context):
        try:
            self.log("into newmember",tg=True)
            for mem in update.message.new_chat_members:
                if self.joining_user==mem.id:
                    self.joined_users.add(mem.id)
                else:
                    if not self.bot.kick_chat_member(self.group_id,mem.id):
                        self.log("kick %s failed!"%(getstrname(mem),),l=2,tg=True)
                    self.bot.send_message(self.joining_user,"你被检测到将入群链接复制给他人!")
                    self.log("%s copied link to others!"%(getstrname(mem),),l=2,tg=True)
                self.bot.export_chat_invite_link(self.group_id)
                self.log("export chat link: newmember",tg=True)
        except:
            log("",l=3)
        finally:
            self.joining_msg.edit_text("链接已失效")       
            self.joining_user=None
            self.joinging_msg=None
            self.lock=False
            members=[getstrname(mem) for mem in update.message.new_chat_members]
            self.log("unlocked the lock: %s joined the group"%(members,),tg=True)
    
    def leftmember(self,update,context):
        self.log("into leftmember: %s left"%(getstrname(update.message.left_chat_member),),tg=True)
        self.joined_users.discard(update.message.left_chat_member.id)

class ChatBot_ForwardMsg(ChatBot_JoinVerify):
    def __init__(self,token,bugmanager,group_id):
        ChatBot_JoinVerify.__init__(self,token,bugmanager,group_id)
        #for joined
        self.can_talk_users=set()
        self.alias={}
        #for delete msg
        self.msg_dict={}
        self.log("ChatBot_ForwardMsg inited")
    
    def refresh_kernel(self,context):
        ChatBot_JoinVerify.refresh_kernel(self,context)
        self.can_talk_users.clear()
        self.alias.clear()
        self.msg_dict.clear()
        self.log("refreshed ForwardMsg",tg=True)

    def dump_kernel(self,update,context):
        re_code=ChatBot_JoinVerify.dump_kernel(self,update,context)
        if re_code==0:
            self.log("<b>alias:</b> %s\n<b>msg_dict:</b> %s"%(self.alias,self.msg_dict),tg=True)
        return re_code

    def turnon_forwardmsg(self):
        self.dp.add_handler(CommandHandler("whoami",self.whoami,filters=(Filters.command & Filters.private)))
        self.dp.add_handler(MessageHandler(Filters.private & Filters.reply & (~Filters.command),self.reply_message))
        self.dp.add_handler(MessageHandler(Filters.private & (~ Filters.reply) & (~Filters.command),self.message))

    def leftmember(self,update,context):
        ChatBot_JoinVerify.leftmember(self,update,context)
        self.can_talk_users.discard(update.message.left_chat_member.id)

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

    def whoami(self,update,context):
        userid=update.message.from_user.id
        if userid in self.alias.keys():
            update.message.reply_text("您当前的名字是 %s"%(self.get_alias(userid)))
        else:
            update.message.reply_text("您当前还没有被分配名字.")

    def user_can_talk(self,userid):
        flag=0
        if userid in self.can_talk_users:
            flag=1
        else:
            thisuser=self.bot.get_chat_member(self.group_id,userid)
            if thisuser.status in ("creator","administrator","member") or thisuser.can_send_messages==True:
                self.can_talk_users.add(userid)
                flag=1
            if thisuser.status in ("creator","administrator","member","restricted"):
                self.joined_users.add(userid)
        return flag

    def message(self,update,context):
        msg1=update.message
        userid=msg1.from_user.id
        #if msg1.text.startswith("report ") or msg1.text.startswith("re "):
        if self.user_can_talk(userid)==1:
            msg2_id=self.forward_message(msg1,userid,self.group_id)
            if msg2_id is None:
                msg1.reply_text("抱歉,您的消息发送失败")
            else:
                self.msg_dict[userid][msg1.message_id]=msg2_id
                tempmsg=msg1.reply_text("您的消息已被成功转发",disable_notification=True)
                def delsucmsg(context):
                    tempmsg.delete()
                self.job_queue.run_once(delsucmsg,60)
        else:
            update.message.reply_text("很抱歉, 您无权匿名发送消息. 祝您身体健康, 生活愉快!")

    def forward_message(self,msg,userid,chatid):
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
            text='<b>[%s]</b> %s'%(self.get_alias(userid),msg.text_html)
            r=self.bot.send_message(chatid,text,parse_mode="HTML")
        return r.message_id

    def reply_message(self,update,context):
        msg1=update.message
        if msg1.text=="del" or msg1.text=="d" or msg1.text=="delmsg":
            delmsgid=update.message.reply_to_message.message_id
            userid=update.message.from_user.id
            if (userid in self.msg_dict) and (delmsgid in self.msg_dict[userid]):
                try:
                    self.bot.deleteMessage(self.group_id,self.msg_dict[userid][delmsgid])
                    self.msg_dict[userid].__delitem__(delmsgid)
                    update.message.reply_text("这条消息已经成功删除!")
                except:
                    update.message.reply_text("抱歉, 删除消息失败")
                    self.log("",l=3)
            else:
                update.message.reply_text("您似乎不能删除本条消息, 如果您遇到了问题, 请用 /reportbug 报告")
        else:
            update.message.reply_text("在与机器人的私聊中回复想要删除的消息 del 或者 d 或者 delmsg 以删除这条消息")

def start_bot():
    c=ChatBot_ForwardMsg(TOKEN,BUGMANAGER,GROUP_ID)
    c.turnon_basicecho()
    c.turnon_joinverify()
    c.turnon_forwardmsg()
    c.log("starting...",tg=True)
    c.updater.start_polling()
    c.updater.idle()

if __name__=="__main__":
    start_bot()
