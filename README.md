# Data Organization Tool

## Description
Tool for the [MouseFeatureExtraction project](https://github.com/SimpingOjou/MouseFeatureExtraction), used to organize the data into the required arborescence.

## How to run
After installing the required libraries (via ```pip install -r requirements.txt```), launch the `Window.py` file.

## Arborescence created

```bash
Target folder
    |- Batch 1
    |    |----- Dataset 1
    |    |        |--------- Side view
    |    |        |            |---Mouse 1 run 1 (.csv)
    |    |        |            |---Mouse 1 run 2 (.csv)
    |    |        |            ...
    |    |        |--------- Ventral view
    |    |        |            |---Mouse 1 run 1 (.csv)
    |    |        |            |---Mouse 1 run 2 (.csv)
    |    |        |            ...
    |    |        |--------- Video
    |    |                    |---Mouse 1 run 1 (.csv)
    |    |                    |---Mouse 1 run 2 (.csv)
    |    |                    ...
    |    |
    |    |----- Dataset 2
    |            ...
    |            
    |- Batch 2
        ...
```

## Parameters
- Side keyword: keyword contained only in the name of the side view CSV files
- Ventral keyword: keyword contained only in the name of the ventral view CSV files

- X name delimiters: Values just before and just after the name of the X in all the file names, used to extract it