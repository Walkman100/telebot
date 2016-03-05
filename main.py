import StringIO
import json
import logging
import random
import urllib
import urllib2

# for sending images
from PIL import Image
import multipart

# roman numerals: https://github.com/Walkman100/NumeralConverter/blob/master/Python27/numeralconverter.py
import numeralconverter

# standard app engine imports
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
import webapp2

TOKEN = '183074970:<REDACTED>'

BASE_URL = 'https://api.telegram.org/bot' + TOKEN + '/'

# ================================

class EnableStatus(ndb.Model):
    # key name: str(chat_id)
    enabled = ndb.BooleanProperty(indexed=False, default=False)

class UnknownCommandStatus(ndb.Model):
    # key name: str(chat_id)
    enabled = ndb.BooleanProperty(indexed=False, default=False)

class MessageList(ndb.Model):
    # key name: str(chat_id)
    message = ndb.StringProperty(indexed=False, default="")
    # TextProperty is "unlimited length" (https://cloud.google.com/appengine/docs/python/ndb/properties#types)

# ================================

def setEnabled(chat_id, yes):
    es = EnableStatus.get_or_insert(str(chat_id))
    es.enabled = yes
    es.put()

def getEnabled(chat_id):
    es = EnableStatus.get_by_id(str(chat_id))
    if es:
        return es.enabled
    return False

def setUnknownCommandEnabled(chat_id, yes):
    es = UnknownCommandStatus.get_or_insert(str(chat_id))
    es.enabled = yes
    es.put()

def getUnknownCommandEnabled(chat_id):
    es = UnknownCommandStatus.get_by_id(str(chat_id))
    if es:
        return es.enabled
    return True

def setMessage(chat_id, message):
    es = MessageList.get_or_insert(str(chat_id))
    es.message = message
    es.put()

def getMessage(chat_id):
    es = MessageList.get_by_id(str(chat_id))
    if es:
        return es.message
    return ""

# ================================

class MeHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getMe'))))


class GetUpdatesHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getUpdates'))))


class SetWebhookHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        url = self.request.get('url')
        if url:
            self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'setWebhook', urllib.urlencode({'url': url})))))


class WebhookHandler(webapp2.RequestHandler):
    def post(self):
        urlfetch.set_default_fetch_deadline(60)
        body = json.loads(self.request.body)
        logging.info('request body: ' + str(body))
        self.response.write(json.dumps(body))
        
        update_id = body['update_id']
        try:
            message = body['message']
        except:
            message = body['edited_message']
        message_id = message.get('message_id')
        date = message.get('date')
        text = message.get('text')
        fr = message.get('from')
        chat = message['chat']
        chat_id = chat['id']
        
        if not text:
            logging.info('no text')
            return
        else:
            logging.info('received message: ' + text + ', from ' + fr['first_name'])
        
        def reply(msg=None, img=None):
            if msg:
                resp = urllib2.urlopen(BASE_URL + 'sendMessage', urllib.urlencode({
                    'chat_id': str(chat_id),
                    'text': msg.encode('utf-8'),
                    'parse_mode': 'Markdown',
                    'disable_web_page_preview': 'true',
                    'reply_to_message_id': str(message_id),
                })).read()
            elif img:
                resp = multipart.post_multipart(BASE_URL + 'sendPhoto', [
                    ('chat_id', str(chat_id)),
                    ('reply_to_message_id', str(message_id)),
                ], [
                    ('photo', 'image.jpg', img),
                ])
            else:
                logging.error('no msg or img specified')
                resp = None

            logging.info('send response: ' + str(resp))
        
        def reply_html(msg=None, img=None):
            # exactly the same as reply() but parse it as html
            if msg:
                resp = urllib2.urlopen(BASE_URL + 'sendMessage', urllib.urlencode({
                    'chat_id': str(chat_id),
                    'text': msg.encode('utf-8'),
                    'parse_mode': 'HTML',
                    'disable_web_page_preview': 'true',
                    'reply_to_message_id': str(message_id),
                })).read()
            elif img:
                resp = multipart.post_multipart(BASE_URL + 'sendPhoto', [
                    ('chat_id', str(chat_id)),
                ], [
                    ('photo', 'image.jpg', img),
                ])
            else:
                logging.error('no msg or img specified')
                resp = None

            logging.info('send response: ' + str(resp))
        
        def send_message(msg=None, img=None):
            # exactly the same as reply() but no reply_to_message_id parameter
            if msg:
                resp = urllib2.urlopen(BASE_URL + 'sendMessage', urllib.urlencode({
                    'chat_id': str(chat_id),
                    'text': msg.encode('utf-8'),
                    'parse_mode': 'Markdown',
                    'disable_web_page_preview': 'true',
                })).read()
            elif img:
                resp = multipart.post_multipart(BASE_URL + 'sendPhoto', [
                    ('chat_id', str(chat_id)),
                ], [
                    ('photo', 'image.jpg', img),
                ])
            else:
                logging.error('no msg or img specified')
                resp = None

            logging.info('send response: ' + str(resp))
        
        admins = [61311478, 83416231]
        def isSudo():
            if fr['id'] in admins:
                return True
            return False
        
        # COMMANDS BELOW
        
        if text.endswith('@WalkmanBot'): text = text[:-11]
        if text.lower() == '/start':
            reply('Bot *enabled* in this chat: /help for commands')
            setEnabled(chat_id, True)
        elif getEnabled(chat_id):
            if text.startswith('/'):
                if text.lower() == '/stop':
                    reply('Bot *disabled* in this chat: /start to re-enable')
                    setEnabled(chat_id, False)
                elif text.lower() == '/ucs':
                    if isSudo():
                        if getUnknownCommandEnabled(chat_id):
                            setUnknownCommandEnabled(chat_id, False)
                            reply('unknown command messages disabled')
                        else:
                            setUnknownCommandEnabled(chat_id, True)
                            reply('unknown command messages enabled')
                    else:
                        reply('You are not an admin!')
                elif text.lower() == '/about':
                    reply('based on `telebot` created by yukuku ([source](https://github.com/yukuku/telebot)).\nThis version by @Walkman100 ([source](https://github.com/Walkman100/telebot))')
                elif text.lower() == '/help':
                    helpText = '*Available commands*'
                    helpText = helpText + '\n/start - Enables bot in this chat'
                    helpText = helpText + '\n/stop - Disables bot responses in this chat: bot won\'t respond to anything except /start'
                    helpText = helpText + '\n/about - Show version info'
                    helpText = helpText + '\n/help - Show this help'
                    helpText = helpText + '\n/getChatID - Show this chat\'s ID'
                    helpText = helpText + '\n/getUserID - Show your UserID'
                    helpText = helpText + '\n/image - Send a "randomly" generated image'
                    helpText = helpText + '\n`/echo <text>` - Respond with `text`. Supports markdown'
                    helpText = helpText + '\n`/shout <text>` - Shout `text` in caps'
                    helpText = helpText + '\n`/curl <url>` - Return the contents of `url` (Warning: reply could be very long!)'
                    helpText = helpText + '\n`/r2a <roman numerals>` - Convert Roman Numerals to Arabic numbers'
                    helpText = helpText + '\n`/a2r <arabic number>` - Convert Arabic numbers to Roman Numerals'
                    helpText = helpText + '\n\n*Custom Message* (Coming Soon)'
                    helpText = helpText + '\n`/msgset <text>` - sets the custom message to `text`'
                    helpText = helpText + '\n`/msgadd <text>` - adds `text` to the end'
                    helpText = helpText + '\n`/msginsert <index> <text>` - inserts `text` at the specified `index`'
                    helpText = helpText + '\n`/msgremove <count>` - removes `count` characters'
                    helpText = helpText + '\n/msg [text] - send the custom message with `text` on the end'
                    # helpText = helpText + '\n/'
                    send_message(helpText)
                elif text.lower() == '/image':
                    img = Image.new('RGB', (512, 512))
                    base = random.randint(0, 16777216)
                    pixels = [base+i*j for i in range(512) for j in range(512)]  # generate sample image
                    img.putdata(pixels)
                    output = StringIO.StringIO()
                    img.save(output, 'JPEG')
                    reply(img=output.getvalue())
                elif text.lower() == '/getchatid':
                    reply(str(chat_id))
                elif text.lower() == '/getuserid':
                    reply(str(fr['id']))
                elif text.lower() == '/echo':
                    reply('Usage: /echo <text>')
                elif text.lower().startswith('/echo'):
                    text = text[5:]
                    if text.startswith('@WalkmanBot'): text = text[11:]
                    if text.startswith(' '): text = text[1:]
                    send_message(text)
                elif text.lower() == '/shout':
                    reply('Usage: /shout <text>')
                elif text.lower().startswith('/shout'):
                    text = text[6:]
                    if text.startswith('@WalkmanBot'): text = text[11:]
                    if text.startswith(' '): text = text[1:]
                    text = text.upper()
                    
                    shoutTxt = '<code>'
                    for letter in text:
                        shoutTxt = shoutTxt + letter + ' '
                    
                    text = text[1:]
                    for letter in text:
                        shoutTxt = shoutTxt + '\n' + letter
                    shoutTxt = shoutTxt + '</code>'
                    
                    try:
                        reply_html(str(shoutTxt))
                    except UnicodeEncodeError, err:
                        reply('ERROR: `' + str(err) + '`\n\nThis error is usually caused by copying and pasting unsupported Unicode characters.')
                    except urllib2.HTTPError, err:
                        logging.info('ERROR: ' + str(err))
                        reply('ERROR: `' + str(err) + '`\n\nSorry no <tags> ' + u'\U0001f61e')
                elif text.lower() == '/curl':
                    reply('Usage: /curl <url>')
                elif text.lower().startswith('/curl'):
                    text = text[5:]
                    if text.startswith('@WalkmanBot'): text = text[11:]
                    if text.startswith(' '): text = text[1:]
                    send_message('Downloading...')
                    try:
                        back = urllib2.urlopen(text).read()
                        reply('`' + str(back) + '`')
                    except urllib2.HTTPError, err:
                        logging.info('ERROR: ' + str(err))
                        reply('ERROR: ' + str(err))
                    except UnicodeDecodeError, err:
                        logging.info('ERROR: ' + str(err))
                        reply('ERROR: ' + str(err))
                    except ValueError, err:
                        logging.info('ERROR: ' + str(err))
                        reply('ERROR: ' + str(err))
                elif text.lower() == '/r2a':
                    reply('Usage: /r2a <roman numerals>')
                elif text.lower().startswith('/r2a'):
                    text = text[4:]
                    if text.startswith('@WalkmanBot'): text = text[11:]
                    if text.startswith(' '): text = text[1:]
                    try:
                        reply(numeralconverter.returnArabicNumber(text))
                    except urllib2.HTTPError, err:
                        logging.info('ERROR: ' + str(err))
                        reply('ERROR: ' + str(err))
                elif text.lower() == '/a2r':
                    reply('Usage: /a2r <arabic number>')
                elif text.lower().startswith('/a2r'):
                    text = text[4:]
                    if text.startswith('@WalkmanBot'): text = text[11:]
                    if text.startswith(' '): text = text[1:]
                    try:
                        reply(numeralconverter.checkAndReturnRomanNumeral(text))
                    except urllib2.HTTPError, err:
                        logging.info('ERROR: ' + str(err))
                        reply('ERROR: ' + str(err))
                elif text.lower().startswith('/msgset'):
                    text = text[7:]
                    if text.startswith('@WalkmanBot'): text = text[11:]
                    if text.startswith(' '): text = text[1:]
                    setMessage(chat_id, text)
                    reply('Custom Message set to "' + text + '"')
                elif text.lower().startswith('/msgadd'):
                    text = text[7:]
                    if text.startswith('@WalkmanBot'): text = text[11:]
                    if text.startswith(' '): text = text[1:]
                    text = getMessage(chat_id) + text
                    setMessage(chat_id, text)
                    reply('Custom Message set to "' + text + '"')
                elif text.lower().startswith('/msginsert'):
                    text = text[10:]
                    if text.startswith('@WalkmanBot'): text = text[11:]
                    if text.startswith(' '): text = text[1:]
                    
                    indexOfTheIndex = 0
                    try:
                        indexOfTheIndex = text.index(' ')
                    except ValueError, err:
                        reply('Space seperating index and text not found!')
                        return
                    
                    index = 0
                    if numeralconverter.is_number(text[:indexOfTheIndex]):
                        index = int(text[:indexOfTheIndex])
                        text = text[indexOfTheIndex + 1:]
                    else:
                        reply('"' + text[:indexOfTheIndex] + '" isn\'t a number!')
                        return
                    
                    # now we have the index to insert to in `index`, and the text to insert at the index in `text`
                    text = getMessage(chat_id)[:index] + text + getMessage(chat_id)[index:]
                    setMessage(chat_id, text)
                    reply('Custom Message set to "' + text + '"')
                elif getUnknownCommandEnabled(chat_id):
                    reply('Unknown command `' + text + '`. Use /help to see existing commands')
            
            elif 'what time' in text:
                reply('look at the corner of your screen!')
            else:
                pass
                #reply('I got your message! (but I do not know how to answer)')
        else:
            logging.info('not enabled for chat_id {}'.format(chat_id))


app = webapp2.WSGIApplication([
    ('/me', MeHandler),
    ('/updates', GetUpdatesHandler),
    ('/set_webhook', SetWebhookHandler),
    ('/webhook', WebhookHandler),
], debug=True)
