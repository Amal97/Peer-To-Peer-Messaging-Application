"""
COMPSYS 302 ASSIGNMENT
AMAL CHANDRA

This file contains all the login server API that is used for the implementation of the messaging app
"""

import urllib2


# Returns all the API that is provided by the login server
def listAPI():
    url = "http://cs302.pythonanywhere.com/listAPI"
    list_of_API = urllib2.urlopen(url).read
    return list_of_API


# Returns a list of all the users that are currently online
def getList(username, hashedPassword):
    try:
        url = "http://cs302.pythonanywhere.com/getList?username=" + username +\
            "&password=" + hashedPassword + "&enc=0" + "&json=1"
        onlineUsers = urllib2.urlopen(url).read()
        return onlineUsers
    except TypeError,e:
        return e


# Returns a list of all the users that are registered
def listUsers():
    url = "http://cs302.pythonanywhere.com/listUsers"
    users_list = urllib2.urlopen(url).read()
    return users_list.split(",")


# This function is used to authenticate whether the login details provided by the user is correct or not
def authoriseUserLogin(username, password, ip, listen_port):
    try:
        local_ip = ip
        # Checks if the user is using Uni desktop computers
        if local_ip.startswith("10.103"):
            location = "0"
        # Checks if the user is using Uni Wifi
        elif local_ip.startswith("172.2"):
            location = "1"
        # Checks if the user is using external wifi
        else:
            location = "2"
            ipAddressURL = "https://api.ipify.org" # gets the users external ip address
            local_ip = urllib2.urlopen(ipAddressURL).read()

        url = "http://cs302.pythonanywhere.com/report?username=" + username + "&password=" + password + "&location=" \
              + location + "&ip=" + local_ip + "&port=" + str(listen_port) + "&enc=0"
        loginMessage = urllib2.urlopen(url).read()
        return loginMessage
    except urllib2.HTTPError,e:
        return e


# This function is used to log off from the login server so that the user is offline for all users
def signout( username, hashedPassword):
    url = "http://cs302.pythonanywhere.com/logoff?username=" + username + "&password=" + hashedPassword + "&enc=0"
    logoutMessage = urllib2.urlopen(url).read()
    # Logs the current user out, expires their session
    if logoutMessage == "0, Logged off successfully":
        return '0'
    else:
        return '1'
