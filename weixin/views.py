# coding=utf-8
import xml.etree.ElementTree as ET
import urllib
import urllib2
import time
import hashlib

from django.http import HttpResponse
from django.template import RequestContext, Template
from django.views.decorators.csrf import csrf_exempt
from django.utils.encoding import smart_str, smart_unicode

from config import *


@csrf_exempt
def index(request):
    if request.method == 'GET':
        response = HttpResponse(checkSign(request), content_type='text/plain')
        return response
    elif request.method == 'POST':
        response = HttpResponse(responseMsg(request), content_type='application/xml')
        return response
    else:
        return None


def checkSign(request):
    params = request.GET
    signature = params.get('signature', None)
    timestamp = params.get('timestamp', None)
    nonce = params.get('nonce', None)
    echoStr = params.get('echostr', None)

    tmpList = [WEIXIN_TOKEN, timestamp, nonce]
    tmpList.sort()
    tmpstr = ''.join(tmpList)
    tmpstr = hashlib.sha1(tmpstr).hexdigest()
    # return echoStr
    if tmpstr == signature and echoStr is not None:
        return echoStr
    return 'Access verification fail'


def responseMsg(request):
    rawStr = smart_str(request.body)
    msg = parseXml(ET.fromstring(rawStr))

    queryStr = msg.get('Content', 'You have input nothing!')

    raw_youdao_url = '%s?keyfrom=%s&key=%s&type=data&doctype=%s&version=1.1&q=%s' % (
        YOUDAO_API_URL, YOUDAO_API_KEYFROM, YOUDAO_API_KEY,
        YOUDAO_DOC_TYPE, urllib2.quote(queryStr))

    req = urllib2.Request(url=raw_youdao_url)
    result = urllib2.urlopen(req).read()

    replyContent = parseYouDaoXml(ET.fromstring(result))

    return getReplyXml(msg, replyContent)


def parseXml(root):
    msg = dict()
    if root.tag == 'xml':
        for child in root:
            msg[child.tag] = smart_str(child.text)
    return msg


def parseYouDaoXml(root):
    replyContent = ''
    if root.tag == 'youdao-fanyi':
        for child in root:
            if child.tag == 'errorCode':
                if child.text == '20':
                    return 'too long to translate\n'
                elif child.text == '30':
                    return 'can not be able to translate with effect\n'
                elif child.text == '40':
                    return 'can not be able to support this language\n'
            elif child.text == '50':
                return 'invalid key\n'

            # 查询字符串
            elif child.tag == 'query':
                replyContent = "%s%s\n" % (replyContent, child.text)

            # 有道翻译
            elif child.tag == 'translation':
                replyContent = '%s%s\n%s\n' % (replyContent, '-' * 6 + u'翻译结果' + '-' * 6, child[0].text)

            # 有道词典-基本词典
            elif child.tag == 'basic':
                replyContent = "%s%s\n" % (replyContent, '-' * 6 + u'基本词典' + '-' * 6)
                for c in child:
                    if c.tag == 'phonetic':
                        replyContent = '%s%s\n' % (replyContent, c.text)
                    elif c.tag == 'explains':
                        for ex in c.findall('ex'):
                            replyContent = '%s%s\n' % (replyContent, ex.text)

            # 有道词典-网络释义
            elif child.tag == 'web':
                replyContent = "%s%s\n" % (replyContent, '-' * 6 + u'网络释义' + '-' * 6)
                for explain in child.findall('explain'):
                    for key in explain.findall('key'):
                        replyContent = '%s%s\n' % (replyContent, key.text)
                    for value in explain.findall('value'):
                        for ex in value.findall('ex'):
                            replyContent = '%s%s\n' % (replyContent, ex.text)
                    replyContent = '%s\n' % replyContent
        return replyContent


def getReplyXml(msg, replyContent):
    msgTpl = u"""
		<xml>
		    <ToUserName><![CDATA[%s]]></ToUserName>
		    <FromUserName><![CDATA[%s]]></FromUserName>
		    <CreateTime>%s</CreateTime>
		    <MsgType><![CDATA[%s]]></MsgType>
		    <Content><![CDATA[%s]]></Content>
		    <FuncFlag>0</FuncFlag>
		</xml>""";
    msgTpl = msgTpl % (msg['FromUserName'], \
                       msg['ToUserName'], \
                       str(int(time.time())), \
                       'text', replyContent)
    return msgTpl
