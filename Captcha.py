#!/usr/bin/python3
# -*- coding: UTF-8 -*-
import random,logging,json
from telegram import InlineKeyboardButton,InlineKeyboardMarkup
logging.basicConfig(format='[%(asctime)s][%(name)s][%(levelname)s]%(message)s',level=logging.INFO)
logger=logging.getLogger(__name__)
CAPTCHA={"问题":{"right":("正确答案,只有一个请记得在tuple里面加逗号",),"confuse":("错误答案","至少有仨","会从错误答案中挑仨,从正确答案中挑一个")}
}
class Captcha():
    def genCaptcha():
        q=random.choice(list(CAPTCHA.keys()))
        r=random.choice(CAPTCHA[q]["right"])
        c=random.sample(CAPTCHA[q]["confuse"],3)
        keyboard=[]
        location=random.randint(0,3)
        for i in range(0,3):
            if i==location:
                keyboard.append([InlineKeyboardButton(r,callback_data="captcha:r")])
            keyboard.append([InlineKeyboardButton(c[i],callback_data="captcha:c%d"%(i))])
        if location==3:
            keyboard.append([InlineKeyboardButton(r,callback_data="captcha:r")])
        markup=InlineKeyboardMarkup(keyboard)
        return {"q":q,"markup":markup}
if __name__=="__main__":
    for i in range(10):
        c=Captcha.genCaptcha()
        print(c["q"])
        print(c["markup"])
        print()
