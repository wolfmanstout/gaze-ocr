# gaze-ocr

The `gaze-ocr` package makes easy to apply OCR to wherever the user is
looking. This library is designed for voice control and is currently tied to
Dragonfly.

## Installation

NOTE: This package will eventually be shared on PyPI for easier installation.

1. Follow [instructions for installing
   screen-ocr](https://github.com/wolfmanstout/screen-ocr).
2. Install this package (e.g. `pip install -e <path to cloned repository>`).
3. Download the [latest
   Tobii.Interaction](https://www.nuget.org/packages/Tobii.Interaction/) package
   from NuGet (these instructions have been tested on 0.7.3).
4. Rename the file extension to .zip and expand the contents.
5. Copy these 3 DLLs to a directory of your choice:
   build/AnyCPU/Tobii.EyeX.Client.dll, lib/net45/Tobii.Interaction.Model.dll,
   lib/net45/Tobii.Interaction.Net.dll.
6. Ensure that the files are not blocked (right-click Properties, and if there
   is a "Security" section at the bottom, check the "Unblock" box.)

## Usage

1. Provide the path to the DLL directory when constructing an EyeTracker instance.
