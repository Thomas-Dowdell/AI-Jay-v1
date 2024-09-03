import os
import sys
import time
from termcolor import colored
os.system('color')

from _util import _prompt_llama_cpp

def _agent_calculator_func(
    _math_input: str,
    _print_function,
    _model_file: str = 'together.ai',
    _model_path: str = 'meta-llama/Meta-Llama-3.1-8b-Instruct-Turbo',
    _together_api_key: str = ''):
  '''
  Agent Calculator is an LLM that exclusiely solves math problems.
  It's called Agent Calculator because that calculator is agentic, rather then a single LLM run.
  The process is as follows:
  (1) An LLM breaks down the math problem into a smaller set of solvable math problems, if necessary.
  (2) The Coder LLM generates the answer to the math question in a two-step process, but in one prompt (the model "thinks out loud", and then writes a python code (with strict coding conditions) to answer the question).
  (3) If the Coder's results do not produce error-free code, then the Refiner reads the question, the Coder's response and the error, and the refiner rewrites the code to remove the error. The refiner is repeated until there is not error, or for 3 loops.
  When either the Coder or the Refiner write code, it is run using the "exec" function.
  The code must be written under the "main" function.
  
  The base LLM is Llama3.1-8B-Instruct. Either the model is run online (using together.ai) or a .gguf model using llama_cpp.
  
  Args:
   - _math_input (STR): The math question, in a natural language, to be solved.
   - _print_function: The function that will print information inside the function.
   - _model_file (STR): The file and library information for the LLM. 'llama-cpp-python' or 'together.ai' for either local. gguf models or for together.ai.
   - _model_path (STR): The path that the model is found in.
  
  Outputs:
   - _final_result (STR): The final result of the code being run.
   - _final_code (STR): The final code that was run to get the answer.
  ```python
  def _print_function(x, to_print = 0.0):
    print(colored(x, 'blue'))
  
  _question = 'What is 6243.83 divided by 95.26, rounded to 5 decimal points?'
  _answer, _code = _agent_calculator_func(_math_input = _question, _print_function = _print_function, _model_file = 'together.ai')
  ```
  '''
  def _generate_response(
      _use_llm,
      _prompt_input,
      _stop_tokens,
      _stream,
      _model):
    if _use_llm in ['llama-cpp-python']:
      _start_time = time.time()
      def _print_function(_str):
        return colored(_str, 'blue')
      _assistant_output, _pt, _ct, _tt = _prompt_llama_cpp(
          _print_function = _print_function,
          _llm = _model,
          _prompt_input = _prompt_input.replace('<|begin_of_text|>', ''),
          _stop_tokens = _stop_tokens,
          _stream = _stream)
      _time_taken = time.time() - _start_time
    elif _use_llm in ['together.ai']:
      _assistant_output, _pt, _ct, _tt, _time_taken = _model(
          _prompt_input, 
          _stop = _stop_tokens, 
          _max_tokens = -1)
    return _assistant_output, _pt, _ct, _tt, _time_taken
  
  # Step (1): The LLM is loaded.
  # All different parts of the agent calculator are built on top of the same LLM, just with different prompting.
  assert _model_file in ['llama-cpp-python', 'together.ai']
  if _model_file == 'llama-cpp-python':
    from llama_cpp import Llama
    _model = Llama(model_path = _model_path, n_ctx = 8192, n_gpu_layers = 0, verbose = False)
  elif _model_file == 'together.ai':
    from _together_api import _API
    _model = _API(_api_key = _together_api_key, _model_name = _model_path)
  
  # Step (2): The LLM is given the math problem, and is asked to refine the question so that it makes more sense.
  # This allows the model to have greater understanding of the question before it begins to answer the question.
  _breakdown_prompt = f'''<|begin_of_text|><|start_header_id|>system<|end_header_id|>

\tYou are a helpful mathematical assistant, who is able to rephrase difficult math problems in a very simple and easy to understand way.
You will be given a math problem, and you will rewrite it to make it as clear and simple as possible.
If it makes more sense to do so, you may rewrite the math problem into a set of simple math problems.
If you are asked a question that involves strings, do not change the case of strings.
For example, if you are asked how many "a"'s are in albatross, specify you are searching for "a", not "A".
Do not answer the question, only rewrite the question so that it is as clear and simple as possible.<|eot_id|>\n<|start_header_id|>user<|end_header_id|>

\t'''
  _breakdown_prompt += f'Question: [{_math_input}].<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>\n\n\tQuestion: [' 
  _breakdown_output, _breakdown_pt, _breakdown_ct, _breakdown_tt, _breakdown_time_taken = _generate_response(_use_llm = _model_file, _prompt_input = _breakdown_prompt, _stop_tokens = ['<|eot_id|>'], _stream = False, _model = _model)
  _print_function(_breakdown_output, to_print = 0.0)
  # The _breakdown_output is added to the _math_input, so that later LLMs can read both the input question and an initial exploration and refinement of the question.
  _broken_math_input = _math_input + '\n' + _breakdown_output
  
  # Step (2): The Coder.
  # The Coder is encouraged to solve the math problem in two steps:
  # (a) The model thinks out-loud and plans it approach to get the answer. There are few limits on what the model can explore during this stage.
  # (b) The model will write the math solution using a python program (```python). The rules here are very strict, it must use the correct version of python and must run "main()" to get the answer. Nothing can be printed and using the "input" function is strictly disallowed.
  _coder_system = '''You are an LLM that solves math problems using the Python programming language.
When you are given a math problem to solve, you will solve it in two steps.
(1) You will write out the steps it takes to solve the problem in natural language first. You will think out loud, write out intermediate conclusions based on your thinking and prepare your code in this way. If the math problem is very complicated, break down the math problem into a set of smaller problems so it is easier to solve.
(2) The second thing you will do is write out a python code that solves the math problem. You will use the reasoning from step (1) to inform your coding, which is why (1) must be so precise. Begin writing your code with "```python\n". The user would encourage you to use the libraries "sympy" and/or "numpy" whenever necessary.

The reason why you must write a python code is because, as an LLM, you are brilliant at reasoning and mathemtical planning, but you can struggle with complicated arthmetic.
By planning out how to solve the math problem using an LLM's reasoning skills, and then doing the complicated math using a proper programming language, you are the best of both worlds and can now solve any math problem using these two tools.

You are a world class python programmer. You have professional-grade programming and mathematical skills, and write out every step of your code to make sure there are no mistakes.
You may plan out the mathematics when you think out loud, but all arthmetic and mathematics must be done in the python code.
Where possible, you use pre-written functions in python libraries rather then writing your own.
Avoid overly complicated code whevever possible.
You must use Australian dating (i.e. day/month/year).
Where there are multiple answers to the question, return every possible solution.
You are writing code for Python 3.11, use syntax and libraries that can be used by that version of Python.
Make sure there is a function called "main()", which will return the answer to the user's question when run.
Put everything inside the "main()" function, including any other function you write.
Return the answer, do not print it.
When you combine terms of an equation, remember to multiple one side by -1 before you add them together. You have an unfortuante habit of forgetting to do this.
The user will not input anything in the function, so do not use the function "input".
Also, do not use the "print" function at all. Return the answer at the end of "main()", but print nothing.
Once your code has been approved, it will be run and the result of the code will be returned to the user.
Use comments to describe what you're doing with the code, and the instructions you are following. The user will read your code, and instructive comments will be crucial to understand your code.
While you are encouraged to think out loud and plan your approach carefully, you WILL NOT REPEAT YOURSELF UNDER ANY CIRCUMSTANCES.
Your final function that returns the answer must be "def main()".'''
  _coder_prompt = f'''<|begin_of_text|><|start_header_id|>system<|end_header_id|>

\t{_coder_system}<|eot_id|>\n<|start_header_id|>user<|end_header_id|>

\t'''
  # The Coder is prompted with the system prompt, the math question and the broken down question response.
  # From here, the Coder must generate the answer.
  # The answer is (a) a natural language explanation where the model is "thinking out loud", and (b) the python code that answers the question.
  _coder_prompt += f'Question: [{_broken_math_input}].<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>\n\n\t'  
  _print_function('====================', to_print = 0.0)
  _coder_output, _coder_pt, _coder_ct, _coder_tt, _coder_time_taken = _generate_response(
      _use_llm = _model_file,
      _prompt_input = _coder_prompt,
      _stop_tokens = ['<|eot_id|>'],
      _stream = False,
      _model = _model)
  _print_function(f'|- "The Coder", {_coder_time_taken} secs, P:{_coder_pt} - Comp:{_coder_ct} - Total:{_coder_tt}', to_print = 1.0)
  _print_function(_coder_output, to_print = 0.0)
  _print_function('====================', to_print = 0.0)
  
  # Step (4): The code from the Coder is extracted (the final chunk of code under "```python" and "```").
  # If the code runs successfully then the results are sent off.
  # If not, the code is sent to the refiner alongside the error.
  _coder_output = '```'.join(_coder_output.split('```')[:-1])
  _final_code = _coder_output.split('```python')[-1].split('```')[0]
  _final_code = _final_code.replace('\nreturn ', '\n')
  _final_code = '\n'.join([_ for _ in _final_code.split('\n') if 'print(' not in _])
  _print_function(_final_code, to_print = 1.0)
  _error_message = ''
  try:
    exec(_final_code, globals())
    _final_result = main()
    _print_function(f'|- Coder Answer: {_final_result}', to_print = 1.0)
    _success_run = True
  except Exception as e:
    _error_message = str(e)
    if "'main'" in _error_message:
      _error_message += '. Ensure the "main" function is used to run the code.'
    if "'return' outside function" in _error_message:
      _error_message += '. Ensure that "return" is used inside a function, never use it outside a function.'
      if '\nreturn ' in _final_code:
        _final_code = _final_code.replace('\nreturn ', '\n')
    _print_function(f'|- Coder Error: {_error_message}', to_print = 1.0)
    _success_run = False
    
  # The number of loops through the refiner is set to 3.
  _t = 0
  while not _success_run:
    # Step (5): The Refiner.
    # The Refiner is identical to the Coder, except that the Refiner is fed the Coder's results and the error message that is produces.
    _refiner_system = f'''You are an LLM that solves math problems using the Python programming language.
You are too be given a previously written python code written with errors, an explanation of the code and the error that resulted from the code when it\'s run.
Your job is to read the explanation of the code, the code itself and it's result, and rewrite the code to make it more accurate.
If the code is inefficent, you must rewrite it so it is more efficient.
If the code makes a math mistake, you must correct to there is no math mistake.
If the code makes an error and it can't run properly, you must change the code so there is no error.
Begin writing your code with "```python".

The reason why you must write a python code is because, as an LLM, you are brilliant at reasoning and mathemtical planning, but you can struggle with complicated arthmetic.
By planning out how to solve the math problem using an LLM's reasoning skills, and then doing the complicated math using a proper programming language, you are the best of both worlds and can now solve any math problem using these two tools.

You are a world class python programmer. You have professional-grade programming and mathematical skills, and write out every step of your code to make sure there are no mistakes.
You may plan out the mathematics when you think out loud, but all arthmetic and mathematics must be done in the python code.
Where possible, you use pre-written functions in python libraries rather then writing your own.
Avoid overly complicated code whevever possible.
You must use Australian dating (i.e. day/month/year).
Where there are multiple answers to the question, return every possible solution.
You are writing code for Python 3.11, use syntax and libraries that can be used by that version of Python.
Make sure there is a function called "main()", which will return the answer to the user's question when run.
Put everything inside the "main()" function, including any other function you write.
Return the answer, do not print it.
LLMs often struggle to remember to multiple the values you are moving by -1, make sure you remember.
The user will not input anything in the function, so do not use the function "input".
Also, do not use the "print" function at all. Return the answer at the end of "main()", but print nothing.
Once your code has been approved, it will be run and the result of the code will be returned to the user.
Use comments to describe what you're doing with the code, and the instructions you are following. The user will read your code, and instructive comments will be crucial to understand your code.
While you are encouraged to think out loud and plan your approach carefully, you will not repeat yourself.'''
    _refiner_prompt = f'''<|start_header_id|>system<|end_header_id|>

\t{_refiner_system}<|eot_id|>n<|start_header_id|>user<|end_header_id|>

\t'''
    if _error_message == '':
      _refiner_prompt += f'Question: [{_math_input}].\nPrevious Code: [{_coder_output}].<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>\n\n'
    else:
      _refiner_prompt += f'Question: [{_math_input}].\nPrevious Code: [{_coder_output}]. Error Message: [{_error_message}].<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>\n\n'
    _print_function('====================', to_print = 0.0)
    _refiner_output, _refiner_pt, _refiner_ct, _refiner_tt, _refiner_time_taken = _generate_response(
        _use_llm = _model_file,
        _prompt_input = _refiner_prompt,
        _stop_tokens = ['<|eot_id|>'],
        _stream = False,
        _model = _model)
    _print_function(f'|- "The Refiner", {_refiner_time_taken} secs, P:{_refiner_pt} - Comp:{_refiner_ct} - Total:{_refiner_tt}', to_print = 1.0)
    _print_function(_refiner_output, to_print = 0.0)
    _print_function('====================', to_print = 0.0)
  
    _refined_code = _refiner_output.split('```python')[-1].split('```')[0]
    _refined_code = _refined_code.replace('\nreturn ', '\n')
    _refined_code = '\n'.join([_ for _ in _refined_code.split('\n') if 'print(' not in _])
    _print_function(_refined_code, to_print = 1.0)
    try:
      # If the refined code runs successfully, then the loop is finished and the results are returned.
      exec(_refined_code, globals())
      _final_result = main()
      _print_function(f'|- Refiner Answer: {_final_result}', to_print = 1.0)
      _success_run = True
    except Exception as e:
      _error_message = str(e)
      if "'main'" in _error_message:
        _error_message += '. Ensure the "main" function is used to run the code.'
      if "'return' outside function" in _error_message:
        _error_message += '. Ensure that "return" is used inside a function.'
        if '\nreturn ' in _refined_code:
          _refined_code = _refined_code.replace('\nreturn ', '\n')
      _print_function(f'|- Refiner Error: {_error_message}', to_print = 1.0)
      _success_run = False
    _final_code = _refined_code
    
    # If there have 3 loops through the refiner, then the loop is broken and the result "Code run unsuccessfully".
    _t += 1
    if _t == 3 and not _success_run:
      _success_run = True
      _final_result = "Code run unsuccessfully"
  return _final_result, _final_code