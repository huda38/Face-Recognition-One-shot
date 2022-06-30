# -*- coding: utf-8 -*-
"""face recognition using one shot learning.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1xrbLLFqF4Yy_LhZvEliHdDtK8v0TgkwX

**Import**
"""

# Commented out IPython magic to ensure Python compatibility.
import cv2
import os
import random
from tensorflow.keras.layers import Layer, Conv2D, Dense, MaxPooling2D, Input, Flatten
from PIL import Image

import matplotlib.pyplot as plt
# %matplotlib inline

import numpy as np
import os
import sys
import random
import tensorflow as tf
from pathlib import Path
from six.moves import urllib
import tarfile
import shutil

from tensorflow.keras import applications
from tensorflow.keras import layers
from tensorflow.keras import losses
from tensorflow.keras import optimizers
from tensorflow.keras import metrics
from tensorflow.keras import Model

from tensorflow.keras.applications import inception_v3
from tensorflow.keras.applications.inception_v3 import InceptionV3

target_size = (224, 224)

inception_model = InceptionV3(weights='imagenet', input_shape = target_size + (3,), include_top=False)

#positive, negative and anchor setup
class SimilarityLayer(layers.Layer):

    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    def call(self, anchor, positive, negative):
        d1 = tf.reduce_sum(tf.square(anchor-positive), -1)
        d2 = tf.reduce_sum(tf.square(anchor-negative), -1)
        return(d1,d2)
    
anchor = layers.Input(name='anchor', shape = target_size + (3,))
positive = layers.Input(name='positive', shape = target_size + (3,))
negative = layers.Input(name='negative', shape = target_size + (3,))

sim_layer_output = SimilarityLayer().call(
    transfer_inception_model(inputs = inception_v3.preprocess_input(anchor)),
    transfer_inception_model(inputs = inception_v3.preprocess_input(positive)),
    transfer_inception_model(inputs = inception_v3.preprocess_input(negative))
)

siamese_model = Model(inputs=[anchor, positive,negative], outputs=sim_layer_output)

class SiameseModelClass(Model):
    def __init__(self, siamese_model, margin = 0.5):
        super(SiameseModelClass, self).__init__()
        
        self.siamese_model = siamese_model
        self.margin = margin
        
        #track the loss
        self.loss_tracker = metrics.Mean(name="loss")
        
    def call(self, inputs):
        return self.siamese_model(inputs)
    
   
    def train_step(self, data):
        with tf.GradientTape() as tape:
            
            loss = self.custom_loss(data)
            
       
        trainable_vars = self.siamese_model.trainable_variables
        gradients = tape.gradient(loss, trainable_vars)
        
        
        self.optimizer.apply_gradients(zip(gradients, trainable_vars))
        
        
        self.loss_tracker.update_state(loss)
        
        return {"loss": self.loss_tracker.result()}
    
    
    def test_step(self, data):
        
        loss = self.custom_loss(data)
        
        
        self.loss_tracker.update_state(loss)
        
        return {"loss": self.loss_tracker.result()}
    
   
    def custom_loss(self, data):
        #distances from the siamese model output
        d1, d2 = self.siamese_model(data)
        
        #loss
        loss = tf.maximum(d1 - d2 + self.margin, 0)
        
        return loss
    
    @property
    def metrics(self):
        
        return [self.loss_tracker]

def download_and_uncompress_tarball(tarball_url, dataset_dir):
    
    filename = tarball_url.split('/')[-1]
    filepath = os.path.join(dataset_dir, filename)

    def _progress(count, block_size, total_size):
        sys.stdout.write('\r>> Downloading %s %.1f%%' % (
            filename, float(count * block_size) / float(total_size) * 100.0))
        sys.stdout.flush()

    filepath, _ = urllib.request.urlretrieve(tarball_url, filepath, _progress)
    print()
    statinfo = os.stat(filepath)
    print('Successfully downloaded', filename, statinfo.st_size, 'bytes.')
    tarfile.open(filepath, 'r:gz').extractall(dataset_dir)

database_url = 'http://vis-www.cs.umass.edu/lfw/lfw-deepfunneled.tgz'

root_folder = '../working'
download_folder = root_folder + '/'+ 'data/lfw_original'
selection_folder = root_folder + '/' + 'data/lfw_selection'
download_path = download_folder + '/lfw-deepfunneled.tgz'

if not os.path.exists(download_folder):
    os.makedirs(download_folder)

if not os.path.exists(selection_folder):
    os.makedirs(selection_folder)
    
if not os.path.exists(download_path):
    download_and_uncompress_tarball(database_url, download_folder)

extracted_folder = download_folder + '/lfw-deepfunneled'

subfolders = [x[0] for x in os.walk(extracted_folder)]

subfolders.pop(0)

people_list = []

for path in subfolders:
    image_count = len([f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))])
    people_list.append((path.split('\\')[-1], image_count))
    
people_list = sorted(people_list, key=lambda x: x[1], reverse=True)

print(f'Number of people: {len(subfolders)}')
print(f'Number of people with only one photo: {len([person for person, image_count in people_list if image_count==1])}')
print(f'Number of people with >=5 photos: {len([person for person, image_count in people_list if image_count>=5])}')

selected_persons = {}
i = 0

for person,image_count in people_list:
    if image_count >=5:
        file_list = []
        

        newpath = selection_folder + '/' + person.split('/')[-1]
        if not os.path.exists(newpath):
            os.makedirs(newpath)
        
    
        files = [os.path.join(person, f) for f in os.listdir(person) if os.path.isfile(os.path.join(person, f))]
        files = files[0:5] 
        for file in files:
            filename = file.split('/')[-1]
            shutil.copyfile(file, newpath + '/' + filename)
            file_list.append(newpath + '/' + filename)
            
        selected_persons[i] = file_list
        i = i + 1

triplets = []

for item in selected_persons.items():
    images = item[1]
    
    for i in range(len(images)-1):
        for j in range(i+1,len(images)):
            anchor = images[i]
            positive = images[j]
            
           
            random_class = item[0]
            while random_class == item[0]:
                random_class = random.randint(0, len(selected_persons)-1)
            
            random_image = random.randint(0, 4)
            negative = selected_persons[random_class][random_image]
            
            triplets.append((anchor, positive, negative))

def preprocess_image(filename):
    image_string = tf.io.read_file(filename)
    image = tf.image.decode_jpeg(image_string, channels = 3)
    image = tf.image.convert_image_dtype(image, tf.float32)
    image = tf.image.resize(image, target_size)
    return image

def plot_images(triplets):
    def show(ax, image):
        ax.imshow(image)
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
    
    fig = plt.figure(figsize=(7,12))
    axis = fig.subplots(5, 3)
    
    for i in range(0,5):
        anchor,positive,negative = triplets[40+i]
        show(axis[i,0], preprocess_image(anchor))
        show(axis[i,1], preprocess_image(positive))
        show(axis[i,2], preprocess_image(negative))

plot_images(triplets)

def preprocess_triplets(anchor, positive, negative):
    

    return (
        preprocess_image(anchor),
        preprocess_image(positive),
        preprocess_image(negative)
    )

rng = np.random.RandomState(seed=101)
rng.shuffle(triplets)

anchor_images = [a_tuple[0] for a_tuple in triplets]
positive_images = [a_tuple[1] for a_tuple in triplets]
negative_images = [a_tuple[2] for a_tuple in triplets]

anchor_dataset = tf.data.Dataset.from_tensor_slices(anchor_images)
positive_dataset = tf.data.Dataset.from_tensor_slices(positive_images)
negative_dataset = tf.data.Dataset.from_tensor_slices(negative_images)

dataset = tf.data.Dataset.zip((anchor_dataset, positive_dataset, negative_dataset))
dataset = dataset.shuffle(buffer_size=1024)
dataset = dataset.map(preprocess_triplets)

training_data = dataset.take(round(image_count * 0.8))
validation_data = dataset.skip(round(image_count * 0.8))

training_data = training_data.batch(32, drop_remainder=False)
training_data = training_data.prefetch(8)

validation_data = validation_data.batch(32, drop_remainder=False)
validation_data = validation_data.prefetch(8)

import time
start_time = time.time()

epochs = 25

siameze_custom_model = SiameseModelClass(siamese_model)
siameze_custom_model.compile(optimizer = optimizers.Adam(0.0001))
siameze_custom_model.fit(training_data, epochs=epochs, validation_data = validation_data)

stop_time = time.time()
print(f'It took {(stop_time - start_time)} to train for {epochs} epochs.')

print(history.history.keys())

#history for loss
plt.plot(history.history['loss'])
plt.plot(history.history['val_loss'])
plt.title('Model loss during training')
plt.ylabel('loss')
plt.xlabel('epoch')
plt.legend(['train', 'validation'], loc='upper left')
plt.show()

#sample plot images
sample = next(iter(training_data))

anchor, positive, negative = sample
anchor_embedding, positive_embedding, negative_embedding = (
    transfer_inception_model(inputs = inception_v3.preprocess_input(anchor)),
    transfer_inception_model(inputs = inception_v3.preprocess_input(positive)),
    transfer_inception_model(inputs = inception_v3.preprocess_input(negative)),
)

d1 = np. sum(np. power((anchor_embedding-positive_embedding),2))
print(f'Anchor-positive difference = {d1}')

d2 = np. sum(np. power((anchor_embedding-negative_embedding),2))
print(f'Anchor-negative difference = {d2}')

#similiarity values
cosine_similarity = metrics.CosineSimilarity()

positive_similarity = cosine_similarity(anchor_embedding, positive_embedding)
print("Positive similarity:", positive_similarity.numpy())

negative_similarity = cosine_similarity(anchor_embedding, negative_embedding)
print("Negative similarity", negative_similarity.numpy())