"""Generate a synthetic CT-like DICOM dataset.

Default: 100 files of 512 x 512 pixels at 16 bits, about 512 KB each, which is the size of a typical
CT slice. (The first version of the study used 256 x 256, about 129 KB, which is a quarter of that.)
Pixel data are smooth structure plus noise, seeded, so files are reproducible and not constant.

Usage: python -m bench.dataset --out dicom_files --count 100 --rows 512 --cols 512 --seed 0
"""
import argparse
import os

import numpy as np
from pydicom import dcmwrite
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid


def make_slice(rng, rows, cols, index):
    yy, xx = np.mgrid[0:rows, 0:cols]
    cy, cx = rows / 2.0, cols / 2.0
    r = np.sqrt(((yy - cy) / (rows / 2.0)) ** 2 + ((xx - cx) / (cols / 2.0)) ** 2)
    body = np.where(r < 0.85, 40.0, -1000.0)               # soft tissue inside, air outside
    organ = 60.0 * np.exp(-(((yy - cy) ** 2 + (xx - cx - 30) ** 2) / (2 * (rows / 8.0) ** 2)))
    noise = rng.normal(0, 12.0, size=(rows, cols))
    arr = np.clip(body + organ + noise + index % 7, -1024, 3071)
    return arr.astype(np.int16)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dicom_files")
    ap.add_argument("--count", type=int, default=100)
    ap.add_argument("--rows", type=int, default=512)
    ap.add_argument("--cols", type=int, default=512)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    study_uid, series_uid = generate_uid(), generate_uid()
    for i in range(a.count):
        meta = FileMetaDataset()
        meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.2"   # CT Image Storage
        meta.MediaStorageSOPInstanceUID = generate_uid()
        meta.TransferSyntaxUID = ExplicitVRLittleEndian
        ds = Dataset()
        ds.file_meta = meta
        ds.is_little_endian, ds.is_implicit_VR = True, False
        ds.PatientID, ds.PatientName, ds.Modality = f"P{i:04d}", f"Synthetic^{i}", "CT"
        ds.SeriesNumber, ds.InstanceNumber = 1, i
        ds.StudyInstanceUID, ds.SeriesInstanceUID = study_uid, series_uid
        ds.SOPClassUID, ds.SOPInstanceUID = meta.MediaStorageSOPClassUID, meta.MediaStorageSOPInstanceUID
        ds.Rows, ds.Columns = a.rows, a.cols
        ds.BitsAllocated, ds.BitsStored, ds.HighBit = 16, 16, 15
        ds.PixelRepresentation, ds.SamplesPerPixel = 1, 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.PixelData = make_slice(rng, a.rows, a.cols, i).tobytes()
        dcmwrite(os.path.join(a.out, f"image_{i:04d}.dcm"), ds, write_like_original=False)
    size = os.path.getsize(os.path.join(a.out, "image_0000.dcm"))
    print(f"wrote {a.count} files of {size / 1024:.0f} KB ({a.rows}x{a.cols}) to {a.out}")


if __name__ == "__main__":
    main()
