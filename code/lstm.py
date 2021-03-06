# -*- coding: utf-8 -*-
"""Copy of twitter-all.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1QJERYrGCy4X6w_nc4GjPMk5PAbi-Cfas
"""

# Commented out IPython magic to ensure Python compatibility.
#!pip install keras-bert
import pandas as pd
#import keras_bert as bert
import keras
from nltk.tokenize import word_tokenize
import numpy as np
import re
from collections import Counter
from xml.etree import ElementTree as ET
import os
import glob
import pandas as pd
from collections import OrderedDict
import matplotlib.pyplot as plt
# %matplotlib inline
import nltk
nltk.download("stopwords")
from nltk.corpus import stopwords
stopword = stopwords.words('english')
from nltk.tokenize import word_tokenize

# mount google drive
from google.colab import drive
drive.mount('/content/drive')

# Path and construct a file list
PATH = "/content/drive/My Drive/LangPro2/"
DIREC = PATH + "pan20-author-profiling-training-2020-02-23/"
LANG  = "en/"
file_list = os.listdir(DIREC + LANG)

for i in file_list:
    if i[-3:] != "xml":
        file_list.remove(i)

file_list = sorted(file_list)

# Get ground truth, append into the dataframe
GT = DIREC + LANG + "truth.txt"
true_values = OrderedDict()
f = open(GT)

for line in f:
    linev = line.strip().split(":::")
    true_values[linev[0]] = linev[1]
    
f.close()

df = pd.DataFrame(sorted(true_values.items()))
df = df.rename({0:"ID", 1:"label"}, axis = 1)
df["label"] = df["label"].astype("int")

df.head()

def clean(sentence):
    input_str = sentence
    output_str = re.sub('[^A-Za-z0-9]+', ' ', input_str) # remove punctiation
    output_str = re.sub('URL', ' ', output_str) # remove URL tag
    output_str = re.sub('RT', ' ', output_str) # remove RT tag
    output_str = re.sub('USER', ' ', output_str) # remove USER tag
    output_str = re.sub('HASHTAG', ' ', output_str) # remove HASHTAG tag
    output_str = re.sub(' s ', ' ', output_str) # remove 's

    return output_str

def get_representation_tweets(FILE):
    parsedtree = ET.parse(FILE)
    documents = parsedtree.iter("document")
    
    texts = []
    for doc in documents:
        texts.append(doc.text)
        
    lengths = [len(text) for text in texts]
    
#    return (np.mean(lengths), np.std(lengths))
    return (texts)

# append each content into DF
x = []
for i in range(len(file_list)):
    ind = file_list[i]
    x.append(get_representation_tweets(DIREC + LANG + ind))
    
df["content"] = pd.Series(x)

df.head()

X = df.copy()
y = df["label"]

from sklearn.model_selection import train_test_split as split

X_train, X_test, y_train, y_test = split(X, y, test_size=0.33, random_state=42)

"""## Model"""

lstm_keys = X_train.index # preserve keys 
print ("length", len(X_train))
X_train.head()

"""### LSTM"""

import tensorflow as tf
from tensorflow.keras.preprocessing.text import Tokenizer
from keras.preprocessing import sequence
import keras

# Flatten the "content" column, extract 100 posts from a single ID
con = []
ans = []
X_train.index = range(201) # reindex X_train
y_train.index = range(201)

for i in range(201):
    for j in range(100):
        con.append(X_train["content"][i][j])
        ans.append(y_train[i])

con = pd.Series(con)
ans = pd.Series(ans)

new = pd.DataFrame(con)

new["label"] = ans

new.head()

new = new.rename(columns = {0: "content"})

clean_df = []
for i in range(20100):

  clean_df.append(clean(new["content"][i]))

clean_df = pd.Series(clean_df)
clean_df = pd.DataFrame(clean_df)
clean_df = clean_df.rename(columns= {0: "content"})
clean_df.head()

clean_df["label"] = new["label"]

# The maximum number of words to be used. (most frequent)
MAX_NB_WORDS = 50000
# Max number of words in each complaint.
MAX_SEQUENCE_LENGTH = 250
# This is fixed.
EMBEDDING_DIM = 100

tokenizer = Tokenizer(num_words=MAX_NB_WORDS, filters='!"#$%&()*+,-./:;<=>?@[\]^_`{|}~', lower=True)
tokenizer.fit_on_texts(clean_df["content"].values)
word_index = tokenizer.word_index
print('Found %s unique tokens.' % len(word_index))

X_lstm = tokenizer.texts_to_sequences(clean_df["content"].values)
X_lstm = sequence.pad_sequences(X_lstm, maxlen=MAX_SEQUENCE_LENGTH)
print('Shape of data tensor:', X_lstm.shape)

Y_lstm = pd.get_dummies(clean_df["label"]).values
print('Shape of label tensor:', Y_lstm.shape)

from sklearn.model_selection import train_test_split

X_lstm_train, X_lstm_test, Y_lstm_train, Y_lstm_test = train_test_split(X_lstm,Y_lstm, test_size = 0.1, random_state = 42)

print(X_lstm_train.shape,Y_lstm_train.shape)
print(X_lstm_test.shape,Y_lstm_test.shape)

from tensorflow.python.client import device_lib
print(device_lib.list_local_devices())

from tensorflow.keras import Sequential
from tensorflow.keras.layers import Embedding
from tensorflow.keras.layers import LSTM, Dense, SpatialDropout1D
from tensorflow.keras.callbacks import EarlyStopping


model = Sequential()
model.add(Embedding(MAX_NB_WORDS, EMBEDDING_DIM, input_length=X.shape[1]))
model.add(SpatialDropout1D(0.2))
model.add(LSTM(100))#, dropout=0.5, recurrent_dropout=0.2))
model.add(Dense(100, activation='relu'))
model.add(Dense(20, activation='relu'))
model.add(Dense(2, activation='softmax'))
weights = model.get_weights()
model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])

model.summary()

epochs = 1
batch_size = 128

history = model.fit(X_lstm_train, Y_lstm_train, epochs=epochs, batch_size=batch_size,
                    validation_split=0.1,
                    callbacks=[EarlyStopping(monitor='val_loss', patience=3, min_delta=0.0001)])

accr = model.evaluate(X_lstm_test,Y_lstm_test)
print('Test set\n  Loss: {:0.3f}\n  Accuracy: {:0.3f}'.format(accr[0],accr[1]))

w = model.get_weights()

for i in range(10):
        print(w[i].shape)

lstm = np.array(w[-2])
lstm

neu = pd.DataFrame(index=range(300),columns=range(20))
neu["label"] = df["label"]
for i in range(300):
    for j in range(20):
      if neu["label"][i] == 0:
        neu.iat[i, j] = lstm[j, 0]
            
      if neu["label"][i] == 1:
        neu.iat[i, j] = lstm[j, 1]

neu = neu.drop(columns = "label", axis = 1)
df = pd.concat([df, neu[neu.keys()]], axis = 1)
for i in range(20):
    df = df.rename(columns = {i: "neuron{}".format(i)})

print (df.keys())
df.head()

X = df.drop(d, axis = 1)
y = df["label"]

from sklearn.model_selection import train_test_split as split

X_train, X_test, y_train, y_test = split(X, y, test_size=0.33, random_state=42)

k = X_train.index

k == lstm_keys

X_train.head()