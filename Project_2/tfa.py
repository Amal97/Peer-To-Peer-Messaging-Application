import base64
import hmac
import time
import os, os.path
import struct
import hashlib

# Creates a new random code
def newSecret():
    return base64.b32encode(os.urandom(10))


# Makes the link for the QR code
def getQRLink(name, secret):
    url = "https://www.google.com/chart?chs=200x200&chld=M|0&cht=qr&chl=otpauth://totp/{0}-{1}%3Fsecret%3D{2}".format(
        name, "myApp", secret)
    return url

# Checks if the code is the correct one
def auth(secret, num):
    int(num)
    tm = int(time.time() / 30)
    secret = base64.b32decode(secret)
    for ix in [-1, 0, 1]:
        bytes = struct.pack(">q", tm + ix)
        hm = hmac.HMAC(secret, bytes, hashlib.sha1).digest()
        offset = ord(hm[-1]) & 0x0F
        truncatedHash = hm[offset:offset + 4]
        code = struct.unpack(">L", truncatedHash)[0]
        code &= 0x7FFFFFFF;
        code %= 1000000;
        if ("%06d" % code) == num:
            return True
    return False

