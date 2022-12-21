#!/usr/bin/python3
#
#            DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
#   TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION
#
#  0. You just DO WHAT THE FUCK YOU WANT TO.
#
import hashlib
from mycroft import intent_file_handler
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from mycroft.skills.audioservice import AudioService
from mycroft.api import DeviceApi
from .mpc_croft import MpcCroft
# from mpd import MPDClient 
from .music_info import Music_info
import subprocess

# mpcc = MPDClient()  
# mpcc.timeout = 10                # network timeout in seconds (floats allowed), default: None
# mpcc.idletimeout = None          # timeout for fetching the result of the idle command is handled seperately, default: None

class Mpc(CommonPlaySkill):

  def __init__(self):
    super().__init__()
    self._setup = False
    self.audio_service = None
    self.mpc_croft = MpcCroft("/home/pi/usbdrive/music/")
    self.device_id = hashlib.md5(('Mpc'+DeviceApi().identity.uuid).encode()).hexdigest()

  def initialize(self):
    music_info = Music_info("", "", {}, []) # music to play 
    self._audio_session_id: Optional[str] = None
    self._stream_session_id: Optional[str] = None
    self._is_playing = False
    self.register_handlers()

  def initialize(self):
    pass

  def register_handlers(self):
    """Register handlers for events to or from the GUI."""
    self.bus.on("mycroft.audio.service.playing", self.handle_media_playing)
    self.bus.on("mycroft.audio.service.stopped", self.handle_media_stopped)
    self.bus.on("play:pause", self.handle_pause)
    self.bus.on("play:resume", self.handle_resume)
    self.add_event("gui.namespace.displayed", self.handle_gui_namespace_displayed)
    self.bus.on("mycroft.audio.service.position", self.handle_media_position)
    self.bus.on("mycroft.audio.queue_end", self.handle_media_finished)

  def speak_playing(self, media):
    data = dict()
    data['media'] = media
    self.speak_dialog('mpc', data)

  def handle_media_stopped(self, message):
    mycroft_session_id = message.data.get("mycroft_session_id")
    if mycroft_session_id == self._stream_session_id:
      self._is_playing = False

  @intent_file_handler('playlist.intent')
  def handle_playlist(self, message):
    utterance = str(message.data["utterance"])
    self.log.log(20, "handle_playlist(): utterance = "+utterance) 

    # return value is file name of .dialog file to speak and values to be plugged in
    mesg_info = []
    mesg_file, mesg_info = self.mpc_croft.manipulate_playlists(utterance)
    if [ mesg_file != None ]:                # there is a reply to speak
      self.speak_dialog(mesg_file, data=mesg_info, wait=True)

  def stop(self):
    self.log.log(20, "stop() - clearing queue") 
    return
    # cmd = ["/usr/bin/mpc", "clear"]
    # self.log.log(20, "stop(): running cmd = "+str(cmd))
    subprocess.Popen("/usr/bin/mpc clear", shell=True) 

  def CPS_start(self, phrase, data):
    """ 
    Start playback - called by the playback control skill to start playback if the
    skill is selected (has the best match level)
    Clear the queue, add all tracks passed in then play them
    """
    # self.speak_dialog(self.music_info.mesg_file, self.music_info.mesg_info, wait=True) # have Mycroft speak the message  
    self.log.log(20, "CPS_start(): running: /usr/bin/mpc clear")
    subprocess.Popen("/usr/bin/mpc clear", shell=True) 
    for next_file in self.music_info.track_files: # add track(s) to the queue
      self.log.log(20, 'CPS_start(): calling: /usr/bin/mpc add '+next_file)
      subprocess.Popen("/usr/bin/mpc add "+next_file, shell=True)
    self.log.log(20, "CPS_start(): calling: /usr/bin/mpc play")
    subprocess.Popen("/usr/bin/mpc play", shell=True)   
  
  def CPS_match_query_phrase(self, phrase):
    """ Return whether the skill can play input phrase or not - invoked by the PlayBackControlSkill.
        Returns: tuple (matched phrase(str),
                        match level(CPSMatchLevel),
                        optional data(dict))
                 or None if no match was found.
        """    
    self.log.log(20, "CPS_match_query_phrase() searching for phrase = "+phrase)
    self.music_info = self.mpc_croft.parse_common_phrase(phrase)
    self.log.log(20, "CPS_match_query_phrase() match_type = "+str(self.music_info.match_type))
    self.log.log(20, "CPS_match_query_phrase() mesg_file = "+self.music_info.mesg_file)
    self.log.log(20, "CPS_match_query_phrase() mesg_info = "+str(self.music_info.mesg_info))
    self.log.log(20, "CPS_match_query_phrase() track_files = "+str(self.music_info.track_files))
    self.log.log(20, "CPS_match_query_phrase() calling speak.dialog")  
    # self.speak_dialog(mesg_file, mesg_info, wait=True) # have Mycroft speak the message
    # self.speak_dialog(self.music_info.mesg_file, self.music_info.mesg_info) # have Mycroft speak the message  

    if self.music_info.track_files:        # music was found
      # track_files = []
      track_files = self.music_info.track_files
      num_tracks = len(track_files)
      self.log.log(20, "CPS_match_query_phrase() first "+str(num_tracks)+" file names returned")
      tracks_logged = 0
      for track in self.music_info.track_files: # log first three tracks on the queue
        self.log.log(20, "CPS_match_query_phrase() track = "+str(track))
        tracks_logged = tracks_logged + 1
        if tracks_logged >= 3:
          break
      return phrase, CPSMatchLevel.EXACT, {}
    else:                                  # no music found
      return None

def create_skill():
    return Mpc()
