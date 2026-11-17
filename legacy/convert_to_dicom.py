#!/usr/bin/env python3
"""
Convert MedMNIST images to DICOM format for MinIO storage
"""

import medmnist
import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import generate_uid
import os
import tempfile
from PIL import Image
import io

def numpy_to_dicom(image_array, patient_id, modality="CT"):
    """
    Convert a NumPy image array to a DICOM file object
    
    Args:
        image_array: 2D numpy array (grayscale image)
        patient_id: Patient identifier
        modality: CT, X-ray, MRI, etc.
    
    Returns:
        DICOM dataset ready to save or upload
    """
    # Ensure 8-bit image
    if image_array.dtype != np.uint8:
        # Normalize to 0-255 range
        image_array = ((image_array - image_array.min()) / 
                       (image_array.max() - image_array.min() + 1e-8) * 255).astype(np.uint8)
    
    ds = Dataset()
    
    # Required DICOM fields
    ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.2'  # CT Image Storage
    ds.SOPInstanceUID = generate_uid()
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.PatientID = patient_id
    ds.Modality = modality
    
    # Image dimensions
    ds.Rows, ds.Columns = image_array.shape[:2]
    ds.BitsAllocated = 8
    ds.BitsStored = 8
    ds.HighBit = 7
    ds.PixelRepresentation = 0  # unsigned
    ds.SamplesPerPixel = 1  # grayscale
    
    # Pixel data
    ds.PixelData = image_array.tobytes()
    
    return ds

def save_dicom_to_temp(ds, filename):
    """Save DICOM dataset to a temporary file"""
    ds.save_as(filename)
    return filename

def main():
    print("=" * 60)
    print("CONVERTING MEDMNIST TO DICOM")
    print("=" * 60)
    
    # Load ChestMNIST dataset
    print("\n📥 Loading ChestMNIST dataset...")
    chest_dataset = medmnist.ChestMNIST(root='./data', split='train', download=True)
    images = chest_dataset.imgs  # shape: (n_samples, 28, 28)
    labels = chest_dataset.labels
    
    print(f"   Images loaded: {len(images)}")
    print(f"   Image shape: {images[0].shape}")
    
    # Convert first 1000 images to DICOM (adjust based on your laptop storage)
    num_to_convert = min(1000, len(images))
    print(f"\n🔄 Converting {num_to_convert} images to DICOM format...")
    
    # Create output directory for DICOM files (optional, or we can upload directly)
    output_dir = "./dicom_files"
    os.makedirs(output_dir, exist_ok=True)
    
    converted_count = 0
    for i in range(num_to_convert):
        patient_id = f"PATIENT_{i:04d}"
        modality = "CT" if labels[i][0] == 0 else "XR"  # 0 = normal, 1 = pneumonia
        
        # Convert to DICOM
        ds = numpy_to_dicom(images[i], patient_id, modality)
        
        # Save to file
        filename = f"{output_dir}/image_{i:04d}_{patient_id}.dcm"
        ds.save_as(filename)
        converted_count += 1
        
        if (i + 1) % 100 == 0:
            print(f"   Converted {i+1}/{num_to_convert} images")
    
    print(f"\n✅ Converted {converted_count} DICOM files to {output_dir}/")
    print(f"   Total size: ~{converted_count * 28 * 28 / 1024:.1f} KB")
    
    # Display sample info
    print("\n📋 Sample DICOM file info:")
    sample_file = f"{output_dir}/image_0000_PATIENT_0000.dcm"
    ds = pydicom.dcmread(sample_file)
    print(f"   Patient ID: {ds.PatientID}")
    print(f"   Modality: {ds.Modality}")
    print(f"   Image size: {ds.Rows} x {ds.Columns}")
    print(f"   SOP Class UID: {ds.SOPClassUID}")
    
    return output_dir

if __name__ == "__main__":
    dicom_dir = main()
    print(f"\n💡 Next step: Upload these DICOM files to MinIO")
    print(f"   Run: python3 upload_to_minio.py --dir {dicom_dir}")
