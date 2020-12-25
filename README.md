# MNIST Double Digits Datasets Classification and Detectection

Datasets:
- 64x64 size images containing two digits
- digits range [0, 9]
- digits size (bounding box size) 28x28

Algorithm used:
- Labels: classification
    - two digits range from 0 to 9
    - model returned labels range from 0 to 19
    - reshape the labels into shape [N, 2]
    - each n data contain two class that the two digits belongs to
    
- Bounding Boxes: Classification
    - two digits' position ranges from 0 to 37 ((64+1)-28)
    - model returned labels range from 0 to 148 (4*37)
    - reshape the labels in to shape [N, 2, 4]
    - each n data contain [x1, y1, x1+28, y1+28], [x2, y2, x2+28, y2+28] where x and y represents the exist and 1 and 2 represent first and second digits

Model: <br />
&nbsp;&nbsp;&nbsp;&nbsp; ![alt text](https://github.com/WenrrrBeth/classification-MNISTDD/blob/master/model.png)

Result:
- Validation datasets with model.pt.172:
    - Classification accuracy: 99.63
    - Detection IOU: 95.17
    - Valid time (GPU): ≈23.28
    - Valid time (CPU): ≈418

