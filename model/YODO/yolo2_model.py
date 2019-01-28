import numpy as np
from keras import backend as K
from keras.layers import Input, Lambda, Conv2D
from keras.models import Model

from yad2k.models.keras_yolo import (preprocess_true_boxes, yolo_body,
                                     yolo_eval, yolo_head, yolo_loss)

def load_anchors(anchors_file):
    anchors = None
    with open(anchors_file) as f:
        anchors = f.readline()
        anchors = [float(x) for x in anchors.split(',')]
        anchors = np.array(anchors).reshape(-1, 2)

    return anchors

def load_classes(class_file):
    classes = None
    with open(class_file, 'r') as f:
        classes = [line.strip() for line in f.readlines()]

    return classes

def create_model(anchors, class_names):
    image_size = 416
    image_deep = 3
    detectors_mask_shape = (13, 13, 5, 1)
    matching_boxes_shape = (13, 13, 5, 5)

    # Create model input layers.
    image_input = Input(shape=(image_size, image_size, image_deep))
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

    model_loss = Lambda(
        yolo_loss,
        output_shape=(1,),
        name='yolo_loss',
        arguments={'anchors': anchors,
                   'num_classes': len(class_names)})([model_body.output,
                                                      boxes_input,
                                                      detectors_mask_input,
                                                      matching_boxes_input])

    model = Model([model_body.input, boxes_input, detectors_mask_input, matching_boxes_input],
                  model_loss)

    return model_body, model

def build_model(weight_file, config_file, class_names):
    anchors = load_anchors(config_file)

    yolo_model, model = create_model(anchors, class_names)
    yolo_model.load_weights(weight_file)

    num_classes = len(class_names)
    num_anchors = len(anchors)
    print('Class Anchor:', num_classes, num_anchors)
    print('Class:', class_names[0], class_names[1], class_names[2], class_names[3])
    print('anchors:', anchors[0], anchors[1], anchors[2], anchors[3], anchors[4])

    model_output_channels = yolo_model.layers[-1].output_shape[-1]
    assert model_output_channels == num_anchors * (num_classes + 5), \
        'Mismatch between model and given anchor and class sizes.'
    print('{} model, anchors, and classes loaded.'.format(weight_file))

    yolo_outputs = yolo_head(yolo_model.output, anchors, len(class_names))
    input_image_shape = K.placeholder(shape=(2,))
    boxes, scores, classes = yolo_eval(
        yolo_outputs,
        input_image_shape,
        score_threshold=0.3,
        iou_threshold=0.5)

    ts_parm = [input_image_shape, boxes, scores, classes]

    return yolo_model, ts_parm

def detect_object(sess, yolo_model, ts_parm, class_names, image):
    image_size = 416
    # threshold = 0.3
    result = [[0,0.],[1,0.],[2,0.],[3,0.]]

    input_image_shape = ts_parm[0]
    boxes = ts_parm[1]
    scores = ts_parm[2]
    classes = ts_parm[3]

    image_data = np.array(image, dtype='float32')
    image_data /= 255.
    image_data = np.expand_dims(image_data, 0)

    out_boxes, out_scores, out_classes = sess.run(
        [boxes, scores, classes],
        feed_dict={
            yolo_model.input: image_data,
            input_image_shape: [image_size, image_size],
            K.learning_phase(): 0})

    print('Found {} objects in the image'.format(len(out_boxes)))

    for i, c in reversed(list(enumerate(out_classes))):        
        predicted_class = class_names[c]
        # box = out_boxes[i]
        score = out_scores[i]
        
        # label = '\t{} {:.2f}'.format(predicted_class, score)
        # print(label)

        # if score > result[c][1] and score > threshold:
        if score > result[c][1]:
            result[c][1] = score

    return result
