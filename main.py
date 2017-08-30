#!/usr/bin/env python

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

app_title = "TITLE FOR ALEXA SKILL"
app_id = "amzn1.ask.skill.XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
app_help_msg = "Helpful Message" 
main_domain = "https://www.bungie.net"
api_key = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
db_host = "XXXXXXXXXXXXX.XXXXXXXXXXXX.XXXXXXXXXX.rds.amazonaws.com"
db_name_alexa = "XXXXXXXXXX"
db_name_bungie = "XXXXXXXXXXXXXXXXXXX"
db_user = "XXXXXXXXXXX"
db_pass = "XXXXXXXXXXX"
db_port = "5432"


def handler(event, context):
    print(print_linenumber(), "     FUNCTION : handler         : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              : handler                      : event                    : " + str(event))
    print(print_linenumber(), "              : handler                      : context                  : " + str(context))

    global app_id
    global app_title

    if (event['session']['application']['applicationId'] != app_id):
        print(print_linenumber(), "                      ERROR : Invalid Application ID, set the app_id")
        card_title = app_title + " : ERROR : Invalid Application ID."
        speech = "I am currently undergoing maintenance. " \
               + "Sorry for the inconvinience, please try again later."
        end_session = True
        return alexa_speak(card_title, speech, end_session)

    if event['session']['user']['accessToken']:
        auth_token = event['session']['user']['accessToken']
        print(print_linenumber(), "                 auth_token : " + auth_token)

    else:
        auth_token = ""

    if event['session']['new']:
        print(print_linenumber(), "                  App Title : " + app_title)
        print(print_linenumber(), "                     App ID : " + app_id)

    if event['session']['user']['userId']:
        user_id = event['session']['user']['userId']
        print(print_linenumber(), "                     userId : " + user_id)
    else:
        user_id = ""

    if event['context']['System']['device']['deviceId']:
        device_id = event['context']['System']['device']['deviceId']
        print(print_linenumber(), "                  device_id : " + device_id)
    else:
        device_id = ""
      
    if event['request']['type'] == "IntentRequest":
        print(print_linenumber(), "                    Request : IntentRequest")
        return on_intent(event['request']['intent'], auth_token)    
    elif event['request']['type'] == "LaunchRequest" or event['request']['type'] == "Launch":
        print(print_linenumber(), "                    Request : LaunchRequest")
        card_title = "Welcome to " + app_title + "."
        speech = "This is " + app_title + ". " \
                 "You can ask me to save or equip a loadout."
        end_session = False
        return alexa_speak(card_title, speech, end_session)
    elif event['request']['type'] == "SessionEndedRequest":
        session_ended_request = event['request']
        session = event['session']
        print(print_linenumber(), "                    Request : SessionEndedRequest")
        print(print_linenumber(), "                  requestId : " + session_ended_request['requestId'])
        print(print_linenumber(), "                  sessionId : " + session['sessionId'])
        print(print_linenumber(), "                    Session : Ended")
        print(print_linenumber(), "on_session_ended requestId=" + session_ended_request['requestId'] + ", sessionId=" + session['sessionId'])
        return
    else:
        print(print_linenumber(), "                    Request : Welcome (Default)")
        card_title = "Welcome to " + app_title + "."
        speech = "This is " + app_title + ". " \
                 "If you need help using this app, just say, \"help\"."
        end_session = False
        return alexa_speak(card_title, speech, end_session)


def on_intent(intent, auth_token):
    print(print_linenumber(), "     FUNCTION : on_intent : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              : on_intent                    : intent                   : " + str(intent))
    print(print_linenumber(), "              : auth_token                   : auth_token               : " + str(auth_token))

    global app_title
    global app_help_msg
    
    if intent:
        print(print_linenumber(), "                     intent : " + str(intent))
    if intent['name']:
        print(print_linenumber(), "             intent['name'] : " + str(intent['name']))

    user_info = get_userinfo(auth_token)
    try:
        if user_info['version'] == '1.0':
            return user_info
    except KeyError:

        character_zero_inventory, character_one_inventory, character_two_inventory, \
        vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault, bucket_hashes_subclass = get_character_inventories(auth_token, user_info['membership_type'], user_info['membership_id'])
    
        print(print_linenumber(), "            vault_inventory : " + str(vault_inventory))

        exotics = get_all_exotics_in_game(auth_token)

        equipped_items = get_character_equipped_items(auth_token, user_info['membership_type'], user_info['membership_id'], user_info['character_zero_id'], exotics, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory)
        
        print(print_linenumber(), "             equipped_items : " + str(equipped_items))
    
        print(print_linenumber(), "   character_zero_inventory : " + str(character_zero_inventory))
        print(print_linenumber(), "    character_one_inventory : " + str(character_one_inventory))
        print(print_linenumber(), "    character_two_inventory : " + str(character_two_inventory))
        print(print_linenumber(), "            vault_inventory : " + str(vault_inventory))
    
        character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory = mark_full_inventories(character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault)
        
        print('Character Zero Full Buckets : ' + str(character_zero_inventory['bucketsFull']))
        print( 'Character One Full Buckets : ' + str(character_one_inventory['bucketsFull']))
        print(' Character Two Full Buckets : ' + str(character_two_inventory['bucketsFull']))
        print(         'Vault Full Buckets : ' + str(vault_inventory['bucketsFull']))   
    
        if "Primary Weapons" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "       zero bucketsFull : Primary Weapons")
        if "Special Weapons" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "       zero bucketsFull : Special Weapons")
        if "Heavy Weapons" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "       zero bucketsFull : Heavy Weapons")
        if "Ghost" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "       zero bucketsFull : Ghost")
            
        if "Helmet" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "       zero bucketsFull : Helmet")
        if "Gauntlets" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "       zero bucketsFull : Gauntlets")
        if "Chest Armor" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "       zero bucketsFull : Chest Armor")
        if "Leg Armor" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "       zero bucketsFull : Leg Armor")
        if "Class Armor" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "       zero bucketsFull : Class Armor")
        if "Artifacts" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "       zero bucketsFull : Artifacts")

        if "Emblems" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "       zero bucketsFull : Emblems")
        if "Shaders" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "       zero bucketsFull : Shaders")
        if "Emotes" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "       zero bucketsFull : Emotes")
        if "Ships" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "       zero bucketsFull : Ships")
        if "Vehicle" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "       zero bucketsFull : Vehicle")
        if "Sparrow Horn" in character_zero_inventory['bucketsFull']:
            print(print_linenumber(), "       zero bucketsFull : Sparrow Horn")
            
        if "Weapons" in vault_inventory['bucketsFull']:
            print(print_linenumber(), "      vault bucketsFull : Weapons")
        if "Armor" in vault_inventory['bucketsFull']:
            print(print_linenumber(), "      vault bucketsFull : Armor")
        if "General" in vault_inventory['bucketsFull']:
            print(print_linenumber(), "      vault bucketsFull : General")
    
        '''if 306958364 in character_inventory['itemHashes']:
            index = character_inventory['itemHashes'].index(306958364)
            print('Vision of Confluence is in Inventory')
            print('      itemHash : ' + str(character_inventory['itemHashes'][index]))
            print('        itemId : ' + str(character_inventory['itemIds'][index]))
            print(' bucket_hashes : ' + str(character_inventory['bucket_hashes'][index]))
            print('characterIndex : ' + str(character_inventory['characterIndices'][index]))
            print('      quantity : ' + str(character_inventory['quantities'][index]))
           
            # ADEPT EXOTIC VERSION
            it_is_exotic = is_it_an_exotic(1620583065, exotics)
            if it_is_exotic:
                print('        Exotic : YES ')
            else:
                print('        Exotic : NO ')    '''       
            
            #strings_match = do_strings_match("Atheon's Epilogue (Adept)", "atheons_epilogue_adept")
            #SELECT json->>'itemName' AS itemName, json->>'itemHash' AS itemHash from DestinyInventoryItemDefinition 
            #WHERE json->>'itemName' = E'Atheon\'s Epilogue (Adept)';
            #-- atheons_epilogue_adept
            #-- 2512322824
            #if strings_match:
            #    print('         Match : YES ')
            #else:
            #    print('         Match : NO ')
            
            
        if intent['name'] == "EquipEmblem":
            character_inventory = get_character_inventory(auth_token, membership_type, membership_id)
            
        elif intent['name'] == "EquipEmote":
            character_inventory = get_character_inventory(auth_token, membership_type, membership_id)
            
        elif intent['name'] == "EquipExoticArmor":
            character_inventory = get_character_inventory(auth_token, membership_type, membership_id)
            
        elif intent['name'] == "EquipExoticWeapon":
            character_inventory = get_character_inventory(auth_token, membership_type, membership_id)
            
        elif intent['name'] == "EquipLoadout":
                
            if intent['slots']:
                print(print_linenumber(), "                    intent['slots'] : " + str(intent['slots']))
            if intent['slots']['LOADOUT']['name']:
                print(print_linenumber(), "intent['slots']['LOADOUT']['name']  : " + str(intent['slots']['LOADOUT']['name']))
            if intent['slots']['LOADOUT']['value']:
                print(print_linenumber(), "intent['slots']['LOADOUT']['value'] : " + str(intent['slots']['LOADOUT']['value']))
        
            loadout_name = standardize_loadout_name(intent)
    
            timestamp = datetime.datetime.now()
            
            return equip_loadout(auth_token, user_info['display_name'], user_info['membership_id_bungie'], user_info['membership_type'], user_info['membership_id'], user_info['character_zero_id'], user_info['character_zero_race'], user_info['character_zero_gender'], user_info['character_zero_class'], loadout_name, equipped_items, user_info, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault, bucket_hashes_subclass)
    
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
                
            loadout_name = standardize_loadout_name(intent)
    
            timestamp = datetime.datetime.now()
            
            return save_loadout(user_info['display_name'], user_info['membership_id_bungie'], user_info['membership_type'], user_info['membership_id'], user_info['character_zero_id'], user_info['character_zero_race'], user_info['character_zero_gender'], user_info['character_zero_class'], loadout_name, equipped_items, timestamp)
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


def call_api(url, api_key, auth_token, data="", method="GET"):
    print(print_linenumber(), "     FUNCTION : call_api                     : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              : call_api                     : url                      : " + str(url))
    print(print_linenumber(), "              : call_api                     : api_key                  : " + str(api_key))
    print(print_linenumber(), "              : call_api                     : auth_token               : " + str(auth_token))

    if data:
        print(print_linenumber(), "              : call_api                     : data                     : " + str(data)) 
        print(print_linenumber(), "              : call_api                     : method                   : " + str(method)) 
        
    connection_code = 200
    
    handler = urllib2.HTTPHandler()
    opener = urllib2.build_opener(handler)
    
    if method == "POST":
        #data = urllib.urlencode(json.loads(json_data))
        request = urllib2.Request(url, data=data)
        print(print_linenumber(), "                               data : " + str(data))
        #data : itemId=6917529130345955914&itemReferenceHash=1569892242&membershipType=2&transferToVault=true&stackSize=1&characterId=2305843009217357501
    else:
        request = urllib2.Request(url)
        
    request.add_header('X-API-Key', api_key)
    request.add_header('Authorization', "Bearer " + auth_token)
    request.add_header("Content-Type",'application/json')

    request.get_method = lambda: method

    #try:
    #    response = urllib2.urlopen(request)
    #except urllib2.HTTPError, e:
    #    if e.code == 401:
    
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
        speech = "ERROR. H. T. T. P. four oh one.  Unauthorized. " \
               + "Please ensure this skill is 'Approved' to connect to your Bungie account."
        end_session = True
        return alexa_speak(card_title, speech, end_session)
    elif connection_code == 403:
        print(print_linenumber(), "                              ERROR : HTTP 403 Forbidden.")
        card_title = app_title + " : ERROR : HTTP 403 Forbidden."
        speech = "ERROR. H. T. T. P. four oh three.  Forbidden. " \
               + "It appears Bungie's network is undergoing maintenace, please try again later."
        end_session = True
        return alexa_speak(card_title, speech, end_session)
    elif connection_code == 404:
        print(print_linenumber(), "                      ERROR : HTTP 404 Not Found.")
        card_title = app_title + " : ERROR : HTTP 404 Not Found."
        speech = "ERROR. H. T. T. P. four oh four.  Not Found. " \
               + "It appears Bungie's network is undergoing maintenace, please try again later."
        end_session = True
        return alexa_speak(card_title, speech, end_session)
    elif connection_code == 429:
        print(print_linenumber(), "                      ERROR : HTTP 429 Too Many Requests.")
        card_title = app_title + " : ERROR : HTTP 429 Too Many Requests."
        speech = "ERROR. H. T. T. P. four twenty nine.  Too Many Requests. " \
               + "Bungie's servers are rejecting new connections from this app at this time, please try again later."
        end_session = True
        return alexa_speak(card_title, speech, end_session)      
    elif connection_code == 500:
        print(print_linenumber(), "                      ERROR : HTTP 500 Internal Server Error.")
        card_title = app_title + " : ERROR : HTTP 500 Internal Server Error."
        speech = "ERROR. H. T. T. P. five hundred.  Internal Server Error. " \
               + "It appears Bungie's network is undergoing maintenace, please try again later."
        end_session = True
        return alexa_speak(card_title, speech, end_session)
    elif connection_code == 502:
        print(print_linenumber(), "                      ERROR : HTTP 502 Bad Gateway.")
        card_title = app_title + " : ERROR : HTTP 502 Bad Gateway."
        speech = "ERROR. H. T. T. P. five oh two.  Bad Gateway. " \
               + "It appears Bungie's network is undergoing maintenace, please try again later."
        end_session = True
        return alexa_speak(card_title, speech, end_session)
    elif connection_code == 503:
        print(print_linenumber(), "                      ERROR : HTTP 503 Service Unavailable.")
        card_title = app_title + " : ERROR : HTTP 503 Service Unavailable."
        speech = "ERROR. H. T. T. P. five oh three. Service Unavailable. " \
               + "I am having trouble connecting to Destiny's network, please try again later."
        end_session = True
        return alexa_speak(card_title, speech, end_session)            
    elif connection_code == 504:
        print(print_linenumber(), "                      ERROR : HTTP 504 Gateway Timeout.")
        card_title = app_title + " : ERROR : HTTP 504 Gateway Timeout."
        speech = "ERROR. H. T. T. P. five oh four. Gateway Timeout. " \
               + "It appears Bungie's network is undergoing maintenace, please try again later."
        end_session = True
        return alexa_speak(card_title, speech, end_session)            
    else:
        print(print_linenumber(), "                      ERROR : HTTP " + str(connection_code))
        card_title = app_title + " : ERROR : HTTP " + str(connection_code) + "."
        speech = "ERROR. H. T. T. P. Error Unknown." \
               + "It appears Bungie's network is undergoing maintenace, please try again later."
        end_session = True
        return alexa_speak(card_title, speech, end_session)    

    if response_json['ErrorCode'] == 217:
        print(print_linenumber(), "                      ERROR : Bungie User API Code: 217 : Retrying...")
        time.sleep(3)
        print(response_json)
        response_json = call_api(url, api_key, auth_token)

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
    cur.close()
    conn.close()

    print(print_linenumber(), "                      query_results : " + str(query_results))
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
    
    
def get_userinfo(auth_token):
    print(print_linenumber(), "     FUNCTION : get_userinfo : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              : get_userinfo                 : auth_token               : " + str(auth_token))

    global main_domain
    global api_key
    
    character_lastplayed_xbox = 0
    character_lastplayed_psn = 0
    character_lastplayed_pc = 0
    
    url = main_domain + "/Platform/User/GetMembershipsForCurrentUser/"
    
    get_memberships_for_currentuser = call_api(url, api_key, auth_token)
    try:
        if get_memberships_for_currentuser['version'] == '1.0':
            return get_memberships_for_currentuser
    except KeyError:
        print(print_linenumber(), "    get_memberships_for_currentuser : " + str(get_memberships_for_currentuser))   
    
        membership_id_bungie = get_memberships_for_currentuser['Response']['bungieNetUser']['membershipId']
    
        display_name = get_memberships_for_currentuser['Response']['bungieNetUser']['displayName']
        print(print_linenumber(), "               membership_id_bungie : " + membership_id_bungie)
        print(print_linenumber(), "                       display_name : " + display_name)  
        
        for index, item in enumerate(get_memberships_for_currentuser['Response']['destinyMemberships']):
            print(print_linenumber(), "                               item : " + str(item))  
            if item['membershipType'] == 1:
                membership_id_xbox = item['membershipId']
                print(print_linenumber(), "                 membership_id_xbox : " + membership_id_xbox)
                url = main_domain + "/Platform/User/GetBungieAccount/" + membership_id_xbox + "/1/"
                get_bungie_account_xbox = call_api(url, api_key, auth_token)
                for index_b, item_b in enumerate(get_bungie_account_xbox['Response']['destinyAccounts']):
                    if item_b['userInfo']['membershipId'] == membership_id_xbox:
                        character_zero_id_xbox = item_b['characters'][0]['characterId']
                        character_one_id_xbox = item_b['characters'][1]['characterId']
                        character_two_id_xbox = item_b['characters'][2]['characterId']
                        character_lastplayed_xbox = item_b['characters'][0]['dateLastPlayed']
                        character_zero_race_xbox = item_b['characters'][0]['race']['raceType']
                        character_zero_gender_xbox = item_b['characters'][0]['genderType']
                        character_zero_class_xbox = item_b['characters'][0]['characterClass']['classType']
                        character_one_race_psn = item_b['characters'][1]['race']['raceType']
                        character_one_gender_xbox = item_b['characters'][1]['genderType']
                        character_one_class_xbox = item_b['characters'][1]['characterClass']['classType']
                        character_two_race_xbox = item_b['characters'][2]['race']['raceType']
                        character_two_gender_xbox = item_b['characters'][2]['genderType']
                        character_two_class_xbox = item_b['characters'][2]['characterClass']['classType']
                        
            elif item['membershipType'] == 2:
                membership_id_psn = item['membershipId']
                print(print_linenumber(), "                  membership_id_psn : " + membership_id_psn)
                url = main_domain + "/Platform/User/GetBungieAccount/" + membership_id_psn + "/2/"
                get_bungie_account_psn = call_api(url, api_key, auth_token)
                for index_b, item_b in enumerate(get_bungie_account_psn['Response']['destinyAccounts']):
                    if item_b['userInfo']['membershipId'] == membership_id_psn:
                        character_zero_id_psn = item_b['characters'][0]['characterId']
                        character_one_id_psn = item_b['characters'][1]['characterId']
                        character_two_id_psn = item_b['characters'][2]['characterId']
                        character_lastplayed_psn = item_b['characters'][0]['dateLastPlayed']
                        character_zero_race_psn = item_b['characters'][0]['race']['raceType']
                        character_zero_gender_psn = item_b['characters'][0]['genderType']
                        character_zero_class_psn = item_b['characters'][0]['characterClass']['classType']
                        character_one_race_psn = item_b['characters'][1]['race']['raceType']
                        character_one_gender_psn = item_b['characters'][1]['genderType']
                        character_one_class_psn = item_b['characters'][1]['characterClass']['classType']
                        character_two_race_psn = item_b['characters'][2]['race']['raceType']
                        character_two_gender_psn = item_b['characters'][2]['genderType']
                        character_two_class_psn = item_b['characters'][2]['characterClass']['classType']              
                        
            elif item['membershipType'] == 4:
                membership_id_pc = item['membershipId']
                print(print_linenumber(), "                   membership_id_pc : " + membership_id_pc)
                url = main_domain + "/Platform/User/GetBungieAccount/" + membership_id_pc + "/4/"
                get_bungie_account_psn = call_api(url, api_key, auth_token)
                for index_b, item_b in enumerate(get_bungie_account_psn['Response']['destinyAccounts']):
                    if item_b['userInfo']['membershipId'] == membership_id_pc:
                        character_zero_id_pc = item_b['characters'][0]['characterId']
                        character_one_id_pc = item_b['characters'][1]['characterId']
                        character_two_id_pc = item_b['characters'][2]['characterId']
                        character_lastplayed_pc = item_b['characters'][0]['dateLastPlayed']
                        character_zero_race_pc = item_b['characters'][0]['race']['raceType']
                        character_zero_gender_pc = item_b['characters'][0]['genderType']
                        character_zero_class_pc = item_b['characters'][0]['characterClass']['classType']
                        character_one_race_pc = item_b['characters'][1]['race']['raceType']
                        character_one_gender_pc = item_b['characters'][1]['genderType']
                        character_one_class_pc = item_b['characters'][1]['characterClass']['classType']
                        character_two_race_pc = item_b['characters'][2]['race']['raceType']
                        character_two_gender_pc = item_b['characters'][2]['genderType']
                        character_two_class_pc = item_b['characters'][2]['characterClass']['classType']
                        
            if (character_lastplayed_xbox > character_lastplayed_psn) and (character_lastplayed_xbox > character_lastplayed_pc):
                membership_type = 1
                membership_id = membership_id_xbox
                character_zero_id = character_zero_id_xbox
                character_one_id = character_one_id_xbox
                character_two_id = character_two_id_xbox
                character_zero_race = character_zero_race_xbox
                character_zero_gender = character_zero_gender_xbox
                character_zero_class = character_zero_class_xbox
                character_one_race = character_zero_race_xbox
                character_one_gender = character_zero_gender_xbox
                character_one_class = character_zero_class_xbox
                character_two_race = character_zero_race_xbox
                character_two_gender = character_zero_gender_xbox
                character_two_class = character_zero_class_xbox
            elif (character_lastplayed_psn > character_lastplayed_xbox) and (character_lastplayed_psn > character_lastplayed_pc):
                membership_type = 2
                membership_id = membership_id_psn
                character_zero_id = character_zero_id_psn
                character_one_id = character_one_id_psn
                character_two_id = character_two_id_psn
                character_zero_race = character_zero_race_psn
                character_zero_gender = character_zero_gender_psn
                character_zero_class = character_zero_class_psn
                character_one_race = character_zero_race_psn
                character_one_gender = character_zero_gender_psn
                character_one_class = character_zero_class_psn
                character_two_race = character_zero_race_psn
                character_two_gender = character_zero_gender_psn
                character_two_class = character_zero_class_psn
            elif (character_lastplayed_pc > character_lastplayed_psn) and (character_lastplayed_pc > character_lastplayed_xbox):
                membership_type = 4
                membership_id = membership_id_pc
                character_zero_id = character_zero_id_pc
                character_one_id = character_one_id_pc
                character_two_id = character_two_id_pc
                character_zero_race = character_zero_race_pc
                character_zero_gender = character_zero_gender_pc
                character_zero_class = character_zero_class_pc
                character_one_race = character_zero_race_pc
                character_one_gender = character_zero_gender_pc
                character_one_class = character_zero_class_pc
                character_two_race = character_zero_race_pc
                character_two_gender = character_zero_gender_pc
                character_two_class = character_zero_class_pc
            else:
                print(print_linenumber(), "                              ERROR : Could not determine which platform last played on.")
                card_title = app_title + " : ERROR : You've never played Destiny?"
                speech = "I am having trouble finding a character you've played in Destiny the Game. " \
                       + "Please play Destiny and create a character before using this app." \
                       + "This app must be approved on Bungie dot net, and your Bungie dot net account " \
                       + "must be linked to your Destiny account."
                end_session = True
                return alexa_speak(card_title, speech, end_session)
                
            # RACE 0 = HUMAN, 1 = AWOKEN, 2 = EXO
            # GENDER 0 = MALE, 1 = FEMALE
            # CLASS 0 = TITAN, 1 = HUNTER, 2 = WARLOCK
    
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

def itemName_from_itemHash(hash):
    print(print_linenumber(), "     FUNCTION : itemName_from_itemHash : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              : itemName_from_itemHash       : hash                     : " + str(hash))    

    sql = "SELECT json->>'itemName' AS itemName from DestinyInventoryItemDefinition WHERE json->>'itemHash' = '" + hash + "';"
    item_name = query_bungie_db(sql)[0]
    item_name = item_name[0]
    print(print_linenumber(), "                          item_name : " + str(item_name)) 
    return str(item_name)


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
            #itemId = itemId_from_itemHash(itemHash, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory)
        elif int(itemHash) in character_one_inventory['itemHashes']:
            location_id = user_info['character_one_id']
            #itemId = itemId_from_itemHash(itemHash, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory)
        elif int(itemHash) in character_two_inventory['itemHashes']:
            location_id = user_info['character_two_id']
            #itemId = itemId_from_itemHash(itemHash, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory)
        elif int(itemHash) in vault_inventory['itemHashes']:
            location_id = -1
            #itemId = itemId_from_itemHash(itemHash, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory)
        else:
            print(print_linenumber(), "                             WARNING: find_item_location failed.  Item probably deleted since loadout was saved.")
            
    return int(location_id)

 
def itemId_from_itemHash(itemHash, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory):
    #print(print_linenumber(), "     FUNCTION : itemId_from_itemHash : " + str(datetime.datetime.now()).split('.')[0])
    #print(print_linenumber(), "              : itemId_from_itemHash         : itemHash                 : " + str(itemHash))    
    #print(print_linenumber(), "              : itemId_from_itemHash         : character_zero_inventory : " + str(character_zero_inventory))  
    #print(print_linenumber(), "              : itemId_from_itemHash         : character_one_inventory  : " + str(character_one_inventory))  
    #print(print_linenumber(), "              : itemId_from_itemHash         : character_two_inventory  : " + str(character_two_inventory))  
    #print(print_linenumber(), "              : itemId_from_itemHash         : vault_inventory          : " + str(vault_inventory))  

    itemId = ""
    try:
        itemId = character_zero_inventory['itemIds'][character_zero_inventory['itemHashes'].index(itemHash)]
    except ValueError:
        try:
            itemId = character_one_inventory['itemIds'][character_one_inventory['itemHashes'].index(itemHash)]
        except ValueError:
            try:
                itemId = character_two_inventory['itemIds'][character_two_inventory['itemHashes'].index(itemHash)]
            except ValueError:
                try: 
                    itemId = vault_inventory['itemIds'][vault_inventory['itemHashes'].index(itemHash)]
                except ValueError:
                    print(print_linenumber(), " itemId : Not Found, probably a subclass or something like that.")
                    itemId = -1
    print(print_linenumber(), "                             itemId : " + str(itemId))
    return int(itemId)
    

def bucket_hash_from_itemHash(itemHash, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory):
    #print(print_linenumber(), "     FUNCTION : bucket_hash_from_itemHash    : " + str(datetime.datetime.now()).split('.')[0])
    #print(print_linenumber(), "              : bucket_hash_from_itemHash    : itemHash                 : " + str(itemHash))    
    #print(print_linenumber(), "              : bucket_hash_from_itemHash    : character_zero_inventory : " + str(character_zero_inventory))    
    #print(print_linenumber(), "              : bucket_hash_from_itemHash    : character_one_inventory  : " + str(character_one_inventory))    
    #print(print_linenumber(), "              : bucket_hash_from_itemHash    : character_two_inventory  : " + str(character_two_inventory))    
    #print(print_linenumber(), "              : bucket_hash_from_itemHash    : vault_inventory          : " + str(vault_inventory))    

    bucket_hash = ""
    try:
        bucket_hash = character_zero_inventory['bucket_hashes'][character_zero_inventory['itemHashes'].index(itemHash)]
    except ValueError:
        try:
            bucket_hash = character_one_inventory['bucket_hashes'][character_one_inventory['itemHashes'].index(itemHash)]
        except ValueError:
            try:
                bucket_hash = character_two_inventory['bucket_hashes'][character_two_inventory['itemHashes'].index(itemHash)]
            except ValueError:
                try: 
                    bucket_hash = vault_inventory['bucket_hashes'][vault_inventory['itemHashes'].index(itemHash)]
                except ValueError:
                    print(print_linenumber(), " bucket_hash : Not Found, probably a subclass or something like that.")
                    bucket_hash = -1
    print(print_linenumber(), "                             bucket_hash : " + str(bucket_hash))
    return int(bucket_hash)
    

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


def item_hash_from_name(name):
    print(print_linenumber(), "     FUNCTION : item_hash_from_name : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              : item_hash_from_name          : name                     : " + str(name))    
    
    sql = "SELECT json->>'itemHash' AS itemHash from DestinyInventoryItemDefinition WHERE json->>'itemName' = '" + name + "';"
    item_hash = query_bungie_db(sql)[0]
    item_hash = item_hash[0]
 
    print(print_linenumber(), "                          item_hash : " + str(item_hash)) 
    return str(item_hash)
    
    
def get_all_exotics_in_game(auth_token):
    print(print_linenumber(), "     FUNCTION :      get_all_exotics : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              :      get_all_exotics         : auth_token               : " + str(auth_token))
     
    global main_domain
    global api_key      
    
    url = main_domain + "/Platform/Destiny/Explorer/Items/?count=500&rarity=Exotic"
    exotics = call_api(url, api_key, auth_token)['Response']['data']['itemHashes']
    
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


'''character = {'Subclass': dict 
                       { "itemHash", dict 
                                    { "itemName", value } 
                                    { "itemId", value } 
                                    { "itemHash", value } 
                                    { "bucketHash", value } 
                                    { "transferStatus", value } 
                        } 
                       { "itemHash", dict 
                                    { "itemName", value } 
                                    { "itemId", value } 
                                    { "itemHash", value } 
                                    { "bucketHash", value } 
                                    { "transferStatus", value } 
                        } 
            {'Primary Weapons': dict 
                       { "itemHash", dict 
                                    { "itemName", value } 
                                    { "itemId", value } 
                                    { "itemHash", value } 
                                    { "bucketHash", value } 
                                    { "transferStatus", value } 
                        } 
                        { "itemHash", dict 
                                    { "itemName", value } 
                                    { "itemId", value } 
                                    { "itemHash", value } 
                                    { "bucketHash", value } 
                                    { "transferStatus", value } 
                        } '''
                        


def is_bucket_full(character_inventory, bucket_hashes, bucket_type, max_items, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault):
    #print(print_linenumber(), "     FUNCTION : is_bucket_full : " + str(datetime.datetime.now()).split('.')[0])
    #print(print_linenumber(), "              : is_bucket_full               : character_inventory      : " + str(character_inventory))
    #print(print_linenumber(), "              : is_bucket_full               : bucket_hashes            : " + str(bucket_hashes))
    #print(print_linenumber(), "              : is_bucket_full               : bucket_type              : " + str(bucket_type))
    #print(print_linenumber(), "              : is_bucket_full               : max_items                : " + str(max_items))

    #bucket_count = character_inventory['bucket_hashes'].count(int(bucket_hashes[bucket_type]))

    #print(print_linenumber(), "str(bucket_type) : " + str(bucket_type))
    #print(print_linenumber(), "bucket_hashes_weapons : " + str(bucket_hashes_weapons))
    #print(print_linenumber(), "bucket_hashes_weapons.values() : " + str(bucket_hashes_weapons.values()))
    
    #bucket_type = next(find_dict_key_by_value(bucket_hashes_weapons, str(bucket_hash)), None)
    
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
        print(print_linenumber(), "                            loadout : " + str(loadout))
            
        if ("trial" in loadout) or ("osiris" in loadout) or "tyrrells" in loadout or "cyrus" in loadout or "trowels" in loadout:
            loadout_name = "TRIALS"
        elif "iron banner" in loadout or "iron banner gear" in loadout or "iron banana" in loadout or "lord salad man's party" in loadout:
            loadout_name = "IRON_BANNER"
        elif "iron" in loadout or "banner" in loadout or "banana" in loadout or "salad" in loadout or "saladin" in loadout:
            loadout_name = "IRON_BANNER"
        elif "ranked" in loadout or "competitive" in loadout or "ranked playlist" in loadout or "ranked matches" in loadout or "ranked match" in loadout:
            loadout_name = "COMPETITIVE_PLAY"           
        elif "quick" in loadout or "crucible" in loadout or "p. v. p." in loadout or "quick play" in loadout:
            loadout_name = "QUICK_PLAY"
        elif "strike" in loadout or "p. v. e." in loadout or "strikes" in loadout:
            loadout_name = "STRIKE"              
        elif "patrol" in loadout or "lost" in loadout or "sector" in loadout or "public" in loadout or "event" in loadout:
            loadout_name = "PATROL"            
        elif "adventure" in loadout or "flash" in loadout or "point" in loadout or "farm" in loadout:
            loadout_name = "PATROL"    
        elif "lost sector" in loadout or "lost sectors" in loadout or "public event" in loadout or "public events" in loadout:
            loadout_name = "PATROL"   
        elif "adventures" in loadout or "flashpoint" in loadout or "flashpoints" in loadout or "the farm" in loadout:
            loadout_name = "PATROL"   
        elif "favorite" in loadout or "favourite" in loadout:
            loadout_name = "FAVORITE"              
        elif "desolate" in loadout or "taken" in loadout or "taken shiver" in loadout:
            loadout_name = "DESOLATE"              
        elif "v. o. g." in loadout or "hezen lords" in loadout or "hezen" in loadout or "ka beers" in loadout or "kabrs" in loadout:
            loadout_name = "VAULT_OF_GLASS"    
        elif "kabers" in loadout or "prime zealot" in loadout or "vault" in loadout or "glass" in loadout or "Vltava" in loadout:
            loadout_name = "VAULT_OF_GLASS"    
        elif "crota" in loadout or "krota" in loadout or "crota's end" in loadout or "crotas end" in loadout or "cuirass" in loadout:
            loadout_name = "CROTAS_END"          
        elif "curassis" in loadout or "curasis" in loadout or "death singers" in loadout or "deathsingers" in loadout or "death singer's" in loadout or "chronos" in loadout:
            loadout_name = "CROTAS_END" 
        elif "oryx" in loadout or "totems" in loadout or "daughters of oryx" in loadout or "golgorath" in loadout or "golgoroth" in loadout or "war numens" in loadout:
            loadout_name = "KINGS_FALL"  
        elif "kings fall" in loadout or "king's fall" in loadout or "dark hallow" in loadout or "darkhallow" in loadout or "harrowed" in loadout:
            loadout_name = "KINGS_FALL"      
        elif "spliced red misama" in loadout or "spliced red miasma" in loadout or "spliced nanomania" in loadout or "cosmoclast" in loadout or "spliced cosmoclast" in loadout:
            loadout_name = "WRATH_OF_THE_MACHINE"              
        elif "miasma" in loadout or "misama" in loadout or "red misama" in loadout or "red miasma" in loadout or "perfected siva" in loadout:
            loadout_name = "WRATH_OF_THE_MACHINE"    
        elif "siva" in loadout or "spliced" in loadout or "nanomania" in loadout or "nano mania" in loadout or "wrath" in loadout or "machine" in loadout:
            loadout_name = "WRATH_OF_THE_MACHINE"
        #elif "raid part four" in loadout or "the raid part four":
        #    loadout_name = "RAID_PART_4"  
        #elif "raid part three" in loadout or "the raid part three":
        #    loadout_name = "RAID_PART_3"              
        #elif "raid part two" in loadout or "the raid part two":
        #    loadout_name = "RAID_PART_2"              
        #elif "the raid" in loadout or "raid" in loadout:
        #    loadout_name = "RAID"  
        else:
            loadout_name = "DEFAULT"
    else:
        loadout_name = "DEFAULT"
        
    print(print_linenumber(), "                       loadout_name : " + str(loadout_name))            
    return str(loadout_name)
        
        
def get_character_equipped_items(auth_token, membership_type, membership_id, character_id, exotics, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory):
    print(print_linenumber(), "     FUNCTION : get_character_equipped_items : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              : get_character_equipped_items : auth_token               : " + str(auth_token))
    print(print_linenumber(), "              : get_character_equipped_items : membership_type          : " + str(membership_type))
    print(print_linenumber(), "              : get_character_equipped_items : membership_id            : " + str(membership_id))
    print(print_linenumber(), "              : get_character_equipped_items : character_id             : " + str(character_id))
    print(print_linenumber(), "              : get_character_equipped_items : exotics                  : " + str(exotics))
    print(print_linenumber(), "              : get_character_equipped_items : character_zero_inventory : " + str(character_zero_inventory))
    print(print_linenumber(), "              : get_character_equipped_items : character_one_inventory  : " + str(character_one_inventory))
    print(print_linenumber(), "              : get_character_equipped_items : character_two_inventory  : " + str(character_two_inventory))    
    print(print_linenumber(), "              : get_character_equipped_items : vault_inventory          : " + str(vault_inventory))    
     
    global main_domain
    global api_key      

    exotic_items = []
    itemHashes = []
    itemIds = []
    bucket_hashes = []
    equipped_items = {"exotic_item": exotic_items, "itemHash": itemHashes, "itemId": itemIds, "bucket_hash": bucket_hashes}
    
    url = main_domain + "/Platform/Destiny/" + str(membership_type) + "/Account/" \
        + str(membership_id) + "/Character/" + str(character_id) + "/" 
    character_equipped_items = call_api(url, api_key, auth_token)['Response']['data']['characterBase']['peerView']['equipment']
    print(print_linenumber(), "           character_equipped_items : " + str(character_equipped_items))
    
    for index, item in enumerate(character_equipped_items):
        itemHashes.append(item['itemHash'])    
        exotic_items.append(is_it_an_exotic(item['itemHash'], exotics))
        itemIds.append(itemId_from_itemHash(item['itemHash'], character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory))
        bucket_hashes.append(bucket_hash_from_itemHash(item['itemHash'], character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory))
       
    print(print_linenumber(), "                       exotic_items : " + str(exotic_items))        
    print(print_linenumber(), "                         itemHashes : " + str(itemHashes))
    return equipped_items    
    
    
def get_character_inventories(auth_token, membership_type, membership_id):
    print(print_linenumber(), "     FUNCTION : get_character_inventories : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              : get_character_inventories    : auth_token               : " + str(auth_token))
    print(print_linenumber(), "              : get_character_inventories    : membership_type          : " + str(membership_type))
    print(print_linenumber(), "              : get_character_inventories    : membership_id            : " + str(membership_id))
     
    global main_domain
    global api_key  

    character_zero_itemHashes = []
    character_zero_itemIds = []
    character_zero_bucket_hashes = []
    character_zero_characterIndices = []
    character_zero_quantities = []
    character_zero_bucket_is_full = []
    character_zero_inventory = {'itemHashes': character_zero_itemHashes, \
                                'itemIds': character_zero_itemIds, \
                                'bucket_hashes': character_zero_bucket_hashes, \
                                'quantities': character_zero_quantities, \
                                'bucketsFull': character_zero_bucket_is_full}
    character_one_itemHashes = []
    character_one_itemIds = []
    character_one_bucket_hashes = []
    character_one_characterIndices = []
    character_one_quantities = []
    character_one_bucket_is_full = []
    character_one_inventory = {'itemHashes': character_one_itemHashes, \
                                'itemIds': character_one_itemIds, \
                                'bucket_hashes': character_one_bucket_hashes, \
                                'quantities': character_one_quantities, \
                                'bucketsFull': character_one_bucket_is_full}
    character_two_itemHashes = []
    character_two_itemIds = []
    character_two_bucket_hashes = []
    character_two_characterIndices = []
    character_two_quantities = []
    character_two_bucket_is_full = []
    character_two_inventory = {'itemHashes': character_two_itemHashes, \
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

    #bucket_hashes_all = dict(query_bungie_db("SELECT json->>'bucketName' AS bucketName, json->>'hash' AS bucketHash FROM DestinyInventoryBucketDefinition ORDER BY bucketName;"))
    #print(print_linenumber(), "                  bucket_hashes_all : " + str(bucket_hashes_all))

    bucket_hashes = dict(query_bungie_db("SELECT json->>'bucketName' AS bucketName, json->>'hash' AS bucketHash FROM DestinyInventoryBucketDefinition WHERE json->>'bucketName' = 'Primary Weapons' or json->>'bucketName' = 'Special Weapons' or json->>'bucketName' = 'Heavy Weapons' or json->>'bucketName' = 'Helmet' or json->>'bucketName' = 'Gauntlets' or json->>'bucketName' = 'Chest Armor' or json->>'bucketName' = 'Leg Armor' or json->>'bucketName' = 'Class Armor' or json->>'bucketName' = 'Artifacts' or json->>'bucketName' = 'Ghost' or json->>'bucketName' = 'Emblems' or json->>'bucketName' = 'Ships' or json->>'bucketName' = 'Shaders' or json->>'bucketName' = 'Emotes' or json->>'bucketName' = 'Vehicle' or json->>'bucketName' = 'Sparrow Horn' ORDER BY json->>'bucketName';"))
    print(print_linenumber(), "                      bucket_hashes : " + str(bucket_hashes))
    
    bucket_hashes_weapons = dict(query_bungie_db("SELECT json->>'bucketName' AS bucketName, json->>'hash' AS bucketHash FROM DestinyInventoryBucketDefinition WHERE json->>'bucketName' = 'Primary Weapons' or json->>'bucketName' = 'Special Weapons' or json->>'bucketName' = 'Heavy Weapons' ORDER BY json->>'bucketName';"))
    print(print_linenumber(), "              bucket_hashes_weapons : " + str(bucket_hashes_weapons))

    bucket_hashes_armor = dict(query_bungie_db("SELECT json->>'bucketName' AS bucketName, json->>'hash' AS bucketHash FROM DestinyInventoryBucketDefinition WHERE json->>'bucketName' = 'Helmet' or json->>'bucketName' = 'Gauntlets' or json->>'bucketName' = 'Chest Armor' or json->>'bucketName' = 'Leg Armor' or json->>'bucketName' = 'Class Armor' or json->>'bucketName' = 'Artifacts' or json->>'bucketName' = 'Ghost' ORDER BY json->>'bucketName';"))
    print(print_linenumber(), "                bucket_hashes_armor : " + str(bucket_hashes_armor))
    
    bucket_hashes_general = dict(query_bungie_db("SELECT json->>'bucketName' AS bucketName, json->>'hash' AS bucketHash FROM DestinyInventoryBucketDefinition WHERE json->>'bucketName' = 'Emblems' or json->>'bucketName' = 'Ships' or json->>'bucketName' = 'Shaders' or json->>'bucketName' = 'Emotes' or json->>'bucketName' = 'Vehicle' or json->>'bucketName' = 'Sparrow Horn' ORDER BY json->>'bucketName';"))
    print(print_linenumber(), "            bucket_hashes_general : " + str(bucket_hashes_general))
    
    bucket_hashes_vault = dict(query_bungie_db("SELECT json->>'bucketName' AS bucketName, json->>'hash' AS bucketHash FROM DestinyInventoryBucketDefinition WHERE json->>'bucketName' = 'Weapons' or json->>'bucketName' = 'Armor' or json->>'bucketName' = 'General' ORDER BY json->>'bucketName';"))
    print(print_linenumber(), "                bucket_hashes_vault : " + str(bucket_hashes_vault))

    bucket_hashes_subclass = dict(query_bungie_db("SELECT json->>'bucketName' AS bucketName, json->>'hash' AS bucketHash FROM DestinyInventoryBucketDefinition WHERE json->>'bucketName' = 'Subclass' ORDER BY json->>'bucketName';"))
    print(print_linenumber(), "             bucket_hashes_subclass : " + str(bucket_hashes_subclass))

    # Subclass   | 3284755031
    
    url = main_domain + "/Platform/Destiny/" + str(membership_type) + "/Account/" + str(membership_id) + "/Items/" 
    account_inventory_from_api = call_api(url, api_key, auth_token)['Response']['data']['items']

    # TRYING TO ADD REAL BUCKET TYPES FROM QUERYING VAULT INSTEAD OF ITEMS
    # http://www.bungie.net/Platform/Destiny/{membershipType}/MyAccount/Vault/Summary/
    url = main_domain + "/Platform/Destiny/" + str(membership_type) + "/MyAccount/Vault/Summary/?definitions=true" 
    vault_inventory_from_api = call_api(url, api_key, auth_token)['Response']['definitions']['items']

    # print(print_linenumber(), "   vault_inventory_from_api : " + str(vault_inventory_from_api))
    
    #{
    #  "Response": {
    #    "data": {
    #    "definitions": {
    #      "items": {
    #        "201220485": {
    #          "itemHash": 201220485,
    #          "itemName": "Iron Saga Vest",
    #          "itemDescription": "Thus armed were the Iron Lords of old, in the days after the Collapse.",
    #          "icon": "/common/destiny_content/icons/43ba33377e3c950aa7a8a8c891045de8.jpg",
    #          "hasIcon": true,
    #          "secondaryIcon": "/img/misc/missing_icon.png",
    #          "actionName": "Dismantle",
    #          "hasAction": true,
    #          "deleteOnAction": true,
    #          "tierTypeName": "Legendary",
    #          "tierType": 5,
    #          "itemTypeName": "Chest Armor",
    #          "bucketTypeHash": 14239492,

    for index, item in enumerate(account_inventory_from_api):
        #print(print_linenumber(), "                              index : " + str(index))
        #print(print_linenumber(), "                               item : " + str(item))
        
        if item['characterIndex'] == 0:
            #print(print_linenumber(), "        item['characterIndex'] == 0 : ")
            if item['transferStatus'] != 2 and str(item['bucketHash']) not in bucket_hashes_subclass.values():
            #if item['transferStatus'] != 2 and item['bucketHash'] not in bucket_hashes['Subclass'].values():
                #print(print_linenumber(), "item['transferStatus'] != 2 and item['bucketHash'] not in bucket_hashes_subclass.values() : ")
                character_zero_itemHashes.append(item['itemHash'])
                character_zero_itemIds.append(item['itemId'])
                character_zero_characterIndices.append(item['characterIndex'])
                character_zero_quantities.append(item['quantity'])
                character_zero_bucket_hashes.append(item['bucketHash'])
        elif item['characterIndex'] == 1:
            #print(print_linenumber(), "        item['characterIndex'] == 1 : ")
            if item['transferStatus'] != 2 and str(item['bucketHash']) not in bucket_hashes_subclass.values():
            #if item['transferStatus'] != 2 and item['bucketHash'] not in bucket_hashes['Subclass'].values():
                #print(print_linenumber(), "item['transferStatus'] != 2 and item['bucketHash'] not in bucket_hashes_subclass.values() : ")
                character_one_itemHashes.append(item['itemHash'])
                character_one_itemIds.append(item['itemId'])
                character_one_characterIndices.append(item['characterIndex'])
                character_one_quantities.append(item['quantity'])
                character_one_bucket_hashes.append(item['bucketHash'])
        elif item['characterIndex'] == 2:
            #print(print_linenumber(), "        item['characterIndex'] == 2 : ")
            if item['transferStatus'] != 2 and str(item['bucketHash']) not in bucket_hashes_subclass.values():
            #if item['transferStatus'] != 2 and item['bucketHash'] not in bucket_hashes['Subclass'].values():
                #print(print_linenumber(), "item['transferStatus'] != 2 and item['bucketHash'] not in bucket_hashes_subclass.values() : ")
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
                vault_bucket_hashes.append(vault_inventory_from_api[str(item['itemHash'])]['bucketTypeHash'])
            else:
                print(print_linenumber(), "str(item['bucketHash']) not in bucket_hashes_vault.values() : ")
                print(print_linenumber(), "                bucket_hashes_vault : " + str(bucket_hashes_vault))
                print(print_linenumber(), "                 item['bucketHash'] : " + str(item['bucketHash']))
        else:
            print(print_linenumber(), "                                ERROR : This should never happen.  Character index for item was not 0, 1, 2, or -1.  ")
            print(print_linenumber(), "               item['characterIndex'] : " + str(item['characterIndex']))
            
    print(print_linenumber(), "                    vault_inventory : " + str(vault_inventory))
    
    character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory = mark_full_inventories(character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault)

    return character_zero_inventory, character_one_inventory, \
           character_two_inventory, vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault, bucket_hashes_subclass


def mark_full_inventories(character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault):
    print(print_linenumber(), "     FUNCTION : mark_full_inventories : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              : mark_full_inventories        : character_zero_inventory : " + str(character_zero_inventory))
    print(print_linenumber(), "              : mark_full_inventories        : character_one_inventory  : " + str(character_one_inventory))
    print(print_linenumber(), "              : mark_full_inventories        : character_two_inventory  : " + str(character_two_inventory))
    print(print_linenumber(), "              : mark_full_inventories        : vault_inventory          : " + str(vault_inventory))
    print(print_linenumber(), "              : mark_full_inventories        : bucket_hashes            : " + str(bucket_hashes))

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
           

def save_loadout(display_name, membership_id_bungie, membership_type, membership_id, character_id, character_race, character_gender, character_class, loadout_name, equipped_items, timestamp):
    print(print_linenumber(), "     FUNCTION : save_loadout : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              : save_loadout                 : display_name             : " + str(display_name))
    print(print_linenumber(), "              : save_loadout                 : membership_id_bungie     : " + str(membership_id_bungie))
    print(print_linenumber(), "              : save_loadout                 : membership_type          : " + str(membership_type))
    print(print_linenumber(), "              : save_loadout                 : membership_id            : " + str(membership_id))
    print(print_linenumber(), "              : save_loadout                 : character_id             : " + str(character_id))
    print(print_linenumber(), "              : save_loadout                 : character_race           : " + str(character_race))
    print(print_linenumber(), "              : save_loadout                 : character_gender         : " + str(character_gender))
    print(print_linenumber(), "              : save_loadout                 : character_class          : " + str(character_class))
    print(print_linenumber(), "              : save_loadout                 : loadout_name             : " + str(loadout_name))
    print(print_linenumber(), "              : save_loadout                 : equipped_items           : " + str(equipped_items))
    print(print_linenumber(), "              : save_loadout                 : timestamp                : " + str(timestamp))

    global db_host
    global db_name_alexa
    global db_user
    global db_pass
    global db_port

    equipped_items_encoded = pickle.dumps(equipped_items).encode('base64', 'strict')
    equipped_items = equipped_items_encoded
    
    # SEE IF LOADOUT ALREADY EXISTS
    exists = query_alexa_db("SELECT equipped_items FROM public.loadouts WHERE membership_id_bungie = '" + str(membership_id_bungie) + "' AND membership_type =  '" + str(membership_type) + "' AND membership_id = '" + str(membership_id) + "' AND character_id = '" + str(character_id) + "' AND character_race = '" + str(character_race) + "' AND character_gender = '" + str(character_gender) + "' AND character_class = '" + str(character_class) + "' AND loadout_name = '" + str(loadout_name) + "';")

    conn = None
    conn = psycopg2.connect(host=db_host, database=db_name_alexa, user=db_user, \
                            password=db_pass, port=db_port)
    cur = conn.cursor()

    if exists:
        # UPDATE LOADOUT TO NEW LIST OF ITEMS
        sql = "UPDATE public.loadouts SET equipped_items = '" + str(equipped_items) + "' WHERE membership_id_bungie = '" + str(membership_id_bungie) + "' AND membership_type =  '" + str(membership_type) + "' AND membership_id = '" + str(membership_id) + "' AND character_id = '" + str(character_id) + "' AND character_race = '" + str(character_race) + "' AND character_gender = '" + str(character_gender) + "' AND character_class = '" + str(character_class) + "' AND loadout_name = '" + str(loadout_name) + "';"
        cur.execute(sql)
        
        # UPDATE TIMESTAMP TO LAST MODIFIED DATE
        sql = "UPDATE public.loadouts SET timestamp = '" + str(timestamp) + "' WHERE membership_id_bungie = '" + str(membership_id_bungie) + "' AND membership_type =  '" + str(membership_type) + "' AND membership_id = '" + str(membership_id) + "' AND character_id = '" + str(character_id) + "' AND character_race = '" + str(character_race) + "' AND character_gender = '" + str(character_gender) + "' AND character_class = '" + str(character_class) + "' AND loadout_name = '" + str(loadout_name) + "';"
        cur.execute(sql)
    else:
        # INSERT NEW LOADOUT INTO DB
        sql = "INSERT INTO public.loadouts (membership_id_bungie, display_name, membership_type, membership_id, character_id, character_race, character_gender, character_class, loadout_name, equipped_items, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cur.execute(sql, (membership_id_bungie, display_name, membership_type, membership_id, character_id, character_race, character_gender, character_class, loadout_name, equipped_items, timestamp))
        
    cur.close()
    conn.commit()
    conn.close()

    card_title = app_title + " : SUCCESS : Loadout Saved."
    speech = "Loadout Saved for " + loadout_name.replace("_", " ").title() + "."
    end_session = True
    return alexa_speak(card_title, speech, end_session)
    

def equip_loadout(auth_token, display_name, membership_id_bungie, membership_type, membership_id, character_id, character_race, character_gender, character_class, loadout_name, equipped_items, user_info, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault, bucket_hashes_subclass):
    print(print_linenumber(), "     FUNCTION :       equip_loadout : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              :       equip_loadout          : display_name             : " + str(display_name))
    print(print_linenumber(), "              :       equip_loadout          : membership_id_bungie     : " + str(membership_id_bungie))
    print(print_linenumber(), "              :       equip_loadout          : membership_type          : " + str(membership_type))
    print(print_linenumber(), "              :       equip_loadout          : membership_id            : " + str(membership_id))
    print(print_linenumber(), "              :       equip_loadout          : character_id             : " + str(character_id))
    print(print_linenumber(), "              :       equip_loadout          : character_race           : " + str(character_race))
    print(print_linenumber(), "              :       equip_loadout          : character_gender         : " + str(character_gender))
    print(print_linenumber(), "              :       equip_loadout          : character_class          : " + str(character_class))
    print(print_linenumber(), "              :       equip_loadout          : loadout_name             : " + str(loadout_name))
    print(print_linenumber(), "              :       equip_loadout          : equipped_items           : " + str(equipped_items))
    print(print_linenumber(), "              :       equip_loadout          : user_info                : " + str(user_info))
    print(print_linenumber(), "              :       equip_loadout          : bucket_hashes            : " + str(bucket_hashes))
    print(print_linenumber(), "              :       equip_loadout          : character_zero_inventory : " + str(character_zero_inventory))
    print(print_linenumber(), "              :       equip_loadout          : character_one_inventory  : " + str(character_one_inventory))
    print(print_linenumber(), "              :       equip_loadout          : character_two_inventory  : " + str(character_two_inventory))
    print(print_linenumber(), "              :       equip_loadout          : vault_inventory          : " + str(vault_inventory))
    
    global main_domain
    global api_key  
    global db_host
    global db_name_alexa
    global db_user
    global db_pass
    global db_port

    list_of_items_to_equip = ""
    
    armor = ['Chest Armor', 'Helmet', 'Gauntlets', 'Leg Armor', 'Class Armor']
    weapons = ['Special Weapons', 'Primary Weapons', 'Heavy Weapons']
    general = ['Ships', 'Vehicle', 'Ghost', 'Emblems', 'Shaders', 'Emotes', 'Sparrow Horn', 'Artifacts']
    
    conn = None
    conn = psycopg2.connect(host=db_host, database=db_name_alexa, user=db_user, \
                            password=db_pass, port=db_port)
    cur = conn.cursor()
    
    loadout_encoded = query_alexa_db("SELECT equipped_items FROM public.loadouts WHERE membership_id_bungie = '" + str(membership_id_bungie) + "' AND membership_type =  '" + str(membership_type) + "' AND membership_id = '" + str(membership_id) + "' AND character_id = '" + str(character_id) + "' AND character_race = '" + str(character_race) + "' AND character_gender = '" + str(character_gender) + "' AND character_class = '" + str(character_class) + "' AND loadout_name = '" + str(loadout_name) + "';")
    
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

    # Make loadout_decoded become equipped_items
    # DO THIS FOR EXOTICS ONLY / FIRST TO AVOID EXOTIC RACE CONDITION
    for key, value in enumerate(equipped_items['exotic_item']):
        #print(print_linenumber(), "                                key : " + str(key))
        #print(print_linenumber(), "                              value : " + str(value))
        if value == 1:
            print(print_linenumber(), "                     value == 1 : ")
            # EXOTIC ITEM EQUIPPED IN THIS SLOT
            print(print_linenumber(), "              Exotic Found Equipped : " + str(equipped_items['itemHash'][key]))
            print(print_linenumber(), "             Replace the Exotic with: " + str(loadout_decoded['itemHash'][key]))
            itemId = loadout_decoded['itemId'][key]
            itemHash = loadout_decoded['itemHash'][key]
            if equipped_items['itemId'][key] == itemId:
                print(print_linenumber(), "equipped_items['itemId'][key] == itemId : ")
                # SAME ITEM EQUIPPED AS IN LOADOUT, SO DO NOTHING
                print(print_linenumber(), "                               INFO : This item in loadout is same as one already equipped, no action necessary: " + str(equipped_items['itemHash'][key]))
            else:
                print(print_linenumber(), "equipped_items['itemId'][key] <> itemId : ")
                # FIND CHARACTER ID OF ITEM TO EQUIP LOCATION
                location_id = find_item_location(user_info, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, itemId, itemHash)
                print(print_linenumber(), "location_id : " + str(location_id))
                if str(location_id) == (user_info['character_zero_id']):
                    print(print_linenumber(), "location_id == user_info['character_zero_id'] : ")
                    # THE ITEM IS LOCATED ON THIS CHARACTER, JUST NOT EQUIPPED YET
                    print(print_linenumber(), "                               INFO : This item is already on this character, no transfer necessary: " + str(equipped_items['itemHash'][key]))
                else:
                    print(print_linenumber(), "location_id <> user_info['character_zero_id'] : ")
                    # DO THE TRANSFER SHUFFLE
                    bucket_hash = equipped_items['bucket_hash'][key]

                    # armor = ['Chest Armor', 'Helmet', 'Gauntlets', 'Leg Armor', 'Class Armor']
                    # weapons = ['Special Weapons', 'Primary Weapons', 'Heavy Weapons']
                    # general = ['Ships', 'Vehicle', 'Ghost', 'Emblems', 'Shaders', 'Emotes', 'Sparrow Horn', 'Artifacts']
                    
                    # FIND TYPE OF BUCKET FOR A GENERIC ONE
                    #bucket_type = next(find_dict_key_by_value(bucket_hashes, str(equipped_items['bucket_hash'][key])), None)
                    
                    #bucket_type = next(find_dict_key_by_value(bucket_hashes['Weapons'], str(bucket_hash)), None)

                    if str(bucket_hash) in bucket_hashes_weapons.values():
                        print(print_linenumber(), "str(bucket_hash) in bucket_hashes_weapons.values() : ")
                        bucket_type = next(find_dict_key_by_value(bucket_hashes_weapons, str(bucket_hash)), None)
                        vault_bucket_type = "Weapons"
                    elif str(bucket_hash) in bucket_hashes_armor.values():
                        print(print_linenumber(), "str(bucket_hash) in bucket_hashes_armor.values() : ")
                        bucket_type = next(find_dict_key_by_value(bucket_hashes_armor, str(bucket_hash)), None)
                        vault_bucket_type = "Armor"
                    elif str(bucket_hash) in bucket_hashes_general.values():
                        print(print_linenumber(), "str(bucket_hash) in bucket_hashes_general.values() : ")
                        bucket_type = next(find_dict_key_by_value(bucket_hashes_general, str(bucket_hash)), None)
                        vault_bucket_type = "General"
                    elif str(bucket_hash) in bucket_hashes_subclass.values():
                        print(print_linenumber(), "str(bucket_hash) in bucket_hashes_subclass.values() : ")
                        bucket_type = "Subclass"
                    elif str(bucket_hash) in bucket_hashes_vault.values():
                        print(print_linenumber(), "str(bucket_hash) in bucket_hashes_vault.values() : ")
                        bucket_type = "Vault"
                        vault_bucket_type = "Vault"
                    else:
                        print(print_linenumber(), "str(bucket_hash) not found in any bucket_hashes : ")
                        print(print_linenumber(), "str(bucket_hash) : " + str(bucket_hash))
                    
                    if bucket_hash > 0:
                        if bucket_type in character_zero_inventory['bucketsFull']:
                            print(print_linenumber(), "bucket_type in character_zero_inventory['bucketsFull'] : ")
                            print(print_linenumber(), "bucket_type : " + str(bucket_type))
                            print(print_linenumber(), "character_zero_inventory['bucketsFull'] : " + str(character_zero_inventory['bucketsFull']))
                            # THIS CHARACTER IS FULL OF THIS TYPE OF ITEM
                            # NEED TO MAKE THIS CHARACTER NOT FULL
                        #    if bucket_type in armor:
                        #        print(print_linenumber(), "           bucket_type in armor : ")
                        #        vault_bucket_type = "Armor"
                        #    elif bucket_type in weapons:
                        #        print(print_linenumber(), "         bucket_type in weapons : ")
                        #        vault_bucket_type = "Weapons"
                        #    elif bucket_type in general:
                        #        print(print_linenumber(), "         bucket_type in general : ")
                        #        vault_bucket_type = "General"
                                
                            free_vault_space(auth_token, display_name, membership_id_bungie, membership_type, membership_id, character_id, character_race, character_gender, character_class, loadout_name, equipped_items, user_info, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, vault_bucket_type, bucket_type, bucket_hash, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault)
    
                            # VAULT HAS SPACE NOW, TRANSFER A RANDOM ITEM AWAY TO VAULT
                            counter = 0
                            for bucket_hash_key, bucket_hash_value in enumerate(character_zero_inventory['bucket_hashes']):
                                print(print_linenumber(), "                                key : " + str(key))
                                print(print_linenumber(), "                              value : " + str(value))
                                print(print_linenumber(), "                    bucket_hash_key : " + str(bucket_hash_key))
                                print(print_linenumber(), "                  bucket_hash_value : " + str(bucket_hash_value))
                                if bucket_hash_value == bucket_hash and counter == 0:
                                    print(print_linenumber(), "bucket_hash_value == bucket_hash and counter == 0 : ")
                                    other_itemId = character_zero_inventory['itemIds'][bucket_hash_key]
                                    other_itemHash = character_zero_inventory['itemHashes'][bucket_hash_key]
                                    print(print_linenumber(), "                       other_itemId : " + str(other_itemId))
                                    print(print_linenumber(), "                     other_itemHash : " + str(other_itemHash))
                                    if equipped_items['itemId'][key] != other_itemId and loadout_decoded['itemId'][key] != other_itemId and counter == 0:
                                        print(print_linenumber(), "equipped_items['itemId'][key] != other_itemId and loadout_decoded['itemId'][key] != other_itemId and counter == 0 : ")
                                        counter = 1
                                        print(print_linenumber(), "                            counter : " + str(counter))
                                        # MOVE THIS other_itemId to vault to make room on character
                                        transfer_item(auth_token, other_itemHash, other_itemId, user_info['character_zero_id'], membership_type, "true")
                                        mark_full_inventories(character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault)
    
                            #if bucket_type in armor:
                            #    print(print_linenumber(), "           bucket_type in armor : ")
                            #    vault_bucket_type = "Armor"
                            #elif bucket_type in weapons:
                            #    print(print_linenumber(), "         bucket_type in weapons : ")
                            #    vault_bucket_type = "Weapons"
                            #elif bucket_type in general:
                            #    print(print_linenumber(), "         bucket_type in general : ")
                            #    vault_bucket_type = "General"
                            free_vault_space(auth_token, display_name, membership_id_bungie, membership_type, membership_id, character_id, character_race, character_gender, character_class, loadout_name, equipped_items, user_info, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, vault_bucket_type, bucket_type, bucket_hash, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault)
                        
                        # FINALLY MOVE THE REAL ITEM TO VAULT FROM OTHER CHARACTER (-1 is vault location)
                        if str(location_id) == (user_info['character_one_id']) or str(location_id) == (user_info['character_two_id']):
                            print(print_linenumber(), "                location_id > 0 : ")
                            transfer_item(auth_token, itemHash, itemId, location_id, membership_type, "true")
                            mark_full_inventories(character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault)                    
                        
                        # THEN MOVE ITEM FROM VAULT TO CHARACTER ZERO
                        transfer_item(auth_token, itemHash, itemId, user_info['character_zero_id'], membership_type, "false")
                        mark_full_inventories(character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault)     

                # NOW THAT ITEM IS TRANSFERRED TO CHARACTER, EQUIP IT.
                equip_item(auth_token, itemId, user_info['character_zero_id'], membership_type)


    for key, value in enumerate(equipped_items['exotic_item']):
        print(print_linenumber(), "                                key : " + str(key))
        print(print_linenumber(), "                              value : " + str(value))
        if value == 0:
            print(print_linenumber(), "                     value == 0 : ")
            # EXOTIC ITEM EQUIPPED IN THIS SLOT
            print(print_linenumber(), "          Non-Exotic Found Equipped : " + str(equipped_items['itemHash'][key]))
            print(print_linenumber(), "         Replace the Non-Exotic with: " + str(loadout_decoded['itemHash'][key]))
            itemId = loadout_decoded['itemId'][key]
            itemHash = loadout_decoded['itemHash'][key]
            if equipped_items['itemId'][key] == itemId:
                print(print_linenumber(), "equipped_items['itemId'][key] == itemId : ")
                # SAME ITEM EQUIPPED AS IN LOADOUT, SO DO NOTHING
                print(print_linenumber(), "                               INFO : This item in loadout is same as one already equipped, no action necessary: " + str(equipped_items['itemHash'][key]))
            else:
                print(print_linenumber(), "equipped_items['itemId'][key] <> itemId : ")
                # FIND CHARACTER ID OF ITEM TO EQUIP LOCATION
                location_id = find_item_location(user_info, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, itemId, itemHash)
                print(print_linenumber(), "location_id : " + str(location_id))
                print(print_linenumber(), "user_info['character_zero_id'] : " + str(user_info['character_zero_id']))
                if str(location_id) == (user_info['character_zero_id']):
                    print(print_linenumber(), "location_id == user_info['character_zero_id'] : ")
                    # THE ITEM IS LOCATED ON THIS CHARACTER, JUST NOT EQUIPPED YET
                    print(print_linenumber(), "                               INFO : This item is already on this character, no transfer necessary: " + str(equipped_items['itemHash'][key]))
                else:
                    print(print_linenumber(), "location_id <> user_info['character_zero_id'] : ")
                    # DO THE TRANSFER SHUFFLE
                    bucket_hash = equipped_items['bucket_hash'][key]

                    # armor = ['Chest Armor', 'Helmet', 'Gauntlets', 'Leg Armor', 'Class Armor']
                    # weapons = ['Special Weapons', 'Primary Weapons', 'Heavy Weapons']
                    # general = ['Ships', 'Vehicle', 'Ghost', 'Emblems', 'Shaders', 'Emotes', 'Sparrow Horn', 'Artifacts']
                    
                    # FIND TYPE OF BUCKET FOR A GENERIC ONE
                    #bucket_type = next(find_dict_key_by_value(bucket_hashes, str(equipped_items['bucket_hash'][key])), None)
                    if str(bucket_hash) in bucket_hashes_weapons.values():
                        print(print_linenumber(), "str(bucket_hash) in bucket_hashes_weapons.values() : ")
                        bucket_type = next(find_dict_key_by_value(bucket_hashes_weapons, str(bucket_hash)), None)
                        vault_bucket_type = "Weapons"
                    elif str(bucket_hash) in bucket_hashes_armor.values():
                        print(print_linenumber(), "str(bucket_hash) in bucket_hashes_armor.values() : ")
                        bucket_type = next(find_dict_key_by_value(bucket_hashes_armor, str(bucket_hash)), None)
                        vault_bucket_type = "Armor"
                    elif str(bucket_hash) in bucket_hashes_general.values():
                        print(print_linenumber(), "str(bucket_hash) in bucket_hashes_general.values() : ")
                        bucket_type = next(find_dict_key_by_value(bucket_hashes_general, str(bucket_hash)), None)
                        vault_bucket_type = "General"
                    elif str(bucket_hash) in bucket_hashes_subclass.values():
                        print(print_linenumber(), "str(bucket_hash) in bucket_hashes_subclass.values() : ")
                        bucket_type = "Subclass"
                    elif str(bucket_hash) in bucket_hashes_vault.values():
                        print(print_linenumber(), "str(bucket_hash) in bucket_hashes_vault.values() : ")
                        bucket_type = "Vault"
                        vault_bucket_type = "Vault"
                    else:
                        print(print_linenumber(), "str(bucket_hash) not found in any bucket_hashes : ")
                        print(print_linenumber(), "str(bucket_hash) : " + str(bucket_hash))
                    
                    if bucket_hash > 0:
                        if bucket_type in character_zero_inventory['bucketsFull']:
                            # THIS CHARACTER IS FULL OF THIS TYPE OF ITEM
                            # NEED TO MAKE THIS CHARACTER NOT FULL
                        #    if bucket_type in armor:
                        #        print(print_linenumber(), "           bucket_type in armor : ")
                        #        vault_bucket_type = "Armor"
                        #    elif bucket_type in weapons:
                        #        print(print_linenumber(), "         bucket_type in weapons : ")
                        #        vault_bucket_type = "Weapons"
                        #    elif bucket_type in general:
                        #        print(print_linenumber(), "         bucket_type in general : ")
                        #        vault_bucket_type = "General"
                                
                            free_vault_space(auth_token, display_name, membership_id_bungie, membership_type, membership_id, character_id, character_race, character_gender, character_class, loadout_name, equipped_items, user_info, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, vault_bucket_type, bucket_type, bucket_hash, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault)
    
                            # VAULT HAS SPACE NOW, TRANSFER A RANDOM ITEM AWAY TO VAULT
                            counter = 0
                            for bucket_hash_key, bucket_hash_value in enumerate(character_zero_inventory['bucket_hashes']):
                                #print(print_linenumber(), "                                key : " + str(key))
                                #print(print_linenumber(), "                              value : " + str(value))
                                #print(print_linenumber(), "                    bucket_hash_key : " + str(bucket_hash_key))
                                #print(print_linenumber(), "                  bucket_hash_value : " + str(bucket_hash_value))
                                if bucket_hash_value == bucket_hash and counter == 0:
                                    print(print_linenumber(), "bucket_hash_value == bucket_hash and counter == 0 : ")
                                    other_itemId = character_zero_inventory['itemIds'][bucket_hash_key]
                                    other_itemHash = character_zero_inventory['itemHashes'][bucket_hash_key]
                                    print(print_linenumber(), "                       other_itemId : " + str(other_itemId))
                                    print(print_linenumber(), "                     other_itemHash : " + str(other_itemHash))
                                    if equipped_items['itemId'][key] != other_itemId and loadout_decoded['itemId'][key] != other_itemId and counter == 0:
                                        print(print_linenumber(), "equipped_items['itemId'][key] != other_itemId and loadout_decoded['itemId'][key] != other_itemId and counter == 0 : ")
                                        counter = 1
                                        print(print_linenumber(), "                            counter : " + str(counter))
                                        # MOVE THIS other_itemId to vault to make room on character
                                        transfer_item(auth_token, other_itemHash, other_itemId, user_info['character_zero_id'], membership_type, "true")
                                        mark_full_inventories(character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault)
    
                            #if bucket_type in armor:
                            #    print(print_linenumber(), "           bucket_type in armor : ")
                            #    vault_bucket_type = "Armor"
                            #elif bucket_type in weapons:
                            #    print(print_linenumber(), "         bucket_type in weapons : ")
                            #    vault_bucket_type = "Weapons"
                            #elif bucket_type in general:
                            #    print(print_linenumber(), "         bucket_type in general : ")
                            #    vault_bucket_type = "General"
                            free_vault_space(auth_token, display_name, membership_id_bungie, membership_type, membership_id, character_id, character_race, character_gender, character_class, loadout_name, equipped_items, user_info, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, vault_bucket_type, bucket_type, bucket_hash, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault)
                        
                        # FINALLY MOVE THE REAL ITEM TO VAULT FROM OTHER CHARACTER (-1 is vault location)
                        if str(location_id) == (user_info['character_one_id']) or str(location_id) == (user_info['character_two_id']):
                            print(print_linenumber(), "                location_id > 0 : ")
                            transfer_item(auth_token, itemHash, itemId, location_id, membership_type, "true")
                            mark_full_inventories(character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault)                    
                        
                        # THEN MOVE ITEM FROM VAULT TO CHARACTER ZERO
                        transfer_item(auth_token, itemHash, itemId, user_info['character_zero_id'], membership_type, "false")
                        mark_full_inventories(character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault)     

                # NOW THAT ITEM IS TRANSFERRED TO CHARACTER, EQUIP IT.
                equip_item(auth_token, itemId, user_info['character_zero_id'], membership_type)
        
    cur.close()
    conn.commit()
    conn.close()

    card_title = app_title + " : SUCCESS : Loadout Equipped."
    if loadout_name.upper() == "TRIALS":
        speech = "Loadout Equipped for " + loadout_name.replace("_", " ").title() + \
        ".  Don't forget to buy your boons."
    else:
        speech = "Loadout Equipped for " + loadout_name.replace("_", " ").title() + "."
    
    end_session = True
    return alexa_speak(card_title, speech, end_session)


def free_vault_space(auth_token, display_name, membership_id_bungie, membership_type, membership_id, character_id, character_race, character_gender, character_class, loadout_name, equipped_items, user_info, character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, vault_bucket_type, bucket_type, bucket_hash, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault):
    print(print_linenumber(), "     FUNCTION :    free_vault_space : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              :    free_vault_space          : display_name             : " + str(display_name))
    print(print_linenumber(), "              :    free_vault_space          : membership_id_bungie     : " + str(membership_id_bungie))
    print(print_linenumber(), "              :    free_vault_space          : membership_type          : " + str(membership_type))
    print(print_linenumber(), "              :    free_vault_space          : membership_id            : " + str(membership_id))
    print(print_linenumber(), "              :    free_vault_space          : character_id             : " + str(character_id))
    print(print_linenumber(), "              :    free_vault_space          : character_race           : " + str(character_race))
    print(print_linenumber(), "              :    free_vault_space          : character_gender         : " + str(character_gender))
    print(print_linenumber(), "              :    free_vault_space          : character_class          : " + str(character_class))
    print(print_linenumber(), "              :    free_vault_space          : loadout_name             : " + str(loadout_name))
    print(print_linenumber(), "              :    free_vault_space          : equipped_items           : " + str(equipped_items))
    print(print_linenumber(), "              :    free_vault_space          : vault_bucket_type        : " + str(vault_bucket_type))
    print(print_linenumber(), "              :    free_vault_space          : bucket_type              : " + str(bucket_type))
    print(print_linenumber(), "              :    free_vault_space          : bucket_hash              : " + str(bucket_hash))
    print(print_linenumber(), "              :    free_vault_space          : bucket_hashes            : " + str(bucket_hashes))
    print(print_linenumber(), "              :    free_vault_space          : character_zero_inventory : " + str(character_zero_inventory))
    print(print_linenumber(), "              :    free_vault_space          : character_one_inventory  : " + str(character_one_inventory))
    print(print_linenumber(), "              :    free_vault_space          : character_two_inventory  : " + str(character_two_inventory))
    print(print_linenumber(), "              :    free_vault_space          : vault_inventory          : " + str(vault_inventory))

    global main_domain
    global api_key  
    
    if vault_bucket_type in vault_inventory['bucketsFull']:
        print(print_linenumber(), "vault_bucket_type in vault_inventory['bucketsFull'] : ")
        # VAULT IS FULL FOR THIS TYPE PIECES
        if bucket_type in character_one_inventory['bucketsFull']:
            print(print_linenumber(), "bucket_type in character_one_inventory['bucketsFull'] : ")
            # DAMN CHARACTER ONE IS FULL OF THIS TYPE OF ITEM AS WELL
            if bucket_type in character_two_inventory['bucketsFull']:
                print(print_linenumber(), "bucket_type in character_two_inventory['bucketsFull'] : ")
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
                print(print_linenumber(), "bucket_type not in character_two_inventory['bucketsFull'] : ")
                print(print_linenumber(), "character_two_inventory['bucketsFull'] is not full of this bucket_type : ")
                # MOVE A RANDOM ITEM OF THIS TYPE FROM VAULT TO CHARACTER TWO
                counter = 0
                print(print_linenumber(), "                            counter : " + str(counter))
                for bucket_hash_key, bucket_hash_value in enumerate(vault_inventory['bucketTypeHashes']):
                    print(print_linenumber(), "                    bucket_hash_key : " + str(bucket_hash_key))
                    print(print_linenumber(), "                  bucket_hash_value : " + str(bucket_hash_value))
                    if bucket_hash_value == bucket_hash and counter == 0:
                        print(print_linenumber(), "bucket_hash_value == bucket_hash and counter == 0 : ")
                        other_itemId = vault_inventory['itemIds'][bucket_hash_key]
                        other_itemHash = vault_inventory['itemHashes'][bucket_hash_key]
                        print(print_linenumber(), "                       other_itemId : " + str(other_itemId))
                        print(print_linenumber(), "                     other_itemHash : " + str(other_itemHash))
                        if equipped_items['itemId'][bucket_hash_key] != other_itemId and loadout_decoded['itemId'][bucket_hash_key] != other_itemId and counter == 0:
                            print(print_linenumber(), "equipped_items['itemId'][bucket_hash_key] != other_itemId and loadout_decoded['itemId'][bucket_hash_key] != other_itemId and counter == 0 : ")
                            counter = 1
                            print(print_linenumber(), "                            counter : " + str(counter))
                            # MOVE THIS other_itemId to character two to make room in vault.
                            transfer_item(auth_token, other_itemHash, other_itemId, user_info['character_two_id'], membership_type, "false")
                            mark_full_inventories(character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault)
        else:
            # MOVE A RANDOM ITEM OF THIS TYPE FROM VAULT TO CHARACTER ONE
            counter = 0
            print(print_linenumber(), "                            counter : " + str(counter))
            for bucket_hash_key, bucket_hash_value in enumerate(vault_inventory['bucketTypeHashes']):
                print(print_linenumber(), "                    bucket_hash_key : " + str(bucket_hash_key))
                print(print_linenumber(), "                  bucket_hash_value : " + str(bucket_hash_value))
                if bucket_hash_value == bucket_hash and counter == 0:
                    print(print_linenumber(), "bucket_hash_value == bucket_hash and counter == 0 : ")
                    other_itemId = vault_inventory['itemIds'][bucket_hash_key]
                    other_itemHash = vault_inventory['itemHashes'][bucket_hash_key]
                    print(print_linenumber(), "                       other_itemId : " + str(other_itemId))
                    print(print_linenumber(), "                     other_itemHash : " + str(other_itemHash))
                    if equipped_items['itemId'][bucket_hash_key] != other_itemId and loadout_decoded['itemId'][bucket_hash_key] != other_itemId and counter == 0:
                        print(print_linenumber(), "equipped_items['itemId'][bucket_hash_key] != other_itemId and loadout_decoded['itemId'][bucket_hash_key] != other_itemId and counter == 0 : ")
                        counter = 1
                        print(print_linenumber(), "                            counter : " + str(counter))
                        # MOVE THIS other_itemId to character one to make room in vault.
                        transfer_item(auth_token, other_itemHash, other_itemId, user_info['character_one_id'], membership_type, "false")
                        mark_full_inventories(character_zero_inventory, character_one_inventory, character_two_inventory, vault_inventory, bucket_hashes, bucket_hashes_weapons, bucket_hashes_armor, bucket_hashes_general, bucket_hashes_vault)
    return


def transfer_item(auth_token, itemHash, itemId, character_id, membership_type, to_vault):
    print(print_linenumber(), "     FUNCTION :    transfer_item    : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              :    transfer_item             : itemHash                 : " + str(itemHash))
    print(print_linenumber(), "              :    transfer_item             : itemId                   : " + str(itemId))
    print(print_linenumber(), "              :    transfer_item             : character_id             : " + str(character_id))
    print(print_linenumber(), "              :    transfer_item             : membership_type          : " + str(membership_type))
    print(print_linenumber(), "              :    transfer_item             : to_vault                 : " + str(to_vault))
  
    url = main_domain + "/Platform/Destiny/TransferItem/"
    data='{"itemReferenceHash":"' + str(itemHash) + '","stackSize":"' + str(1) + '","transferToVault":"' + str(to_vault) + '","itemId":"' + str(itemId) + '","characterId":"' + str(character_id) + '","membershipType":' + str(membership_type) + '}'
    response = call_api(url, api_key, auth_token, data, method="POST")
    print(print_linenumber(), "                       data : " + str(data))
    print(print_linenumber(), "                   response : " + str(response))
    
    # IF LOCATION IS FULL
    # response : {u'ThrottleSeconds': 0, u'ErrorCode': 1642, u'ErrorStatus': u'DestinyNoRoomInDestination', u'Message': u'There are no item slots available to transfer this item.', u'Response': 0, u'MessageData': {}}
    
    return response
    

def equip_item(auth_token, itemId, character_id, membership_type):
    print(print_linenumber(), "     FUNCTION :    equip_item       : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              :    equip_item                : itemId                   : " + str(itemId))
    print(print_linenumber(), "              :    equip_item                : character_id             : " + str(character_id))
    print(print_linenumber(), "              :    equip_item                : membership_type          : " + str(membership_type))
      
    url = main_domain + "/Platform/Destiny/EquipItem/"
    data='{"itemId":' + str(itemId) + ',"characterId":"' + str(character_id) + '","membershipType":' + str(membership_type) + '}'
    response = call_api(url, api_key, auth_token, data, method="POST")
    print(print_linenumber(), "                       data : " + str(data))
    print(print_linenumber(), "                   response : " + str(response))
    return response


def equip_items(auth_token, itemIds, character_id, membership_type):
    print(print_linenumber(), "     FUNCTION :    equip_items      : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              :    equip_items               : itemIds                  : " + str(itemIds))
    print(print_linenumber(), "              :    equip_items               : character_id             : " + str(character_id))
    print(print_linenumber(), "              :    equip_items               : membership_type          : " + str(membership_type))
   
    url = main_domain + "/Platform/Destiny/EquipItems/"
    data='{"itemIds":["' + str(itemIds) + '"],"characterId":"' + str(character_id) + '","membershipType":' + str(membership_type) + '}'
    response = call_api(url, api_key, auth_token, data, method="POST")
    print(print_linenumber(), "                       data : " + str(data))
    print(print_linenumber(), "                   response : " + str(response))
    return response
    

def find_dict_key_by_value(input_dict, value):
    print(print_linenumber(), "     FUNCTION :    find_dict_key_by_value    : " + str(datetime.datetime.now()).split('.')[0])
    print(print_linenumber(), "              :    find_dict_key_by_value    : input_dict               : " + str(input_dict))
    print(print_linenumber(), "              :    find_dict_key_by_value    : value                    : " + str(value))
    
    for k, v in input_dict.items():
        if v == value:
            yield k


def print_linenumber():
    #print(print_linenumber(), "     FUNCTION :            get_linenumber    : " + str(datetime.datetime.now()).split('.')[0])
    cf = currentframe()
    return cf.f_back.f_lineno
    

if __name__ == '__main__':
    print(print_linenumber(), "     FUNCTION :  __main__           : " + str(datetime.datetime.now()).split('.')[0])

    
    
    
