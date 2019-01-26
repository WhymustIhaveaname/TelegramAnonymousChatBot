#!/usr/bin/python3
# -*- coding: UTF-8 -*-
from Captcha import *
from Consts import *
from telegram import KeyboardButton,ReplyKeyboardMarkup
from telegram.ext import Updater,CommandHandler,MessageHandler,Filters,CallbackQueryHandler
from datetime import time as datetime_time
import logging,time,random,traceback,itertools,sys
# Enable logging
logging.basicConfig(format='[%(asctime)s][%(name)s][%(levelname)s]%(message)s',level=logging.INFO)
logger = logging.getLogger(__name__)

S_START=0
S_GOTCAPTCHA=1
S_BAN=2
S_WFJ=3

TOKEN=""
GROUP_ID=
BUGMANAGER=
NAMES=("Alice","Bob")
now = lambda: int(time.time())
class myUpdater(Updater):
    def start_polling(self,poll_interval=0.0, timeout=10, clean=False, bootstrap_retries=-1, read_latency=2.0, allowed_updates=None):
        Updater.start_polling(self,poll_interval,timeout,clean,bootstrap_retries,read_latency,allowed_updates)
        self.bot.send_message(GROUP_ID,M_IamOnline)
    def stop(self):
        self.bot.send_message(GROUP_ID,M_IamOffline)
        Updater.stop(self)
        
class ChatBot():
    def __init__(self,token):
        self.updater=myUpdater(token)
        self.bot=self.updater.bot
        #for to_join
        self.user_status={}
        #for joining
        self.lock=False
        self.joining_user=None
        self.joining_msg=None
        #for joined
        self.can_talk_users=set()
        self.joined_users=set()
        self.alias={}
        try:
            self.bot.export_chat_invite_link(GROUP_ID)
            self.log("export chat link in init")
        except Exception as e:
            self.log(format(e))
    def log(self,msg): #用于调试,调试好了会关掉日志
        msg="[%s]%s:%s"%(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime()),sys._getframe(1).f_code.co_name,msg)
        print(msg)
        with open(__file__+".log","a") as f:
            f.write(msg+"\n")    
    def start(self,bot,update):
        userid=update.message.from_user.id
        #if user has in group
        if self.fun_unnamed(userid)>0:
            self.bot.send_message(userid,"您已是群成员,开始发消息吧!")
            return 1
        #if user is banning
        if userid in self.user_status:
            if self.user_status[update.message.from_user.id]==S_BAN:
                update.message.reply_text("我是不会理你的")
                return 2
        #if everything is ok
        keyboard=[[KeyboardButton("/继续"),KeyboardButton("/退出")]]
        reply_markup=ReplyKeyboardMarkup(keyboard,one_time_keyboard=True,resize_keyboard=True)
        update.message.reply_text("早上好!加我可以进入北大物院匿名讨论群.",reply_markup=reply_markup)        
        self.user_status[update.message.from_user.id]=S_START
        return 0
    def fun_unnamed(self,userid):
        if userid in self.joined_users:
            return 1
        status=self.bot.get_chat_member(GROUP_ID,userid).status
        if status in ("creator","administrator","member","restricted"):
            self.joined_users.add(userid)
            return 1
        elif status in ("left","kicked"):
            return 0
        else:
            return -1
    def sendCaptcha(self,bot,update):
        userid=update.message.from_user.id
        if self.fun_unnamed(userid)>0:
            self.bot.send_message(userid,"您已是群成员,开始发消息吧!")
            return 1
        if (userid in self.user_status) and self.user_status[userid]==S_START:
            captcha=Captcha.genCaptcha()
            update.message.reply_text(captcha["q"],reply_markup=captcha["markup"])
            self.user_status[userid]=S_GOTCAPTCHA
            return 0
        elif (userid in self.user_status) and self.user_status[userid]==S_GOTCAPTCHA:
            update.message.reply_text("您已经获得过验证问题了!请乖乖回答问题")
        else:
            update.message.reply_text("您的操作似乎不在控制流中,如果您想加群,请从 /start 开始,如果您遇到了问题,请用 /reportbug 报告,祝您身体健康,生活愉快!")
            return 2
    def sendByebye(self,bot,update):
        userid=update.message.from_user.id
        if self.fun_unnamed(userid)>0:
            self.bot.send_message(userid,"您已是群成员,开始发消息吧!")
            return 1
        if (userid in self.user_status) and self.user_status[userid]==S_START:
            update.message.reply_text("再见.很高兴认识您,祝您身体健康,生活愉快!")
            try:
                self.user_status.__delitem__(userid)
            except:
                self.log(traceback.format_exc())
            return 0
        else:
            update.message.reply_text("您的操作似乎不在控制流中,如果您遇到了问题,请用 /reportbug 报告.")
            return 2
    def button(self,bot,update,job_queue):
        data=update.callback_query.data.split(":")
        msg=update.callback_query.message
        #if this is a captcha return
        if data[0]=="captcha":
            #if captcha is right
            if data[1]=="r":
                if self.lock:
                    self.log("%s want to join group but lock is true"%(msg.chat.id))
                    tempmsg="恭喜您回答正确!但是非常抱歉,有人正在加群,请等大约30s后回复 /getlink 获取邀请链接."
                    msg.edit_text(tempmsg)
                    self.user_status[msg.chat.id]=S_WFJ
                    return 0
                else:
                    self.lock=True
                    self.log("%s is joining the group and locked the lock"%(msg.chat.id))
                    self.joining_user=msg.chat.id
                    self.joining_msg=msg
                    tempmsg="恭喜您回答正确!请在一分钟内通过 %s 入群"%(self.bot.export_chat_invite_link(GROUP_ID))
                    self.log("export chat link normally")
                    msg.edit_text(tempmsg,disable_web_page_preview=True)                    
                    try:
                        self.user_status.__delitem__(msg.chat.id) #一个人在上一次启动时获得了验证问题,重启后回答会导致这句话执行失败
                    except:
                        self.log(traceback.format_exc())
                    job_queue.run_once(self.abortlink,60,context=msg.chat.id)
                    return 0                  
            #if captcha is wrong
            else:
                msg.edit_text("你竟然答错了,等一分钟再 /restart 重试吧.")
                self.user_status[msg.chat.id]=S_BAN
                job_queue.run_once(self.unban,60,context=msg.chat.id)
                return 0
    def newmember(self,bot,update):
        for mem in update.message.new_chat_members:
            if self.joining_user==mem.id:
                self.joined_users.add(mem.id)
                self.can_talk_users.add(mem.id)
            else: #if illigal user joined group
                #update invite link immediately
                if not self.bot.kick_chat_member(GROUP_ID,mem.id):
                    self.bot.send_message(BUGMANAGER,"剔除%s(%s)(id:%s)失败!"%(mem.name,mem.fullname,mem.id))
                self.bot.send_message(self.joining_user,"你被检测到将入群链接复制给他人")
                self.bot.send_message(BUGMANAGER,"%s 用户将入群链接复制给了他人"%(self.joining_user))
            try:
                self.bot.export_chat_invite_link(GROUP_ID)
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
        try:
            self.user_status.__delitem__(job.context)
        except:
            self.log(traceback.format_exc())
    def abortlink(self,bot,job):
        if self.joining_user==job.context:
            #下面两句一定要分别try-catch,否则一旦失败会造成死锁
            try:
                self.bot.export_chat_invite_link(GROUP_ID)
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
        if self.fun_unnamed(userid)>0:
            self.bot.send_message(userid,"您已是群成员,开始发消息吧!")
            return 1
        if (userid in self.user_status) and self.user_status[userid]==S_WFJ:
            if self.lock==True:
                self.log("%s getlink but lock is true"%(userid))
                update.message.reply_text("请您再耐心等等.")
                return 0
            else:
                self.lock=True
                self.log("%s getlink and locked the lock"%(userid))
                self.joining_user=userid
                try:
                    link=self.bot.export_chat_invite_link(GROUP_ID)
                    self.log("export chat link")
                except:
                    self.log(traceback.format_exc())
                    link="获得链接失败"
                try:
                    self.joining_msg=self.bot.send_message(userid,"请在一分钟内通过 %s 入群"%(link),disable_web_page_preview=True)
                except:
                    self.log(traceback.format_exc())
                try:
                    self.user_status.__delitem__(userid)
                except:
                    self.log(traceback.format_exc())
                job_queue.run_once(self.abortlink,60,context=userid)
                return 0
        else:
            update.message.reply_text("抱歉您需要通过验证才能获得链接")
            return 2
    def gen_alias(self,userid):
        lalias=len(self.alias)
        names=set(NAMES)
        namelen=1
        while 1:
            if lalias<len(names):
                break
            else:
                namelen+=1
                pattern=" ".join(["%s"]*namelen)
                for i in itertools.product(NAMES,repeat=namelen):
                    names.add(pattern%i)              
        names=names.difference(self.alias.values())
        return random.sample(names,1)[0]
    def get_alias(self,userid):
        if not(userid in self.alias.keys()):
            self.alias[userid]=self.gen_alias(userid)
        return self.alias[userid]
    def message(self,bot,update):
        userid=update.message.from_user.id
        flag=0
        if userid in self.can_talk_users:
            flag=1
        else:
            thisuser=bot.get_chat_member(GROUP_ID,userid)
            if thisuser.status in ("creator","administrator","member") or thisuser.can_send_messages==True:
                self.can_talk_users.add(userid)
                flag=1
            if thisuser.status in ("creator","administrator","member","restricted"):
                self.joined_users.add(userid)
        if flag==1:
            msg=update.message
            msg_id=self.forward_message(msg,userid)
            if msg_id is None:
                msg.reply_text("抱歉,您的消息发送失败")
            else:
                msg.reply_text("您的消息已被成功转发",disable_notification=True)
        else:
            update.message.reply_text(M_NotAllowed2SendMsg)
    def forward_message(self,msg,userid):
        """Forward a message."""
        if msg.photo:
            caption='<b>[%s]</b>'%(self.get_alias(userid))
            if msg.caption:
                caption+=msg.caption
            r=self.bot.send_photo(GROUP_ID,msg.photo[0].file_id,caption=caption,parse_mode="HTML")
        elif msg.video:
            caption='<b>[%s]</b>'%(self.get_alias(userid))
            if msg.caption:
                caption+=msg.caption
            r=self.bot.send_video(GROUP_ID,msg.video.file_id,caption=caption,parse_mode="HTML")
        elif msg.voice:
            caption='<b>[%s]</b>'%(self.get_alias(userid))
            if msg.caption:
                caption+=msg.caption
            r=self.bot.send_voice(GROUP_ID,msg.voice.file_id,caption=caption,parse_mode="HTML")
        elif msg.document:
            caption='<b>[%s]</b>'%(self.get_alias(userid))
            if msg.caption:
                caption+=msg.caption
            r=self.bot.send_document(GROUP_ID,msg.document.file_id,caption=caption,parse_mode="HTML")
        else:
            text='<b>[%s]</b>%s'%(self.get_alias(userid),msg.text_html)
            r=self.bot.send_message(GROUP_ID,text,parse_mode="HTML")
        return r.message_id
    def reportbug(self,bot,update):
        L=len("/reportbug ")
        text=update.message.text
        if len(text)<=L:
            update.message.reply_text("您似乎没有在命令后附加您要说的")
        else:
            user=update.message.from_user
            msg="%s(%s)报告:\n%s"%(user.name,user.id,text[L:len(text)])
            self.bot.send_message(BUGMANAGER,msg)
            update.message.reply_text("您的bug报告已经被提交给开发者")
    def whoami(self,bot,update):
        userid=update.message.from_user.id
        if userid in self.alias.keys():
            update.message.reply_text("您当前的名字是%s"%(self.alias[userid]))
        else:
            update.message.reply_text("您当前还没有被分配名字.")
    def help(self,bot,update):
        update.message.reply_text(M_HELP)
    def refresh(self,bot,update):
        userid=update.message.from_user.id
        status=self.bot.get_chat_member(GROUP_ID,userid).status
        if status in ("creator","administrator"):
            self.joined_users.clear()
            self.can_talk_users.clear()
            self.alias.clear()
            update.message.reply_text("成功刷新!")
            self.bot.send_message(GROUP_ID,"匿名列表已被管理员刷新")
        else:
            update.message.reply_text("您无权进行此操作!")
            self.bot.send_message(BUGMANAGER,"%s(%s)试图使用refresh"%(user.name,user.fullname))
    def dailyrefresh(self):
        try:
            self.joined_users.clear()
            self.can_talk_users.clear()
            self.alias.clear()
        except Exception as e:
            self.bot.send_message(BUGMANAGER,"匿名列表自动刷新失败:%s"%(format(e)))
        else:
            self.bot.send_message(GROUP_ID,"匿名列表已每日自动刷新")
    def printchatid(bot,update):
        update.message.reply_text(update.message.chat.id)
    def printuserid(bot,update):
        update.message.reply_text(update.message.from_user.id)
    def error(self,bot,update,error):
        print('Update "%s" caused error "%s"', update, error)    
    def main(self):
        dp = self.updater.dispatcher
        dp.add_handler(CommandHandler("start",self.start))
        dp.add_handler(CommandHandler("继续",self.sendCaptcha))
        dp.add_handler(CommandHandler("退出",self.sendByebye))
        dp.add_handler(CommandHandler("restart",self.start))
        dp.add_handler(CommandHandler("reportbug",self.reportbug))
        dp.add_handler(CommandHandler("whoami",self.whoami))
        dp.add_handler(CommandHandler("help",self.help))
        dp.add_handler(CommandHandler("getlink",self.getlink,pass_job_queue=True))
        dp.add_handler(CommandHandler("refresh",self.refresh))
        dp.add_handler(CommandHandler("printchatid",ChatBot.printchatid))
        dp.add_handler(CommandHandler("printuserid",ChatBot.printuserid))        
        dp.add_handler(CallbackQueryHandler(self.button,pass_job_queue=True))
        dp.add_handler(MessageHandler(Filters.private,self.message))
        dp.add_handler(MessageHandler(Filters.status_update.left_chat_member,self.leftmember))
        dp.add_handler(MessageHandler(Filters.status_update.new_chat_members,self.newmember))
        dp.job_queue.run_daily(self.dailyrefresh,datetime_time(4)) #每日自动刷新
        
        dp.add_error_handler(self.error)

        self.updater.start_polling()
        self.updater.idle()
if __name__=="__main__":
    c=ChatBot(TOKEN)
    c.main()
