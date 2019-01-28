import argparse
import colorsys
import imghdr
import os
import random

import numpy as np
from keras import backend as K
from keras.layers import Input, Lambda, Conv2D
from keras.models import load_model, Model
from PIL import Image, ImageDraw, ImageFont
import tensorflow as tf

from yad2k.models.keras_yolo import (preprocess_true_boxes, yolo_body,
                                     yolo_eval, yolo_head, yolo_loss)

parser = argparse.ArgumentParser(
    description='Run a YOLO_v2 style detection model on test images..')
parser.add_argument(
    '-w',
    '--weights_path',
    help='path to h5 weights of a YOLO_v2 model',
    default='./trained_stage_2_best.h5')
parser.add_argument(
    '-a',
    '--anchors_path',
    help='path to anchors file, defaults to yolo_anchors.txt',
    default='/home/jovyan/at073-group49/model_data/yolo_anchors.txt')
parser.add_argument(
    '-c',
    '--classes_path',
    help='path to classes file, defaults to class_list.txt',
    default='/home/jovyan/at073-group49/AT073_49_Orig_Trash/data/class_list.txt')
parser.add_argument(
    '-t',
    '--test_path',
    help='path to directory of test images, defaults to test_img/',
#     default='/home/jovyan/at073-group49/AT073_49_Orig_Trash/data/Chien/images')
    default='/home/jovyan/at073-group49/AT073_49_Orig_Trash/data/Test')
#     default='./test_img')
parser.add_argument(
    '-o',
    '--output_path',
    help='path to output test images, defaults to output_images/',
    default='./output_images')
parser.add_argument(
    '-s',
    '--score_threshold',
    type=float,
    help='threshold for bounding box scores, default .3',
    default=.3)
parser.add_argument(
    '-iou',
    '--iou_threshold',
    type=float,
    help='threshold for non max suppression IOU, default .5',
    default=.5)

def create_model(anchors, class_names):
    detectors_mask_shape = (13, 13, 5, 1)
    matching_boxes_shape = (13, 13, 5, 5)

    # Create model input layers.
    image_input = Input(shape=(416, 416, 3))
    boxes_input = Input(shape=(None, 5))
    detectors_mask_input = Input(shape=detectors_mask_shape)
    matching_boxes_input = Input(shape=matching_boxes_shape)

    # Create model body.
    yolo_model = yolo_body(image_input, len(anchors), len(class_names))
    topless_yolo = Model(yolo_model.input, yolo_model.layers[-2].output)
            
    final_layer = Conv2D(len(anchors)*(5+len(class_names)),
                         (1, 1),
                         activation='linear')(topless_yolo.output)

    model_body = Model(image_input, final_layer)

    # Place model loss on CPU to reduce GPU memory usage.
    with tf.device('/cpu:0'):
        # TODO: Replace Lambda with custom Keras layer for loss.
        model_loss = Lambda(
            yolo_loss,
            output_shape=(1, ),
            name='yolo_loss',
            arguments={'anchors': anchors,
                       'num_classes': len(class_names)})([model_body.output,
                                                          boxes_input,
                                                          detectors_mask_input,
                                                          matching_boxes_input])

    model = Model([model_body.input, boxes_input, detectors_mask_input, matching_boxes_input],
                  model_loss)

    return model_body, model

def _main(args):
    weights_path = os.path.expanduser(args.weights_path)
    assert weights_path.endswith('.h5'), 'Keras model must be a .h5 file.'
    anchors_path = os.path.expanduser(args.anchors_path)
    classes_path = os.path.expanduser(args.classes_path)
    test_path = os.path.expanduser(args.test_path)
    output_path = os.path.expanduser(args.output_path)

    if not os.path.exists(output_path):
        print('Creating output path {}'.format(output_path))
        os.mkdir(output_path)

    sess = K.get_session()

    with open(classes_path) as f:
        class_names = f.readlines()
    class_names = [c.strip() for c in class_names]

    with open(anchors_path) as f:
        anchors = f.readline()
        anchors = [float(x) for x in anchors.split(',')]
        anchors = np.array(anchors).reshape(-1, 2)

    # yolo_model = load_model(model_path)
    yolo_model, model = create_model(anchors, class_names)
    yolo_model.load_weights(weights_path)

    # Verify model, anchors, and classes are compatible
    num_classes = len(class_names)
    num_anchors = len(anchors)
    print('Class Anchor:', num_classes, num_anchors)
    
    # TODO: Assumes dim ordering is channel last
    model_output_channels = yolo_model.layers[-1].output_shape[-1]
    assert model_output_channels == num_anchors * (num_classes + 5), \
        'Mismatch between model and given anchor and class sizes. ' \
        'Specify matching anchors and classes with --anchors_path and ' \
        '--classes_path flags.'
    print('{} model, anchors, and classes loaded.'.format(weights_path))
    
    # Check if model is fully convolutional, assuming channel last order.
    model_image_size = yolo_model.layers[0].input_shape[1:3]

    # Generate colors for drawing bounding boxes.
#     hsv_tuples = [(x / len(class_names), 1., 1.)
#                   for x in range(len(class_names))]
#     colors = list(map(lambda x: colorsys.hsv_to_rgb(*x), hsv_tuples))
#     colors = list(
#         map(lambda x: (int(x[0] * 255), int(x[1] * 255), int(x[2] * 255)), colors))
#     random.seed(10101)  # Fixed seed for consistent colors across runs.
#     random.shuffle(colors)  # Shuffle colors to decorrelate adjacent classes.
#     random.seed(None)  # Reset seed to default.

    # Generate output tensor targets for filtered bounding boxes.
    # TODO: Wrap these backend operations with Keras layers.
    yolo_outputs = yolo_head(yolo_model.output, anchors, len(class_names))
    input_image_shape = K.placeholder(shape=(2, ))
    boxes, scores, classes = yolo_eval(
        yolo_outputs,
        input_image_shape,
        score_threshold=args.score_threshold,
        iou_threshold=args.iou_threshold)
    
    output_results = []
    for image_file in os.listdir(test_path):
        try:
            image_type = imghdr.what(os.path.join(test_path, image_file))
            if not image_type:
                continue
        except IsADirectoryError:
            continue

        image = Image.open(os.path.join(test_path, image_file))
        resized_image = image.resize(tuple(reversed(model_image_size)), Image.BICUBIC)
        image_data = np.array(resized_image, dtype='float32')

        image_data /= 255.
        image_data = np.expand_dims(image_data, 0)  # Add batch dimension.
        
        out_boxes, out_scores, out_classes = sess.run(
            [boxes, scores, classes],
            feed_dict={
                yolo_model.input: image_data,
                input_image_shape: [image.size[1], image.size[0]],
                K.learning_phase(): 0})
        
        print('Found {} boxes for {}'.format(len(out_boxes), image_file))

#         font = ImageFont.truetype(
#             font='font/FiraMono-Medium.otf',
#             size=np.floor(3e-2 * image.size[1] + 0.5).astype('int32'))
#         thickness = (image.size[0] + image.size[1]) // 300

        detected = []
        for i, c in reversed(list(enumerate(out_classes))):
            predicted_class = class_names[c]
            box = out_boxes[i]
            score = out_scores[i]

            label = '{} {:.2f}'.format(predicted_class, score)
            print('Label=', label)

#             draw = ImageDraw.Draw(image)
#             label_size = draw.textsize(label, font)

#             top, left, bottom, right = box
#             top = max(0, np.floor(top + 0.5).astype('int32'))
#             left = max(0, np.floor(left + 0.5).astype('int32'))
#             bottom = min(image.size[1], np.floor(bottom + 0.5).astype('int32'))
#             right = min(image.size[0], np.floor(right + 0.5).astype('int32'))
#             print(label, (left, top), (right, bottom))

#             if top - label_size[1] >= 0:
#                 text_origin = np.array([left, top - label_size[1]])
#             else:
#                 text_origin = np.array([left, top + 1])

            # draw boxes and label
#             for i in range(thickness):
#                 draw.rectangle(
#                     [left + i, top + i, right - i, bottom - i],
#                     outline=colors[c])
#             draw.rectangle(
#                 [tuple(text_origin), tuple(text_origin + label_size)],
#                 fill=colors[c])
#             draw.text(text_origin, label, fill=(0, 0, 0), font=font)
#             del draw
            
#             detected.append([label, (left, top, right, bottom)])
#         image.save(os.path.join(output_path, image_file), quality=90)
#         output_results.append([image, detected])
            
#     return list(zip(*output_results))

if __name__ == '__main__':
    _main(parser.parse_args())
