"""
This script is an automated tool for data augmentation.
It mainly deals with the images in folder: ./dd2419_coco

Download dependencies:
pip install albumentations -U

Tested with Python 3.6.9 and PyTorch 1.4.0
"""

import os
import json
import random
from abc import ABC, abstractmethod

import cv2
import albumentations as A

# NOTE: using 'pip install albumentations -U' may not download the latest version?
# How to import `Rotate` depends on the version.
from albumentations.augmentations.transforms import Rotate

from config import NUM_CATEGORIES, CATEGORY_DICT, IMG_W, IMG_H


# check data set before augmentation!
IMAGE_ID_START = 1258    # beginning image_id of new images
ID_START = 1257     # beginning id of new annotations

# data augmentation config
MIN_VIS = 0.9
DUP_TIMES = 20  # duplicate and transform how many times for each image
BBOX_PARAM = A.BboxParams(
    format="coco", min_visibility=MIN_VIS, label_fields=["class_labels"]
)
# NOTE: `min_visibility` ensures that the bbox is not lost.
# `label_fields` will be an argument when using this transform

# path
COVER_OLD = False   # cover the original file or not
ANN_PATH = "dd2419_coco/annotations/training.json"
IMG_PATH = "dd2419_coco/training/"
if COVER_OLD:
    NEW_ANN_PATH = ANN_PATH
    NEW_IMG_PATH = IMG_PATH
else:
    NEW_ANN_PATH = "dd2419_coco/annotations/training_new.json"
    NEW_IMG_PATH = "dd2419_coco/training_new/"  # save in a new folder and will merge later


class Strategy(ABC):
    """
    Strategies for different combinations of transforms.
    Each strategy contains a transform.
    If a new strategy is needed, a derived class should be implemented.
    """

    def __init__(self, strategy_name):
        self.strategy_name = strategy_name

    @abstractmethod
    def get_transform(self):
        pass


class AllTransform(Strategy):
    """
    A derived class of `Strategy`, performing all kinds of transforms.
    """

    def __init__(self, strategy_name="AllTransform"):
        super().__init__(strategy_name)
        self.__transforms = [
            A.RandomSizedBBoxSafeCrop(width=IMG_W, height=IMG_H, p=0.5),
            A.HorizontalFlip(p=0.2),
            A.VerticalFlip(p=0.2),
            A.RandomBrightnessContrast(p=0.2),
            Rotate(limit=(-10, 10), p=0.2),
            A.Blur(p=0.2),
            A.ColorJitter(p=0.2),
            A.GaussNoise(p=0.2),
        ]
        random.shuffle(self.__transforms)

    def get_transform(self):
        return A.Compose(
            self.__transforms,
            bbox_params=BBOX_PARAM,
        )


class NoFlip(Strategy):
    """
    A derived class of `Strategy`, whose object does not flip images.
    """

    def __init__(self, strategy_name="NoFlip"):
        super.__init__(strategy_name)
        self.__transforms = [
            A.RandomSizedBBoxSafeCrop(width=IMG_W, height=IMG_H, p=0.5),
            A.RandomBrightnessContrast(p=0.2),
            Rotate(limit=(-10, 10), p=0.3),
            A.Blur(p=0.2),
            A.ColorJitter(p=0.3),
            A.GaussNoise(p=0.2),
        ]
        random.shuffle(self.__transforms)

    def get_transform(self):
        return A.Compose(
            self.__transforms,
            bbox_params=BBOX_PARAM,
        )


class DataAugmentation:
    """
    A class for image data augmentation.
    """

    def __init__(self, dup_times=DUP_TIMES):
        self.dup_times = dup_times

        self.images = []        # transformed images: a list of numpy.ndarray
        self.data = {}          # store original json
        self.new_data = {}      # store new json
        self.annotations = []   # store the annotation list of original json
        self.images_json = []   # store new image data
        self.ann_json = []      # store new annotation data

        self.image_id = IMAGE_ID_START  # new image_id of ann = id of image
        self.idx = ID_START # new id of ann

    def update_id(self):
        """
        Update idx and image_id
        """
        self.image_id = self.image_id + 1
        self.idx = self.idx + 1

    def read(self, path):
        """
        Read annotations.
        """
        with open(path) as json_file:
            self.data = json.load(json_file)
            self.annotations = self.data["annotations"]

    @staticmethod
    def label2strategy(label):
        """
        Get a Strategy object depending on the given label.
        Args:
            label: int
        Returns: a Strategy object
        """
        if label in [2, 11, 12]:
            # TODO: more labels after data collection of missing classes
            return NoFlip()
        else:
            return AllTransform()

    @staticmethod
    def show_image_array(img, bboxes=None, labels=None):
        """
        Show image with the bounding box.
        Args:
            img: numpy.ndarray
            bboxes: list of tuples
            labels: list of int
        """

        # add bounding box or not
        if bboxes is not None and labels is not None:
            # single input case
            if type(labels) is int:
                labels = [labels]
                bboxes = [bboxes]

            # the length should match
            assert len(bboxes) == len(labels)

            for idx in range(len(bboxes)):
                bbox = bboxes[idx]
                lbl = labels[idx]
                bbox = list(map(int, bbox))
                start_point = (bbox[0], bbox[1])
                text_point = (bbox[0], bbox[1] - 5)
                end_point = (bbox[0] + bbox[2], bbox[1] + bbox[3])
                cv2.rectangle(img, start_point, end_point, (0, 0, 255), 2)
                cv2.putText(
                    img,
                    CATEGORY_DICT[lbl]["name"],
                    text_point,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 0, 0),
                    2,
                    cv2.LINE_AA,
                )

        cv2.imshow("show image", img)
        cv2.waitKey()
        cv2.destroyAllWindows()

    def augment(self, debug=False):
        """
        Do data augmentation.
        Args:
            debug: In debug mode, only one image is used and shown.
        """

        # check annotations and corresponding images
        for idx in range(len(self.annotations)):
            # NOTE: `idx == image_id` does not always hold.
            image_id = self.annotations[idx]['image_id']
            idx_str = "%06d" % image_id  # pad zero
            img_path = IMG_PATH + idx_str + ".jpg"
            image = cv2.imread(img_path)
            bbox = self.annotations[idx]["bbox"]
            label = self.annotations[idx]["category_id"]
            # label_str = str(label)

            for _ in range(self.dup_times):
                # generate a new image
                strategy = DataAugmentation.label2strategy(label)
                transform = strategy.get_transform()

                # use pipeline to transform
                transformed = transform(
                    image=image, bboxes=[bbox], class_labels=[label]
                )
                image_transformed = transformed["image"]  # ndarray, (W, H, C=3)
                bbox_transformed = transformed["bboxes"]
                label_transformed = transformed["class_labels"]
                self.images.append(image_transformed)

                # store annotation json
                # TODO: update 'id' and 'image_id'
                # example:
                # json['images']  {'id': 0, 'width': 640, 'height': 480, 'file_name': '000000.jpg'}
                # json['annotations'] {'id': 0, 'image_id': 0, 'category_id': 0, 'bbox': [325, 192, 68, 65]}

                self.ann_json.append({'id': self.idx, 'image_id': self.image_id, 'category_id': label_transformed[0],
                                      'bbox': list(bbox_transformed[0])})
                self.update_id()

            if debug:
                DataAugmentation.show_image_array(
                    image_transformed.copy(), bbox_transformed, label_transformed
                )
                break

    def write_image(self):
        """
        Save images.
        """
        object_dir = os.getcwd() + "/" + NEW_IMG_PATH
        if not os.path.exists(object_dir):
            os.makedirs("/" + NEW_IMG_PATH)
        for idx, img in enumerate(self.images):
            save_path = NEW_IMG_PATH + "new" + str(idx) + ".jpg"
            # save image in the correct directory
            cv2.imwrite(save_path, img)

            # store image json
            # TODO: update 'id' (image_id)
            self.images_json.append({'id': self.ann_json[idx]['image_id'], 'width': 640, 'height': 480,
                                     'file_name': "new" + str(idx) + ".jpg"})

    def update_json(self):
        """
        Merge new json data into the original one.
        Only 'images' and 'annotations' in 'self.data' are needed to be updated.
        """
        self.new_data['info'] = self.data['info']
        self.new_data['images'] = self.data['images'] + self.images_json
        self.new_data['annotations'] = self.annotations + self.ann_json
        self.new_data['categories'] = self.data['categories']

        with open(NEW_ANN_PATH, 'w') as json_file:
            json.dump(self.new_data, json_file, indent=2)
            print('JSON file written')


def data_augmentation(debug=False):
    da = DataAugmentation()
    da.read(ANN_PATH)   # read annotation data
    da.augment(debug)   # read images; data augmentation; get annotation json
    da.write_image()    # write images; get image json
    da.update_json()    # update json file


if __name__ == "__main__":
    data_augmentation(debug=True)
