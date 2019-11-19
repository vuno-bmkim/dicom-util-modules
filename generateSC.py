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
import cv2

class SCUtil():
    def get_base_directory(self):
        return os.path.dirname(os.path.abspath(__file__))

    def genActivationMap(self, probability, prob_threshold=0.5, alpha=1., gaussianKernel=101):
        dtype = np.uint8
        max_bin = 2.55
        int_probability = (probability * max_bin).astype(dtype)
        int_prob_threshold = 0  # prob_threshold*max_bin
        thresh_classmap = int_probability
        print('multi-class : ', thresh_classmap.min(), thresh_classmap.max())
        thresh_classmap = thresh_classmap.clip(min=0)
        alpha_channel = (thresh_classmap * alpha).astype(dtype)
        color_classmap = cv2.applyColorMap(thresh_classmap, cv2.COLORMAP_JET)
        b_channel, g_channel, r_channel = cv2.split(color_classmap)
        out = cv2.merge((b_channel, g_channel, r_channel, alpha_channel))
        return out

    def update_pixel_image(self, ds, heatmap_path, overlay_opacity, text_to_draw=None):
        if ds.file_meta.TransferSyntaxUID.is_compressed:
            ds.decompress()
        # rescale dicom image
        pixel_array = ds.pixel_array.astype(float)
        photometric_interpretation = ds.PhotometricInterpretation
        window_width = ds.WindowWidth if (
            'WindowWidth' in ds and not isinstance(ds.WindowWidth, str)
            ) else (pixel_array.max() - pixel_array.min())
        window_center = ds.WindowCenter if (
            'WindowCenter' in ds and not isinstance(ds.WindowCenter, str)
            ) else (pixel_array.max() + pixel_array.min())/2
        window_max = window_center + window_width * 1/2
        window_min = window_center - window_width * 1/2
        # rescale each pixel from 0.~n to 0~255
        if photometric_interpretation == "MONOCHROME1":
            scaled_2d_img = (window_max - np.clip(
                pixel_array, window_min, window_max)) / (
                    window_width) * 255.0
            scaled_2d_img = np.uint8(scaled_2d_img)
            # create image by interpreting array by
            # L mode (8-bit pixels grayscale)
            # https://pillow.readthedocs.io/en/4.2.x/handbook/concepts.html#concept-modes
            background_img = Image.fromarray(scaled_2d_img, 'L')
        elif photometric_interpretation == "MONOCHROME2":
            scaled_2d_img = (np.clip(
                pixel_array, window_min, window_max) - window_min) / (
                    window_width) * 255.0
            scaled_2d_img = np.uint8(scaled_2d_img)
            background_img = Image.fromarray(scaled_2d_img, 'L')
        elif photometric_interpretation == "RGB":
            scaled_2d_img = np.uint8(pixel_array)
            background_img = Image.fromarray(scaled_2d_img, "RGB")

        overlay_img = Image.new('RGBA', background_img.size)
        overlay_img.paste(background_img, (0, 0))

        # Create overlay image
        if heatmap_path is not None:
            #heatmap_img = Image.open(heatmap_path, 'r')
            #
            #npa = np.array(heatmap_img)[...]
            npa = cv2.imread(heatmap_path, -1)
            heatmap_img = self.genActivationMap(npa)
            cv2.imwrite(heatmap_path.replace(".png", "_2.png"), heatmap_img)
            heatmap_img = Image.open(heatmap_path.replace(".png", "_2.png"), 'r')
            heatmap_img = heatmap_img.resize(background_img.size)
            if heatmap_img.mode != 'RGBA':
                foreground_img = heatmap_img.convert('RGBA')
            else:
                foreground_img = heatmap_img.copy()
            _, _, _, alpha = foreground_img.split()
            alpha_updated = ImageEnhance.Brightness(alpha).enhance(
                overlay_opacity)
            foreground_img.putalpha(alpha_updated)
            overlay_img.paste(foreground_img, (0, 0), mask=foreground_img)

        if text_to_draw is not None:
            FONT_PATH = "{}/fonts/NotoSansCJKkr-Medium.otf".format(
                self.get_base_directory())
            background_width = overlay_img.size[0]
            background_height = overlay_img.size[1]
            font_size = int(
                40 * (background_width + background_height) / (2000))
            fnt = ImageFont.truetype(FONT_PATH, font_size)
            draw = ImageDraw.Draw(overlay_img)
            w, h = draw.textsize(text_to_draw, font=fnt)
            pos_x = (background_width-w) * 1/2
            pos_y = (background_height-h)*47/50
            stroke_border = 3
            stroke_fill = (255, 255, 255)
            text_fill = (0, 0, 0)
            for i in range(-stroke_border, stroke_border):
                for j in range(-stroke_border, stroke_border):
                    draw.text(
                        (pos_x-i, pos_y-j), text_to_draw, font=fnt,
                        fill=stroke_fill)
            draw.text(
                (pos_x, pos_y), text_to_draw, font=fnt, fill=text_fill)

        # Update pixel data
        npa = np.array(overlay_img)[..., :3]
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
        # C.11.2.1.2.2 : delete VOI LUT attributes
        # which is used only for MONOCHROME1 and MONOCHROME2
        voi_lut_attributes = ['VOILUTFunction', 'WindowCenter', 'WindowWidth']
        for attr in voi_lut_attributes:
            if attr in ds:
                delattr(ds, attr)
        return ds

    def update_tag(self, ds):
        file_meta = ds.file_meta
        file_meta.MediaStorageSOPClassUID = \
            MultiframeTrueColorSecondaryCaptureImageStorage
        sop_instance_uid = pydicom.uid.generate_uid()
        file_meta.MediaStorageSOPInstanceUID = sop_instance_uid
        file_meta.ImplementationClassUID = pydicom.uid.generate_uid()
        ds.file_meta = file_meta
        ds.SOPClassUID = MultiframeTrueColorSecondaryCaptureImageStorage
        ds.SOPInstanceUID = sop_instance_uid
        ds.ConversionType = "WSD"
        # ds.Modality = "OT"
        ds.SecondaryCaptureDeviceManufacturer = "VUNO"
        ds.SecondaryCaptureDeviceManufacturerModelName = "VN-M-02"
        ds.SecondaryCaptureDeviceSoftwareVersions = "1.0.0"
        # Update Series Instance UID
        # Don't change Patient ID and Study Instnace UID
        # for specifying relationship b/w original file
        ds.SeriesInstanceUID = \
            "{}.1".format(ds.SeriesInstanceUID[:61]) if 'SeriesInstanceUID' in ds else None
        #ds.SeriesDate = inference_result['analysis_date']
        #ds.SeriesTime = inference_result['analysis_time']
        ds.SeriesDescription = "VUNO MED Analysis Result"
        # ds.SeriesDescription = finding['analysis_result']
        ds.ImageComments = "VUNO MED Analysis Result : abnormal"
        ds.NumberOfFrames = 1
        ds.BurnedInAnnotation = "NO"
        ds.FrameTime = 0
        ds.FrameIncrementPointer = 0x00181063
        return ds

if __name__ == '__main__':
    """
    python img2dicom.py "<INPUT_DIR_PATH>" "<OUTPUT_DIR_PATH>"
    """
    input_dir_path = sys.argv[1]
    output_dir_path = sys.argv[2]
    img_path = glob.glob(os.path.join(input_dir_path, "*.png"))[0]
    dcm_path = glob.glob(os.path.join(input_dir_path, "*.dcm"))[0]

    ds = dcmread(dcm_path)
    sc_util = SCUtil()
    ds = sc_util.update_pixel_image(
        ds=ds,
        heatmap_path=img_path,
        overlay_opacity=0.6,
        text_to_draw="Analyzed")
    ds = sc_util.update_tag(
        ds=ds)
    output_path = os.path.join(
        output_dir_path, 
        dcm_path.replace(input_dir_path, ""))
    ds.save_as(output_path, write_like_original=False)
