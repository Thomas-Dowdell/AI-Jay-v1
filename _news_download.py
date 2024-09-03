import os
import time
from gnews import GNews

class NewsScraper():
  def __init__(
      self,
      _print_function,
      _period = None,
      _max_results = None,
      _country = '',
      _language = None,
      _exclude_websites = None,
      _start_date = None,
      _end_date = None):
    '''
    A specialist news scraper.
    This is not a general website scraper, this is only to be used for news.
    This is a versatile news scaper, and has the following capabilites:
     - Returns the top news by location/topic/keyword/in general.
     - Returns the news, given a URL.
     - Can have particular parameters set (period, max_results, country, language, start and end dates, exclude websites).
    '''
    self._print_function = _print_function
    
    _print_function(f'|- Country Request: {[_country]}', to_print = 1.0)
    _country_code = self._country_code_validation(_country = _country)
    _print_function(f'|- Country Code Request: {[_country_code]}', to_print = 1.0)
    _stt = time.time()
    self._google_news = GNews()
    _print_function(f'|- GNews Object Loaded, Country: {[_country_code]}', to_print = 0.0)
    self._set_news_parameters(
        _period = _period,
        _max_results = _max_results, 
        _country = _country_code,
        _language = _language,
        _exclude_websites = _exclude_websites,
        _start_date = _start_date,
        _end_date = _end_date)
  
  def _get_top_news(self):
    '''
    Returns the top news, given the set parameters.
    
    Returns:
     - _news (LIST): Each entry is a particular news article (DICT), which has keys ('title', 'published date', 'url', 'publisher').
    '''
    return self._google_news.get_top_news()
  
  def _get_news(
      self,
      _keyword):
    '''
    Returns news, given a keyword.
    
    Args:
     - _keyword (STR): The keyword to search.
    
    Returns:
     - _news (LIST): Each entry is a particular news article (DICT), which has keys ('title', 'published date', 'url', 'publisher').
    '''
    return self._google_news.get_news(_keyword)
  
  def _get_news_by_topic(
      self,
      _topic):
    assert _topic in ['WORLD', 'NATION', 'BUSINESS', 'TECHNOLOGY', 'ENTERTAINMENT', 'SPORTS', 'SCIENCE', 'HEALTH']
    return self._google_news.get_news_by_topic(_topic)
  
  def _get_news_by_location(
      self,
      _location):
    return self._google_news.get_news_by_location(_location)
  
  def _get_news_by_site(
      self,
      _website):
    return self._google_news.get_news_by_site(_website)
  
  def _get_full_article(
      self,
      _url):
    '''
    Downloads the title, text, authors and images from a news article.
    This doesn't work very well.
    
    Args:
     - _url (STR): The URL of article.
    
    Returns:
     - _title (STR): The title of the article.
     - _text (STR): The text of the article.
     - _authors (LIST): The list of authors.
     - _images (LIST): List of images.
    '''
    _article = self._google_news.get_full_article(_url)
    return _article.title, _article.text, _article.authors, _article.images
  
  def _set_news_parameters(
      self,
      _period,
      _max_results,
      _country,
      _language,
      _exclude_websites,
      _start_date,
      _end_date):
    if _period is not None:
      self._google_news.period = _period
    if _max_results is not None:
      self._google_news.max_results = _max_results
    if _country is not None:
      self._google_news.country = _country
    if _language is not None:
      self._google_news.language = _language
    if _exclude_websites is not None:
      self._google_news.exclude_websites = _exclude_websites
    if _start_date is not None:
      self._google_news.start_date = _start_date
    if _end_date is not None:
      self._google_news.end_date = _end_date
  
  def _valid_countries(self):
    '''
    {'Australia': 'AU', 'Botswana': 'BW', 'Canada ': 'CA', 'Ethiopia': 'ET', 'Ghana': 'GH', 'India ': 'IN',
 'Indonesia': 'ID', 'Ireland': 'IE', 'Israel ': 'IL', 'Kenya': 'KE', 'Latvia': 'LV', 'Malaysia': 'MY', 'Namibia': 'NA',
 'New Zealand': 'NZ', 'Nigeria': 'NG', 'Pakistan': 'PK', 'Philippines': 'PH', 'Singapore': 'SG', 'South Africa': 'ZA',
 'Tanzania': 'TZ', 'Uganda': 'UG', 'United Kingdom': 'GB', 'United States': 'US', 'Zimbabwe': 'ZW',
 'Czech Republic': 'CZ', 'Germany': 'DE', 'Austria': 'AT', 'Switzerland': 'CH', 'Argentina': 'AR', 'Chile': 'CL',
 'Colombia': 'CO', 'Cuba': 'CU', 'Mexico': 'MX', 'Peru': 'PE', 'Venezuela': 'VE', 'Belgium ': 'BE', 'France': 'FR',
 'Morocco': 'MA', 'Senegal': 'SN', 'Italy': 'IT', 'Lithuania': 'LT', 'Hungary': 'HU', 'Netherlands': 'NL',
 'Norway': 'NO', 'Poland': 'PL', 'Brazil': 'BR', 'Portugal': 'PT', 'Romania': 'RO', 'Slovakia': 'SK', 'Slovenia': 'SI',
 'Sweden': 'SE', 'Vietnam': 'VN', 'Turkey': 'TR', 'Greece': 'GR', 'Bulgaria': 'BG', 'Russia': 'RU', 'Ukraine ': 'UA',
 'Serbia': 'RS', 'United Arab Emirates': 'AE', 'Saudi Arabia': 'SA', 'Lebanon': 'LB', 'Egypt': 'EG',
 'Bangladesh': 'BD', 'Thailand': 'TH', 'China': 'CN', 'Taiwan': 'TW', 'Hong Kong': 'HK', 'Japan': 'JP',
 'Republic of Korea': 'KR'}
    '''
    return self._google_news.AVAILABLE_COUNTRIES
  
  def _valid_languages(self):
    '''
    {'english': 'en', 'indonesian': 'id', 'czech': 'cs', 'german': 'de', 'spanish': 'es-419', 'french': 'fr',
 'italian': 'it', 'latvian': 'lv', 'lithuanian': 'lt', 'hungarian': 'hu', 'dutch': 'nl', 'norwegian': 'no',
 'polish': 'pl', 'portuguese brasil': 'pt-419', 'portuguese portugal': 'pt-150', 'romanian': 'ro', 'slovak': 'sk',
 'slovenian': 'sl', 'swedish': 'sv', 'vietnamese': 'vi', 'turkish': 'tr', 'greek': 'el', 'bulgarian': 'bg',
 'russian': 'ru', 'serbian': 'sr', 'ukrainian': 'uk', 'hebrew': 'he', 'arabic': 'ar', 'marathi': 'mr', 'hindi': 'hi',
 'bengali': 'bn', 'tamil': 'ta', 'telugu': 'te', 'malyalam': 'ml', 'thai': 'th', 'chinese simplified': 'zh-Hans',
 'chinese traditional': 'zh-Hant', 'japanese': 'ja', 'korean': 'ko'}
    '''
    return self._google_news.AVAILABLE_LANGUAGES

  def _country_code_validation(self, _country):
    _country_to_code = {'Australia': 'AU', 'Botswana': 'BW', 'Canada ': 'CA', 'Ethiopia': 'ET', 'Ghana': 'GH', 'India ': 'IN',
                        'Indonesia': 'ID', 'Ireland': 'IE', 'Israel ': 'IL', 'Kenya': 'KE', 'Latvia': 'LV', 'Malaysia': 'MY', 'Namibia': 'NA',
                        'New Zealand': 'NZ', 'Nigeria': 'NG', 'Pakistan': 'PK', 'Philippines': 'PH', 'Singapore': 'SG', 'South Africa': 'ZA',
                        'Tanzania': 'TZ', 'Uganda': 'UG', 'United Kingdom': 'GB', 'United States': 'US', 'Zimbabwe': 'ZW',
                        'Czech Republic': 'CZ', 'Germany': 'DE', 'Austria': 'AT', 'Switzerland': 'CH', 'Argentina': 'AR', 'Chile': 'CL',
                        'Colombia': 'CO', 'Cuba': 'CU', 'Mexico': 'MX', 'Peru': 'PE', 'Venezuela': 'VE', 'Belgium ': 'BE', 'France': 'FR',
                        'Morocco': 'MA', 'Senegal': 'SN', 'Italy': 'IT', 'Lithuania': 'LT', 'Hungary': 'HU', 'Netherlands': 'NL',
                        'Norway': 'NO', 'Poland': 'PL', 'Brazil': 'BR', 'Portugal': 'PT', 'Romania': 'RO', 'Slovakia': 'SK', 'Slovenia': 'SI',
                        'Sweden': 'SE', 'Vietnam': 'VN', 'Turkey': 'TR', 'Greece': 'GR', 'Bulgaria': 'BG', 'Russia': 'RU', 'Ukraine ': 'UA',
                        'Serbia': 'RS', 'United Arab Emirates': 'AE', 'Saudi Arabia': 'SA', 'Lebanon': 'LB', 'Egypt': 'EG',
                        'Bangladesh': 'BD', 'Thailand': 'TH', 'China': 'CN', 'Taiwan': 'TW', 'Hong Kong': 'HK', 'Japan': 'JP',
                        'Republic of Korea': 'KR', 'Ameria': 'US', 'United States of America': 'US', 'Britain': 'GB', 'Great Britain': 'GB'}
    _country = _country.replace('"', '')
    if _country in _country_to_code.keys():
      return _country_to_code[_country]
    elif _country in _country_to_code.values():
      return _country
    else:
      return ''

def _get_the_news(
    _country = '',
    _max_results = 10,
    _print_function = print):
  '''
  Returns the news headlines and description. A country can be given, but worldwide news can be found as well.
  '''
  if True: #try:
    if type(_country) == str:
      if _country != '':
        _ns = NewsScraper(
            _print_function = _print_function,
            _max_results = _max_results,
            _country = _country)
      else:
        _ns = NewsScraper(_print_function = _print_function, _max_results = _max_results)
    else:
      _ns = NewsScraper(_print_function = _print_function, _max_results = _max_results)
    _stt = time.time()
    _tp_nws = _ns._get_top_news()
    _print_function('|- News Loaded: {:.4f} secs'.format(time.time() - _stt), to_print = 1.0)
  
    _titles, _descriptions = [], []
    for _ in _tp_nws:
      _titles.append(_['title'])
      _descriptions.append(_['description'])
    return _titles, _descriptions
  else: #except:
    return ['to-Jay: News download failed.'], ['to-Jay: News download failed']