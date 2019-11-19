import pydicom
from pydicom import dcmread
from pydicom.dataset import Dataset, DataElement, Tag, FileDataset
from pydicom.uid import JPEGLossless
from pydicom._storage_sopclass_uids import (
    MultiframeTrueColorSecondaryCaptureImageStorage)
import glob
import os
import sys
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
from datetime import datetime
import numpy as np


class DicomUtil:
    def create_base_ds(self, output_name):
        file_meta = Dataset()
        file_meta.MediaStorageSOPClassUID = \
            MultiframeTrueColorSecondaryCaptureImageStorage
        file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
        file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
        ds = FileDataset(
            output_name, {}, file_meta=file_meta, preamble=b"\0" * 128)
        ds.is_little_endian = True
        ds.is_implicit_VR = False
        return ds

    def add_sop_common(self, ds, now):
        ds.SOPClassUID = MultiframeTrueColorSecondaryCaptureImageStorage
        ds.SOPInstanceUID = ds.file_meta.MediaStorageSOPInstanceUID
        ds.SpecificCharacterSet = "ISO_IR 100"
        ds.InstanceCreationDate = now.date().strftime("%Y%m%d")
        ds.InstanceCreationTime = now.time().strftime("%H%M%S")
        return ds

    def add_patient(self, ds):
        ds.PatientID = ""
        ds.PatientName = ""
        ds.PatientBirthDate = ""
        return ds

    def add_general_study(self, ds, now):
        ds.StudyInstanceUID = pydicom.uid.generate_uid()
        ds.AccessionNumber = ""
        ds.StudyDate = now.date().strftime("%Y%m%d")
        ds.StudyTime = now.time().strftime("%H%M%S")
        return ds

    def add_general_series(self, ds, now):
        ds.SeriesInstanceUID = pydicom.uid.generate_uid()
        ds.SeriesDate = now.date().strftime("%Y%m%d")
        ds.SeriesTime = now.time().strftime("%H%M%S")
        ds.SeriesNumber = 1
        ds.SeriesDescription = ""
        return ds

    def add_general_equipment(self, ds):
        ds.Manufacturer = ""
        ds.ManufacturerModelName = ""
        ds.SoftwareVersions = ""
        return ds

    def add_sc_equiment(self, ds):
        ds.Modality = "SC"  
        return ds

    def add_image_pixel(self, ds, path):
        img = Image.open(path, 'r')
        npa = np.array(img)[..., :3]
        # Correct for the trailing NULL byte padding for odd length data
        pixel_data = npa.tobytes() + b'\x00' \
            if(len(npa.tobytes()) % 2 != 0) else npa.tobytes()
        ds.PixelData = pixel_data
        # Update pixel image information by changing pixel data
        ds.SamplesPerPixel = 3
        ds.PhotometricInterpretation = "RGB"
        ds.PlanarConfiguration = 0
        ds.Rows, ds.Columns, _ = npa.shape
        (ds.BitsAllocated, ds.BitsStored, ds.HighBit) = (8, 8, 7)
        ds.PixelRepresentation = 0
        return ds


if __name__ == '__main__':
    """
    python img2dicom.py "<IMGS_DIR_PATH>" "<OUTPUT_DIR_PATH>"
    """
    img_dir_path = sys.argv[1]
    output_dir_path = sys.argv[2]
    img_path_list = glob.glob(os.path.join(img_dir_path, "*.png"))
    img_path_list += glob.glob(os.path.join(img_dir_path, "*.jpg"))
    img_path_list += glob.glob(os.path.join(img_dir_path, "*.jpeg"))
    print("# of Files : {}".format(len(img_path_list)))
    for path in img_path_list:
        output_path = os.path.join(
            output_dir_path, 
            path.replace(img_dir_path, "")\
                .replace(".png", ".dcm")\
                .replace(".jpg", ".dcm")\
                .replace(".jpeg", ".dcm"))
        output_name = output_path.replace(output_dir_path, "")
        now = datetime.now()
        du = DicomUtil()
        ds = du.create_base_ds(output_name)
        ds = du.add_sop_common(ds, now)
        ds = du.add_patient(ds)
        ds = du.add_general_study(ds, now)
        ds = du.add_general_series(ds, now)
        ds = du.add_general_equipment(ds)
        ds = du.add_sc_equiment(ds)
        ds = du.add_image_pixel(ds, path)
        ds.save_as(output_path, write_like_original=False)

    