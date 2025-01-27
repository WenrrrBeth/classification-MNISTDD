import numpy as np
import torch
from torch import nn
from torchvision import models
import torch.nn.functional as F
import os

class Params():
  def __init__(self):
    self.n_epochs = 300
    self.lr = 3e-4
    self.weight_decay = 0.001
    self.load_weights = 1
    self.root = '/content/drive/My Drive/A6/ckpts' #root to save model
    self.model_name = 'model.pt.172'
    self.wts_path = os.path.join(self.root, self.model_name)

class Images(object):
  def __init__(self, subset, batch=128, shuffle=True):
    root_dir = '/content/drive/My Drive/A6/MNISTDD_train_valid'
    if subset=='train':
      images = np.load(os.path.join(root_dir, "train_X.npy")) #[55000, 4096] training images
      classes = np.load(os.path.join(root_dir, "train_Y.npy")) #[55000, 2]
      bboxes = np.load(os.path.join(root_dir, "train_bboxes.npy")) #[55000, 2, 4]
    else:
      images = np.load(os.path.join(root_dir, "valid_X.npy")) #[55000, 4096] training images
      classes = np.load(os.path.join(root_dir, "valid_Y.npy"))  #[55000, 2]
      bboxes = np.load(os.path.join(root_dir, "valid_bboxes.npy")) #[55000, 2, 4]
    self._images = images
    self.images = self._images
    self._classes = classes
    self.classes = self._classes
    self._bboxes = bboxes
    self.bboxes = self._bboxes
    self.batch_size = batch
    self.sample_num = len(self.images)
    self.shuffle = shuffle
    if self.shuffle:
      self.shuffle_samples()
    self.batch_pointer = 0

  def shuffle_samples(self):
    image_indices = np.random.permutation(np.arange(self.sample_num))
    self.images = self._images[image_indices]
    self.classes = self._classes[image_indices]
    self.bboxes = self._bboxes[image_indices]
  
  def get_next_batch(self):
    total_remained_samples = self.sample_num - self.batch_pointer
    if total_remained_samples >= self.batch_size:
      image_batch = self.images[self.batch_pointer:self.batch_pointer+self.batch_size] # array slicing from batch pointer to batch pointer+batchsize
      classes_batch = self.classes[self.batch_pointer:self.batch_pointer+self.batch_size]
      bboxes_batch = self.bboxes[self.batch_pointer:self.batch_pointer+self.batch_size]
      self.batch_pointer += self.batch_size
    else:
      image_batch1 = self.images[self.batch_pointer:self.sample_num]
      classes_batch1 = self.classes[self.batch_pointer:self.sample_num]
      bboxes_batch1 = self.bboxes[self.batch_pointer:self.sample_num]

      if self.shuffle:
        self.shuffle_samples()

      image_batch2 = self.images[0:self.batch_size-total_remained_samples]
      classes_batch2 = self.classes[0:self.batch_size-total_remained_samples]
      bboxes_batch2 = self.bboxes[0:self.batch_size-total_remained_samples]

      image_batch = np.vstack((image_batch1, image_batch2))
      classes_batch = np.vstack((classes_batch1, classes_batch2))
      bboxes_batch = np.vstack((bboxes_batch1, bboxes_batch2))

      self.batch_pointer = self.batch_size - total_remained_samples
    return image_batch, classes_batch, bboxes_batch


class VGG(nn.Module):
  def __init__(self, classes=10, digits=2, boxes=4):
      super(VGG, self).__init__()

      self.conv1_1 = nn.Conv2d(1, 64, kernel_size=3, padding=1)  # stride = 1, by default
      self.batch1_1 = nn.BatchNorm2d(64)
      self.conv1_2 = nn.Conv2d(64, 64, kernel_size=3, padding=1)
      self.batch1_2 = nn.BatchNorm2d(64)
      self.pool1 = nn.MaxPool2d(kernel_size=2, stride=2)  #32*32

      self.conv2_1 = nn.Conv2d(64, 256, kernel_size=3, padding=1)
      self.batch2_1 = nn.BatchNorm2d(256)
      self.conv2_2 = nn.Conv2d(256, 256, kernel_size=3, padding=1)
      self.batch2_2 = nn.BatchNorm2d(256)
      self.pool2 = nn.MaxPool2d(kernel_size=4, stride=4) #16*16

      self.conv4_1 = nn.Conv2d(256, 1024, kernel_size=3, padding=1)
      self.batch4_1 = nn.BatchNorm2d(1024)
      self.conv4_2 = nn.Conv2d(1024, 1024, kernel_size=3, padding=1)
      self.batch4_2 = nn.BatchNorm2d(1024)
      self.conv4_3 = nn.Conv2d(1024, 1024, kernel_size=3, padding=1)
      self.batch4_3 = nn.BatchNorm2d(1024)
      self.pool4 = nn.MaxPool2d(kernel_size=8, stride=8)  #2*2

      self.fc7 = nn.Linear(1024, 512)
      self.batch7 = nn.BatchNorm1d(512)
      self.fc8 = nn.Linear(512, 256)
      self.batch8 = nn.BatchNorm1d(256)
      self.fc9 = nn.Linear(256, 148)
      self.fc10 = nn.Linear(148, 20)

      self.drop1 = nn.Dropout(p=0.05)
      self.drop2 = nn.Dropout(p=0.01)
    
  def forward(self, x):
      x = x.reshape(len(x), 1, 64, 64)
      x = F.relu(self.batch1_1(self.conv1_1(x)))
      x = F.relu(self.batch1_2(self.conv1_2(x)))
      # x = F.relu(self.batch1_3(self.conv1_3(x)))
      x = self.pool1(x)

      x = F.relu(self.batch2_1(self.conv2_1(x)))
      x = F.relu(self.batch2_2(self.conv2_2(x)))
      x = self.pool2(x)

      x = F.relu(self.batch4_1(self.conv4_1(x)))
      x = F.relu(self.batch4_2(self.conv4_2(x)))
      x = F.relu(self.batch4_3(self.conv4_3(x)))
      x = self.pool4(x)

      x = x.view(x.size(0), -1)

      x = self.drop1(F.relu(self.batch7(self.fc7(x))))
      x = self.drop2(F.relu(self.batch8(self.fc8(x))))
      x_bbox = self.fc9(x)
      x_classes= self.fc10(x_bbox)
      bbox = x_bbox
      cls = x_classes
      return cls, bbox

def classify_and_detect(images):
    """

    :param np.ndarray images: N x 4096 array containing N 64x64 images flattened into vectors
    :return: np.ndarray, np.ndarray
    """
    N = images.shape[0] #[5000,4096] only valid is passed in
    pred_class = np.empty((N, 2), dtype=np.int32)
    pred_bboxes = np.empty((N, 2, 4), dtype=np.float64)

    use_cuda = 1

    if use_cuda and torch.cuda.is_available():
        device = torch.device("cuda")
        print('Training on GPU: {}'.format(torch.cuda.get_device_name(0)))
    else:
        device = torch.device("cpu")
        print('Training on CPU')

    param = Params()
    
    train = Images('train')
    valid = Images('valid', shuffle=False)

    model =  VGG().to(device)

    def compute_iou(b_pred, b_gt):
      """

      :param b_pred: predicted bounding boxes, shape=(n,2,4)
      :param b_gt: ground truth bounding boxes, shape=(n,2,4)
      :return:
      """

      n = np.shape(b_gt)[0]
      L_pred = np.zeros((64, 64))
      L_gt = np.zeros((64, 64))
      iou = 0.0
      for i in range(n):
          for b in range(2):
              rr, cc = polygon([b_pred[i, b, 0], b_pred[i, b, 0], b_pred[i, b, 2], b_pred[i, b, 2]],
                              [b_pred[i, b, 1], b_pred[i, b, 3], b_pred[i, b, 3], b_pred[i, b, 1]], [64, 64])
              L_pred[rr, cc] = 1

              rr, cc = polygon([b_gt[i, b, 0], b_gt[i, b, 0], b_gt[i, b, 2], b_gt[i, b, 2]],
                              [b_gt[i, b, 1], b_gt[i, b, 3], b_gt[i, b, 3], b_gt[i, b, 1]], [64, 64])
              L_gt[rr, cc] = 1

              iou += (1.0 / (2 * n)) * (np.sum((L_pred + L_gt) == 2) / np.sum((L_pred + L_gt) >= 1))

              L_pred[:, :] = 0
              L_gt[:, :] = 0

      return iou

    def evaluation(image, classes, bboxes):
      eval_batch_size = 100
      pred_classes = []
      pred_bboxes = []
      model.eval()
      bboxes_size = len(bboxes)
      with torch.no_grad():
        for idx in range(0, len(images), eval_batch_size):
          e_idx = idx + eval_batch_size
          img = image[idx:e_idx]
          img = torch.FloatTensor(img).to(device) 
          pred_cls, pred_box = model(img)

          ################## pred_classes reshaping ###################
          pred_cls1 = pred_cls.permute(1, -2)[0:10].permute(1, -2)
          pred_cls2 = pred_cls.permute(1, -2)[10:20].permute(1, -2)

          pred_cls1 = torch.argmax(pred_cls1, axis=1).reshape(eval_batch_size, 1)
          pred_cls2 = torch.argmax(pred_cls2, axis=1).reshape(eval_batch_size, 1)

          pred_cls1.permute(1, -2)
          pred_cls2.permute(1, -2)
          
          pred_class = torch.cat((pred_cls1, pred_cls2), 1)
          pred_class = pred_class.cpu().numpy()
          pred_classes += list(pred_class)
          


          ##################### pred_bboxes reshaping #########################
          pred_box1 = pred_box.permute(1, -2)[0:74].permute(1, -2).reshape(eval_batch_size, 2, 37) 
          pred_box2 = pred_box.permute(1, -2)[74:148].permute(1, -2).reshape(eval_batch_size, 2, 37) 

          pred_box_1x = torch.argmax(pred_box1[:, 0, :], axis=1).reshape(eval_batch_size, 1)
          pred_box_1y = torch.argmax(pred_box1[:, 1, :], axis=1).reshape(eval_batch_size, 1)
          pred_box_2x = torch.argmax(pred_box2[:, 0, :], axis=1).reshape(eval_batch_size, 1)
          pred_box_2y = torch.argmax(pred_box2[:, 1, :], axis=1).reshape(eval_batch_size, 1)

          pred_box_1xR = pred_box_1x+28
          pred_box_1yR = pred_box_1y+28
          pred_box_2xR = pred_box_2x+28
          pred_box_2yR = pred_box_2y+28

          pred_boxes1 = torch.cat((pred_box_1x, pred_box_1y, pred_box_1xR, pred_box_1yR), 1)
          pred_boxes2 = torch.cat((pred_box_2x, pred_box_2y, pred_box_2xR, pred_box_2yR), 1)
          pred_boxes = torch.cat((pred_boxes1, pred_boxes2), 1).reshape(eval_batch_size, 2, 4)
          pred_boxes = pred_boxes.cpu().numpy()
          pred_bboxes += list(pred_boxes)


      pred_classes = np.vstack(pred_classes)
      pred_classes_calc = pred_classes.flatten()
      classes = classes.flatten()
      cls_acc = float((pred_classes_calc == classes).astype(np.int32).sum())/classes.size

      pred_bboxes = np.vstack(pred_bboxes).reshape(bboxes_size, 2, 4)
      iou = compute_iou(pred_bboxes, bboxes)
      return pred_classes, pred_bboxes, cls_acc, iou
    
    if param.load_weights:
      print('Loading weights from: {}'.format(param.wts_path))
      ckpt = torch.load(param.wts_path, map_location=device)
      model.load_state_dict(ckpt['model'])
    else:
      criterion = nn.CrossEntropyLoss().to(device) 
      optimizer = torch.optim.Adam(model.parameters(), lr=param.lr) 

      print("Training...")
      mean_loss = 0
      steps = 0
      losses = []
      max_acc = 0
      acc_id = 0
      n_batch = int(train.sample_num/train.batch_size)

      for epoch in range(param.n_epochs):
        model.train()
        for batch in range(n_batch):
          image, classes, bboxes = train.get_next_batch()

          image = torch.FloatTensor(image).to(device) 
          classes = torch.LongTensor(classes).squeeze().permute(1, -2).to(device)
          
          bboxes = torch.LongTensor(bboxes).squeeze().to(device)

          optimizer.zero_grad()

          out_class, out_box = model(image)  

          class1 = classes[0].squeeze()
          class2 = classes[1].squeeze()
          out_class1 = out_class.permute(1, -2)[0:10].permute(1, -2)
          out_class2 = out_class.permute(1, -2)[10:20].permute(1, -2)

          class_loss = criterion(out_class1, class1) + criterion(out_class2, class2)

          bboxes_1x = bboxes[:, 0, 0]
          bboxes_1y = bboxes[:, 0, 1]
          bboxes_2x = bboxes[:, 1, 0]
          bboxes_2y = bboxes[:, 1, 1]

          out_box_1x = out_box.permute(1, -2)[0:74].permute(1, -2).reshape(128, 2, 37)[:, 0, :]
          out_box_1y = out_box.permute(1, -2)[0:74].permute(1, -2).reshape(128, 2, 37)[:, 1, :]
          out_box_2x = out_box.permute(1, -2)[74:148].permute(1, -2).reshape(128, 2, 37)[:, 0, :]
          out_box_2y = out_box.permute(1, -2)[74:148].permute(1, -2).reshape(128, 2, 37)[:, 1, :]

          bbox_loss = criterion(out_box_1x, bboxes_1x) + criterion(out_box_1y, bboxes_1y) + criterion(out_box_2x, bboxes_2x) + criterion(out_box_2y, bboxes_2y)

          loss = class_loss + bbox_loss/2
          
          loss.backward()
          optimizer.step()

          _loss = loss.item()
          steps += 1
          mean_loss += (_loss-mean_loss)/steps
          losses.append(_loss)

        pred_class, pred_bboxes, cls_acc, box_acc = evaluation(valid._images, valid._classes, valid._bboxes)

        max_acc = cls_acc 
        max_id = epoch
        if epoch>250:
          ckpt = {
              'model':model.state_dict(),
          }
          torch.save(ckpt, '{}.{}'.format(param.wts_path, max_id))
        print("epoch {}/{}: Test Class Acc = {:.3f}, Test BBox iou = {:.3f} max_acc = {:.3f} in epoch {}".format(
            epoch+1, param.n_epochs, cls_acc, box_acc, max_acc, max_id+1))
      print("Done training. Weights saved to: {}".format('model.pt'))
      ckpt = {
          'model':model.state_dict(),
      }
      torch.save(ckpt, param.wts_path)
      return pred_class, pred_bboxes

    print("Evaluating without Training")
    pred_class, pred_bboxes, cls_acc, box_acc = evaluation(images, valid._classes, valid._bboxes)
    return pred_class, pred_bboxes

import time
import numpy as np
from skimage.draw import polygon
import os
from tqdm import tqdm



def compute_classification_acc(pred, gt):
    assert pred.shape == gt.shape
    return (pred == gt).astype(int).sum() / gt.size


def compute_iou(b_pred, b_gt):
    """

    :param b_pred: predicted bounding boxes, shape=(n,2,4)
    :param b_gt: ground truth bounding boxes, shape=(n,2,4)
    :return:
    """

    n = np.shape(b_gt)[0]
    L_pred = np.zeros((64, 64))
    L_gt = np.zeros((64, 64))
    iou = 0.0
    for i in range(n):
        for b in range(2):
            rr, cc = polygon([b_pred[i, b, 0], b_pred[i, b, 0], b_pred[i, b, 2], b_pred[i, b, 2]],
                             [b_pred[i, b, 1], b_pred[i, b, 3], b_pred[i, b, 3], b_pred[i, b, 1]], [64, 64])
            L_pred[rr, cc] = 1

            rr, cc = polygon([b_gt[i, b, 0], b_gt[i, b, 0], b_gt[i, b, 2], b_gt[i, b, 2]],
                             [b_gt[i, b, 1], b_gt[i, b, 3], b_gt[i, b, 3], b_gt[i, b, 1]], [64, 64])
            L_gt[rr, cc] = 1

            iou += (1.0 / (2 * n)) * (np.sum((L_pred + L_gt) == 2) / np.sum((L_pred + L_gt) >= 1))

            L_pred[:, :] = 0
            L_gt[:, :] = 0

    return iou


def main():
    prefix = "valid"

    images = np.load(os.path.join('/content/drive/My Drive/A6/MNISTDD_train_valid', prefix + "_X.npy"))   # 2D matrix with dimension [N,4096] train: [55000,4096] valid: [5000,4096] (flattened images)

    start_t = time.time()
    pred_class, pred_bboxes = classify_and_detect(images)
    end_t = time.time()

    gt_class = np.load(os.path.join('/content/drive/My Drive/A6/MNISTDD_train_valid', prefix + "_Y.npy"))   # 2D matrix with dimension [N,2]  train: [55000,2]  valid: [5000,2] (2 labels of int)
    gt_bboxes = np.load(os.path.join('/content/drive/My Drive/A6/MNISTDD_train_valid', prefix + "_bboxes.npy"))   # 2D matrix with dimension [N,2,4]  train: [55000,2,4]  valid: [5000,2,4] (2 numbers, 4 loc ind)
    acc = compute_classification_acc(pred_class, gt_class)
    iou = compute_iou(pred_bboxes, gt_bboxes)

    time_taken = end_t - start_t

    print(f"Classification Acc: {acc}")
    print(f"Detection IOU: {iou}")
    print(f"Test time: {time_taken}")


if __name__ == '__main__':
    main()
