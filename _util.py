import sys

def _prompt_llama_cpp(
    _print_function,
    _llm,
    _prompt_input: str,
    _prompt_tokens: int = -1,
    _console_length: int = 171,
    _stop_tokens: list = ['<|eot_id|>'],
    _max_tokens: int = -1,
    _repeat_penalty: float = 1.1,
    _stream: bool = False,
    _input_text: str = 'Streamed Text: "'):
  '''
  Generates a text output from a Llama_CPP llm.
  Either the output is streamed or generated statically.
  
  Args:
   - _print_function: The function to print streamed text.
   - _llm: The language model, from Llama_CPP.
   - _prompt_input: The input text.
   - _prompt_tokens: The number of tokens in the input text.
   - _console_length: The length of the string that can be printed in a single line using a python console. Computer being tested has length of 171.
                      As of 5/7/2024, we are unsure of how to do that except for trial and error.
   - _stop_tokens: The stop tokens for the Llama_CPP model. Default model uses Llama3 stop-tokens.
   - _max_tokens: The maximum output tokens of the Llama_CPP model. Defaults to -1 (no maximum length).
   - _repeat_penalty: Defaults to 1.1.
   - _stream: Whether to stream the output.
   - _input_text: The beginning of the text to be streamed.
  
  Output:
   - _output: The generated output text.
   - _prompt_tokens: The length of prompt tokens.
   - _completion_tokens: The length of tokens that are generated.
   - _total_tokens: The total number of tokens that are prompted and generated.
  
  ```python
  import os
  from termcolor import colored
  os.system('color')
  def _print_function(_str):
    return colored(_str, 'blue')
  
  from llama_cpp import Llama
  _llm = Llama(model_path = _model_file, n_ctx = 8192, n_gpu_layers = 0, verbose = False)
  _user_input = 'Hello, how are you today?'
  _prompt_input = f"<|start_header_id|>system<|end_header_id|>\n\n\You are a polite, helpful AI assistant.<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{_user_input}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
  _output, _prompt_tokens, _completion_tokens, _total_tokens =  _prompt_llama_cpp(
      _print_function = _print_function,
      _llm = _llm,
      _prompt_input = _prompt_input)
  print(f"Output: {_output}")
  print(_prompt_tokens)
  print(_completion_tokens)
  print(_total_tokens)
  ```
  '''
  if '<|begin_of_text|>' == _prompt_input[:17]:
    _prompt_input = _prompt_input[17:]
  if _stream:
    assert _console_length > 0, 'Set _console_length to the length of the str that takes entire line on Python console.'
    _output, _prompt_tokens, _completion_tokens = _stream_llama_cpp(
        _print_function = _print_function,
        _llm = _llm,
        _prompt_input = _prompt_input,
        _console_length = _console_length,
        _stop_tokens = _stop_tokens,
        _max_tokens = _max_tokens,
        _repeat_penalty = _repeat_penalty,
        _input_text = _input_text)
    _total_tokens = _completion_tokens + _prompt_tokens
  else:
    _output_dict = _llm(
        _prompt_input,
        stop = _stop_tokens,
        max_tokens = _max_tokens,
        echo = False,
        repeat_penalty = _repeat_penalty)
    _output = _output_dict['choices'][0]['text']
    _prompt_tokens = _output_dict['usage']['prompt_tokens']
    _completion_tokens = _output_dict['usage']['completion_tokens']
    _total_tokens = _output_dict['usage']['total_tokens']
  return _output, _prompt_tokens, _completion_tokens, _total_tokens

def _stream_llama_cpp(
    _print_function,
    _llm,
    _prompt_input: str,
    _console_length: int = 171,
    _stop_tokens: list = ['<|eot_id|>'],
    _max_tokens: int = -1,
    _repeat_penalty: float = 1.1,
    _input_text = 'Streamed Text: "'):
  '''
  Prints and streams the text from a Llama_CPP model.
  The text is subject to post-processing, so the output is not final.
  It is recommended that the _print_function be debugging, not output.
  
  Args:
   - _print_function: The function to print streamed text.
   - _llm: The language model, from Llama_CPP.
   - _prompt_input: The input text.
   - _console_length: The length of the string that can be printed in a single line using a python console. Computer being tested has length of 171.
                      As of 5/7/2024, we are unsure of how to do that except for trial and error.
   - _stop_tokens: The stop tokens for the Llama_CPP model. Default model uses Llama3 stop-tokens.
   - _max_tokens: The maximum output tokens of the Llama_CPP model. Defaults to -1 (no maximum length).
   - _repeat_penalty: Defaults to 1.1.
  
  Output:
   - _output: The generated output text.
   - _prompt_tokens: The length of tokens as input.
   - _completion_tokens: The length of tokens that are generated.
  
  ```python
  import os
  from termcolor import colored
  os.system('color')
  def _print_function(_str):
    return colored(_str, 'blue')
  
  from llama_cpp import Llama
  _llm = Llama(model_path = _model_file, n_ctx = 8192, n_gpu_layers = 0, verbose = False)
  _user_input = 'Hello, how are you today?'
  _prompt_input = f"<|start_header_id|>system<|end_header_id|>\n\n\You are a polite, helpful AI assistant.<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{_user_input}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
  _output, _completion_tokens =  _stream_llama_cpp(
      _print_function = _print_function,
      _llm = _llm,
      _prompt_input = _prompt_input)
  print(f"Output: {_output}")
  print(_completion_tokens)
  ```
  '''
  _tokenized_input = _llm.tokenize(bytes(_prompt_input, 'utf-8'))
  _prompt_tokens = len(_tokenized_input)
  _output, _printable_streamed_text, _completion_tokens = '', _input_text, 0
  for _token in _llm(
      _prompt_input,
      stop = _stop_tokens,
      max_tokens = _max_tokens,
      repeat_penalty = _repeat_penalty,
      echo = False,
      stream = True):
    _output += _token['choices'][0]['text']
    if '\n' in _token['choices'][0]['text']:
      for _character in _token['choices'][0]['text']:
        if _character != '\n':
          _printable_streamed_text += _character
        else:
         sys.stdout.write(_print_function(f"{_printable_streamed_text}     \n ... \r")); sys.stdout.flush()
         _printable_streamed_text = ''
    elif len(_printable_streamed_text + _token['choices'][0]['text'] + ' ... ') > _console_length:
      _printable_streamed_text += _token['choices'][0]['text']
      sys.stdout.write(_print_function(f"{_printable_streamed_text[:_console_length - 1]}\r"))
      sys.stdout.write(_print_function('\n \r'))
      _printable_streamed_text = _printable_streamed_text[_console_length - 1:]
    else:
      _printable_streamed_text += _token['choices'][0]['text']
    
    sys.stdout.write(_print_function(f"{_printable_streamed_text} ... \r"))
    sys.stdout.flush()
    _completion_tokens += 1
  sys.stdout.write(_print_function(f"{_printable_streamed_text}\"     \n"))
  sys.stdout.flush()
  return _output, _prompt_tokens, _completion_tokens