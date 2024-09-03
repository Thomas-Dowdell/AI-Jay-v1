import os
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import itertools
import json
from llama_cpp import Llama
import lxml
import requests
import io
import time
from trafilatura import fetch_url, extract
import wikipedia

from termcolor import colored
os.system('color')

from _together_api import _API
from _util import _prompt_llama_cpp

'''
_Query is used to, given a natural language query, search the internet and provide an answer

_Query follows a two-step process:
1) Search Google Answer Box (which will be skipped if the query has already been asked)
2) Read and summarize a downloaded URL from Google (if the URL does not return anything, then the next URL is downloaded)

This will return a str as context for Jay
'''

class _Query():
  def __init__(
      self,
      _print_function,
      _generation_model: str = 'together.ai',
      _generation_model_path: str = 'meta-llama/Meta-Llama-3.1-8b-Instruct-Turbo',
      _together_api_key: str = ''):
    self._print_function = _print_function
    self._generation_model = _generation_model
    self._generation_model_path = _generation_model_path
    
    self._reference_number = 0
    
    if self._generation_model == 'together.ai':
      self._model = _API(_api_key = _together_api_key, _model_name = self._generation_model_path)
    elif self._generation_model == 'llama-cpp-python':
      _llm = Llama(self._generation_model_path, n_ctx = 32768, n_gpu_layers = 0, verbose = False)
      class Model():
        def __init__(self, _llm):
          self._llm = _llm
        
        def __call__(self, inputs, _stop, _max_tokens):
          _stt = time.time()
          _output = self._llm(inputs, stop = _stop, max_tokens = _max_tokens, echo = False)
          return _output['choices'][0]['text'], _output['usage']['prompt_tokens'], _output['usage']['completion_tokens'], _output['usage']['total_tokens'], time.time() - _stt
      self._model = Model(_llm = _llm)
    
  def call(
      self,
      _query: str,
      _urls: list = [],
      _no_of_downloaded_websites: int = 5,
      _no_of_sources = 2,
      _search_engine: str = 'google',
      _use_answer_box: bool = True) -> str:
    '''
    Given a natural language query, searches the internet and returns an STR answer.
    The information from _query will contain:
        (a) references to where the information was collected.
        (b) parts of the webpage that is used to inform the answer, to minimize chances of hallucination.
    
    Args:
     - _query (STR): Query to be searched.
     - _no_of_downloaded_websites (INT): The number of websites to be downloaded.
     - _search_engine (STR): The seach engine to use to get relevant URLs. As of 17/7/2024, ['duckduckgo', 'google'] are available.
     - _use_answer_box (BOOL): Whether to attempt to use the google answer box before a search engine is used.
    
    Returns:
     - _final_output (STR): Context that contains the answer.
    '''
    _start_time = time.time()
    self._print_function('|- _q.call initialized', to_print = 0.0)
    self._print_function(f'|- Query: "{_query}"', to_print = 0.0)
    if _urls != []:
      self._print_function(f'|- Provided URLs: {len(_urls)}', to_print = 0.0)
    
    if len(_urls) != 0:
      # If the URLs to search for a provided, then the titles are copied
      _titles = []
      for _url in _urls:
        if 'wikipedia' in _url and 'simple.wikipedia' not in _url:
          _title = wikipedia.search(_url.split('/')[-1].replace('_', ' '))[0]
          _titles.append(_title)
        else:
          _titles.append(_url)
        _downloaded_files_and_urls = []
    else:
      # The files that are too be downloaded.
      # Each element is a 2 element list: the STR of the downloaded website, and the URL.
      # If information is downloaded from the google answer box, then the first str and url is from google answer box.
      _downloaded_files_and_urls = []
    
      # Step (1): The query is sent to the Google Answer Box, if _use_answer_box
      # The information from the Google Answer Box is sent to the _query LLM downstream.
      # The URL is the 'Primary Link' key.
      if _use_answer_box:
        _google_output = self._google_answer_box(_query = _query)
        if len(_google_output) != 0 and 'Primary Link' in _google_output.keys():
          _url = _google_output['Primary Link']
          _final_output = f'Google Query: "{_query}"\n'; _download_facts = []; _urls = []; _title = 'N\A'
          _answer_box_title = _url
          for _k, _v in _google_output.items():
            if 'Link' not in _k and _v not in _download_facts:
              _final_output += f'- {_k}: {_v}\n'
              _download_facts.append(_v)
            if 'Title' in _k:
              _answer_box_title = _v
          _downloaded_files_and_urls.append([_final_output, _url])
        if len(_download_facts) == 0:
          _use_answer_box = False
        
      # Step (2): A search engine is used, the files are downloaded and the model 
      # Either Google of DuckDuckGo are used to search the internet, given the query.
      # The top 10 results are returned.
      # Each of the top 10 results are downloaded, and websites that do not return valid text are discarded.
      _urls, _titles, _bodies = self._download_search_engine(_query = _query, _no_of_downloaded_websites = _no_of_downloaded_websites, _search_engine = _search_engine)
      if len(_downloaded_files_and_urls) > 0:
        self._print_function(f'|- Total URLs Extracted ({_search_engine.capitalize()}) + Google Answer Box: {len(_urls)}', to_print = 1.0)
      else:
        self._print_function(f'|- Total URLs Extracted ({_search_engine.capitalize()}): {len(_urls)}', to_print = 1.0)
      assert len(_urls) == len(_titles) == len(_bodies), 'Assert that the URLs and titles are the same length'
    
      if len(_downloaded_files_and_urls) > 0:
        _url = _downloaded_files_and_urls[0][1]
        _webpage = _downloaded_files_and_urls[0][0]
    
    _extracted_answers = []
    _references = {}
    for _index in range(len(_urls) + 1):
      if _index == 0:
        _download_check = False
        if len(_downloaded_files_and_urls) > 0 and _use_answer_box:
          _url = _downloaded_files_and_urls[0][1]
          _webpage = _downloaded_files_and_urls[0][0]
          _title = _answer_box_title
          _download_check = True
          if len(_webpage.split()) < 25:
            _download_check = False
      
      else:
        _url = _urls[_index - 1]
        _title = _titles[_index - 1]
        _webpage, _download_check = self._download_webpage(_url = _url, _title = _title)
      if _download_check:
        self._print_function(f'|- URL: {_url}', to_print = 1.0)
        self._print_function(f'|- Word Count: {len(_webpage.split())}', to_print = 1.0)
        _abstract = _webpage[:250].replace('\n', ' ').replace('  ', ' ')
        self._print_function(f'|- Abstract: {_abstract} ...', to_print = 1.0)
        _answer_output, _answer_output_check, _summary_answer_output, _txt_name = self._generate_answer(_query = _query, _webpage = _webpage, _title = _title, _prepare_sentence_references = False)
        if _answer_output_check:
          _extracted_answers.append(f'[{_answer_output}]. REFERENCE: <{len(_references) + 1 + self._reference_number}>')
          _references[len(_references) + 1] = _url
          self._print_function(f'|- <{len(_references)}> Title: {_title}', to_print = 2.0)
          if type(_txt_name) is not bool:
            self._print_function(f'|- {_txt_name}')
          self._print_function('====================', to_print = 1.0)
          
          if len(_references) == _no_of_sources:
            self._reference_number += len(_references)
            self._print_function('|- _q.call completed. Time: {:.4f}'.format(time.time() - _start_time), to_print = 1.0)
            _extracted_answers = str(_extracted_answers)
            return _extracted_answers
    
    self._print_function('|- _q.call completed. Time: {:.4f}'.format(time.time() - _start_time), to_print = 1.0)
    if len(_extracted_answers) == 0:
      return 'No information was found online.'
    else:
      _extracted_answers = str(_extracted_answers)
      self._reference_number += len(_references)
      return _extracted_answers
  
  def _generate_answer(
      self,
      _query,
      _webpage,
      _title,
      _prepare_sentence_references):
    if len(_webpage.split()) < 25:
      return '', False, '', ''
    _context = _webpage.replace('\n', ' ').replace('  ', ' ')
    
    _website_download_prompt = '''You are an LLM, and it is your job to read a downloaded website.
If the downloaded website does not contain any useful information, then the download is a failure.
You are looking for the following problems with the download:
(1) An error, such as a 404 Error.
(2) The website saying that Javascript needs to be enabled.
If the website does contain useful information, then the download was successful.
You will read the conversation, and then explain your reasoning behind your decision as to whether it is a download or not.'''
    _website_download_prompt = f'''<|start_header_id|>system<|end_header_id|>

\t{_website_download_prompt}<|eot_id|>\n<|start_header_id|>user<|end_header_id|>

\t{_context} EXPLAIN YOUR REASONING AS TO IF THE WEBSITE HAS BEEN SUCCESSUFLLY DOWNLOADED.<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>

\t'''
    _website_download_output, _website_download_pt, _website_download_ct, _website_download_tt, _website_download_time_taken = self._model(_website_download_prompt, _stop = ['<|eot_id|>'], _max_tokens = 1024)
    self._print_function(f"|- Website Downloading Answer: {_website_download_time_taken} secs, P:{_website_download_pt} - Comp:{_website_download_ct} - Total:{_website_download_tt}", to_print = 1.0)
    _website_download_prompt += _website_download_output + '<|eot_id|>\n<|start_header_id|>user<|end_header_id|>\n\n\tTherefore, if you had to summarize your answer as either "TRUE" (the download was successful) or "FALSE" (the download failed), what would you answer?<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>\n\n\t'
    _website_download_output, _, _, _, _ = self._model(_website_download_prompt, _stop = ['<|eot_id|>'], _max_tokens = 1024)
    if 'TRUE' not in _website_download_output:
      return '', False, '', ''
    
    _base_system_prompt = '''You are an LLM that performs reading comprehension. You are given context to read, and you must answer questions based on the context you are given. You will give as much detail in your answer as possible. You are going to answer this question by following these instructions:
(1) You will prompt the reasoning, based on the extracted information, that you will use to inform your answer. Remember, you are capable of incredible reasoning abilities, and you will think out loud too get the right answer. Begin this prompt by saying "REASONING: ".
(2) You will repeat keywords and phrases from the context that can help inform your answer. You can repeat as much information as you feel is wise. Begin this prompt by saying "KEYPHRASES: ".
(3) You will give your final answer only at the end, based on your extracted context and out-loud reasoning. Begin your final prompt by saying "ANSWER: ".
If you feel there is no relevant information to answer the question, use the keyphrase "N\A".
If you are given an open-ended question, give as much information as possible to answer the question from all perspectives.
If you are given a closed-ended question, then give the answer and your supporting facts in as much detail as possible.'''
    _base_prompt = f'''<|start_header_id|>system<|end_header_id|>

\t{_base_system_prompt}<|eot_id|>\n<|start_header_id|>user<|end_header_id|>

\t{_context} QUESTION: "{_query}"<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>

\t'''
    _generated_answers, _generated_answers_bool = [], []
    _base_output, _base_pt, _base_ct, _base_tt, _base_time_taken = self._model(_base_prompt, _stop = ['<|eot_id|>'], _max_tokens = 1024)
    self._print_function(f"|- Base Answer: {_base_time_taken} secs, P:{_base_pt} - Comp:{_base_ct} - Total:{_base_tt}", to_print = 1.0)
    
    _check_system_prompt = '''You are an LLM that is designed to ensure that assist in a reading comprehension task.
You are to be given two pieces of information:
    (a) Context: A large chunk of text, that was used to answer the question.
    (b) Sentence to Support: A sentence that is part of an answer based of Context.
You must output the sentence or sentences in "Context" that the "Sentence to Support" is based on.
Present each sentence you extract from "Context" in the following form:
- "SENTENCE A"
- "SENTENCE B".'''
    
    _proper_design = 'ANSWER:' in _base_output and 'KEYPHRASES:' in _base_output and 'REASONING:' in _base_output
    if _prepare_sentence_references and _proper_design:
      _base_output_adjusted = _base_output.replace('REASONING:', '')
      _reasoning_output = _base_output_adjusted.split('KEYPHRASES:')[0]
      _answer_output = _base_output.split('ANSWER:')[1]
    
      _reasoning_output = _reasoning_output.split('.')
      _answer_output = _answer_output.split('.')
    
      _reasoning_output = [_ for _ in _reasoning_output if _ not in ['\n', '', ' ']]
      _answer_output = [_ for _ in _answer_output if _ not in ['\n', '', ' ']]
        
      _context_to_save_to_str = _context.lower()
      
      for _no, _sentence in enumerate(_reasoning_output + _answer_output):
        _check_prompt = f'''<|start_header_id|>system<|end_header_id|>

\t{_check_system_prompt}<|eot_id|>\n<|start_header_id|>user<|end_header_id|>

\tContext: [{_context}]
Sentence to Support: "{_sentence}"<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>

\tThe information in Context that best supports "{_sentence}" is 
'''
        _check_output, _check_pt, _check_ct, _check_tt, _check_time_taken = self._model(_check_prompt, _stop = ['<|eot_id|>'], _max_tokens = 256)
        self._print_function(f"|- Check Answer #{_no + 1}: {_base_time_taken} secs, P:{_base_pt} - Comp:{_base_ct} - Total:{_base_tt}", to_print = 0.0)
        _check_output_individuals = _check_output.replace('"\n', '').replace('- "', '').split('.')
        _sentences_in_paragraph = 0
        
        for _ in _check_output_individuals:
          if _[:2] == '" ':
            _ = _[2:]
          if _.lower() in _context.lower():
            _sentences_in_paragraph += 1
            _context_to_save_to_str = _context_to_save_to_str.replace(_.lower(), _.upper())
          else:
            _unfounded_sentence = _.replace('\n', '')
            self._print_function(f'Unfounded Sentence: {_unfounded_sentence}', to_print = 0.0)
    
      _txt_name = _query.replace(' ', '_').replace('.', '').replace('?', '').replace('!', '').lower()
      _txt_name = f'Query_Output\\{_txt_name}.txt'
      f = open(_txt_name, 'w', encoding = 'utf-8')
      _context_to_save_to_str = _context_to_save_to_str.replace('\n', '').replace('.', '.\n')
      f.write(_context_to_save_to_str)
      f.close()
    else:
      _txt_name = False
    
    _summary_system_prompt = f'''<|start_header_id|>system<|end_header_id|>

\tYou are being given a question, and a detailed answer.
The detailed answer was generated by an LLM, and may or may contain the answer to the question.
The context the original LLM used to generate it's answer has been discarded, you only have access to the original LLM's detailed answer.
Be aware, LLMs are not perfect, and sometimes will give detailed response that do not answer the question.<|eot_id|>\n<|start_header_id|>user<|end_header_id|>

\tQUESTION: "{_query}". Generated Response: "{_base_output}".'''
  
    _summary_system_prompt += 'Has the question been properly answered using the context? Answer [TRUE] or [FALSE].<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>\n\n\t'
    _summary_check_output, _, _, _, _ = self._model(_summary_system_prompt, _stop = ['<|eot_id|>'], _max_tokens = 16)
    if 'TRUE' in _summary_check_output:
      _summary_system_prompt += f'TRUE<|eot_id|>\n<|start_header_id|>user<|end_header_id|>\n\n\tBased on your returned context, answer the user\'s question {_query} in as few words as possible. If you cannot answer the question, return N\A.<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>\n\n\t'
      _summary_answer_output, _, _, _, _ = self._model(_summary_system_prompt, _stop = ['<|eot_id|>'], _max_tokens = 64)
      if 'N\A' in _summary_answer_output or 'N/A' in _summary_answer_output:
        _summary_check_output = 'FALSE'
      else:
        self._print_function(f'|- Minute Answer: {_summary_answer_output}', to_print = 2.0)
    else:
      _summary_answer_output = 'N\A'
      _summary_check_output = 'FALSE'
    if 'FALSE' in _summary_check_output:
      return _base_output, False, _summary_answer_output, _txt_name
    else:
      return _base_output, True, _summary_answer_output, _txt_name
  
  def _download_webpage(
      self,
      _url: str,
      _title: str):
    def _download_wikipedia(_url, _title):
      _wikipedia_search_title = _title.replace(' - Wikipedia', '')
      _search_results = wikipedia.search(_wikipedia_search_title)
      if len(_search_results) == 0:
        return '', False
      _first_search_result = _search_results[0]
      if _first_search_result == _title:
        _page = wikipedia.WikipediaPage(_first_search_result)
      else:
        _page = wikipedia.WikipediaPage(_first_search_result)
      _content = _page.content.replace('U.S', 'US')
      _content = _content.split('\n')
      _content = [_ for _ in _content if _[:2] != '==']
      _content = '\n'.join(_content)
      return _content, True
    
    def _download_quora(_url, _title):
      # BOTH REDDIT AND QUORA ARE COMMON WEBSITES, THAT DO NOT RETURN VALID INFORMATION
      # THEY ARE SET TO FALSE
      return '', False
    
    def _download_youtube(_url, _title):
      try:
        _video_link = _url.split('watch%3Fv%3D')[1]
        from youtube_transcript_api import YouTubeTranscriptApi
        srt = YouTubeTranscriptApi.get_transcript(_video_link)
        _text = [_['text'] for _ in srt]
        _text = 'YOUTUBE VIDEO TRANSCRIPT: ' + ' '.join(_text)
        _text = _text.replace('\n', ' ')
        return _text, True
      except:
        return '', False
    
    def _download_reddit(_url, _title):
      # BOTH REDDIT AND QUORA ARE COMMON WEBSITES, THAT DO NOT RETURN VALID INFORMATION
      # THEY ARE SET TO FALSE
      return '', False
    
    def _download_pdf_online(_url, _title):
      try:
        from PyPDF2 import PdfReader
        _response = requests.get(_url, timeout = 10.0)
        _on_fly_mem_obj = io.BytesIO(_response.content)
        _pdf_file = PdfReader(_on_fly_mem_obj)
        _pdf_text = '\n'.join(_pdf_file.pages[_].extract_text() for _ in range(len(_pdf_file.pages)))
        while '  ' in _pdf_text:
          _pdf_text = _pdf_text.replace('  ', ' ')
        while '\n \n' in _pdf_text:
          _pdf_text = _pdf_text.replace('\n \n', '\n')
        while '\n\n' in _pdf_text:
          _pdf_text = _pdf_text.replace('\n\n', '\n')
        return _pdf_text, True
      except:
        return '', False
    
    def _download_website(_url, _title):
      try:
        _html = requests.get(_url, timeout = 10.0)
        _soup = BeautifulSoup(_html.text, 'html.parser')
        for script in _soup(['script', 'style']):
          script.extract()
        _text = _soup.get_text()
        _lines = (line.strip() for line in _text.splitlines())
        chunks = (phrase.strip() for line in _lines for phrase in line.split(' '))
        _text = ' '.join(chunk for chunk in chunks if chunk)
        return _text, True
      except:
        return '', False
      
    if 'wikipedia' in _url and 'simple.wikipedia' not in _url:
      _webpage, _download_check = _download_wikipedia(_url = _url, _title = _title)
    elif 'youtube' in _url:
      _webpage, _download_check = _download_youtube(_url = _url, _title = _title)
    elif 'quora' in _url:
      _webpage, _download_check = _download_quora(_url = _url, _title = _title)
    elif 'reddit' in _url:
      _webpage, _download_check = _download_reddit(_url = _url, _title = _title)
    elif '.pdf' in _url[-10:]:
      _webpage, _download_check = _download_pdf_online(_url = _url, _title = _title)
    else:
      _webpage, _download_check = _download_website(_url = _url, _title = _title)
    _webpage = ' '.join([_ for _ in _webpage.split() if len(_) < 20])
    return _webpage, _download_check
  
  def _download_search_engine(
      self,
      _query,
      _no_of_downloaded_websites: int,
      _search_engine: str):
    '''
    Downloads a certain number of websites using a search engine.
    Either Google or DuckDuckGo.
    '''
    def _download_duckduckgo(_query, _no_of_downloaded_websites, _safesearch = 'moderate'):
      assert _safesearch in ['on', 'moderate', 'off']
      _results = DDGS().text(_query, safesearch = _safesearch, max_results = _no_of_downloaded_websites)
      _final_titles, _final_urls, _final_bodies = [], [], []
      for _ in _results:
        _title, _url, _body = _['title'], _['href'], _['body']
        _final_titles.append(_title); _final_urls.append(_url); _final_bodies.append(_body)
      return (_final_urls, _final_titles, _final_bodies)
    
    def _download_google(_query, _no_of_downloaded_websites, _safesearch = ''):
      # Step (1) Download URL metadata
      _params = {'q': _query}
      _response = requests.get('https://www.google.com/search', params = _params)
      _soup = BeautifulSoup(_response.text, 'html.parser')
      _results = _soup.find_all()
      # Step (2) Extract and clean URL and title information from metadata
      _result_titles = []; _result_urls = []
      for _result in _results:
        _title = _result.find('h3')
        _url = _result.find('a')
        if _title is None or _url is None:
          pass
        else:
          _result_titles.append(_result.find('h3').text)
          _result_urls.append(_result.find('a')['href'])
      _suitable_titles = []; _suitable_urls = []
      for _title, _url in zip(_result_titles, _result_urls):
        _url = _url.split('/url?q=')
        if len(_url) != 1:
          _url = _url[1].split('&sa=')[0]
          if _title not in _suitable_titles:
            _suitable_titles.append(_title)
            _suitable_urls.append(_url)
  
      # Step (3) Remove non-functional popular webpages from list of URLs
      _final_urls = []; _final_titles = []
      _bodies_empty = []
      for _url, _title in zip(_suitable_urls, _suitable_titles):
        _final_urls.append(_url)
        _final_titles.append(_title)
        _bodies_empty.append('')
      if _no_of_downloaded_websites < len(_final_urls):
        _final_urls = _final_urls[:_no_of_downloaded_websites]
        _final_titles = _final_titles[:_no_of_downloaded_websites]
        _bodies_empty = _bodies_empty[:_no_of_downloaded_websites]
      return (_final_urls, _final_titles, _bodies_empty)
    
    assert _no_of_downloaded_websites > 0
    assert _search_engine.lower() in ['google', 'duckduckgo']
    if _search_engine == 'duckduckgo':
      _urls, _titles, _bodies = _download_duckduckgo(_query = _query, _no_of_downloaded_websites = _no_of_downloaded_websites)
    if _search_engine == 'google':
      _urls, _titles, _bodies = _download_google(_query = _query, _no_of_downloaded_websites = _no_of_downloaded_websites)
    return _urls, _titles, _bodies
  
  def _google_answer_box(
      self,
      _query):
    '''
    The Google Answer Box is used to inform the answer.
    This is the most efficient way to search the internet, and can provide useful information.
    However, only simple questions can be answered this way.
    
    As of 27/7/2024, only google answer boxes that return a link and reference are returned.
    Answer boxes that do not are commented out.
    
    The link will be found in the key "Primary Link".
    '''
    _headers = {'User-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.67 Safari/537.36'}
    _params = {'q': _query}
    _html = requests.get('https://www.google.com/search', headers = _headers, params = _params)
    _soup = BeautifulSoup(_html.text, 'lxml')
    
    # _google_box_answers ["Type of Information": "Extracted Info"]
    _google_box = {}
    def _load_notable_text(_soup):
      '''How many protons in Oxygen atom?'''
      if _soup.select_one('.ILfuVd') != None:
        _notable_answer = _soup.select_one('.ILfuVd').text
        _google_box['Notable Text'] = _notable_answer
    _load_notable_text(_soup = _soup)
    
    def _google_business_box(_soup):
      '''state parliament nsw open hours'''
      try:
        _desc = _soup.select_one('.xDKLO')
        _google_box['Business Information'] = _desc.text
      except:
        pass
    _google_business_box(_soup = _soup)
    
    def _google_table(_soup):
      try:
        _desc = _soup.select_one('.Crs1tb')
        _google_box['Table'] = _desc.text
      except:
        pass
    _google_table(_soup = _soup)
    
    def _google_address_box(_soup):
      try:
        _desc = _soup.select_one('.sXLaOe')
        _google_box['Address'] = _desc.text
      except:
        pass
    _google_address_box(_soup = _soup)
    
    def _google_side_box(_soup):
      try:
        _desc = _soup.select_one('.kno-rdesc')
        _desc_href = str(_desc).split('href="')[1].split('" ')[0]
        _desc = _desc.text
        _google_box['Side Box'] = _desc
        _google_box['Side Box (href)'] = _desc_href
        x = _soup.select('.rVusze')
        for _ in x:
          _key, _value = _.text.split(': ')
          _google_box['Side Box {}'.format(_key)] = _value
      except:
        pass
    _google_side_box(_soup = _soup)
    
    def _google_quaternary_answer(_soup):
      try:
        _title = _soup.select_one('.QpPSMb').text
        _subtitle = _soup.select_one('.loJjTe').text
        while _title[0] == ' ':
          _title = _title[1:]
        while _subtitle[0] == ' ':
          _subtitle = _subtitle[1:]
        _google_box['Quaternary Title'] = _title
        _google_box['Quaternary Subtitle'] = _subtitle
      except:
        pass
    _google_quaternary_answer(_soup = _soup)

    def _google_tertiary_answer(_soup):
      # _google_answer_box('How much is a large pizza at Papa John\'s')
      try:
        _title = _soup.select_one('.ifM9O .LC20lb').text
        _link = _soup.select_one('.ifM9O .yuRUbf a')['href']
        _displayed_link = _soup.select_one('.ifM9O .iUh30').text
        _snippet = _soup.select_one('.ifM9O .iKJnec').text
  
        _google_box['Tertiary Title'] = _title
        _google_box['Tertiary Link'] = _link
        _google_box['Tertiary Displayed Link'] = _displayed_link
        _google_box['Tertiary Snippet'] = _snippet
  
        for _table_key, _table_value, _table_value_price in zip(
            _soup.select('.ztXv9~ tr+ tr td:nth-child(1)'),
            _soup.select('td:nth-child(2)'),
            _soup.select('td~ td+ td')):
          _key = _table_key.text
          _value = _table_value.text
          _price = _table_value_price.text
          _google_box['Tertiary Table Row'] = [_key, _value, _price]
      except:
        pass
    _google_tertiary_answer(_soup = _soup)

    def _google_secondary_answer(_soup):
      '''dynasties of macedonia'''
      try:
        _title = _soup.select_one('.xpdopen .DKV0Md').text
        _link = _soup.select_one('.xpdopen .yuRUbf a')['href']
        _displayed_link = _soup.select_one('.xpdopen .iUh30').text
        _google_box['Secondary Title'] = _title
        _google_box['Secondary Link'] = _link
        #_google_box['Secondary Displayed Link'] = _displayed_link
  
        if _soup.select_one('.xpdopen .co8aDb b') and _soup.select_one('.TrT0Xe') is not None:
          _snippet = _soup.select_one('.xpdopen .co8aDb b').text
          _bullet_points = '\n'.join([_bullet_point.text for _bullet_point in _soup.select('.TrT0Xe')])
        elif _soup.select_one('.TrT0Xe') is not None:
          _bullet_points = '\n'.join([_bullet_point.text for _bullet_point in _soup.select('.TrT0Xe')])
          _snippet = None
        else: 
          _snippet = _soup.select_one('.xpdopen .iKJnec').text
          _bullet_points = None
      
        if type(_snippet) is str:
          _google_box['Secondary Snippet'] = _snippet
        if type(_bullet_points) is str:
          _google_box['Secondary Bullet Points'] = _bullet_points
  
        if _soup.select_one('#rso td:nth-child(1)') is None:
          pass
        else:
         for _table_key, _table_value in zip(
            _soup.select('#rso td:nth-child(1)'), 
            _soup.select('#rso td+ td')):
            _key = _table_key.text
            _value = _table_value.text
            _google_box['Secondary {}'.format(_key)] = _value
      except:
        pass
    _google_secondary_answer(_soup = _soup)

    def _google_primany_answer(_soup):
      '''luke skywalker lightsaber color'''
      try:
        _link = _soup.select_one('.yuRUbf a')['href']
        _google_box['Primary Link'] = _link
        _answer = _soup.select_one('.IZ6rdc').text
        _google_box['Primary Answer'] = _answer
        _snippet = _soup.select_one('.hgKElc').text
        _google_box['Primary Snippet'] = _snippet
      except:
        pass
    _google_primany_answer(_soup = _soup)

    def _google_dictionary_answer(_soup):
      '''define slob'''
      try:
        _definition = 1
        for _result in _soup.select('.VpH2eb.vmod'):
          #_syllables = _result.select_one('.DgZBFd span').text
          #_audio_link = f"https:{result.select_one('.brWULd audio source')['src']}"
          #_phonetic_result.select_one('.S23sjd .LTKOO span').text
          #_word_types = [_word_type.text for _word_type in _result.select('.vdBwhd .YrbPuc')]
    
          _definitions = [_definition.text for _definition in _result.select('.PZPZlf')]
          _sentence_examples = [_definition.text for _definition in _result.select('.ubHt5c')]
          _similar_words = [_similar_word.text for _similar_word in _result.select('.p9F8Cd span')]
          _google_box['Definition {}'.format(_definition)] = _definitions
          _definition += 1
      except:
        pass
    _google_dictionary_answer(_soup = _soup)

    def _google_currency_conversion_answer(_soup):
      '''100 usd in aud'''
      try:
        _conversion = _soup.select_one('.SwHCTb').text
        _google_box['Conversion Rate'] = _conversion
        _conversion_currency = _soup.select_one('.MWvIVe').text
        _google_box['Conversion Currency'] = _conversion_currency
      except:
        pass
    _google_currency_conversion_answer(_soup  = _soup)

    def _google_population_answer(_soup):
      '''What is the population of India?'''
      try:
        _place = _soup.select_one('.GzssTd span').text; _google_box['Location'] = _place
        _population_year = _soup.select_one('.KBXm4e').text.split(' ')
        _population = _population_year[0]; _google_box['Population'] = _population
        _year = _population_year[1].replace('(', '').replace(')', ''); _google_box['Year Captured'] = _year
        _sources = [_source.text for _source in _soup.select('.kno-ftr span a')]; _google_box['Source of Info'] = _sources

        #for other_city, other_population in zip(_soup.select('.AleqXe'), _soup.select('.kpd-lv')):
        #  other_place_city = other_city.text.strip()
        #  other_place_population = other_population.text
      except:
        pass
    _google_population_answer(_soup = _soup)

    def _google_stock_answer(_soup):
      '''vas Stock'''
      try:
        _title = _soup.select_one('.oPhL2e').text.replace(u'\xa0', u'').split('>')[1]; _google_box['Stock Title'] = _title
        _date_time = _soup.select_one('[jsname=ihIZgd]').text.replace(' ·', ''); _google_box['Stock Datetime'] = _date_time
        _market_status = _soup.select_one('.TgMHGc span:nth-child(1)').text.strip().replace(':', ''); _google_box['Market Status'] = _market_status
        _currency = _soup.select_one('.knFDje').text.strip(); _google_box['Currency'] = _currency
        _current_price = _soup.select_one('.wT3VGc, .XcVN5d').text; _google_box['Current Price'] = _current_price
        _price_change = _soup.select_one('.WlRRw > span:nth-child(1)').text; _google_box['Price Change'] = _price_change
        _price_change_percent = _soup.select_one('.jBBUv span:nth-child(1)').text.replace('(', '').replace(')', ''); _google_box['Price Change Percent'] = _price_change_percent
        _price_change_date = _soup.select_one('.jdUcZd span').text.strip().capitalize(); _google_box['Price Change Date'] = _price_change_date
        _price_movement = 'Down' if '−' in _price_change else 'Up'; _google_box['Price Movement'] = _price_movement

        for _stock_table_key, _stock_table_value in zip(_soup.select('.JgXcPd'), _soup.select('.iyjjgb')):
          _stock_key = _stock_table_key.text
          _stock_value = _stock_table_value.text
          _google_box[_stock_key] = _stock_value
      except:
        pass
    _google_stock_answer(_soup = _soup)

    def _google_weather_answer(_soup):
      '''What is the weather in Orange, NSW?'''
      try:
        _location = _soup.select_one('#wob_loc').text; _google_box['Weather Location'] = _location
        _weather_condition = _soup.select_one('#wob_dc').text; _google_box['Weather Condition'] = _weather_condition
        _temperature = _soup.select_one('#wob_tm').text; _google_box['Weather Temperature'] = _temperature
        _precipitation = _soup.select_one('#wob_pp').text; _google_box['Weather Precipitation'] = _precipitation
        _humidity = _soup.select_one('#wob_hm').text; _google_box['Weather Humidity'] = _humidity
        _wind = _soup.select_one('#wob_ws').text; _google_box['Weather Wind'] = _wind
        _current_time = _soup.select_one('#wob_dts').text; _google_box['Weather Current-Time'] = _current_time
  
        for _wind_speed_direction in _soup.select('.wob_noe .wob_hw'):
          try:
            _wind_speed = _wind_speed_direction.select_one('.wob_t').text; _google_box['Weather Wind Speed'] = _wind_speed
            _wind_direction = ' '.join(_wind_speed_direction.select_one('.wob_t')['aria-label'].split(' ')[2:4]); _google_box['Weather Wind Direction'] = _wind_direction
          except:
            pass
  
        for _forecast in _soup.select('.wob_df'):
          _day = _forecast.select_one('.Z1VzSb')['aria-label']
          _weather = str(_forecast.select_one('.YQ4gaf')).split('img alt="')[1].split('" class=')[0]
          if _forecast.select_one('.vk_gy .wob_t:nth-child(1)') is None:
            _high_temp = _forecast.select_one('.gNCp2e .wob_t').text
          else:
            _high_temp = _forecast.select_one('.vk_gy .wob_t:nth-child(1)').text
          _low_temp = _forecast.select_one('.QrNVmd .wob_t:nth-child(1)').text
          _google_box['Weather Forecast {}'.format(_day)] = 'Weather: {}, High: {}, Low: {}'.format(_weather, _high_temp, _low_temp)
      except:
        pass
    _google_weather_answer(_soup = _soup)
    
    def _google_calculator_answer(_soup):
      '''32 * 3 / 3 + 12 * 332 - 1995'''
      try:
        _math_expression = _soup.select_one('.XH1CIc').text.strip().replace(' =', '')
        _calc_answer = _soup.select_one('#cwos').text.strip()
        _google_box['Mathematical Expression'] = _math_expression
        _google_box['Calculated Answer'] = _calc_answer
      except:
        pass
    _google_calculator_answer(_soup = _soup)
    return _google_box
    
if __name__ == '__main__':
  def _print_function(string, to_print = 1.0):
    if to_print == 1.0:
      print(colored(string, 'blue'))

  _question = 'What is the height of Mount Everest?'
  
  _together_api_key = ''
  _q = _Query(_print_function = _print_function, _together_api_key = _together_api_key)
  _output = _q.call(_query = _question, _search_engine = 'google', _no_of_downloaded_websites = 5)
  print(_output)