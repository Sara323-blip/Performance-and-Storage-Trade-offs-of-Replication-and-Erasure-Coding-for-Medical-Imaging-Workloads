#!/usr/bin/env python3
"""
Fixed DICOM conversion with proper file metadata
"""

import os
import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid
from pydicom.filebase import DicomBytesIO

# Create output directory
output_dir = "./dicom_files"
os.makedirs(output_dir, exist_ok=True)

print("=" * 60)
print("CREATING SYNTHETIC DICOM FILES (FIXED VERSION)")
print("=" * 60)

# Create 100 synthetic DICOM files
num_files = 100
print(f"\n📝 Creating {num_files} synthetic DICOM files...")

for i in range(num_files):
    # Create file meta information (REQUIRED for valid DICOM)
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.2'  # CT Image Storage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    
    # Create dataset
    ds = Dataset()
    ds.file_meta = file_meta
    
    # Set Transfer Syntax explicitly
    ds.is_little_endian = True
    ds.is_implicit_VR = False
    
    # Required DICOM fields
    ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.2'
    ds.SOPInstanceUID = generate_uid()
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.PatientID = f'PATIENT_{i:04d}'
    ds.Modality = 'CT'
    
    # Image dimensions
    ds.Rows = 512
    ds.Columns = 512
    
    # Image settings
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 1  # signed
    ds.SamplesPerPixel = 1
    
    # Create random pixel data (512x512 = 262,144 pixels, 2 bytes each)
    pixel_data = np.random.randint(-1000, 1000, size=(512, 512), dtype=np.int16)
    ds.PixelData = pixel_data.tobytes()
    
    # Save the DICOM file using proper writer
    filename = f"{output_dir}/image_{i:04d}.dcm"
    ds.save_as(filename, write_like_original=False)
    
    if (i + 1) % 20 == 0:
        print(f"   Created {i+1}/{num_files} files")

print(f"\n✅ Created {num_files} synthetic DICOM files in {output_dir}/")

# Verify first file
test_file = f"{output_dir}/image_0000.dcm"
if os.path.exists(test_file):
    file_size = os.path.getsize(test_file) / 1024
    print(f"   First file size: {file_size:.0f} KB")
    
    # Try to read it back to verify
    try:
        ds = pydicom.dcmread(test_file)
        print(f"   ✅ Verified: Patient {ds.PatientID}, Modality {ds.Modality}")
    except Exception as e:
        print(f"   ⚠️ Read verification: {e}")
