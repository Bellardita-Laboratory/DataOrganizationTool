
import glob
import os
import shutil

from tqdm import tqdm
import regex as re

def get_common_data_name_from_path(filepath:os.PathLike, first_name_delimiter:str, last_name_delimiter:str):
    """
        Get the filename, returns the part between the delimiters if it exists in the filename
        Otherwise returns the whole file name
    """
    # Get the file name
    data_name_ext : str = os.path.basename(filepath)

    # Remove the file extension
    data_name, _ = os.path.splitext(data_name_ext)

    # Get the part of the file name between the first occurence of the first delimiter and the first occurence of the last delimiter
    regexp = f'(?<={first_name_delimiter})((.*)(?={last_name_delimiter}))'

    name_match = re.search(regexp, data_name)

    if name_match is not None:
        common_data_name = name_match.group()
    else:
        common_data_name = data_name
    
    return common_data_name

class FileOrganizer:
    def set_and_load_data_parameters(self,side_keyword:str, ventral_keyword:str,
                                    data_folder_path:os.PathLike, target_folder_path:os.PathLike,
                                    csv_extension:str, video_extension:str):
        """
            Set the data parameters and load the filepaths
        """
        self.side_keyword = side_keyword
        self.ventral_keyword = ventral_keyword

        self.data_folder_path = data_folder_path
        self.target_folder_path = target_folder_path
        self.csv_extension = csv_extension
        self.video_extension = video_extension

        # Load the filepaths to all the files in the corresponding folder
        self.side_csv_filepaths, self.ventral_csv_filepaths, self.video_filepaths = self._get_filepaths(self.data_folder_path, self.csv_extension, self.video_extension)

    def set_structure_parameters(self, default_batch_name:str,
                                    dataset_name_delimiters:tuple[str,str], mouse_name_delimiters:tuple[str,str], run_name_delimiters:tuple[str,str],
                                    batch_name_delimiters:tuple[str,str]|None):
        """
            Set the structure parameters
        """    
        self.dataset_name_delimiters = dataset_name_delimiters
        self.mouse_name_delimiters = mouse_name_delimiters
        self.run_name_delimiters = run_name_delimiters
        self.batch_name_delimiters = batch_name_delimiters

        self.default_batch_name = default_batch_name
    
    def get_names(self):
        """
            Get the names of the batch, dataset, mouse and run for each filepath loaded
        """
        # Associate the side views with the corresponding ventral views and video
        associated_paths_and_names = self._associate_files(self.side_csv_filepaths, self.ventral_csv_filepaths, self.video_filepaths, False, False, verbose=False)

        # Get the names of the batch, dataset, mouse and run for each ventral file
        associated_names = [(batch_name, dataset_name, mouse_name, run_name) 
                            for batch_name, dataset_name, mouse_name, run_name, _, _, _ in associated_paths_and_names]
    
        return associated_names

    def organize_files(self, side_folder_name:str='sideview', ventral_folder_name:str='ventralview', video_folder_name:str='video',
                       require_ventral_data:bool=False, require_video_data:bool=False):
        # Associate the side views with the corresponding ventral views and video
        associated_paths_and_names = self._associate_files(self.side_csv_filepaths, self.ventral_csv_filepaths, self.video_filepaths, require_ventral_data, require_video_data)

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

    def _associate_files(self, side_csv_filepaths:list[os.PathLike], ventral_csv_filepaths:list[os.PathLike], video_filepaths:list[os.PathLike],
                         require_ventral_data:bool, require_video_data:bool, verbose:bool=True):
        """
            Associate the side views with the corresponding ventral views and video if they exist
        """
        # Get the names of the batch, dataset and mouse for each ventral file
        ventral_csv_data : list[tuple[str,str,str,str]] = []
        for ventral_csv_filepath in ventral_csv_filepaths:
            if self.batch_name_delimiters is not None:
                batch_name = get_common_data_name_from_path(ventral_csv_filepath, self.batch_name_delimiters[0], self.batch_name_delimiters[1])
            else:
                batch_name = ''
            
            dataset_name = get_common_data_name_from_path(ventral_csv_filepath, self.dataset_name_delimiters[0], self.dataset_name_delimiters[1])
            mouse_name = get_common_data_name_from_path(ventral_csv_filepath, self.mouse_name_delimiters[0], self.mouse_name_delimiters[1])
            run_name = get_common_data_name_from_path(ventral_csv_filepath, self.run_name_delimiters[0], self.run_name_delimiters[1])
            ventral_csv_data.append((batch_name, dataset_name, mouse_name, run_name))

        # Get the names of the batch, dataset and mouse for each video file
        video_data : list[tuple[str,str,str,str]] = []
        for video_filepath in video_filepaths:
            if self.batch_name_delimiters is not None:
                batch_name = get_common_data_name_from_path(video_filepath, self.batch_name_delimiters[0], self.batch_name_delimiters[1])
            else:
                batch_name = ''
            
            dataset_name = get_common_data_name_from_path(video_filepath, self.dataset_name_delimiters[0], self.dataset_name_delimiters[1])
            mouse_name = get_common_data_name_from_path(video_filepath, self.mouse_name_delimiters[0], self.mouse_name_delimiters[1])
            run_name = get_common_data_name_from_path(video_filepath, self.run_name_delimiters[0], self.run_name_delimiters[1])
            video_data.append((batch_name, dataset_name, mouse_name, run_name))


        associated_paths : list[tuple[str,str,str,str, os.PathLike,os.PathLike|None,os.PathLike|None]] = []
        for side_csv_filepath in side_csv_filepaths:
            # Get the names of the batch, dataset and mouse
            if self.batch_name_delimiters is not None:
                batch_name = get_common_data_name_from_path(side_csv_filepath, self.batch_name_delimiters[0], self.batch_name_delimiters[1])
            else:
                batch_name = ''
            
            dataset_name = get_common_data_name_from_path(side_csv_filepath, self.dataset_name_delimiters[0], self.dataset_name_delimiters[1])
            mouse_name = get_common_data_name_from_path(side_csv_filepath, self.mouse_name_delimiters[0], self.mouse_name_delimiters[1])
            run_name = get_common_data_name_from_path(side_csv_filepath, self.run_name_delimiters[0], self.run_name_delimiters[1])


            # Get the corresponding video file
            ventral_correspondances = [ventral_csv_filepaths[i] for i in range(len(ventral_csv_filepaths)) 
                                    if (batch_name, dataset_name, mouse_name, run_name) == ventral_csv_data[i]]
            
            video_correspondances = [video_filepaths[i] for i in range(len(video_filepaths)) 
                                    if (batch_name, dataset_name, mouse_name, run_name) == video_data[i]]

            if verbose: print(batch_name, dataset_name, mouse_name, run_name)

            # Ensure existence of the corresponding files
            if len(ventral_correspondances) == 0:
                if verbose: print(f"No corresponding ventral view for {side_csv_filepath}")

                # Skip the file if the ventral view is required
                if require_ventral_data:
                    if verbose: print(f"Skipping {side_csv_filepath}")
                    continue

                ventral_correspondances = [None]

            if len(video_correspondances) == 0:
                if verbose: print(f"No corresponding video for {side_csv_filepath}")

                if require_video_data:
                    if verbose: print(f"Skipping {side_csv_filepath}")
                    continue

                video_correspondances = [None]

            # Ensure uniqueness of the corresponding files
            if len(ventral_correspondances) > 1:
                if verbose: print(f"Multiple ventral views for {side_csv_filepath} : {ventral_correspondances}")
                if verbose: print(f"Choosing the first one : {ventral_correspondances[0]}")
                ventral_correspondances = [ventral_correspondances[0]]

            if len(video_correspondances) > 1:
                if verbose: print(f"Multiple videos for {side_csv_filepath} : {video_correspondances}")

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

    val = get_common_data_name_from_path('.\\Data\\Batch1\\CnF_1_ventral_1_eft_1_DLC.csv', 'CnF_1_', '_1_.*1')
    print(val)