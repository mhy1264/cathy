import configparser
import time
import requests
from bs4 import BeautifulSoup as bs
import os
import ddddocr
import base64
import json
class Cathy:
    def __init__(self, id, pwd):
        self.id = id
        self.pwd = pwd
        self.session = requests.session()
        self.session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like\
                                              Gecko) Chrome/74.0.3729.169 Safari/537.36'
        self.loginPreURL = "https://www.cathaybk.com.tw/promotion/"
        self.loginURL = "https://www.cathaybk.com.tw/promotion/promotion/CreditCard/AuthenticationSubmit"
        self.reserveURL = "https://www.cathaybk.com.tw/promotion/promotion/CreditCard/Event"
        self.signAddr = "https://www.cathaybk.com.tw/promotion/promotion/CreditCard/SignCampaign"
        self.requestVerificationToken = ""
        self.ocr = ddddocr.DdddOcr()
        self.act = []

    def Consolelog(self, msg):
        temp = "{} {} ".format(time.strftime(
            "[%Y-%m-%d %H:%M:%S]", time.localtime()), msg)
        print(temp)

    def getCapt(self, img_data):
        try:
            with open("captcha.png", "wb") as fh:
                fh.write(base64.b64decode(img_data))

            with open('captcha.png', 'rb') as f:
                img_bytes = f.read()

            return self.ocr.classification(img_bytes)
        except Exception as e:
            self.Consolelog(e.args)
            return False


    def login(self):
        while True:
            self.session.cookies.clear()

            loginHtml = self.session.get(self.loginPreURL)
            parser = bs(loginHtml.text, 'lxml')
            base = parser.select("div.bg_block img")[0]["src"][len("data:image/png;base64,"):-1]

            temp = base
            for i in range(4-len(temp) % 4):
                base += "="

            capt = self.getCapt(base)

            if capt == False:
                continue

            self.requestVerificationToken = parser.select("div.wrap input")[5]['value']

            loginPayLoad = {
                "ID": self.id,
                "BirthDate": self.pwd,
                "Captcha": capt,
                "CheckAgreement": "true",
                "__RequestVerificationToken": self.requestVerificationToken,
            }

            login = self.session.post(self.loginURL, data=loginPayLoad)

            with open ("debug.html","wt",encoding=login.encoding) as f:
                f.write(login.text)

            if "已登錄活動" in login.text:
                self.Consolelog("Login Success "+capt)
                break
            else:
                if "身分證字號/居留證號碼格式錯誤" in login.text:
                    self.Consolelog("身分證字號/居留證號碼格式錯誤")
                    exit(1)
                elif "您所輸入的身分證字號/居留證號與出生年月日不符，煩請確認並重新輸入" in login.text:
                    self.Consolelog("您所輸入的身分證字號/居留證號與出生年月日不符，煩請確認並重新輸入")
                    exit(1)
                elif "&#x751F;&#x65E5;&#x683C;&#x5F0F;YYYYMMDD&#x932F;&#x8AA4;" in login.text:
                    self.Consolelog("生日格式YYYYMMDD錯誤")
                    exit(1)
                elif "驗證碼輸入錯誤" in login.text:
                    self.Consolelog("驗證碼輸入錯誤")
                elif "&#x8ACB;&#x8F38;&#x5165;&#x6B63;&#x78BA;&#x7684;&#x9A57;&#x8B49;&#x78BC;" in login.text:
                    self.Consolelog("驗證碼輸入錯誤")
                elif "請輸入驗證碼" in login.text:
                    self.Consolelog("驗證碼輸入錯誤")
                else:
                    self.Consolelog("未知的錯誤")


    def refresh(self):
        self.Consolelog(">>> refreshing")
        page = self.session.get(self.reserveURL)
        if "已登錄活動" not in page.text:
            self.login()

        parser = bs(page.text, 'lxml')

        act = parser.select("a.link")
        code = parser.select("a.btn")
        status = parser.select("a.btn span")

        item = []
        for j in range(min(len(act),len(code))):
            if status[j].getText() == "登錄":
                self.Consolelog(act[j].getText().strip().rstrip() + " " + code[j]['data-campaign-id'])
                temp = [act[j].getText().strip().rstrip(), code[j]['data-campaign-id']]
                item.append(temp)
            else:
                self.Consolelog(act[j].getText().strip().rstrip()+" 滿ㄌ")

        self.act = item

    def run(self):
        count = 5

        while True:
            if count == 5:
                count = 0
                self.refresh()

            if len(self.act) == 0:
                self.Consolelog("All Done")
                exit(0)

            submitPayLoad = {
                "CampaignId": "",
                "__RequestVerificationToken": self.requestVerificationToken
            }
            for i in self.act:
                submitPayLoad["CampaignId"] = i[1]
                result = self.session.post(self.signAddr, data=submitPayLoad)
                data = json.loads(result.text)
                data["signResultText"] = 0
                if data["signResultText"] == "登錄成功":
                    self.Consolelog("{} {} (登錄編號: {} )".format(i[0], data["signResultText"], data["signUpNumber"]))
                    self.act.remove(i)
                else:
                    self.Consolelog("{} {}".format(i[0], data["signResultText"]))
            count += 1


if __name__ == "__main__":
    configFilename = 'information.ini'
    if not os.path.isfile(configFilename):
        with open(configFilename, 'a') as f:
            f.writelines(["[Default]\n", "id = your id\n", "birth = yourBirth\n"])
            print('input your info in information.ini')
            f.close()
            exit()

    config = configparser.ConfigParser()
    config.read(configFilename)
    info = [config['Default']['id'], config['Default']['birth']]

    Bot = Cathy(info[0], info[1])

    Bot.login()
    Bot.run()