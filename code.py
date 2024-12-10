# -*- coding: utf-8 -*-
"""Code.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1FEN5_jGt1rsL499tUKm1UXnr6njmdJIr

# Global Setup
"""

import numpy as np
import random
import torch
from torch import nn
import torch.nn.functional as F
import torch.optim as optim
import torchvision
from torchvision import datasets, transforms
from torch.utils.data import DataLoader, Subset
import matplotlib.pyplot as plt
import time
import copy
from sklearn.model_selection import train_test_split

def measure_inference_time(model, testloader, device):
    model.eval()
    inputs, _ = next(iter(testloader))  # Get one batch of data
    inputs = inputs.to(device)
    start_time = time.time()
    with torch.no_grad():
        outputs = model(inputs)  # Perform inference
    end_time = time.time()
    return (end_time - start_time) / len(inputs)  # Average inference time per image

def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)

"""# Baseline CNN"""

# Define a transform to normalize the data
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.5,), (0.5,)),
])

full_trainset = datasets.MNIST('data/', download=True, train=True, transform=transform)

# Use train_test_split to divide the training dataset into training and validation sets
train_indices, val_indices = train_test_split(
    range(len(full_trainset)), test_size=0.2, random_state=42
)


trainset = Subset(full_trainset, train_indices)
valset = Subset(full_trainset, val_indices)
trainloader = DataLoader(trainset, batch_size=64, shuffle=True)
valloader = DataLoader(valset, batch_size=64, shuffle=False)
dataloaders = {'train': trainloader, 'val': valloader}
dataset_sizes = {'train': len(trainset), 'val': len(valset)}

testset = datasets.MNIST('data/', download=True, train=False, transform=transform)
testloader = DataLoader(testset, batch_size=64, shuffle=False)

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

dataiter = iter(trainloader)
images, labels = next(dataiter)
print(type(images))
print(images.shape)
print(labels.shape)
plt.imshow(images[0].numpy().squeeze(), cmap='gray_r');

class CNNFramework(nn.Module):
    def __init__(self):
        super(CNNFramework, self).__init__()
        self.conv1 = nn.Conv2d(1, 32, kernel_size=3, padding=1)
        self.pool1 = nn.MaxPool2d(2, 2)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.pool2 = nn.MaxPool2d(2, 2)
        self.fc = nn.Linear(64 * 7 * 7, 10)

    def forward(self, x):
        x = self.pool1(F.relu(self.conv1(x)))
        x = self.pool2(F.relu(self.conv2(x)))
        x = x.view(-1, 64 * 7 * 7)
        x = self.fc(x)
        return x
model = CNNFramework()
print(model)

optimizer = optim.SGD(model.parameters(), lr=0.001)
criterion = nn.CrossEntropyLoss()

exp_lr_scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.1)

if torch.cuda.is_available():
    model = model.to(device)
    criterion = criterion.to(device)

def train_model(model, criterion, optimizer, scheduler, dataset_sizes, dataloaders, num_epochs, testloader):
    since = time.time()
    best_model_wts = copy.deepcopy(model.state_dict())
    best_acc = 0.0

    history = {
        'train_loss': [],
        'train_acc': [],
        'val_loss': [],
        'val_acc': []
    }

    test_accuracies = []

    for epoch in range(num_epochs):
        print('Epoch {}/{}'.format(epoch, num_epochs - 1))
        print('-' * 10)
        for phase in ['train', 'val']:
            if phase == 'train':
                model.train()
            else:
                model.eval()

            running_loss = 0.0
            running_corrects = 0

            for inputs, labels in dataloaders[phase]:
                inputs = inputs.to(device)
                labels = labels.to(device)

                optimizer.zero_grad()

                with torch.set_grad_enabled(phase == 'train'):
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                    loss = criterion(outputs, labels)

                    if phase == 'train':
                        loss.backward()
                        optimizer.step()

                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)

            if phase == 'train':
                scheduler.step()

            epoch_loss = running_loss / dataset_sizes[phase]
            epoch_acc = running_corrects.double() / dataset_sizes[phase]

            print('{} Loss: {:.4f} Acc: {:.4f}'.format(phase, epoch_loss, epoch_acc))

            if phase == 'train':
                history['train_loss'].append(epoch_loss)
                history['train_acc'].append(epoch_acc.item())
            else:
                history['val_loss'].append(epoch_loss)
                history['val_acc'].append(epoch_acc.item())

            if phase == 'val' and epoch_acc > best_acc:
                best_acc = epoch_acc
                best_model_wts = copy.deepcopy(model.state_dict())

        print()

    time_elapsed = time.time() - since
    print('Training complete in {:.0f}m {:.0f}s'.format(time_elapsed // 60, time_elapsed % 60))
    print('Best val Acc: {:4f}'.format(best_acc))


    model.load_state_dict(best_model_wts)

    model.eval()
    running_corrects = 0
    total = 0
    with torch.no_grad():
        for inputs, labels in testloader:
            inputs = inputs.to(device)
            labels = labels.to(device)

            outputs = model(inputs)
            _, preds = torch.max(outputs, 1)

            running_corrects += torch.sum(preds == labels.data)
            total += labels.size(0)

    test_acc = running_corrects.double() / total
    test_accuracies.append(test_acc.item())
    print('Test Accuracy: {:.4f}'.format(test_acc))

    return model, history, test_accuracies

import json
method_name = "Baseline CNN"
model = CNNFramework().to(device)
optimizer = torch.optim.AdamW(model.parameters(), lr=0.001)

trained_model, metrics, test_accuracies = train_model(
    model, criterion, optimizer, exp_lr_scheduler, dataset_sizes, dataloaders, num_epochs=10, testloader=testloader
)


# Add performance metrics
metrics['test_accuracy'] = test_accuracies[0]
inference_time = measure_inference_time(trained_model, testloader, device)
metrics['inference_time_per_image'] = inference_time
param_count = count_parameters(trained_model)
metrics['parameter_count'] = param_count

def imshow(inp, title=None):
    """Imshow for Tensor."""
    inp = inp.numpy().squeeze()
    plt.imshow(inp, cmap='gray_r')
    if title is not None:
        plt.title(title, fontsize=10)

def visualize_model(model, num_correct, num_wrong):
    was_training = model.training
    model.eval()
    correct_samples = []
    misclassified_samples = []

    with torch.no_grad():
        for inputs, labels in dataloaders['val']:
            inputs = inputs.to(device)
            labels = labels.to(device)

            outputs = model(inputs)
            _, preds = torch.max(outputs, 1)
            softmax_probs = torch.nn.functional.softmax(outputs, dim=1)

            for j in range(inputs.size(0)):
                sample = {
                    "image": inputs[j].cpu(),
                    "pred": preds[j].item(),
                    "true_label": labels[j].item(),
                    "confidence": softmax_probs[j, preds[j]].item(),
                }
                if preds[j] == labels[j]:
                    correct_samples.append(sample)
                else:
                    misclassified_samples.append(sample)

    sampled_correct = random.sample(correct_samples, min(len(correct_samples), num_correct))
    sampled_wrong = random.sample(misclassified_samples, min(len(misclassified_samples), num_wrong))
    sampled_images = sampled_correct + sampled_wrong

    num_images = len(sampled_images)
    num_rows, num_cols = 4, 4
    plt.figure(figsize=(12, 12))

    for i, sample in enumerate(sampled_images[:num_rows * num_cols]):
        image, pred, true_label, confidence = sample["image"], sample["pred"], sample["true_label"], sample["confidence"]

        ax = plt.subplot(num_rows, num_cols, i + 1)
        ax.axis('off')

        if pred == true_label:
            ax.set_title('Correct: {} \nConf: {:.2f}'.format(pred, confidence))
        else:
            ax.set_title('Wrong: {} (True: {}) \nConf: {:.2f}'.format(pred, true_label, confidence))

        imshow(image)

    plt.subplots_adjust(hspace=0.5, wspace=0.3)
    plt.show()

    model.train(mode=was_training)

visualize_model(model,num_correct=8, num_wrong=8)

"""# Braching/ Merging CNN"""

transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.5,), (0.5,)),
])

full_trainset = datasets.MNIST('data/', download=True, train=True, transform=transform)

train_indices, val_indices = train_test_split(
    range(len(full_trainset)), test_size=0.2, random_state=42
)


trainset = Subset(full_trainset, train_indices)
valset = Subset(full_trainset, val_indices)
trainloader = DataLoader(trainset, batch_size=64, shuffle=True)
valloader = DataLoader(valset, batch_size=64, shuffle=False)
dataloaders = {'train': trainloader, 'val': valloader}
dataset_sizes = {'train': len(trainset), 'val': len(valset)}

testset = datasets.MNIST('data/', download=True, train=False, transform=transform)
testloader = DataLoader(testset, batch_size=64, shuffle=False)

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

class BranchingMergingCNN(nn.Module):
    def __init__(self):
        super(BranchingMergingCNN, self).__init__()
        # Branch 1: Convolution with 3x3 kernel
        self.branch1 = nn.Conv2d(1, 32, kernel_size=3, padding=1)
        # Branch 2: Convolution with 5x5 kernel
        self.branch2 = nn.Conv2d(1, 32, kernel_size=5, padding=2)
        # Branch 3: Convolution with 7x7 kernel
        self.branch3 = nn.Conv2d(1, 32, kernel_size=7, padding=3)

        # Convolution layer after merging branches
        self.conv_merge = nn.Sequential(
            nn.Conv2d(96, 128, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2, stride=2)  # Downsample to reduce size
        )

        # Additional convolution layers after merging
        self.conv_post_merge = nn.Sequential(
            nn.Conv2d(128, 128, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2, stride=2)  # Further downsampling
        )

        # Fully connected layers
        self.fc = nn.Sequential(
            nn.Linear(128 * 7 * 7, 256),
            nn.ReLU(),
            nn.Linear(256, 10)
        )

    def forward(self, x):
        # Apply branch convolutions
        b1 = F.relu(self.branch1(x))
        b2 = F.relu(self.branch2(x))
        b3 = F.relu(self.branch3(x))

        # Merge branches
        merged = torch.cat([b1, b2, b3], dim=1)  # Concatenate along the channel dimension
        merged = self.conv_merge(merged)

        # Further processing with additional convolution layers
        post_merge = self.conv_post_merge(merged)

        # Flatten and pass through fully connected layers
        post_merge = post_merge.view(post_merge.size(0), -1)
        out = self.fc(post_merge)

        return out

# Initialize the model
model = BranchingMergingCNN()

# Xavier initialization
def init_weights(m):
    if isinstance(m, nn.Conv2d) or isinstance(m, nn.Linear):
        nn.init.xavier_uniform_(m.weight)

model.apply(init_weights)

print(model)

optimizer = torch.optim.AdamW(model.parameters(), lr=0.001)
criterion = nn.CrossEntropyLoss()

exp_lr_scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.1)

if torch.cuda.is_available():
    model = model.to(device)
    criterion = criterion.to(device)

def train_model(model, criterion, optimizer, scheduler, dataset_sizes, dataloaders, num_epochs, testloader):
    since = time.time()
    best_model_wts = copy.deepcopy(model.state_dict())
    best_acc = 0.0

    history = {
        'train_loss': [],
        'train_acc': [],
        'val_loss': [],
        'val_acc': []
    }

    # Record test set accuracy
    test_accuracies = []

    for epoch in range(num_epochs):
        print('Epoch {}/{}'.format(epoch, num_epochs - 1))
        print('-' * 10)

        # Each epoch has a training and validation phase
        for phase in ['train', 'val']:
            if phase == 'train':
                model.train()
            else:
                model.eval()

            running_loss = 0.0
            running_corrects = 0

            for inputs, labels in dataloaders[phase]:
                inputs = inputs.to(device)
                labels = labels.to(device)

                optimizer.zero_grad()

                with torch.set_grad_enabled(phase == 'train'):
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                    loss = criterion(outputs, labels)

                    if phase == 'train':
                        loss.backward()
                        optimizer.step()

                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)

            if phase == 'train':
                scheduler.step()

            epoch_loss = running_loss / dataset_sizes[phase]
            epoch_acc = running_corrects.double() / dataset_sizes[phase]

            print('{} Loss: {:.4f} Acc: {:.4f}'.format(phase, epoch_loss, epoch_acc))

            if phase == 'train':
                history['train_loss'].append(epoch_loss)
                history['train_acc'].append(epoch_acc.item())
            else:
                history['val_loss'].append(epoch_loss)
                history['val_acc'].append(epoch_acc.item())

            # Save the best model weights based on validation accuracy
            if phase == 'val' and epoch_acc > best_acc:
                best_acc = epoch_acc
                best_model_wts = copy.deepcopy(model.state_dict())

        print()

    time_elapsed = time.time() - since
    print('Training complete in {:.0f}m {:.0f}s'.format(time_elapsed // 60, time_elapsed % 60))
    print('Best val Acc: {:4f}'.format(best_acc))

    # Load the best model weights
    model.load_state_dict(best_model_wts)

    # Evaluate on the test set
    model.eval()
    running_corrects = 0
    total = 0
    with torch.no_grad():
        for inputs, labels in testloader:
            inputs = inputs.to(device)
            labels = labels.to(device)

            outputs = model(inputs)
            _, preds = torch.max(outputs, 1)

            running_corrects += torch.sum(preds == labels.data)
            total += labels.size(0)

    test_acc = running_corrects.double() / total
    test_accuracies.append(test_acc.item())
    print('Test Accuracy: {:.4f}'.format(test_acc))

    return model, history, test_accuracies

method_name = "BranchingMergingCNN"
model = BranchingMergingCNN().to(device)
optimizer = torch.optim.AdamW(model.parameters(), lr=0.001)

trained_model, metrics, test_accuracies = train_model(
    model, criterion, optimizer, exp_lr_scheduler, dataset_sizes, dataloaders, num_epochs=10, testloader=testloader
)


# Add performance metrics
metrics['test_accuracy'] = test_accuracies[0]
inference_time = measure_inference_time(trained_model, testloader, device)
metrics['inference_time_per_image'] = inference_time
param_count = count_parameters(trained_model)
metrics['parameter_count'] = param_count

"""# MAGE CNN"""

transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.5,), (0.5,)),
])
full_trainset = datasets.MNIST('data/', download=True, train=True, transform=transform)
train_indices, val_indices = train_test_split(
    range(len(full_trainset)), test_size=0.2, random_state=42
)


trainset = Subset(full_trainset, train_indices)
valset = Subset(full_trainset, val_indices)
trainloader = DataLoader(trainset, batch_size=64, shuffle=True)
valloader = DataLoader(valset, batch_size=64, shuffle=False)
dataloaders = {'train': trainloader, 'val': valloader}
dataset_sizes = {'train': len(trainset), 'val': len(valset)}

# Load the MNIST test set
testset = datasets.MNIST('data/', download=True, train=False, transform=transform)
testloader = DataLoader(testset, batch_size=64, shuffle=False)

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

def generate_mask(batch_size, img_size, mask_ratio=0.2):
    mask = torch.rand(batch_size, img_size, img_size) < mask_ratio
    return mask.unsqueeze(1)  # [batch_size, 1, img_size, img_size]

class SelfAttention(nn.Module):
    def __init__(self, in_channels):
        super(SelfAttention, self).__init__()
        self.query = nn.Conv2d(in_channels, in_channels // 8, kernel_size=1)
        self.key = nn.Conv2d(in_channels, in_channels // 8, kernel_size=1)
        self.value = nn.Conv2d(in_channels, in_channels, kernel_size=1)
        self.gamma = nn.Parameter(torch.zeros(1))

    def forward(self, x):
        batch_size, C, H, W = x.size()

        query = self.query(x).view(batch_size, -1, H * W).permute(0, 2, 1)  # [batch_size, H*W, C//8]
        key = self.key(x).view(batch_size, -1, H * W)  # [batch_size, C//8, H*W]
        value = self.value(x).view(batch_size, -1, H * W)  # [batch_size, C, H*W]

        # calculate the weights
        attention = torch.softmax(torch.bmm(query, key), dim=-1)  # [batch_size, H*W, H*W]

        # Use attention-weighted eigenvalues
        out = torch.bmm(value, attention)  # [batch_size, C, H*W]
        out = out.view(batch_size, C, H, W)  # [batch_size, C, H, W]

        return self.gamma * out + x

class MAGE_CNN(nn.Module):
    def __init__(self):
        super(MAGE_CNN, self).__init__()
        self.conv1 = nn.Conv2d(1, 64, kernel_size=3, padding=1)
        self.pool1 = nn.MaxPool2d(2, 2)
        self.att1 = SelfAttention(64)

        self.conv2 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
        self.pool2 = nn.MaxPool2d(2, 2)
        self.att2 = SelfAttention(128)

        self.conv3 = nn.Conv2d(128, 256, kernel_size=3, padding=1)
        self.pool3 = nn.MaxPool2d(2, 2)
        self.att3 = SelfAttention(256)

        self.dropout = nn.Dropout(0.3)
        self.fc = nn.Linear(256 * 3 * 3, 10)  # Adjust based on the new feature map size

    def forward(self, x, mask=None):
        if mask is not None:
            x = x * mask  # Apply mask

        x = self.pool1(F.relu(self.conv1(x)))
        x = self.att1(x)
        x = self.pool2(F.relu(self.conv2(x)))
        x = self.att2(x)
        x = self.pool3(F.relu(self.conv3(x)))
        x = self.att3(x)
        x = x.view(-1, 256 * 3 * 3)
        x = self.dropout(x)
        x = self.fc(x)
        return x

model = MAGE_CNN().to(device)
optimizer = torch.optim.AdamW(model.parameters(), lr=0.001)
criterion = nn.CrossEntropyLoss()
exp_lr_scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.1)

def train_model(
    model, criterion, optimizer, scheduler, dataset_sizes, dataloaders, num_epochs, testloader, use_mask=False, img_size=28, mask_ratio=0.2
):
    since = time.time()
    best_model_wts = copy.deepcopy(model.state_dict())
    best_acc = 0.0

    # Store training history
    history = {'train_loss': [], 'train_acc': [], 'val_loss': [], 'val_acc': []}

    for epoch in range(num_epochs):
        print(f'Epoch {epoch}/{num_epochs - 1}')
        print('-' * 10)

        for phase in ['train', 'val']:
            model.train() if phase == 'train' else model.eval()

            running_loss = 0.0
            running_corrects = 0

            for inputs, labels in dataloaders[phase]:
                inputs, labels = inputs.to(device), labels.to(device)

                # Apply mask during training if enabled
                mask = generate_mask(inputs.size(0), img_size, mask_ratio).to(device) if (use_mask and phase == 'train') else None
                if mask is not None:
                    inputs = inputs * mask

                optimizer.zero_grad()

                # Forward and backward pass
                with torch.set_grad_enabled(phase == 'train'):
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                    loss = criterion(outputs, labels)

                    if phase == 'train':
                        loss.backward()
                        optimizer.step()

                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)

            if phase == 'train':
                scheduler.step()

            # Calculate epoch metrics
            epoch_loss = running_loss / dataset_sizes[phase]
            epoch_acc = running_corrects.double() / dataset_sizes[phase]

            print(f'{phase} Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f}')
            history[f'{phase}_loss'].append(epoch_loss)
            history[f'{phase}_acc'].append(epoch_acc.item())

            # Update best model
            if phase == 'val' and epoch_acc > best_acc:
                best_acc = epoch_acc
                best_model_wts = copy.deepcopy(model.state_dict())

    # Training complete
    time_elapsed = time.time() - since
    print(f'Training complete in {time_elapsed // 60:.0f}m {time_elapsed % 60:.0f}s')
    print(f'Best val Acc: {best_acc:.4f}')

    # Load best weights
    model.load_state_dict(best_model_wts)

    # Evaluate on test set
    model.eval()
    running_corrects = 0
    total = 0
    with torch.no_grad():
        for inputs, labels in testloader:
            inputs, labels = inputs.to(device), labels.to(device)
            outputs = model(inputs)
            _, preds = torch.max(outputs, 1)
            running_corrects += torch.sum(preds == labels.data)
            total += labels.size(0)

    test_acc = running_corrects.double() / total
    print(f'Test Accuracy: {test_acc:.4f}')

    return model, history, test_acc


# Initialize model, optimizer, and other components
method_name = "MAGE"
model = MAGE_CNN().to(device)
optimizer = torch.optim.AdamW(model.parameters(), lr=0.001)
criterion = nn.CrossEntropyLoss()
scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.1)

trained_model, metrics, test_accuracy = train_model(
    model,
    criterion,
    optimizer,
    scheduler,
    dataset_sizes,
    dataloaders,
    num_epochs=10,
    testloader=testloader,
    use_mask=False  # Disable mask for debugging
)

# Add performance metrics
metrics['test_accuracy'] = test_accuracies[0]
inference_time = measure_inference_time(trained_model, testloader, device)
metrics['inference_time_per_image'] = inference_time
param_count = count_parameters(trained_model)
metrics['parameter_count'] = param_count

"""# Visualization

"""

# Accuracy Data
epochs = range(1, 11)

baseline_acc = [0.9075, 0.9533, 0.9625, 0.9625, 0.9667, 0.9617, 0.9650, 0.9658, 0.9667, 0.9642]
mage_acc = [0.9350, 0.9692, 0.9708, 0.9667, 0.9717, 0.9808, 0.9800, 0.9833, 0.9858, 0.9842]
branching_merging_acc = [0.9567, 0.9567, 0.9583, 0.9633, 0.9733, 0.9742, 0.9758, 0.9683, 0.9733, 0.9750]

# Plot the graph
plt.figure(figsize=(12, 8))
plt.plot(epochs, baseline_acc, label='Baseline CNN', marker='o', linestyle='--', linewidth=2)
plt.plot(epochs, branching_merging_acc, label='Branching/Merging CNN', marker='^', linestyle='-', linewidth=2)
plt.plot(epochs, mage_acc, label='MAGE CNN', marker='s', linestyle='-.', linewidth=2)

# Highlight the maximum point for MAGE CNN
max_epoch_mage = np.argmax(mage_acc) + 1
max_value_mage = max(mage_acc)

# Adjust annotation to avoid the arrow going out of bounds
plt.annotate(f'Max: {max_value_mage:.4f}',
             xy=(max_epoch_mage, max_value_mage),
             xytext=(max_epoch_mage - 1.5, max_value_mage - 0.01),
             arrowprops=dict(facecolor='black', arrowstyle='->', shrinkA=0, shrinkB=5),
             fontsize=12, color='black')


plt.title('Accuracy Comparison Across Models', fontsize=16, fontweight='bold')
plt.xlabel('Epoch', fontsize=14)
plt.ylabel('Accuracy', fontsize=14)
plt.legend(loc='lower right', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.6)
plt.xticks(epochs, fontsize=12)
plt.yticks(np.linspace(0.9, 1.0, 11), fontsize=12)

# Set y-axis limits
plt.ylim(0.9, 1.0)

# Display the graph
plt.tight_layout()
plt.show()

# Loss Data
epochs = range(1, 11)

baseline_loss = [0.2766, 0.1660, 0.1335, 0.1138, 0.1042, 0.1241, 0.1094, 0.1078, 0.1249, 0.1294]
mage_loss = [0.1810, 0.1118, 0.0893, 0.0960, 0.0920, 0.0701, 0.0687, 0.0661, 0.0611, 0.0609]
branching_merging_loss = [0.1335, 0.1316, 0.1405, 0.1250, 0.1046, 0.1322, 0.1355, 0.1367, 0.1337, 0.1433]

plt.figure(figsize=(12, 8))
plt.plot(epochs, baseline_loss, label='Baseline CNN', marker='o', linestyle='--', linewidth=2, color='blue')
plt.plot(epochs, mage_loss, label='MAGE CNN', marker='s', linestyle='-.', linewidth=2, color='green')
plt.plot(epochs, branching_merging_loss, label='Branching/Merging CNN', marker='^', linestyle='-', linewidth=2, color='orange')

# Find the minimum point for MAGE CNN
min_epoch_mage = np.argmin(mage_loss) + 1
min_loss_mage = min(mage_loss)

# Add annotation: Highlight the minimum point for MAGE CNN
plt.annotate(f'Min: {min_loss_mage:.4f}',
             xy=(min_epoch_mage, min_loss_mage),
             xytext=(min_epoch_mage - 1.5, min_loss_mage + 0.015),
             arrowprops=dict(facecolor='green', arrowstyle='->', shrinkA=0, shrinkB=5),
             fontsize=12, color='green')


plt.title('Validation Loss Comparison Across Models', fontsize=16, fontweight='bold')
plt.xlabel('Epoch', fontsize=14)
plt.ylabel('Validation Loss', fontsize=14)
plt.legend(loc='upper right', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.6)

# Configure x and y ticks
plt.xticks(epochs, fontsize=12)
plt.yticks(fontsize=12)

# Display the graph
plt.tight_layout()
plt.show()

# Data
data = [baseline_acc, mage_acc, branching_merging_acc]
labels = ['Baseline CNN', 'MAGE CNN', 'Branching/Merging CNN']

# Create the boxplot
plt.figure(figsize=(8, 6))
plt.boxplot(data, labels=labels, patch_artist=True, boxprops=dict(facecolor='lightblue'))

plt.title('Accuracy Distribution Across Models', fontsize=16)
plt.ylabel('Accuracy', fontsize=14)
plt.ylim(0.9, 1.0)

plt.tight_layout()
plt.show()