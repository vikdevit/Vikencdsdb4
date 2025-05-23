# -*- coding: utf-8 -*-
"""vikenbloc4GANvielli19h.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1aC5rX5DoCgBXNMvrJX-7-5mdXm862F42
"""

import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from PIL import Image
import matplotlib.pyplot as plt
import time

# Dataset personnalisé pour le dataset UTKFace Cropped
class UTKFaceCroppedDataset(Dataset):
    def __init__(self, image_dir, transform=None):
        self.image_dir = image_dir
        self.transform = transform
        self.image_paths = [os.path.join(image_dir, fname) for fname in os.listdir(image_dir) if fname.endswith('.jpg')]

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        # Chargement de l'image
        image_path = self.image_paths[idx]
        image = Image.open(image_path).convert('RGB')

        # Extraction de l'âge depuis le nom de fichier (format: <age>_<gender>_<race>.jpg)
        filename = os.path.basename(image_path)
        age = int(filename.split('_')[0])  # Récupère l'âge depuis le nom du fichier

        # Transformation si nécessaire
        if self.transform:
            image = self.transform(image)

        # Retourne l'image et l'âge
        return image, torch.tensor(age, dtype=torch.float32)

# Transformations pour prétraiter les images
transform = transforms.Compose([
    transforms.Resize((64, 64)),  # Réduire la taille pour accélérer le calcul
    transforms.ToTensor(),
    transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
])

# Charger le dataset UTKFace Cropped
image_dir = 'drive/MyDrive/Bloc4Viken/utkcropped'  # Remplace par le chemin réel vers ton dossier d'images
dataset = UTKFaceCroppedDataset(image_dir, transform=transform)
train_loader = DataLoader(dataset, batch_size=16, shuffle=True)

# Modèle générateur simplifié
class Generator(nn.Module):
    def __init__(self, z_dim=100, age_dim=1):
        super(Generator, self).__init__()
        self.fc = nn.Sequential(
            nn.Linear(z_dim + age_dim, 128),  # Réduire la taille pour simplifier
            nn.ReLU(True),
            nn.Linear(128, 256),
            nn.ReLU(True),
            nn.Linear(256, 3 * 64 * 64),  # Réduire la taille de l'image générée à 64x64
            nn.Tanh()
        )

    def forward(self, z, age):
        # Concatenation du bruit et de l'âge
        x = torch.cat([z, age], dim=1)
        x = self.fc(x)
        x = x.view(-1, 3, 64, 64)  # Redimensionner pour avoir une image 64x64
        return x

# Modèle discriminateur simplifié
class Discriminator(nn.Module):
    def __init__(self, age_dim=1):
        super(Discriminator, self).__init__()
        self.model = nn.Sequential(
            nn.Conv2d(3, 32, 4, 2, 1),  # Réduire les filtres pour simplifier
            nn.LeakyReLU(0.2),
            nn.Conv2d(32, 64, 4, 2, 1),
            nn.LeakyReLU(0.2),
            nn.Flatten()
        )
        self.age_embed = nn.Linear(age_dim, 128)  # Embedding de l'âge
        self.fc = nn.Sequential(
            nn.Linear(64 * 16 * 16 + 128, 1),  # Ajuster en fonction de la taille des images
            nn.Sigmoid()
        )

    def forward(self, x, age):
        # Passer l'image dans le modèle
        x = self.model(x)

        # Embedding de l'âge
        age_embedded = self.age_embed(age).view(age.size(0), -1)  # Applatir l'âge

        # Concatenate l'âge avec les caractéristiques extraites de l'image
        x = torch.cat([x, age_embedded], dim=1)  # Ajouter l'âge aux caractéristiques extraites de l'image

        # Classification finale
        x = self.fc(x)
        return x

# Initialisation des modèles
z_dim = 100
age_dim = 1

# Utilisation du CPU
device = torch.device("cpu")

# Envoi des modèles sur le CPU
generator = Generator(z_dim=z_dim, age_dim=age_dim).to(device)
discriminator = Discriminator(age_dim=age_dim).to(device)

# Optimiseur
lr = 0.0002
betas = (0.5, 0.999)
optimizer_G = optim.Adam(generator.parameters(), lr=lr, betas=betas)
optimizer_D = optim.Adam(discriminator.parameters(), lr=lr, betas=betas)

# Critère
criterion = nn.BCELoss()

# Sélectionner une image spécifique (par exemple, la première image du dataset)
real_image, real_age = dataset[0]  # Utiliser la première image pour l'affichage constant
real_image = real_image.unsqueeze(0).to(device)  # Ajouter une dimension batch
real_age = real_age.unsqueeze(0).to(device).view(-1, 1)  # Ajouter une dimension batch et redimensionner l'âge

# Fonction pour afficher les images
def show_images(real_image, fake_image, real_age, fake_age, epoch):
    real_image = real_image / 2 + 0.5  # Dénormaliser l'image
    fake_image = fake_image / 2 + 0.5  # Dénormaliser l'image

    fig, axes = plt.subplots(1, 2, figsize=(8, 4))
    axes[0].imshow(real_image[0].permute(1, 2, 0).cpu().detach().numpy())
    axes[0].set_title(f'Real Age: {real_age[0].item()}')
    axes[1].imshow(fake_image[0].permute(1, 2, 0).cpu().detach().numpy())
    axes[1].set_title(f'Fake Age: {fake_age[0].item()}')
    plt.show()

# Entraînement
num_epochs = 10
for epoch in range(num_epochs):
    start_time = time.time()  # Démarrer le chronomètre pour l'époch
    for i, (real_images, real_ages) in enumerate(train_loader):
        batch_start_time = time.time()  # Chronomètre pour chaque batch
        batch_size = real_images.size(0)
        real_images = real_images.to(device)
        real_ages = real_ages.float().to(device).view(-1, 1)  # Convertir l'âge en float et redimensionner

        # Labels réels pour le discriminateur
        real_labels = torch.ones(batch_size, 1).to(device)
        fake_labels = torch.zeros(batch_size, 1).to(device)

        # 🔹 1. Avec de vraies images
        outputs_real = discriminator(real_images, real_ages)
        d_loss_real = criterion(outputs_real.view(-1, 1), real_labels)
        d_loss_real.backward()

        # 🔹 2. Avec des images générées
        z = torch.randn(batch_size, z_dim).to(device)  # Générer du bruit pour le générateur
        fake_ages = real_ages + 30  # Ajouter un vieillissement fixe de 30 ans
        fake_images = generator(z, fake_ages)  # Générer une image avec l'âge vieillissant

        outputs_fake = discriminator(fake_images.detach(), fake_ages)  # Ne pas rétropropager dans le générateur
        d_loss_fake = criterion(outputs_fake.view(-1, 1), fake_labels)
        d_loss_fake.backward()

        optimizer_D.step()

        # 🔹 Mise à jour du générateur
        optimizer_G.zero_grad()
        outputs_fake_gen = discriminator(fake_images, fake_ages)
        g_loss = criterion(outputs_fake_gen.view(-1, 1), real_labels)
        g_loss.backward()

        optimizer_G.step()

        # Affichage périodique des résultats (toutes les 50 étapes)
        if (i + 1) % 50 == 0:
            print(f'Epoch [{epoch+1}/{num_epochs}], Batch [{i+1}/{len(train_loader)}], d_loss: {d_loss_real.item() + d_loss_fake.item():.4f}, g_loss: {g_loss.item():.4f}')
            show_images(real_image, fake_images, real_ages, fake_ages, epoch)

        batch_duration = time.time() - batch_start_time  # Temps écoulé pour ce batch
        print(f"Batch {i+1}, Durée du batch: {batch_duration:.2f} secondes")

    epoch_duration = time.time() - start_time  # Temps total pour une époque
    print(f"Durée totale de l'époque {epoch+1}: {epoch_duration:.2f} secondes")

import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from PIL import Image
import matplotlib.pyplot as plt
import time

# Dataset personnalisé pour le dataset UTKFace Cropped
class UTKFaceCroppedDataset(Dataset):
    def __init__(self, image_dir, transform=None):
        self.image_dir = image_dir
        self.transform = transform
        self.image_paths = [os.path.join(image_dir, fname) for fname in os.listdir(image_dir) if fname.endswith('.jpg')]

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        # Chargement de l'image
        image_path = self.image_paths[idx]
        image = Image.open(image_path).convert('RGB')

        # Extraction de l'âge depuis le nom de fichier (format: <age>_<gender>_<race>.jpg)
        filename = os.path.basename(image_path)
        age = int(filename.split('_')[0])  # Récupère l'âge depuis le nom du fichier

        # Transformation si nécessaire
        if self.transform:
            image = self.transform(image)

        # Retourne l'image et l'âge
        return image, torch.tensor(age, dtype=torch.float32)

# Transformations pour prétraiter les images
transform = transforms.Compose([
    transforms.Resize((64, 64)),  # Réduire la taille pour accélérer le calcul
    transforms.ToTensor(),
    transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
])

# Charger le dataset UTKFace Cropped
image_dir = 'drive/MyDrive/Bloc4Viken/utkcropped'  # Remplace par le chemin réel vers ton dossier d'images
dataset = UTKFaceCroppedDataset(image_dir, transform=transform)
train_loader = DataLoader(dataset, batch_size=16, shuffle=True)

# Modèle générateur simplifié
class Generator(nn.Module):
    def __init__(self, z_dim=100, age_dim=1):
        super(Generator, self).__init__()
        self.fc = nn.Sequential(
            nn.Linear(z_dim + age_dim, 128),  # Réduire la taille pour simplifier
            nn.ReLU(True),
            nn.Linear(128, 256),
            nn.ReLU(True),
            nn.Linear(256, 3 * 64 * 64),  # Réduire la taille de l'image générée à 64x64
            nn.Tanh()
        )

    def forward(self, z, age):
        # Concatenation du bruit et de l'âge
        x = torch.cat([z, age], dim=1)
        x = self.fc(x)
        x = x.view(-1, 3, 64, 64)  # Redimensionner pour avoir une image 64x64
        return x

# Modèle discriminateur simplifié
class Discriminator(nn.Module):
    def __init__(self, age_dim=1):
        super(Discriminator, self).__init__()
        self.model = nn.Sequential(
            nn.Conv2d(3, 32, 4, 2, 1),  # Réduire les filtres pour simplifier
            nn.LeakyReLU(0.2),
            nn.Conv2d(32, 64, 4, 2, 1),
            nn.LeakyReLU(0.2),
            nn.Flatten()
        )
        self.age_embed = nn.Linear(age_dim, 128)  # Embedding de l'âge
        self.fc = nn.Sequential(
            nn.Linear(64 * 16 * 16 + 128, 1),  # Ajuster en fonction de la taille des images
            nn.Sigmoid()
        )

    def forward(self, x, age):
        # Passer l'image dans le modèle
        x = self.model(x)

        # Embedding de l'âge
        age_embedded = self.age_embed(age).view(age.size(0), -1)  # Applatir l'âge

        # Concatenate l'âge avec les caractéristiques de l'image
        x = torch.cat([x, age_embedded], dim=1)  # Ajouter l'âge aux caractéristiques extraites de l'image

        # Classification finale
        x = self.fc(x)
        return x

# Initialisation des modèles
z_dim = 100
age_dim = 1

# Utilisation du CPU
device = torch.device("cpu")

# Envoi des modèles sur le CPU
generator = Generator(z_dim=z_dim, age_dim=age_dim).to(device)
discriminator = Discriminator(age_dim=age_dim).to(device)

# Optimiseur
lr = 0.0002
betas = (0.5, 0.999)
optimizer_G = optim.Adam(generator.parameters(), lr=lr, betas=betas)
optimizer_D = optim.Adam(discriminator.parameters(), lr=lr, betas=betas)

# Critère
criterion = nn.BCELoss()

# Fonction pour afficher les images
def show_images(real_images, fake_images, real_ages, fake_ages, epoch):
    real_images = real_images / 2 + 0.5  # Dénormaliser les images
    fake_images = fake_images / 2 + 0.5  # Dénormaliser les images

    fig, axes = plt.subplots(1, 2, figsize=(8, 4))
    axes[0].imshow(real_images[0].permute(1, 2, 0).cpu().detach().numpy())
    axes[0].set_title(f'Real Age: {real_ages[0].item()}')
    axes[1].imshow(fake_images[0].permute(1, 2, 0).cpu().detach().numpy())
    axes[1].set_title(f'Fake Age: {fake_ages[0].item()}')
    plt.show()

# Entraînement
num_epochs = 10
for epoch in range(num_epochs):
    start_time = time.time()  # Démarrer le chronomètre pour l'époch
    for i, (real_images, real_ages) in enumerate(train_loader):
        batch_start_time = time.time()  # Chronomètre pour chaque batch
        batch_size = real_images.size(0)
        real_images = real_images.to(device)
        real_ages = real_ages.float().to(device).view(-1, 1)  # Convertir l'âge en float et redimensionner

        # Labels réels pour le discriminateur
        real_labels = torch.ones(batch_size, 1).to(device)
        fake_labels = torch.zeros(batch_size, 1).to(device)

        # 🔹 1. Avec de vraies images
        outputs_real = discriminator(real_images, real_ages)
        d_loss_real = criterion(outputs_real.view(-1, 1), real_labels)
        d_loss_real.backward()

        # 🔹 2. Avec des images générées
        z = torch.randn(batch_size, z_dim).to(device)  # Générer du bruit pour le générateur
        fake_ages = real_ages + 30  # Ajouter un vieillissement fixe de 30 ans
        fake_images = generator(z, fake_ages)  # Générer une image avec l'âge vieillissant

        outputs_fake = discriminator(fake_images.detach(), fake_ages)  # Ne pas rétropropager dans le générateur
        d_loss_fake = criterion(outputs_fake.view(-1, 1), fake_labels)
        d_loss_fake.backward()

        optimizer_D.step()

        # 🔹 Mise à jour du générateur
        optimizer_G.zero_grad()
        outputs_fake_gen = discriminator(fake_images, fake_ages)
        g_loss = criterion(outputs_fake_gen.view(-1, 1), real_labels)
        g_loss.backward()

        optimizer_G.step()

        # Affichage périodique des résultats (toutes les 50 étapes)
        if (i + 1) % 50 == 0:
            print(f'Epoch [{epoch+1}/{num_epochs}], Batch [{i+1}/{len(train_loader)}], d_loss: {d_loss_real.item() + d_loss_fake.item():.4f}, g_loss: {g_loss.item():.4f}')
            show_images(real_images, fake_images, real_ages, fake_ages, epoch)

        batch_duration = time.time() - batch_start_time  # Temps écoulé pour ce batch
        print(f"Batch {i+1}, Durée du batch: {batch_duration:.2f} secondes")

    epoch_duration = time.time() - start_time  # Temps total pour une époque
    print(f"Durée totale de l'époque {epoch+1}: {epoch_duration:.2f} secondes")