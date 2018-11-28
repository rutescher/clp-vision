# coding: utf-8
from __future__ import division
import os
import scipy.io
import numpy as np
import datetime
import matplotlib.pyplot as plt
import matplotlib
from PIL import Image as PImage


icorpus_code = {
    'saiapr': 0,           # the original SAIAPR corpus; original regions
    'mscoco': 1,           # MSCOCO; original bounding boxes
    'saiapr_berkeley': 2,  # SAIAPR, with berkeley region proposals
    'mscoco_grprops': 3,   # MSCOCO, region proposals as per google refexp
    'image_net': 4,        # ImageNet; with bbs
    'visual_genome': 5,    # VG, images and regions from visual genome
    'ade_20k': 6,          # ADE, images from ade 20k corpus
    'tingdataset': 7,  # https://tingh.github.io/resources/object_description
    'flickr_30k': 8,   # flickr 30k Entities
    'cub_birds': 9     # http://www.vision.caltech.edu/visipedia/CUB-200-2011.html
    }

code_icorpus = {item: key for key, item in icorpus_code.items()}


def print_timestamped_message(message, indent=0):
    now = datetime.datetime.now().strftime('%Y-%m-%d @ %H:%M:%S')
    print ' ' * indent, '[ %s ] %s' % (now, message)


def saiapr_basepath(image_id):
    '''return the basepath for an SAIAPR image, given the image ID'''
    if len(str(image_id)) == 5:
        directory = str(image_id)[:2]
    elif len(str(image_id)) == 4:
        directory = '0' + str(image_id)[0]
    else:
        directory = '00'
    return directory


def saiapr_image_filename(config, image_id):
    '''return the path of a SAIAPR image, given the image ID'''
    directory = saiapr_basepath(image_id)
    return config.get('SAIAPR', 'saiapr_img_base') + '/' + \
        directory + '/images/' + str(image_id) + '.jpg'


def saiapr_mask_filename(config, image_id, region_id):
    '''return the path of a SAIAPR mask, given the image ID and region ID'''
    directory = saiapr_basepath(image_id)
    return config.get('SAIAPR', 'saiapr_img_base') +\
        '/' + directory + '/segmentation_masks/' + \
        str(image_id) + '_' + str(region_id) + '.mat'


def get_saiapr_bb(config, image_id, region_id):
    '''get the bounding box of an SAIAPR region, given image and region IDs'''
    mask_path = saiapr_mask_filename(config, image_id, region_id)
    # print mask_path
    mask = scipy.io.loadmat(mask_path)
    mask = mask['segimg_t']
    mask = mask + 1
    x1, y1 = np.nonzero(mask)[1].min(), np.nonzero(mask)[0].min()
    x2, y2 = np.nonzero(mask)[1].max(), np.nonzero(mask)[0].max()
    return [x1, y1, x2-x1, y2-y1]


def mscoco_image_filename(config, image_id):
    '''get the image path for an MSCOCO image (from train2014),
       given the ID'''
    mscoco_basedir = config.get('MSCOCO', 'mscoco_base') + '/train2014'
    return os.path.join(mscoco_basedir, 'COCO_train2014_%012d.jpg' % (image_id))


def visgen_image_filename(config, image_id):
    visgen_image_root = config.get('VISGEN', 'visgen_12') + '/images'
    file_base = '%d.jpg' % (image_id)
    full_path = visgen_image_root + '/VG_100K/' + file_base
    if not os.path.isfile(full_path):
        return visgen_image_root + '/VG_100K_2/' + file_base
    return full_path


def flickr_image_filename(config, image_id):
    flickr_image_root = config.get('FLICKR', 'flickr_images')
    return flickr_image_root + '/' + str(image_id) + '.jpg'


def join_imagenet_id(image_id, region_id):
    return 'n%08d_%d' % (image_id, region_id)

def birds_filename(config, image_path):
    bird_image_root = config.get('CUB_BIRDS', 'birds_images')
    return bird_image_root + '/' + image_path

def get_image_filename(config, icorp, image_id):
    if 'saiapr' in code_icorpus[icorp]:
        return saiapr_image_filename(config, image_id)
    if 'mscoco' in code_icorpus[icorp]:
        return mscoco_image_filename(config, image_id)
    if code_icorpus[icorp] == 'visual_genome':
        return visgen_image_filename(config, image_id)
    if code_icorpus[icorp] == 'flickr_30k':
        return flickr_image_filename(config, image_id)
    if code_icorpus[icorp] == 'cub_birds':
        return birds_filename(config, image_id)
    raise ValueError('Unknown corpus code')


def get_image_part(config, (prev_image_id, img), i_corpus, image_id, bb,
                   resize=True,
                   xs=224, ys=224):
    if prev_image_id != image_id:
        this_path = get_image_filename(config, i_corpus, image_id)
        img = plt.imread(this_path)

    if bb is None:
        img_cropped = img
    else:
        # need to clip bounding box to 0, because the google region
        #   weirdly sometimes have negative coordinates (?!):
        x, y, w, h = np.clip(np.array(bb), 0, np.max(img.shape))
        w = img.shape[1]-x if x+w >= img.shape[1] else w
        h = img.shape[0]-y if y+h >= img.shape[0] else h
        # print 'after', x,y,w,h,
        img_cropped = img[int(y):int(y+h), int(x):int(x+w)]

    if resize:
        pim = PImage.fromarray(img_cropped)
        pim2 = pim.resize((xs, ys), PImage.ANTIALIAS)
        img_resized = np.array(pim2)
    else:
        img_resized = img_cropped
    return ((image_id, img), img_resized)


def plot_labelled_bb(impath, bblist, title=None, text_size='large',
                     mode='path', omode='screen', opath=None):
    '''Given the path of an image and a list containing tuples
    of bounding box (a list of x,y,w,h) and label info,
    plot these boxes and labels into the image.
    Label info can be tuple, in which case it is interpreted as
    (label, colour); otherwise it has to be just a string (the label).
    If mode is path, impath is path, if it is image, impath is the actual
    image on top of which the bbs are to be drawn.
    If omode is screen, assumption is that matplotlib functions are
    displayed directly (i.e., IPython inline mode), if it is
    img, function saves the plot to opath.'''

    if mode == 'path':
        img = plt.imread(impath)
    elif mode == 'img':
        img = impath

    fig, ax = plt.subplots()
    fig.set_size_inches(10, 20)
    ax.imshow(img)

    if bblist is not None:
        for (this_bb, this_label) in bblist:
            x, y, w, h = this_bb

            if type(this_label) == tuple:
                edgecolor = this_label[1]
                this_label = this_label[0]
            else:
                edgecolor = 'r'
            ax.add_patch(
                matplotlib.patches.Rectangle(
                    (x, y),
                    w,
                    h,
                    edgecolor=edgecolor,
                    fill=False, linewidth=4
                )
            )
            if this_label != '':
                ax.text(x, y, this_label, size=text_size, style='italic',
                        bbox={'facecolor': 'white', 'alpha': 0.7, 'pad': 10})
    if title is not None:
        ax.set_title(title)
    ax.axis('off')

    if omode == 'img':
        fig.savefig(opath, bbox_inches='tight', pad_inches=0)
        plt.close()  # to supress showing the plot in interactive mode


def plot_img_cropped(impath, this_bb, title=None, text_size='large',
                     mode='path', omode='screen', opath=None):
    if mode == 'path':
        img = plt.imread(impath)
    elif mode == 'img':
        img = impath

    fig, ax = plt.subplots()
    fig.set_size_inches(10, 20)

    x, y, w, h = this_bb

    img_cropped = img[y:y+h, x:x+w]

    ax.imshow(img_cropped)

    if omode == 'img':
        fig.savefig(opath, bbox_inches='tight', pad_inches=0)
        plt.close()  # to supress showing the plot in interactive mode

    return img_cropped
