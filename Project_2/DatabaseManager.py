"""
COMPSYS 302 ASSIGNMENT
AMAL CHANDRA

This file is used to interact with the database
The functions in this file is used to create database, insert, update, delete or retrieve data to and from the database
"""


import sqlite3
import time

# Creates tables users,messages,profile,myself(users who login using the app),ratelimit in the database if not present
def createDB():
    try:
        conn = sqlite3.connect('db.db')
        c = conn.cursor()
        # Creates the Users table if it doesnt exist
        c.execute("CREATE TABLE IF NOT EXISTS Users(username TEXT NOT NULL UNIQUE,location TEXT NOT NULL,"
                  "ip TEXT NOT NULL,port TEXT NOT NULL,login_time 	TEXT NOT NULL)")

        # Creates the messages table if it doesnt exist
        c.execute("CREATE TABLE IF NOT EXISTS Messages(id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT,"
                  "destination TEXT,message TEXT,stamp TEXT,encoding TEXT,encryption TEXT,hashing TEXT,hash TEXT,"
                  "decryptionKey TEXT,groupID TEXT, file TEXT, filename TEXT, content_type TEXT, status TEXT)")

        # Creates the Profile table if it doesnt exist
        c.execute("CREATE TABLE IF NOT EXISTS Profile(username TEXT UNIQUE,fullname TEXT,position TEXT,"
                  " description TEXT,location TEXT,picture TEXT,encoding TEXT,encryption TEXT,decryptionKey TEXT,"
                  "lastUpdated TEXT)")

        # Creates the Myself table if it doesnt exist
        c.execute("CREATE TABLE IF NOT EXISTS Myself(username TEXT UNIQUE,Hashedpassword TEXT, key TEXT)")

        # Creates the RateLimit table if it doesnt exist
        c.execute("CREATE TABLE IF NOT EXISTS RateLimit(username TEXT UNIQUE,allowance INTEGER, time INTEGER)")

        conn.commit()
        c.close()
        conn.close()
        return '1'
    except sqlite3.Error:
        return '4'


# Stores the user who login in using this application in the database, along with the 2FA key
def storeMyself(username, password, key):
    conn = sqlite3.connect('db.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO Myself VALUES(?,?,?)", (username, password, key))
    conn.commit()
    c.close()
    conn.close()

# Returns the user who is logged in from the database
def getMyself(username=None):
    conn = sqlite3.connect('db.db')
    c = conn.cursor()
    if username is not None:
        c.execute("SELECT * FROM Myself WHERE username = ? ", (username,))
    else:
        c.execute("SELECT * FROM Myself")
    myself = c.fetchone()
    conn.commit()
    c.close()
    conn.close()
    return myself


# Store all the users from the login server in the database
def storeUsersinDB(allUsers):
    try:
        conn = sqlite3.connect('db.db')
        c = conn.cursor()
        # Adds all the users in the database using a loop
        for username in allUsers:
            c.execute("INSERT OR IGNORE INTO Users VALUES(?,?,?,?,?)", (username, '-', '-', '-', '-'))
        conn.commit()
        c.close()
        conn.close()
    except sqlite3.Error:
        return '4'  # Returns 4 if something goes wrong in the database


# Store online users in the database
def storeOnlineUsersInDB(onlineUsers):
    try:
        conn = sqlite3.connect('db.db')
        c = conn.cursor()
        count = 0
        c.execute("UPDATE Users SET location=?,ip=?,port=?,login_time=?", ("-", "-", "-", "-"))
        while str(count) in onlineUsers:
            c.execute("UPDATE Users SET location=?,ip=?,port=?,login_time=? WHERE username = ? ",
                      (onlineUsers[str(count)]['location'], onlineUsers[str(count)]['ip'],
                       onlineUsers[str(count)]['port'],
                       onlineUsers[str(count)]['lastLogin'], onlineUsers[str(count)]['username']))
            count = count + 1
        conn.commit()
        c.close()
        conn.close()
        return '0'
    except:
        return '4'  # Returns 4 if something goes wrong in the database


# Returns a list of online users
def getOnlineUsers():
    conn = sqlite3.connect('db.db')
    conn.text_factory = str
    c = conn.cursor()
    onlineUserList = []
    newList = []
    x = 0
    for username in c.execute("SELECT username FROM Users WHERE location = '0' or location ='1' or location = '2'"):
        onlineUserList.append(username)
        newList.append(onlineUserList[x][0])
        x = x + 1
    c.close()
    conn.close()
    return newList


# Gets the recipient users ip from the database
def getUserIP(recipient):
    conn = sqlite3.connect('db.db')
    conn.text_factory = str
    c = conn.cursor()
    c.execute("SELECT ip FROM Users WHERE username = ? ", (recipient,))
    user_ip = c.fetchone()[0]
    c.close()
    conn.close()
    return user_ip


# Gets the recipient users port from the database
def getUserPort(recipient):
    conn = sqlite3.connect('db.db')
    conn.text_factory = str
    c = conn.cursor()
    c.execute("SELECT port FROM Users WHERE username = ? ", (recipient,))
    user_port = c.fetchone()[0]
    c.close()
    conn.close()
    return user_port


# Stores messages sent to other users from the app in the database
def storeMessages(input_data):
    conn = sqlite3.connect('db.db')
    c = conn.cursor()

    c.execute("SELECT stamp FROM Messages where (message = ? and sender = ? and destination = ? and stamp = ?)"
              " ORDER BY stamp DESC",(input_data['message'],input_data['sender'],input_data['destination'], input_data['stamp']))
    data = c.fetchone()
    # Checks if the message doesnt exists in the database than add in the message (avoid duplicates)
    if data is None:
        c.execute("INSERT into Messages (stamp,message,destination,sender) values (?,?,?,?)",
              (input_data['stamp'], input_data['message'], input_data['destination'], input_data['sender']))
    conn.commit()
    c.close()
    conn.close()


# Store received messages in the database
def storeReceivedMessages(input_data):
    conn = sqlite3.connect('db.db')
    c = conn.cursor()
    c.execute("SELECT stamp FROM Messages where (message = ? and sender = ? and destination = ? and stamp = ?)"
              " ORDER BY stamp DESC", (input_data['message'], input_data['sender'], input_data['destination'],
                                       input_data['stamp']))
    data = c.fetchone()
    # Checks if the message doesnt exists in the database than add in the message (avoid duplicates)
    if data is None:
        c.execute("INSERT into Messages (stamp,message,destination,sender,status) values (?,?,?,?)",
                  (input_data['stamp'], input_data['message'], input_data['destination'], input_data['sender'],
                   "not seen"))
    conn.commit()
    c.close()
    conn.close()


# Stores sent and received files in the database
def storeFiles(input_data):
    conn = sqlite3.connect('db.db')
    c = conn.cursor()

    c.execute("SELECT stamp FROM Messages where (sender = ? and destination = ? and stamp = ?)"
              " ORDER BY stamp DESC",(input_data['sender'],input_data['destination'], input_data['stamp']))
    data = c.fetchone()
    # Checks if the message doesnt exists in the database than add in the message (avoid duplicates)
    if data is None:
        c.execute("INSERT into Messages (file,stamp,filename,content_type,destination,sender) values (?,?,?,?,?,?)",
                  (input_data['file'],input_data['stamp'],input_data['filename'],input_data['content_type'],
                   input_data['destination'], input_data['sender']))
    conn.commit()
    c.close()
    conn.close()


# Gets messages from between 2 users from the database
def getMessages(username, destination):
    conn = sqlite3.connect('db.db')
    # conn.text_factory = str
    c = conn.cursor()
    c.execute(
        "SELECT message, sender, destination, filename,content_type, stamp,hashing,hash FROM Messages where"
        " (sender = ? and destination = ?) or (sender = ? and destination = ?)"
        " ORDER BY stamp ASC", (username, destination, destination,username))
    messages = c.fetchall()
    c.close()
    conn.close()
    return messages


# This function is called set or edit profile of users in the database
def setProfile(username=None, fullname=None, position=None, description=None, location=None, picture=None,
               lastUpdated=None):
    conn = sqlite3.connect('db.db')
    c = conn.cursor()
    c.execute("SELECT username FROM Profile WHERE username = ?", (username,))
    user = c.fetchone()
    # If no picture is provided use a default one
    if not picture:
        picture = "http://media3.oakpark.com/Images/2/2/36431/2/1/2_2_36431_2_1_690x520.jpg"
    # If the profile doesnt exist than add the user's profile
    if user is None:
        c.execute(
            "INSERT into Profile(username,fullname,position,description,location,picture,lastUpdated) values(?,?,?,?,?,?,?)",
            (username, fullname, position, description, location, picture, lastUpdated))
    # If the profile does exist than update the user's profile
    else:
        c.execute("UPDATE Profile set fullname = ?,position=?,description=?,location=?,picture=?,lastUpdated=?"
                  " where username=?", (fullname, position, description, location, picture, lastUpdated, username))
    conn.commit()
    c.close()
    conn.close()


# Returns the profile of users from the database
def getProfileFromDB(profile_username):
    conn = sqlite3.connect('db.db')
    c = conn.cursor()
    c.execute("SELECT * FROM Profile WHERE username = ?", (profile_username,))
    profile = c.fetchone()
    try:
        dict = {"fullname": profile[1], "position": profile[2], "description": profile[3], "location": profile[4],
                "picture": profile[5], "lastUpdated": profile[9]}
    except TypeError:
        return '1'
    conn.commit()
    c.close()
    conn.close()
    return dict

# Adds all the users in the RateLimiting table
def addRatelimit(allUsers):
    try:
        conn = sqlite3.connect('db.db')
        c = conn.cursor()
        for username in allUsers:
            c.execute("INSERT OR IGNORE INTO RateLimit VALUES(?,?,?)", (username, 0,0))
        conn.commit()
        c.close()
        conn.close()
        return '0'
    except sqlite3.Error:
        return '4'

# Gets the users rate limit information (allowance and last request) for rate limiting
def getRateLimit(username):
    conn = sqlite3.connect('db.db')
    c = conn.cursor()
    c.execute("SELECT * FROM RateLimit WHERE username = ?", (username,))
    user = c.fetchone()
    conn.commit()
    c.close()
    conn.close()
    return user

# Updates the users rate limits allowance and time
def updateRateLimit(username,allowance,time):
    conn = sqlite3.connect('db.db')
    c = conn.cursor()
    c.execute("UPDATE RateLimit set allowance=?,time=? where username=?", (allowance,time,username))
    conn.commit()
    c.close()
    conn.close()

