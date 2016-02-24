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

class UnknownCommandStatus(ndb.Model):
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

def setUnknownCommandEnabled(chat_id, yes):
    es = UnknownCommandStatus.get_or_insert(str(chat_id))
    es.enabled = yes
    es.put()

def getUnknownCommandEnabled(chat_id):
    es = UnknownCommandStatus.get_by_id(str(chat_id))
    if es:
        return es.enabled
    return True

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
        
        def is_number(s):
            try:
                float(s)
                return True
            except ValueError:
                return False
        # https://github.com/Walkman100/NumeralConverter/blob/17fe334fb34088fbd7c7c25ef31fba5df8961512/Python27/numeralconverter.py#L68
        def checkAndOutputRomanNumeral(input):
            if is_number(input):
                if len(input) < 19:
                    outputRomanNumeral(int(input))
                else:
                    reply("\"" + input + "\" is " + (len(input) - 18 + " digit(s) too long! Maximum size for \"//\" operations is 18 digits"))
            else:
                reply("\"" + input + "\" is not an Arabic number!")
        def outputRomanNumeral(number):
            returnString = ""
            if number > 1000:
                for i in range(1, (number // 1000) +1):
                    returnString = returnString + "M"
                number = number - (number // 1000) * 1000
            while number > 900:
                number = number - 900
                returnString = returnString + "CM"
            
            while number > 500:
                number = number - 500
                returnString = returnString + "D"
            while number > 400:
                number = number - 400
                returnString = returnString + "CD"
            
            while number > 100:
                number = number - 100
                returnString = returnString + "C"
            while number > 90:
                number = number - 90
                returnString = returnString + "XC"
            
            while number > 50:
                number = number - 50
                returnString = returnString + "L"
            while number > 40:
                number = number - 40
                returnString = returnString + "XL"
            
            while number > 10:
                number = number - 10
                returnString = returnString + "X"
            while number > 9:
                number = number - 9
                returnString = returnString + "IX"
            
            while number > 5:
                number = number - 5
                returnString = returnString + "V"
            while number > 4:
                number = number - 4
                returnString = returnString + "IV"
            
            while number >= 1:
                number = number - 1
                returnString = returnString + "I"
            reply('`' + returnString + '`')
        def outputArabicNumber(RomanNumber):
            RomanNumber = RomanNumber.upper()
            nonvalid = ""
            for i in range(0, len(RomanNumber)):
                # https://stackoverflow.com/a/1228327/2999220
                if RomanNumber[i] == "I":   RomanNumber = RomanNumber[:i] + '1' + RomanNumber[i + 1:]
                elif RomanNumber[i] == "V": RomanNumber = RomanNumber[:i] + '2' + RomanNumber[i + 1:]
                elif RomanNumber[i] == "X": RomanNumber = RomanNumber[:i] + '3' + RomanNumber[i + 1:]
                elif RomanNumber[i] == "L": RomanNumber = RomanNumber[:i] + '4' + RomanNumber[i + 1:]
                elif RomanNumber[i] == "C": RomanNumber = RomanNumber[:i] + '5' + RomanNumber[i + 1:]
                elif RomanNumber[i] == "D": RomanNumber = RomanNumber[:i] + '6' + RomanNumber[i + 1:]
                elif RomanNumber[i] == "M": RomanNumber = RomanNumber[:i] + '7' + RomanNumber[i + 1:]
                else:
                    nonvalid = RomanNumber[i]
            if nonvalid:
                reply("\"" + nonvalid + "\" is not a valid Roman Numeral character!")
            else:
                # Now we have the roman number in arabic numbers (so we can use < and >), we just add it all
                ArabicNumber = 0
                RomanNumber = RomanNumber + "0" # Because loops, length calculation and next letter calculation
                for i in range(0, len(RomanNumber)):
                    if i < len(RomanNumber) - 1 and RomanNumber[i] >= RomanNumber[i + 1]:
                        if RomanNumber[i] == "1":   ArabicNumber = ArabicNumber + 1
                        elif RomanNumber[i] == "2": ArabicNumber = ArabicNumber + 5
                        elif RomanNumber[i] == "3": ArabicNumber = ArabicNumber + 10
                        elif RomanNumber[i] == "4": ArabicNumber = ArabicNumber + 50
                        elif RomanNumber[i] == "5": ArabicNumber = ArabicNumber + 100
                        elif RomanNumber[i] == "6": ArabicNumber = ArabicNumber + 500
                        elif RomanNumber[i] == "7": ArabicNumber = ArabicNumber + 1000
                    elif i < len(RomanNumber) - 1:
                        if RomanNumber[i] == "1":   ArabicNumber = ArabicNumber - 1
                        elif RomanNumber[i] == "2": ArabicNumber = ArabicNumber - 5
                        elif RomanNumber[i] == "3": ArabicNumber = ArabicNumber - 10
                        elif RomanNumber[i] == "4": ArabicNumber = ArabicNumber - 50
                        elif RomanNumber[i] == "5": ArabicNumber = ArabicNumber - 100
                        elif RomanNumber[i] == "6": ArabicNumber = ArabicNumber - 500
                        elif RomanNumber[i] == "7": ArabicNumber = ArabicNumber - 1000
                reply('`' + str(ArabicNumber) + '`')
        
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
                    helpText = helpText + '\n/echo <text> - Respond with <text>. Supports markdown'
                    helpText = helpText + '\n/shout <text> - Shout <text> in caps'
                    helpText = helpText + '\n/image - Send a randomly generated image'
                    helpText = helpText + '\n/curl <url> - Return the text of <url> (Warning: reply could be very long!)'
                    helpText = helpText + '\n/r2a <roman numerals> - Convert Roman Numerals to Arabic numbers'
                    helpText = helpText + '\n/a2r <arabic number> - Convert Arabic numbers to Roman Numerals'
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
                        reply('ERROR: `' + str(err) + '`\n\nIf your message contained single quotation marks (`\'`) that\'s probably the problem.')
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
                    outputArabicNumber(text)
                elif text.lower() == '/a2r':
                    reply('Usage: /a2r <arabic number>')
                elif text.lower().startswith('/a2r'):
                    text = text[4:]
                    if text.startswith('@WalkmanBot'): text = text[11:]
                    if text.startswith(' '): text = text[1:]
                    checkAndOutputRomanNumeral(text)
                
                else:
                    if getUnknownCommandEnabled(chat_id):
                        reply('Unknown command `' + text + '`. Use /help to see existing commands')
            
            elif 'what time' in text:
                reply('look at the corner of your screen!')
            else:
                reply('I got your message! (but I do not know how to answer)')
        else:
            logging.info('not enabled for chat_id {}'.format(chat_id))


app = webapp2.WSGIApplication([
    ('/me', MeHandler),
    ('/updates', GetUpdatesHandler),
    ('/set_webhook', SetWebhookHandler),
    ('/webhook', WebhookHandler),
], debug=True)
