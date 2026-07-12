# Getting started with image de-identification with Presidio

Presidio provides a simple way to de-identify image data by detecting and anonymizing personally identifiable information (PII). This guide shows you how to get started with image de-identification using Presidio's Python packages.

Presidio has two main modules for image de-identification: General purpose, and specifically for DICOM (medical) images.

## Simple flow - Python package

=== "Anonymize PII in images"

    1. Install presidio-image-redactor
    
        ```sh
        pip install presidio-image-redactor
        ```
       
    2. Redact PII from image
    
        ```py
        from presidio_image_redactor import ImageRedactorEngine
        from PIL import Image
        
        image = Image.open(path_to_image_file)
        
        redactor = ImageRedactorEngine()
        redactor.redact(image=image)
        ```

=== "Redact text PII in DICOM images"

    1. Install presidio-image-redactor
    
        ```sh
        pip install presidio-image-redactor
        ```
       
    2. Redact text PII from DICOM image
    
        ```py
        import pydicom
        from presidio_image_redactor import DicomImageRedactorEngine

        # Set input and output paths
        input_path = "path/to/your/dicom/file.dcm"
        output_dir = "./output"

        # Initialize the engine
        engine = DicomImageRedactorEngine()

        # Option 1: Redact from a loaded DICOM image
        dicom_image = pydicom.dcmread(input_path)
        redacted_dicom_image = engine.redact(dicom_image, fill="contrast")

        # Option 2: Redact from DICOM file
        engine.redact_from_file(input_path, output_dir, padding_width=25, fill="contrast")

        # Option 3: Redact from directory
        engine.redact_from_directory("path/to/your/dicom", output_dir, padding_width=25, fill="contrast")
        ```
---

## Simple flow - Docker container

Presidio provides a Docker containers that you can use to de-identify image data.

1. Download Docker image

```sh
docker pull ghcr.io/data-privacy-stack/presidio-image-redactor
```

2. Run container

```sh
docker run -d -p 5003:3000 ghcr.io/data-privacy-stack/presidio-image-redactor:latest
```

3. Use the API

```sh
curl -XPOST "http://localhost:5003/redact" -H "content-type: multipart/form-data" -F "image=@img.png" -F "data=\"{'color_fill':'255'}\"" > out.png 
```

## Read more

- [Installing Presidio](../installation.md)
- [PII detection in images](../image-redactor/index.md)
- [Samples](../samples/index.md)
- [Python API reference - Image Redactor](../api/image_redactor_python.md)
