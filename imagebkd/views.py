from django.contrib.auth.hashers import make_password
from django.http import HttpRequest, HttpResponse, JsonResponse
from .models import User, OperationSubmitForm, Operation
from django.contrib import auth
from .apiutils import RequestHandleFailException, getKeyOrRaiseBlankRHFE, AlertResponse, assertRequestMethod, asyncNN
from django.shortcuts import render_to_response, redirect
import threading


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


def upload(req: HttpRequest):
    assertRequestMethod(req, "POST")
    user = req.user
    if not user.is_anonymous:
        form = OperationSubmitForm(req.POST, req.FILES)
        form.instance.user = user
        form.save()
        asyncNN(Image.open(form.instance.input.path), form["tocall"].data, form.instance).start()
        return redirect("/resultPage?id=" + str(form.instance.id))
    else:
        return AlertResponse("您还没有登录", 400, redirect="loginPage")


def test(req: HttpRequest):
    return AlertResponse("yyy", redirect="test2")


def test2(req: HttpRequest):
    return HttpResponse("qwq")


def resultPage(req: HttpRequest):
    assertRequestMethod(req, "GET")
    user = req.user
    if not user.is_anonymous:
        id = int(req.GET["id"])
        try:
            model = Operation.objects.get(id=id)
        except Operation.DoesNotExist:
            raise RequestHandleFailException(404, "所访问的操作不存在！")
        if (model.user != user):
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
            if otp.outputFile:
                otpData["outputFileUrl"] = otp.outputFile.url
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
        if (model.user != user):
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
            if otp.outputFile:
                otpData["outputFileUrl"] = otp.outputFile.url
            otpList.append(otpData)
        res["opers"] = otpList
        return JsonResponse(res)
    else:
        return AlertResponse("您还没有登录", 400, redirect="loginPage")
