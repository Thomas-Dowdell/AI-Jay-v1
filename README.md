# Jay, the AI Assistant On Your Local Machine

Welcome to Jay, an open-source AI assistant that can help with any general-purpose text tasks, all on your local machine.
Jay is a large language model, built atop Llama 3.1 8B (https://huggingface.co/meta-llama/Llama-3.1-8B). However, Jay's strengths comes from it's tool-use: the LLM is prompted with a set of tools to use, from life admin like searching calendars to more complicated tasks like searching the internet.

The LLM is built atop llama.cpp (https://github.com/ggerganov/llama.cpp), which allows quantized language models to be run efficiently and quickly, even on CPU-only computers.

## What can Jay do?

Jay can help with a wide range of tasks, including
* Searching the internet to answer questions.
* Providing information on news, weather and calendar events.
* Performing calculations and solving math problems.
* Playing music from a playlist.
* Sending emails and setting reminders.

In order to run, Jay requires the following dependencies:
* 'llama-cpp'
* A credentials file for Google Calendar.
The Google Calendar credentials file is optional, as it is only necessary for calendar functions.

Jay is still in very early days, and begun as an experiment to test small language models' (10B parameters or less) ability to use tools. After a year of experimentation and development, I have found my approach to be accurate. I have found it to be so accurate that I use Jay in my day-to-day life.
