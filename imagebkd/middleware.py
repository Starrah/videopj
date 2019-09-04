import re
from videopj.urls import REDIRECT_DICT
from .apiutils import RequestHandleFailException, AlertResponse
from django.utils.deprecation import MiddlewareMixin

def _getDefaultRedirect(path):
    str = path if path[0] != "/" else path[1:]
    for regex in REDIRECT_DICT:
        if re.match(regex, str):
            return REDIRECT_DICT[regex]
    return None


class RequestExceptionHandlerMiddleware(MiddlewareMixin):
    def process_exception(self, req, e):
        if type(e) == RequestHandleFailException:
            return AlertResponse(e.to_resp, e.to_statusCode, e.to_redi if e.to_redi else _getDefaultRedirect(req.path))
        else:
            return AlertResponse(str(e), 400, _getDefaultRedirect(req.path))