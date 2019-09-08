import math
from django.http import HttpResponse, HttpRequest


RECORD_PER_PAGE = 10


# 接口校验与返回
class RequestHandleFailException(Exception):
    def __init__(self, to_statusCode=400, to_resp="", redirect=None):
        self.to_statusCode = to_statusCode
        self.to_resp = to_resp
        self.to_redi = redirect


def AlertResponse(text: str, status=200, redirect=None):
    toRes = "<script>alert(\"" + text + "\");"
    if redirect != None:
        if (redirect[0] != "\"" or redirect[-1] != "\""):
            redirect = "\"" + redirect + "\""
        toRes += ("window.location.href = " + redirect + ";")
    toRes += "</script>"
    return HttpResponse(toRes, status=status)


def getKeyOrRaiseBlankRHFE(obj, key, errStr="无效的输入参数"):
    if type(key) == list:
        resList = []
        for k in key:
            try:
                r = obj[k]
                if r == "" or r is None:
                    raise RequestHandleFailException(400, errStr)
                resList.append(r)
            except KeyError:
                raise RequestHandleFailException(400, errStr)
        return resList
    else:
        try:
            r = obj[key]
            if r == "" or r is None:
                raise RequestHandleFailException(400, errStr)
        except KeyError:
            raise RequestHandleFailException(400, errStr)
        return r


def assertKeyExist(key: str, form):
    d = form.__dict__["data"]
    return (key in d) and d[key] != ""


def assertRequestMethod(req: HttpRequest, method: str, errStr="错误的请求方法"):
    if req.method != method:
        raise RequestHandleFailException(405, errStr)


def assertUser(req: HttpRequest, aimUser=None, allowSuperUser=True):
    user = req.user
    if user.is_anonymous:
        raise RequestHandleFailException(403, "您还没有登录！")
    if not (((not aimUser) or user == aimUser) or (allowSuperUser and user.is_superuser)):
        raise RequestHandleFailException(403, "您无权限执行此操作！")


def assertSuperUser(req: HttpRequest):
    if not req.user.is_superuser:
        raise RequestHandleFailException(403, "您无权限执行此操作！")


def subList(l, len, begin=0):
    """选取列表中从begin开始的，不超过len个元素，构成新列表"""
    r = []
    c = 0
    for n in l:
        if c >= begin:
            r.append(n)
        c = c + 1
        if c >= len:
            break
    return r


# 根据数据库的最新记录产生输出结构以便完成渲染页面和ajax的输出
def validateOutputStatus(model):
    from imagebkd.views import MOST_PIC_SHOW_RES
    from imagebkd.nnadapter import NNList
    from .fileutils import getFilesListOrZip, getForDownloadPath
    otps = model.output_set.all()
    otpList = []
    for otp in otps:
        otpData = {
            "name": NNList[otp.type]["name"],
            "outputStr": otp.outputStr
        }
        otpRawDown, otpRawList = getFilesListOrZip(otp.outputFilePath, otp, True if otp.process else False)
        otpData["outputFileUrls"] = getForDownloadPath(otpRawList, MOST_PIC_SHOW_RES)
        otpData["outputDownload"] = getForDownloadPath(otpRawDown)
        otpList.append(otpData)
    return otpList


# 完成分页显示的分页工作
def generatePageInfo(query, page, recordInOnePage=RECORD_PER_PAGE):
    total = len(query)
    totalPage = math.ceil(total / recordInOnePage)
    resDict = {
        "total": total,
        "totalPage": totalPage,
        "curPage": page
    }
    if not 1 <= page - 1 <= totalPage:
        resDict["noLast"] = 1
    if not 1 <= page + 1 <= totalPage:
        resDict["noNext"] = 1
    pageRange = range((page - 1) * recordInOnePage, min(page * recordInOnePage, total)) if totalPage > 0 else []
    if totalPage > 0 and (page <= 0 or page > totalPage):
        raise RequestHandleFailException(400, "页码无效", "history")
    return resDict, total, totalPage, pageRange