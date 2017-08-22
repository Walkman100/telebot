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
    # key name: str(fr.get("id"))
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
    def generateCommandDict(self):
        commandDict = []
        #keys = ['command', 'arguments', 'usage', clickable=False, has_chat_mode=False, 'chat_mode_prompt', \
        #    'moreinfo']
        # thanks to https://bytes.com/topic/python/answers/781432-how-create-list-dictionaries
        commandDict.append({"command":"about", "usage":"Show version info"})
        commandDict.append({"command":"help", "arguments":"<command>", "usage":"Show this help, or show help for <command>", "clickable": True})
        commandDict.append({"command":"whoAmI", "usage":"Get ID's and info about the user"})
        commandDict.append({"command":"echo", "arguments":"<text>", "usage":"Respond with `text`",  "has_chat_mode":True, "chat_mode_prompt":"text:", \
            "moreinfo":"Supports Telegram's limited version of Markdown, e.g. stars for bold and underscores for italics."})
        commandDict.append({"command":"recho", "arguments":"<text>", "usage":"Respond with `text` reversed", "has_chat_mode":True, "chat_mode_prompt":"text:", \
            "moreinfo":"Supports Telegram's limited version of Markdown, e.g. stars for bold and underscores for italics."})
        commandDict.append({"command":"uecho", "arguments":"<text>", "usage":"Respond with `text` encoded with Unicode", "has_chat_mode":True, "chat_mode_prompt":"text to encode:", \
            "moreinfo":"Format is \u2211 (or u2211 for a single character). Supports Telegram's limited version of Markdown, e.g. stars for bold and underscores for italics. Sending a unicode character results in an error, but can be used to find the sequence of unicode characters."})
        commandDict.append({"command":"shout", "arguments":"<text>", "usage":"Shout `text` in caps", "has_chat_mode":True, "chat_mode_prompt":"text:", \
            "moreinfo":"Sends a '3D' message of the input in caps, i.e. the input is sent across, down and diagonally. Do not use <> characters as the message is sent with HTML."})
        commandDict.append({"command":"image", "usage":"Send a 'randomly' generated image"})
        commandDict.append({"command":"getimg", "arguments":"<url>", "usage":"Return an image at `url`", "has_chat_mode":True, "chat_mode_prompt":"image url:", \
            "moreinfo":"This is retrieved with python2's urllib2.urlopen method, and seems to have a problem with ~10MB or bigger images."})
        commandDict.append({"command":"preview", "arguments":"<url>", "usage":"Get a preview image of webpage `url`", "has_chat_mode":True, "chat_mode_prompt":"page url:", \
            "moreinfo":"Generated using pagepeeker.com, which requires you request the image to be generated, then send a second request once it has been generated in order to get the image."})
        commandDict.append({"command":"expand", "arguments":"<url>", "usage":"Get expanded version of `url` using goo.gl/IGL1lE", "has_chat_mode":True, "chat_mode_prompt":"short url:", \
            "moreinfo":"unshorten.me doesn't take anything after a ? through the API, go to the service directly in order to expand those URLs."})
        commandDict.append({"command":"curl", "arguments":"<url>", "usage":"Return contents of `url` (Warning: reply could be very long!)", "has_chat_mode":True, "chat_mode_prompt":"url:", \
            "moreinfo":"Most errors occur from unicode characters in the source."})
        commandDict.append({"command":"r2a", "arguments":"<roman numerals>", "usage":"Convert Roman Numerals to Arabic numbers", "has_chat_mode":True, "chat_mode_prompt":"roman numerals:"})
        commandDict.append({"command":"a2r", "arguments":"<arabic number>", "usage":"Convert Arabic numbers to Roman Numerals", "has_chat_mode":True, "chat_mode_prompt":"arabic number:"})
        commandDict.append({"command":"roll", "arguments":"<number of die>d<sides of die>", "usage":"Return `number of die` amount of random numbers from 1 to `sides of die`", "has_chat_mode":True, "chat_mode_prompt":"<number of die>d<sides of die>:", \
            "moreinfo":"Accepts input as d<sides of die> to roll 1 die"})
        commandDict.append({"command":"randbetween", "arguments":"<start> <end>", "usage":"Sends a random number between `start` and `end`", "has_chat_mode":True, "chat_mode_prompt":"<start> <end>:", \
            "moreinfo":"Entering numbers in reverse order errors (e.g. 50 20). Solution: enter numbers the other way around."})
        commandDict.append({"command":"calc", "arguments":"<expression>", "usage":"evaluates `expression`", "has_chat_mode":True, "chat_mode_prompt":"expression:", \
            "moreinfo":"Since the bot runs python, this uses python operators to run calculations, in the form of `<number> <operator> <number>` - operators can be any of +/-/\*, and also:\n" + \
            "Divide (true): /\nDivide (floor): //\nModulus Division: %\nExponent: \*\*\nConcatenation: +\n" + \
            "You can also use this function to call random functions in the bots code, see the last link in /about, e.g. `/calc (str(reply_noreply('1')) + str(reply_noreply('2')) + str(reply_noreply('3')) + str(reply_noreply('4')) + str(reply_noreply('5')))[20:] + '6'`"})
        #commandDict.append({"command":"", "arguments":"", "usage":"", "moreinfo":"", "has_chat_mode":True, "chat_mode_prompt":""})
        
        return commandDict
    
    def post(self):
        urlfetch.set_default_fetch_deadline(60)
        body = json.loads(self.request.body)
        
        logging.info("request body: " + str(body))
        self.response.write(json.dumps(body))
        update_id = body.get("update_id")
        message   = body.get("message")
        if not message: message = body.get("edited_message")
        if not message: return
        
        message_id = message.get("message_id")
        date       = message.get("date")
        fr         = message.get("from")
        chat       = message.get("chat")
        chat_id    =    chat.get("id")
        text       = message.get("text")
        if not text: text = message.get("caption")
        if not text:
            logging.info("no text")
            return
        else:
            logging.info("received message: " + text + ", from " + fr.get("first_name"))
        
        def reply(msg=None, img=None, parse_mode="Markdown", disable_web_page_preview="true"):
            try:
                if msg:
                    resp = urllib2.urlopen(BASE_URL + "sendMessage", urllib.urlencode({
                        "chat_id": str(chat_id),
                        "text": msg.encode("utf-8"),
                        "parse_mode": parse_mode,
                        "disable_web_page_preview": disable_web_page_preview,
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
        
        def reply_noreply(msg=None, img=None, parse_mode="Markdown", disable_web_page_preview="true"): # exactly the same as reply() but no reply_to_message_id parameter
            try:
                if msg:
                    resp = urllib2.urlopen(BASE_URL + "sendMessage", urllib.urlencode({
                        "chat_id": str(chat_id),
                        "text": msg.encode("utf-8"),
                        "parse_mode": parse_mode,
                        "disable_web_page_preview": disable_web_page_preview,
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
            
            return json.loads(resp).get("result")
        
        def isChatAdmin():
            if chat.get("type") == "private":
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
            if fr.get("id") in AdminIDs:
                return True
            return False
        
        botAdmins = [61311478, 83416231]
        def isBotAdmin():
            if fr.get("id") in botAdmins:
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
            command = text.lower()
            text = ""
        # Clean start of text
        if text.startswith(" "): text = text[1:]
        if text.lower().startswith("@walkmanbot"): text = text[11:]
        if text.startswith(" "): text = text[1:]
        # COMMANDS BELOW
        def processCommands(command, text, chat_id):
            # This actually comes up, believe it or not
            if text.startswith(" "): text = text[1:]
            if text.endswith(" "): text = text[:-1]
            
            # Ignored Input
            if command in ["s", "r"]:
                pass
            if command.startswith("r/"):
                pass
            
            # Usage
            elif command == "help" and text =="":
                helpText = "*Available commands*"
                # apparently because it's not global it needs to be called explicitly
                # http://i0.kym-cdn.com/photos/images/newsfeed/000/187/270/1318822944910.jpg
                for command in WebhookHandler(self).generateCommandDict():
                    helpText += "\n"
                    if command.get("arguments"):
                        if command.get("clickable") == True:
                            helpText += "/" + command.get("command") +" "+ command.get("arguments") + " - " + command.get("usage")
                        else:
                            helpText += "`/" + command.get("command") +" "+ command.get("arguments") + "` - " + command.get("usage")
                    else:
                        helpText += "/" + command.get("command") + " - " + command.get("usage")
                
                helpText += "\n\n*Custom Message*"
                helpText += "\n`/msgset <text>` - sets the custom message to `text`"
                helpText += "\n`/msgadd <text>` - adds `text` to the end"
                helpText += "\n`/msginsert <index> <text>` - inserts `text` at the specified `index`"
                helpText += "\n`/msgremove <count>` - removes `count` characters from the end"
                helpText += "\n/msg <text> - send the custom message with `text` on the end, start with " + u'\xa7' + " for HTML instead of markdown"
                helpText += "\n/mymsg <text> - send the custom message set in private chat with `text` on the end"
                # helpText += "\n/"
                reply_noreply(helpText)
            elif command == "help":
                for command in WebhookHandler(self).generateCommandDict():
                    if text == command.get("command"):
                        text = "Usage: "
                        
                        if command.get("arguments"):
                            if command.get("clickable") == True:
                                text += "/" + command.get("command") +" "+ command.get("arguments")
                            else:
                                text += "`/" + command.get("command") +" "+ command.get("arguments") + "`"
                        else:
                            text += "/" + command.get("command")
                        
                        text += " - " + command.get("usage")
                        if command.get("moreinfo"):
                            text += "\n\n" + command.get("moreinfo")
                        
                        reply(text)
                        return
                reply("Command `" + text + "` not found!")
            elif command == "generatecommandlist":
                text = "info - Quick Command info: On Mobile, scroll to a command and Tap-and-Hold to insert. On Desktop, use the arrow keys to highlight a command and Tab to insert."
                for command in WebhookHandler(self).generateCommandDict():
                    text += "\n"
                    if command.get("command") == "help":
                        text += "help - <command> - Show available commands, or show help for <command>"
                        continue
                    
                    if command.get("arguments"):
                        text += command.get("command").lower() + " - " + command.get("arguments") + " - " + command.get("usage")
                    else:
                        text += command.get("command").lower() + " - " + command.get("usage")
                text += "\nmsg - <text> - send the custom message with <text> on the end\nmymsg - <text> - send the custom message set in private chat with <text> on the end\nmsgset - <text> - sets the custom message to <text>\nmsgadd - <text> - adds <text> to the end\nmsginsert - <index> <text> - inserts <text> at the specified <index>\nmsgremove - <count> - removes <count> characters from the end"
                reply(text)
            elif command in ["echo", "recho", "shout"] and text == "":
                if chat.get("type") == "private":
                    setLastAction(str(fr["id"]), command)
                    reply("Enter text:")
                else:
                    reply("Usage: `/" + command + " <text>`")
            elif command == "uecho" and text == "":
                if chat.get("type") == "private":
                    setLastAction(str(fr["id"]), command)
                    reply("Enter text to encode:")
                else:
                    reply("Usage: `/uecho <unicode sequence>`")
            elif command == "getimg" and text == "":
                if chat.get("type") == "private":
                    setLastAction(str(fr["id"]), command)
                    reply("Enter image url:")
                else:
                    reply("Usage: `/getimg <url>`")
            elif command == "preview" and text == "":
                if chat.get("type") == "private":
                    setLastAction(str(fr["id"]), command)
                    reply("Enter page url:")
                else:
                    reply("Usage: `/preview <url>`")
            elif command == "expand" and text == "":
                if chat.get("type") == "private":
                    setLastAction(str(fr["id"]), command)
                    reply("Enter short url:")
                else:
                    reply("Usage: `/expand <url>`")
            elif command == "curl" and text == "":
                if chat.get("type") == "private":
                    setLastAction(str(fr["id"]), command)
                    reply("Enter url:")
                else:
                    reply("Usage: `/curl <url>`")
            elif command == "r2a" and text == "":
                if chat.get("type") == "private":
                    setLastAction(str(fr["id"]), command)
                    reply("Enter roman numerals:")
                else:
                    reply("Usage: `/r2a <roman numerals>`")
            elif command == "a2r" and text == "":
                if chat.get("type") == "private":
                    setLastAction(str(fr["id"]), command)
                    reply("Enter arabic number:")
                else:
                    reply("Usage: `/a2r <arabic number>`")
            elif command == "roll" and text == "":
                if chat.get("type") == "private":
                    setLastAction(str(fr["id"]), command)
                    reply("Enter <number of die>d<sides of die>:")
                else:
                    reply("Usage: `/roll <number of die>d<sides of die>`")
            elif command == "randbetween" and text == "":
                if chat.get("type") == "private":
                    setLastAction(str(fr["id"]), command)
                    reply("Enter <start> <end>:")
                else:
                    reply("Usage: `/randbetween <start> <end>`")
            elif command == "calc" and text == "":
                if chat.get("type") == "private":
                    setLastAction(str(fr["id"]), command)
                    reply("Enter expression:")
                else:
                    reply("Usage: `/calc <expression>`")
            
            # Simple response (no computation)
            elif command == "start":
                reply("Use /help for commands")
            elif command == "about":
                reply("based on `telebot` created by yukuku ([source](https://github.com/yukuku/telebot)).\nThis version by @Walkman100 ([source](https://github.com/Walkman100/telebot))")
            elif command == "info":
                infoText = "*Telegram Command input info:* After typing `/`:"
                infoText += "\nDesktop (Windows, Linux & Mac QT Client):\n- Use the arrow keys or your mouse to highlight a command"
                infoText += "\n- Use `Tab` to insert it into the input box"
                infoText += "\nMobile (Official Android Client & forks):\n- Scroll to a command"
                infoText += "\n- Tap-and-hold on it to insert it into the input box"
                reply(infoText)
            elif command == "echo":
                reply_noreply(text)
            
            # No NDB Modification
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
                
                replystring += "with an ID of <code>" + str(fr.get("id")) + "</code>, chatting in a " + str(chat.get("type"))
                try:
                    replystring += " chat called <code>" + chat["title"] + "</code> "
                except KeyError:
                    replystring += " chat "
                
                replystring += "with ID <code>" + str(chat_id) + "</code>."
                if isBotAdmin() and isChatAdmin():
                    replystring += " You are a Bot Admin and a Chat Admin."
                elif isBotAdmin():
                    replystring += " You are a Bot Admin."
                elif isChatAdmin():
                    replystring += " You are a Chat Admin."
                
                try:
                    reply(replystring, parse_mode="HTML")
                except urllib2.HTTPError, err:
                    reply("HTTPError: " + str(err))
            elif command == "recho":
                revTxt = ""
                for letter in text:
                    revTxt = letter + revTxt
                reply_noreply(revTxt)
            elif command == "uecho":
                if text.count("\\") == 0: text = "\\" + text
                try:
                    reply_noreply(text.decode("unicode-escape"))
                except UnicodeEncodeError, err:
                    reply("ERROR: `" + str(err) + "`\n\nDon't use unicode! (But this message can be used to find the sequence of unicode characters)")
                except UnicodeDecodeError, err:
                    reply("`" + text + "` contains an invalid unicode character sequence!\n`" + str(err) + '`')
                except urllib2.HTTPError, err:
                    reply("ERROR: `" + str(err) + "`")
                except:
                    reply("Caught error!\nType: `" + str(sys.exc_info()[0]) + "`\nValue: `" + str(sys.exc_info()[1]) + "`")
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
                    reply(shoutTxt, parse_mode="HTML")
                except urllib2.HTTPError, err:
                    reply("ERROR: `" + str(err) + "`\n\nSorry no <tags> " + u"\U0001f61e")
            elif command == "expand":
                send_chat_action("typing")
                try:
                    jsonResp = json.loads(urllib2.urlopen("https://unshorten.me/json/" + text).read())
                    
                    if jsonResp.get("success") == True:
                        reply(jsonResp.get("resolved_url"), parse_mode="HTML", disable_web_page_preview="false")
                    elif jsonResp.get("success") == False:
                        reply("There was an error expanding `" + jsonResp.get("requested_url") + "`: " + jsonResp.get("error"))
                    else:
                        reply("`" + str(jsonResp) + "`")
                except urllib2.HTTPError, err:
                    reply("HTTPError: `" + str(err) + "`")
                except urllib2.URLError, err:
                    reply("URLError: `" + str(err) + "`")
                except ValueError, err:
                    reply("ValueError: `" + str(err) + "`")
                except TypeError, err:
                    reply("TypeError: `" + str(err) + "`")
                except UnicodeDecodeError, err:
                    reply("UnicodeDecodeError: `" + str(err) + "`")
                except:
                    reply("Couldn't resolve `" + text + "`!\n`" + str(sys.exc_info()[1]) + "`")
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
            elif command == "r2a":
                try:
                    reply(numeralconverter.returnArabicNumber(text))
                except urllib2.HTTPError, err:
                    reply("ERROR: `" + str(err) + "`")
            elif command == "a2r":
                try:
                    reply(numeralconverter.checkAndReturnRomanNumeral(text))
                except urllib2.HTTPError, err:
                    reply("ERROR: `" + str(err) + "`")
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
            elif command == "calc":
                try:
                    reply(str(eval(text)))
                except:
                    reply("Caught error!\nType: `" + str(sys.exc_info()[0]) + "`\nValue: `" + str(sys.exc_info()[1]) + "`")
            
            # Admin commands
            elif command == "echoid":
                if isBotAdmin():
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
                    reply("You are not a Bot Admin!")
            elif command == "runas":
                if isBotAdmin():
                    if not text.startswith("-"):
                        text = "-" + text
                    indexOfID = 0
                    try:
                        indexOfID = text.index(" ")
                    except ValueError:
                        reply("Space separating ID and text not found!")
                        return
                    
                    if numeralconverter.is_number(text[:indexOfID]):
                        chat_id = int(text[:indexOfID])
                        text = text[indexOfID + 1:]
                    else:
                        reply("'" + text[:indexOfID] + "' isn't a number!")
                        return
                    
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
                    
                    if command <> "":
                        processCommands(command, text, chat_id)
                    else:
                        processCommands(text.lower(), "", chat_id)
            
            # NDB modifying
            elif command == "ucs":
                if isBotAdmin() or isChatAdmin():
                    if getUnknownCommandEnabled(chat_id):
                        setUnknownCommandEnabled(chat_id, False)
                        reply("unknown command messages disabled")
                    else:
                        setUnknownCommandEnabled(chat_id, True)
                        reply("unknown command messages enabled")
                else:
                    reply("You are not a bot or chat admin!")
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
                elif text.startswith(u'\xa7'):
                    reply(text[1:], parse_mode="HTML") # [1:] is to remove the §
                else:
                    reply(text)
            elif command == "mymsg":
                if text == "":
                    text = getMessage(str(fr["id"]))
                else:
                    text = getMessage(str(fr["id"])) + " " + text
                if text == "":
                    reply("Custom message hasn't been set, use `/msgset <text>` in private chat (@WalkmanBot) to set it")
                elif text.startswith(u'\xa7'):
                    reply(text[1:], parse_mode="HTML")
                else:
                    reply(text)
            
            # Media
            elif command == "image":
                send_chat_action("upload_photo")
                img = Image.new("RGB", (512, 512))
                base = random.randint(0, 16777216)
                pixels = [base+i*j for i in range(512) for j in range(512)]  # generate sample image
                img.putdata(pixels)
                output = StringIO.StringIO()
                img.save(output, "JPEG")
                reply(img=output.getvalue())
            elif command == "getimg":
                send_chat_action("upload_photo")
                try:
                    reply(img=urllib2.urlopen(text).read())
                except urllib2.HTTPError, err:
                    reply("HTTPError: `" + str(err) + "`")
                except urllib2.URLError, err:
                    reply("URLError: `" + str(err) + "`")
                except ValueError, err:
                    reply("ValueError: `" + str(err) + "`")
                except TypeError, err:
                    reply("TypeError: `" + str(err) + "`")
                except UnicodeDecodeError, err:
                    reply("UnicodeDecodeError: `" + str(err) + "`")
                except:
                    reply("Couldn't get/upload an image at `" + text + "`!\nErrorType: `" + str(sys.exc_info()[0]) + "`\nValue: `" + str(sys.exc_info()[1]) + "`")
            elif command == "preview":
                send_chat_action("upload_photo")
                try:
                    imgURL = "http://free.pagepeeker.com/v2/thumbs.php?size=x&url=" + text
                    checkURL = "http://free.pagepeeker.com/v2/thumbs_ready.php?size=x&url=" + text
                    
                    jsonResp = json.loads(urllib2.urlopen(checkURL).read())
                    
                    if jsonResp.get("IsReady") == 1:
                        reply(img=urllib2.urlopen(imgURL).read())
                    elif jsonResp.get("IsReady") == 0:
                        reply("Preview not generated yet. Please wait ~1min and try again")
                    elif jsonResp.get("Error") <> None:
                        reply("There was an error generating the preview: " + jsonResp.get("Error"))
                    else:
                        reply("`" + str(jsonResp) + "`")
                    
                except urllib2.HTTPError, err:
                    reply("HTTPError: `" + str(err) + "`")
                except urllib2.URLError, err:
                    reply("URLError: `" + str(err) + "`")
                except ValueError, err:
                    reply(str(urllib2.urlopen(checkURL).read())[:-47] + "\n(<code>" + str(err) + "</code>)", parse_mode="HTML")
                except TypeError, err:
                    reply("TypeError: `" + str(err) + "`")
                except UnicodeDecodeError, err:
                    reply("UnicodeDecodeError: `" + str(err) + "`")
                except:
                    reply("Couldn't get/upload an image at `" + imgURL + "`!\nErrorType: `" + str(sys.exc_info()[0]) + "`\nValue: `" + str(sys.exc_info()[1]) + "`")
            
            # Private Chat talk mode & unknown commands
            elif chat.get("type") == "private" and getLastAction(str(fr.get("id"))) <> "none":
                processCommands( getLastAction(str(fr.get("id"))), command + " " + text, chat_id )
            elif getUnknownCommandEnabled(chat_id):
                if "fuck off" in (command + " " + text).lower() or "shut the fuck up" in (command + " " + text).lower():
                    reply("Use /ucs to turn off Unknown Command messages")
                else:
                    reply("Unknown command `" + command + "`. Use /help to see existing commands")
        
        processCommands(command, text, chat_id)
        
        #except:
            #reply("Caught error!\nType: `" + str(sys.exc_info()[0]) + "`\nValue: `" + str(sys.exc_info()[1]) + "`")

app = webapp2.WSGIApplication([
    ("/me", MeHandler),
    ("/updates", GetUpdatesHandler),
    ("/set_webhook", SetWebhookHandler),
    ("/webhook", WebhookHandler),
], debug=True)
