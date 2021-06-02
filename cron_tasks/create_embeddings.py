#!/usr/bin/env python
#Called every night to regenerate route names vector forms from BERT embeddings..

import pickle

import torch
import pymorphy2
import re
from torch.utils.data import DataLoader, Dataset
from transformers import BertTokenizer, TFAutoModel, AutoTokenizer, AutoModel
import time
import os

path = '/var/log/allclimb/qa_source'


def preprocess(sentences, lemmer=pymorphy2.MorphAnalyzer()):
    return [' '.join([lemmer.parse(re.sub(r'[^\w\s]+', '', token))[0].normal_form.lower() for token in sent.split()])
            for sent in sentences]


class TitlesDataset(Dataset):
    def __init__(self, titles):
        self.titles = titles

    def __len__(self):
        return self.titles['input_ids'].shape[0]

    def __getitem__(self, idx):
        return {'input_ids': self.titles['input_ids'][idx],
                'token_type_ids': self.titles['token_type_ids'][idx],
                'attention_mask': self.titles['attention_mask'][idx]}


start_time = time.time()

tokenizer = AutoTokenizer.from_pretrained("sberbank-ai/sbert_large_nlu_ru")
model = AutoModel.from_pretrained("sberbank-ai/sbert_large_nlu_ru")

with open(os.path.join(path, 'qa_route_specs.txt'), 'r') as source:
    text = source.readlines()

pattern = re.compile(r'Маршрут "(.+?)"')
names = [re.search(pattern, route).group(1) for route in text]

with open(os.path.join(path, 'titles.pkl'), 'wb') as titles:
    pickle.dump(names, titles)

titles_tokenized = tokenizer(preprocess(names), padding='max_length',
                             truncation=True, max_length=20, return_tensors='pt')

dataset = TitlesDataset(titles_tokenized)
data_loader = DataLoader(dataset, batch_size=128, shuffle=False)

titles_vectorized = []
with torch.no_grad():
    for batch in data_loader:
        titles_vectorized.append(model(**batch)[1])

titles_vectorized_tensor = torch.cat(titles_vectorized)
torch.save(titles_vectorized_tensor, os.path.join(path, 'titles_vectorized.pkl'))

print(f'Execution time: {(time.time() - start_time)/60} min')
