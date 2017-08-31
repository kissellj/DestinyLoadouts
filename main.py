#!/usr/bin/env python
#
###############################################################################
#
#      TITLE: Destiny Loadouts (Voice Inventory Management for Destiny 2)
#
#    LICENSE: GNU General Public License GPLv3
#             https://www.gnu.org/licenses/gpl-3.0.en.html
#
#     AUTHOR: KissellJ
#  
#     GITHUB: https://github.com/kissellj/DestinyLoadouts
# 
#    VERSION: 2017.08.31
#
#     PYTHON: v2.7
#
###############################################################################
#
# TOP PRIORITY TODO LIST
# ----------------------
# 0) Implement Try/Except on all call_api returns like at line 542 
#
# 1) D2 replaces GetBungieAccount with GetProfile for finding Character IDs
#    https://bungie-net.github.io/multi/operation_get_Destiny2-GetProfile.html#operation_get_Destiny2-GetProfile
#    /Destiny2/{membershipType}/Profile/{destinyMembershipId}/
#
# 2) Change Security group to try to allow Alexa Skill from Lambda to DB without 0.0.0.0/0
#
# 3) Try the SoundEx Matching to equip items by name.  
#    Will require "import fuzzy" http://www.informit.com/articles/article.aspx?p=1848528
#    Will need to take intent value and compare it's fuzzy against fuzzy of list of items.
#    Will need to be able to find the itemId from that name. 
#
# 4) Keep saving cosmetics but remove them from Transfer/Equip intent unless "with cosmetics" is specified.
#
# 5) #GetItem - Need to be able to transfer items...  "Alexa, ask destiny loadouts for heavy ammo"
#    Alexa, ask destiny loadouts for five passage coins.
#    Alexa, ask desitny loadouts for thirteen strange coins.
#    Alexa, ask destiny loadouts for all my spin metal.
#
# 6) #SplitItems - Need to be able to count all items in all locations and evenly split between characters.
#    For instance, get count of heavy ammo in inventory on every character and in vault, then
#    Count number of characters created and if heavy ammo is less than character count * 200 then
#    Divide it and transfer it to all the created characters.
#    If more than character count * 200, then after transfering 200 to each character, put rest in vault.
#    Do this for ammos, planetary materials, passage coins, ect...
#    1) to split heavy ammo
#    2) to split all items
#
# 7) #SendEngrams - Need to be able to remove all engrams from active character's inventory for farming.
#    to send engrams to vault = get engrams off character, preferably to vault, if vault is full then to other characters.
#    Be able to send just exotics to vault. send exotic engrams to vault.

# 8) #GetEngrams - Transfer engrams from vault and other characters to the current character.
#    Prefer to get lower level engrams first until full, respond that character inventory is full but more engrams exist.
#    Be able to get just exotics from vault.  get exotic engrams
#    
# 9) Implement new loadout for "favorite weapons" that goes to all characters (this should be easy with #10 done)
# 
# 10) Implement "Load favorite shader" from favorite loadout (Already implemented saving favorite items)
#  

from __future__ import print_function
from inspect import currentframe
from urllib import urlopen

import ast
import sys
import json
import time
import datetime
import calendar
import psycopg2
import pickle
import urllib
import urllib2

# app_id is found on Skill Information tab of your skill: https://developer.amazon.com
app_id = "XXXXX.XXX.XXXXX.XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"

# api_key is found in your Bungie application configuration: https://www.bungie.net/en/Application
api_key = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

# Postgres Database connection information for Bungie Manifest.
# Use bootstrap-db.sh to create a postgresql database schema.
# And use bungie-manifest-refresh.sh as a cronjob to populate it and keep it updated.
db_host = "XXXXXXXXXXXXX.XXXXXXXXXXXX.us-XXXX-X.rds.amazonaws.com"
db_user = "XXXXXXXXXXX"
db_pass = "XXXXXXXXXXX"

# There are two DB names in the same postgres database.
# One is for this app
# The other is the Bungie Destiny World Manifest which is updated every week
# They are separate because the Bungie Manifest may be useful to other apps.
db_name_alexa = "alexa_destinyloadouts"
db_name_bungie = "bungie_destiny_world_sql_content"
db_port = "5432"

app_title = "Destiny Loadouts"
main_domain = "https://www.bungie.net"
app_help_msg = "You can ask me to save or equip your loadout for an activity. " \
               "Or to equip a single item by name. " 


def handler(event, context):
    print(print_linenumber(), "     FUNCTION : handler         : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              : handler                      : event                    : " + str(event))
    #print(print_linenumber(), "              : handler                      : context                  : " + str(context))

    '''
    handler is the main function that Alexa uses
    You put a AWS Lambda endpoint into the Skill configuration: https://developer.amazon.com
    This lets Alexa call this Python code hosted in Lambda.
    
    The Lamda endpoint configuration has a "handler" value that we set to "main.handler"
    The main in main.handler is the name if this script, main.py.
    The handler in main.handler is this function "handler" which is called first.
    
    The purpose of the handler is to parse the data from Alexa,
    and generate the proper response back to her. 
    '''

    global app_id
    global app_title

    # Check that application id is correct (required for AWS Skill Certification)
    try:
        application_id = event['session']['application']['applicationId']
    except:
        application_id = ""

    if application_id == app_id:
        print(print_linenumber(), "                  App Title : " + app_title)
        print(print_linenumber(), "                     App ID : " + app_id)
    else:
        print(print_linenumber(), "                      ERROR : Invalid Application ID, set the app_id")
        card_title = app_title + " : ERROR : Invalid Application ID."
        speech = "We are currently undergoing maintenance. " \
               + "Sorry for the inconvinience, please try again later."
        end_session = True
        return alexa_speak(card_title, speech, end_session)

    # Print to AWS Cloudwatch the Oauth Token from Bungie (for troubleshooting)
    try:
        auth_token = event['session']['user']['accessToken']
        print(print_linenumber(), "                 auth_token : " + auth_token)
    except:
        print(print_linenumber(), "                      ERROR : Authorization Not Allowed")
        card_title = app_title + " : ERROR : Authorization Not Allowed."
        speech = "ERROR : Authorization Not Allowed. " \
               + "It appears Bungie's network is undergoing maintenace, please try again later."
        end_session = True
        return alexa_speak(card_title, speech, end_session)    

    # Get Amazon Alexa User ID (Currently don't use)
    try:
        user_id = event['session']['user']['userId']
        print(print_linenumber(), "                     userId : " + user_id)
    except:    
        user_id = ""
        
    # Get Amazon Alexa Device ID (Currently don't use)    
    try: 
        device_id = event['context']['System']['device']['deviceId']
        print(print_linenumber(), "                  device_id : " + device_id)
    except:
        device_id = ""

    # Parse the Alexa user's speech
    if event['request']['type'] == "IntentRequest":
        print(print_linenumber(), "                    Request : IntentRequest")
        # User asked this skill to do something
        return on_intent(event['request']['intent'], auth_token)
    elif event['request']['type'] == "LaunchRequest" or event['request']['type'] == "Launch":
        print(print_linenumber(), "                    Request : LaunchRequest")
        # User just opened the skill, and didn't instruct it to do anything yet.
        card_title = "Welcome to " + app_title + "."
        speech = "This is " + app_title + ". You can ask me to save or equip a loadout."
        end_session = False
        return alexa_speak(card_title, speech, end_session)
    elif event['request']['type'] == "SessionEndedRequest":
        # User requested to quit the skill
        session_ended_request = event['request']
        session = event['session']
        print(print_linenumber(), "                    Request : SessionEndedRequest")
        print(print_linenumber(), "                  requestId : " + session_ended_request['requestId'])
        print(print_linenumber(), "                  sessionId : " + session['sessionId'])
        print(print_linenumber(), "                    Session : Ended")
        card_title = "End Session for " + app_title + "."
        speech = "Goodbye from " + app_title + "."
        end_session = True
        return alexa_speak(card_title, speech, end_session)
    else:
        # Don't know what happened, default to basic help prompt for user.
        print(print_linenumber(), "                    Request : Welcome (Default)")
        print(print_linenumber(), "                      event : " + str(event))
        card_title = "Welcome to " + app_title + "."
        speech = "This is " + app_title + ". " \
                 "If you need help using this app, just say, \"help\"."
        end_session = False
        return alexa_speak(card_title, speech, end_session)


def on_intent(intent, auth_token):
    print(print_linenumber(), "     FUNCTION : on_intent : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              : on_intent                    : intent                   : " + str(intent))
    print(print_linenumber(), "              : auth_token                   : auth_token               : " + str(auth_token))

    '''
    Main function, when user asks this skill to do something, this function 
    matches the user's "intent" passed here from the skill's interactive model.
    Then it launches the appropriate code/function for that "intent".
    '''
    
    global app_title
    global app_help_msg
    
    try:
        test = intent
        print(print_linenumber(), "                     intent : " + str(intent))
    except:
        print(print_linenumber(), "                      ERROR : Unknown Intent.")
        card_title = app_title + " : ERROR : Unknown Intent."
        speech = "We are currently undergoing maintenance. " \
               + "Sorry for the inconvinience, please try again later."
        end_session = True
        return alexa_speak(card_title, speech, end_session)   
        
    try:
        test = intent['name']
        print(print_linenumber(), "             intent['name'] : " + str(intent['name']))
    except:
        print(print_linenumber(), "                      ERROR : Unknown Intent Name.")
        card_title = app_title + " : ERROR : Unknown Intent Name."
        speech = "We are currently undergoing maintenance. " \
               + "Sorry for the inconvinience, please try again later."
        end_session = True
        return alexa_speak(card_title, speech, end_session) 

    if intent['name'] == "EquipEmblem":
        print(print_linenumber(), " intent['name'] == 'EquipEmblem' : " + str(equipped_items))
    elif intent['name'] == "EquipEmote":
        print(print_linenumber(), "  intent['name'] == 'EquipEmote' : " + str(equipped_items))
    elif intent['name'] == "EquipExoticArmor":
        print(print_linenumber(), "  intent['name'] == 'EquipExoticArmor' : " + str(equipped_items))
    elif intent['name'] == "EquipExoticWeapon":
        print(print_linenumber(), "  intent['name'] == 'EquipExoticWeapon' : " + str(equipped_items))
    elif intent['name'] == "EquipLoadout":
        try:
            slots = intent['slots']
            print(print_linenumber(), "                    intent['slots'] : " + str(intent['slots']))
        except: 
            slots = ""
        
        try:
            slots = intent['slots']['LOADOUT']['name']
            print(print_linenumber(), "intent['slots']['LOADOUT']['name']  : " + str(intent['slots']['LOADOUT']['name']))
        except:
            slots = ""
            
        try:
            intent['slots']['LOADOUT']['value']
            print(print_linenumber(), "intent['slots']['LOADOUT']['value'] : " + str(intent['slots']['LOADOUT']['value']))
        except:
            slots = ""

        user_info = get_userinfo(auth_token)
        try:
            display_name = user_info['display_name']
            print(print_linenumber(), "                  user_info : " + str(user_info))
        except:
            print(print_linenumber(), "                      ERROR : No User Info.")
            card_title = app_title + " : ERROR : No User Info."
            speech = "We are currently undergoing maintenance. " \
                   + "Sorry for the inconvinience, please try again later."
            end_session = True
            return alexa_speak(card_title, speech, end_session)         

        character_zero_inventory, character_one_inventory, character_two_inventory, \
        vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault, bucket_hashes_subclass = get_character_inventories(auth_token, user_info['membership_type'], user_info['membership_id'])
        try:
            test = character_zero_inventory['bucket_hashes'][0]
        except:
            print(print_linenumber(), "                      ERROR : No Character Inventory.")
            card_title = app_title + " : ERROR : No Character Inventory."
            speech = "We are currently undergoing maintenance. " \
                   + "Sorry for the inconvinience, please try again later."
            end_session = True
            return alexa_speak(card_title, speech, end_session)      
            
        exotics = get_all_exotics_in_game(auth_token)
        
        # TEST OF SPLITTING HEAVY AMMO EVENLY
        split_items(auth_token, user_info, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory)
        
        equipped_items = get_character_equipped_items(exotics, character_zero_inventory)
        print(print_linenumber(), "             equipped_items : " + str(equipped_items))
    
        #print(print_linenumber(), "   character_zero_inventory : " + str(character_zero_inventory))
        #print(print_linenumber(), "    character_one_inventory : " + str(character_one_inventory))
        #print(print_linenumber(), "    character_two_inventory : " + str(character_two_inventory))
        #print(print_linenumber(), "            vault_inventory : " + str(vault_inventory))
    
        character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory = mark_full_inventories(character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault)
        
        loadout_name = standardize_loadout_name(intent)
        
        timestamp = datetime.datetime.now()
        
        try:
            value = intent['slots']['FILTER']['value']
        except:     
            value = "NO_FILTER"
            
        if value == "subclass" or value == "sparrow" or value == "ship" or value == "shader" or value == "emote" or value == "emblem" or value == "ghost":
            loadout_name = "FAVORITE" 
        
        return equip_loadout(auth_token, loadout_name, equipped_items, user_info, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault, bucket_hashes_subclass)

    elif intent['name'] == "EquipShader":
        character_inventory = get_character_inventory(auth_token, membership_type, membership_id)
             
    elif intent['name'] == "EquipShip":
        character_inventory = get_character_inventory(auth_token, membership_type, membership_id)

    elif intent['name'] == "EquipSparrow":
        character_inventory = get_character_inventory(auth_token, membership_type, membership_id)
                         
    elif intent['name'] == "EquipSubclass":
        character_inventory = get_character_inventory(auth_token, membership_type, membership_id)
                     
    elif intent['name'] == "SaveLoadout":
        # RACE 0 = HUMAN, 1 = AWOKEN, 2 = EXO
        # GENDER 0 = MALE, 1 = FEMALE
        # CLASS 0 = TITAN, 1 = HUNTER, 2 = WARLOCK

        if intent['slots']:
            print(print_linenumber(), "                    intent['slots'] : " + str(intent['slots']))
        if intent['slots']['LOADOUT']['name']:
            print(print_linenumber(), " intent['slots']['LOADOUT']['name'] : " + str(intent['slots']['LOADOUT']['name']))
        if intent['slots']['LOADOUT']['value']:
            print(print_linenumber(), "intent['slots']['LOADOUT']['value'] : " + str(intent['slots']['LOADOUT']['value']))
            
        user_info = get_userinfo(auth_token)
        try:
            display_name = user_info['display_name']
            print(print_linenumber(), "                  user_info : " + str(user_info))
        except:
            print(print_linenumber(), "                      ERROR : No User Info.")
            card_title = app_title + " : ERROR : No User Info."
            speech = "We are currently undergoing maintenance. " \
                   + "Sorry for the inconvinience, please try again later."
            end_session = True
            return alexa_speak(card_title, speech, end_session)         

        character_zero_inventory, character_one_inventory, character_two_inventory, \
        vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault, bucket_hashes_subclass = get_character_inventories(auth_token, user_info['membership_type'], user_info['membership_id'])
        try:
            test = character_zero_inventory['bucket_hashes'][0]
        except:
            print(print_linenumber(), "                      ERROR : No Character Inventory.")
            card_title = app_title + " : ERROR : No Character Inventory."
            speech = "We are currently undergoing maintenance. " \
                   + "Sorry for the inconvinience, please try again later."
            end_session = True
            return alexa_speak(card_title, speech, end_session)      
            
        exotics = get_all_exotics_in_game(auth_token)
        equipped_items = get_character_equipped_items(exotics, character_zero_inventory)
        print(print_linenumber(), "             equipped_items : " + str(equipped_items))
    
        #print(print_linenumber(), "   character_zero_inventory : " + str(character_zero_inventory))
        #print(print_linenumber(), "    character_one_inventory : " + str(character_one_inventory))
        #print(print_linenumber(), "    character_two_inventory : " + str(character_two_inventory))
        #print(print_linenumber(), "            vault_inventory : " + str(vault_inventory))
        
        loadout_name = standardize_loadout_name(intent)
        
        timestamp = datetime.datetime.now()
        
        try:
            value = intent['slots']['FILTER']['value']
        except:     
            value = "NO_FILTER"
            
        if value == "subclass" or value == "sparrow" or value == "ship" or value == "shader" or value == "emote" or value == "emblem" or value == "ghost":
            loadout_name = "FAVORITE" 
            
        return save_loadout(user_info, loadout_name, equipped_items, value, timestamp)
    elif intent['name'] == "AMAZON.CancelIntent":
        card_title = "Cancelled request to " + app_title + "."
        speech = "Okay. Request cancelled."
        end_session = True
        return alexa_speak(card_title, speech, end_session)
    elif intent['name'] == "AMAZON.StopIntent":
        card_title = "Goodbye from " + app_title + "."
        speech = "Thank you for using " + app_title + "." \
                 "Please rate this skill and leave feedback. "
        end_session = True
        return alexa_speak(card_title, speech, end_session)
    elif intent['name'] == "AMAZON.HelpIntent":
        card_title = "Help for " + app_title + "."
        speech = "I am here to help. " + app_help_msg + " " \
                 "What would you like to know?"
        end_session = False
        return alexa_speak(card_title, speech, end_session)
    else:
        card_title = "Welcome to " + app_title + "."
        speech = "This is " + app_title + ". " \
                 "If you need help using this app, just say, \"help\"."
        end_session = False
        return alexa_speak(card_title, speech, end_session)


def alexa_speak(card_title, speech, end_session):
    print(print_linenumber(), "     FUNCTION : alexa_speak : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              : alexa_speak                  : card_title               : " + card_title)
    print(print_linenumber(), "              : alexa_speak                  : speech                   : " + speech)
    print(print_linenumber(), "              : alexa_speak                  : end_session              : " + str(end_session))
    
    global db_host
    global db_name_alexa
    global db_user
    global db_pass
    global db_port
    
    timestamp = datetime.datetime.now()
    
    conn = None
    conn = psycopg2.connect(host=db_host, database=db_name_alexa, user=db_user, \
                            password=db_pass, port=db_port)
    cur = conn.cursor()
    sql = "INSERT INTO public.alexa_speak (card_title, speech, timestamp) VALUES (%s, %s, %s)"
    cur.execute(sql, (card_title, speech, timestamp))
    cur.close()
    conn.commit()
    conn.close()

    session_attributes = {}
    reprompt = speech

    json_data = {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': speech
            },
            'card': {
                'type': 'Simple',
                'title': card_title,
                'content': speech,
            },
            'reprompt': {
                'outputSpeech': {
                    'type': 'PlainText',
                    'text': reprompt
                }
            },
            'shouldEndSession': end_session
        }
    }

    return json_data


def call_api(endpoint, auth_token, data="", method="GET"):
    print(print_linenumber(), "     FUNCTION : call_api                     : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              : call_api                     : endpoint                      : " + str(endpoint))
    #print(print_linenumber(), "              : call_api                     : auth_token               : " + str(auth_token))

    global main_domain
    global api_key
    
    root_app = "D1"
    #root_app = "Destiny2"
    #get_character_ids = /Destiny2/{membershipType}/Profile/{destinyMembershipId}/
    
    if endpoint == "get_userinfo":
        url = main_domain + "/Platform/User/GetMembershipsForCurrentUser/"
    elif endpoint == "get_character_ids":
        membership_type = data['membershipType']
        membership_id = data['membershipId']
        url = main_domain + "/" + root_app + "/Platform/Destiny/" + str(membership_type) + "/Account/" + str(membership_id) + "/"
    elif endpoint == "get_all_exotics_in_game":
        url = main_domain + "/" + root_app + "/Platform/Destiny/Explorer/Items/?count=500&rarity=Exotic"
    elif endpoint == "account_inventory_from_api":
        membership_type = data['membershipType']
        membership_id = data['membershipId']
        url = main_domain + "/" + root_app + "/Platform/Destiny/" + str(membership_type) + "/Account/" + str(membership_id) + "/Items/"
    elif endpoint == "vault_inventory_from_api":
        membership_type = data['membershipType']
        url = main_domain + "/" + root_app + "/Platform/Destiny/" + str(membership_type) + "/MyAccount/Vault/Summary/?definitions=true"
    elif endpoint == "transfer_item":
        url = main_domain + "/" + root_app + "/Platform/Destiny/TransferItem/"
    elif endpoint == "equip_items":
        url = main_domain + "/" + root_app + "/Platform/Destiny/EquipItems/"
    else:
        print(print_linenumber(), "                      ERROR : Unknown API Endpoint.")
        card_title = app_title + " : ERROR : Unknown API Endpoint."
        speech = "ERROR: Unknown API Endpoint. " \
               + "It appears Bungie's network is undergoing maintenace, please try again later."
        end_session = True
        return alexa_speak(card_title, speech, end_session)        
        
    if data:
        print(print_linenumber(), "              : call_api                     : data                     : " + str(data)) 
        #print(print_linenumber(), "              : call_api                     : method                   : " + str(method)) 
        
    connection_code = 200
    
    handler = urllib2.HTTPHandler()
    opener = urllib2.build_opener(handler)
    
    if method == "POST":
        request = urllib2.Request(url, data=data)
        #print(print_linenumber(), "                               data : " + str(data))
    else:
        request = urllib2.Request(url)
        
    request.add_header('X-API-Key', api_key)
    request.add_header('Authorization', "Bearer " + auth_token)
    request.add_header("Content-Type",'application/json')

    request.get_method = lambda: method

    try:
        connection = opener.open(request)
    except urllib2.HTTPError,e:
        connection_code = e.code

    if connection_code == 200:
        response = connection.read()
        response_json = json.loads(response)
    elif connection_code == 401:
        print(print_linenumber(), "                              ERROR : HTTP 401 Unauthorized.")
        card_title = app_title + " : ERROR : HTTP 401 Unauthorized."
        speech = "ERROR: 401: Unauthorized. " \
               + "Please ensure this skill is 'Approved' to connect to your Bungie account."
        end_session = True
        return alexa_speak(card_title, speech, end_session)
    elif connection_code == 403:
        print(print_linenumber(), "                              ERROR : HTTP 403 Forbidden.")
        card_title = app_title + " : ERROR : HTTP 403 Forbidden."
        speech = "ERROR: 403: Forbidden. " \
               + "It appears Bungie's network is undergoing maintenace, please try again later."
        end_session = True
        return alexa_speak(card_title, speech, end_session)
    elif connection_code == 404:
        print(print_linenumber(), "                      ERROR : HTTP 404 Not Found.")
        card_title = app_title + " : ERROR : HTTP 404 Not Found."
        speech = "ERROR: 404: Not Found. " \
               + "It appears Bungie's network is undergoing maintenace, please try again later."
        end_session = True
        return alexa_speak(card_title, speech, end_session)
    elif connection_code == 429:
        print(print_linenumber(), "                      ERROR : HTTP 429 Too Many Requests.")
        card_title = app_title + " : ERROR : HTTP 429 Too Many Requests."
        speech = "ERROR: 429:  Too Many Requests. " \
               + "Bungie's servers are rejecting new connections from this app at this time, please try again later."
        end_session = True
        return alexa_speak(card_title, speech, end_session)      
    elif connection_code == 500:
        print(print_linenumber(), "                      ERROR : HTTP 500 Internal Server Error.")
        card_title = app_title + " : ERROR : HTTP 500 Internal Server Error."
        speech = "ERROR: 500:  Internal Server Error. " \
               + "It appears Bungie's network is undergoing maintenace, please try again later."
        end_session = True
        return alexa_speak(card_title, speech, end_session)
    elif connection_code == 502:
        print(print_linenumber(), "                      ERROR : HTTP 502 Bad Gateway.")
        card_title = app_title + " : ERROR : HTTP 502 Bad Gateway."
        speech = "ERROR: 502:  Bad Gateway. " \
               + "It appears Bungie's network is undergoing maintenace, please try again later."
        end_session = True
        return alexa_speak(card_title, speech, end_session)
    elif connection_code == 503:
        print(print_linenumber(), "                      ERROR : HTTP 503 Service Unavailable.")
        card_title = app_title + " : ERROR : HTTP 503 Service Unavailable."
        speech = "ERROR: 503: Service Unavailable. " \
               + "I am having trouble connecting to Destiny's network, please try again later."
        end_session = True
        return alexa_speak(card_title, speech, end_session)            
    elif connection_code == 504:
        print(print_linenumber(), "                      ERROR : HTTP 504 Gateway Timeout.")
        card_title = app_title + " : ERROR : HTTP 504 Gateway Timeout."
        speech = "ERROR: 504: Gateway Timeout. " \
               + "It appears Bungie's network is undergoing maintenace, please try again later."
        end_session = True
        return alexa_speak(card_title, speech, end_session)            
    else:
        print(print_linenumber(), "                      ERROR : HTTP " + str(connection_code))
        card_title = app_title + " : ERROR : HTTP " + str(connection_code) + "."
        speech = "ERROR: HTTP: Unknown." \
               + "It appears Bungie's network is undergoing maintenace, please try again later."
        end_session = True
        return alexa_speak(card_title, speech, end_session)    

    if response_json['ErrorCode'] == 217:
        print(print_linenumber(), "                      ERROR : Bungie User API Code: 217 : Retrying...")
        time.sleep(3)
        print(response_json)
        response_json = call_api(endpoint, auth_token)

    #print(print_linenumber(), "              response_json : " + str(response_json)) 
    return response_json
    
    
def query_bungie_db(sql):
    print(print_linenumber(), "     FUNCTION : query_bungie_db : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              : query_bungie_db              : sql                      : " + str(sql))

    global db_host
    global db_name_bungie
    global db_user
    global db_pass
    global db_port

    conn = None
    conn = psycopg2.connect(host=db_host, database=db_name_bungie, user=db_user, \
                            password=db_pass, port=db_port)
                            
    cur = conn.cursor()
    cur.execute(sql)
    query_results = cur.fetchall()
    print(print_linenumber(), "                      query_results : " + str(query_results))
    
    cur.close()
    conn.close()

    return query_results


def query_alexa_db(sql):
    print(print_linenumber(), "     FUNCTION : query_alexa_db : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              : query_alexa_db               : sql                      : " + str(sql))

    global db_host
    global db_name_alexa
    global db_user
    global db_pass
    global db_port

    conn = None
    conn = psycopg2.connect(host=db_host, database=db_name_alexa, user=db_user, \
                            password=db_pass, port=db_port)
                            
    cur = conn.cursor()
    cur.execute(sql)
    query_results = cur.fetchall()
    cur.close()
    conn.commit()
    conn.close()
    
    print(print_linenumber(), "                      query_results : " + str(query_results))
    return query_results
    

def get_character_ids(auth_token, item):
    print(print_linenumber(), "     FUNCTION : get_character_ids : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              : get_character_ids                 : auth_token               : " + str(auth_token))
    print(print_linenumber(), "              : get_character_ids                 : item                     : " + str(item))

    character_lastplayed = 0
    
    membership_type = item['membershipType']
    membership_id = item['membershipId']
    
    print(print_linenumber(), "                    membership_type : " + str(membership_type))
    print(print_linenumber(), "                      membership_id : " + str(membership_id))
    
    endpoint = "get_character_ids"
    get_bungie_account = call_api(endpoint, auth_token, item)
    
    # TROUBLESHOOT NEW API ENDPOINT AFTER D2 LAUNCH (NEED RESPONSE DATA JSON FORMAT)
    #print(print_linenumber(), "         get_bungie_account : " + str(get_bungie_account))

    try:
        player_account = get_bungie_account['Response']['data']['characters']
    except:
        return get_bungie_account

    print(print_linenumber(), "             player_account : " + str(player_account))        
    for index, item in enumerate(get_bungie_account['Response']['data']['characters']):
        print(print_linenumber(), "                               item : " + str(item))
        if item['characterBase']['membershipId'] == membership_id:
            if index == 0:
                try:
                    character_lastplayed = item['characterBase']['dateLastPlayed']
                    character_zero_id = item['characterBase']['characterId']
                    character_zero_race = item['characterBase']['raceHash']
                    character_zero_gender = item['characterBase']['genderHash']
                    character_zero_class = item['characterBase']['classHash']
                except: 
                    character_lastplayed = datetime.datetime.now().split('.')[0]
                    character_zero_id = 254
                    character_zero_race = 254
                    character_zero_gender = 254
                    character_zero_class = 254
            elif index == 1:
                try:    
                    character_one_id = item['characterBase']['characterId']
                    character_one_race = item['characterBase']['raceHash']
                    character_one_gender = item['characterBase']['genderHash']
                    character_one_class = item['characterBase']['classHash']
                except:
                    character_one_id = 254
                    character_one_race = 254
                    character_one_gender = 254
                    character_one_class = 254
            elif index == 2:    
                try:
                    character_two_id = item['characterBase']['characterId']
                    character_two_race = item['characterBase']['raceHash']
                    character_two_gender = item['characterBase']['genderHash']
                    character_two_class = item['characterBase']['classHash']
                except:
                    character_two_id = 254
                    character_two_race = 254
                    character_two_gender = 254
                    character_two_class = 254

    return membership_id, membership_type, character_lastplayed, character_zero_id, character_zero_race, character_zero_gender, character_zero_class, character_one_id, character_one_race, character_one_gender, character_one_class, character_two_id, character_two_race, character_two_gender, character_two_class
        
    
def get_userinfo(auth_token):
    print(print_linenumber(), "     FUNCTION : get_userinfo : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              : get_userinfo                 : auth_token               : " + str(auth_token))

    character_lastplayed_xbox = 0
    character_lastplayed_psn = 0
    character_lastplayed_pc = 0
    
    endpoint = "get_userinfo"
    get_memberships_for_currentuser = call_api(endpoint, auth_token)
    try:
        membership_id_bungie = get_memberships_for_currentuser['Response']['bungieNetUser']['membershipId']
        print(print_linenumber(), "    get_memberships_for_currentuser : " + str(get_memberships_for_currentuser))  
        display_name = get_memberships_for_currentuser['Response']['bungieNetUser']['displayName']
        print(print_linenumber(), "               membership_id_bungie : " + membership_id_bungie)
        print(print_linenumber(), "                       display_name : " + display_name)  
    except:
        return get_memberships_for_currentuser

    for index, item in enumerate(get_memberships_for_currentuser['Response']['destinyMemberships']):
        #print(print_linenumber(), "                               item : " + str(item))  
        if item['membershipType'] == 1:
            try:
                membership_id_xbox, membership_type_xbox, character_lastplayed_xbox, character_zero_id_xbox, character_zero_race_xbox, character_zero_gender_xbox, character_zero_class_xbox, character_one_id_xbox, character_one_race_xbox, character_one_gender_xbox, character_one_class_xbox, character_two_id_xbox, character_two_race_xbox, character_two_gender_xbox, character_two_class_xbox = get_character_ids(auth_token, item)
            except:
                return get_character_ids(auth_token, item)
        elif item['membershipType'] == 2:
            try:
                membership_id_psn, membership_type_psn, character_lastplayed_psn, character_zero_id_psn, character_zero_race_psn, character_zero_gender_psn, character_zero_class_psn, character_one_id_psn, character_one_race_psn, character_one_gender_psn, character_one_class_psn, character_two_id_psn, character_two_race_psn, character_two_gender_psn, character_two_class_psn = get_character_ids(auth_token, item)
            except:
                return get_character_ids(auth_token, item)
        elif item['membershipType'] == 4:
            try:
                membership_id_pc, membership_type_pc, character_lastplayed_pc, character_zero_id_pc, character_zero_race_pc, character_zero_gender_pc, character_zero_class_pc, character_one_id_pc, character_one_race_pc, character_one_gender_pc, character_one_class_pc, character_two_id_pc, character_two_race_pc, character_two_gender_pc, character_two_class_pc = get_character_ids(auth_token, item)
            except:
                return get_character_ids(auth_token, item)

        if (character_lastplayed_xbox > character_lastplayed_psn) and (character_lastplayed_xbox > character_lastplayed_pc):
            membership_type = 1
            membership_id = membership_id_xbox
            character_zero_id = character_zero_id_xbox
            character_one_id = character_one_id_xbox
            character_two_id = character_two_id_xbox
            character_zero_race = character_zero_race_xbox
            character_zero_gender = character_zero_gender_xbox
            character_zero_class = character_zero_class_xbox
            character_one_race = character_one_race_xbox
            character_one_gender = character_one_gender_xbox
            character_one_class = character_one_class_xbox
            character_two_race = character_two_race_xbox
            character_two_gender = character_two_gender_xbox
            character_two_class = character_two_class_xbox
        elif (character_lastplayed_psn > character_lastplayed_xbox) and (character_lastplayed_psn > character_lastplayed_pc):
            membership_type = 2
            membership_id = membership_id_psn
            character_zero_id = character_zero_id_psn
            character_one_id = character_one_id_psn
            character_two_id = character_two_id_psn
            character_zero_race = character_zero_race_psn
            character_zero_gender = character_zero_gender_psn
            character_zero_class = character_zero_class_psn
            character_one_race = character_one_race_psn
            character_one_gender = character_one_gender_psn
            character_one_class = character_one_class_psn
            character_two_race = character_two_race_psn
            character_two_gender = character_two_gender_psn
            character_two_class = character_two_class_psn
        elif (character_lastplayed_pc > character_lastplayed_psn) and (character_lastplayed_pc > character_lastplayed_xbox):
            membership_type = 4
            membership_id = membership_id_pc
            character_zero_id = character_zero_id_pc
            character_one_id = character_one_id_pc
            character_two_id = character_two_id_pc
            character_zero_race = character_zero_race_pc
            character_zero_gender = character_zero_gender_pc
            character_zero_class = character_zero_class_pc
            character_one_race = character_one_race_pc
            character_one_gender = character_one_gender_pc
            character_one_class = character_one_class_pc
            character_two_race = character_two_race_pc
            character_two_gender = character_two_gender_pc
            character_two_class = character_two_class_pc
        else:
            print(print_linenumber(), "                              ERROR : Could not determine which platform last played on.")
            card_title = app_title + " : ERROR : You've never played Destiny?"
            speech = "I am having trouble finding a character you've played in Destiny the Game. " \
                   + "Please play Destiny and create a character before using this app." \
                   + "This app must be approved on Bungie dot net, and your Bungie dot net account " \
                   + "must be linked to your Destiny account."
            end_session = True
            return alexa_speak(card_title, speech, end_session)

        # "raceHash": 2803282938,   (Awoken)
        # "genderHash": 3111576190, (Male)
        # "classHash": 3655393761,  (Titan)
        # "raceHash": 3887404748,   (Human)
        # "genderHash": 2204441813, (Female)
        # "classHash": 2271682572,  (Warlock)
        # "raceHash": 3887404748,   (Human)
        # "genderHash": 3111576190, (Male)
        # "classHash": 671679327,   (Hunter)

        print(print_linenumber(), "                  character_zero_id : " + str(character_zero_id))
        print(print_linenumber(), "                character_zero_race : " + str(character_zero_race))
        print(print_linenumber(), "              character_zero_gender : " + str(character_zero_gender))
        print(print_linenumber(), "               character_zero_class : " + str(character_zero_class))
        print(print_linenumber(), "                   character_one_id : " + str(character_one_id))
        print(print_linenumber(), "                 character_one_race : " + str(character_one_race))
        print(print_linenumber(), "               character_one_gender : " + str(character_one_gender))
        print(print_linenumber(), "                character_one_class : " + str(character_one_class))
        print(print_linenumber(), "                   character_two_id : " + str(character_two_id))
        print(print_linenumber(), "                 character_two_race : " + str(character_two_race))
        print(print_linenumber(), "               character_two_gender : " + str(character_two_gender))
        print(print_linenumber(), "                character_two_class : " + str(character_two_class))

        user_info = {}
        user_info = {'display_name': display_name, 'membership_id_bungie': membership_id_bungie, \
        'membership_type': membership_type, 'membership_id': membership_id, \
        'character_zero_id': character_zero_id, 'character_zero_race': character_zero_race, \
        'character_zero_gender': character_zero_gender, 'character_zero_class': character_zero_class, \
        'character_one_id': character_one_id, 'character_one_race': character_one_race, \
        'character_one_gender': character_one_gender, 'character_one_class': character_one_class, \
        'character_two_id': character_two_id, 'character_two_race': character_two_race, \
        'character_two_gender': character_two_gender, 'character_two_class': character_two_class }

        return user_info


def find_item_location(user_info, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, itemId = 0, itemHash = 0, ):
    print(print_linenumber(), "     FUNCTION : find_item_location   : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              : find_item_location           : itemId                   : " + str(itemId))    
    print(print_linenumber(), "              : find_item_location           : itemHash                 : " + str(itemHash))   
 
    location_id = 0
    
    if itemId <> 0:
        if int(itemId) in character_zero_inventory['itemIds']:
            location_id = user_info['character_zero_id']
        elif int(itemId) in character_one_inventory['itemIds']:
            location_id = user_info['character_one_id']
        elif int(itemId) in character_two_inventory['itemIds']:
            location_id = user_info['character_two_id']
        elif int(itemId) in vault_inventory['itemIds']:
            location_id = -1
        else:
            itemId = "NOT_FOUND"

    if itemHash <> 0 and itemId == "NOT_FOUND":
        if int(itemHash) in character_zero_inventory['itemHashes']:
            location_id = user_info['character_zero_id']
        elif int(itemHash) in character_one_inventory['itemHashes']:
            location_id = user_info['character_one_id']
        elif int(itemHash) in character_two_inventory['itemHashes']:
            location_id = user_info['character_two_id']
        elif int(itemHash) in vault_inventory['itemHashes']:
            location_id = -1
        else:
            print(print_linenumber(), "                             WARNING: find_item_location failed.  Item probably deleted since loadout was saved.")
            location_id = 0
            
    return str(location_id)


def do_strings_match(string_from_db, string_from_user):
    print(print_linenumber(), "     FUNCTION :    do_strings_match : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              :    do_strings_match          : string_from_db           : " + str(string_from_db))    
    print(print_linenumber(), "              :    do_strings_match          : string_from_user         : " + str(string_from_user))    

    string_from_db = string_from_db.replace('_', '')    
    string_from_db = string_from_db.replace(' ', '')   
    string_from_db = string_from_db.replace("'", '')   
    string_from_db = string_from_db.replace('`', '')   
    string_from_db = string_from_db.replace('(', '')   
    string_from_db = string_from_db.replace(')', '')   
    string_from_db = string_from_db.replace('-', '')
    string_from_db = string_from_db.replace('"', '').lower()
    
    string_from_user = string_from_user.replace('_', '')    
    string_from_user = string_from_user.replace(' ', '')   
    string_from_user = string_from_user.replace("'", '')   
    string_from_user = string_from_user.replace('`', '')   
    string_from_user = string_from_user.replace('(', '')   
    string_from_user = string_from_user.replace(')', '')   
    string_from_user = string_from_user.replace('-', '')
    string_from_user = string_from_user.replace('"', '').lower()
   
    print(print_linenumber(), "                   string_from_db   : " + str(string_from_db))    
    print(print_linenumber(), "                   string_from_user : " + str(string_from_user))   
    
    if string_from_db == string_from_user:
        return 1
    else:
        return 0


def get_all_exotics_in_game(auth_token):
    print(print_linenumber(), "     FUNCTION :      get_all_exotics : " + str(datetime.datetime.now()).split('.')[0])
    #print(print_linenumber(), "              :      get_all_exotics         : auth_token               : " + str(auth_token))

    endpoint = "get_all_exotics_in_game"
    #exotics = call_api(endpoint, auth_token)['Response']['data']['itemHashes']
    exotics = call_api(endpoint, auth_token)

    try:
        test = exotics['Response']['data']['itemHashes']
    except:
        return exotics
        
    exotics = exotics['Response']['data']['itemHashes']
    
    # Fix missing Y3 Ice Breaker
    exotics.append(4242230174)
    print(print_linenumber(), "                            exotics : " + str(exotics))

    return exotics
    
    
def is_it_an_exotic(hash, exotics):
    #print(print_linenumber(), "     FUNCTION :     is_it_an_exotic : " + str(datetime.datetime.now()).split('.')[0])
    #print(print_linenumber(), "              :     is_it_an_exotic          :       hash               : " + str(hash))
    #print(print_linenumber(), "              :     is_it_an_exotic          :    exotics               : " + str(exotics))

    if int(hash) in exotics:
        return 1
    else:
        return 0


def is_bucket_full(character_inventory, bucket_hashes, bucket_type, max_items, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault):
    #print(print_linenumber(), "     FUNCTION : is_bucket_full : " + str(datetime.datetime.now()).split('.')[0])
    #print(print_linenumber(), "              : is_bucket_full               : character_inventory      : " + str(character_inventory))
    #print(print_linenumber(), "              : is_bucket_full               : bucket_hashes            : " + str(bucket_hashes))
    #print(print_linenumber(), "              : is_bucket_full               : bucket_type              : " + str(bucket_type))
    #print(print_linenumber(), "              : is_bucket_full               : max_items                : " + str(max_items))

    if str(bucket_type) in bucket_hashes_weapons:
        #print(print_linenumber(), "str(bucket_type) in bucket_hashes_weapons")
        bucket_count = character_inventory['bucket_hashes'].count(int(bucket_hashes_weapons[bucket_type]))
    elif str(bucket_type) in bucket_hashes_armor:
        #print(print_linenumber(), "str(bucket_type) in bucket_hashes_armor")
        bucket_count = character_inventory['bucket_hashes'].count(int(bucket_hashes_armor[bucket_type]))
    elif str(bucket_type) in bucket_hashes_general:
        #print(print_linenumber(), "str(bucket_type) in bucket_hashes_general")
        bucket_count = character_inventory['bucket_hashes'].count(int(bucket_hashes_general[bucket_type]))
    elif str(bucket_type) in bucket_hashes_vault:
        #print(print_linenumber(), "str(bucket_type) in bucket_hashes_vault")
        bucket_count = character_inventory['bucket_hashes'].count(int(bucket_hashes_vault[bucket_type]))
    else:
        #print(print_linenumber(), "str(bucket_type) not in anything that can be full")
        bucket_count = 0
    
    #print(print_linenumber(), "bucket_count: " + str(bucket_count))
    
    if int(bucket_count) == int(max_items):
        #print(print_linenumber(), "int(bucket_count) == int(max_items)")
        character_inventory['bucketsFull'].append(bucket_type)
    #else:
        #print(print_linenumber(), "int(bucket_count) != int(max_items)")
    
    return character_inventory
    

def standardize_loadout_name(intent):
    print(print_linenumber(), "     FUNCTION : standardize_loadout_name : " + str(datetime.datetime.now()).split('.')[0])  
    print(print_linenumber(), "              : standardize_loadout_name     : intent                   : " + str(intent))   
   
    if intent['slots']['LOADOUT']['value']:
        loadout = str(intent['slots']['LOADOUT']['value'])
        #print(print_linenumber(), "                            loadout : " + str(loadout))
            
        if ("trial" in loadout) or ("osiris" in loadout) or "tyrrells" in loadout or "cyrus" in loadout or "trowels" in loadout:
            loadout_name = "TRIALS"
        elif "iron" in loadout or "banner" in loadout or "banana" in loadout or "salad man" in loadout or "saladin" in loadout:
            loadout_name = "IRON_BANNER"
        elif "ranked" in loadout or "competitive" in loadout:
            loadout_name = "COMPETITIVE_PLAY"           
        elif "quick" in loadout or "crucible" in loadout or "p. v. p." in loadout:
            loadout_name = "QUICK_PLAY"
        elif "strike" in loadout or "p. v. e." in loadout:
            loadout_name = "STRIKE"              
        elif "patrol" in loadout or "lost" in loadout or "sector" in loadout or "public" in loadout or "event" in loadout:
            loadout_name = "PATROL"            
        elif "adventure" in loadout or "flash" in loadout or "point" in loadout or "farm" in loadout or "tower" in loadout:
            loadout_name = "PATROL"    
        elif "favorite" in loadout or "favourite" in loadout:
            loadout_name = "FAVORITE"              
        elif "desolate" in loadout or "taken" in loadout:
            loadout_name = "DESOLATE"              
        elif "v. o. g." in loadout or "hezen" in loadout or "beers" in loadout or "kabrs" in loadout or "volt" in loadout:
            loadout_name = "VAULT_OF_GLASS"    
        elif "kabers" in loadout or "zealot" in loadout or "vault" in loadout or "glass" in loadout or "Vltava" in loadout:
            loadout_name = "VAULT_OF_GLASS"    
        elif "crota" in loadout or "krota" in loadout or "end" in loadout or "cuirass" in loadout or "chronos" in loadout:
            loadout_name = "CROTAS_END"          
        elif "curassis" in loadout or "curasis" in loadout or "death" in loadout or "singer" in loadout:
            loadout_name = "CROTAS_END" 
        elif "oryx" in loadout or "totem" in loadout or "daughter" in loadout or "golgorath" in loadout or "golgoroth" in loadout or "war numens" in loadout:
            loadout_name = "KINGS_FALL"  
        elif "kings" in loadout or "fall" in loadout or "hallow" in loadout or "harrowed" in loadout:
            loadout_name = "KINGS_FALL"      
        elif "spliced" in loadout or "miasma" in loadout or "nanomania" in loadout or "cosmoclast" in loadout or "machine" in loadout:
            loadout_name = "WRATH_OF_THE_MACHINE"              
        elif "misama" in loadout or "perfected" in loadout or "siva" in loadout or "nano" in loadout or "wrath" in loadout:
            loadout_name = "WRATH_OF_THE_MACHINE"    
        elif "leviathan" in loadout or "level ethan" in loadout or "leviethen" in loadout:
            loadout_name = "LEVIATHAN"
        elif "arc" in loadout or "ark" in loadout:
            loadout_name = "ARC_BURN"
        elif "solar" in loadout:
            loadout_name = "SOLAR_BURN"
        elif "void" in loadout:
            loadout_name = "VOID_BURN"
        else:
            loadout_name = "DEFAULT"
    else:
        loadout_name = "DEFAULT"
        
    #print(print_linenumber(), "                       loadout_name : " + str(loadout_name))            
    return str(loadout_name)


def get_character_equipped_items(exotics, character_inventory):
    print(print_linenumber(), "     FUNCTION : get_character_equipped_items : " + str(datetime.datetime.now()).split('.')[0])
    #print(print_linenumber(), "              : get_character_equipped_items : auth_token               : " + str(auth_token))
    #print(print_linenumber(), "              : get_character_equipped_items : exotics                  : " + str(exotics))
    #print(print_linenumber(), "              : get_character_equipped_items : character_inventory : " + str(character_inventory))  
    #print(print_linenumber(), "              : get_character_equipped_items : vault_inventory          : " + str(vault_inventory))    

    exotic_items = []
    itemHashes = []
    itemIds = []
    bucket_hashes = []
    equipped_items = {"exotic_item": exotic_items, "itemHash": itemHashes, "itemId": itemIds, "bucket_hash": bucket_hashes}

    for index, value in enumerate(character_inventory['transferStatus']):
        if int(character_inventory['transferStatus'][index]) == 1 or int(character_inventory['transferStatus'][index]) == 3:
            itemHashes.append(character_inventory['itemHashes'][index])    
            exotic_items.append(is_it_an_exotic(character_inventory['itemHashes'][index], exotics))
            itemIds.append(character_inventory['itemIds'][index])
            bucket_hashes.append(character_inventory['bucket_hashes'][index])
       
    print(print_linenumber(), "                       exotic_items : " + str(exotic_items))        
    print(print_linenumber(), "                         itemHashes : " + str(itemHashes))
    return equipped_items    
    
    
def get_character_inventories(auth_token, membership_type, membership_id):
    print(print_linenumber(), "     FUNCTION : get_character_inventories : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              : get_character_inventories    : auth_token               : " + str(auth_token))
    print(print_linenumber(), "              : get_character_inventories    : membership_type          : " + str(membership_type))
    print(print_linenumber(), "              : get_character_inventories    : membership_id            : " + str(membership_id))

    data = {}
    data['membershipType'] = membership_type
    data['membershipId'] = membership_id
    
    # "transferStatus": 1,
    character_zero_transferStatus = []
    character_zero_itemHashes = []
    character_zero_itemIds = []
    character_zero_bucket_hashes = []
    character_zero_characterIndices = []
    character_zero_quantities = []
    character_zero_bucket_is_full = []
    character_zero_inventory = {'transferStatus': character_zero_transferStatus, \
                                'itemHashes': character_zero_itemHashes, \
                                'itemIds': character_zero_itemIds, \
                                'bucket_hashes': character_zero_bucket_hashes, \
                                'quantities': character_zero_quantities, \
                                'bucketsFull': character_zero_bucket_is_full}
    character_one_transferStatus = []
    character_one_itemHashes = []
    character_one_itemIds = []
    character_one_bucket_hashes = []
    character_one_characterIndices = []
    character_one_quantities = []
    character_one_bucket_is_full = []
    character_one_inventory = {'transferStatus': character_one_transferStatus, \
                                'itemHashes': character_one_itemHashes, \
                                'itemIds': character_one_itemIds, \
                                'bucket_hashes': character_one_bucket_hashes, \
                                'quantities': character_one_quantities, \
                                'bucketsFull': character_one_bucket_is_full}
    character_two_transferStatus = []
    character_two_itemHashes = []
    character_two_itemIds = []
    character_two_bucket_hashes = []
    character_two_characterIndices = []
    character_two_quantities = []
    character_two_bucket_is_full = []
    character_two_inventory = {'transferStatus': character_two_transferStatus, \
                                'itemHashes': character_two_itemHashes, \
                                'itemIds': character_two_itemIds, \
                                'bucket_hashes': character_two_bucket_hashes, \
                                'quantities': character_two_quantities, \
                                'bucketsFull': character_two_bucket_is_full}
    vault_itemHashes = []
    vault_itemIds = []
    vault_bucket_hashes = []
    vault_bucket_type_hashes = []
    vault_characterIndices = []
    vault_quantities = []
    vault_bucket_is_full = []
    vault_inventory = {'itemHashes': vault_itemHashes, \
                       'itemIds': vault_itemIds, \
                       'bucket_hashes': vault_bucket_hashes, \
                       'bucket_type_hashes' : vault_bucket_type_hashes, \
                       'quantities': vault_quantities, \
                       'bucketsFull': vault_bucket_is_full}
                       
    bucket_hashes = {}    
    bucket_hashes_weapons = {}
    bucket_hashes_armor = {}
    bucket_hashes_general = {}
    bucket_hashes_vault = {}
    bucket_hashes_subclass = {}

    # Also this : https://destiny.plumbing/en/raw/DestinyInventoryBucketDefinition.json

    # Get itemHash of Heavy Ammo, find char/vault inventories index number.    
    # SELECT json->>'itemHash' FROM DestinyInventoryItemDefinition WHERE json->>'itemName'='Heavy Ammo Synthesis' limit 1;

    try:
        bucket_hashes_everything = dict(query_bungie_db("SELECT json->>'bucketName' AS bucketName, json->>'hash' AS bucketHash FROM DestinyInventoryBucketDefinition ORDER BY json->>'bucketName';"))
    except:
        bucket_hashes_everything = {
            'Armor':'3003523923',
            'Artifacts':'434908299',
            'Bounties':'2197472680',
            'Chest Armor':'14239492',
            'Class Armor':'1585787867',
            'Consumables':'1469714392',
            'Crucible Marks':'2689798310',
            'Currency':'3772930460',
            'Emblems':'4274335291',
            'Emotes':'3054419239',
            'Gauntlets':'3551918588',
            'General':'138197802',
            'Ghost':'4023194814',
            'Glimmer':'2689798308',
            'Heavy Weapons':'953998645',
            'Helmet':'3448274439',
            'Legacy Record Books':'549485690',
            'Leg Armor':'20886954',
            'Legendary Marks':'2689798304',
            'Lost Items':'215593132',
            'Materials':'3865314626',
            'Messages':'3161908920',
            'Mission':'375726501',
            'Ornaments':'3313201758',
            'Primary Weapons':'1498876634',
            'Quests':'1801258597',
            'Record Books':'2987185182',
            'Shaders':'2973005342',
            'Ships':'284967655',
            'Silver':'2689798311',
            'Sparrow Horn':'3796357825',
            'Special Orders':'1367666825',
            'Special Weapons':'2465295065',
            'Subclass':'3284755031',
            'Vanguard Marks':'2689798309',
            'Vehicle':'2025709351',
            'Weapons':'4046403665'
        }
        
    print(print_linenumber(), "           bucket_hashes_everything : " + str(bucket_hashes_everything)) 
    
    #bucket_hashes = dict(query_bungie_db("SELECT json->>'bucketName' AS bucketName, json->>'hash' AS bucketHash FROM DestinyInventoryBucketDefinition WHERE json->>'bucketName' = 'Primary Weapons' or json->>'bucketName' = 'Special Weapons' or json->>'bucketName' = 'Heavy Weapons' or json->>'bucketName' = 'Helmet' or json->>'bucketName' = 'Gauntlets' or json->>'bucketName' = 'Chest Armor' or json->>'bucketName' = 'Leg Armor' or json->>'bucketName' = 'Class Armor' or json->>'bucketName' = 'Artifacts' or json->>'bucketName' = 'Ghost' or json->>'bucketName' = 'Emblems' or json->>'bucketName' = 'Ships' or json->>'bucketName' = 'Shaders' or json->>'bucketName' = 'Emotes' or json->>'bucketName' = 'Vehicle' or json->>'bucketName' = 'Sparrow Horn' ORDER BY json->>'bucketName';"))
    #print(print_linenumber(), "                      bucket_hashes : " + str(bucket_hashes))
    keys = ['Primary Weapons', 'Special Weapons', 'Heavy Weapons', 'Helmet', 'Gauntlets', 'Chest Armor', 'Leg Armor', 'Class Armor', 'Artifacts', 'Ghost', 'Emblems', 'Ships', 'Shaders', 'Emotes', 'Vehicle', 'Sparrow Horn']
    bucket_hashes = {x:bucket_hashes_everything[x] for x in keys}
    
    #bucket_hashes_weapons = dict(query_bungie_db("SELECT json->>'bucketName' AS bucketName, json->>'hash' AS bucketHash FROM DestinyInventoryBucketDefinition WHERE json->>'bucketName' = 'Primary Weapons' or json->>'bucketName' = 'Special Weapons' or json->>'bucketName' = 'Heavy Weapons' ORDER BY json->>'bucketName';"))
    #print(print_linenumber(), "              bucket_hashes_weapons : " + str(bucket_hashes_weapons))
    keys = ['Primary Weapons', 'Special Weapons', 'Heavy Weapons']
    bucket_hashes_weapons = {x:bucket_hashes[x] for x in keys}
    
    #bucket_hashes_armor = dict(query_bungie_db("SELECT json->>'bucketName' AS bucketName, json->>'hash' AS bucketHash FROM DestinyInventoryBucketDefinition WHERE json->>'bucketName' = 'Helmet' or json->>'bucketName' = 'Gauntlets' or json->>'bucketName' = 'Chest Armor' or json->>'bucketName' = 'Leg Armor' or json->>'bucketName' = 'Class Armor' or json->>'bucketName' = 'Artifacts' or json->>'bucketName' = 'Ghost' ORDER BY json->>'bucketName';"))
    #print(print_linenumber(), "                bucket_hashes_armor : " + str(bucket_hashes_armor))
    keys = ['Helmet', 'Gauntlets', 'Chest Armor', 'Leg Armor', 'Class Armor', 'Artifacts', 'Ghost']
    bucket_hashes_armor = {x:bucket_hashes[x] for x in keys}
    
    #bucket_hashes_general = dict(query_bungie_db("SELECT json->>'bucketName' AS bucketName, json->>'hash' AS bucketHash FROM DestinyInventoryBucketDefinition WHERE json->>'bucketName' = 'Emblems' or json->>'bucketName' = 'Ships' or json->>'bucketName' = 'Shaders' or json->>'bucketName' = 'Emotes' or json->>'bucketName' = 'Vehicle' or json->>'bucketName' = 'Sparrow Horn' ORDER BY json->>'bucketName';"))
    #print(print_linenumber(), "            bucket_hashes_general : " + str(bucket_hashes_general))
    keys = ['Emblems', 'Ships', 'Shaders', 'Emotes', 'Vehicle', 'Sparrow Horn']
    bucket_hashes_general = {x:bucket_hashes[x] for x in keys}
    
    #bucket_hashes_vault = dict(query_bungie_db("SELECT json->>'bucketName' AS bucketName, json->>'hash' AS bucketHash FROM DestinyInventoryBucketDefinition WHERE json->>'bucketName' = 'Weapons' or json->>'bucketName' = 'Armor' or json->>'bucketName' = 'General' ORDER BY json->>'bucketName';"))
    #print(print_linenumber(), "                bucket_hashes_vault : " + str(bucket_hashes_vault))
    keys = ['Weapons', 'Armor', 'General']
    bucket_hashes_vault = {x:bucket_hashes_everything[x] for x in keys}
    
    #bucket_hashes_subclass = dict(query_bungie_db("SELECT json->>'bucketName' AS bucketName, json->>'hash' AS bucketHash FROM DestinyInventoryBucketDefinition WHERE json->>'bucketName' = 'Subclass' ORDER BY json->>'bucketName';"))
    #print(print_linenumber(), "             bucket_hashes_subclass : " + str(bucket_hashes_subclass))
    keys = ['Subclass']
    bucket_hashes_subclass = {x:bucket_hashes_everything[x] for x in keys}
    
    endpoint = "account_inventory_from_api"
    #account_inventory_from_api = call_api(endpoint, auth_token)['Response']['data']['items']
    account_inventory_from_api = call_api(endpoint, auth_token, data)
    print(print_linenumber(), "         account_inventory_from_api : " + str(account_inventory_from_api))

    try:
        test = account_inventory_from_api['Response']['data']['items']
    except:
        return account_inventory_from_api
        
    account_inventory_from_api = account_inventory_from_api['Response']['data']['items']
        
    # ADDING REAL BUCKET TYPES FROM QUERYING VAULT INSTEAD OF ITEMS
    # http://www.bungie.net/Platform/Destiny/{membershipType}/MyAccount/Vault/Summary/
    
    endpoint = "vault_inventory_from_api"
    #vault_inventory_from_api = call_api(endpoint, auth_token)['Response']['definitions']['items']
    vault_inventory_from_api = call_api(endpoint, auth_token, data)
    print(print_linenumber(), "         vault_inventory_from_api : " + str(vault_inventory_from_api))

    try:
        test = vault_inventory_from_api['Response']['definitions']['items']
    except:
        return vault_inventory_from_api

    vault_inventory_from_api = vault_inventory_from_api['Response']['definitions']['items']
    
    # print(print_linenumber(), "   vault_inventory_from_api : " + str(vault_inventory_from_api))

    for index, item in enumerate(account_inventory_from_api):
        #print(print_linenumber(), "                              index : " + str(index))
        #print(print_linenumber(), "                               item : " + str(item))
        
        if item['characterIndex'] == 0:
            #print(print_linenumber(), "        item['characterIndex'] == 0 : ")
            if item['transferStatus'] != 2 and str(item['bucketHash']) not in bucket_hashes_subclass.values():
                #print(print_linenumber(), "item['transferStatus'] != 2 and item['bucketHash'] not in bucket_hashes_subclass.values() : ")
                character_zero_transferStatus.append(item['transferStatus'])
                character_zero_itemHashes.append(item['itemHash'])
                character_zero_itemIds.append(item['itemId'])
                character_zero_characterIndices.append(item['characterIndex'])
                character_zero_quantities.append(item['quantity'])
                character_zero_bucket_hashes.append(item['bucketHash'])
        elif item['characterIndex'] == 1:
            #print(print_linenumber(), "        item['characterIndex'] == 1 : ")
            if item['transferStatus'] != 2 and str(item['bucketHash']) not in bucket_hashes_subclass.values():
                #print(print_linenumber(), "item['transferStatus'] != 2 and item['bucketHash'] not in bucket_hashes_subclass.values() : ")
                character_one_transferStatus.append(item['transferStatus'])
                character_one_itemHashes.append(item['itemHash'])
                character_one_itemIds.append(item['itemId'])
                character_one_characterIndices.append(item['characterIndex'])
                character_one_quantities.append(item['quantity'])
                character_one_bucket_hashes.append(item['bucketHash'])
        elif item['characterIndex'] == 2:
            #print(print_linenumber(), "        item['characterIndex'] == 2 : ")
            if item['transferStatus'] != 2 and str(item['bucketHash']) not in bucket_hashes_subclass.values():
                #print(print_linenumber(), "item['transferStatus'] != 2 and item['bucketHash'] not in bucket_hashes_subclass.values() : ")
                character_two_transferStatus.append(item['transferStatus'])
                character_two_itemHashes.append(item['itemHash'])
                character_two_itemIds.append(item['itemId'])
                character_two_characterIndices.append(item['characterIndex'])
                character_two_quantities.append(item['quantity'])
                character_two_bucket_hashes.append(item['bucketHash'])
        elif item['characterIndex'] == -1:
            #print(print_linenumber(), "                              index : " + str(index))
            #print(print_linenumber(), "                               item : " + str(item))
            #print(print_linenumber(), "        item['characterIndex'] == -1 : ")
            vault_itemHashes.append(item['itemHash'])
            vault_itemIds.append(item['itemId'])
            vault_characterIndices.append(item['characterIndex'])
            vault_quantities.append(item['quantity'])
            vault_bucket_type_hashes.append(item['bucketHash'])
            
            #print(print_linenumber(), "bucket_hashes_vault.values() : " + str(bucket_hashes_vault.values()))
            if str(item['bucketHash']) in bucket_hashes_vault.values():
                #print(print_linenumber(), "str(item['bucketHash']) in bucket_hashes_vault.values() : ")
                #print(print_linenumber(), "str(vault_inventory_from_api[str(item['itemHash'])]) : " + str(vault_inventory_from_api[str(item['itemHash'])]))
                #print(print_linenumber(), "str(vault_inventory_from_api[str(item['itemHash'])]['itemName'])) : " + str(vault_inventory_from_api[str(item['itemHash'])]['itemName']))
                #print(print_linenumber(), "str(vault_inventory_from_api[str(item['itemHash'])]['bucketTypeHash']) : " + str(vault_inventory_from_api[str(item['itemHash'])]['bucketTypeHash']))
                try:
                    vault_bucket_hashes.append(vault_inventory_from_api[str(item['itemHash'])]['bucketTypeHash'])
                except:
                    print("vault_bucket_hashes.append(vault_inventory_from_api[str(item['itemHash'])]['bucketTypeHash'])")
                    print(vault_inventory_from_api)
                    print(item['itemHash'])
                    print(vault_inventory_from_api[str(item['itemHash'])]['bucketTypeHash'])
            else:
                print(print_linenumber(), "str(item['bucketHash']) not in bucket_hashes_vault.values() : ")
                print(print_linenumber(), "                bucket_hashes_vault : " + str(bucket_hashes_vault))
                print(print_linenumber(), "                 item['bucketHash'] : " + str(item['bucketHash']))
        else:
            print(print_linenumber(), "                                ERROR : This should never happen.  Character index for item was not 0, 1, 2, or -1.  ")
            print(print_linenumber(), "               item['characterIndex'] : " + str(item['characterIndex']))

    print(print_linenumber(), "           character_zero_inventory : " + str(character_zero_inventory))
    print(print_linenumber(), "            character_one_inventory : " + str(character_one_inventory))
    print(print_linenumber(), "            character_two_inventory : " + str(character_two_inventory))
    print(print_linenumber(), "                    vault_inventory : " + str(vault_inventory))

    return character_zero_inventory, character_one_inventory, \
           character_two_inventory, vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault, bucket_hashes_subclass


def mark_full_inventories(character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault):
    print(print_linenumber(), "     FUNCTION : mark_full_inventories : " + str(datetime.datetime.now()).split('.')[0])
    #print(print_linenumber(), "              : mark_full_inventories        : character_zero_inventory : " + str(character_zero_inventory))
    #print(print_linenumber(), "              : mark_full_inventories        : character_one_inventory  : " + str(character_one_inventory))
    #print(print_linenumber(), "              : mark_full_inventories        : character_two_inventory  : " + str(character_two_inventory))
    #print(print_linenumber(), "              : mark_full_inventories        : vault_inventory          : " + str(vault_inventory))
    #print(print_linenumber(), "              : mark_full_inventories        : bucket_hashes            : " + str(bucket_hashes))

    print('Character Zero Full Buckets : ' + str(character_zero_inventory['bucketsFull']))
    print( 'Character One Full Buckets : ' + str(character_one_inventory['bucketsFull']))
    print(' Character Two Full Buckets : ' + str(character_two_inventory['bucketsFull']))
    print(         'Vault Full Buckets : ' + str(vault_inventory['bucketsFull']))   

    character_zero_inventory['bucketsFull'] = []
    character_one_inventory['bucketsFull'] = []
    character_two_inventory['bucketsFull'] = []
    vault_inventory['bucketsFull'] = []
    
    max_items = 10
    bucket_types_max_ten = ["Primary Weapons", "Special Weapons", "Heavy Weapons", \
    "Ghost", "Helmet", "Gauntlets", "Chest Armor", "Leg Armor", "Class Armor", \
    "Artifacts", "Emblems", "Emotes", "Shaders", "Ships", "Vehicle"]
    for bucket_type in bucket_types_max_ten:
        character_zero_inventory = is_bucket_full(character_zero_inventory, bucket_hashes, bucket_type, max_items, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault)
        character_one_inventory = is_bucket_full(character_one_inventory, bucket_hashes, bucket_type, max_items, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault)
        character_two_inventory = is_bucket_full(character_two_inventory, bucket_hashes, bucket_type, max_items, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault) 
        
    max_items = 108
    bucket_types_max_one_zero_eight = ["Armor", "Weapons"]
    for bucket_type in bucket_types_max_one_zero_eight:
        vault_inventory = is_bucket_full(vault_inventory, bucket_hashes, bucket_type, max_items, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault)

    max_items = 72
    bucket_types_max_seventy_two = ["General"]
    for bucket_type in bucket_types_max_seventy_two:
        vault_inventory = is_bucket_full(vault_inventory, bucket_hashes, bucket_type, max_items, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault)    

        if "Primary Weapons" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "  char zero bucketsFull : Primary Weapons")
        if "Special Weapons" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "  char zero bucketsFull : Special Weapons")
        if "Heavy Weapons" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "  char zero bucketsFull : Heavy Weapons")
        if "Ghost" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "  char zero bucketsFull : Ghost")
            
        if "Helmet" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "  char zero bucketsFull : Helmet")
        if "Gauntlets" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "  char zero bucketsFull : Gauntlets")
        if "Chest Armor" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "  char zero bucketsFull : Chest Armor")
        if "Leg Armor" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "  char zero bucketsFull : Leg Armor")
        if "Class Armor" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "  char zero bucketsFull : Class Armor")
        if "Artifacts" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "  char zero bucketsFull : Artifacts")

        if "Emblems" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "  char zero bucketsFull : Emblems")
        if "Shaders" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "  char zero bucketsFull : Shaders")
        if "Emotes" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "  char zero bucketsFull : Emotes")
        if "Ships" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "  char zero bucketsFull : Ships")
        if "Vehicle" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "  char zero bucketsFull : Vehicle")
        if "Sparrow Horn" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "  char zero bucketsFull : Sparrow Horn")

        if "Primary Weapons" in character_one_inventory['bucketsFull']:
            print(print_linenumber(), "   char one bucketsFull : Primary Weapons")
        if "Special Weapons" in character_one_inventory['bucketsFull']:
            print(print_linenumber(), "   char one bucketsFull : Special Weapons")
        if "Heavy Weapons" in character_one_inventory['bucketsFull']:
            print(print_linenumber(), "   char one bucketsFull : Heavy Weapons")
        if "Ghost" in character_one_inventory['bucketsFull']:
            print(print_linenumber(), "   char one bucketsFull : Ghost")
            
        if "Helmet" in character_one_inventory['bucketsFull']:
            print(print_linenumber(), "   char one bucketsFull : Helmet")
        if "Gauntlets" in character_one_inventory['bucketsFull']:
            print(print_linenumber(), "   char one bucketsFull : Gauntlets")
        if "Chest Armor" in character_one_inventory['bucketsFull']:
            print(print_linenumber(), "   char one bucketsFull : Chest Armor")
        if "Leg Armor" in character_one_inventory['bucketsFull']:
            print(print_linenumber(), "   char one bucketsFull : Leg Armor")
        if "Class Armor" in character_one_inventory['bucketsFull']:
            print(print_linenumber(), "   char one bucketsFull : Class Armor")
        if "Artifacts" in character_one_inventory['bucketsFull']:
            print(print_linenumber(), "   char one bucketsFull : Artifacts")

        if "Emblems" in character_one_inventory['bucketsFull']:
            print(print_linenumber(), "   char one bucketsFull : Emblems")
        if "Shaders" in character_one_inventory['bucketsFull']:
            print(print_linenumber(), "   char one bucketsFull : Shaders")
        if "Emotes" in character_one_inventory['bucketsFull']:
            print(print_linenumber(), "   char one bucketsFull : Emotes")
        if "Ships" in character_one_inventory['bucketsFull']:
            print(print_linenumber(), "   char one bucketsFull : Ships")
        if "Vehicle" in character_one_inventory['bucketsFull']:
            print(print_linenumber(), "   char one bucketsFull : Vehicle")
        if "Sparrow Horn" in character_one_inventory['bucketsFull']:
            print(print_linenumber(), "   char one bucketsFull : Sparrow Horn")
            
        if "Primary Weapons" in character_two_inventory['bucketsFull']:
            print(print_linenumber(), "   char two bucketsFull : Primary Weapons")
        if "Special Weapons" in character_two_inventory['bucketsFull']:
            print(print_linenumber(), "   char two bucketsFull : Special Weapons")
        if "Heavy Weapons" in character_two_inventory['bucketsFull']:
            print(print_linenumber(), "   char two bucketsFull : Heavy Weapons")
        if "Ghost" in character_two_inventory['bucketsFull']:
            print(print_linenumber(), "   char two bucketsFull : Ghost")
            
        if "Helmet" in character_two_inventory['bucketsFull']:
            print(print_linenumber(), "   char two bucketsFull : Helmet")
        if "Gauntlets" in character_two_inventory['bucketsFull']:
            print(print_linenumber(), "   char two bucketsFull : Gauntlets")
        if "Chest Armor" in character_two_inventory['bucketsFull']:
            print(print_linenumber(), "   char two bucketsFull : Chest Armor")
        if "Leg Armor" in character_two_inventory['bucketsFull']:
            print(print_linenumber(), "   char two bucketsFull : Leg Armor")
        if "Class Armor" in character_two_inventory['bucketsFull']:
            print(print_linenumber(), "   char two bucketsFull : Class Armor")
        if "Artifacts" in character_two_inventory['bucketsFull']:
            print(print_linenumber(), "   char two bucketsFull : Artifacts")

        if "Emblems" in character_two_inventory['bucketsFull']:
            print(print_linenumber(), "   char two bucketsFull : Emblems")
        if "Shaders" in character_two_inventory['bucketsFull']:
            print(print_linenumber(), "   char two bucketsFull : Shaders")
        if "Emotes" in character_two_inventory['bucketsFull']:
            print(print_linenumber(), "   char two bucketsFull : Emotes")
        if "Ships" in character_two_inventory['bucketsFull']:
            print(print_linenumber(), "   char two bucketsFull : Ships")
        if "Vehicle" in character_two_inventory['bucketsFull']:
            print(print_linenumber(), "   char two bucketsFull : Vehicle")
        if "Sparrow Horn" in character_two_inventory['bucketsFull']:
            print(print_linenumber(), "   char two bucketsFull : Sparrow Horn")
            
        if "Weapons" in vault_inventory['bucketsFull']:
            print(print_linenumber(), "      vault bucketsFull : Weapons")
        if "Armor" in vault_inventory['bucketsFull']:
            print(print_linenumber(), "      vault bucketsFull : Armor")
        if "General" in vault_inventory['bucketsFull']:
            print(print_linenumber(), "      vault bucketsFull : General")

    return character_zero_inventory, character_one_inventory, \
           character_two_inventory, vault_inventory
           

def save_loadout(user_info, loadout_name, equipped_items, value, timestamp):
    print(print_linenumber(), "     FUNCTION : save_loadout : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              : save_loadout                 : user_info                : " + str(user_info))
    print(print_linenumber(), "              : save_loadout                 : loadout_name             : " + str(loadout_name))
    print(print_linenumber(), "              : save_loadout                 : equipped_items           : " + str(equipped_items))
    print(print_linenumber(), "              : save_loadout                 : value                    : " + str(value))
    print(print_linenumber(), "              : save_loadout                 : timestamp                : " + str(timestamp))

    global db_host
    global db_name_alexa
    global db_user
    global db_pass
    global db_port
    
    print(print_linenumber(), "                     equipped_items : " + str(equipped_items))
    equipped_items_encoded = pickle.dumps(equipped_items).encode('base64', 'strict')
    
    conn = None
    conn = psycopg2.connect(host=db_host, database=db_name_alexa, user=db_user, \
                            password=db_pass, port=db_port)
    cur = conn.cursor()
    
    if loadout_name == "FAVORITE":
        loadout_encoded = query_alexa_db("SELECT equipped_items FROM public.loadouts WHERE membership_id_bungie = '" + str(user_info['membership_id_bungie']) + "' AND membership_type =  '" + str(user_info['membership_type']) + "' AND membership_id = '" + str(user_info['membership_id']) + "' AND character_id = '" + str(user_info['character_zero_id']) + "' AND loadout_name = '" + str(loadout_name) + "';")

        if loadout_encoded == []:
            card_title = app_title + " : FAILED : Can't Equip loadout, no loadout found."
            speech = "No loadout for " + loadout_name.replace("_", " ").title() + \
            " has been saved on this character.  Loadouts are character specific."
            end_session = True
            return alexa_speak(card_title, speech, end_session)        
        
        loadout_encoded = loadout_encoded[0]
        loadout_encoded = loadout_encoded[0]
        favorite_items = dict(pickle.loads(loadout_encoded.decode('base64', 'strict')))

        if value == "emblem":
            bucket_hash = query_bungie_db("SELECT json->>'hash' AS bucketHash FROM DestinyInventoryBucketDefinition WHERE json->>'bucketName' = 'Emblems';")[0]
            bucket_hash = int(bucket_hash[0])

            position = equipped_items.get('bucket_hash').index(bucket_hash)
            exotic_item = equipped_items.get('exotic_item')[position]
            itemId = equipped_items.get('itemId')[position]
            itemHash = equipped_items.get('itemHash')[position]
            
            position = favorite_items.get('bucket_hash').index(bucket_hash)
            favorite_items['exotic_item'][position] = exotic_item
            favorite_items['itemId'][position] = itemId
            favorite_items['itemHash'][position] = itemHash

            equipped_items = favorite_items
            equipped_items_encoded = pickle.dumps(equipped_items).encode('base64', 'strict')
            
        elif value == "emote":
            # bucket_hash = '3054419239'
            bucket_hash = query_bungie_db("SELECT json->>'hash' AS bucketHash FROM DestinyInventoryBucketDefinition WHERE json->>'bucketName' = 'Emotes';")[0]
            bucket_hash = int(bucket_hash[0])
           
            position = equipped_items.get('bucket_hash').index(bucket_hash)
            exotic_item = equipped_items.get('exotic_item')[position]
            itemId = equipped_items.get('itemId')[position]
            itemHash = equipped_items.get('itemHash')[position]
            
            position = favorite_items.get('bucket_hash').index(bucket_hash)
            favorite_items['exotic_item'][position] = exotic_item
            favorite_items['itemId'][position] = itemId
            favorite_items['itemHash'][position] = itemHash

            equipped_items = favorite_items
            equipped_items_encoded = pickle.dumps(equipped_items).encode('base64', 'strict')          
        elif value == "ghost":
            # bucket_hash = '4023194814'
            bucket_hash = query_bungie_db("SELECT json->>'hash' AS bucketHash FROM DestinyInventoryBucketDefinition WHERE json->>'bucketName' = 'Ghost';")[0]
            bucket_hash = int(bucket_hash[0])
            
            position = equipped_items.get('bucket_hash').index(bucket_hash)
            exotic_item = equipped_items.get('exotic_item')[position]
            itemId = equipped_items.get('itemId')[position]
            itemHash = equipped_items.get('itemHash')[position]
            
            position = favorite_items.get('bucket_hash').index(bucket_hash)
            favorite_items['exotic_item'][position] = exotic_item
            favorite_items['itemId'][position] = itemId
            favorite_items['itemHash'][position] = itemHash

            equipped_items = favorite_items
            equipped_items_encoded = pickle.dumps(equipped_items).encode('base64', 'strict')             
        elif value == "shader":
            # bucket_hash = '2973005342'
            bucket_hash = query_bungie_db("SELECT json->>'hash' AS bucketHash FROM DestinyInventoryBucketDefinition WHERE json->>'bucketName' = 'Shaders';")[0]
            bucket_hash = int(bucket_hash[0])
            
            position = equipped_items.get('bucket_hash').index(bucket_hash)
            exotic_item = equipped_items.get('exotic_item')[position]
            itemId = equipped_items.get('itemId')[position]
            itemHash = equipped_items.get('itemHash')[position]
            
            position = favorite_items.get('bucket_hash').index(bucket_hash)
            favorite_items['exotic_item'][position] = exotic_item
            favorite_items['itemId'][position] = itemId
            favorite_items['itemHash'][position] = itemHash

            equipped_items = favorite_items
            equipped_items_encoded = pickle.dumps(equipped_items).encode('base64', 'strict')  
        elif value == "ship":
            # bucket_hash = '284967655'
            bucket_hash = query_bungie_db("SELECT json->>'hash' AS bucketHash FROM DestinyInventoryBucketDefinition WHERE json->>'bucketName' = 'Ships';")[0]
            bucket_hash = int(bucket_hash[0])
            
            position = equipped_items.get('bucket_hash').index(bucket_hash)
            exotic_item = equipped_items.get('exotic_item')[position]
            itemId = equipped_items.get('itemId')[position]
            itemHash = equipped_items.get('itemHash')[position]
            
            position = favorite_items.get('bucket_hash').index(bucket_hash)
            favorite_items['exotic_item'][position] = exotic_item
            favorite_items['itemId'][position] = itemId
            favorite_items['itemHash'][position] = itemHash

            equipped_items = favorite_items
            equipped_items_encoded = pickle.dumps(equipped_items).encode('base64', 'strict')              
        elif value == "subclass":
            # bucket_hash = '3284755031'
            bucket_hash = query_bungie_db("SELECT json->>'hash' AS bucketHash FROM DestinyInventoryBucketDefinition WHERE json->>'bucketName' = 'Subclass';")[0]
            bucket_hash = int(bucket_hash[0])
            
            position = equipped_items.get('bucket_hash').index(bucket_hash)
            exotic_item = equipped_items.get('exotic_item')[position]
            itemId = equipped_items.get('itemId')[position]
            itemHash = equipped_items.get('itemHash')[position]
            
            position = favorite_items.get('bucket_hash').index(bucket_hash)
            favorite_items['exotic_item'][position] = exotic_item
            favorite_items['itemId'][position] = itemId
            favorite_items['itemHash'][position] = itemHash

            equipped_items = favorite_items
            equipped_items_encoded = pickle.dumps(equipped_items).encode('base64', 'strict')             
        elif value == "sparrow":
            # bucket_hash = '2025709351'
            bucket_hash = query_bungie_db("SELECT json->>'hash' AS bucketHash FROM DestinyInventoryBucketDefinition WHERE json->>'bucketName' = 'Vehicle';")[0]
            bucket_hash = int(bucket_hash[0])
            
            position = equipped_items.get('bucket_hash').index(bucket_hash)
            exotic_item = equipped_items.get('exotic_item')[position]
            itemId = equipped_items.get('itemId')[position]
            itemHash = equipped_items.get('itemHash')[position]
            
            position = favorite_items.get('bucket_hash').index(bucket_hash)
            favorite_items['exotic_item'][position] = exotic_item
            favorite_items['itemId'][position] = itemId
            favorite_items['itemHash'][position] = itemHash

            equipped_items = favorite_items
            equipped_items_encoded = pickle.dumps(equipped_items).encode('base64', 'strict')                
            
        print(print_linenumber(), "                     favorite_items : " + str(favorite_items))

    # SEE IF LOADOUT ALREADY EXISTS FOR CHARACTER ZERO
    exists_character_zero = query_alexa_db("SELECT equipped_items FROM public.loadouts WHERE membership_id_bungie = '" + str(user_info['membership_id_bungie']) + "' AND membership_type =  '" + str(user_info['membership_type']) + "' AND membership_id = '" + str(user_info['membership_id']) + "' AND character_id = '" + str(user_info['character_zero_id']) + "' AND loadout_name = '" + str(loadout_name) + "';")

    # SEE IF LOADOUT ALREADY EXISTS FOR CHARACTER ONE
    exists_character_one = query_alexa_db("SELECT equipped_items FROM public.loadouts WHERE membership_id_bungie = '" + str(user_info['membership_id_bungie']) + "' AND membership_type =  '" + str(user_info['membership_type']) + "' AND membership_id = '" + str(user_info['membership_id']) + "' AND character_id = '" + str(user_info['character_one_id']) + "' AND loadout_name = '" + str(loadout_name) + "';")
    
    # SEE IF LOADOUT ALREADY EXISTS FOR CHARACTER TWO
    exists_character_two = query_alexa_db("SELECT equipped_items FROM public.loadouts WHERE membership_id_bungie = '" + str(user_info['membership_id_bungie']) + "' AND membership_type =  '" + str(user_info['membership_type']) + "' AND membership_id = '" + str(user_info['membership_id']) + "' AND character_id = '" + str(user_info['character_two_id']) + "' AND loadout_name = '" + str(loadout_name) + "';")

    if exists_character_zero:
        # UPDATE LOADOUT TO NEW LIST OF ITEMS
        sql = "UPDATE public.loadouts SET equipped_items = '" + str(equipped_items_encoded) + "' WHERE membership_id_bungie = '" + str(user_info['membership_id_bungie']) + "' AND membership_type =  '" + str(user_info['membership_type']) + "' AND membership_id = '" + str(user_info['membership_id']) + "' AND character_id = '" + str(user_info['character_zero_id']) + "' AND loadout_name = '" + str(loadout_name) + "';"
        cur.execute(sql)
        
        # UPDATE TIMESTAMP TO LAST MODIFIED DATE
        sql = "UPDATE public.loadouts SET timestamp = '" + str(timestamp) + "' WHERE membership_id_bungie = '" + str(user_info['membership_id_bungie']) + "' AND membership_type =  '" + str(user_info['membership_type']) + "' AND membership_id = '" + str(user_info['membership_id']) + "' AND character_id = '" + str(user_info['character_zero_id']) + "' AND loadout_name = '" + str(loadout_name) + "';"
        cur.execute(sql)
    else:
        # INSERT NEW LOADOUT INTO DB
        sql = "INSERT INTO public.loadouts (membership_id_bungie, display_name, membership_type, membership_id, character_id, character_race, character_gender, character_class, loadout_name, equipped_items, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cur.execute(sql, (user_info['membership_id_bungie'], user_info['display_name'], user_info['membership_type'], user_info['membership_id'], user_info['character_zero_id'], user_info['character_zero_race'], user_info['character_zero_gender'], user_info['character_zero_class'], loadout_name, equipped_items_encoded, timestamp))
    
    if not exists_character_one:
        # INSERT NEW LOADOUT INTO DB
        sql = "INSERT INTO public.loadouts (membership_id_bungie, display_name, membership_type, membership_id, character_id, character_race, character_gender, character_class, loadout_name, equipped_items, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cur.execute(sql, (user_info['membership_id_bungie'], user_info['display_name'], user_info['membership_type'], user_info['membership_id'], user_info['character_one_id'], user_info['character_one_race'], user_info['character_one_gender'], user_info['character_one_class'], loadout_name, equipped_items_encoded, timestamp))

    if not exists_character_two:
        # INSERT NEW LOADOUT INTO DB
        sql = "INSERT INTO public.loadouts (membership_id_bungie, display_name, membership_type, membership_id, character_id, character_race, character_gender, character_class, loadout_name, equipped_items, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cur.execute(sql, (user_info['membership_id_bungie'], user_info['display_name'], user_info['membership_type'], user_info['membership_id'], user_info['character_two_id'], user_info['character_two_race'], user_info['character_two_gender'], user_info['character_two_class'], loadout_name, equipped_items_encoded, timestamp))
        
    cur.close()
    conn.commit()
    conn.close()

    if value == "subclass" or value == "sparrow" or value == "ship" or value == "shader" or value == "emote" or value == "emblem" or value == "ghost":
        if loadout_name == "FAVORITE":
            speech = "Saved " + loadout_name.replace("_", " ").title() + " " + str(value) + "."
        else:
            speech = "Loadout Saved for " + loadout_name.replace("_", " ").title() + "."
    else:
        speech = "Loadout Saved for " + loadout_name.replace("_", " ").title() + "."
        
    card_title = app_title + " : SUCCESS : Loadout Saved."
    end_session = True
    return alexa_speak(card_title, speech, end_session)


def equip_loadout(auth_token, loadout_name, equipped_items, user_info, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault, bucket_hashes_subclass):
    print(print_linenumber(), "     FUNCTION :       equip_loadout : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              :       equip_loadout          : loadout_name             : " + str(loadout_name))
    print(print_linenumber(), "              :       equip_loadout          : equipped_items           : " + str(equipped_items))
    print(print_linenumber(), "              :       equip_loadout          : user_info                : " + str(user_info))
    print(print_linenumber(), "              :       equip_loadout          : bucket_hashes            : " + str(bucket_hashes))
    #print(print_linenumber(), "              :       equip_loadout          : character_zero_inventory : " + str(character_zero_inventory))
    #print(print_linenumber(), "              :       equip_loadout          : character_one_inventory  : " + str(character_one_inventory))
    #print(print_linenumber(), "              :       equip_loadout          : character_two_inventory  : " + str(character_two_inventory))
    #print(print_linenumber(), "              :       equip_loadout          : vault_inventory          : " + str(vault_inventory))
    
    global db_host
    global db_name_alexa
    global db_user
    global db_pass
    global db_port

    # user_info['display_name'], user_info['membership_id_bungie'], user_info['membership_type'], user_info['membership_id'], user_info['character_zero_id'], user_info['character_zero_race'], user_info['character_zero_gender'], user_info['character_zero_class'], 

    list_of_items_to_equip = ""

    conn = None
    conn = psycopg2.connect(host=db_host, database=db_name_alexa, user=db_user, \
                            password=db_pass, port=db_port)
    cur = conn.cursor()
    
    loadout_encoded = query_alexa_db("SELECT equipped_items FROM public.loadouts WHERE membership_id_bungie = '" + str(membership_id_bungie) + "' AND membership_type =  '" + str(membership_type) + "' AND membership_id = '" + str(membership_id) + "' AND character_id = '" + str(character_id) + "' AND loadout_name = '" + str(loadout_name) + "';")
    
    if loadout_encoded == []:
        card_title = app_title + " : FAILED : Can't Equip loadout, no loadout found."
        speech = "No loadout for " + loadout_name.replace("_", " ").title() + \
        " has been saved on this character.  Loadouts are character specific."
        end_session = True
        return alexa_speak(card_title, speech, end_session)        
    
    loadout_encoded = loadout_encoded[0]
    loadout_encoded = loadout_encoded[0]
    loadout_decoded = dict(pickle.loads(loadout_encoded.decode('base64', 'strict')))
    
    print(print_linenumber(), "                    equipped_items  : " + str(equipped_items))
    print(print_linenumber(), "                    loadout_decoded : " + str(loadout_decoded))

    cur.close()
    conn.commit()
    conn.close()
    
    # Make loadout_decoded become equipped_items
    # DO THIS FOR EXOTICS FIRST TO AVOID EXOTIC RACE CONDITION
    for x in range(0,2):    
        for key, value in enumerate(equipped_items['exotic_item']):
            #print(print_linenumber(), "                                key : " + str(key))
            #print(print_linenumber(), "                              value : " + str(value))
            if value == x:
                print(print_linenumber(), "                     value == " + str(x) + " : ")
                # IF ONE, EXOTIC ITEM EQUIPPED IN THIS SLOT
                if x == 1:
                    print(print_linenumber(), "                    Exotic Equipped : " + str(equipped_items['itemHash'][key]))
                    print(print_linenumber(), "                     Replace Exotic : " + str(loadout_decoded['itemHash'][key]))
                elif x == 0:
                    print(print_linenumber(), "             Non-Exotic Equipped : " + str(equipped_items['itemHash'][key]))
                    print(print_linenumber(), "              Replace Non-Exotic : " + str(loadout_decoded['itemHash'][key]))
                else:
                    print(print_linenumber(), "ERROR : An item should always be exotic or non-exotic, you should never see this.")
                itemId = loadout_decoded['itemId'][key]
                itemHash = loadout_decoded['itemHash'][key]
                if equipped_items['itemId'][key] == itemId:
                    #print(print_linenumber(), "equipped_items['itemId'][key] == itemId : ")
                    # SAME ITEM EQUIPPED AS IN LOADOUT, SO DO NOTHING
                    print(print_linenumber(), "                               INFO : This item in loadout is same as one already equipped, no action necessary: " + str(equipped_items['itemHash'][key]))
                else:
                    #print(print_linenumber(), "equipped_items['itemId'][key] <> itemId : ")
                    # FIND CHARACTER ID OF ITEM TO EQUIP LOCATION
                    location_id = find_item_location(user_info, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, itemId, itemHash)
                    #print(print_linenumber(), "location_id : " + str(location_id))
                    #print(print_linenumber(), "user_info['character_zero_id'] : " + str(user_info['character_zero_id']))
                    if str(location_id) == (user_info['character_zero_id']):
                        #print(print_linenumber(), "location_id == user_info['character_zero_id'] : ")
                        # THE ITEM IS LOCATED ON THIS CHARACTER, JUST NOT EQUIPPED YET
                        print(print_linenumber(), "                               INFO : This item is already on this character, no transfer necessary: " + str(equipped_items['itemHash'][key]))
                    else:
                        #print(print_linenumber(), "location_id <> user_info['character_zero_id'] : ")
                        # DO THE TRANSFER SHUFFLE
                        bucket_hash = equipped_items['bucket_hash'][key]

                        # FIND TYPE OF BUCKET FOR A GENERIC ONE
                        #bucket_type = next(find_dict_key_by_value(bucket_hashes, str(equipped_items['bucket_hash'][key])), None)
                        if str(bucket_hash) in bucket_hashes_weapons.values():
                            #print(print_linenumber(), "str(bucket_hash) in bucket_hashes_weapons.values() : ")
                            bucket_type = next(find_dict_key_by_value(bucket_hashes_weapons, str(bucket_hash)), None)
                            vault_bucket_type = "Weapons"
                        elif str(bucket_hash) in bucket_hashes_armor.values():
                            #print(print_linenumber(), "str(bucket_hash) in bucket_hashes_armor.values() : ")
                            bucket_type = next(find_dict_key_by_value(bucket_hashes_armor, str(bucket_hash)), None)
                            vault_bucket_type = "Armor"
                        elif str(bucket_hash) in bucket_hashes_general.values():
                            #print(print_linenumber(), "str(bucket_hash) in bucket_hashes_general.values() : ")
                            bucket_type = next(find_dict_key_by_value(bucket_hashes_general, str(bucket_hash)), None)
                            vault_bucket_type = "General"
                        elif str(bucket_hash) in bucket_hashes_subclass.values():
                            #print(print_linenumber(), "str(bucket_hash) in bucket_hashes_subclass.values() : ")
                            bucket_type = "Subclass"
                        elif str(bucket_hash) in bucket_hashes_vault.values():
                            #print(print_linenumber(), "str(bucket_hash) in bucket_hashes_vault.values() : ")
                            bucket_type = "Vault"
                            vault_bucket_type = "Vault"
                        else:
                            print(print_linenumber(), "str(bucket_hash) not found in any bucket_hashes : ")
                            print(print_linenumber(), "str(bucket_hash) : " + str(bucket_hash))
                        
                        if bucket_hash > 0:
                            if bucket_type in character_zero_inventory['bucketsFull']:
                                # THIS CHARACTER IS FULL OF THIS TYPE OF ITEM
                                # NEED TO MAKE THIS CHARACTER NOT FULL

                                free_vault_space(auth_token, loadout_name, equipped_items, user_info, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, vault_bucket_type, bucket_type, bucket_hash, bucket_hashes)
                                mark_full_inventories(character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault)
                                
                                # VAULT HAS SPACE NOW, TRANSFER A RANDOM ITEM AWAY TO VAULT
                                counter = 0
                                for bucket_hash_key, bucket_hash_value in enumerate(character_zero_inventory['bucket_hashes']):
                                    #print(print_linenumber(), "                                key : " + str(key))
                                    #print(print_linenumber(), "                              value : " + str(value))
                                    #print(print_linenumber(), "                    bucket_hash_key : " + str(bucket_hash_key))
                                    #print(print_linenumber(), "                  bucket_hash_value : " + str(bucket_hash_value))
                                    if bucket_hash_value == bucket_hash and counter == 0:
                                        #print(print_linenumber(), "bucket_hash_value == bucket_hash and counter == 0 : ")
                                        other_itemId = character_zero_inventory['itemIds'][bucket_hash_key]
                                        other_itemHash = character_zero_inventory['itemHashes'][bucket_hash_key]
                                        print(print_linenumber(), "                       other_itemId : " + str(other_itemId))
                                        print(print_linenumber(), "                     other_itemHash : " + str(other_itemHash))
                                        if equipped_items['itemId'][key] != other_itemId and loadout_decoded['itemId'][key] != other_itemId and counter == 0:
                                            #print(print_linenumber(), "equipped_items['itemId'][key] != other_itemId and loadout_decoded['itemId'][key] != other_itemId and counter == 0 : ")
                                            counter = 1
                                            #print(print_linenumber(), "                            counter : " + str(counter))
                                            # MOVE THIS other_itemId to vault to make room on character
                                            transfer_item(auth_token, other_itemHash, other_itemId, user_info['character_zero_id'], membership_type, "true")
                                            mark_full_inventories(character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault)

                                free_vault_space(auth_token, loadout_name, equipped_items, user_info, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, vault_bucket_type, bucket_type, bucket_hash, bucket_hashes)
                                mark_full_inventories(character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault)
                                
                            # FINALLY MOVE THE REAL ITEM TO VAULT FROM OTHER CHARACTER (-1 is vault location)
                            if str(location_id) == (user_info['character_one_id']) or str(location_id) == (user_info['character_two_id']):
                                #print(print_linenumber(), "                location_id > 0 : ")
                                transfer_item(auth_token, itemHash, itemId, location_id, membership_type, "true")
                                mark_full_inventories(character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault)                    
                            
                            if int(location_id) == 0:
                                print(print_linenumber(), "                           itemHash : " + str(itemHash))
                                print(print_linenumber(), "                             itemId : " + str(itemId))
                                print(print_linenumber(), "INFO : It appears this item has been deleted.  Can't find it.")
                            elif int(location_id) == -1:
                                # THEN MOVE ITEM FROM VAULT TO CHARACTER ZERO (-1 is vault location)
                                transfer_item(auth_token, itemHash, itemId, user_info['character_zero_id'], membership_type, "false")
                                mark_full_inventories(character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault)     
                            else:
                                print(print_linenumber(), "                           itemHash : " + str(itemHash))
                                print(print_linenumber(), "                             itemId : " + str(itemId))
                                print(print_linenumber(), "ERROR : Should never see this, all other possibilities for item location should be accounted for.")                                
    
                    # NOW THAT ITEM IS TRANSFERRED TO CHARACTER, EQUIP IT.
                    if list_of_items_to_equip:
                        list_of_items_to_equip = list_of_items_to_equip + ',"' + str(itemId) + '"'
                    else:
                        list_of_items_to_equip = '"' + str(itemId) + '"'

    equip_items(auth_token, list_of_items_to_equip, user_info['character_zero_id'], membership_type)                    
    card_title = app_title + " : SUCCESS : Loadout Equipped."
    if loadout_name.upper() == "TRIALS":
        speech = "Loadout Equipped for " + loadout_name.replace("_", " ").title() + \
        ".  Don't forget to buy your boons."
    elif loadout_name.upper() == "IRON_BANNER":
        speech = "Loadout Equipped for " + loadout_name.replace("_", " ").title() + \
        ".  Show them no mercy."
    elif loadout_name.upper() == "COMPETITIVE_PLAY":
        speech = "Loadout Equipped for " + loadout_name.replace("_", " ").title() + \
        ".  Show them no mercy."
    elif loadout_name.upper() == "QUICK_PLAY":
        speech = "Loadout Equipped for " + loadout_name.replace("_", " ").title() + \
        ".  Have Fun."
    elif loadout_name.upper() == "STRIKE":
        speech = "Loadout Equipped for " + loadout_name.replace("_", " ").title() + \
        ".  Defeat the minons of the darkness."
    elif loadout_name.upper() == "PATROL":
        speech = "Loadout Equipped for " + loadout_name.replace("_", " ").title() + \
        ".  Have Fun."
    elif loadout_name.upper() == "FAVORITE":
        speech = "Loadout Equipped for " + loadout_name.replace("_", " ").title() + \
        ".  It's amazing!"
    elif loadout_name.upper() == "DESOLATE":
        speech = "Loadout Equipped for " + loadout_name.replace("_", " ").title() + \
        ".  You're Taken now."
    elif loadout_name.upper() == "VAULT_OF_GLASS":
        speech = "Loadout Equipped for " + loadout_name.replace("_", " ").title() + \
        ".  Atheon will fall."
    elif loadout_name.upper() == "CROTAS_END":
        speech = "Loadout Equipped for " + loadout_name.replace("_", " ").title() + \
        ".  Who's going to carry the sword?"
    elif loadout_name.upper() == "KINGS_FALL":
        speech = "Loadout Equipped for " + loadout_name.replace("_", " ").title() + \
        ".  Go slay The Taken King."
    elif loadout_name.upper() == "WRATH_OF_THE_MACHINE":
        speech = "Loadout Equipped for " + loadout_name.replace("_", " ").title() + \
        ".  Siva is no match for you."
    elif loadout_name.upper() == "LEVIATHAN":
        speech = "Loadout Equipped for " + loadout_name.replace("_", " ").title() + \
        ".  Enter the belly of the beast."
    elif loadout_name.upper() == "ARC_BURN":
        speech = "Loadout Equipped for " + loadout_name.replace("_", " ").title() + \
        ".  Electrifying isn't it?"
    elif loadout_name.upper() == "SOLAR_BURN":
        speech = "Loadout Equipped for " + loadout_name.replace("_", " ").title() + \
        ".  Burn your enemies with fire."
    elif loadout_name.upper() == "VOID_BURN":
        speech = "Loadout Equipped for " + loadout_name.replace("_", " ").title() + \
        ".  Destroy minions with the power of void."
    else:
        speech = "Loadout Equipped for " + loadout_name.replace("_", " ").title() + "."
    
    end_session = True
    return alexa_speak(card_title, speech, end_session)


def free_vault_space(auth_token, loadout_name, equipped_items, user_info, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, vault_bucket_type, bucket_type, bucket_hash, bucket_hashes):
    print(print_linenumber(), "     FUNCTION :    free_vault_space : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              :    free_vault_space          : equipped_items           : " + str(equipped_items))
    print(print_linenumber(), "              :    free_vault_space          : vault_bucket_type        : " + str(vault_bucket_type))
    print(print_linenumber(), "              :    free_vault_space          : bucket_type              : " + str(bucket_type))
    print(print_linenumber(), "              :    free_vault_space          : bucket_hash              : " + str(bucket_hash))
    print(print_linenumber(), "              :    free_vault_space          : bucket_hashes            : " + str(bucket_hashes))

    if vault_bucket_type in vault_inventory['bucketsFull']:
        #print(print_linenumber(), "vault_bucket_type in vault_inventory['bucketsFull'] : ")
        # VAULT IS FULL FOR THIS TYPE PIECES
        if bucket_type in character_one_inventory['bucketsFull']:
            #print(print_linenumber(), "bucket_type in character_one_inventory['bucketsFull'] : ")
            # DAMN CHARACTER ONE IS FULL OF THIS TYPE OF ITEM AS WELL
            if bucket_type in character_two_inventory['bucketsFull']:
                #print(print_linenumber(), "bucket_type in character_two_inventory['bucketsFull'] : ")
                # SHIT ALL CHARACTERS FULL OF THIS TYPE OF ITEM AND SO IS VAULT
                # COULD MOVE OTHER ITEMS OF DIFFERENT TYPE FROM VAULT TO OTHER CHARACERS, BUT FOR NOW GIVE UP!
                # vault_inventory['bucketTypeHashes']
                card_title = app_title + " : FAILED : Can't Equip loadout. " + str(vault_bucket_type) + " full."
                speech = "You have too many " + str(bucket_type) + "." \
                       + "All your character inventories are full." \
                       + "Make space for " + vault_bucket_type.lower() + " items in your vault and try again."
                end_session = True
                return alexa_speak(card_title, speech, end_session)     
            else:
                #print(print_linenumber(), "bucket_type not in character_two_inventory['bucketsFull'] : ")
                #print(print_linenumber(), "character_two_inventory['bucketsFull'] is not full of this bucket_type : ")
                # MOVE A RANDOM ITEM OF THIS TYPE FROM VAULT TO CHARACTER TWO
                counter = 0
                #print(print_linenumber(), "                            counter : " + str(counter))
                for bucket_hash_key, bucket_hash_value in enumerate(vault_inventory['bucketTypeHashes']):
                    #print(print_linenumber(), "                    bucket_hash_key : " + str(bucket_hash_key))
                    #print(print_linenumber(), "                  bucket_hash_value : " + str(bucket_hash_value))
                    if bucket_hash_value == bucket_hash and counter == 0:
                        #print(print_linenumber(), "bucket_hash_value == bucket_hash and counter == 0 : ")
                        other_itemId = vault_inventory['itemIds'][bucket_hash_key]
                        other_itemHash = vault_inventory['itemHashes'][bucket_hash_key]
                        print(print_linenumber(), "                       other_itemId : " + str(other_itemId))
                        print(print_linenumber(), "                     other_itemHash : " + str(other_itemHash))
                        if equipped_items['itemId'][bucket_hash_key] != other_itemId and loadout_decoded['itemId'][bucket_hash_key] != other_itemId and counter == 0:
                            #print(print_linenumber(), "equipped_items['itemId'][bucket_hash_key] != other_itemId and loadout_decoded['itemId'][bucket_hash_key] != other_itemId and counter == 0 : ")
                            counter = 1
                            #print(print_linenumber(), "                            counter : " + str(counter))
                            # MOVE THIS other_itemId to character two to make room in vault.
                            transfer_item(auth_token, other_itemHash, other_itemId, user_info['character_two_id'], user_info['membership_type'], "false")
                            #mark_full_inventories(character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault)
        else:
            # MOVE A RANDOM ITEM OF THIS TYPE FROM VAULT TO CHARACTER ONE
            counter = 0
            #print(print_linenumber(), "                            counter : " + str(counter))
            for bucket_hash_key, bucket_hash_value in enumerate(vault_inventory['bucketTypeHashes']):
                #print(print_linenumber(), "                    bucket_hash_key : " + str(bucket_hash_key))
                #print(print_linenumber(), "                  bucket_hash_value : " + str(bucket_hash_value))
                if bucket_hash_value == bucket_hash and counter == 0:
                    #print(print_linenumber(), "bucket_hash_value == bucket_hash and counter == 0 : ")
                    other_itemId = vault_inventory['itemIds'][bucket_hash_key]
                    other_itemHash = vault_inventory['itemHashes'][bucket_hash_key]
                    print(print_linenumber(), "                       other_itemId : " + str(other_itemId))
                    print(print_linenumber(), "                     other_itemHash : " + str(other_itemHash))
                    if equipped_items['itemId'][bucket_hash_key] != other_itemId and loadout_decoded['itemId'][bucket_hash_key] != other_itemId and counter == 0:
                        #print(print_linenumber(), "equipped_items['itemId'][bucket_hash_key] != other_itemId and loadout_decoded['itemId'][bucket_hash_key] != other_itemId and counter == 0 : ")
                        counter = 1
                        #print(print_linenumber(), "                            counter : " + str(counter))
                        # MOVE THIS other_itemId to character one to make room in vault.
                        transfer_item(auth_token, other_itemHash, other_itemId, user_info['character_one_id'], user_info['membership_type'], "false")
                        #mark_full_inventories(character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault)
    return


def split_items(auth_token, user_info, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory):
    print(print_linenumber(), "     FUNCTION :    split_items               : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              :    split_items               : auth_token               : " + str(auth_token))
    print(print_linenumber(), "              :    split_items               : user_info                : " + str(user_info))
    
    max_stack = 100
    characters = 3
    #characters = get_number_of_characters(user_info)
    #consumables = consumables_in_inventory(character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory)
    #materials = materials_in_inventory(character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory)
    
    item_hash = 211861343
    split_item(auth_token, user_info, characters, max_stack, item_hash, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory)
    
    #for item_hash in consumables:
    #    split_item(auth_token, user_info, characters, max_stack, item_hash)
        
    #for item_hash in materials:
    #    split_item(auth_token, user_info, characters, max_stack, item_hash)
        
    return  


def get_number_of_characters(user_info):
    print(print_linenumber(), "     FUNCTION :    get_number_of_characters  : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              :    get_number_of_characters  : user_info                : " + str(user_info))
    
    characters = "CODE"
    
    return characters


def consumables_in_inventory(character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory):
    print(print_linenumber(), "     FUNCTION :    consumables_in_inventory  : " + str(datetime.datetime.now()).split('.')[0])
    
    # transferable consumables (able to be split)
    consumables = "CODE"
    
    return consumables


def materials_in_inventory(character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory):
    print(print_linenumber(), "     FUNCTION :    materials_in_inventory    : " + str(datetime.datetime.now()).split('.')[0])

    # transferable materials (able to be split)
    materials = "CODE"
    
    return materials


def split_item(auth_token, user_info, characters, max_stack, item_hash, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory):
    print(print_linenumber(), "     FUNCTION :    split_item                : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              :    split_item                : auth_token               : " + str(auth_token))
    print(print_linenumber(), "              :    split_item                : user_info                : " + str(user_info))
    print(print_linenumber(), "              :    split_item                : characters               : " + str(characters))
    print(print_linenumber(), "              :    split_item                : max_stack                : " + str(max_stack))
    print(print_linenumber(), "              :    split_item                : item_hash                : " + str(item_hash))
    
    total = 0
    character_zero_total = 0
    character_one_total = 0
    character_two_total = 0
    vault_total = 0
    
    #consumables = {'Black Wax Idol': 1043138475, 'Blue Polyphage': 1772853454, 'Ether Seeds':3783295803, 'Resupply Codes':3446457162, 'House Banners':269776572, 'Silken Codex':3632619276, 'Axiomatic Beads':2904517731, 'Network Keys':1932910919, 'Three of Coins':417308266, 'Ammo Synth':2180254632, 'Special Ammo Synth':928169143, 'Heavy Ammo Synth':211861343, 'Primary Telemetry':705234570, 'Special Telemetry':3371478409, 'Heavy Telemetry':2929837733, 'Auto Rifle Telemetry':4159731660, 'Hand Cannon Telemetry':846470091, 'Pulse Rifle Telemetry':2610276738, 'Scout Rifle Telemetry':323927027, 'Fusion Rifle Telemetry':729893597, 'Shotgun Telemetry':4141501356, 'Sniper Rifle Telemetry':927802664, 'Machine Gun Telemetry':1485751393, 'Rocket Launcher Telemetry':3036931873, 'Vanguard Reputation Booster':2220921114, 'Crucible Reputation Booster':1500229041, 'House of Judgment Reputation Booster':1603376703, 'Splicer Intel Relay':2575095887, 'Splicer Cache Key':3815757277, 'Splicer Key':4244618453}
    
    #materials = {'Helium': 1797491610, 'Relic Iron': 3242866270, 'Spinmetal': 2882093969, 'Spirit Bloom': 2254123540, 'Wormspore': 3164836592, 'Hadium Flakes': 3164836593, 'Exotic Shard': 452597397, 'Armor Materials': 1542293174, 'Weapon Materials': 1898539128, 'Motes of Light': 937555249, 'Strange Coins': 1738186005, 'Ascendant Shards': 258181985, 'Ascendant Energy': 1893498008, 'Radiant Shards': 769865458, 'Radiant Energy': 616706469, 'Reciprocal Rune': 342707701, 'Stolen Rune': 342707700, 'Antiquated Rune': 2906158273, 'Stolen Rune (Charging)': 2620224196, 'Antiquated Rune (Charging)': 2906158273}
    
    #item_hash = consumables['Heavy Ammo Synth']
    
    indices = [i for i, x in enumerate(character_zero_inventory.get('itemHashes')) if x == int(item_hash)]
    for key, value in enumerate(indices):
        character_zero_total = character_zero_total + character_zero_inventory.get('quantities')[value]
    
    indices = [i for i, x in enumerate(character_one_inventory.get('itemHashes')) if x == int(item_hash)]
    for key, value in enumerate(indices):
        character_one_total = character_one_total + character_one_inventory.get('quantities')[value]
    
    indices = [i for i, x in enumerate(character_two_inventory.get('itemHashes')) if x == int(item_hash)]
    for key, value in enumerate(indices):
        character_two_total = character_two_total + character_two_inventory.get('quantities')[value]
    
    indices = [i for i, x in enumerate(vault_inventory.get('itemHashes')) if x == int(item_hash)]
    for key, value in enumerate(indices):
        vault_total = vault_total + vault_inventory.get('quantities')[value]
    
    total = character_zero_total + character_one_total + character_two_total + vault_total
    
    remainder = total%characters
    each_character = (total - remainder) / characters
    final_vault = total - (each_character * characters)
    
    if each_character >= max_stack:
        final_vault = final_vault + ((each_character - max_stack) * characters)
        each_character = max_stack
        remainder = 0
    
    if characters == 2 and character_two_total > 0:
        print(print_linenumber(), "   Move from character two to vault : " + str(character_two_total))
        vault_total = vault_total + character_two_total
        character_two_total = character_two_total - character_two_total
        transfer_item(auth_token, item_hash, 254, user_info['character_two_id'], user_info['membership_type'], "true", character_two_total)
    
    if characters == 1 and character_one_total > 0:
        print(print_linenumber(), "   Move from character two to vault : " + str(character_two_total))
        vault_total = vault_total + character_two_total
        character_two_total = character_two_total - character_two_total
        transfer_item(auth_token, item_hash, 254, user_info['character_two_id'], user_info['membership_type'], "true", character_two_total)
        print(print_linenumber(), "   Move from character one to vault : " + str(character_one_total))
        vault_total = vault_total + character_one_total
        character_one_total = character_one_total - character_one_total
        transfer_item(auth_token, item_hash, 254, user_info['character_one_id'], user_info['membership_type'], "true", character_one_total)
    
    print(print_linenumber(), "               character_zero_total : " + str(character_zero_total))
    print(print_linenumber(), "                character_one_total : " + str(character_one_total))
    print(print_linenumber(), "                character_two_total : " + str(character_two_total))
    print(print_linenumber(), "                        vault_total : " + str(vault_total))
    print(print_linenumber(), "                              total : " + str(total))
    print(print_linenumber(), "                          remainder : " + str(remainder))
    print(print_linenumber(), "                     each_character : " + str(each_character))

    if character_zero_total > each_character:
      quantity_to_move = character_zero_total - each_character
      if character_one_total < each_character and characters > 1:
        print(print_linenumber(), "  Move from character zero to vault : " + str(quantity_to_move))
        character_zero_total = character_zero_total - quantity_to_move
        transfer_item(auth_token, item_hash, 254, user_info['character_zero_id'], user_info['membership_type'], "true", quantity_to_move)
        
        print(print_linenumber(), "   Move from vault to character one : " + str(quantity_to_move))
        character_one_total = character_one_total + quantity_to_move
        transfer_item(auth_token, item_hash, 254, user_info['character_one_id'], user_info['membership_type'], "false", quantity_to_move)
      elif character_two_total < each_character and characters > 2:
        print(print_linenumber(), "  Move from character zero to vault : " + str(quantity_to_move))
        character_zero_total = character_zero_total - quantity_to_move
        transfer_item(auth_token, item_hash, 254, user_info['character_zero_id'], user_info['membership_type'], "true", quantity_to_move)
        
        print(print_linenumber(), "   Move from vault to character two : " + str(quantity_to_move))
        character_two_total = character_two_total + quantity_to_move
        transfer_item(auth_token, item_hash, 254, user_info['character_two_id'], user_info['membership_type'], "false", quantity_to_move)
      else:
        print(print_linenumber(), "  Move from character zero to vault : " + str(quantity_to_move))
        character_zero_total = character_zero_total - quantity_to_move
        vault_total = vault_total + quantity_to_move
        transfer_item(auth_token, item_hash, 254, user_info['character_zero_id'], user_info['membership_type'], "true", quantity_to_move)
        
    if character_one_total > each_character:
      quantity_to_move = character_one_total - each_character
      if character_zero_total < each_character:
        print(print_linenumber(), "   Move from character one to vault : " + str(quantity_to_move))
        character_one_total = character_one_total - quantity_to_move
        transfer_item(auth_token, item_hash, 254, user_info['character_one_id'], user_info['membership_type'], "true", quantity_to_move)
        
        print(print_linenumber(), "  Move from vault to character zero : " + str(quantity_to_move))
        character_zero_total = character_zero_total + quantity_to_move
        transfer_item(auth_token, item_hash, 254, user_info['character_zero_id'], user_info['membership_type'], "false", quantity_to_move)
      elif character_two_total < each_character and characters > 2:
        print(print_linenumber(), "   Move from character one to vault : " + str(quantity_to_move))
        character_one_total = character_one_total - quantity_to_move
        transfer_item(auth_token, item_hash, 254, user_info['character_one_id'], user_info['membership_type'], "true", quantity_to_move)
        
        print(print_linenumber(), "   Move from vault to character two : " + str(quantity_to_move))
        character_two_total = character_two_total + quantity_to_move
        transfer_item(auth_token, item_hash, 254, user_info['character_two_id'], user_info['membership_type'], "false", quantity_to_move)
      else:
        print(print_linenumber(), "   Move from character one to vault : " + str(quantity_to_move))
        character_one_total = character_one_total - quantity_to_move
        vault_total = vault_total + quantity_to_move
        transfer_item(auth_token, item_hash, 254, user_info['character_one_id'], user_info['membership_type'], "true", quantity_to_move)
        
    if character_two_total > each_character:
      quantity_to_move = character_two_total - each_character
      if character_zero_total < each_character:
        print(print_linenumber(), "   Move from character two to vault : " + str(quantity_to_move))
        character_two_total = character_two_total - quantity_to_move
        transfer_item(auth_token, item_hash, 254, user_info['character_two_id'], user_info['membership_type'], "true", quantity_to_move)
        
        print(print_linenumber(), "  Move from vault to character zero : " + str(quantity_to_move))
        character_zero_total = character_zero_total + quantity_to_move
        transfer_item(auth_token, item_hash, 254, user_info['character_zero_id'], user_info['membership_type'], "false", quantity_to_move)
      elif character_one_total < each_character and characters > 1:
        print(print_linenumber(), "   Move from character two to vault : " + str(quantity_to_move))
        character_two_total = character_two_total - quantity_to_move
        transfer_item(auth_token, item_hash, 254, user_info['character_two_id'], user_info['membership_type'], "true", quantity_to_move)
        
        print(print_linenumber(), "   Move from vault to character one : " + str(quantity_to_move))
        character_one_total = character_one_total + quantity_to_move
        transfer_item(auth_token, item_hash, 254, user_info['character_one_id'], user_info['membership_type'], "false", quantity_to_move)
      else:
        print(print_linenumber(), "   Move from character two to vault : " + str(quantity_to_move))
        character_two_total = character_two_total - quantity_to_move
        vault_total = vault_total + quantity_to_move
        transfer_item(auth_token, item_hash, 254, user_info['character_two_id'], user_info['membership_type'], "true", quantity_to_move)
        
    if character_zero_total < each_character:
      quantity_to_move = each_character - character_zero_total
      if vault_total >= quantity_to_move:
        print(print_linenumber(), "  Move from vault to character zero : " + str(quantity_to_move))
        vault_total = vault_total - quantity_to_move
        character_zero_total = character_zero_total + quantity_to_move
        transfer_item(auth_token, item_hash, 254, user_info['character_zero_id'], user_info['membership_type'], "false", quantity_to_move)
    
    if character_one_total < each_character and characters > 1:
      quantity_to_move = each_character - character_one_total
      if vault_total >= quantity_to_move:
        print(print_linenumber(), "   Move from vault to character one : " + str(quantity_to_move))
        vault_total = vault_total - quantity_to_move
        character_one_total = character_one_total + quantity_to_move
        transfer_item(auth_token, item_hash, 254, user_info['character_one_id'], user_info['membership_type'], "false", quantity_to_move)
    
    if character_two_total < each_character and characters > 2:
      quantity_to_move = each_character - character_two_total
      if vault_total >= quantity_to_move:
        print(print_linenumber(), "   Move from vault to character two : " + str(quantity_to_move))
        vault_total = vault_total - quantity_to_move
        character_two_total = character_two_total + quantity_to_move
        transfer_item(auth_token, item_hash, 254, user_info['character_two_id'], user_info['membership_type'], "false", quantity_to_move)

    print(print_linenumber(), "               character_zero_total : " + str(character_zero_total))
    print(print_linenumber(), "                character_one_total : " + str(character_one_total))
    print(print_linenumber(), "                character_two_total : " + str(character_two_total))
    print(print_linenumber(), "                        vault_total : " + str(vault_total))
    print(print_linenumber(), "                              total : " + str(total))

    return


def transfer_item(auth_token, itemHash, itemId, character_id, membership_type, to_vault, quantity="1"):
    print(print_linenumber(), "     FUNCTION :    transfer_item    : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              :    transfer_item             : itemHash                 : " + str(itemHash))
    print(print_linenumber(), "              :    transfer_item             : itemId                   : " + str(itemId))
    print(print_linenumber(), "              :    transfer_item             : character_id             : " + str(character_id))
    print(print_linenumber(), "              :    transfer_item             : membership_type          : " + str(membership_type))
    print(print_linenumber(), "              :    transfer_item             : to_vault                 : " + str(to_vault))
  
    endpoint = "transfer_item"
    if int(quantity) > 1 and itemId == 254:
        data='{"itemReferenceHash":"' + str(itemHash) + '","stackSize":"' + str(quantity) + '","transferToVault":"' + str(to_vault) + '","characterId":"' + str(character_id) + '","membershipType":' + str(membership_type) + '}'
    else:   
        data='{"itemReferenceHash":"' + str(itemHash) + '","stackSize":"' + str(1) + '","transferToVault":"' + str(to_vault) + '","itemId":"' + str(itemId) + '","characterId":"' + str(character_id) + '","membershipType":' + str(membership_type) + '}'
    
    response = call_api(endpoint, auth_token, data, method="POST")
    
    print(print_linenumber(), "                       data : " + str(data))
    print(print_linenumber(), "                   response : " + str(response))
    
    # IF LOCATION IS FULL
    # response : {u'ThrottleSeconds': 0, u'ErrorCode': 1642, u'ErrorStatus': u'DestinyNoRoomInDestination', u'Message': u'There are no item slots available to transfer this item.', u'Response': 0, u'MessageData': {}}
    
    return response


def equip_items(auth_token, itemIds, character_id, membership_type):
    print(print_linenumber(), "     FUNCTION :    equip_items      : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              :    equip_items               : itemIds                  : " + str(itemIds))
    print(print_linenumber(), "              :    equip_items               : character_id             : " + str(character_id))
    print(print_linenumber(), "              :    equip_items               : membership_type          : " + str(membership_type))
   
    endpoint = "equip_items"
    data='{"itemIds":[' + str(itemIds) + '],"characterId":"' + str(character_id) + '","membershipType":' + str(membership_type) + '}'
    response = call_api(endpoint, auth_token, data, method="POST")
    #print(print_linenumber(), "                       data : " + str(data))
    #print(print_linenumber(), "                   response : " + str(response))
    return response
    

def find_dict_key_by_value(input_dict, value):
    #print(print_linenumber(), "     FUNCTION :    find_dict_key_by_value    : " + str(datetime.datetime.now()).split('.')[0])
    #print(print_linenumber(), "              :    find_dict_key_by_value    : input_dict               : " + str(input_dict))
    #print(print_linenumber(), "              :    find_dict_key_by_value    : value                    : " + str(value))
    
    for k, v in input_dict.items():
        if v == value:
            yield k


def print_linenumber():
    #print(print_linenumber(), "     FUNCTION :            get_linenumber    : " + str(datetime.datetime.now()).split('.')[0])
    cf = currentframe()
    return cf.f_back.f_lineno
    

if __name__ == '__main__':
    print(print_linenumber(), "     FUNCTION :  __main__           : " + str(datetime.datetime.now()).split('.')[0])
    '''sample_event_raw = ast.literal_eval("{u'session': {u'new': True, u'sessionId': u'amzn1.echo-api.session.82842f35-f1ec-46cc-a7ea-3b4d690a1a59', u'user': {u'userId': u'amzn1.ask.account.XXXXXXXXXXXX', u'accessToken': u'XXXXXXXXXXXX'}, u'application': {u'applicationId': u'amzn1.ask.skill.8f96749d-8fa5-4a44-8f17-3bd7f7e69aa8'}}, u'version': u'1.0', u'request': {u'locale': u'en-US', u'timestamp': u'2017-08-04T23:24:09Z', u'type': u'LaunchRequest', u'requestId': u'amzn1.echo-api.request.18981e59-2980-42ac-bfe7-7ede53d0c2c3'}, u'context': {u'AudioPlayer': {u'playerActivity': u'IDLE'}, u'System': {u'device': {u'deviceId': u'amzn1.ask.device.XXXXXXXXXXXX', u'supportedInterfaces': {u'AudioPlayer': {}}}, u'application': {u'applicationId': u'amzn1.ask.skill.8f96749d-8fa5-4a44-8f17-3bd7f7e69aa8'}, u'user': {u'userId': u'amzn1.ask.account.XXXXXXXXXXXX', u'accessToken': u'XXXXXXXXXXXX'}, u'apiEndpoint': u'https://api.amazonalexa.com'}}}")
    
    sample_event_json = json.loads(json.dumps(sample_event_raw))
    sample_context = "<__main__.LambdaContext object at 0x000000000000>"
    handler(sample_event_json, sample_context)'''
    
    
    
    
    
    
    

