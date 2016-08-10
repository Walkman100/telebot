#!/usr/bin/python
# coding: utf-8
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

# ================================

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
            message = body["edited_message"]
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
        
        def reply_html(msg=None, img=None):
            # exactly the same as reply() but parse it as html
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
        
        def send_message(msg=None, img=None):
            # exactly the same as reply() but no reply_to_message_id parameter
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
        
        admins = [61311478, 83416231]
        def isSudo():
            if fr["id"] in admins:
                return True
            return False
        
        # Clean up text variable
        if text.lower().endswith("@walkmanbot"): text = text[:-11]
        if text.endswith(" "): text = text[:-1]
        if text.startswith("/"): text = text[1:]

        # COMMANDS BELOW
        if text.lower() == "start":
            reply("Use /help for commands")
        elif text.lower() == "ucs":
            if isSudo():
                if getUnknownCommandEnabled(chat_id):
                    setUnknownCommandEnabled(chat_id, False)
                    reply("unknown command messages disabled")
                else:
                    setUnknownCommandEnabled(chat_id, True)
                    reply("unknown command messages enabled")
            else:
                reply("You are not an admin!")
        elif text.lower() == "about":
            reply("based on `telebot` created by yukuku ([source](https://github.com/yukuku/telebot)).\nThis version by @Walkman100 ([source](https://github.com/Walkman100/telebot))")
        elif text.lower() == "info":
            infoText = "*Telegram Command input info:* After typing `/`:"
            infoText += "\nDesktop (Windows, Linux & Mac QT Client):\n- Use the arrow keys or your mouse to highlight a command"
            infoText += "\n- Use `Tab` to insert it into the input box"
            infoText += "\nMobile (Official Android Client & forks):\n- Scroll to a command"
            infoText += "\n- Tap-and-hold on it to insert it into the input box"
            reply(infoText)
        elif text.lower() == "help":
            helpText = "*Available commands*"
            helpText += "\n/about - Show version info"
            helpText += "\n/help - Show this help"
            helpText += "\n/whoAmI - Get ID's and info about the user"
            helpText += "\n/image - Send a \"randomly\" generated image"
            helpText += "\n`/echo <text>` - Respond with `text`, supports markdown"
            helpText += "\n`/uecho <text>` - Respond with `text` encoded with Unicode, format is \u2211"
            helpText += "\n`/shout <text>` - Shout `text` in caps"
            helpText += "\n`/curl <url>` - Return the contents of `url` (Warning: reply could be very long!)"
            helpText += "\n`/r2a <roman numerals>` - Convert Roman Numerals to Arabic numbers"
            helpText += "\n`/a2r <arabic number>` - Convert Arabic numbers to Roman Numerals"
            helpText += "\n\n*Custom Message*"
            helpText += "\n`/msgset <text>` - sets the custom message to `text`"
            helpText += "\n`/msgadd <text>` - adds `text` to the end"
            helpText += "\n`/msginsert <index> <text>` - inserts `text` at the specified `index`"
            helpText += "\n`/msgremove <count>` - removes `count` characters from the end"
            helpText += "\n/msg <text> - send the custom message with `text` on the end"
            # helpText += "\n/"
            send_message(helpText)
        elif text.lower() == "image":
            img = Image.new("RGB", (512, 512))
            base = random.randint(0, 16777216)
            pixels = [base+i*j for i in range(512) for j in range(512)]  # generate sample image
            img.putdata(pixels)
            output = StringIO.StringIO()
            img.save(output, "JPEG")
            reply(img=output.getvalue())
        elif text.lower() == "whoami":
            replystring = "You are <code>"
            try:
                replystring += fr["first_name"] + "</code> "
            except KeyError, err:
                pass
            
            try:
                replystring += "(first) <code>" + fr["last_name"] + "</code> (last) "
            except KeyError, err:
                pass
            
            try:
                replystring += "(@" + fr["username"] + ") "
            except KeyError, err:
                pass
            
            replystring += "with an ID of <code>" + str(fr["id"]) + "</code>, chatting in a " + chat["type"]
            try:
                replystring += " chat called <code>" + chat["title"] + "</code> "
            except KeyError, err:
                replystring += " chat "
            
            replystring += "with ID <code>" + str(chat_id) + "</code>."
            try:
                reply_html(replystring)
            except urllib2.HTTPError, err:
                reply("HTTPError: " + str(err))
        elif text.lower() == "echo":
            reply("Usage: `/echo <text>`")
        elif text.lower().startswith("echo"):
            text = text[4:]
            if text.startswith("@WalkmanBot"): text = text[11:]
            if text.startswith(" "): text = text[1:]
            send_message(text)
        elif text.lower() == "uecho":
            reply("Usage: `/uecho <unicode sequence>`")
        elif text.lower().startswith("uecho"):
            text = text[5:]
            if text.startswith("@WalkmanBot"): text = text[11:]
            if text.startswith(" "): text = text[1:]
            if text.count("\\") == 0: text = "\\" + text
            try:
                send_message(text.decode("unicode-escape"))
            except UnicodeEncodeError, err:
                reply("ERROR: `" + str(err) + "`\n\nDon't use unicode! (But this message can be used to find the sequence of unicode characters)")
            except UnicodeDecodeError, err:
                reply("`" + text + "` contains an invalid unicode character sequence!")
            except urllib2.HTTPError, err:
                reply("ERROR: `" + str(err) + "`")
        elif text.lower() == "shout":
            reply("Usage: `/shout <text>`")
        elif text.lower().startswith("shout"):
            text = text[5:]
            if text.startswith("@WalkmanBot"): text = text[11:]
            if text.startswith(" "): text = text[1:]
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
        elif text.lower() == "curl":
            reply("Usage: `/curl <url>`")
        elif text.lower().startswith("curl"):
            text = text[4:]
            if text.startswith("@WalkmanBot"): text = text[11:]
            if text.startswith(" "): text = text[1:]
            send_message("Downloading...")
            try:
                back = urllib2.urlopen(text).read()
                reply("`" + back + "`")
            except urllib2.HTTPError, err:
                reply("HTTPError: `" + str(err) + "`")
            except ValueError, err:
                reply("ValueError: `" + str(err) + "`")
            except UnicodeDecodeError, err:
                reply("UnicodeDecodeError: `" + str(err) + "`")
        elif text.lower() == "r2a":
            reply("Usage: `/r2a <roman numerals>`")
        elif text.lower().startswith("r2a"):
            text = text[3:]
            if text.startswith("@WalkmanBot"): text = text[11:]
            if text.startswith(" "): text = text[1:]
            try:
                reply(numeralconverter.returnArabicNumber(text))
            except urllib2.HTTPError, err:
                reply("ERROR: `" + str(err) + "`")
        elif text.lower() == "a2r":
            reply("Usage: `/a2r <arabic number>`")
        elif text.lower().startswith("a2r"):
            text = text[3:]
            if text.startswith("@WalkmanBot"): text = text[11:]
            if text.startswith(" "): text = text[1:]
            try:
                reply(numeralconverter.checkAndReturnRomanNumeral(text))
            except urllib2.HTTPError, err:
                reply("ERROR: `" + str(err) + "`")
        elif text.lower().startswith("msgset"):
            text = text[6:]
            if text.startswith("@WalkmanBot"): text = text[11:]
            if text.startswith(" "): text = text[1:]
            setMessage(chat_id, text)
            reply("Custom Message set to `" + text + "`")
        elif text.lower().startswith("msgadd"):
            text = text[6:]
            if text.startswith("@WalkmanBot"): text = text[11:]
            if text.startswith(" "): text = text[1:]
            text = getMessage(chat_id) + text
            setMessage(chat_id, text)
            reply("Custom Message set to `" + text + "`")
        elif text.lower().startswith("msginsert"):
            text = text[9:]
            if text.startswith("@WalkmanBot"): text = text[11:]
            if text.startswith(" "): text = text[1:]
            
            indexOfTheIndex = 0
            try:
                indexOfTheIndex = text.index(" ")
            except ValueError, err:
                reply("Space seperating index and text not found!")
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
        elif text.lower().startswith("msgremove"):
            text = text[9:]
            if text.startswith("@WalkmanBot"): text = text[11:]
            if text.startswith(" "): text = text[1:]
            
            if numeralconverter.is_number(text):
                index = int(text)
                text = getMessage(chat_id)
                text = text[: len(text) - index]
                setMessage(chat_id, text)
                reply("Custom Message set to `" + text + "`")
            else:
                reply("'" + text + "' isn't a number!")
        elif text.lower().startswith("msg"):
            text = text[3:]
            if text.startswith("@WalkmanBot"): text = text[11:]
            if text.startswith(" "): text = text[1:]
            if text == "":
                text = getMessage(chat_id)
            else:
                text = getMessage(chat_id) + " " + text
            if text == "":
                reply("Custom message hasn't been set, use `/msgset <text>` to set it")
            else:
                reply(text)
        elif getUnknownCommandEnabled(chat_id):
            reply("Unknown command `" + text + "`. Use /help to see existing commands")

app = webapp2.WSGIApplication([
    ("/me", MeHandler),
    ("/updates", GetUpdatesHandler),
    ("/set_webhook", SetWebhookHandler),
    ("/webhook", WebhookHandler),
], debug=True)
