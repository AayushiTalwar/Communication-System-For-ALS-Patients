import os
import time
from openai import OpenAI
from playsound import playsound

from collections import deque

ROOT = os.path.dirname(__file__)

client = OpenAI(
    # defaults to os.environ.get("OPENAI_API_KEY")
    api_key= "<OPENAI API KEY>",
)

def autocomplete(sentence):
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": """Autocomplete or autocorrect the last word of below sentence
I need a list of 4 most probable auto-completions or most probables words in form of a python list. Make sure the response only consists of comma separated strings in form of a python list

the sentence is:
%s""" % sentence,
            }
        ],
        model="gpt-3.5-turbo-1106",
    )
    
    return chat_completion.choices[0].message.content

def suggest(sentence):
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": """suggest the next word in the following sentence
I need a list of 4 most probable words that may occur after the given sentence in form of a python list. Make sure the response only consists of comma separated strings in form of a python list

the sentence is:
%s""" % sentence,
            }
        ],
        model="gpt-3.5-turbo-1106",
    )
    
    return chat_completion.choices[0].message.content

# print(autocomplete(""))

def builder(conn):
    
    history = deque(maxlen=5)
    word = ""
    time_delta = 1

    index1 = 0
    row_mode = True
    index2 = 0

    possibilities = [['⌫', '_', '↵', ','],
                     ['a', 'b', 'c', 'd', 'e', '⌫'], 
                     ['f', 'g', 'h', 'i', 'j', '⌫'], 
                     ['k', 'l', 'm', 'n', 'o', '⌫'], 
                     ['p', 'q', 'r', 's', 't', '⌫'], 
                     ['u', 'v', 'w', 'x', 'y', 'z', '⌫'],
                     ["hello", "how", "good", "i"]]

    if conn.recv() != "Ready":
        print("Child dead")
        quit()

    while True:

        print((chr(27) + "[2J"))
        for w in history:
            print(w)

        print(word, end='\n\n')
        for i, row in enumerate(possibilities):
            if row_mode and i == index1:
                print('\x1b[0;30;47m' + ''.join(['\t' + e for e in row]) + '\x1b[0m')
            elif not row_mode and i == index1:
                print(''.join(['\t' + e if j != index2 else '\x1b[0;30;47m\t'+e+'\x1b[0m' for j, e in enumerate(row)]))
            else:
                print(''.join(['\t' + e for e in row]))


        # print(char, end='\b')
        start_time = time.time()

        while time.time() - start_time < time_delta:
            conn.send('Request')
            if conn.recv():

                if row_mode:
                    row_mode = False
                    time.sleep(1)
                    break

                char = possibilities[index1][index2]

                if char == '↵' and word:
                    response = client.audio.speech.create(
                        model="tts-1",
                        voice="alloy",
                        input=word,
                    )

                    response.stream_to_file(os.path.join(ROOT, "output.mp3"))
                    row_mode = True
                    history.append(word)
                    word = ""
                    playsound("output.mp3")
                    os.remove('output.mp3')
                    break


                if char == '⌫' and word:
                    word = word[:-1]
                elif char == '_' and word:
                    word += ' '
                elif char != '⌫' and char != '_': 
                    word += char

                if index1 == len(possibilities) - 1:
                    word = ' '.join(word.split(' ')[:-1] + [char]) + ' '
                    try:
                        suggested_words = eval(suggest('\n'.join(history) + '\n' + word))
                    except:
                        suggested_words = None

                    if suggested_words is not None:
                        possibilities[-1] = suggested_words
                else:
                    try:
                        autocomplete_words = eval(autocomplete('\n'.join(history) + '\n' + word))
                    except:
                        autocomplete_words = None

                    if autocomplete_words is not None:
                        possibilities[-1] = autocomplete_words

                # if word:
                #     print('\n' + word)
                #     index = 0

                row_mode = True
                index2 = 0

                time.sleep(1)
                break


        if row_mode:
            index1 = (index1+1) % len(possibilities)
        else:
            index2 = (index2+1) % len(possibilities[index1])

    conn.close()