from __future__ import absolute_import, division, print_function
from .utils import *
from .init_paths import *

import argparse
import importlib
import itertools
import matplotlib

matplotlib.use('Agg')
import time
import numpy as np
import os
import pdb
import pickle
import subprocess
import sys
import tensorflow as tf
import tensorflow.contrib.slim as slim
import threading
import scipy.misc

import scipy
import skimage
import skimage.io
import transforms3d
import math
import matplotlib.pyplot as plt
import random
import models.architectures as architectures
import lib.data.load_ops as load_ops
from multiprocessing import Pool
from skimage import color
from models.sample_models import *
from lib.data.synset import *
from PIL import Image, ImageDraw, ImageFont
from .task_viz import *
from data.load_ops import resize_rescale_image
from data.load_ops import rescale_image



tf.logging.set_verbosity(tf.logging.ERROR)

list_of_tasks = 'ego_motion \
fix_pose \
non_fixated_pose '
list_of_tasks = list_of_tasks.split()


def generate_cfg(task):
    repo_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    CONFIG_DIR = os.path.join(repo_dir, 'experiments/final', task)
    # Load Configs #
    #import utils
    import data.load_ops as load_ops
    from general_utils import RuntimeDeterminedEnviromentVars
    cfg = load_config(CONFIG_DIR, nopause=True)
    RuntimeDeterminedEnviromentVars.register_dict(cfg)
    cfg['batch_size'] = 1
    if 'batch_size' in cfg['encoder_kwargs']:
        cfg['encoder_kwargs']['batch_size'] = 1
    cfg['model_path'] = os.path.join(repo_dir, 'temp', task, 'model.permanent-ckpt')
    cfg['root_dir'] = repo_dir
    return cfg




def run_to_tasks(task=None, imgs='', store_rep=False, store_pred=False,
                store_name=None):
    if imgs:
        imgs=imgs.split(',')
    import general_utils
    from general_utils import RuntimeDeterminedEnviromentVars
    tf.logging.set_verbosity(tf.logging.ERROR)

    if task == 'ego_motion' and len(imgs) != 3:
        raise ValueError('Wrong number of images, expecting 3 but got {}'.format(len(imgs)))
    if task != 'ego_motion' and len(imgs) != 2:
        raise ValueError('Wrong number of images, expecting 2 but got {}'.format(len(imgs)))

    if task not in list_of_tasks:
        raise ValueError('Task not supported')

    cfg = generate_cfg(task)

    input_img = np.empty((len(imgs), 256, 256, 3), dtype=np.float32)
    for i, imname in enumerate(imgs):
        img = load_raw_image_center_crop(imname)
        img = skimage.img_as_float(img)
        scipy.misc.toimage(np.squeeze(img), cmin=0.0, cmax=1.0).save(imname)
        img = cfg['input_preprocessing_fn'](img, **cfg['input_preprocessing_fn_kwargs'])
        input_img[i, :, :, :] = img
    input_img = input_img[np.newaxis, :]

    print("Doing {task}".format(task=task))
    general_utils = importlib.reload(general_utils)
    tf.reset_default_graph()
    training_runners = {'sess': tf.InteractiveSession(), 'coord': tf.train.Coordinator()}

    # Set Up Inputs #
    # tf.logging.set_verbosity( tf.logging.INFO )
    setup_input_fn = setup_input
    inputs = setup_input_fn(cfg, is_training=False, use_filename_queue=False)
    RuntimeDeterminedEnviromentVars.load_dynamic_variables(inputs, cfg)
    RuntimeDeterminedEnviromentVars.populate_registered_variables()
    start_time = time.time()

    # Set Up Model #
    model = setup_model(inputs, cfg, is_training=False)
    m = model['model']
    model['saver_op'].restore(training_runners['sess'], cfg['model_path'])

    predicted, representation = training_runners['sess'].run(
        [m.decoder_output, m.encoder_output], feed_dict={m.input_images: input_img})

    if store_rep:
        s_name, file_extension = os.path.splitext(store_name)
        with open('{}.npy'.format(s_name), 'wb') as fp:
            np.save(fp, np.squeeze(representation))

    if store_pred:
        s_name, file_extension = os.path.splitext(store_name)
        with open('{}_pred.npy'.format(s_name), 'wb') as fp:
            np.save(fp, np.squeeze(predicted))

    if task == 'ego_motion':
        ego_motion(predicted, store_name)
        return
    if task == 'fix_pose':
        cam_pose(predicted, store_name, is_fixated=True)
        return
    if task == 'non_fixated_pose':
        cam_pose(predicted, store_name, is_fixated=False)
        return

        # Clean Up #
    training_runners['coord'].request_stop()
    training_runners['coord'].join()
    print("Done: {}".format(config_name))

    # Reset graph and paths #
    tf.reset_default_graph()
    training_runners['sess'].close()
    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Viz Single Task')

    parser.add_argument('--task', dest='task')
    parser.set_defaults(task='NONE')

    parser.add_argument('--img', dest='im_name')
    parser.set_defaults(im_name='NONE')

    parser.add_argument('--store', dest='store_name')
    parser.set_defaults(store_name='NONE')

    parser.add_argument('--store-rep', dest='store_rep', action='store_true')
    parser.set_defaults(store_rep=False)

    parser.add_argument('--store-pred', dest='store_pred', action='store_true')
    parser.set_defaults(store_pred=False)

    parser.add_argument('--on-screen', dest='on_screen', action='store_true')
    parser.set_defaults(on_screen=False)
    args = parser.parse_args()

    run_to_tasks()
