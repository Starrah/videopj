from datetime import datetime
from imagebkd.apiutils import RequestHandleFailException, assertKeyExist


def getAllOpers(user):
    return user.operation_set.all()


def getOpersByTime(user, begin: datetime, end: datetime):
    return user.operation_set.filter(time__range=(begin, end))


def generateChoiceList():
    from imagebkd.nnadapter import NNList
    res = []
    c = 0
    for nn in NNList:
        res.append((c, nn["name"]))
        c = c + 1
    return res


def getInfoFromTimeForm(form):
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
    return curPage, page, begin, end, username