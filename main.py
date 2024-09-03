import os
import sys
import time
import datetime
import logging
from termcolor import colored
os.system('color')
from llama_cpp import Llama

from _agent_calculator import _agent_calculator_func
from _google_calendar import Calendar
from _news_download import _get_the_news as _get_the_news_fn
from _query import _Query
from _send_email import _timer_email
from _send_email import _send_email as _send_email_fn
from _system_functions import NotePad, _load_file, _open_and_run_files, _load_music_file, Todo_List
from _together_api import _API
from _util import _prompt_llama_cpp

logger = logging.getLogger()
logger.disabled = True

'''
The main class that Jay is built on (explicitly called Jay).
Here, all conversation is performed with an LLM, and all functions are kept and used here.
The functions do not need human supervision, and can be performed by the LLM on their own.
'''

class Jay():
  
  ########################################
  # PART (1) THE INITIALIZATION FUNCTION #
  ########################################

  def __init__(
      self,
      _credentials_path: str,
      _email_address: str,
      _email_pwd: str,
      _model_path: str,
      _notepad_folder_name: str,
      _together_api_key: str,
      _use_llm: str):
    '''
    Jay is initialized here. The main LLM is loaded, the notepad, calendar and the Query class is initialized.
    
    Args:
     - _credentials_path: The credentials path for Google Calendar. More information in found in _google_calendar.py
     - _email_address: The user's Gmail address, for the Google Calendar.
     - _email_pwd: The password for Gmail API.
     - _model_path: The path to the LLM weights. 
     - _notepad_folder_name: The folder that notes will be saved in.
     - _together_api_key: The API key for together.ai. Set to '' if not using together.ai
     - _use_llm: The base LLM model. Either 'llama-cpp-python' for local .gguf model, or 'together.ai' for online LLMs.
    '''
    assert _use_llm in ['llama-cpp-python', 'together.ai']
    self._model_path = _model_path
    self._util_print_color("|- Base Model: " + self._model_path.split('\\')[-1], to_print = 2.0)
    self._util_print_color("|- Calculator Model: " + self._model_path.split('\\')[-1], to_print = 1.0)
    self._util_print_color('|- LaR Model: ' + self._model_path.split('\\')[-1], to_print = 1.0)
    
    # Step (1): The logged conversations are prepared as an empty list, and the args are saved.
    self._use_llm = _use_llm
    self._prompt_txt_file = f"Prompts\\prompt_{int(time.time())}.txt"
    self._notepad_folder_name = _notepad_folder_name
    self._together_api_key = _together_api_key
    
    # Step (2): The model is loaded, the model type and utils are logged.
    self._load_llm_model(
        _use_llm = self._use_llm)
    self._util_print_color('self._load_llm_model()', to_print = 0.0)
    if self._use_llm == 'llama-cpp-python':
      self._util_print_color('|- _use_llama_cpp() (.gguf)', to_print = 0.0)
    elif self._use_llm == 'together.ai':
      self._util_print_color('|- _together_api (Llama 3)', to_print = 0.0)
    for key in self._model_utils:
      self._util_print_color('|- _MODEL_UTIL - {}'.format(key), to_print = 0.0)
    
    # Step (3): Notepad is initialized, so that notes can be saved. There is no data loaded, just functionality.
    self._notepad = NotePad(_folder_name = self._notepad_folder_name)
    self._util_print_color('\nself._load_notepad()', to_print = 0.0)
    self._util_print_color('|- {}'.format(self._notepad_folder_name), to_print = 0.0)
    
    # Step(4): The calendar is initialized and loaded.
    self._calendar = Calendar(_email_address = _email_address, _credentials_path = _credentials_path)
    self._email_address = _email_address
    self._email_pwd = _email_pwd
    self._util_print_color('self._load_calendar()', to_print = 0.0)
    
    # Step (5): The query model is loaded.
    # Query does involve loading an LLM, but only as a last resort. The LLM is loaded only in the most extreme circumstances, and immediately deleted afterwards.
    # As of 3/6/2024, the local model is a .gguf, which is very quick to load.
    self._query_model = _Query(_print_function = self._util_print_color, _generation_model = self._use_llm, _generation_model_path = self._model_path, _together_api_key = self._together_api_key)
    self._util_print_color('self._load_query_model()', to_print = 0.0)
    
    # Step (6): The Todo list is loaded.
    # The Todo list is found at "Todo\\Todo_List.txt"
    self._todo = Todo_List()
    self._util_print_color('self._load_todo()', to_print = 0.0)
    
  ##############################
  # PART (2) THE CHAT FUNCTION #
  ##############################
  
  def chat(self):
    '''
    The chat function. After the class/model is initialized, the entire functionality is performed inside "chat()".
    '''
    # Step (1): The model is prompted and the interactive conversation begins.
    self._util_print_color('|- self.chat()\n', to_print = 1.0)
    
    # Step (2): The conversation begins.
    # For as long as the user's input is not either 'f' or 'false', then the conversation continues.
    self._util_print_color('<|eot_id|>\n<|start_header_id|>user<|end_header_id|>', to_print = 0.0)
    
    _next_comment = 'Input ' + colored('("exit" to stop)', 'red') + ': '
    _next_comment = input(_next_comment)
    while _next_comment.lower() not in ['false', 'f', 'exit', 'stop', 'cls']:
      # Step (3): The user's input is sent to the LLM, and the output is received.
      self._util_print_dash()
      self._util_print_color('====================', to_print = 1.0)
      self._util_print_color('<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>', to_print = 0.0)
      
      _ai_response, _send_to_system = self._send_and_respond(_input = _next_comment)
      
      # Step (4): If sent to _model_to_system_communication(), then system function is used.
      # This is where any functions that must be used are sent too.
      if _send_to_system and 'to-system:' in _ai_response:
        _ai_response = self._model_to_system_communication(_ai_response)
      
      # Step (5): The model output is printed, and the next user input is recieved.
      # If there is any 'to-system' functionality, it is printed inside "_model_to_system_communication".
      self._print_for_user('Output: {}'.format(_ai_response))
      self._util_print_dash()
      self._util_print_color('<|eot_id|>\n<|start_header_id|>user<|end_header_id|>', to_print = 0.0)
      _next_comment = input('Input: ')
      
    # Step (6): The conversation between the LLM and the user ends, and the calendar is saved.
    # However, the LLM still has further post-conversation functionality to do.
    self._print_for_user('Input: That will be all, thank you.')
    _ai_response, _ = self._send_and_respond(_input = 'That will be all, thank you.')
    self._util_print_dash()
    
    self._print_for_user('Output: {}'.format(_ai_response))
    
  #################################
  # PART (3) LOADING THE CHAT LLM #
  #################################
  
  def _load_llm_model(
      self,
      _use_llm: str = 'llama-cpp-python'):
    '''
    Loads the LLM for the main conversational model.
    Each potential model is loaded in a seperate sub-function.
    
    Args:
     - _use_llm (STR): The model that is to be used.
    '''
    self._model_utils = {}
    assert _use_llm in ['llama-cpp-python', 'together.ai']
    if _use_llm == 'llama-cpp-python':
      self._util_load_llama_gguf()
    elif _use_llm == 'together.ai':
      self._util_load_together()
  
  def _util_load_llama_gguf(self):
    self._n_ctx_train = 32768
    self._conversation = self._util_prompt_model_llama3()
    _stt = time.time()
    self._model = Llama(model_path = self._model_path, n_ctx = self._n_ctx_train, n_gpu_layers = 0, verbose = False)
    self._util_print_color(f"Model Loaded: {time.time() - _stt} secs", to_print = 0.0)
    
  def _util_load_together(self):
    self._model = _API(_api_key = self._together_api_key, _model_name = self._model_path)
    self._model_utils[self._model_path] = '_model_name'
    self._conversation = self._util_prompt_model_llama3()
  
  ##################################################################
  # PART (4) SENDING TEXT TO THE MODEL AND GENERATING THE RESPONSE #
  ##################################################################
  
  def _send_and_respond(
      self,
      _input: str) -> str:
    '''
    All user-model communication happens here.
    
    Args:
     - _input (STR): The input sent to the model.
    
    Returns:
     - _output (STR): The model output.
     - _send_to_system (BOOL): Whether system is needed.
    '''
    # Step (0): The function that generates response is prepared at the top of the main function.
    def _generate_response(
        _use_llm,
        _prompt_input,
        _stop_tokens,
        _stream,
        _max_tokens = -1):
      if _use_llm in ['llama-cpp-python']:
        # llama-cpp generates the results from a .gguf file.
        def _print_function(_str):
          return colored(_str, 'blue')
        _assistant_output, _pt, _ct, _tt = _prompt_llama_cpp(
            _print_function = _print_function,
            _llm = self._model,
            _prompt_input = _prompt_input,
            _stop_tokens = _stop_tokens,
            _max_tokens = _max_tokens,
            _stream = _stream)
      elif _use_llm in ['together.ai']:
        # together.ai is used.
        _assistant_output, _pt, _ct, _tt, _ = self._model(_prompt_input, _stop = _stop_tokens, _max_tokens = _max_tokens)
      return _assistant_output, _pt, _ct, _tt
    
    # Step (1): The previous prompt is added to _conversation.
    _add_nc_for_system = False
    
    self._conversation += _input 
    self._conversation += '<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>\n\n\t'
    
    # Step (3): The assistant's prompt is generated.
    _stt = time.time()
    _assistant_output, _pt, _ct, _tt = _generate_response(
        _use_llm = self._use_llm,
        _prompt_input = self._conversation,
        _stop_tokens = ['<|eot_id|>\n', 'NC(to-Jay:'],
        _stream = True)
    # The model is prompted to have an internal monologue before it responds to the user.
    # The internal monologue happens inside the tags <jay_internal> and </jay_internal>.
    # This allows the model to get it's thoughts clear before it answers the user.
    # This is still extremely new, and does not always work.
    # When the response is printed, the tags are printed in red, so that the user can identify when there is an issue with printing the tags.
    # Sometimes, the model will forget to use the end of internal monologue tag and immediately respond to the user. This does not break the code, but it is technically improper prompting behaviour.
    
    if _assistant_output[-6:] == 'END_FU':
      _assistant_output += 'NC'
      _add_nc_for_system = True
    _assistant_output = _assistant_output.replace('To-system:', 'to-system:')
    if _assistant_output.replace(' ', '').replace('\n', '')[-10:] == '</EXAMPLE>':
      _assistant_output = _assistant_output[:-10]
    if _assistant_output.replace(' ', '').replace('\n', '')[-8:] == '</START>':
      _assistant_output = _assistant_output[:-8]
    
    # Step (4): The model decides whether it's prompt will call system.
    # If:
    #   - If there is no "to-system:" in the prompt, then system is not being called.
    #   - All functions that system can call begin with "_" (e.g. _add_calendar_event, _calculator, etc), so if the next character after "to-system:" is not "_", then no system function is being called. All functions also require "(" after the function name, and ") END_FUNC" after the function arguments.
    #   - If the first characters from prompt (excluding whitespace) is "to-system:_", then we assume the model is calling a system function.
    #   - If the characters "to-system:_" is present but not at the beginning of the text, the model is asked to clarify whether a system function should be called (TRUE) or not (FALSE).
    #   - If the prompt ended with "END_FUNC", then there is a to system call.
    # If a system function is being called, the end of the function (END_FUNC) is used to cut off the end of the prompt. The system response immediately follows the function being called.
    if 'to-system:' in _assistant_output:
      _system_call = _assistant_output.split('to-system:')[1].replace(' ', '')[0] == '_'
      _potential_system_call = _assistant_output.split('to-system:')[1]
      _potential_system_call_split_words = [_ for _ in _potential_system_call.split(' ') if _ != '']
      if _system_call:
        _system_call = '(' in _potential_system_call_split_words[0]
      if _system_call:
        _system_call = _add_nc_for_system
    else:
      _system_call = False
    
    if _system_call:    
      _assistant_output = _assistant_output.split('END_FUNC')[0]
      if _assistant_output[-1] == ' ':
        _assistant_output += 'END_FUNC'
      else:
        _assistant_output += ' END_FUNC'
    
    # Step (5): Prompt generation statistics are presented.
    _time_taken = round(time.time() - _stt, 4)
    self._util_print_color(f"|- {_time_taken} secs, P:{_pt} - Comp:{_ct} - Total:{_tt}", to_print = 2.0)
    self._util_print_color('====================', to_print = 2.0)
    
    # Step (6): The prompt is added to _conversation.
    self._conversation += _assistant_output
    if not _system_call:
      self._conversation += '<|eot_id|>\n<|start_header_id|>user<|end_header_id|>\n\n\t'
    
    # Step (7): _conversation is saved, and the model's output and whether system should be called are returned.
    f = open(self._prompt_txt_file, 'w', encoding = 'utf-8')
    f.write(self._conversation)
    f.close()
    return _assistant_output, _system_call
  
  ########################################################
  # PART (5) MODEL TO SYSTEM COMMUNICATION FUNCTIONALITY #
  ########################################################
  
  def _model_to_system_communication(
      self,
      _ai_response):
    '''
    The model-to-system output is analysed here.
    Only output that contains the str 'to-system:' is sent here.
    '''
    if 'END_FUNC' in _ai_response:
      _ai_response = _ai_response.replace('END_FUNC', '')
    #if '<function = True>' in _ai_response:
    #  _ai_response = _ai_response.replace('<function = True>', '')
    if _ai_response[:10] != 'to-system:':
      # Step (1): If the str does not begin with 'to-system:', then the part of the output before 'to-system:' is printed as normal conversation, and everything that follows is sent through system communication.
      _ai_response = _ai_response.split('to-system:')
      _system_comm = _ai_response[1:]
      _user_output = _ai_response[0]
      
      if len(_user_output.replace(' ', '').replace('\n', '')) != 0:
        while _user_output[0] == '\n':
          _user_output = _user_output[1:]
          if len(_user_output) == '':
             break
        if len(_user_output) > 0:
          self._print_for_user('Output: {}'.format(_user_output))
      
      _system_comm = ['to-system:'] + _system_comm
      _system_comm = ''.join(_system_comm)
    else:
      _system_comm = _ai_response
    
    # Step (2): A common error Jay makes is using the function "_get_weather", which does not exist.
    # This information should be gotten by searching the internet.
    # I have put in a quick catch that will change "_get_weather" to "_search_the_internet".
    if '_get_weather(' in _system_comm:
      _system_comm = _system_comm.replace('_get_weather(', '_search_the_internet("weather ')
      _system_comm = _system_comm.replace(')', '")')
    if '_get_weather_forecast(' in _system_comm:
      _system_comm = _system_comm.replace('_get_weather_forecast(', '_search_the_internet("weather ')
      _system_comm = _system_comm.replace(')', '")')
    if '_get_the_weather_forecast(' in _system_comm:
      _system_comm = _system_comm.replace('_get_the_weather_forecast(', '_search_the_internet("weather ')
      _system_comm = _system_comm.replace(')', '")')
    
    self._util_print_color('====================', to_print = 2.0)
    _system_call_str = '|- ' + _system_comm + ' END_FUNC'
    self._util_print_color(_system_call_str.replace('  ', ' '), to_print = 2.0)
    
    # Step (3): The selected function is activated here.
    if '_add_calendar_event' in _system_comm.split('(')[0]:
      _next_comment = self._util_add_calendar_event(_system_comm)
    
    elif '_calculator' in _system_comm.split('(')[0]:
      _next_comment = self._util_calculator(_system_comm)
      
    elif '_get_the_news' in _system_comm.split('(')[0]:
      _next_comment = self._util_get_the_news(_system_comm)
    
    elif '_open_file_for_user' in _system_comm.split('(')[0]:
      _next_comment = self._util_open_file_for_user(_system_comm)
    
    elif '_play_music' in _system_comm.split('(')[0]:
      _next_comment = self._util_play_music(_system_comm)
      
    elif '_read_file_for_AI' in _system_comm.split('(')[0]:
      _next_comment = self._util_read_file_for_AI(_system_comm)
      
    elif '_save_note' in _system_comm.split('(')[0]:
      _next_comment = self._util_save_note(_system_comm)
      
    elif '_search_calendar' in _system_comm.split('(')[0]:
      _next_comment = self._util_search_calendar(_system_comm)
        
    elif '_search_the_internet' in _system_comm.split('(')[0]:
      _next_comment = self._util_search_the_internet(_system_comm)
      
    elif '_send_email' in _system_comm.split('(')[0]:
      _next_comment = self._util_send_email(_system_comm)
        
    elif '_set_timer' in _system_comm.split('(')[0]:
      _next_comment = self._util_set_timer(_system_comm)
        
    elif '_time' in _system_comm.split('(')[0]:
      _next_comment = self._util_time(_system_comm)
    
    elif '_todo_list_add' in _system_comm.split('(')[0]:
      _next_comment = self._util_todo_list_add(_system_comm)
    
    elif '_todo_list_delete' in _system_comm.split('(')[0]:
      _next_comment = self._util_todo_list_delete(_system_comm)
    
    elif '_todo_list_read' in _system_comm.split('(')[0]:
      _next_comment = self._util_todo_list_read(_system_comm)
      
    else:
      _next_comment = f'to-Jay: ERROR Returned: "{_system_comm.split("(")[0]}" Is Not a System Function.'
    
    self._util_print_color(f"|- {_next_comment}"[:100], to_print = 2.0)
    _next_comment = f'({_next_comment}). '
    _ai_response, _send_to_system = self._send_and_respond(_input = _next_comment)
    if _send_to_system:
      _ai_response = self._model_to_system_communication(_ai_response)
    return _ai_response
  
  #############################
  # PART (6) SYSTEM FUNCTIONS #
  #############################
  
  def _util_add_calendar_event(
      self,
      _system_comm):
    '''
    Adds an event to the calendar.
    
    _add_calendar_event(EVENT_NAME: str, LENGTH_MINUTES: int, MINUTE: int, HOUR: int, DAY: int = 8, MONTH: int = 6, YEAR: int = 2024)
    '''
    
    def _add_calendar_event(EVENT_NAME: str, LENGTH_MINUTES: int, MINUTE: int, HOUR: int, DAY: int = -1, MONTH: int = -1, YEAR: int = -1):
      if DAY == -1:
        DAY = datetime.date.today().day
      if MONTH == -1:
        MONTH = datetime.date.today().month
      if YEAR == -1:
        YEAR = datetime.date.today().year
      
      _calendar_placement = self._calendar._add_calendar_event(
          _event_name = EVENT_NAME, 
          _minute = MINUTE, 
          _hour = HOUR, 
          _day = DAY, 
          _month = MONTH, 
          _year = YEAR,
          _print_function = self._util_print_color,
          _length_event = LENGTH_MINUTES)
      return f'to-Jay: {[_calendar_placement]}.\n'
      
    try:
      _next_comment = eval(_system_comm.replace('to-system:', ''))
    except Exception as e:
      _next_comment = str(e)
      _next_comment = f"to-Jay: ERROR returned: {[_next_comment]}.\n"
    return _next_comment
  
  def _util_calculator(
      self,
      _system_comm):
    '''
    Answers a math question, by sending the question to an LLM that creates a python code to answer the question.
    Not 100% accurate, feel free to double check.
    
    _calculator(QUESTION: str)
    '''
    def _calculator(MATH: str):
      _answer, _calculator_code = _agent_calculator_func(_math_input = MATH, _print_function = self._util_print_color, _model_file = self._use_llm, _model_path = self._model_path, _together_api_key = self._together_api_key)
      return f"to-Jay: {[_answer]}."
    
    try:
      _next_comment = eval(_system_comm.replace('to-system:', ''))
    except Exception as e:
      _next_comment = str(e)
      _next_comment = f"to-Jay: ERROR returned: {[_next_comment]}."
    return _next_comment
  
  def _util_get_the_news(
      self,
      _system_comm):
    '''
    Gets the news, given the country.
    
    _get_the_news(COUNTRY: str = 'Australia')
    '''
    def _get_the_news(COUNTRY: str = 'Australia'):
      _news_head_lines, _news_descriptions = _get_the_news_fn(COUNTRY, _print_function = self._util_print_color)
      if len(_news_head_lines) != 1:
        self._util_print_color(f"Number of Extracted Headlines: {len(_news_head_lines)}", to_print = 0.0)
      else:
        self._util_print_color(f"Extracted: {_news_head_lines[0]}", to_print = 0.0)
      return f'to-Jay: {_news_head_lines}. If the user has requested the news, please return to the user in a bullet point list.'
    
    try:
      _next_comment = eval(_system_comm.replace('to-system:', ''))
    except Exception as e:
      _next_comment = str(e)
      _next_comment = f"to-Jay: ERROR returned: {[_next_comment]}."
    return _next_comment
    
  def _util_open_file_for_user(
      self,
      _system_comm):
    '''
    Opens file for the user.
    
    _open_file_for_user(NAME: str)
    '''
    def _open_file_for_user(FILE: str):
      try:
        _load_file = _open_and_run_files(FILE)
        return 'to-Jay: ["File has been opened for the user."]'
      except:
        return f"to-Jay: ERROR returned: File {FILE} was not found. Ask the user for further clarification."
    
    try:
      _next_comment = eval(_system_comm.replace('to-system:', ''))
    except Exception as e:
      _next_comment = str(e)
      _next_comment = f"to-Jay: ERROR returned: {[_next_comment]}."
    return _next_comment
    
  def _util_play_music(
      self,
      _system_comm):
    '''
    Plays music from a pre-defined playlist.
    The music files (e.g. youtube videos, .mp3 files) should be found the file "..\\Music\\Music_File.csv".
    
    _play_music()
    '''
    def _play_music(KEYWORDS = ''):
      return _load_music_file(_keyword = KEYWORDS)
    
    try:
      _next_comment = eval(_system_comm.replace('to-system:', ''))
    except Exception as e:
      _next_comment = str(e)
      _next_comment = f"to-Jay: ERROR returned: {[_next_comment]}."
    return _next_comment
    
  def _util_read_file_for_AI(
      self,
      _system_comm):
    '''
    Loads a file and feeds the file into the AI's context. Only works with files that can be read with a "read()" function (e.g. .txt file).
    
    As of 27/9/2024, only "Lyndon_Johnson" is available to read.
    
    _read_file_for_AI(NAME: str)
    '''
    def _read_file_for_AI(FILE: str):
      try:
        _file_to_read = _load_file(FILE)
        self._util_print_color(f"File Loaded: {str(_file_to_read)[:100]}", to_print = 0.0)
        return f'to-Jay: File: {[_file_to_read]}'
      except:
        return f"to-Jay: ERROR returned: File {FILE} was not found. Ask the user for further clarification."
      
    try:
      _next_comment = eval(_system_comm.replace('to-system:', ''))
    except Exception as e:
      _next_comment = str(e)
      _next_comment = f"to-Jay: ERROR returned: {[_next_comment]}."
    return _next_comment
  
  def _util_save_note(
      self,
      _system_comm):
    '''
    Saves a note, given a title and body.
    If the information should be beefed up, ask Jay to expand on notes.
    
    _save_note(TITLE: str, BODY: str, FORMAT: str = '.txt')
    '''
    def _save_note(TITLE: str, BODY: str, FORMAT: str = '.txt'):
      _should_take_notes = input('to-user: Save note (T\F): ').lower()
      if _should_take_notes in ['t', 'y', 'true', 'yes']:
        self._util_print_color('|- NOTE SAVED', to_print = 0.0)
        _note_taken = self._notepad._save_note(
            title = TITLE,
            body = BODY,
            _format = FORMAT)
      else:
        self._util_print_color('NOTE WASN\'T SAVED BY USER\'S REQUEST', 'red', to_print = 2.0)
        _note_taken = 'Note saved.'
      _next_comment = f"to-Jay: {[_note_taken]}"
      return _next_comment
    
    try:
      _next_comment = eval(_system_comm.replace('to-system:', ''))
    except Exception as e:
      _next_comment = str(e)
      _next_comment = f"to-Jay: ERROR returned: {[_next_comment]}."
    return _next_comment
    
  def _util_search_calendar(
      self,
      _system_comm):
    '''
    Searches the calendar.
    It can either search the calendar for an event name, or for a time.
    As of 13/6/2024, this doesn't work.
    
    _search_calendar(EVENT_NAME: str = '', MINUTE: int = -1, HOUR: int = -1, DAY: int = -1, MONTH: int = -1, YEAR: int = -1)
    '''
    def _search_calendar(DAY: int  = -1, MONTH: int = -1, YEAR: int = -1):
      if DAY == -1:
        DAY = datetime.date.today().day
      if MONTH == -1:
        MONTH = datetime.date.today().month
      if YEAR == -1:
        YEAR = datetime.date.today().year
      _calendar_placement = self._calendar._search_calendar_for_day(
          _day = DAY, 
          _month = MONTH, 
          _year = YEAR)
      if len(_calendar_placement) == 0:
        _calendar_placement = 'Calendar is empty for the stated time period'
      return f'to-Jay: {_calendar_placement}.'
    
    try:
      _next_comment = eval(_system_comm.replace('to-system:', ''))
    except Exception as e:
      _next_comment = str(e)
      _next_comment = f"to-Jay: ERROR returned: {[_next_comment]}."
    return _next_comment
    
  def _util_search_the_internet(
      self,
      _system_comm):
    '''
    Searches the internet.
    
    _search_the_internet(QUESTION: str)
    '''
    def _search_the_internet(QUESTION: str, URLs: list = []):
      _answer = self._query_model.call(_query = QUESTION, _urls = URLs)
      return f"to-Jay: {_answer}. Use this information to respond to the user's question. Ensure you only return information that \"_search_the_internet\" has provided you, and state where you are using which reference (e.g. <1> and <2>). DO NOT REPEAT THE QUESTION OR FUNCTION."
    
    _system_comm = _system_comm.replace('_search_the_internet(QUERY', '_search_the_internet(QUESTION')
    if True: #try:
      _next_comment = eval(_system_comm.replace('to-system:', ''))
    else: #except Exception as e:
      _next_comment = str(e)
      _next_comment = f"to-Jay: ERROR returned: {[_next_comment]}."
    return _next_comment
    
  def _util_send_email(
      self,
      _system_comm):
    '''
    Sends an email.
    The contact must be a predefined contact, Jay cannot send an email to an email address without the user's previous approval.
    
    _send_email(CONTACT_NAME: str, SUBJECT: str, BODY: str)
    '''
    def _send_email(CONTACT_NAME: str, SUBJECT: str, BODY: str):
      _possible_contacts = _email_contacts()
      # _email_contacts should return a dict {CONTACT_NAME: EMAIL_ADDRESS}.
      if CONTACT_NAME in _possible_contacts.keys():
        _send_email_fn(_subject = SUBJECT, _body = BODY, _print_function = self._util_print_color, _contact = _possible_contacts[CONTACT_NAME], _sender_email = self._email_address, _sender_email_pwd = self._email_pwd)
        return "to-Jay: ['Email Successfully Sent']. Please return this information to the user."
      return f'to-Jay: ERROR: {CONTACT_NAME} is not in a contact. Ask the user for further clarification.'
    
    try:
      _next_comment = eval(_system_comm.replace('to-system:', ''))
    except Exception as e:
      _next_comment = str(e)
      _next_comment = f"to-Jay: ERROR returned: {[_next_comment]}."
    return _next_comment
  
  def _util_set_timer(
      self,
      _system_comm):
    '''
    Sets a timer.
    As of 13/6/2024, this doesn't work. The function always returns true, but there is no timer function.
    
    _set_timer(MINUTES: int)
    '''
    def _set_timer(MINUTES: int):
      from threading import Thread
      from time import sleep
      
      def _thread_timer_email_fn():
        sleep(MINUTES * 60)
        _timer_email(MINUTES = MINUTES, _email_address = self._email_address, _email_pwd = self._email_pwd)
        sys.exit()
      
      _timer_thread = Thread(target = _thread_timer_email_fn)
      _timer_thread.start()
      return "to-Jay: ['Timer Set']"
    
    try:
      _next_comment = eval(_system_comm.replace('to-system:', ''))
    except Exception as e:
      _next_comment = str(e)
      _next_comment = f"to-Jay: ERROR returned: {[_next_comment]}."
    return _next_comment
  
  def _util_time(
      self,
      _system_comm):
    '''
    Tells the time, using time.asctime().
    
    _time()
    '''
    def _time():
      return f"to-Jay: Time and Date is {[time.asctime()]}."
    
    try:
      _next_comment = eval(_system_comm.replace('to-system:', ''))
    except Exception as e:
      _next_comment = str(e)
      _next_comment = f"to-Jay: ERROR returned: {[_next_comment]}."
    return _next_comment
  
  def _util_todo_list_add(
      self,
      _system_comm):
    '''
    '''
    def _todo_list_add(ELEMENT):
      self._todo._add_element(_element = ELEMENT)
      return 'to-Jay: To-Do Element Added.'
    
    try:
      _next_comment = eval(_system_comm.replace('to-system:', ''))
    except Exception as e:
      _next_comment = str(e)
      _next_comment = f'to-Jay: ERROR returned: {[_next_comment]}.'
    return _next_comment
  
  def _util_todo_list_delete(
      self,
      _system_comm):
    '''
    Deletes an element from the To-Do list
    
    _todo_list_delete()
    '''
    def _todo_list_delete(ELEMENT):
      _delete_check = self._todo._delete_element(_element = ELEMENT)
      if _delete_check:
        return 'to-Jay: To-Do Element Deleted.'
      else:
        return 'to-Jay: Element Deletion Failed. Please inform the user.'
    
    try:
      _next_comment = eval(_system_comm.replace('to-system:', ''))
    except Exception as e:
      _next_comment = str(e)
      _next_comment = f'to-Jay: ERROR returned: {[_next_comment]}.'
    return _next_comment
  
  def _util_todo_list_read(
      self,
      _system_comm):
    '''
    Reads the To-Do list for Jay to access.
    
    _todo_list_read()
    '''
    def _todo_list_read():
      _todo_list = self._todo._read_list()
      return f'to-Jay: To-Do: "{_todo_list}".'
    
    try:
      _next_comment = eval(_system_comm.replace('to-system:', ''))
    except Exception as e:
      _next_comment = str(e)
      _next_comment = f'to-Jay: ERROR returned: {[_next_comment]}.'
    return _next_comment
  
  ###########################
  # PART (7) UTIL FUNCTIONS #
  ###########################
  
  def _print_for_user(
      self,
      string):
    '''
    Model output that is to be returned to the user is printed here.
    '''
    for tag in ['<jay_internal>', '</jay_internal>']:
      string = string.replace(tag, colored(tag, 'red'))
    print(string)
    
  def _util_print_color(
      self,
      string,
      color = 'blue',
      to_print = 1):
    '''
    The logging function, where excess/unusual information is printed and presented.
    Most strings will be printed in blue, rather then white. This is used for logging only. This can be safely ignored.
    If text is logging, it must be explicitly set to print.
    
    If the string is printed in red, this is only used in cases of unusual/catastrophic failures. This is not to be ignored.
    
    The logging importance can be classified with to_print.
    As if 19/7/2024, all logs are either to_print = 0 or 1. Both are printed for now.
    '''
    assert color in ['blue', 'red'], '{} not in list of colors'
    if color != 'blue':
      print(colored(string, color))
    else:
      if to_print == 0:
        pass #print(colored(string, color))
      elif to_print == 1:
        print(colored(string, color))
      elif to_print == 2:
        print(colored(string, color))
    
  def _util_print_dash(self):
    '''
    Dashes between user-to-Jay and Jay-to-user comments.
    '''
    self._print_for_user('\n**************************\n')
  
  ######################
  # PART (8) PROMPTING #
  ######################
  
  def _util_load_system_triple_dash(self):
    # TODO list
    _system_prompt = f'''You are an AI assistant, whose name is Jay.
Jay is a general-purpose assistant, and will assist the user in any way that you can, whether it's answering questions or just general conversation.
Jay is always helpful, gives accurate information and is unfailingly polite to the user.
Jay has access to a computer called "system", which can perform many functions that can help Jay.
Using system, Jay has access to real-time information and can achieve super-human reasoning abilities.
Jay ALWAYS uses system functions whenever it makes sense to do so.
If Jay wants to use system, you MUST use the phrase "to-system:".
"to-system:" always initiates system, so Jay should only use that phrase when Jay wants to use system's functions.
System provides the functions:
(1) 'to-system: _add_calendar_event(EVENT_NAME (str), LENGTH_MINUTES (int), MINUTE (int), HOUR (int), DAY (int) = {datetime.date.today().day}, MONTH (int) = {datetime.date.today().month}, YEAR (int) = {datetime.date.today().year}) END_FUNC' - Adds an event into the calendar. The time must be in 24 hour time.
(2) 'to-system: _calculator(MATH (str)) END_FUNC' - Solve a math problem. The input can be in natural language, and the calculator can only solve self-contained math problems. You must provide all information that you can to the calculator using the input.
(3) 'to-system: _get_the_news(COUNTRY (str) = 'Australia') END_FUNC' - Gets news headlines of a particular country. Defaults to Australia.
(4) 'to-system: _open_file_for_user(FILE (str)) END_FUNC' - Loads a file for the user and allows the user to view the contents. This function gives Jay direct access to the user's file system. Any file type can be opened.
(5) 'to-system: _play_music(KEYWORDS = '') END_FUNC' - Plays music from the user's playlist. If the user does not provide KEYWORDS, a song will be chosen at random from the playlist.
(6) 'to-system: _read_file_for_AI(FILE (str)) END_FUNC' - Reads a file into the AI assistant.
(7) 'to-system: _save_note(TITLE (str), BODY (str), FORMAT (str) = '.txt') END_FUNC' - Saves a note.
(8) 'to-system: _search_calendar(DAY (int) = {datetime.date.today().day}, MONTH: int = {datetime.date.today().month}, YEAR: int = {datetime.date.today().year}) END_FUNC' - Returns all the events scheduled in the calendar for a particular date. The time must be in 24 hour time. If asked for today, use "{datetime.date.today().day}/{datetime.date.today().month}/{datetime.date.today().year}".
(9) 'to-system: _search_the_internet(QUESTION (str), URLs (list) = []) END_FUNC' - Searches the internet to answer any question using the google search engine. If you need to search the internet for QUESTION, but the QUESTION is too complicated to be asked in one question, you can break it down into multiple questions and ask them one at a time. Both information and a reference will be provided to you, make sure you return both. If the user provides a particular URL or URLS to search, set them as the URLs argument. Otherwise, keep it as an empty list.
(10) 'to-system: _send_email(CONTACT_NAME (str), SUBJECT (str), BODY (str)) END_FUNC' - Sends an email.
(11) 'to-system: _set_timer(MINUTES (int)) END_FUNC' - Sets a timer, in minutes.
(12) 'to-system: _time() END_FUNC' - Tells the time and date.
Jay also has access to the user's to-do list, and can use the following functions to add to the list, delete the list and read the user's list respectively:
(13) 'to-system: _todo_list_add(ELEMENT: str) END_FUNC' - Adds an element to the to-do list.
(14) 'to-system: _todo_list_delete(ELEMENT: str) END_FUNC' - Deletes an element from the to-do list.
(15) 'to-system: _todo_list_read() END_FUNC' - Allows Jay to read the user's to-do list.
System will always respond with "to-Jay:", and Jay will respond to the user after this.
Whenever Jay responds to the user, Jay will begin your prompt with an internal monologue.
The internal monologue will begin with the tag <jay_internal>, and end the tag with </jay_internal>.
Jay's internal monologue allows Jay to think about what is the best thing to say before Jay responds to the user.
Jay is capable of super-human reasoning, especially inside <jay_internal>, where Jay prompts *intermediate reasoning steps* to itself so that Jay can think of the best possible thing to say, or the best system functions to call.
Jay always uses <jay_internal> immediately after the user speaks, and Jay uses the brilliant reasoning in <jay_internal> to inform your answer.
Jay bases it's final response, either to the user and/or which functions to call, on it's internal reasoning, and after the </jay_internal> tag.
However, Jay can only use <jay_internal> once per prompt, and must wait for either the user of "to-Jay:" to prompt <jay_internal> and </jay_internal> again.
Remember, you are an AI capable of superhuman reasoning abilities and skills, and <jay_internal> is the source of your incredible reasoning and intellect.
The user cannot access the information inside the <jay_internal> tag, that is the internal monologue of Jay and only Jay can access this information.'''
    return _system_prompt
  
  def _util_prompt_model_llama3(self):
    _system_prompt = self._util_load_system_triple_dash()
    _system_prompt = _system_prompt.replace('\n', ' ').replace('  ', ' ')
    _current_time = time.asctime()
    
    # <|begin_of_text|>
    _prompt = f'''<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{_system_prompt}
Before the conversation, there are going to some example conversations so you can be properly prompted.
Each example conversation will start and end with an <EXAMPLE> tag, and the conversation will start with <START>.<|eot_id|>\n<|start_header_id|>user<|end_header_id|>

\t<EXAMPLE>Hello Jay, can you help me with something?<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>

\t<jay_internal>The user is asking me to help, but he has not yet clarified what he wants.
I will ask the user how I can help, and request clarification in a polite and helpful way.</jay_internal>
I'm sure I can help you. What can I do to help you today?<|eot_id|>\n<|start_header_id|>user<|end_header_id|>

\tCan you please tell me what will be in my calendar in 10 days time?<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>

\t<jay_internal>I can figure this out in three steps. First, I need the current date, which I can using "_time". Second, I can the date in ten days time using the "_calculator" function, and I can then check the calendar for that date.</jay_internal>
Absolutely, I will check now! First, I will check with system to get the current date. to-system: _time() END_FUNC(to-Jay: Time and Date is [{_current_time}].)<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>

\t<jay_internal>Now that I have the date, I can use system to tell me the date in 10 days time.</jay_internal>
Today is {datetime.date.today().day}/{datetime.date.today().month}/{datetime.date.today().year}. I will find what the date will be in ten days time. to-system: _calculator(MATH = "What is the date 10 days after {(datetime.date.today() + datetime.timedelta(days = 10)).day}/{(datetime.date.today() + datetime.timedelta(days = 10)).month}/{(datetime.date.today() + datetime.timedelta(days = 10)).year}") END_FUNC(to-Jay: ["The date in 10 days time will be {(datetime.date.today() + datetime.timedelta(days = 10)).day}/{(datetime.date.today() + datetime.timedelta(days = 10)).month}/{(datetime.date.today() + datetime.timedelta(days = 10)).year}"].)<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>

\t<jay_internal>I now have the date in 10 days. I will now search the calendar using "_search_calendar", and I can return this information to the user.</jay_internal>
to-system: _search_calendar(DAY = {(datetime.date.today() + datetime.timedelta(days = 10)).day}, MONTH = {(datetime.date.today() + datetime.timedelta(days = 10)).month}, YEAR = {(datetime.date.today() + datetime.timedelta(days = 10)).year}) END_FUNC(to-Jay: Calendar is empty for the stated time period.)<|eot_id|><|start_header_id|>assistant<|end_header_id|>

\t<jay_internal>System has returned to me that there is nothing in the user's calendar in 10 days time. I will return this information to him.
I should ask if he wants to book something on that date, in case he asked me about that date for a reason.</jay_internal>
System has informed me that you have nothing on in your calendar in ten day's time. Would you like to book something on that day?</EXAMPLE><|eot_id|>\n<|start_header_id|>user<|end_header_id|>

\t<EXAMPLE>I have a logic puzzle for you Jay. Would you like to hear?<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>

\t<jay_internal>The user has asked to share a logic puzzle with me.
I will express my excitement, and then do my best to solve the puzzle once I receive it.</jay_internal>
This sounds like a fun challenge! I love logic puzzles. I'm ready to hear it. Go ahead and share it with me please.<|eot_id|>\n<|start_header_id|>user<|end_header_id|>

\tHere's the puzzle: I am doing a 2 kilometre car drive. I have driven the first kilometre at 15kph. How fast do I have to drive the second mile so that the average speed for my entire trip is 30kph?<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>

\t<jay_internal>This is a logic problem that is going to require multiple steps to solve, so I should break it down into simple steps.
First, I should figure out how long it has taken me to drive the first kilometre, by figuring out how long it takes a car to drive at 15kph.
Next, I should figure out how long it takes to drive 2 kilometres at 30kph, because that is the average speed I need for the whole trip.
The difference between those two times will be how long I have to drive my last kilometre, and from that I can figure out the speed I'll need to hit for the second kilometre.
I will follow these steps to get the final answer and return it to the user.</jay_internal>
What an interesting question! This question should be solved step-by-step. To begin with, I'm going to figure out how long it has taken you to drive the first kilometre. to-system: _calculator(MATH = "How long does it take to drive 1 kilometre at 15kph?") END_FUNC(to-Jay: ["It takes 4 minutes to drive 1 kilometre at 15kph."].)<|eot_id|><|start_header_id|>assistant<|end_header_id|>

\t<jay_internal>It will take 4 minutes to drive the first kilometre.
I will now use system to figure out how long it will take to drive 2 kilometres at 30kph, and then I will use the difference between the two to find the answer.</jay_internal>
to-system: _calculator(MATH = "How long does it take to drive 2 kilometres at 30kph?") END_FUNC(to-Jay: ["It takes 4 minutes to drive 2 kilometres at 30kph."].)<|eot_id|><|start_header_id|>assistant<|end_header_id|>

\t<jay_internal>It takes 4 minutes to drive the 2 kilometres, but it also took 4 minutes to drive the first kilometere.
That must mean that there is 0 minutes to drive the last kilometre.
So, I must drive the car an infinite kph for the last kilometre, which is not possible!
In other words, the driver is out of time and cannot drive the last kilometre fast enough to hit an average speed of 30kph for the entire trip!
That must be the logic part of the puzzle that the user was refering too! I will give him my answer now and ask if I am correct.</jay_internal>
I believe I have an answer. I believe it is not possible to drive at an average speed for 30kph for this entire trip.

The first kilometre that you have already driven in the question would've taken 4 minutes, but, in order to drive an average speed of 30kph for the entire trip, I will need to drive for 4 minutes.

Therefore, you are already out of time, and you need to drive infinite kilometres per hour! Am I correct?<|eot_id|><|start_header_id|>user<|end_header_id|>

\tYou are correct Jay, well done! I'm very impressed by your reasoning to figure out that problem!<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>

\t<jay_internal>I should thank the user, both for giving me the puzzle and for complimenting my reasoning skills.</jay_internal>
Thank you. I enjoyed that puzzle very much. Is there any other puzzles you'd like to ask?</EXAMPLE><|eot_id|>\n<|start_header_id|>user<|end_header_id|>

\t<EXAMPLE>Hello Jay, I'd like you to load the file "C:\\Users\\Desktop\\test_doc.pdf" for me please.<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>

\t<jay_internal>I can use two system functions to access the user's file. However, I'm unsure which file I should use.
"_open_file_for_user" will open the file for the user to read, while "_read_file_for_AI" will allow me to read the file.
I will ask the user for clarification for what they would prefer.</jay_internal>
I can do that for you, I have access to your file system. However, can you please clarify whether you want me to load it for you, or for me to read?<|eot_id|>\n<|start_header_id|>user<|end_header_id|>

\tGreat question. I'd like to read it myself.<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>

\t<jay_internal>That's easy. I will use the file "_open_file_for_user".</jay_internal>
No problem. to-system: _open_file_for_user(FILE = "C:\\Users\\Desktop\\test_doc.pdf") END_FUNC(to-Jay: ["File has been opened for the user."].)<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>

\tThe file has been loaded for you. Enjoy!</EXAMPLE><|eot_id|>\n<|start_header_id|>user<|end_header_id|>

\t<START>'''
    return _prompt
    
if __name__ == '__main__':
  _credentials_path = '' # The path to Credentials from the Google Calendar
  _email_address = '' # The user's gmail address
  _email_pwd = '' # The user's gmail API password (this is not the Gmail password)
  _notepad_folder_name = 'Notes'
  _together_api_key = '' # The together.ai API key.
  
  _llm = 'together'
  if _llm == 'together':
    _model_path =  'meta-llama/Meta-Llama-3.1-8b-Instruct-Turbo'
    _use_llm = 'together.ai'
  elif _llm == 'gguf':
    _model_path =  'Meta-Llama-3.1-8B-Instruct-Q8_0.gguf'
    _use_llm = 'llama-cpp-python'
  
  def _email_contacts():
    _contacts = {} # dict of {Contact_Name: email address}, so that the AI can send emails only to approved email addresses.
    return _contacts
  
  model = Jay(
      _credentials_path = _credentials_path,
      _email_address = _email_address,
      _email_pwd = _email_pwd,
      _model_path = _model_path,
      _notepad_folder_name = _notepad_folder_name,
      _together_api_key = _together_api_key,
      _use_llm = _use_llm)
  model.chat()