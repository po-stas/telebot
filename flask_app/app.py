# This is the core answering part. SQuAd called from here
# All the QA logic implemented in this app and running as a flask internal service
# This flask service called from main backend when bot getting a message

from flask import Flask
from flask import request
from deeppavlov import build_model, configs
import torch
import pymorphy2
import numpy as np
import sys
import re
import os
from transformers import BertTokenizer, TFAutoModel, AutoTokenizer, AutoModel
import pickle

app = Flask(__name__)
path = '/var/log/allclimb/qa_source'

squad_model = build_model(configs.squad.squad_ru_rubert, download=False)
tokenizer = AutoTokenizer.from_pretrained("sberbank-ai/sbert_large_nlu_ru")
model = AutoModel.from_pretrained("sberbank-ai/sbert_large_nlu_ru")

with open(os.path.join(path, 'qa_route_specs.txt'), 'r') as source:
    text = source.readlines()

with open(os.path.join(path, 'titles.pkl'), 'rb') as titles:
    names = pickle.load(titles)

titles_vectorized_tensor = torch.load(os.path.join(path, 'titles_vectorized.pkl'))


@app.route('/')
def process_query():
    query = request.args.get('query')
    result, score = answer(query)
    return {'answer': result, 'score': str(score[0])}


def match(sentence, pdist=torch.nn.PairwiseDistance(p=8.0)):
    encoded_input = tokenizer(sentence, max_length=20, truncation=True,
                              padding='max_length', return_tensors='pt')

    with torch.no_grad():
        out = model(**encoded_input)

    populated_result = torch.cat(titles_vectorized_tensor.shape[0] * [out[1]])
    distances = pdist(populated_result, titles_vectorized_tensor).numpy()
    length = np.min(distances)
    index = np.argmin(distances)
    return index, length


def variants(sentence):
    result = []
    splitted = sentence.split()
    for i in range(len(splitted)):
        left_slice = splitted[i:]
        for j in range(i + 1, len(left_slice) + i + 1):
            result.append(splitted[i:j])
    return result


def match_sentence(sentence, lemmer=pymorphy2.MorphAnalyzer()):
    perms = variants(re.sub(r'[^\w\s]+', '', sentence))
    best_match, best_score = -1, (999999, 0)
    for var in perms:
        processed = [lemmer.parse(token)[0].normal_form for token in var] if lemmer else var
        text = ' '.join(processed)
        index, length = match(text.lower())

        if length < best_score[0]:
            best_match = index
            best_score = (length, len(processed))
        elif length == best_score[0]:
            if len(processed) > best_score[1]:
                best_match = index
                best_score = (length, len(processed))

    return best_match, best_score


def answer(question):
    index, score = match_sentence(question)
    result = f'Маршрут: "{names[index]}"\n'
    result += squad_model([text[index]], [question])[0][0]
    return result, score


if __name__ == '__main__':
    # run app in debug mode on port 5000
    app.run(debug=True, port=5000)
