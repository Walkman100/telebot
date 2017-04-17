#!/usr/bin/python
# coding: utf-8
import StringIO
import json
import logging
import random
import urllib
import urllib2
import sys # for catch-all error reporting

# for sending images
from PIL import Image
import multipart

# roman numerals: https://github.com/Walkman100/NumeralConverter/blob/master/Python27/numeralconverter.py
import numeralconverter

# standard app engine imports
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
import webapp2

TOKEN = "183074970:<REDACTED>"

BASE_URL = "https://api.telegram.org/bot" + TOKEN + "/"

# ================================

class UnknownCommandStatus(ndb.Model):
    # key name: str(chat_id)
    enabled = ndb.BooleanProperty(indexed=False, default=False)

class MessageList(ndb.Model):
    # key name: str(chat_id)
    message = ndb.StringProperty(indexed=False, default="")
    # TextProperty is "unlimited length" (https://cloud.google.com/appengine/docs/python/ndb/properties#types)

class LastActionList(ndb.Model):
    # key name: str(fr["id"])
    lastAction = ndb.StringProperty(indexed=False, default="none")

# ================================

def setUnknownCommandEnabled(chat_id, yes):
    ucs = UnknownCommandStatus.get_or_insert(str(chat_id))
    ucs.enabled = yes
    ucs.put()

def getUnknownCommandEnabled(chat_id):
    ucs = UnknownCommandStatus.get_by_id(str(chat_id))
    if ucs:
        return ucs.enabled
    return True

def setMessage(chat_id, message):
    ml = MessageList.get_or_insert(str(chat_id))
    ml.message = message
    ml.put()

def getMessage(chat_id):
    ml = MessageList.get_by_id(str(chat_id))
    if ml:
        return ml.message
    return ""

def setLastAction(user_id, action):
    la = LastActionList.get_or_insert(user_id)
    la.lastAction = action
    la.put()

def getLastAction(user_id):
    la = LastActionList.get_by_id(user_id)
    if la:
        return la.lastAction
    return "none"

# ================================

class MeHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + "getMe"))))


class GetUpdatesHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + "getUpdates"))))


class SetWebhookHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        url = self.request.get("url")
        if url:
            self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + "setWebhook", urllib.urlencode({"url": url})))))


class WebhookHandler(webapp2.RequestHandler):
    def post(self):
        urlfetch.set_default_fetch_deadline(60)
        body = json.loads(self.request.body)
        logging.info("request body: " + str(body))
        self.response.write(json.dumps(body))
        
        update_id = body["update_id"]
        try:
            message = body["message"]
        except:
            try:
                message = body["edited_message"]
            except: # empty edits
                return
        message_id = message.get("message_id")
        date = message.get("date")
        text = message.get("text")
        fr = message.get("from")
        chat = message["chat"]
        chat_id = chat["id"]
        
        if not text:
            logging.info("no text")
            return
        else:
            logging.info("received message: " + text + ", from " + fr["first_name"])
        
        def reply(msg=None, img=None):
            try:
                if msg:
                    resp = urllib2.urlopen(BASE_URL + "sendMessage", urllib.urlencode({
                        "chat_id": str(chat_id),
                        "text": msg.encode("utf-8"),
                        "parse_mode": "Markdown",
                        "disable_web_page_preview": "true",
                        "reply_to_message_id": str(message_id),
                    })).read()
                elif img:
                    resp = multipart.post_multipart(BASE_URL + "sendPhoto", [
                        ("chat_id", str(chat_id)),
                        ("reply_to_message_id", str(message_id)),
                    ], [
                        ("photo", "image.jpg", img),
                    ])
                else:
                    logging.error("no msg or img specified")
                    resp = None

                logging.info("send response: " + str(resp))
            except:
                logging.info("Error responding with " + msg)
                reply("Error responding!\nType: `" + str(sys.exc_info()[0]) + "`\nValue: `" + str(sys.exc_info()[1]) + "`")
        
        def reply_html(msg=None, img=None): # exactly the same as reply() but parse it as html
            try:
                if msg:
                    resp = urllib2.urlopen(BASE_URL + "sendMessage", urllib.urlencode({
                        "chat_id": str(chat_id),
                        "text": msg.encode("utf-8"),
                        "parse_mode": "HTML",
                        "disable_web_page_preview": "true",
                        "reply_to_message_id": str(message_id),
                    })).read()
                elif img:
                    resp = multipart.post_multipart(BASE_URL + "sendPhoto", [
                        ("chat_id", str(chat_id)),
                    ], [
                        ("photo", "image.jpg", img),
                    ])
                else:
                    logging.error("no msg or img specified")
                    resp = None

                logging.info("send response: " + str(resp))
            except:
                logging.info("Error responding with " + msg)
                reply("Error responding!\nType: `" + str(sys.exc_info()[0]) + "`\nValue: `" + str(sys.exc_info()[1]) + "`")
        
        def send_message(msg=None, img=None): # exactly the same as reply() but no reply_to_message_id parameter
            try:
                if msg:
                    resp = urllib2.urlopen(BASE_URL + "sendMessage", urllib.urlencode({
                        "chat_id": str(chat_id),
                        "text": msg.encode("utf-8"),
                        "parse_mode": "Markdown",
                        "disable_web_page_preview": "true",
                    })).read()
                elif img:
                    resp = multipart.post_multipart(BASE_URL + "sendPhoto", [
                        ("chat_id", str(chat_id)),
                    ], [
                        ("photo", "image.jpg", img),
                    ])
                else:
                    logging.error("no msg or img specified")
                    resp = None

                logging.info("send response: " + str(resp))
            except:
                logging.info("Error responding with " + msg)
                reply("Error responding!\nType: `" + str(sys.exc_info()[0]) + "`\nValue: `" + str(sys.exc_info()[1]) + "`")
        
        def send_chat_action(action): # https://core.telegram.org/bots/api#sendchataction
            resp = urllib2.urlopen(BASE_URL + "sendChatAction", urllib.urlencode({
                "chat_id": str(chat_id),
                "action": str(action),
            })).read()
            
            logging.info("send_chat_action response: " + str(resp))
        
        def get_chat_administrators():
            resp = urllib2.urlopen(BASE_URL + "getChatAdministrators", urllib.urlencode({
                "chat_id": str(chat_id)
            })).read()
            
            chatAdmins = json.loads(resp)["result"]
            return chatAdmins
        
        def isChatAdmin():
            if chat["type"] == "private":
                return True
            
            chatAdmins = get_chat_administrators()
            AdminIDs = []
            i = 0
            try:
                while True:
                    AdminIDs.append(chatAdmins[i].get("user").get("id"))
                    i += 1
            except:
                pass
            if fr["id"] in AdminIDs:
                return True
            return False
        
        botAdmins = [61311478, 83416231]
        def isBotAdmin():
            if fr["id"] in botAdmins:
                return True
            return False
        
        # Clean end of text
        if text.lower().endswith("@walkmanbot"): text = text[:-11]
        if text.endswith(" "): text = text[:-1]
        # Seperate command and text
        if text.startswith("/") or text.startswith("#") or text.startswith("!"): text = text[1:]
        try:
            commandIndex = text.index(" ")
            command = text[:commandIndex]
            text = text[commandIndex + 1:]
            command = command.lower()
            if command.endswith("@walkmanbot"): command = command[:-11]
        except ValueError:
            command = ""
        # Clean start of text
        if text.startswith(" "): text = text[1:]
        if text.lower().startswith("@walkmanbot"): text = text[11:]
        if text.startswith(" "): text = text[1:]
        # COMMANDS BELOW
        def processCommands(command, text):
            if command == "start":
                reply("Use /help for commands")
            elif command == "ucs":
                if isBotAdmin():
                    if getUnknownCommandEnabled(chat_id):
                        setUnknownCommandEnabled(chat_id, False)
                        reply("unknown command messages disabled")
                    else:
                        setUnknownCommandEnabled(chat_id, True)
                        reply("unknown command messages enabled")
                else:
                    reply("You are not an admin!")
            elif command == "about":
                reply("based on `telebot` created by yukuku ([source](https://github.com/yukuku/telebot)).\nThis version by @Walkman100 ([source](https://github.com/Walkman100/telebot))")
            elif command == "info":
                infoText = "*Telegram Command input info:* After typing `/`:"
                infoText += "\nDesktop (Windows, Linux & Mac QT Client):\n- Use the arrow keys or your mouse to highlight a command"
                infoText += "\n- Use `Tab` to insert it into the input box"
                infoText += "\nMobile (Official Android Client & forks):\n- Scroll to a command"
                infoText += "\n- Tap-and-hold on it to insert it into the input box"
                reply(infoText)
            elif command == "help":
                helpText = "*Available commands*"
                helpText += "\n/about - Show version info"
                helpText += "\n/help - Show this help"
                helpText += "\n/whoAmI - Get ID's and info about the user"
                helpText += "\n/image - Send a 'randomly' generated image"
                helpText += "\n`/echo <text>` - Respond with `text`, supports markdown"
                helpText += "\n`/recho <text>` - Respond with `text` reversed"
                helpText += "\n`/uecho <text>` - Respond with `text` encoded with Unicode, format is \u2211"
                helpText += "\n`/shout <text>` - Shout `text` in caps"
                helpText += "\n`/curl <url>` - Return the contents of `url` (Warning: reply could be very long!)"
                helpText += "\n`/r2a <roman numerals>` - Convert Roman Numerals to Arabic numbers"
                helpText += "\n`/a2r <arabic number>` - Convert Arabic numbers to Roman Numerals"
                helpText += "\n`/roll <number of die>d<sides of die>` - Return `number of die` amount of random numbers from 1 to `sides of die`"
                helpText += "\n`/randbetween <start> <end>` - Sends a random number between `start` and `end`"
                helpText += "\n`/calc <expression>` - evaluates `expression`"
                helpText += "\n\n*Custom Message*"
                helpText += "\n`/msgset <text>` - sets the custom message to `text`"
                helpText += "\n`/msgadd <text>` - adds `text` to the end"
                helpText += "\n`/msginsert <index> <text>` - inserts `text` at the specified `index`"
                helpText += "\n`/msgremove <count>` - removes `count` characters from the end"
                helpText += "\n/msg <text> - send the custom message with `text` on the end"
                helpText += "\n/mymsg <text> - send the custom message set in private chat with `text` on the end"
                # helpText += "\n/"
                send_message(helpText)
            elif command == "image":
                send_chat_action("upload_photo")
                img = Image.new("RGB", (512, 512))
                base = random.randint(0, 16777216)
                pixels = [base+i*j for i in range(512) for j in range(512)]  # generate sample image
                img.putdata(pixels)
                output = StringIO.StringIO()
                img.save(output, "JPEG")
                reply(img=output.getvalue())
            elif command == "whoami":
                replystring = "You are <code>"
                try:
                    replystring += fr["first_name"] + "</code> "
                except KeyError:
                    pass
                
                try:
                    replystring += "(first) <code>" + fr["last_name"] + "</code> (last) "
                except KeyError:
                    pass
                
                try:
                    replystring += "(@" + fr["username"] + ") "
                except KeyError:
                    pass
                
                replystring += "with an ID of <code>" + str(fr["id"]) + "</code>, chatting in a " + chat["type"]
                try:
                    replystring += " chat called <code>" + chat["title"] + "</code> "
                except KeyError:
                    replystring += " chat "
                
                replystring += "with ID <code>" + str(chat_id) + "</code>."
                try:
                    reply_html(replystring)
                except urllib2.HTTPError, err:
                    reply("HTTPError: " + str(err))
            elif command == "uecho" and text == "":
                if chat["type"] == "private":
                    setLastAction(str(fr["id"]), command)
                    reply("Enter text to encode:")
                else:
                    reply("Usage: `/uecho <unicode sequence>`")
            elif command == "uecho":
                if text.count("\\") == 0: text = "\\" + text
                try:
                    send_message(text.decode("unicode-escape"))
                except UnicodeEncodeError, err:
                    reply("ERROR: `" + str(err) + "`\n\nDon't use unicode! (But this message can be used to find the sequence of unicode characters)")
                except UnicodeDecodeError, err:
                    reply("`" + text + "` contains an invalid unicode character sequence!\n`" + str(err) + '`')
                except urllib2.HTTPError, err:
                    reply("ERROR: `" + str(err) + "`")
                except:
                    reply("Caught unexpected error!\nType: `" + str(sys.exc_info()[0]) + "`\nValue: `" + str(sys.exc_info()[1]) + "`")
            elif command == "echoid":
                if isBotAdmin():
                    if not text.startswith("-"):
                        text = "-" + text
                    indexOfID = 0
                    try:
                        indexOfID = text.index(" ")
                    except ValueError:
                        reply("Space separating ID and text not found!")
                        return

                    chat_id2 = 0
                    if numeralconverter.is_number(text[:indexOfID]):
                        chat_id2 = int(text[:indexOfID])
                        text = text[indexOfID + 1:]
                    else:
                        reply("'" + text[:indexOfID] + "' isn't a number!")
                        return

                    try:
                        resp = urllib2.urlopen(BASE_URL + "sendMessage", urllib.urlencode({
                            "chat_id": str(chat_id2),
                            "text": text.encode("utf-8"),
                            "parse_mode": "Markdown",
                            "disable_web_page_preview": "true",
                        })).read()

                        logging.info("send response: " + str(resp))
                    except:
                        reply("Error sending message to " + str(chat_id2) + "!\nType: `" + str(sys.exc_info()[0]) + "`\nValue: `" + str(sys.exc_info()[1]) + "`")
                else:
                    reply("You are not an admin!")
            elif command in ["echo", "recho", "shout"] and text == "":
                if chat["type"] == "private":
                    setLastAction(str(fr["id"]), command)
                    reply("Enter text:")
                else:
                    reply("Usage: `/" + command + " <text>`")
            elif command == "echo":
                send_message(text)
            elif command == "recho":
                revTxt = ""
                for letter in text:
                    revTxt = letter + revTxt
                send_message(revTxt)
            elif command == "shout":
                text = text.upper()
                text = text[:20] # truncate text so message can't be ridiculously long

                shoutTxt = "<code>"
                for letter in text:
                    shoutTxt += letter + " "

                text = text[1:]
                seperator = " "
                for letter in text:
                    shoutTxt += "\n" + letter + seperator + letter
                    seperator += "  " # 3D-ness
                shoutTxt = shoutTxt + "</code>"

                try:
                    reply_html(shoutTxt)
                except urllib2.HTTPError, err:
                    reply("ERROR: `" + str(err) + "`\n\nSorry no <tags> " + u"\U0001f61e")
            elif command == "curl" and text == "":
                if chat["type"] == "private":
                    setLastAction(str(fr["id"]), command)
                    reply("Enter url:")
                else:
                    reply("Usage: `/curl <url>`")
            elif command == "curl":
                send_chat_action("upload_document")
                try:
                    back = urllib2.urlopen(text).read()
                    reply("`" + back + "`")
                except urllib2.HTTPError, err:
                    reply("HTTPError: `" + str(err) + "`")
                except urllib2.URLError, err:
                    reply("URLError: `" + str(err) + "`")
                except ValueError, err:
                    reply("ValueError: `" + str(err) + "`")
                except UnicodeDecodeError, err:
                    reply("UnicodeDecodeError: `" + str(err) + "`")
                except:
                    reply("Couldn't resolve `" + text + "`!\n`" + str(sys.exc_info()[1]) + "`")
            elif command == "r2a" and text == "":
                if chat["type"] == "private":
                    setLastAction(str(fr["id"]), command)
                    reply("Enter roman numerals:")
                else:
                    reply("Usage: `/r2a <roman numerals>`")
            elif command == "r2a":
                try:
                    reply(numeralconverter.returnArabicNumber(text))
                except urllib2.HTTPError, err:
                    reply("ERROR: `" + str(err) + "`")
            elif command == "a2r" and text == "":
                if chat["type"] == "private":
                    setLastAction(str(fr["id"]), command)
                    reply("Enter arabic number:")
                else:
                    reply("Usage: `/a2r <arabic number>`")
            elif command == "a2r":
                try:
                    reply(numeralconverter.checkAndReturnRomanNumeral(text))
                except urllib2.HTTPError, err:
                    reply("ERROR: `" + str(err) + "`")
            elif command == "roll" and text == "":
                if chat["type"] == "private":
                    setLastAction(str(fr["id"]), command)
                    reply("Enter <number of die>d<sides of die>:")
                else:
                    reply("Usage: `/roll <number of die>d<sides of die>`")
            elif command == "roll":
                sendText = ""
                inputArgs = text.split("d")

                if len(inputArgs) <> 2:
                    reply("`" + text + "` does not contain one `d`!")
                    return

                if inputArgs[0] == "":
                    inputArgs[0] = "1"
                if numeralconverter.is_number(inputArgs[0]) and numeralconverter.is_number(inputArgs[1]):
                    i = 0
                    while i < int(inputArgs[0]):
                        sendText += "\n" + str(random.randint(1, int(inputArgs[1])))
                        i += 1
                    reply(sendText)
                else:
                    reply("Either `" + inputArgs[0] + "` or `" + inputArgs[1] + "` isn't a number!")
            elif command == "randbetween":
                #randbetween 5 10
                inputArgs = text.split(" ")

                if len(inputArgs) <> 2:
                    reply("`" + text + "` does not contain one space!")
                    return

                if numeralconverter.is_number(inputArgs[0]) and numeralconverter.is_number(inputArgs[1]):
                    try:
                        reply(str(random.randint(int(inputArgs[0]), int(inputArgs[1]))))
                    except ValueError, err:
                        reply("ERROR: `" + str(err) + "`\n`random.randint()` doesn't seem to be able to go backwards " + u"\U0001f61e")
                else:
                    reply("Either `" + inputArgs[0] + "` or `" + inputArgs[1] + "` isn't a number!")
            elif command == "calc" and text == "":
                if chat["type"] == "private":
                    setLastAction(str(fr["id"]), command)
                    reply("Enter expression:")
                else:
                    reply("Usage: `/calc <expression>`")
            elif command == "calc":
                try:
                    reply(str(eval(text)))
                except:
                    reply("Caught unexpected error!\nType: `" + str(sys.exc_info()[0]) + "`\nValue: `" + str(sys.exc_info()[1]) + "`")
            elif command == "msgset":
                setMessage(chat_id, text)
                reply("Custom Message set to `" + text + "`")
            elif command == "msgadd":
                text = getMessage(chat_id) + text
                setMessage(chat_id, text)
                reply("Custom Message set to `" + text + "`")
            elif command == "msginsert":
                indexOfTheIndex = 0
                try:
                    indexOfTheIndex = text.index(" ")
                except ValueError:
                    reply("Space separating index and text not found!")
                    return
                
                index = 0
                if numeralconverter.is_number(text[:indexOfTheIndex]):
                    index = int(text[:indexOfTheIndex])
                    text = text[indexOfTheIndex + 1:]
                else:
                    reply("'" + text[:indexOfTheIndex] + "' isn't a number!")
                    return
                
                # now we have the index to insert to in `index`, and the text to insert at the index in `text`
                text = getMessage(chat_id)[:index] + text + getMessage(chat_id)[index:]
                setMessage(chat_id, text)
                reply("Custom Message set to `" + text + "`")
            elif command == "msgremove":
                if numeralconverter.is_number(text):
                    index = int(text)
                    text = getMessage(chat_id)
                    text = text[: len(text) - index]
                    setMessage(chat_id, text)
                    reply("Custom Message set to `" + text + "`")
                else:
                    reply("'" + text + "' isn't a number!")
            elif command == "msg":
                if text == "":
                    text = getMessage(chat_id)
                else:
                    text = getMessage(chat_id) + " " + text
                if text == "":
                    reply("Custom message hasn't been set, use `/msgset <text>` to set it")
                else:
                    reply(text)
            elif command == "mymsg":
                if text == "":
                    text = getMessage(str(fr["id"]))
                else:
                    text = getMessage(str(fr["id"])) + " " + text
                if text == "":
                    reply("Custom message hasn't been set, use `/msgset <text>` in private chat (@WalkmanBot) to set it")
                else:
                    reply(text)
            elif chat["type"] == "private" and getLastAction(str(fr["id"])) <> "none":
                processCommands(getLastAction(str(fr["id"])), command + " " + text)
            elif getUnknownCommandEnabled(chat_id):
                reply("Unknown command `" + command + "`. Use /help to see existing commands")

        if command <> "":
            processCommands(command, text)
        else:
            processCommands(text.lower(), "")

app = webapp2.WSGIApplication([
    ("/me", MeHandler),
    ("/updates", GetUpdatesHandler),
    ("/set_webhook", SetWebhookHandler),
    ("/webhook", WebhookHandler),
], debug=True)
