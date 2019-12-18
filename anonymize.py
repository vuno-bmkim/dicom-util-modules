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
        # https://support.qmenta.com/hc/en-us/articles/209558109-What-is-DICOM-anonymization-

        self.attributes_to_be_removed = [
            "Institution Name",
            "Referring Physician Identification Sequence",
            "Physician(s) of Record", 
            "Physician(s) of Record Identification Sequence",
            "Performing Physician's Name",
            "Performing Physician Identification Sequence",
            "Name Of Physician(s) Reading Study",
            "Physician(s) Reading Study Identification Sequence",
            "Patient's Primary Language Code Seq",
            "Other Patient IDs",
            "Other Patient Names",
            "Other Patient IDs Sequence",
            "Patient's Address",
            "Patient's Mother's Birth Name",
            "Issuer Of Patient ID",
            "Patient's Birth Time",
            "Patient's Birth Name",
            "Country Of Residence",
            "Region Of Residence",
            "Patient Telephone Numbers",
            "Current Patient Location",
            "Patient Institution Residence",
            "Series Date",
            "Acquisition Date",
            "Overlay Date",
            "Curve Date",
            "Acquisition Date Time",
            "Series Time",
            "Acquisition Time",
            "Overlay Time",
            "Curve Time",
            "Institution Address",
            "Referring Physician's Address",
            "Referring Physician's Telephone Number",
            "Institutional Department Name",
            "Operators Name",
            "Date Time",
            "Date",
            "Time"
            ]
            # Boneage : "Patient's Age",

        self.attributes_to_be_blanked = [
            "Accession Number",
            "Patient's Birth Date",
            "Study Date",
            "Content Date",
            "Study Time",
            "Content Time",
            "Referring Physician's Name",
            "Study ID",
            "Patient's Name",
            "Patient ID",
            "Patient's Sex"
            ]

        self.attributes_to_be_replaced = [
            "Person's Name"
            ]

        ds = ds_original
        ds.remove_private_tags()
        ds.walk(self.remain_callback)
        return ds

    def remain_callback(self, dataset, data_element):
        if data_element.name in self.attributes_to_be_removed:
            del dataset[data_element.tag]
        if data_element.name in  self.attributes_to_be_blanked:
            #if data_element.VR == "DA":
            #    dataset[data_element.tag].value = '19000101'
            #else:
            dataset[data_element.tag].value = ''
        if data_element.name in self.attributes_to_be_replaced:
            dataset[data_element.tag].value = "Anonymized"


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
