import os
import sys
import glob
import argparse

from keras import __version__
from keras.applications.inception_v3 import InceptionV3, preprocess_input
from keras.models import Model
from keras.layers import Dense, GlobalAveragePooling2D
from keras.preprocessing.image import ImageDataGenerator
from keras.optimizers import rmsprop
from keras.callbacks import TensorBoard
from keras.optimizers import SGD

IM_WIDTH, IM_HEIGHT = 299, 299 #fixed size for InceptionV3
NB_EPOCHS = 1
BAT_SIZE = 32
FC_SIZE = 1024
NB_IV3_LAYERS_TO_FREEZE = 172
#RUN NAME

from keras.callbacks import TensorBoard

#If running on google cloud, copy locally and reset the arguments
def download(args):
    if args.train_dir[0:2]=="gs":   
        subprocess.check_call(['gsutil', '-m' , 'cp', '-r', args.train_dir, '/tmp/train'])
        subprocess.check_call(['gsutil', '-m' , 'cp', '-r', args.val_dir, '/tmp/val'])
        args.train_dir='/tmp/train'
        args.val_dir='/tmp/val'

def get_nb_files(directory):
    """Get number of files by searching directory recursively"""
    if not os.path.exists(directory):
        return 0
    cnt = 0
    for r, dirs, files in os.walk(directory):
        for dr in dirs:
            cnt += len(glob.glob(os.path.join(r, dr + "/*")))
    return cnt

def add_new_last_layer(base_model, nb_classes=2):
    """Add last layer to the convnet

    Args:
      base_model: keras model excluding top
      nb_classes: # of classes

    Returns:
      new keras model with last layer
    """
    x = base_model.output
    x = GlobalAveragePooling2D()(x)
    x = Dense(FC_SIZE, activation='relu')(x) #new FC layer, random init
    predictions = Dense(2, activation='softmax')(x) #new output layer
    #TODO xDropout
    model = Model(input=base_model.input, output=predictions)
    return model

def setup_to_finetune(model):
    """Freeze the bottom NB_IV3_LAYERS and retrain the remaining top layers.

    note: NB_IV3_LAYERS corresponds to the top 2 inception blocks in the inceptionv3 arch

    Args:
      model: keras model
    """
    for layer in model.layers[:NB_IV3_LAYERS_TO_FREEZE]:
        layer.trainable = False
    for layer in model.layers[NB_IV3_LAYERS_TO_FREEZE:]:
        layer.trainable = True
    model.compile(optimizer=SGD(lr=0.0001, momentum=0.9), loss='categorical_crossentropy', metrics=['accuracy'])

def setup_to_transfer_learn(model, base_model):
    """Freeze all layers and compile the model"""
    for layer in base_model.layers:
        layer.trainable = False
    model.compile(optimizer='rmsprop',    
                loss='categorical_crossentropy', 
                metrics=['accuracy'])
    
def train(args):
    """Use fine-tuning to train a network on a new dataset"""
    nb_train_samples = get_nb_files(args.train_dir)
    nb_classes = len(glob.glob(args.train_dir + "/*"))
    nb_val_samples = get_nb_files(args.val_dir)
    nb_epoch = int(args.nb_epoch)
    batch_size = int(args.batch_size)
        
    # data prep
    #TODO update to new keras 2
    train_datagen =  ImageDataGenerator(
      preprocessing_function=preprocess_input,
      rotation_range=30,
      width_shift_range=0.2,
      height_shift_range=0.2,
      shear_range=0.2,
      zoom_range=0.2,
      horizontal_flip=True
  )
    test_datagen = ImageDataGenerator(
      preprocessing_function=preprocess_input,
      rotation_range=30,
      width_shift_range=0.2,
      height_shift_range=0.2,
      shear_range=0.2,
      zoom_range=0.2,
      horizontal_flip=True
  )

    train_generator = train_datagen.flow_from_directory(
      args.train_dir,
    target_size=(IM_WIDTH, IM_HEIGHT),
    batch_size=batch_size,
  )

    validation_generator = test_datagen.flow_from_directory(
      args.val_dir,
    target_size=(IM_WIDTH, IM_HEIGHT),
    batch_size=batch_size,
  )

    # setup model
    base_model = InceptionV3(weights='imagenet', include_top=False) #include_top=False excludes final FC layer
    model = add_new_last_layer(base_model, nb_classes)

    #transfer learning initial layers
    setup_to_transfer_learn(model, base_model)
    
    # fine-tuning layers 
    setup_to_finetune(model)
    
    #Tensorboard Callback
    tbcallback=TensorBoard(log_dir='./logs', histogram_freq=0, batch_size=32, write_graph=True, write_grads=False, write_images=False, embeddings_freq=0, embeddings_layer_names=None, embeddings_metadata=None)        
    
    #TODO alter class weights
    #from sklearn.utils import class_weight
    #class_weight = class_weight.compute_class_weight('balanced',np.unique(Y_train),Y_train)
    
    history_ft = model.fit_generator(
      train_generator,
    #samples_per_epoch=nb_train_samples/BAT_SIZE,
    steps_per_epoch=10,    
    nb_epoch=nb_epoch,
    validation_data=validation_generator,
    #validation_steps=nb_val_samples/BAT_SIZE,
    validation_steps=10,    
    class_weight='auto',
    callbacks=[tbcallback])
    
    #TODO, saved model loader type?
    model.save(args.output_model_file)

if __name__=="__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--train_dir",default="/Users/ben/Dropbox/GoogleCloud/Training/")
    a.add_argument("--val_dir",default="/Users/ben/Dropbox/GoogleCloud/Testing/")
    a.add_argument("--nb_epoch", default=NB_EPOCHS)
    a.add_argument("--batch_size", default=BAT_SIZE)
    a.add_argument("--output_model_file", default="inceptionv3-ft.model")

    args = a.parse_args()
    if args.train_dir is None or args.val_dir is None:
        a.print_help()
        sys.exit(1)

    if (not os.path.exists(args.train_dir)) or (not os.path.exists(args.val_dir)):
        print("directories do not exist")
        sys.exit(1)
        
if __name__=="__main__":
    #Check if running on google cloud
    download(args)
    
    #Run model
    train(args)
    