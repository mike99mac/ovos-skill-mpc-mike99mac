#
#            DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
#   TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION
#
#  0. You just DO WHAT THE FUCK YOU WANT TO.
#
class Music_info:
  match_type = ""                  # album, artist or song
  mesg_file = ""                   # if mycroft has to speak first
  mesg_info = {}                   # values to plug in
  track_files = []                 # list of filess to play
  def __init__(self, match_type, mesg_file, mesg_info, track_files):
    self.match_type = match_type
    self.mesg_file = mesg_file
    self.mesg_info = mesg_info
    self.track_files = track_files
