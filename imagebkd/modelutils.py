from datetime import datetime


def getAllOpers(user):
    return user.operation_set.all()


def getOpersByTime(user, begin: datetime, end: datetime):
    return user.operation_set.filter(time__range=(begin, end))