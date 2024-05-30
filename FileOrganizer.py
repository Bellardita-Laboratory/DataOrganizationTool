
import glob
import os
import shutil

def get_common_data_name_from_path(filepath:os.PathLike, first_name_delimiter:str, last_name_delimiter:str):
    """
        Get the filename, returns the part between the delimiters if it exists in the filename
        Otherwise returns the whole file name
    """
    # Get the file name
    data_name_ext : str = os.path.basename(filepath)

    # Remove the file extension
    data_name, _ = os.path.splitext(data_name_ext)

    # Get the part of the file name before the first occurence of the last delimiter
    # (or the whole filename if there is no delimiter in it)
    splitted_data_name = data_name.split(last_name_delimiter)
    before_name = splitted_data_name[0]

    # Get the part of the before_name after the last occurence of the first delimiter
    splitted_data_name = before_name.split(first_name_delimiter)
    common_name = splitted_data_name[-1]

    return common_name

class FileOrganizer:
    def __init__(self, side_keyword:str, ventral_keyword:str,
                 dataset_name_delimiters:tuple[str,str], mouse_name_delimiters:tuple[str,str], run_name_delimiters:tuple[str,str],
                 batch_name_delimiters:tuple[str,str]=None, default_batch_name:str='Batch'):
        """
            Initialize the file organizer
        """
        self.side_keyword = side_keyword
        self.ventral_keyword = ventral_keyword

        self.dataset_name_delimiters = dataset_name_delimiters
        self.mouse_name_delimiters = mouse_name_delimiters
        self.run_name_delimiters = run_name_delimiters
        self.batch_name_delimiters = batch_name_delimiters

        self.default_batch_name = default_batch_name

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

    def _associate_files(self, side_csv_filepaths:list[os.PathLike], ventral_csv_filepaths:list[os.PathLike], video_filepaths:list[os.PathLike]):
        """
            Associate the side views with the corresponding ventral views and video
        """
        associated_paths : list[tuple[str,str,os.PathLike,os.PathLike,os.PathLike]] = []
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
            ventral_correspondances = [filepath for filepath in ventral_csv_filepaths 
                                    if batch_name in filepath and dataset_name in filepath and mouse_name in filepath and run_name in filepath]
            video_correspondances = [filepath for filepath in video_filepaths 
                                    if batch_name in filepath and dataset_name in filepath and mouse_name in filepath and run_name in filepath]

            print(batch_name, dataset_name, mouse_name, run_name)

            # Ensure existence of the corresponding files
            if len(ventral_correspondances) == 0:
                print(f"No corresponding ventral view for {side_csv_filepath}")
                continue

            if len(video_correspondances) == 0:
                print(f"No corresponding video for {side_csv_filepath}")
                continue

            # Ensure uniqueness of the corresponding files
            if len(ventral_correspondances) > 1:
                print(f"Multiple ventral views for {side_csv_filepath} : {ventral_correspondances}")
                continue

            if len(video_correspondances) > 1:
                print(f"Multiple videos for {side_csv_filepath} : {video_correspondances}")
                continue

            # Get the corresponding filepaths
            ventral_csv_filepath = ventral_correspondances[0]
            video_filepath = video_correspondances[0]

            # Add the corresponding filepaths to the list
            associated_paths.append((batch_name, dataset_name, side_csv_filepath, ventral_csv_filepath, video_filepath))
        
        return associated_paths


    def _copy_with_structure(self, target_folder:str, associated_paths:list[tuple[str,str,os.PathLike,os.PathLike,os.PathLike]],
                            side_folder_name:str, ventral_folder_name:str, video_folder_name:str):
        """
            Create the folder strucure and copy the files in their corresponding folders
        """
        # Create the target folder if it does not exist
        if not os.path.exists(target_folder):
            os.makedirs(target_folder)

        for batch_name, dataset_name, side_csv_filepath, ventral_csv_filepath, video_filepath in associated_paths:
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
            ventral_csv_target = os.path.join(ventral_folder, os.path.basename(ventral_csv_filepath))
            video_target = os.path.join(video_folder, os.path.basename(video_filepath))

            shutil.copy2(side_csv_filepath, side_csv_target)
            shutil.copy2(ventral_csv_filepath, ventral_csv_target)
            shutil.copy2(video_filepath, video_target)


    def organize_files(self, data_folder_path:os.PathLike, target_folder_path:os.PathLike,
                       csv_extension:str='.csv', video_extension:str='.mp4',
                       side_folder_name:str='sideview', ventral_folder_name:str='ventralview', video_folder_name:str='video'):
        # Get the filepaths to all the files in the corresponding folder
        side_csv_filepaths, ventral_csv_filepaths, video_filepaths = self._get_filepaths(data_folder_path, csv_extension, video_extension)

        # Associate the side views with the corresponding ventral views and video
        associated_paths = self._associate_files(side_csv_filepaths, ventral_csv_filepaths, video_filepaths)
        
        # Copy the files to the corresponding folders
        self._copy_with_structure(target_folder_path, associated_paths, side_folder_name, ventral_folder_name, video_folder_name)
    

if __name__ == "__main__":
    folder_path = '.\\Data'
    target_folder = '.\\DataOrganized'
    side_keyword = 'sideview'
    ventral_keyword = 'ventralview'
    dataset_name_delimiters = ('CnF_', '_Corridor')
    mouse_name_delimiter = ('ventral_', '_CnF')
    run_name_delimiters = ('eft_', 'DLC')

    fo = FileOrganizer(side_keyword, ventral_keyword, dataset_name_delimiters, mouse_name_delimiter, run_name_delimiters)

    fo.organize_files(folder_path, target_folder, csv_extension='.csv', video_extension='.mp4',
                      side_folder_name='sideview', ventral_folder_name='ventralview', video_folder_name='video')