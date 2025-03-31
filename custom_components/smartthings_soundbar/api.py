import json

import requests
from homeassistant.const import (STATE_OFF, STATE_ON, STATE_PAUSED, STATE_PLAYING, STATE_UNAVAILABLE)

API_BASEURL = "https://api.smartthings.com/v1"
API_DEVICES = API_BASEURL + "/devices/"
COMMAND_POWER_ON = "{'commands': [{'component': 'main','capability': 'switch','command': 'on'}]}"
COMMAND_POWER_OFF = "{'commands': [{'component': 'main','capability': 'switch','command': 'off'}]}"
COMMAND_REFRESH = "{'commands':[{'component': 'main','capability': 'refresh','command': 'refresh'}]}"
COMMAND_PAUSE = "{'commands':[{'component': 'main','capability': 'mediaPlayback','command': 'pause'}]}"
COMMAND_MUTE = "{'commands':[{'component': 'main','capability': 'audioMute','command': 'mute'}]}"
COMMAND_UNMUTE = "{'commands':[{'component': 'main','capability': 'audioMute','command': 'unmute'}]}"
COMMAND_PLAY = "{'commands':[{'component': 'main','capability': 'mediaPlayback','command': 'play'}]}"
COMMAND_STOP = "{'commands':[{'component': 'main','capability': 'mediaPlayback','command': 'stop'}]}"
COMMAND_REWIND = "{'commands':[{'component': 'main','capability': 'mediaPlayback','command': 'rewind'}]}"
COMMAND_FAST_FORWARD = "{'commands':[{'component': 'main','capability': 'mediaPlayback','command': 'fastForward'}]}"

CONTROLLABLE_SOURCES = ["bluetooth", "wifi"]


class SoundbarApi:

    @staticmethod
    def device_update(entity):
        API_KEY = entity._api_key
        REQUEST_HEADERS = {"Authorization": "Bearer " + API_KEY}
        DEVICE_ID = entity._device_id
        API_DEVICE = API_DEVICES + DEVICE_ID
        API_DEVICE_STATUS = API_DEVICE + "/states"
        API_COMMAND = API_DEVICE + "/commands"
        cmdurl = requests.post(API_COMMAND, data=COMMAND_REFRESH, headers=REQUEST_HEADERS)
        resp = requests.get(API_DEVICE_STATUS, headers=REQUEST_HEADERS)
        data = resp.json()

        switch_state = SoundbarApi.extractor(data, "main.switch.value")
        if switch_state is None:
            entity._state = STATE_UNAVAILABLE
            return
        playback_state = SoundbarApi.extractor(data, "main.playbackStatus.value")
        device_source = SoundbarApi.extractor(data, "main.inputSource.value")
        device_all_sources = json.loads(SoundbarApi.extractor(data, "main.supportedInputSources.value"))
        device_muted = SoundbarApi.extractor(data, "main.mute.value") != "unmuted"
        device_volume = SoundbarApi.extractor(data, "main.volume.value")
        device_volume = min(int(device_volume) / entity._max_volume, 1)
        device_sound_from = SoundbarApi.extractor(data, "main.detailName.value")

        if switch_state == "on":
            if device_source.lower() in CONTROLLABLE_SOURCES:
                if playback_state == "playing":
                    entity._state = STATE_PLAYING
                elif playback_state == "paused":
                    entity._state = STATE_PAUSED
                else:
                    entity._state = STATE_ON
            else:
                entity._state = STATE_ON
        else:
            entity._state = STATE_OFF
        entity._volume = device_volume
        entity._source_list = device_all_sources if type(device_all_sources) is list else device_all_sources["value"]
        entity._muted = device_muted
        entity._source = device_source
        entity._sound_from = device_sound_from if device_sound_from is not None else entity._sound_from
        if entity._state in [STATE_PLAYING, STATE_PAUSED] and 'trackDescription' in data['main']:
            entity._media_title = SoundbarApi.extractor(data, "main.trackDescription.value")
        else:
            entity._media_title = None

    @staticmethod
    def send_command(entity, argument, cmdtype):
        API_KEY = entity._api_key
        REQUEST_HEADERS = {"Authorization": "Bearer " + API_KEY}
        DEVICE_ID = entity._device_id
        API_DEVICES = API_BASEURL + "/devices/"
        API_DEVICE = API_DEVICES + DEVICE_ID
        API_COMMAND = API_DEVICE + "/commands"

        if cmdtype == "setvolume":  # sets volume
            API_COMMAND_DATA = "{'commands':[{'component': 'main','capability': 'audioVolume','command': 'setVolume','arguments': "
            volume = int(argument * entity._max_volume)
            API_COMMAND_ARG = "[{}]}}]}}".format(volume)
            API_FULL = API_COMMAND_DATA + API_COMMAND_ARG
            cmdurl = requests.post(API_COMMAND, data=API_FULL, headers=REQUEST_HEADERS)
        elif cmdtype == "stepvolume":  # steps volume up or down
            if argument == "up":
                API_COMMAND_DATA = "{'commands':[{'component': 'main','capability': 'audioVolume','command': 'volumeUp'}]}"
                cmdurl = requests.post(API_COMMAND, data=API_COMMAND_DATA, headers=REQUEST_HEADERS)
            else:
                API_COMMAND_DATA = "{'commands':[{'component': 'main','capability': 'audioVolume','command': 'volumeDown'}]}"
                cmdurl = requests.post(API_COMMAND, data=API_COMMAND_DATA, headers=REQUEST_HEADERS)
        elif cmdtype == "audiomute":  # mutes audio
            if entity._muted == False:
                cmdurl = requests.post(API_COMMAND, data=COMMAND_MUTE, headers=REQUEST_HEADERS)
            else:
                cmdurl = requests.post(API_COMMAND, data=COMMAND_UNMUTE, headers=REQUEST_HEADERS)
        elif cmdtype == "switch_off":  # turns off
            cmdurl = requests.post(API_COMMAND, data=COMMAND_POWER_OFF, headers=REQUEST_HEADERS)
        elif cmdtype == "switch_on":  # turns on
            cmdurl = requests.post(API_COMMAND, data=COMMAND_POWER_ON, headers=REQUEST_HEADERS)
        elif cmdtype == "play":  # play
            cmdurl = requests.post(API_COMMAND, data=COMMAND_PLAY, headers=REQUEST_HEADERS)
        elif cmdtype == "pause":  # pause
            cmdurl = requests.post(API_COMMAND, data=COMMAND_PAUSE, headers=REQUEST_HEADERS)
        elif cmdtype == "selectsource":  # changes source
            API_COMMAND_DATA = "{'commands':[{'component': 'main','capability': 'mediaInputSource','command': 'setInputSource', 'arguments': "
            API_COMMAND_ARG = "['{}']}}]}}".format(argument)
            API_FULL = API_COMMAND_DATA + API_COMMAND_ARG
            cmdurl = requests.post(API_COMMAND, data=API_FULL, headers=REQUEST_HEADERS)
        elif cmdtype == "selectsoundmode":
            API_COMMAND_DATA = f"""{{
                   "commands":[
                      {{
                         "component":"main",
                         "capability":"execute",
                         "command":"execute",
                         "arguments":[
                            "/sec/networkaudio/soundmode",
                            {{
                               "x.com.samsung.networkaudio.soundmode":"{argument}"
                            }}
                         ]
                      }}
                   ]
                }}"""
            cmdurl = requests.post(API_COMMAND, data=API_COMMAND_DATA, headers=REQUEST_HEADERS)
        entity.schedule_update_ha_state()

    @staticmethod
    def extractor(json, path):
        def extractor_arr(json_obj, path_array):
            if path_array[0] not in json_obj:
                return None
            if len(path_array) > 1:
                return extractor_arr(json_obj[path_array[0]], path_array[1:])
            return json_obj[path_array[0]]
        try:
            return extractor_arr(json, path.split("."))
        except:
            return None
