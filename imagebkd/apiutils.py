from django.http import HttpResponse, HttpRequest
import re

class RequestHandleFailException(Exception):
    def __init__(self, to_statusCode=200, to_resp="", redirect = None):
        self.to_statusCode = to_statusCode
        self.to_resp = to_resp
        self.to_redi = redirect


def getKeyOrRaiseBlankRHFE(obj, key, errStr="invalid parameters"):
    if type(key) == list:
        resList = []
        for k in key:
            try:
                r = obj[k]
                if r == "" or r is None:
                    raise RequestHandleFailException(200, errStr)
                resList.append(r)
            except KeyError:
                raise RequestHandleFailException(200, errStr)
        return resList
    else:
        try:
            r = obj[key]
            if r == "" or r is None:
                raise RequestHandleFailException(200, errStr)
        except KeyError:
            raise RequestHandleFailException(200, errStr)
        return r


def assertRequestMethod(req: HttpRequest, method: str, errStr="错误的请求方法！"):
    if req.method != method:
        raise RequestHandleFailException(405, errStr)



def AlertResponse(text: str, status=200, redirect = None):
    toRes = "<script>alert(\""+ text +"\");"
    if redirect != None:
        if(redirect[0] != "\"" or redirect[-1] != "\""):
            redirect = "\"" + redirect + "\""
        toRes += ("window.location.href = " + redirect + ";")
    toRes += "</script>"
    return HttpResponse(toRes, status=status)

import threading
from PIL import Image
from .models import Output, Operation
class asyncNN(threading.Thread):
    def __init__(self, image: Image, operTypes: list, operObj):
        super().__init__()
        self.image = image
        self.operTypes = operTypes
        self.operObj = operObj
        self.otpList = []
        for oneOper in self.operTypes:
            output = Output(type=oneOper, oper=self.operObj)
            output.save()
            self.otpList.append(output)

    def run(self):
        for otp in self.otpList:
            asyncNN.NNInterface(self.image, otp)
        self.operObj = Operation.objects.select_for_update().get(id=self.operObj.id)
        self.operObj.process = 1
        self.operObj.save()

    def NNInterface(image: Image, otpObj: Output):
        #记得操作数据库时要加锁
        #直接操作otpobj把结果存进去
        import time
        time.sleep(5)
        otpObj = Output.objects.select_for_update().get(id=otpObj.id)
        otpObj.outputStr="已完成"
        otpObj.save()