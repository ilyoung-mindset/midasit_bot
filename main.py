#-*- coding: utf-8 -*-
#
# original:    https://github.com/yukuku/telebot
# modified by: Bak Yeon O @ http://bakyeono.net
# description: http://bakyeono.net/post/2015-08-24-using-telegram-bot-api.html
# github:      https://github.com/bakyeono/using-telegram-bot-api
#
import sys
sys.path.append('/home/nykim/google_appengine/')

# 구글 앱 엔진 라이브러리 로드
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
import webapp2

# URL, JSON, 로그, 정규표현식 관련 라이브러리 로드
import urllib
import urllib2
import json
import logging
import re
import time
from datetime import date, tzinfo
from datetime import timedelta 

from datetime import tzinfo, timedelta, datetime

ZERO = timedelta(0)
HOUR = timedelta(hours=1)
class UTC(tzinfo):
    """UTC"""
    def utcoffset(self, dt):
        return ZERO
    def tzname(self, dt):
        return "UTC"
    def dst(self, dt):
        return ZERO

utc = UTC()

class TimeZoneOffset(tzinfo):
    def __init__(self, hours, name):
        self.__offset = timedelta(hours = hours)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return ZERO

# 봇 토큰, 봇 API 주소
TOKEN = '239557605:AAFPnfm4zOJ6XFK2nByTxdVQZza3WmPbr4E'
BASE_URL = 'https://api.telegram.org/bot' + TOKEN + '/'

# 봇이 응답할 명령어
CMD_START     = '/start'
CMD_STOP      = '/stop'
CMD_HELP      = '/help'
CMD_BROADCAST = '/broadcast'
CMD_BROADCAST_SHORTCUT = '/bc'
CMD_REGISTER_ID = '/register'
CMD_QUERY_ID = '/query'
CMD_TEST = '/test'

# 봇 상태
STATUS_IDLE = 'IDLE'
STATUS_DINNER = 'DINNER'

#인라인 커맨드로 긔..긔긔귀요미 사진 추가;

# 봇 사용법 & 메시지
USAGE = u"""[사용법] 아래 명령어를 메시지로 보내거나 버튼을 누르시면 됩니다.
/start - (봇 활성화)
/stop  - (봇 비활성화)
/help  - (이 도움말 보여주기)
"""
MSG_START = u'봇을 시작합니다.'
MSG_STOP  = u'봇을 정지합니다.'
MSG_BOT_POSTFIX = u' sent from midasit_bot'

# 커스텀 키보드
CUSTOM_KEYBOARD = [
        [CMD_START],
        [CMD_STOP],
        [CMD_HELP]]

SELECT_DINNER_EAT=u'/ㅇㅇ먹음'
SELECT_DINNER_NOT=u'/ㄴㄴ안먹음'
CUSTOM_KEYBOARD_YESNO = [
        [SELECT_DINNER_EAT],
        [SELECT_DINNER_NOT]]

class NDB_Account(ndb.Model):
    id = ndb.StringProperty()
    name = ndb.StringProperty()

def registerAccount(chat_id, user_id):
    # 아이디 확인 절차...
    # - send email to this mail account with a randomly generated passwd
    # - wait for passwd or quit

    # DB 인스턴스에 저장
    instance = NDB_Account.get_or_insert(str(chat_id))
    instance.id = user_id
    instance.put()
    send_msg(chat_id, u'아이디가 등록됨')

def test_func(msg):
    msg_id = msg['message_id']
    chat_id = msg['chat']['id']
    text = msg.get('text')
    logging.info(chat_id)
    for chat in get_enabled_chats():
        logging.info(chat)
        account = NDB_Account.get_by_id(str(chat_id))
        logging.info(account.id)
        logging.info(account.name)
        #send_msg(chat.key.string_id(), text + u' << broadcasted by ' + str(chat_id))
    pass

def queryAccount(chat_id):
    account = NDB_Account.get_by_id(str(chat_id))
    if account == None:
        send_msg(chat_id, u'등록된 아이디가 없습니다')
        return
    send_msg(chat_id, u'등록된 아이디는 ' + account.id)

# 채팅별 봇 활성화 상태
# 구글 앱 엔진의 Datastore(NDB_)에 상태를 저장하고 읽음
# 사용자가 /start 누르면 활성화
# 사용자가 /stop  누르면 비활성화
class NDB_SerivceEnableStatus(ndb.Model):
    enabled = ndb.BooleanProperty(required=True, indexed=True, default=False,)
    status =  ndb.StringProperty(required=True, default=STATUS_IDLE,)

def set_enabled(chat_id, enabled):
    u"""set_enabled: 봇 활성화/비활성화 상태 변경
    chat_id:    (integer) 봇을 활성화/비활성화할 채팅 ID
    enabled:    (boolean) 지정할 활성화/비활성화 상태
    """
    es = NDB_SerivceEnableStatus.get_or_insert(str(chat_id))
    es.enabled = enabled
    es.put()

def get_enabled(chat_id):
    u"""get_enabled: 봇 활성화/비활성화 상태 반환
    return: (boolean)
    """
    es = NDB_SerivceEnableStatus.get_by_id(str(chat_id))
    if es:
        return es.enabled
    return False

def get_enabled_chats():
    u"""get_enabled: 봇이 활성화된 채팅 리스트 반환
    return: (list of NDB_SerivceEnableStatus)
    """
    query = NDB_SerivceEnableStatus.query(NDB_SerivceEnableStatus.enabled == True)
    return query.fetch()

# 메시지 발송 관련 함수들
def send_msg(chat_id, text, reply_to=None, no_preview=True, keyboard=None):
    u"""send_msg: 메시지 발송
    chat_id:    (integer) 메시지를 보낼 채팅 ID
    text:       (string)  메시지 내용
    reply_to:   (integer) ~메시지에 대한 답장
    no_preview: (boolean) URL 자동 링크(미리보기) 끄기
    keyboard:   (list)    커스텀 키보드 지정
    """
    params = {
        'chat_id': str(chat_id),
        'text': text.encode('utf-8'),
        }
    if reply_to:
        params['reply_to_message_id'] = reply_to
    if no_preview:
        params['disable_web_page_preview'] = no_preview
    if keyboard:
        reply_markup = json.dumps({
            'keyboard': keyboard,
            'resize_keyboard': True,
            'one_time_keyboard': False,
            'selective': (reply_to != None),
            })
        params['reply_markup'] = reply_markup
    try:
        urllib2.urlopen(BASE_URL + 'sendMessage', urllib.urlencode(params)).read()
    except Exception as e: 
        logging.exception(e)

def broadcast(chat_id, text):
    u"""broadcast: 봇이 켜져 있는 모든 채팅에 메시지 발송
    text:       (string)  메시지 내용
    """
    for chat in get_enabled_chats():
        send_msg(chat.key.string_id(), text + u' << broadcasted by ' + str(chat_id))

# 봇 명령 처리 함수들
def cmd_start(chat_id):
    u"""cmd_start: 봇을 활성화하고, 활성화 메시지 발송
    chat_id: (integer) 채팅 ID
    """
    set_enabled(chat_id, True)
    send_msg(chat_id, MSG_START, keyboard=CUSTOM_KEYBOARD)

def cmd_stop(chat_id):
    u"""cmd_stop: 봇을 비활성화하고, 비활성화 메시지 발송
    chat_id: (integer) 채팅 ID
    """
    set_enabled(chat_id, False)
    send_msg(chat_id, MSG_STOP)

def cmd_help(chat_id):
    u"""cmd_help: 봇 사용법 메시지 발송
    chat_id: (integer) 채팅 ID
    """
    send_msg(chat_id, USAGE, keyboard=CUSTOM_KEYBOARD)

def cmd_broadcast(chat_id, text):
    u"""cmd_broadcast: 봇이 활성화된 모든 채팅에 메시지 방송
    chat_id: (integer) 채팅 ID
    text:    (string)  방송할 메시지
    """
    send_msg(chat_id, u'메시지를 방송합니다.', keyboard=CUSTOM_KEYBOARD)
    broadcast(chat_id, text)

def cmd_echo(chat_id, text, reply_to):
    u"""cmd_echo: 사용자의 메시지를 따라서 답장
    chat_id:  (integer) 채팅 ID
    text:     (string)  사용자가 보낸 메시지 내용
    reply_to: (integer) 답장할 메시지 ID
    """
    send_msg(chat_id, text, reply_to=reply_to)

#def cmd_midas_check_dinner(chat_id, text, )
# http://erp.midasit.com/main_food_ok.asp?c_date=2016-08-04&c_code=nykim&OX=X
def ask_dinner():
    d = datetime.today().replace(tzinfo=utc)
    d = d.astimezone(tz=TimeZoneOffset(9, "KST")).date();
    day = d.weekday()
    logging.info(d.isoformat())
    logging.info(day)

    if day == 5 or day == 6: # Sat. or Sun.
        return
    
    msg = u'아름다운 밤입니다. 오늘(' + d.isoformat() + u') 저녁식사 하실건가요?' + MSG_BOT_POSTFIX
    if day == 4: # Fri.
        d = d + timedelta(days=1)
        msg = u'즐거운 불금입니다. 내일-토요일(' + d.isoformat() + u') 점심식사 하실건가요?' + MSG_BOT_POSTFIX

    for chat in get_enabled_chats():
        send_msg(chat.key.string_id(), msg, keyboard = CUSTOM_KEYBOARD_YESNO)
        NDB_SerivceEnableStatus.status = STATUS_DINNER

def process_dinner(chat_id, text):
    # http://erp.midasit.com/main_food_ok.asp?c_date=2016-08-09&c_code=nykim&OX=X
    data = {}
    #d = date.today()
    d = datetime.today().replace(tzinfo=utc)
    d = d.astimezone(tz=TimeZoneOffset(9, "KST")).date();
    data['c_date'] = d.isoformat()
    if d.weekday() == 4: # Fri.
        d = d + timedelta(days=1)
        data['c_date'] = d.isoformat()
    logging.info(NDB_Account.id)
    account = NDB_Account.get_by_id(str(chat_id))
    logging.info(account)
    data['c_code'] = account.id

    if SELECT_DINNER_EAT == text:
        data['OX'] = 'X'
    elif SELECT_DINNER_NOT == text:
        data['OX'] = 'O'
    else:
        data['OX'] = 'X'
    url = 'http://erp.midasit.com/main_food_ok.asp?'
    url_values = urllib.urlencode(data)
    full_url = url + url_values

    logging.info(full_url)
    urllib2.urlopen(full_url)
    NDB_SerivceEnableStatus.status = STATUS_IDLE
    send_msg(chat_id, u'식수체크 ㄳㄳ' + MSG_BOT_POSTFIX, keyboard = CUSTOM_KEYBOARD)

def process_cmds(msg):
    u"""사용자 메시지를 분석해 봇 명령을 처리
    chat_id: (integer) 채팅 ID
    text:    (string)  사용자가 보낸 메시지 내용
    """
    msg_id = msg['message_id']
    chat_id = msg['chat']['id']
    text = msg.get('text')

    if (not text):
        return
    if (NDB_SerivceEnableStatus.status == STATUS_DINNER and 
            (SELECT_DINNER_EAT == text or SELECT_DINNER_NOT == text)):
        process_dinner(chat_id, text)
        return
    if CMD_TEST == text:
        test_func(msg)
        return
    if CMD_QUERY_ID == text:
        queryAccount(chat_id)
        return
    if CMD_START == text:
        cmd_start(chat_id)
        return
    if (not get_enabled(chat_id)):
        return
    if CMD_STOP == text:
        cmd_stop(chat_id)
        return
    if CMD_HELP == text:
        cmd_help(chat_id)
        return
    cmd_broadcast_match = re.match('^' + CMD_BROADCAST + ' (.*)', text)
    cmd_broadcast_shortcut_match = re.match('^' + CMD_BROADCAST_SHORTCUT + ' (.*)', text)
    if cmd_broadcast_match:
        cmd_broadcast(chat_id, cmd_broadcast_match.group(1))
        return
    if cmd_broadcast_shortcut_match:
        cmd_broadcast(chat_id, cmd_broadcast_shortcut_match.group(1))
        return

    cmd_register_match = re.match('^' + CMD_REGISTER_ID + ' (.*)', text)
    cmd_query_match = re.match('^' + CMD_QUERY_ID + ' (.*)', text)
    if cmd_register_match:
        registerAccount(chat_id, cmd_register_match.group(1))
        return
    if cmd_query_match:
        queryAccount(chat_id)
        return 
    cmd_echo(chat_id, text, reply_to=msg_id)
    return

# 웹 요청에 대한 핸들러 정의
# /me 요청시
class MeHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getMe'))))

# /updates 요청시
class GetUpdatesHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getUpdates'))))

# /set-wehook 요청시
class SetWebhookHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        url = self.request.get('url')
        if url:
            self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'setWebhook', urllib.urlencode({'url': url})))))

# /webhook 요청시 (텔레그램 봇 API)
class WebhookHandler(webapp2.RequestHandler):
    def post(self):
        urlfetch.set_default_fetch_deadline(60)
        body = json.loads(self.request.body)

        logging.info(self.request)
        #logging.debug('This is a debug message')
        #logging.info('This is an info message')
        #logging.warning('This is a warning message')
        #logging.error('This is an error message')
        #logging.critical('This is a critical message')
        logging.info(body)

        self.response.write(json.dumps(body))
        if 'message' in body:
            process_cmds(body['message'])

class DinnerHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        logging.info(self.request)
        ask_dinner()

class MainPage(webapp2.RequestHandler):
    def get(self):
        #self.response.headers['Content-Type'] = 'text/plain'
        self.response.write('Hello Google App Engine World!')

# 구글 앱 엔진에 웹 요청 핸들러 지정
app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/me', MeHandler),
    ('/updates', GetUpdatesHandler),
    ('/set-webhook', SetWebhookHandler),
    ('/webhook', WebhookHandler),
    ('/dinner', DinnerHandler),
], debug=True)

