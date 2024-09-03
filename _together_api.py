import time

class _API():
  def __init__(
      self,
      _api_key: str,
      _model_name: str,
      _input_type = str,):
    '''
    Loads the Together API client.
    '''
    self._model_name = _model_name
    self._input_type = _input_type
    
    from together import Together
    self._client = Together(api_key = _api_key)
  
  def __call__(
      self,
      _messages,
      _stop = ['<|eot_id|>', 'END_FUNC'],
      _max_tokens = 1024):
    _stt = time.time()
    
    if self._input_type == str:
      _response = self._client.completions.create(
          model = self._model_name,
          prompt = _messages,
          max_tokens = _max_tokens,
          stop = _stop)
      return (_response.choices[0].text, _response.usage.prompt_tokens, _response.usage.completion_tokens, _response.usage.total_tokens, time.time() - _stt)
    elif self._input_type == dict:
      _response = self._client.chat.completions.create(
          model = self._model_name,
          messages = _messages,
          max_tokens = _max_tokens,
          stop = _stop)
      return (_response.choices[0].message.content, _response.usage.prompt_tokens, _response.usage.completion_tokens, _response.usage.total_tokens, time.time() - _stt)