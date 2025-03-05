from copy import deepcopy
from itertools import combinations
import numpy as np
from Levenshtein import distance

from FileOrganizer import FileOrganizer
from UI.UtilsUI import split_with_separators

class StructureFinder:
    def set_parameters(self, data_list:list[str], separators:list[str]):
        self._data_list = data_list
        self.set_separators(separators)

    def set_separators(self, separators:list[str]):
        """
            Set the separators to split the data into components and actualize the components limits (start, end) for each data
        """
        self.separators = separators
        _, self._component_limits = self._get_split_components_ids()

    def _get_split_components_ids(self):
        """
            Split the data into components separated by the separator
        """
        all_components : list[list[str]] = []
        all_components_limits : list[list[tuple[int, int]]] = []
        for data in self._data_list:
            components, component_limits = split_with_separators(data, self.separators)

            all_components.append(components)
            all_components_limits.append(component_limits)
        
        return all_components, all_components_limits

    def _get_possible_configurations(self, initial_str:str, component_limits:list[tuple[int,int]], n_groups:int):
        """
            Get all the possible configurations dividing the components into n_groups groups.
            Returns the possible configurations and the start and end index of the components used for each group.

            Example:
            components = ['A', 'B', 'C', 'D']
            n_groups = 2
            return: [['A', 'B_C_D'], ['A_B', 'C_D'], ['A_B_C', 'D']], [[(0, 1), (1, 4)], [(0, 2), (2, 4)], [(0, 3), (3, 4)]]

            n_groups = 3
            return: [['A', 'B', 'C_D'], ['A', 'B_C', 'D'], ['A_B', 'C', 'D']], [[(0, 1), (1, 2), (2, 4)], [(0, 1), (1, 3), (3, 4)], [(0, 2), (2, 3), (3, 4)]]
        """
        if n_groups == 1:
            return [[initial_str]], [(0, len(component_limits))]
        
        # To allow for empty groups at the beginning and end in order to shift the components
        component_limits = deepcopy(component_limits)
        component_limits = [(0, 1)] + component_limits + [(len(initial_str), len(initial_str))]

        # From https://stackoverflow.com/questions/72063383/place-n-unique-elements-into-all-possible-k-groups-with-monotonicity-maintaining
        ans = []
        idx_ans = []
        all_pos = list(range(1, len(component_limits)))
        for pos in combinations(all_pos, n_groups - 1):
            tmp = []
            idx_tmp = []
            prev_idx = 0
            for curr_idx in pos:
                # tmp.append(self.separator.join(components[prev_idx:curr_idx]))
                tmp.append(initial_str[component_limits[prev_idx][0]:component_limits[curr_idx-1][1]])
                idx_tmp.append((prev_idx, curr_idx-1))
                prev_idx = curr_idx
            # tmp.append(self.separator.join(components[curr_idx:]))
            tmp.append(initial_str[component_limits[curr_idx][0]:])
            idx_tmp.append((curr_idx, len(component_limits)))

            ans.append(tmp)
            idx_ans.append(idx_tmp)
        
        return ans, idx_ans
    
    def get_structure(self, data_id:int, structure_id:int):
        """
            Get the structure value of the data at the given index
        """
        return self._structure_data[structure_id][data_id]
    
    def find_structure(self, initial_structure:list[str], struct_of_interest:set[int]|None=None):
        """
            Returns all the possible values of the data for each component of the initial structure.

            The best match is the one that minimizes the sum of the distances between the possible values of the data and the initial structure, on the struct_of_interests.
            The best match is then used to create the _structure_data list that contains the possible values of the data for each component of the initial structure
            and the _structure_idx list that contains the start and end index of the best match for each component of the initial structure

            Also creates 
                _structure_data list that contains the possible values of the data for each component of the initial structure
                _structure_idx list that contains the start and end index of the best match for each component of the initial structure
        """
        ## Make sure that struct_of_interest is a non empty set
        if struct_of_interest is None or len(struct_of_interest) == 0:
            struct_of_interest = set(range(len(initial_structure)))
            
        if not isinstance(struct_of_interest, set):
            struct_of_interest = set(struct_of_interest)


        n_groups = len(initial_structure)
        self._structure_data = [[] for _ in initial_structure]
        self._structure_idx = []

        ## For each data, find the configuration that minimizes the distance between the initial structure and the data
        for i,line in enumerate(self._data_list):
            possible_configurations, idx = self._get_possible_configurations(line, self._component_limits[i], n_groups)
            
            distances = [sum(distance(possible_configurations[i][j], initial_structure[j]) for j in range(n_groups) if j in struct_of_interest) 
                         for i in range(len(possible_configurations))]

            # Minimize the distance between the initial structure and the data
            best_config_id = np.argmin(distances)
            best_config = possible_configurations[best_config_id]
            
            for i, comp in enumerate(best_config):
                self._structure_data[i].append(comp)

            self._structure_idx.append(idx[best_config_id])
        
        # Remove potential duplicates
        possible_structure_values = [set(comp) for comp in self._structure_data]

        # Save the found configurations in decreasing order of length (useful for regex)
        self._sorted_possible_structure_values = [sorted(comp, key=len, reverse=True) for comp in possible_structure_values]

        return possible_structure_values
    
    def get_structure_str(self, batch_pos:int|None, dataset_pos:int|None, mouse_pos:int|None, run_pos:int|None,
                          batch_delimiter:str='Batch', dataset_delimiter:str='Dataset', mouse_delimiter:str='Mouse', run_delimiter:str='Run'):
        """
            Returns the regex string to capture the structure of the data
        """
        structure_str = ''
        for i in range(len(self._structure_data)):
            if i == 0:
                structure_str += '('
            else:
                structure_str += '(' + '|'.join(self.separators) + ')('
            
            if i == batch_pos:
                structure_str += batch_delimiter + ':'
            elif i == dataset_pos:
                structure_str += dataset_delimiter + ':'
            elif i == mouse_pos:
                structure_str += mouse_delimiter + ':'
            elif i == run_pos:
                structure_str += run_delimiter + ':'

            for j, possible_val in enumerate(self._sorted_possible_structure_values[i]):
                structure_str += possible_val
                if j < len(self._sorted_possible_structure_values[i]) - 1:
                    structure_str += '|'
            
            structure_str += ')'

        return structure_str

        
        
if __name__ == "__main__":
    import os
    
    test_folder = r'C:\Users\walid\Desktop\Work\Kinematrix\Test_Left'
    folder_path = os.path.abspath(os.path.join(test_folder, 'Left'))
    target_path = os.path.abspath(os.path.join(test_folder, 'Target'))
    fo = FileOrganizer()
    fo.set_and_load_data_parameters('Sideview', 'Ventralview', folder_path, target_path, '.csv', '.mp4')

    side_names = [os.path.splitext(os.path.basename(file))[0] for file in fo.side_csv_filepaths]
    print(side_names)

    sf = StructureFinder()
    sf.set_parameters(side_names, ['_', 'DLC'])
    # initial_structure = ['Dual_side_and_ventral', 'Mouse2Cage1', 'Post', 'MU_CX', 'Left', 'Run5DLC_resnet50_stxbp1_Corridor_SideviewOct3shuffle1_1000000_filtered']
    initial_structure = ['Dual_side_and_ventral_Mouse8Cage1_Post_WT_Left_Run6DLC_resnet50_stxbp1_Corridor', 'SideviewOct3shuffle1', '1000000_filtered']
    print(sf.find_structure(initial_structure))
    print(sf.get_structure(0, 0))

    print(sf.get_structure_str(0, 1, 2, 3))