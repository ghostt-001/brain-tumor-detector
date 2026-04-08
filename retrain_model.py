"""
Retrain the brain tumor detection model with better settings.

Dataset folder structure expected:
    dataset/
        Training/
            glioma_tumor/
            meningioma_tumor/
            no_tumor/
            pituitary_tumor/
        Testing/
            glioma_tumor/
            meningioma_tumor/
            no_tumor/
            pituitary_tumor/

Download dataset from: https://www.kaggle.com/datasets/sartajbhuvaji/brain-tumor-classification-mri

Run: python retrain_model.py
"""

import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.applications import EfficientNetB0
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
import os

# ── CONFIG ──
IMG_SIZE    = (224, 224)
BATCH_SIZE  = 32
EPOCHS      = 30
DATASET_DIR = "dataset"   # change this if your folder is named differently
NUM_CLASSES = 4

print("TensorFlow version:", tf.__version__)
print("Looking for dataset in:", os.path.abspath(DATASET_DIR))

# ── DATA AUGMENTATION ──
train_gen = ImageDataGenerator(
    rescale=1./255,
    rotation_range=15,
    zoom_range=0.15,
    width_shift_range=0.1,
    height_shift_range=0.1,
    horizontal_flip=True,
    fill_mode='nearest'
)

val_gen = ImageDataGenerator(rescale=1./255)

train_data = train_gen.flow_from_directory(
    os.path.join(DATASET_DIR, "Training"),
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode='categorical'
)

val_data = val_gen.flow_from_directory(
    os.path.join(DATASET_DIR, "Testing"),
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode='categorical'
)

print("\nClass indices (this is your CLASS_LABELS order for app.py):")
for label, idx in sorted(train_data.class_indices.items(), key=lambda x: x[1]):
    print(f"  [{idx}] {label}")

# ── BUILD MODEL (EfficientNetB0 transfer learning) ──
base_model = EfficientNetB0(
    weights='imagenet',
    include_top=False,
    input_shape=(224, 224, 3)
)

# Freeze base model first
base_model.trainable = False

model = models.Sequential([
    base_model,
    layers.GlobalAveragePooling2D(),
    layers.BatchNormalization(),
    layers.Dense(256, activation='relu'),
    layers.Dropout(0.4),
    layers.Dense(NUM_CLASSES, activation='softmax')
])

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

model.summary()

# ── CALLBACKS ──
callbacks = [
    EarlyStopping(patience=5, restore_best_weights=True, verbose=1),
    ReduceLROnPlateau(factor=0.3, patience=3, verbose=1),
    ModelCheckpoint("best_model.h5", save_best_only=True, verbose=1)
]

# ── PHASE 1: Train top layers only ──
print("\n=== Phase 1: Training top layers ===")
model.fit(
    train_data,
    validation_data=val_data,
    epochs=10,
    callbacks=callbacks
)

# ── PHASE 2: Fine-tune last 30 layers of base model ──
print("\n=== Phase 2: Fine-tuning ===")
base_model.trainable = True
for layer in base_model.layers[:-30]:
    layer.trainable = False

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

model.fit(
    train_data,
    validation_data=val_data,
    epochs=EPOCHS,
    callbacks=callbacks
)

# ── SAVE FINAL MODEL ──
model.save("final_model.h5")
print("\n✅ Model saved as final_model.h5")
print("\nIMPORTANT: Update CLASS_LABELS in app.py to match the order printed above!")
