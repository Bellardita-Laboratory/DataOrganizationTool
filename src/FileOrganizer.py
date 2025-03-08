import glob
import os
import shutil

from tqdm import tqdm
import regex as re
import numpy as np

def capture_variables_from_file(filepath:os.PathLike, structure_str:str, 
        delimiters_keywords:list[str]=['Batch', 'Dataset', 'Mouse', 'Run'], delimiter_opener:str='(', delimiter_closer:str=')',
        delimiter_structure_start:str=':'):
    """
        Get the filename, returns 
            - True if the structure matches the file name, False otherwise
            - The file name
            - A dictionnary with the part maching the delimiters_keywords (surrounded by the opener/closer) in the structure string
                If a part is not found, the corresponding key will have the whole file name as value
    """
    # Get the file name
    data_name_ext : str = os.path.basename(filepath)

    # Remove the file extension
    data_name, _ = os.path.splitext(data_name_ext)

    regexp = structure_str
    # Replace {keyword} by (.*) in the structure string to capture the corresponding part of the file name
    for keyword in delimiters_keywords:
        delimited_keyword = f'{delimiter_opener}{keyword}{delimiter_closer}'
        regexp = regexp.replace(delimited_keyword, f'(?P<{keyword}>.*)', 1)

        structured_delimited_keyword = f'(?P<found_pattern>\\{delimiter_opener}{keyword}{delimiter_structure_start}(?P<matched_struct>[^{delimiter_closer}]*)\\{delimiter_closer})'

        struct_match = re.search(structured_delimited_keyword, regexp)
        if struct_match is not None:
            required_struct = struct_match.group("matched_struct")
            found_pattern = struct_match.group("found_pattern")

            regexp = regexp.replace(found_pattern, f'(?P<{keyword}>{required_struct})', 1)

    name_match = re.search(regexp, data_name)
    
    if name_match is not None:
        match_dict : dict[str,str] = dict()

        for keyword in delimiters_keywords:
            try:
                match_dict[keyword] = name_match.group(keyword)
            except IndexError:
                match_dict[keyword] = data_name
    else:
        match_dict = None
    
    return name_match is not None, data_name, match_dict


class FileOrganizer:
    def __init__(self) -> None:
        self.side_keyword = None
        self.ventral_keyword = None
        self.data_folder_path = None
        self.target_folder_path = None
        self.csv_extension = None
        self.video_extension = None
        
        self.side_csv_filepaths = None
        self.ventral_csv_filepaths = None
        self.video_filepaths = None

        self.delimiters_keywords = None
        self.delimiter_opener = None
        self.delimiter_closer = None
        self.delimiter_structure_start = None


    def set_and_load_data_parameters(self, side_keyword:str, ventral_keyword:str,
                                    data_folder_path:os.PathLike, target_folder_path:os.PathLike,
                                    csv_extension:str, video_extension:str):
        """
            Set the data parameters and load the filepaths

            Returns True if the filepaths were loaded successfully (ie if at least on side view file was found)
        """
        self.side_keyword = side_keyword
        self.ventral_keyword = ventral_keyword

        self.data_folder_path = data_folder_path
        self.target_folder_path = target_folder_path
        self.csv_extension = csv_extension
        self.video_extension = video_extension

        # Load the filepaths to all the files in the corresponding folder
        self.side_csv_filepaths, self.ventral_csv_filepaths, self.video_filepaths = self._get_filepaths(self.data_folder_path, self.csv_extension, self.video_extension)

        return len(self.side_csv_filepaths) > 0

    def get_filenames(self, get_side:bool=False, get_ventral:bool=False, get_video:bool=False):
        """
            Get the names of all the files in the folder
        """
        all_names = []

        if get_side:
            side_names : list[str] = [os.path.splitext(os.path.basename(file))[0] for file in self.side_csv_filepaths]
            all_names += side_names
        
        if get_ventral:
            ventral_names : list[str] = [os.path.splitext(os.path.basename(file))[0] for file in self.ventral_csv_filepaths]
            all_names += ventral_names
        
        if get_video:
            video_names : list[str] = [os.path.splitext(os.path.basename(file))[0] for file in self.video_filepaths]
            all_names += video_names

        return all_names
    
    def get_names(self, use_regex:bool):
        """
            Get the names of the batch, dataset, mouse and run for each filepath loaded

            Returns an array of shape (n_files, 4) with the names of the batch, dataset, mouse and run for each file
        """
        # Associate the side views with the corresponding ventral views and video
        if use_regex:
            associated_paths_and_names = self._associate_files_from_structure_regex(verbose=False)
        else:
            associated_paths_and_names = self._associate_files_from_structure(verbose=False)

        # Get the names of the batch, dataset, mouse and run for each ventral file
        associated_names = np.array([(batch_name, dataset_name, mouse_name, run_name) 
                            for batch_name, dataset_name, mouse_name, run_name, _, _, _ in associated_paths_and_names])
    
        return associated_names
    

    def set_structure_str_parameters(self, structure_str:str):
        """
            Set the structure string parameters
        """
        self.structure_str = structure_str

    def set_structure_parameters(self, side_structure_dicts:list[dict[str,str]], ventral_structure_dicts:list[dict[str,str]], video_structure_dicts:list[dict[str,str]]):
        """
            Set the list of structure dictionaries for the side, ventral and video files
        """
        self._side_structure_dicts = side_structure_dicts
        self._ventral_structure_dicts = ventral_structure_dicts
        self._video_structure_dicts = video_structure_dicts
    
    def set_constraints(self, require_ventral_data:bool, require_video_data:bool):
        """
            Set the constraints for the organization
        """
        self.require_ventral_data = require_ventral_data
        self.require_video_data = require_video_data

    def set_delimiters(self, delimiters_keywords:list[str], 
                       delimiter_opener:str=None, delimiter_closer:str=None, delimiter_structure_start:str=None):
        """
            Set the delimiters for the structure string
        """
        self.delimiters_keywords = delimiters_keywords

        if delimiter_opener is not None:
            self.delimiter_opener = delimiter_opener
        
        if delimiter_closer is not None:
            self.delimiter_closer = delimiter_closer

        if delimiter_structure_start is not None:
            self.delimiter_structure_start = delimiter_structure_start

    def set_use_regex(self, use_regex:bool):
        """
            Set the use of regex for the association of the files
        """
        self.use_regex = use_regex
    

    def organize_files(self, side_folder_name:str='sideview', ventral_folder_name:str='ventralview', video_folder_name:str='video'):
        # Associate the side views with the corresponding ventral views and video
        if self.use_regex:
            associated_paths_and_names = self._associate_files_from_structure_regex()
        else:
            associated_paths_and_names = self._associate_files_from_structure()

        # Remove the mouse name and run name from the associated names (they are not needed for the folder structure)
        associated_paths = [(batch_name, dataset_name, side_csv_filepath, ventral_csv_filepath, video_filepath) 
                            for batch_name, dataset_name, _, _, side_csv_filepath, ventral_csv_filepath, video_filepath in associated_paths_and_names]
        
        # Copy the files to the corresponding folders
        self._copy_with_structure(self.target_folder_path, associated_paths, side_folder_name, ventral_folder_name, video_folder_name)

    
    def _get_filepaths(self, folder_path:os.PathLike, csv_extension:str, video_extension:str):
        """
            Get the filepaths to all the files in the corresponding folder
        """
        # Get the filepaths to all the files in the corresponding folder
        csv_filepaths = glob.glob(os.path.join('**','*'+csv_extension), root_dir=folder_path , recursive=True)
        video_filepaths = glob.glob(os.path.join('**','*'+video_extension), root_dir=folder_path , recursive=True)

        # Get the filepaths for the side and ventral views
        side_csv_filepaths : list[os.PathLike] = [os.path.join(folder_path, filepath) for filepath in csv_filepaths if self.side_keyword in filepath]
        ventral_csv_filepaths : list[os.PathLike] = [os.path.join(folder_path, filepath) for filepath in csv_filepaths if self.ventral_keyword in filepath]
        video_filepaths : list[os.PathLike] = [os.path.join(folder_path, filepath) for filepath in video_filepaths]

        return side_csv_filepaths, ventral_csv_filepaths, video_filepaths

    def _associate_files_from_structure_regex(self, verbose:bool=True):
        """
            Associate the side views with the corresponding ventral views and video if they exist
        """
        if self.side_csv_filepaths is None or self.ventral_csv_filepaths is None or self.video_filepaths is None:
            return []
        
        if self.delimiters_keywords is None or len(self.delimiters_keywords) == 0 or self.delimiter_opener is None or self.delimiter_closer is None or self.delimiter_structure_start is None:
            return []

        # Get the names of the batch, dataset and mouse for each ventral file
        ventral_csv_data : list[tuple[str,str,str,str]] = []
        for ventral_csv_filepath in self.ventral_csv_filepaths:
            match_found, file_name, captured_ventral_dict = capture_variables_from_file(ventral_csv_filepath, self.structure_str, self.delimiters_keywords, 
                                                                                        self.delimiter_opener, self.delimiter_closer, 
                                                                                        self.delimiter_structure_start)

            # If the structure doesn't match the file
            if not match_found:
                if verbose: print(f"Structure does not match the file {ventral_csv_filepath}")
                captured_ventral_tuple = tuple(file_name for _ in self.delimiters_keywords)
            else:
                # Tuple containing batch, dataset, mouse and run names
                captured_ventral_tuple = tuple(captured_ventral_dict[key] for key in self.delimiters_keywords)

            ventral_csv_data.append(captured_ventral_tuple)

        # Get the names of the batch, dataset and mouse for each video file
        video_data : list[tuple[str,str,str,str]] = []
        for video_filepath in self.video_filepaths:
            match_found, file_name, captured_video_dict = capture_variables_from_file(video_filepath, self.structure_str, self.delimiters_keywords, 
                                                                                      self.delimiter_opener, self.delimiter_closer, 
                                                                                      self.delimiter_structure_start)

            # If the structure doesn't match the file
            if not match_found:
                if verbose: print(f"Structure does not match the file {video_filepath}")
                captured_video_tuple = tuple(file_name for _ in self.delimiters_keywords)
            else:
                # Tuple containing batch, dataset, mouse and run names
                captured_video_tuple = tuple(captured_video_dict[key] for key in self.delimiters_keywords)

            video_data.append(captured_video_tuple)


        associated_paths : list[tuple[str,str,str,str, os.PathLike,os.PathLike|None,os.PathLike|None]] = []
        for side_csv_filepath in self.side_csv_filepaths:
            match_found, file_name, captured_side_dict = capture_variables_from_file(side_csv_filepath, self.structure_str, self.delimiters_keywords, 
                                                                                     self.delimiter_opener, self.delimiter_closer, 
                                                                                     self.delimiter_structure_start)

            if not match_found:
                if verbose: print(f"Structure does not match the file {side_csv_filepath}")
                captured_side_tuple = tuple(file_name for _ in self.delimiters_keywords)
            else:
                # Tuple containing batch, dataset, mouse and run names
                captured_side_tuple = tuple(captured_side_dict[key] for key in self.delimiters_keywords)

            # Get the corresponding video file
            ventral_correspondances = [self.ventral_csv_filepaths[i] for i in range(len(self.ventral_csv_filepaths)) 
                                    if captured_side_tuple == ventral_csv_data[i]]
            
            video_correspondances = [self.video_filepaths[i] for i in range(len(self.video_filepaths)) 
                                    if captured_side_tuple == video_data[i]]

            if verbose: print(captured_side_tuple)

            # Ensure existence of the corresponding files
            if len(ventral_correspondances) == 0:
                if verbose: print(f"No corresponding ventral view for this data")

                # Skip the file if the ventral view is required
                if self.require_ventral_data:
                    if verbose: print(f"Skipping {side_csv_filepath}")
                    continue

                ventral_correspondances = [None]

            if len(video_correspondances) == 0:
                if verbose: print(f"No corresponding video for this data")

                if self.require_video_data:
                    if verbose: print(f"Skipping {side_csv_filepath}")
                    continue

                video_correspondances = [None]

            # Ensure uniqueness of the corresponding files
            if len(ventral_correspondances) > 1:
                if verbose: print(f"Multiple ventral views for this data : {ventral_correspondances}")
                if verbose: print(f"Choosing the first one : {ventral_correspondances[0]}")
                ventral_correspondances = [ventral_correspondances[0]]

            if len(video_correspondances) > 1:
                if verbose: print(f"Multiple videos for this data : {video_correspondances}")

                # Get the video with no tracking if it exists
                no_track_vid = [filepath for filepath in video_correspondances if self.side_keyword not in filepath and self.ventral_keyword not in filepath]

                if len(no_track_vid) == 1:
                    if verbose: print(f"Choosing the video with no tracking (ie not containing {self.side_keyword} or {self.ventral_keyword}) : {no_track_vid[0]}")
                    video_correspondances = no_track_vid
                else:
                    if verbose: print(f"Choosing the first one : {video_correspondances[0]}")
                    video_correspondances = [video_correspondances[0]]

            # Get the corresponding filepaths
            ventral_csv_filepath = ventral_correspondances[0]
            video_filepath = video_correspondances[0]

            # Add the corresponding filepaths to the list
            batch_name, dataset_name, mouse_name, run_name = captured_side_tuple
            associated_paths.append((batch_name, dataset_name, mouse_name, run_name, side_csv_filepath, ventral_csv_filepath, video_filepath))

        return associated_paths
    
    def _associate_files_from_structure(self, verbose:bool=True):
        """
            Associate the side views with the corresponding ventral views and video if they exist
        """
        if self.side_csv_filepaths is None or self.ventral_csv_filepaths is None or self.video_filepaths is None:
            return []
        
        if self.delimiters_keywords is None or len(self.delimiters_keywords) == 0:
            return []

        # Get the names of the batch, dataset and mouse for each ventral file
        ventral_csv_data : list[tuple[str,str,str,str]] = []
        for i, ventral_csv_filepath in enumerate(self.ventral_csv_filepaths):
            ventral_struct_dict = self._ventral_structure_dicts[i]

            # Tuple containing batch, dataset, mouse and run names
            captured_ventral_tuple = tuple(ventral_struct_dict[key] for key in self.delimiters_keywords)

            ventral_csv_data.append(captured_ventral_tuple)

        # Get the names of the batch, dataset and mouse for each video file
        video_data : list[tuple[str,str,str,str]] = []
        for i, video_filepath in enumerate(self.video_filepaths):
            video_struct_dict = self._video_structure_dicts[i]

            # Tuple containing batch, dataset, mouse and run names
            captured_video_tuple = tuple(video_struct_dict[key] for key in self.delimiters_keywords)

            video_data.append(captured_video_tuple)


        associated_paths : list[tuple[str,str,str,str, os.PathLike,os.PathLike|None,os.PathLike|None]] = []
        for i, side_csv_filepath in enumerate(self.side_csv_filepaths):
            side_struct_dict = self._side_structure_dicts[i]
            
            # Tuple containing batch, dataset, mouse and run names
            captured_side_tuple = tuple(side_struct_dict[key] for key in self.delimiters_keywords)

            # Get the corresponding video file
            ventral_correspondances = [self.ventral_csv_filepaths[i] for i in range(len(self.ventral_csv_filepaths)) 
                                    if captured_side_tuple == ventral_csv_data[i]]
            
            video_correspondances = [self.video_filepaths[i] for i in range(len(self.video_filepaths)) 
                                    if captured_side_tuple == video_data[i]]

            if verbose: print(captured_side_tuple)

            # Ensure existence of the corresponding files
            if len(ventral_correspondances) == 0:
                if verbose: print(f"No corresponding ventral view for this data")

                # Skip the file if the ventral view is required
                if self.require_ventral_data:
                    if verbose: print(f"Skipping {side_csv_filepath}")
                    continue

                ventral_correspondances = [None]

            if len(video_correspondances) == 0:
                if verbose: print(f"No corresponding video for this data")

                if self.require_video_data:
                    if verbose: print(f"Skipping {side_csv_filepath}")
                    continue

                video_correspondances = [None]

            # Ensure uniqueness of the corresponding files
            if len(ventral_correspondances) > 1:
                if verbose: print(f"Multiple ventral views for this data : {ventral_correspondances}")
                if verbose: print(f"Choosing the first one : {ventral_correspondances[0]}")
                ventral_correspondances = [ventral_correspondances[0]]

            if len(video_correspondances) > 1:
                if verbose: print(f"Multiple videos for this data : {video_correspondances}")

                # Get the video with no tracking if it exists
                no_track_vid = [filepath for filepath in video_correspondances if self.side_keyword not in filepath and self.ventral_keyword not in filepath]

                if len(no_track_vid) == 1:
                    if verbose: print(f"Choosing the video with no tracking (ie not containing {self.side_keyword} or {self.ventral_keyword}) : {no_track_vid[0]}")
                    video_correspondances = no_track_vid
                else:
                    if verbose: print(f"Choosing the first one : {video_correspondances[0]}")
                    video_correspondances = [video_correspondances[0]]

            # Get the corresponding filepaths
            ventral_csv_filepath = ventral_correspondances[0]
            video_filepath = video_correspondances[0]

            # Add the corresponding filepaths to the list
            batch_name, dataset_name, mouse_name, run_name = captured_side_tuple
            associated_paths.append((batch_name, dataset_name, mouse_name, run_name, side_csv_filepath, ventral_csv_filepath, video_filepath))

        return associated_paths

    def _copy_with_structure(self, target_folder:str, associated_paths:list[tuple[str,str,os.PathLike,os.PathLike|None,os.PathLike|None]],
                            side_folder_name:str, ventral_folder_name:str, video_folder_name:str):
        """
            Create the folder strucure and copy the files in their corresponding folders
        """
        # Create the target folder if it does not exist
        if not os.path.exists(target_folder):
            os.makedirs(target_folder)

        for batch_name, dataset_name, side_csv_filepath, ventral_csv_filepath, video_filepath in tqdm(associated_paths):
            if batch_name == '':
                batch_name = self.default_batch_name
            
            # Create the batch folder if it does not exist
            batch_folder = os.path.join(target_folder, batch_name)
            if not os.path.exists(batch_folder):
                os.makedirs(batch_folder)

            # Create the dataset folder if it does not exist
            dataset_folder = os.path.join(batch_folder, dataset_name)
            if not os.path.exists(dataset_folder):
                os.makedirs(dataset_folder)

            # Create the side folder if it does not exist
            side_folder = os.path.join(dataset_folder, side_folder_name)
            if not os.path.exists(side_folder):
                os.makedirs(side_folder)

            # Create the ventral folder if it does not exist
            ventral_folder = os.path.join(dataset_folder, ventral_folder_name)
            if not os.path.exists(ventral_folder):
                os.makedirs(ventral_folder)

            # Create the video folder if it does not exist
            video_folder = os.path.join(dataset_folder, video_folder_name)
            if not os.path.exists(video_folder):
                os.makedirs(video_folder)


            ## Copy the files to the corresponding folders
            side_csv_target = os.path.join(side_folder, os.path.basename(side_csv_filepath))
            shutil.copy2(side_csv_filepath, side_csv_target)

            if ventral_csv_filepath is not None:
                ventral_csv_target = os.path.join(ventral_folder, os.path.basename(ventral_csv_filepath))
                shutil.copy2(ventral_csv_filepath, ventral_csv_target)
            
            if video_filepath is not None:
                video_target = os.path.join(video_folder, os.path.basename(video_filepath))
                shutil.copy2(video_filepath, video_target)
    

if __name__ == "__main__":
    folder_path = '.\\Data'
    target_folder = '.\\DataOrganized'
    side_keyword = 'sideview'
    ventral_keyword = 'ventralview'
    batch_name_delimiters = ('_Mouse[0-9]+_', '_.*_Corridor_.*_Corridor')
    dataset_name_delimiters = ('CnF_', '_Corridor')
    mouse_name_delimiter = ('ventral_', '_CnF')
    run_name_delimiters = ('eft_', 'DLC')

    # fo = FileOrganizer(side_keyword, ventral_keyword, dataset_name_delimiters, mouse_name_delimiter, run_name_delimiters, batch_name_delimiters)

    # fo.organize_files(folder_path, target_folder, csv_extension='.csv', video_extension='.mp4',
    #                   side_folder_name='sideview', ventral_folder_name='ventralview', video_folder_name='video')

    val = capture_variables_from_file('.\\Data\\Batch1\\CnF_1_ventral_1_eft_1_DLC.csv', '(Batch)_(Dataset)_ventral_1_eft_(Run)_DLC')
    print(val)

    for f in re.finditer('\\(Dataset:[^)(]*(?P<rs>\\((?:[^)(]+|(?P>rs))*\\))?[^)()]*\\)', 'Post_(Dataset:(WT|MU_C(x|X)|MU_Saline|.*))_jkhvb'):
        print(f)