from gcsa.google_calendar import GoogleCalendar
from gcsa.event import Event
from gcsa.recurrence import Recurrence, DAILY, WEEKLY, MONTHLY, YEARLY
from gcsa.reminders import PopupReminder
from beautiful_date import hour, minute
from datetime import datetime, timedelta, date

class Calendar():
    def __init__(
        self,
        _email_address: str,
        _credentials_path: str):
      '''
      Calendar keeps a list of calendar event, sorted chronologically.
      The three calendar functions and all subfunctions of this class.
      
      Google calendar requires both an Gmail address and the path to the credentials json file.
      Details about the credentials json file can be found at:
      https://google-calendar-simple-api.readthedocs.io/en/latest/getting_started.html
      '''
      self._calendar = GoogleCalendar(_email_address, credentials_path = _credentials_path)
      
    def _search_calendar_for_today(self):
      '''
      Returns everything in calendar for today.
      '''
      _today = date.today()
      _year, _month, _day = _today.year, _today.month, _today.day
      _events_today = list(self._calendar[datetime(_year, _month, _day, 0, 0): datetime(_year, _month, _day, 23, 59)])
      if len(_events_today) == 0:
        return ''
      else:
        _s = ''
        for _ in _events_today:
          _summary = _.summary
          _start = _.start
          _s += f"({_summary}: {_start}), "
      return _s
    
    def _add_calendar_event(
        self,
        _event_name: str,
        _minute: int,
        _hour: int,
        _day: int,
        _month: int,
        _year: int,
        _print_function,
        _minutes_before_popup_reminder: list = [2, 15],
        _length_event: int = 15,
        _recur: str = 'FALSE'):
      '''
      Events are added to the calendar here.
      There is an input function that must be satisfied, by inputing (T).
      
      Args:
       - _event_name (STR): The name of the event name.
       - _minute
       - _hour
       - _day
       - _month
       - _year
       - _print_function: The function used to print logging info.
       - _minutes_before_popup_reminder: Popup reminder time (defaults to 2/15 minutes).
       - _length_event: Length of event, in minutes.
       - _recur: Str. Must be [DAILY, WEEKLY, MONTHLY, YEARLY, FALSE]
      
      Returns:
       - check (str)
      '''
      # Preparing functions to handle arguments
      assert _recur in ['DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY', 'FALSE']
      if True:
        # Preparing event length and recurrence
        _delta = timedelta(minutes = int(_length_event))
        _recurrence = self._recurrence_formalize(_recur)
      
        # Sends event to calendar
        _event = Event(
            summary = _event_name,
            start = datetime(int(_year), int(_month), int(_day), int(_hour), int(_minute)),
            end = datetime(int(_year), int(_month), int(_day), int(_hour), int(_minute)) + _delta,
            reminders = [PopupReminder(minutes_before_start = _) for _ in _minutes_before_popup_reminder],
            recurrence = _recurrence)
        self._calendar.add_event(_event)
        return 'Calendar updated.'
      else:
        return 'Calendar update failed.'
    
    def _recurrence_formalize(self, _recur):
      '''
      Formalizes the recurrence string into a recurrence class.
      '''
      if _recur == 'FALSE':
        return None
      elif _recur == 'DAILY':
        return Recurrence.rule(freq = DAILY)
      elif _recur == 'WEEKLY':
        return Recurrence.rule(freq = WEEKLY)
      elif _recur == 'MONTHLY':
        return Recurrence.rule(freq = MONTHLY)
      elif _recur == 'YEARLY':
        return Recurrence.rule(freq = YEARLY)
    
    def _search_calendar_for_day(
        self,
        _year,
        _month,
        _day):
      '''
      Returns all the events in the calendar for _day/_month/_year.
      '''
      _start_date = datetime(_year, _month, _day, 0, 0)
      _end_date = datetime(_year, _month, _day, 23, 59)
      _events_today = list(self._calendar[_start_date:_end_date])
      if len(_events_today) == 0:
        return ''
      else:
        _s = ''
        for _ in _events_today:
          _summary = _.summary
          _start = _.start
          _s += f"({_summary}: {_start}), "
      return _s