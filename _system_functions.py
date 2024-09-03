import os
from datetime import datetime

from _send_email import _send_email

'''
System functions are, as implied, basic functions that system uses regularly.
As of 1/8/2024, 2/8 of the functions used by system can be found here:
 - "_save_note": saves a note as .txt. Requires the body and the title.
 - "_load_file": loads a file (using open(..., 'r').read()) and feeds this into Jay.
'''

def _open_and_run_files(_filename):
  '''
  This function opens and runs files, including .mp3 files, .pdfs and webpages.
  The file is opened in the default program (.mp3 is opened in media player, .pdf is opened in the web browser, etc).
  Argument "new = 2" opens the file in a new tab where a previous tab already exists, instead of closing the previous tab and opening a new one.
  The file will remain open after the code has finished running.
  
  As of 9/4/2024, this code is not integrated into Jay's functionality.
  
  Args:
   - _filename (STR): The name of the file to be opened.    
  '''
  #try:
    #import os
    #if os.path.exists(_filename):
  import webbrowser
  webbrowser.open(_filename, new = 2)
  return True
  #  return False
  #except:
  #  return False

def _load_file(_filename):
  '''
  Loads a file, and feeds the file into an LLM, without any processing.
  
  Args:
   - _filename: The name of file to be loaded.
  
  Returns:
   - _txt (STR): Either the loaded file, as a string, or 'NO VALID FILE LOCATED.'
  '''
  try:
    _txt = open(_filename, 'r').read()
    return _txt
  except:
    return 'NO VALID FILE LOCATED.'

def _load_music_file(_keyword = ''):
  _music_file = '..\\Music\\Music_File.csv'
  f = open(_music_file, 'r')
  _name_url = f.readlines()
  f.close()
  
  _name_to_url_dict = {}
  for _ in _name_url[2:-1]:
    _name, _url = _.split('","')
    _name = _name[1:]
    _url = _url
    
    _name_to_url_dict[_name] = _url
  _names = list(_name_to_url_dict.keys())
  if _keyword == '':
    import random
    random.shuffle(_names)
    _chosen_url = _name_to_url_dict[_names[0]]
    if 'youtube' in _chosen_url:
      _open_and_run_files(_chosen_url)
    else:
      os.startfile(os.path.join('..\\Music\\', _chosen_url))
    return 'to-Jay: ["Music playing now."]'
    
  else:
    _keyword = _keyword.lower().split()
    _keyword_to_score = {}
    for _nm in _names:
      _keyword_to_score[_nm] = 0
      for _wrd in _keyword:
        if _wrd in _nm.lower():
          _keyword_to_score[_nm] += 1
      _keyword_to_score[_nm] /= len(_keyword)
    
    _keyword_to_score = dict(sorted(_keyword_to_score.items(), key = lambda item: item[1], reverse = True))
    while True:
      try:
        _selectable_music = 5
        _keys = list(_keyword_to_score.keys())[:_selectable_music]
        _values = list(_keyword_to_score.values())[:_selectable_music]
        if len(_keys) == 0:
          return 'to-Jay: ["The user did not select music"]'
        for _index in range(len(_keys)):
          print(f'({_index + 1}) {_keys[_index]}: {_values[_index]}'.replace('\n', ''))
          del _keyword_to_score[_keys[_index]]
        _chosen_index = input(f'Music Input: Please Pick a Number Between 1 and {_selectable_music} (N if Next Music Choices): ')
        if 'n' not in _chosen_index.lower():
          _chosen_index = int(_chosen_index)
          assert _chosen_index in list(range(_selectable_music))
          _chosen_name = _keys[_chosen_index - 1]
          _chosen_url = _name_to_url_dict[_chosen_name]
          if 'youtube' in _chosen_url:
            _open_and_run_files(_chosen_url)
          else:
            os.startfile(os.path.join('..\\Music\\', _chosen_url))
          return 'to-Jay: ["Music playing now."]'
      except:
        return 'to-Jay: ["The user did not select music"]'

class NotePad():
  def __init__(self, _folder_name):
    # _folder_name is specified in the main file. It is not ever to be changed.
    self._folder_name = _folder_name
    
  def _save_note(self, title, body, _format = '.txt'):
    '''
    Notes are saved here. The note is saved as a .txt file, in a pre-determined folder.
    Jay is specifically told, in the prompting, to save the exact body and not to add unnecessary details.
    Jay can be explicitly told, in conversation, to ignore that instruction.
    
    Args:
     - title (STR): The title of the .txt file to be saved under.
     - body (STR): What is to be saved in the .txt file.
    
    Returns:
     - check (BOOL): Whether the function was successful. Will always be True.
    '''
    # Step (1): The current time is extracted. This is used in the filename, alongside title
    # This is done so that, if a previous note has an identical title, it will not be deleted
    import datetime
    now = datetime.datetime.now()
    current_time = '{}_{}_{}_{}_{}_{}'.format(now.year, now.month, now.day, now.hour, now.minute, now.second)
    
    # Step (2): Given the folder name, two aspects of the file name, and the body, the .txt file is saved
    title = title.replace('.txt', '')
    f = open('{}\\{}-{}.{}'.format(
            self._folder_name, 
            current_time,
            title.replace(' ', '_'),
            _format.replace('.', '')), 
        'w')
    f.write(body)
    f.close()
    return 'Note saved.'

class Time():
  def __init__(
      self,
      minute,
      hour,
      day,
      month,
      year):
    self.minute = int(minute)
    self.hour = int(hour)
    self.day = int(day)
    self.month = int(month)
    self.year = int(year)
      
  def _index(self):
    return [self.year, self.month, self.day, self.hour, self.minute]

class Todo_List():
  def __init__(
      self,
      _filename = 'Todo\\Todo_List.txt'):
    self._filename = _filename
  
  def _add_element(
      self,
      _element):
    _now = datetime.now()
    if _now.hour > 11:
      if _now.minute < 10:
        _time = f'({_now.hour}:0{_now.minute}pm {_now.day}/{_now.month}/{_now.year})'
      else:
        _time = f'({_now.hour}:{_now.minute}pm {_now.day}/{_now.month}/{_now.year})'
    
    else:
      if _now.minute < 10:
        _time = f'({_now.hour}:0{_now.minute}am {_now.day}/{_now.month}/{_now.year})'
      else:
        _time = f'({_now.hour}:{_now.minute}am {_now.day}/{_now.month}/{_now.year})'
    
    with open(self._filename, 'a') as f:
      f.write(f'\n* {_element} {_time}')
  
  def _delete_element(
      self,
      _element):
    _list = self._read_list().split('\n')
    _todo_len = len(_list)
    _list = [_ for _ in _list if _element not in _]
    _list = '\n'.join(_list)
    f = open(self._filename, 'w')
    f.write(_list)
    f.close()
    if _todo_len > len(_list):
      return True
    else:
      return False
  
  def _read_list(self):
    _list = open(self._filename, 'r').read()
    return _list
  
  def _read_elements(
      self,
      _n):
    _list = self._read_list()
    _small_list = '\n'.join(_list.split('\n')[:_n])
    return _small_list