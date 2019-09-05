from django.contrib.auth.hashers import make_password
from django.http import HttpRequest, HttpResponse, JsonResponse
from .models import User, OperationSubmitForm, Operation, TimeForm
from django.contrib import auth
from .apiutils import RequestHandleFailException, getKeyOrRaiseBlankRHFE, AlertResponse, assertRequestMethod, asyncNN
from django.shortcuts import render_to_response, redirect

import requests


# Create your views here.
def logon(req: HttpRequest):
    assertRequestMethod(req, "POST")
    gUsername = getKeyOrRaiseBlankRHFE(req.POST, "username", "invalid parameters")
    gPassword = getKeyOrRaiseBlankRHFE(req.POST, "password", "invalid parameters")
    try:
        User.objects.get(username=gUsername)
        raise RequestHandleFailException(200, "user exists")
    except User.DoesNotExist:
        u = User.objects.create(username=gUsername, password=make_password(gPassword))  # 存在数据库中的密码已加密
        login(req)
        return AlertResponse("注册成功，并已为您自动登录", 200, redirect="uploadPage")


def login(req: HttpRequest):
    assertRequestMethod(req, "POST")
    gUsername = getKeyOrRaiseBlankRHFE(req.POST, "username", "no such a user")
    gPassword = getKeyOrRaiseBlankRHFE(req.POST, "password", "password is wrong")
    try:
        user = User.objects.get(username=gUsername)  # 为了区分用户不存在和密码错误两种情况
        user = auth.authenticate(req, username=gUsername, password=gPassword)
        if user is None:
            raise RequestHandleFailException(200, "password is wrong")
        if user == req.user:
            raise RequestHandleFailException(200, "has logged in")
        auth.login(req, user)
        return AlertResponse("登录成功", 200, redirect="uploadPage")
    except User.DoesNotExist:
        raise RequestHandleFailException(200, "no such a user")


def logout(req: HttpRequest):
    assertRequestMethod(req, "POST")
    user = req.user
    if not user.is_anonymous:
        auth.logout(req)
        return AlertResponse("登出成功", 200, "loginPage")
    else:
        raise RequestHandleFailException(200, "no valid session")


def loginPage(req: HttpRequest):
    assertRequestMethod(req, "GET")
    user = req.user
    if user.is_anonymous:
        return render_to_response("loginPage.html")
    else:
        raise RequestHandleFailException(400, "您已登录，若要换号登录，请先登出此号！", redirect="uploadPage")


def uploadPage(req: HttpRequest):
    assertRequestMethod(req, "GET")
    user = req.user
    if not user.is_anonymous:
        return render_to_response("uploadPage.html", {"form": OperationSubmitForm()})
    else:
        return AlertResponse("您还没有登录", 400, redirect="loginPage")


from PIL import Image

from django.db.models.fields.files import ImageFieldFile
from django.core.files import File
import random
import os
def saveImageFieldFileFromUrl(url: str, imageFieldFile: ImageFieldFile):
    from .models import determineUpload
    r = requests.get(url, stream=True)
    r.raise_for_status()
    ran = random.randint(0, 9999999)
    extname = os.path.splitext(url)[1]
    name = str(ran) + extname
    toSave = os.path.join("image", "temp", name)
    if os.path.exists(toSave):
        return saveImageFieldFileFromUrl(url, imageFieldFile)
    with open(toSave, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024*1024):
            if chunk:
                f.write(chunk)
    with open(toSave, "rb") as f:
        imageFieldFile.save(determineUpload(None, toSave), File(f), False)
    os.remove(toSave)




def upload(req: HttpRequest):
    assertRequestMethod(req, "POST")
    user = req.user
    if not user.is_anonymous:
        form = OperationSubmitForm(req.POST, req.FILES)
        if form.is_valid():
            form.instance.user = user
            if not form["input"].data:
                if form["inputUrl"].data != "":
                    saveImageFieldFileFromUrl(form["inputUrl"].data, form.instance.input)
                else:
                    raise RequestHandleFailException(400, "必须上传文件或指定文件Url")
            elif form["inputUrl"].data != "":
                raise RequestHandleFailException(400, "不能同时上传文件和指定文件Url")
            form.save()
            asyncNN(Image.open(form.instance.input.path), form["tocall"].data, form.instance).start()
            return redirect("/resultPage?id=" + str(form.instance.id))
        else:
            raise RequestHandleFailException(400, "输入的文件或Url无效")
    else:
        return AlertResponse("您还没有登录", 400, redirect="loginPage")


def test(req: HttpRequest):
    return AlertResponse("yyy", redirect="test2")


def test2(req: HttpRequest):
    return HttpResponse("qwq")


def getForDownloadPath(pathStr: str):
    import re
    from os import path
    relaPath =  re.sub(r".*image[/|\\]download[/|\\]", "", pathStr)
    sep = path.sep
    return sep + "image" + sep + "download" + sep + relaPath


def resultPage(req: HttpRequest):
    assertRequestMethod(req, "GET")
    user = req.user
    if not user.is_anonymous:
        id = int(req.GET["id"])
        try:
            model = Operation.objects.get(id=id)
        except Operation.DoesNotExist:
            raise RequestHandleFailException(404, "所访问的操作不存在！")
        if (not user.is_superuser) and model.user != user:
            raise RequestHandleFailException(403, "您无权访问此操作！")
        res = {
            "id": model.id,
            "status": model.process,
            "time": model.time,
            "input": model.input,
        }
        otps = model.output_set.all()
        otpList = []
        for otp in otps:
            otpData = {
                "name": "hhh",
                "outputStr": otp.outputStr,
            }
            if otp.outputFilePath and otp.outputFilePath != "":
                otpData["outputFileUrl"] = getForDownloadPath(otp.outputFilePath)
            otpList.append(otpData)
        res["opers"] = otpList
        return render_to_response("resultPage.html", {"ope": res})
    else:
        return AlertResponse("您还没有登录", 400, redirect="loginPage")


def queryResult(req: HttpRequest):
    assertRequestMethod(req, "GET")
    user = req.user
    if not user.is_anonymous:
        id = int(req.GET["id"])
        try:
            model = Operation.objects.get(id=id)
        except Operation.DoesNotExist:
            raise RequestHandleFailException(404, "所访问的操作不存在！")
        if (not user.is_superuser) and model.user != user:
            raise RequestHandleFailException(403, "您无权访问此操作！")
        res = {
            "id": model.id,
            "status": model.process,
            "inputUrl": model.input.url,
        }
        otps = model.output_set.all()
        otpList = []
        for otp in otps:
            otpData = {
                "name": "hhh",
                "outputStr": otp.outputStr,
            }
            if otp.outputFilePath and otp.outputFilePath != "":
                otpData["outputFileUrl"] = getForDownloadPath(otp.outputFilePath)
            otpList.append(otpData)
        res["opers"] = otpList
        return JsonResponse(res)
    else:
        return AlertResponse("您还没有登录", 400, redirect="loginPage")


RECORD_PER_PAGE = 10
import math

def assertKeyExist(key: str, form):
    d = form.__dict__["data"]
    return (key in d) and d[key] != ""


def history(req: HttpRequest):
    assertRequestMethod(req, "GET")
    form = TimeForm(req.GET)
    if not form.is_valid():
        raise RequestHandleFailException(400, "输入的查询参数无效，请检查", "history")
    fd = form.__dict__["data"]
    curPage = int(fd["curPage"]) if assertKeyExist("curPage", form) else 1
    if assertKeyExist("lastPage", form):
        page = curPage - 1
    elif assertKeyExist("nextPage", form):
        page = curPage + 1
    else:
        page = form.cleaned_data["page"] if form.cleaned_data["page"] != None else curPage
    begin = form.cleaned_data["begin"]
    end = form.cleaned_data["end"]

    user = req.user
    if not user.is_anonymous:
        if begin and end:
            query = user.operation_set.filter(time__range=(begin, end))
        elif begin and (not end):
            query = user.operation_set.filter(time__gt=begin)
        elif (not begin) and end:
            query = user.operation_set.filter(time__lt=end)
        else:
            query = user.operation_set.all()

        total = len(query)
        resList = []
        totalPage = math.ceil(total / RECORD_PER_PAGE)
        resDict = {
            "total": total,
            "totalPage": totalPage,
            "curPage": page
        }
        if not 1<=page-1<=totalPage:
            resDict["noLast"] = 1
        if not 1<=page+1<=totalPage:
            resDict["noNext"] = 1

        if(totalPage > 0):
            if page<=0 or page>totalPage:
                raise RequestHandleFailException(400, "页码无效", "history")
            for i in range((page-1)*RECORD_PER_PAGE, min(page*RECORD_PER_PAGE, total)):
                resList.append({
                    "index": i+1,
                    "id": query[i].id,
                    "time": query[i].time,
                    "status": query[i].process
                })

        resDict["list"] = resList

        return render_to_response("historyPage.html", {"data": resDict, "timeForm": TimeForm(initial={
            "begin": begin,
            "end": end}
        )})
    else:
        return AlertResponse("您还没有登录", 400, redirect="loginPage")


def delete(req: HttpRequest):
    assertRequestMethod(req, "POST")
    user = req.user
    if not user.is_anonymous:
        for id in req.POST:
            try:
                oper = Operation.objects.select_for_update().get(id=int(id))
                if (not user.is_superuser) and oper.user != user:
                    raise RequestHandleFailException(403, "无权进行此操作")
                oper.delete()
            except Exception:
                raise RequestHandleFailException(400, "数据记录不存在或状态异常！")
        if req.headers["Referer"].find("adminHistory"):
            return redirect("/adminHistory")
        return redirect("/history")
    else:
        return AlertResponse("您还没有登录", 400, redirect="loginPage")


def adminHistory(req: HttpRequest):
    assertRequestMethod(req, "GET")
    form = TimeForm(req.GET)
    if not form.is_valid():
        raise RequestHandleFailException(400, "输入的查询参数无效，请检查", "history")
    fd = form.__dict__["data"]
    curPage = int(fd["curPage"]) if assertKeyExist("curPage", form) else 1
    if assertKeyExist("lastPage", form):
        page = curPage - 1
    elif assertKeyExist("nextPage", form):
        page = curPage + 1
    else:
        page = form.cleaned_data["page"] if form.cleaned_data["page"] != None else curPage
    begin = form.cleaned_data["begin"]
    end = form.cleaned_data["end"]
    username = fd["username"] if assertKeyExist("username", form) else None

    if req.user.is_superuser:
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise RequestHandleFailException(400, "查无此用户", redirect="adminHistory")
            if begin and end:
                query = user.operation_set.filter(time__range=(begin, end))
            elif begin and (not end):
                query = user.operation_set.filter(time__gt=begin)
            elif (not begin) and end:
                query = user.operation_set.filter(time__lt=end)
            else:
                query = user.operation_set.all()
        else:
            if begin and end:
                query = Operation.objects.filter(time__range=(begin, end))
            elif begin and (not end):
                query = Operation.objects.filter(time__gt=begin)
            elif (not begin) and end:
                query = Operation.objects.filter(time__lt=end)
            else:
                query = Operation.objects.all()

        total = len(query)
        resList = []
        totalPage = math.ceil(total / RECORD_PER_PAGE)
        resDict = {
            "total": total,
            "totalPage": totalPage,
            "curPage": page
        }
        if not 1<=page-1<=totalPage:
            resDict["noLast"] = 1
        if not 1<=page+1<=totalPage:
            resDict["noNext"] = 1

        if(totalPage > 0):
            if page<=0 or page>totalPage:
                raise RequestHandleFailException(400, "页码无效", "history")
            for i in range((page-1)*RECORD_PER_PAGE, min(page*RECORD_PER_PAGE, total)):
                resList.append({
                    "index": i+1,
                    "id": query[i].id,
                    "time": query[i].time,
                    "status": query[i].process,
                    "username": query[i].user.username
                })

        resDict["list"] = resList

        return render_to_response("adminHistoryPage.html", {"data": resDict, "timeForm": TimeForm(initial={
            "begin": begin,
            "end": end}
        )})
    else:
        return AlertResponse("无权限", 403)


def adminUser(req: HttpRequest):
    assertRequestMethod(req, "GET")
    form = TimeForm(req.GET)
    if not form.is_valid():
        raise RequestHandleFailException(400, "输入的查询参数无效，请检查", "history")
    fd = form.__dict__["data"]
    curPage = int(fd["curPage"]) if assertKeyExist("curPage", form) else 1
    if assertKeyExist("lastPage", form):
        page = curPage - 1
    elif assertKeyExist("nextPage", form):
        page = curPage + 1
    else:
        page = form.cleaned_data["page"] if form.cleaned_data["page"] != None else curPage
    begin = form.cleaned_data["begin"]
    end = form.cleaned_data["end"]

    if req.user.is_superuser:
        if begin and end:
            query = User.objects.filter(last_login__range=(begin, end))
        elif begin and (not end):
            query = User.objects.filter(last_login__gt=begin)
        elif (not begin) and end:
            query = User.objects.filter(last_login__lt=end)
        else:
            query = User.objects.all()

        total = len(query)
        resList = []
        totalPage = math.ceil(total / RECORD_PER_PAGE)
        resDict = {
            "total": total,
            "totalPage": totalPage,
            "curPage": page
        }
        if not 1<=page-1<=totalPage:
            resDict["noLast"] = 1
        if not 1<=page+1<=totalPage:
            resDict["noNext"] = 1

        if(totalPage > 0):
            if page<=0 or page>totalPage:
                raise RequestHandleFailException(400, "页码无效", "history")
            for i in range((page-1)*RECORD_PER_PAGE, min(page*RECORD_PER_PAGE, total)):
                resList.append({
                    "index": i+1,
                    "id": query[i].id,
                    "time": query[i].last_login,
                    "username": query[i].username,
                    "operCount": query[i].operation_set.count()
                })

        resDict["list"] = resList

        return render_to_response("adminUserPage.html", {"data": resDict, "timeForm": TimeForm(initial={
            "begin": begin,
            "end": end}
        )})
    else:
        return AlertResponse("无权限", 403)


def adminDeleteUser(req: HttpRequest):
    assertRequestMethod(req, "POST")
    user = req.user
    if user.is_superuser:
        for id in req.POST:
            try:
                oper = User.objects.select_for_update().get(id=int(id))
                if oper == user:
                    raise RequestHandleFailException(400, "您不能删除您自己")
                oper.delete()
            except Exception:
                raise RequestHandleFailException(400, "数据记录不存在或状态异常！")
        return redirect("/adminUser")
    else:
        raise RequestHandleFailException(403, "无权限！")