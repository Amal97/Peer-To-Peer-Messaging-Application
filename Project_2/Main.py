#!/usr/bin/python
"""
    COMPSYS302 - Software Design
    Author: Amal Chandra

    This program uses the CherryPy web server (from www.cherrypy.org).

    This is the Main file. The Main file calls functions from the DatabaseManager, login_server and tfa. It also
    all the main and helper functions in this file

"""

# Imports of python built in and downloaded functions
import cherrypy
from jinja2 import Environment, FileSystemLoader
import os, os.path
import hashlib
import urllib2
import socket
import json
import time
import base64

# import of functions in the other files
import DatabaseManager, login_server, tfa

ip = socket.gethostbyname(socket.gethostname())
# The address we listen for connections on
listen_ip = "0.0.0.0"
listen_port = 10005

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
env = Environment(loader=FileSystemLoader(CUR_DIR),trim_blocks=True)


class MainApp(object):
    # CherryPy Configuration
    _cp_config = {'tools.encode.on': True,
                  'tools.encode.encoding': 'utf-8',
                  'tools.sessions.on': 'True',
                  'tools.sessions.timeout': 60,
                  }

    def __init__(self):
        self.isLoggedIn = False  # sets the logged in to false when the app starts
        DatabaseManager.createDB()  # creates the database
        allUsers = login_server.listUsers()  # gets all the users from the server
        DatabaseManager.storeUsersinDB(allUsers)  # stores all the users in the database
        DatabaseManager.addRatelimit(allUsers)  # sets up rate limiting allowance for all users
        cherrypy.engine.subscribe('stop', self.forceShutdown)  # logs the user off login server when cherrypy stops

    # If the user tries to go somewhere we don't know, catch it here and send them to a default place.
    @cherrypy.expose
    def default(self, *args, **kwargs):
        """The default page, given when we don't recognise where the request is for."""
        cherrypy.response.status = 404
        Page = file('default.html')
        return Page


    # PAGES (which return HTML that can be viewed in browser)
    @cherrypy.expose
    def index(self):
        raise cherrypy.HTTPRedirect('/login')

    # Page where the users can user the form in login to login to the app
    @cherrypy.expose
    def login(self):
        Page = file('login_page.html')
        return Page

    # First sign in process (communicates with the login server to verify the details)
    @cherrypy.expose
    def signin(self, username=None, password=None):
        try:
            hashedPassword = hashlib.sha256((password + username).encode('utf-8')).hexdigest()
            cherrypy.session['hashedPassword'] = hashedPassword
            error = login_server.authoriseUserLogin(username, hashedPassword,ip,listen_port)
            if error == "0, User and IP logged":
                print error
                cherrypy.session['username'] = username
                raise cherrypy.HTTPRedirect('/tfa?name='+username+'&password='+hashedPassword)
            else:
                raise cherrypy.HTTPRedirect('/login')
        except TypeError:
            raise cherrypy.HTTPRedirect('/login')

    # Geths a list of online users from the login server
    def getOnlineUsers(self):
        username = cherrypy.session.get('username')
        hashedPassword = cherrypy.session.get('hashedPassword')
        data = login_server.getList(username, hashedPassword)
        onlineUsers = self.decode_JSON(data)
        return onlineUsers

    # Home page, page where the user goes when both login server and 2FA authentication is successful
    @cherrypy.expose
    def home(self):
        try:
            if self.isLoggedIn:
                onlineUsers = self.getOnlineUsers()
                allUsers = login_server.listUsers()
                DatabaseManager.storeOnlineUsersInDB(onlineUsers)
                showOnlineUsers = DatabaseManager.getOnlineUsers()
                template = env.get_template('home.html')
                return template.render(username=cherrypy.session.get('username'),
                                       users=allUsers, onlineUsers=showOnlineUsers)
            else:
                raise cherrypy.HTTPRedirect("/login")
        except KeyError, e:
            return e
    
    # Message page, page where the users send messages to other users
    @cherrypy.expose
    def message(self, recipient=None, messageResponse="Message Status"):
        if self.isLoggedIn:
            username = cherrypy.session.get('username')
            onlineUsers = self.getOnlineUsers()
            allUsers = login_server.listUsers()
            DatabaseManager.storeOnlineUsersInDB(onlineUsers)
            showOnlineUsers = DatabaseManager.getOnlineUsers()
            messages = DatabaseManager.getMessages(username, recipient)
            template = env.get_template('message.html')
            return template.render(username=username, users=allUsers,
                                   onlineUsers=showOnlineUsers, messageList=messages,
                                   destination=recipient, messageDelivered=messageResponse)
        else:
            raise cherrypy.HTTPRedirect("/login")


    # Form to send messages to other users and redirects back to messages page
    @cherrypy.expose
    def messageForm(self,recipient=None, message=None):
        if message is not None and recipient is not None:
            response = self.sendMessage(message, recipient)
            if response == '0':
                messageResponse = "Message Delivered"
            else:
                messageResponse = "Message Not Delivered"
        else:
            messageResponse = "Message Not Delivered"
        raise cherrypy.HTTPRedirect("/message?recipient="+recipient+"&messageResponse="+messageResponse)

    # Form to send files to other users and redirects back to messages page
    @cherrypy.expose
    def fileForm(self,recipient=None,myfile=None):
        if myfile is not None and myfile.file is not None and recipient is not None:
            response = self.sendFiles(myfile, recipient)
            if '0' in response:
                messageResponse = "File Delivered"
            elif '12' in response:
                messageResponse = "File couldn't send, size too large"
            else:
                messageResponse = "File Not Delivered"
        else:
            messageResponse = "File Not Delivered"
        raise cherrypy.HTTPRedirect("/message?recipient="+recipient+"&messageResponse="+messageResponse)


    # Profile Page, page where the user can get other users profile
    @cherrypy.expose
    def profile_page(self, profile_username=None):
        try:
            if self.isLoggedIn:
                username = cherrypy.session.get('username')
                onlineUsers = self.getOnlineUsers()
                allUsers = login_server.listUsers()
                DatabaseManager.storeOnlineUsersInDB(onlineUsers)
                showOnlineUsers = DatabaseManager.getOnlineUsers()

                if profile_username is not None:
                    data = self.getProfileOnline(profile_username)
                    if data == '5' or data == '3':
                        data = DatabaseManager.getProfileFromDB(profile_username)
                else:
                    data = None
                template = env.get_template('profile.html')
                if data is not None:
                    if data["lastUpdated"] is not None:
                        updated = time.strftime("%d-%m-%Y %H:%M:%S", time.localtime(float(data["lastUpdated"])))
                    else:
                        updated = "No time given"
                    return template.render(username=username, users=login_server.listUsers(), fullname=data.get('fullname'," "),
                                       position=data.get('position'," "),
                                       description=data.get("description"," "), location=data.get("location"," "),
                                       picture=data.get("picture"," "),
                                       stamp=updated,
                                       onlineUsers=showOnlineUsers)
                else:
                    return template.render(username=username, users=allUsers, onlineUsers=showOnlineUsers)
            else:
                raise cherrypy.HTTPRedirect("/login")
        except Exception:
            return "User profile not available"


    # Page where the user can edit their profile
    @cherrypy.expose
    def edit_profile_page(self):
        if self.isLoggedIn:
            Page = file('edit_profile.html')
            return Page
        else:
            raise cherrypy.HTTPRedirect("/login")


    # decodes the JSON object to dicionary
    def decode_JSON(self, input_data_JSON):
        return json.loads(input_data_JSON)

    # encodes a dictionary to JSON
    def encode_JSON(self, input_data_dict):
        return json.dumps(input_data_dict)

    # Function to send messages to other users
    @cherrypy.expose
    def sendMessage(self, message, recipient):
        try:
            ping_result = self.getPing(recipient)
            if '0' in ping_result:
                output_dict = {"sender": cherrypy.session.get('username'),
                               "message": message,
                               "stamp": time.time(),
                               "destination": recipient}

                recipient_ip = DatabaseManager.getUserIP(recipient)
                recipient_port = DatabaseManager.getUserPort(recipient)
                url = "http://" + recipient_ip + ":" + recipient_port + "/receiveMessage"
                data = self.encode_JSON(output_dict)
                req = urllib2.Request(url, data, {'Content-Type': 'application/json'})
                try:
                    response = urllib2.urlopen(req, timeout=10).read()
                except:
                    response = "Time Out Error"
                if '0' in response:
                    DatabaseManager.storeMessages(output_dict)
                    return '0'
                else:
                    return '5'
            else:
                return '3'
        except urllib2.HTTPError:
            return '3'

    # Function which receives messages
    @cherrypy.expose
    @cherrypy.tools.json_in()
    def receiveMessage(self):
        try:
            input_data = cherrypy.request.json
            if self.rateLimit(input_data['sender']):
                if input_data['message']:
                    input_data['message'] = input_data['message'].replace("<","&lt;").replace(">","&gt;")
                    DatabaseManager.storeMessages(input_data)
                    return '0'
            else:
                return "11, Rate Limited"
        except:
            return '3'


    # Other users getting profile from me
    @cherrypy.expose
    @cherrypy.tools.json_in()
    def getProfile(self):
        data = cherrypy.request.json
        if self.rateLimit(data['sender']):
            myProfile = DatabaseManager.getProfileFromDB(data['profile_username'])
            userProfile = self.encode_JSON(myProfile)
            return userProfile
        else:
            return "11, Rate Limited"

    # To edit users profile using html
    @cherrypy.expose
    def edit_profile(self, fullname=None, position=None, description=None, location=None, picture=None):
        if self.isLoggedIn:
            username = cherrypy.session.get('username')
            DatabaseManager.setProfile(username, fullname, position, description, location, picture,time.time())
            raise cherrypy.HTTPRedirect('/edit_profile_page')
        else:
            raise cherrypy.HTTPRedirect('/login')
        

    # To get peoples profile from other people
    def getProfileOnline(self, profile_username):
        try:
            ping_result = self.getPing(profile_username)
            if '0' in ping_result:
                sender = cherrypy.session.get('username')
                output_dict = {"profile_username": profile_username,
                                "sender": sender}
                recipient_ip = DatabaseManager.getUserIP(profile_username)
                recipient_port = DatabaseManager.getUserPort(profile_username)
                url = "http://" + recipient_ip + ":" + recipient_port + "/getProfile"
                data = self.encode_JSON(output_dict)
                req = urllib2.Request(url, data, {'Content-Type': 'application/json'})
                try:
                    response = urllib2.urlopen(req).read()
                except:
                    response = '5'
                loaded = self.decode_JSON(response)
                loaded = self.replaceText(loaded)
                DatabaseManager.setProfile(profile_username,
                                            loaded.get('fullname','N/A'),
                                            loaded.get('position','N/A'),
                                            loaded.get('description','N/A'),
                                            loaded.get('location','N/A'),
                                            loaded.get('picture','N/A'),
                                            loaded.get('lastUpdated','N/A'))
                return loaded
            else:
                return '5'
        except urllib2.HTTPError:
            return '3'



    # Function which other users call to ping me
    @cherrypy.expose
    def ping(self, sender):
        return '0'

    # Function to call other users ping
    def getPing(self, destination):
        try:
            sender = cherrypy.session.get('username')
            recipient_ip = DatabaseManager.getUserIP(destination)
            recipient_port = DatabaseManager.getUserPort(destination)
            url = "http://" + recipient_ip + ":" + recipient_port + "/ping?sender=" + sender
            response = urllib2.urlopen(url).read()
            return response
        except:
            return '3'

    
    # Function to receive file from other users. File size must be less than 5Mb
    @cherrypy.expose
    @cherrypy.tools.json_in()
    def receiveFile(self):
        data = cherrypy.request.json
        if self.rateLimit(data['sender']):
            if len(data['file']) * 3 / 1024 > 5120 * 4:
                return '12'
            else:
                fileData = data['file']
                data['filename'] = data['filename'].replace(" ","")
                filename = data['filename']
                receivedFile = open("static/received_files/"+filename, "wb")
                receivedFile.write(base64.decodestring(fileData))
                receivedFile.close()
                DatabaseManager.storeFiles(data)
                return '0'
        else:
            return "11, Rate Limited"

    # This function is used to send files to other users which are online
    def sendFiles(self, myfile, recipient):
        try:
            if self.getPing(recipient) == '0':
                filename = str(myfile.filename)  # file name
                content_type = str(myfile.content_type.value) # file type
                output_dict = {"sender": cherrypy.session.get('username'),
                               "destination": recipient,
                               "file": myfile,
                               "filename": filename,
                               "content_type": content_type,
                               "stamp": time.time()}
                data = myfile.file.read()
                output_dict['file'] = data.encode("base64")
                # Checks if the size of the file is less than 5MB before sending
                if len(output_dict['file']) * 3 / 1024 > 5120 * 4:
                    return '12'

                output_dict['filename'] = output_dict['filename'].replace(' ','')  # Removes spaces from the filename
                # Stores the sent file in sent_files folder
                sentFile = open("static/sent_files/"+output_dict['filename'], "wb")
                sentFile.write(base64.decodestring(output_dict['file']))
                sentFile.close()

                recipient_ip = DatabaseManager.getUserIP(recipient)
                recipient_port = DatabaseManager.getUserPort(recipient)
                DatabaseManager.storeFiles(output_dict)
                data = self.encode_JSON(output_dict)
                url = "http://" + recipient_ip + ":" + recipient_port + "/receiveFile"
                req = urllib2.Request(url, data, {'Content-Type': 'application/json'})
                response = urllib2.urlopen(req).read()
                return response
            else:
                print "3: Client Currently Unavailable"
        except urllib2.HTTPError:
            return '3'

    # This function is called when the user logs out
    @cherrypy.expose
    def shutdown(self):
        username = cherrypy.session.get('username')
        password = cherrypy.session.get('hashedPassword')
        response = login_server.signout(username,password)
        if response == '0':
            cherrypy.session['username'] = None
            cherrypy.session['hashedPassword'] = None
            self.isLoggedIn = False
            raise cherrypy.HTTPRedirect('/')
        else:
            self.isLoggedIn = False
            raise cherrypy.HTTPRedirect('/')


    # This function is called when the server shuts down
    def forceShutdown(self):
        try:
            data = DatabaseManager.getMyself()
            response = login_server.signout(data[0], data[1])
            if response == '0':
                self.isLoggedIn = False
                print "Logged out"
            else:
                print "failed to log out"
        except KeyError:
            return '-1'


    # Two Factor Authentication
    @cherrypy.expose
    def tfa(self,name,password):
        myself = DatabaseManager.getMyself(name)
        link = None
        if myself is not None:
            key = myself[2]
        else:
            key = None
        if key is None:
            secret = tfa.newSecret()
            DatabaseManager.storeMyself(name, password,secret)
            cherrypy.session['secret'] = secret
            link = tfa.getQRLink(name, secret)
        template = env.get_template('2fa.html')
        return template.render(link=link)


    # Checks if the code entered matched the secret code in the database
    @cherrypy.expose
    def reply(self,code=None):
        try:
            name = cherrypy.session.get('username')
            password = cherrypy.session.get("hashedPassword")
            secret = DatabaseManager.getMyself(name)[2]
            if tfa.auth(secret, code):
                self.isLoggedIn = True
                reporter = cherrypy.process.plugins.BackgroundTask(50, login_server.authoriseUserLogin,
                                                                       kwargs=dict(username=name, password=password,
                                                                                   ip=ip,listen_port=listen_port))
                reporter.start()
                raise cherrypy.HTTPRedirect('/home')
            else:
                raise cherrypy.HTTPRedirect('/tfa?name='+cherrypy.session.get('username')+'&password=' +
                                            cherrypy.session.get('hashedPassword'))
        except ValueError:
            raise cherrypy.HTTPRedirect('/tfa?name=' + cherrypy.session.get('username') + '&password=' +
                                        cherrypy.session.get('hashedPassword'))


    # Checks if the user should be rate limited or not
    def rateLimit(self,recipient):
        rate = 15
        per = 300

        user_info = DatabaseManager.getRateLimit(recipient)
        allowance = user_info[1]
        last_check = user_info[2]
        current = time.time()

        time_passed = current - float(last_check);
        allowance += time_passed * (float(rate)/per)
        allowance = int(allowance)
        if allowance > rate:
            allowance = rate
        if allowance < 1:
            DatabaseManager.updateRateLimit(recipient, allowance, current)
            return False
        else:
            allowance -= 1
            DatabaseManager.updateRateLimit(recipient, allowance, current)
            return True


    # Replaces < and > from users to prevent html injection
    def replaceText(self,text):
        for index in text:
            if type(text[index]) is not float and type(text[index]) is not int and text[index] is not None:
                text[index] = text[index].replace("<", "&lt;").replace(">", "&gt;")
        return text



def runMainApp():
    conf = {
        '/': {
            'tools.sessions.on': True,
            'tools.staticdir.root': os.path.abspath(os.getcwd())
        },
        '/static': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': './static'
        }
    }
    # Create an instance of MainApp and tell Cherrypy to send all requests under / to it. (ie all of them)
    cherrypy.tree.mount(MainApp(), "/", conf)

    # Tell Cherrypy to listen for connections on the configured address and port.
    cherrypy.config.update({'server.socket_host': listen_ip,
                            'server.socket_port': listen_port,
                            'engine.autoreload.on': True,
                            })

    print "========================="
    print "University of Auckland"
    print "COMPSYS302 - Software Design Application"
    print "========================================"

    # Start the web server
    cherrypy.engine.start()

    # And stop doing anything else. Let the web server take over.
    cherrypy.engine.block()


# Run the function to start everything
runMainApp()
