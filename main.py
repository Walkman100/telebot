import StringIO
import json
import logging
import random
import urllib
import urllib2

# for sending images
from PIL import Image
import multipart

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
            logging.info('received message: ' + text + ', from ' + message['from'].get('first_name'))
        
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
        
        def send_message_html(msg=None, img=None):
            # exactly the same as reply() but no reply_to_message_id parameter
            if msg:
                resp = urllib2.urlopen(BASE_URL + 'sendMessage', urllib.urlencode({
                    'chat_id': str(chat_id),
                    'text': msg.encode('utf-8'),
                    'parse_mode': 'HTML',
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
        
        # COMMANDS BELOW
        
        if text.startswith('/'):
            if text.endswith('@WalkmanBot'): text = text[:-11]
            if text == '/start':
                reply('SimSimi responses *enabled* in this chat: /help for other commands')
                setEnabled(chat_id, True)
            elif text == '/stop':
                reply('SimSimi responses *disabled* in this chat')
                setEnabled(chat_id, False)
            elif text == '/about':
                reply('telebot created by yukuku ([source](https://github.com/yukuku/telebot))\nThis version by @Walkman100 ([source](https://github.com/Walkman100/telebot))')
            elif text == '/help':
                helpText = '*Available commands*'
                helpText = helpText + '\n/start - Enables SimSimi responses in this chat'
                helpText = helpText + '\n/stop - Disables SimSimi responses in this chat'
                helpText = helpText + '\n/about - Show version info'
                helpText = helpText + '\n/help - Show this help'
                helpText = helpText + '\n/getChatId - Show this chat\'s ID'
                helpText = helpText + '\n/echo <text> - Respond with <text>. Supports markdown'
                helpText = helpText + '\n/shout <text> - Shout <text> in caps'
                helpText = helpText + '\n/image - Send a randomly generated image'
                send_message(helpText)
            elif text == '/image':
                img = Image.new('RGB', (512, 512))
                base = random.randint(0, 16777216)
                pixels = [base+i*j for i in range(512) for j in range(512)]  # generate sample image
                img.putdata(pixels)
                output = StringIO.StringIO()
                img.save(output, 'JPEG')
                reply(img=output.getvalue())
            elif text == '/getChatId':
                reply(str(chat_id))
            elif text == '/getchatid':
                reply(str(chat_id))
            elif text == '/echo':
                reply('Usage: /echo\t<text>')
            elif text.startswith('/echo'):
                send_message(text[5:])
            elif text == '/shout':
                reply('Usage: /shout\t<text>')
            elif text.startswith('/shout'):
                text = text[6:]
                if text.startswith('@WalkmanBot'): text = text[11:]
                text = text.upper()
                shoutTxt = '<code>'
                for letter in text:
                    shoutTxt = shoutTxt + letter + ' '
                text = text[2:]
                for letter in text:
                    shoutTxt = shoutTxt + '\n' + letter
                shoutTxt = shoutTxt + '</code>'
                send_message_html(str(shoutTxt))
            else:
                reply('Unknown command `' + text + '`. Use /help to see existing commands')
        
        # elif 'who are you' in text:
        #     reply('')
        elif 'what time' in text:
            reply('look at the corner of your screen!')
        else:
            if getEnabled(chat_id):
                reply('I got your message! (but I do not know how to answer)')
            else:
                logging.info('not enabled for chat_id {}'.format(chat_id))


app = webapp2.WSGIApplication([
    ('/me', MeHandler),
    ('/updates', GetUpdatesHandler),
    ('/set_webhook', SetWebhookHandler),
    ('/webhook', WebhookHandler),
], debug=True)
