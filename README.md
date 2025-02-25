# Data Organization Tool

## Description
Tool for the [MouseFeatureExtraction project](https://github.com/SimpingOjou/MouseFeatureExtraction), used to organize the data into the required arborescence.

## How to run
After installing the required libraries (via ```pip install -r requirements.txt```), launch the `Window.py` file.

## Parameters
- Side keyword: keyword contained only in the name of the side view CSV files
- Ventral keyword: keyword contained only in the name of the ventral view CSV files

- X name delimiters: Values just before and just after the name of the X in all the file names, used to extract it

## Arborescence created

```bash
Target folder
    |- Group 1
    |    |----- Timepoint 1
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
    |    |----- Timepoint 2
    |            ...
    |            
    |- Group 2
        ...
```

### Packaging into an executable

To 'build' the project (ie package into a frozen executable), pyinstaller can be used.

A virtual environment with all the libraries and dependencies has to be created (.venv folder). See [How to run](#how-to-run) for dependencies installation.

Then, the following commands creates the executable in the "dist" folder. 

**Windows**
`
pyinstaller.exe -c --onefile --icon="./src/Resources/Images/Logo.ico" --paths .\.venv\Lib\site-packages\ -n Kinematrix-DataOrganizationTool .\src\Window.py
`