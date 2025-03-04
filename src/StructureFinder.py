from copy import deepcopy
from itertools import combinations
import glob, os
import numpy as np

from Levenshtein import distance

from FileOrganizer import FileOrganizer

# def combinations_idx(iterable, r):
#     """
#     Return successive r-length combinations of elements in the iterable, as well as the index of the last element used
#     combinations('ABCD', 2) --> (AB,2) (AC, AD BC BD CD
#     """
#     # combinations('ABCD', 2) --> AB AC AD BC BD CD
#     # combinations(range(4), 3) --> 012 013 023 123
#     pool = tuple(iterable)
#     n = len(pool)
#     if r > n:
#         return
#     indices = list(range(r))
#     yield tuple(pool[i] for i in indices), indices
#     while True:
#         for i in reversed(range(r)):
#             if indices[i] != i + n - r:
#                 break
#         else:
#             return
#         indices[i] += 1
#         for j in range(i+1, r):
#             indices[j] = indices[j-1] + 1
#         yield tuple(pool[i] for i in indices), indices

class StructureFinder:
    def set_parameters(self, data_list:list[str], separator:str):
        self._data_list = data_list
        self.separator = separator

        self._split_data = self._get_split_components()

    def _get_split_components(self):
        """
            Split the data into components separated by the separator
        """
        all_components = []
        for data in self._data_list:
            components = data.split(self.separator)
            all_components.append(components)
        
        return all_components
    
    def _get_all_possible_fusions(self, components:list[str], max_elem_left:int=0):
        for start in range(len(components)):
            for end in range(start, len(components)-max_elem_left):
                yield (start, end, self.separator.join(components[start:end+1]))

    def _get_possible_configurations(self, components:list[str], n_groups:int):
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
            return [[self.separator.join(components)]], [(0, len(components)-1)]

        # From https://stackoverflow.com/questions/72063383/place-n-unique-elements-into-all-possible-k-groups-with-monotonicity-maintaining
        ans = []
        idx_ans = []
        all_pos = list(range(1, len(components)))
        for pos in combinations(all_pos, n_groups - 1):
            tmp = []
            idx_tmp = []
            prev_idx = 0
            for curr_idx in pos:
                tmp.append(self.separator.join(components[prev_idx:curr_idx]))
                idx_tmp.append((prev_idx, curr_idx))
                prev_idx = curr_idx
            tmp.append(self.separator.join(components[curr_idx:]))
            idx_tmp.append((curr_idx, len(components)))

            ans.append(tmp)
            idx_ans.append(idx_tmp)

        return ans, idx_ans
    
    def get_structure(self, data_id:int, structure_id:int):
        """
            Get the structure value of the data at the given index
        """
        return self._structure_data[structure_id][data_id]
    
    def find_structure(self, initial_structure:list[str]):
        """
            Returns all the possible values of the data for each component of the initial structure.

            Also creates 
                _structure_data list that contains the possible values of the data for each component of the initial structure
                _structure_idx list that contains the start and end index of the best match for each component of the initial structure
        """
        components = self._split_data
        self._structure_data = [[] for _ in initial_structure]
        self._structure_idx = []

        for line in components:
            possible_configurations, idx = self._get_possible_configurations(line, len(initial_structure))
            distances = [sum(distance(possible_configurations[i][j], initial_structure[j]) for j in range(len(initial_structure))) for i in range(len(possible_configurations))]
            
            best_config_id = np.argmin(distances)
            best_config = possible_configurations[best_config_id]
            
            for i, comp in enumerate(best_config):
                self._structure_data[i].append(comp)

            self._structure_idx.append(idx[best_config_id])

            # print("Initial structure: ", initial_structure)
            # print("Best configuration: ", best_config)
            # print("Best idx: ", idx[best_config_id])
            # print()

            # possible_fusions = []
            # limits = []
            # for start, end, fusion in self.get_all_possible_fusions(line):
            #     possible_fusions.append(fusion)
            #     limits.append((start, end))

            # current_max_comp_id = 0
            # for i, struct in enumerate(initial_structure):
            #     distances = [distance(struct, fus) for fus in possible_fusions]
            #     sorted_dist_ids = np.argsort(distances)
                
            #     for j in sorted_dist_ids:
            #         start, end = limits[j]
            #         if start >= current_max_comp_id:
            #             structure_data[i].append(possible_fusions[j])
            #             current_max_comp_id = end + 1

            #             print(f'Best match: \t\t{possible_fusions[j]} from {start} to {end}')
            #             print(f'Initial structure: \t{struct}')
            #             print()
            #             break
        
        possible_structure_values = [set(comp) for comp in self._structure_data]
        self._sorted_possible_structure_values = [sorted(comp, reverse=True) for comp in possible_structure_values]
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
                structure_str += self.separator + '('
            
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
    test_folder = r'C:\Users\walid\Desktop\Work\Kinematrix\Test_Left'
    folder_path = os.path.abspath(os.path.join(test_folder, 'Left'))
    target_path = os.path.abspath(os.path.join(test_folder, 'Target'))
    fo = FileOrganizer()
    fo.set_and_load_data_parameters('Sideview', 'Ventralview', folder_path, target_path, '.csv', '.mp4')

    side_names = [os.path.splitext(os.path.basename(file))[0] for file in fo.side_csv_filepaths]
    print(side_names)

    sf = StructureFinder()
    sf.set_parameters(side_names, '_')
    initial_structure = ['Dual_side_and_ventral', 'Mouse2Cage1', 'Post', 'MU_CX', 'Left', 'Run5DLC_resnet50_stxbp1_Corridor_SideviewOct3shuffle1_1000000_filtered']
    print(sf.find_structure(initial_structure))
    print(sf.get_structure(0, 0))

    print(sf.get_structure_str(0, 1, 2, 3))