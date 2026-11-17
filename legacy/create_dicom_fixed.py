#!/usr/bin/env python3
"""
Create synthetic DICOM files with proper metadata
"""

import os
import numpy as np
from pydicom import dcmwrite
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

# Create output directory
output_dir = "./dicom_files"
os.makedirs(output_dir, exist_ok=True)

print("=" * 60)
print("CREATING SYNTHETIC DICOM FILES (FIXED VERSION)")
print("=" * 60)

num_files = 100
print(f"\n📝 Creating {num_files} DICOM files...")

for i in range(num_files):
    # Create File Meta Information (REQUIRED for valid DICOM)
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.2'  # CT Image Storage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    
    # Create main dataset
    ds = Dataset()
    ds.file_meta = file_meta
    ds.is_little_endian = True
    ds.is_implicit_VR = False
    
    # Basic patient info
    ds.PatientID = f'PATIENT_{i:04d}'
    ds.PatientName = f'Name_{i}'
    ds.Modality = 'CT'
    ds.SeriesNumber = 1
    ds.InstanceNumber = i
    ds.SeriesInstanceUID = generate_uid()
    ds.StudyInstanceUID = generate_uid()
    ds.SOPClassUID = file_meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    
    # Image dimensions (256x256 pixels)
    ds.Rows = 256
    ds.Columns = 256
    
    # Pixel data (random values simulating CT numbers)
    # CT numbers range from -1000 to +1000 Hounsfield Units
    pixel_array = np.random.randint(-1000, 1000, (256, 256), dtype=np.int16)
    ds.PixelData = pixel_array.tobytes()
    
    # Pixel metadata
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 1  # signed
    ds.SamplesPerPixel = 1
    
    # Save the DICOM file
    filename = f"{output_dir}/image_{i:04d}.dcm"
    dcmwrite(filename, ds, write_like_original=False)
    
    if (i + 1) % 20 == 0:
        print(f"   Created {i+1}/{num_files} files")

# Show results
if os.path.exists(f"{output_dir}/image_0000.dcm"):
    file_size = os.path.getsize(f"{output_dir}/image_0000.dcm") / 1024
    total_size = num_files * file_size / 1024
    print(f"\n✅ Created {num_files} DICOM files")
    print(f"   File size: {file_size:.0f} KB each")
    print(f"   Total size: {total_size:.1f} MB")
    print(f"   Location: {output_dir}/")
else:
    print("\n❌ Failed to create files")
