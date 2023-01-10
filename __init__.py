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
from .mpc_client import MpcClient
from .music_info import Music_info
import subprocess

class Mpc(CommonPlaySkill):

  def __init__(self):
    super().__init__(name="LocalMusicSkill")

  def initialize(self):
    music_info = Music_info("", "", {}, []) # music to play 
    self._audio_session_id: Optional[str] = None
    self._stream_session_id: Optional[str] = None
    self._is_playing = False
    self.audio_service = None
    self.mpc_client = MpcClient("/media/") # search for music under /media
    self.device_id = hashlib.md5(('Mpc'+DeviceApi().identity.uuid).encode()).hexdigest()

  def speak_playing(self, media):
    data = dict()
    data['media'] = media
    self.speak_dialog('mpc', data)

  @intent_file_handler('playlist.intent')
  def handle_playlists(self, message):
    """ 
    Process utterances related to maintaing playlists 
    """
    utterance = str(message.data["utterance"])
    self.log.log(20, "handle_playlists(): utterance = "+utterance) 
    mesg_info = []
    mesg_file, mesg_info = self.mpc_client.manipulate_playlists(utterance)
    if [ mesg_file != None ]:              # there is a reply to speak
      self.speak_dialog(mesg_file, data=mesg_info, wait=True)

  @intent_file_handler('radio.intent')
  def handle_radio(self, message):
    """ 
    Process utterances related to playing internet radio 
    A Music_info object is created with radio URLs.  Speak the message if one is passed back then start the music
    """
    utterance = str(message.data["utterance"])
    self.log.log(20, "handle_radio(): utterance = "+utterance) 
    if self.mpc_client.mpc_cmd("clear") != True:      # mpc failed
      self.log.error(20, "get_station() self.mpc_cmd(clear) failed")
      mesg_info = {"return_code": self.mpc_rc}
      return "bad_mpc_rc", mesg_info   

    self.music_info = self.mpc_client.parse_radio(utterance)
    if [ self.music_info.mesg_file != None ]:         # there is a reply to speak
      self.speak_dialog(self.music_info.mesg_file, self.music_info.mesg_info, wait=True) # speak the message 
    if self.mpc_client.mpc_cmd("play") != True: # error playing music
      self.log.log(20, "handle_radio(): self.mpc_client.mpc_cmd(play) failed")  

  def stop(self):
    """ 
    Stop playback - called by the playback control skill 
    """
    self.log.log(20, "stop() - stopping music")
    if self.mpc_client.mpc_cmd("clear") != True:
      self.log.error(20, "stop() - self.mpc_client.mpc_cmd(clear) failed")

  def CPS_start(self, phrase, data):
    """ 
    Start playback - called by the playback control skill 
    Clear the queue, add all tracks passed in then play them
    """
    self.log.log(20, "CPS_start() - starting music")
    self.mpc_client.start_music(self.music_info)

  def CPS_match_query_phrase(self, phrase):
    """ Return whether the skill can play input phrase or not - invoked by the PlayBackControlSkill.
        parse_common_phrase() in the mpc client populates a music_info object with either music
        file names or radio station URLs.  It also passes back message info which is spoken by
        Mycroft before playing the music
        Returns: tuple (matched phrase(str), match level(CPSMatchLevel), but no optional data(dict))
                 or None if no match was found.
        """    
    # parse the phrase and find the music
    self.log.log(20, "CPS_match_query_phrase() searching for phrase = "+phrase)
    self.music_info = self.mpc_client.parse_common_phrase(phrase)  
    self.log.log(20, "CPS_match_query_phrase() match_type = "+str(self.music_info.match_type))
    self.log.log(20, "CPS_match_query_phrase() mesg_file = "+self.music_info.mesg_file)
    self.log.log(20, "CPS_match_query_phrase() mesg_info = "+str(self.music_info.mesg_info))
    self.log.log(20, "CPS_match_query_phrase() track_files = "+str(self.music_info.track_files))

    # speak the message
    self.CPS_extend_timeout()              # don't let speaking message cause a timeout
    self.log.log(20, "CPS_match_query_phrase() calling speak.dialog")  
    self.speak_dialog(self.music_info.mesg_file, self.music_info.mesg_info, wait=True) # speak the message  

    if len(self.music_info.track_files) > 0: # music was found
      if self.mpc_client.mpc_cmd("play") != True:
        self.log.error(20, "CPS_match_query_phrase() - self.mpc_client.mpc_cmd(play) failed")
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
