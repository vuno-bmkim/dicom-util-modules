
import os
import tempfile
import datetime
import pydicom
from pydicom.dataset import Dataset, FileDataset
import sys
import glob
from pydicom import dcmread

class AnonymizeHelper:
    def anonymize(self, ds_original):
        # file_meta = Dataset()
        # file_meta.TransferSyntaxUID = ds_original.file_meta.TransferSyntaxUID
        # file_meta.MediaStorageSOPClassUID = \
        #     ds_original.file_meta.MediaStorageSOPClassUID
        # file_meta.MediaStorageSOPInstanceUID = \
        #     ds_original.file_meta.MediaStorageSOPInstanceUID
        
        # BoneAge
        self.attributes_list = ["Patient's Age", "Patient's Sex", 'Photometric Interpretation', 'Rows', 'Columns', 'Bits Allocated', 'Bits Stored', 'Pixel Data', 'Window Center', 'Window Width'] 
        # BoneAge 추가
        self.attributes_list += ["Samples per Pixel", "Pixel Representation"]  
        # Gravuty
        self.attributes_list += ['SOP Class UID', 'SOP Instance UID', "Study Instance UID", "Study Description", "Samples Per Pixel", "High Bit", "Pixel Representation", 
                                'Series Instance UID', 'Planar Configuration'] #   "Patient's Name"
        # SC
        self.attributes_list += ['Secondary Capture Device Manufacturer', 'Secondary Capture Device Manufacturers Model Name', 'Secondary Capture Device Software Versions']

        # 추가
        self.attributes_list += ['Specific Character Set', 'Modality', 'Body Part Examined', 'Slice Thickness', 'Image Orientation Patient']
        self.attributes_list += ['Study Date', 'Study Time', 'Accession Number', 'Series Number', 'Series Description']


        ds = ds_original
        ds.remove_private_tags()
        ds.walk(self.remain_callback)
        # ds.file_meta = file_meta
        ds = self.fill_required_tag(ds)
        return ds

    def fill_required_tag(self, ds):
        # Patient Module
        if "PatientName" not in ds:
            ds.PatientName = ""
        if "PatientID" not in ds:
            ds.PatientID = "1"
        if "PatientBirthDate" not in ds:
            ds.PatientBirthDate = ""
        if "PatientSex" not in ds:
            ds.PatientSex = ""
        # General Study Module
        if "StudyDate" not in ds:
            ds.StudyDate = ""
        if "StudyTime" not in ds:
            ds.StudyTime = ""
        if "ReferringPhysicianName" not in ds:
            ds.ReferringPhysicianName = ""
        if "StudyID" not in ds:
            ds.StudyID = ""
        if "AccessionNumber" not in ds:
            ds.AccessionNumber = "1"
        # General Series Module
        if "SeriesNumber" not in ds:
            ds.SeriesNumber = None
        # General Image Module
        if "InstanceNumber" not in ds:
            ds.InstanceNumber = ""
        ds.StudyDescription = ""
        ds.SeriesDescription = ""
        return ds

    def remain_callback(self, dataset, data_element):
        if data_element.name not in self.attributes_list:
            del dataset[data_element.tag]

if __name__ == '__main__':
    """
    python img2dicom.py "<INPUT_DIR_PATH>" "<OUTPUT_DIR_PATH>"
    """
    input_dir_path = sys.argv[1]
    output_dir_path = sys.argv[2]
    dcm_path_list = glob.glob(os.path.join(input_dir_path, "*.dcm"))

    for path in dcm_path_list:
        output_path = os.path.join(
            output_dir_path, 
            path.replace(input_dir_path, ""))
        ds = dcmread(path)
        an_helper = AnonymizeHelper()
        ds = an_helper.anonymize(ds)
        ds.save_as(output_path, write_like_original=False)
