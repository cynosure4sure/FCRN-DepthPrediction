# ===========
#  Libraries
# ===========
import tensorflow as tf

from .model.fcrn import ResNet50UpProj
from .plot import Plot
from .dataloader import Dataloader

# ==================
#  Global Variables
# ==================


# ===================
#  Class Declaration
# ===================
class Validation:
    def __init__(self, args, input_size, output_size, max_depth, dataset_name):
        # Raw Input/Output
        self.tf_image_raw = tf.placeholder(tf.uint8, shape=(None, None, None, 3))

        if dataset_name.split('_')[0] == 'kittidiscrete' or \
           dataset_name.split('_')[0] == 'kitticontinuous':
            self.tf_depth_raw = tf.placeholder(tf.uint8, shape=(None, None, None, 1))
        else:
            self.tf_depth_raw = tf.placeholder(tf.uint16, shape=(None, None, None, 1))

        # True Depth Value Calculation. May vary from dataset to dataset.
        self.tf_depth_meters = Dataloader.rawdepth2meters(args.dataset, self.tf_depth_raw)

        # Convert uint8/uint16 to float32
        self.tf_image_raw = tf.cast(self.tf_image_raw, tf.float32, name='image')
        # self.tf_depth = tf.cast(self.tf_depth, tf.float32, name='depth')

        # Workaround for assigning bug
        self.tf_image = self.tf_image_raw
        self.tf_depth = self.tf_depth_meters

        # Crops Input and Depth Images (Removes Sky)
        if dataset_name[0:5] == 'kitti':
            tf_image_shape = tf.shape(self.tf_image_raw)
            tf_depth_shape = tf.shape(self.tf_depth_raw)

            crop_height_perc = tf.constant(0.3, tf.float32)
            tf_image_new_height = crop_height_perc * tf.cast(tf_image_shape[1], tf.float32)
            tf_depth_new_height = crop_height_perc * tf.cast(tf_depth_shape[1], tf.float32)

            # FIXME: Why changing to self.tf_image e self.tf_depth doesn't work?
            self.tf_image = self.tf_image_raw[:, tf.cast(tf_image_new_height, tf.int32):, :]
            self.tf_depth = self.tf_depth_raw[:, tf.cast(tf_depth_new_height, tf.int32):, :]

        # Downsizes Input and Depth Images
        self.tf_image_resized = tf.image.resize_images(self.tf_image, [input_size.height, input_size.width])
        self.tf_depth_resized = tf.image.resize_images(self.tf_depth, [output_size.height, output_size.width])

        self.tf_image_resized_uint8 = tf.cast(self.tf_image_resized, tf.uint8)  # Visual purpose

        self.fcrn = ResNet50UpProj({'data': self.tf_image_resized}, batch=args.batch_size, keep_prob=1, is_training=False)
        self.tf_pred = self.fcrn.get_output()

        # Clips predictions above a certain distance in meters. Inspired from Monodepth's article.
        if max_depth is not None:
            self.tf_pred = tf.clip_by_value(self.tf_pred, 0, tf.constant(max_depth))

        with tf.name_scope('Valid'):
            self.tf_loss = None
            self.loss = -1
            self.loss_hist = []

        if args.show_valid_progress:
            self.plot = Plot(args.mode, title='Validation Prediction')

        print("[Network/Validation] Validation Tensors created.")
        print(self.tf_image)
        print(self.tf_depth)
        print(self.tf_image_resized)
        print(self.tf_image_resized_uint8)
        print(self.tf_depth_resized)
        print()
        # input("valid")
