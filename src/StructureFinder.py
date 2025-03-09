from copy import deepcopy
from itertools import combinations
from numpy import argmax, inf
from Levenshtein import distance
import re

from time import time_ns as time

from FileOrganizer import FileOrganizer
from UI.UtilsUI import split_with_separators

class StructureFinder:
    def set_parameters(self, data_list:list[str], separators:list[str]):
        self._data_list = data_list
        self.set_separators(separators)

    def get_best_representative(self):
        """
            Get the best representative of the data, ie the one with the most components

            Also returns the number of components of the best representative
        """
        best_id = argmax([len(comps) for comps in self._component_limits])
        return self._data_list[best_id], len(self._component_limits[best_id])

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
        ans : list[list[str]] = []
        idx_ans : list[list[tuple[int,int]]] = []
        all_pos = list(range(1, len(component_limits)))
        for pos in combinations(all_pos, n_groups - 1):
            tmp : list[str] = []
            idx_tmp : list[tuple[int,int]] = []
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
    
    def _get_best_match(self, sub_str:str, match_str:str, component_limits:list[tuple[int,int]], 
                        min_start_id:int=0, n_test_components:int=2):
        """
            Get the best match of the sub_str in the match_str starting at the start_pos
        """
        if n_test_components < 1:
            raise ValueError("Need to test at least 1 component to find the best match")

        best_start_id = min_start_id
        best_end_id = min_start_id
        best_distance = inf

        def get_best(start_id:int, end_id:int):
            """ 
                Get the best match between the sub_str and the component of the match_str between start_id and end_id 

                Returns the best distance, the start id and the end id of the best match
            """
            if start_id < 0 or end_id >= len(component_limits) or start_id > end_id:
                return best_distance, best_start_id, best_end_id
            
            possible_component = match_str[component_limits[start_id][0]:component_limits[end_id][1]]
            dist = distance(sub_str, possible_component)

            if dist < best_distance:
                return dist, start_id, end_id
            else:
                return best_distance, best_start_id, best_end_id
            
        ## Find the best match
        for i in range(min_start_id, len(component_limits)):
            ## Find the index j so that the length of the component is around the length of the substring (best chance of matching)
            start = component_limits[i][0]
            sub_str_end = start + len(sub_str)
            j = i
            while j < len(component_limits) - 1 and component_limits[j][1] < sub_str_end:
                j += 1   

            ## Test the n_test_components components around the index j
            for k in range(-n_test_components//2, n_test_components//2):
                if j+k < i or j+k >= len(component_limits):
                    continue
                best_distance, best_start_id, best_end_id = get_best(i, j+k)
        
        return best_start_id, best_end_id
    
    def find_structure(self, initial_structure:list[str], struct_of_interest:list[int|None], struct_names:list[str], n_test_components:int):
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
        if len(struct_of_interest) == 0:
            struct_of_interest_set = set(range(len(initial_structure)))
        else:
            struct_of_interest_set = set(struct_of_interest)

        if None in struct_of_interest_set:
            struct_of_interest_set.remove(None)

        list_struct_of_interest : list[int] = sorted(struct_of_interest_set)

        # n_groups = len(initial_structure)
        self._structure_data : list[list[str]] = [[] for _ in initial_structure]
        self._structure_idx = []

        # total_time = 0
        # total_config_time = 0
        # total_dist_time = 0
        # total_best_time = 0
        # total_assign_time = 0
        ## For each data, find the configuration that minimizes the distance between the initial structure and the data
        for i,line in enumerate(self._data_list):
            min_start_id = 0
            idx = [None] * len(initial_structure)
            ## For each component of interest of the initial structure, find the best match in the data
            for struct_id in list_struct_of_interest:
                # Add empty string if we reached the last component
                if min_start_id >= len(self._component_limits[i]):
                    best_start_pos = best_end_pos = len(line)
                    best_start_id = min_start_id
                    best_end_id = min_start_id - 1
                else:
                    struct = initial_structure[struct_id]
                    best_start_id, best_end_id = self._get_best_match(struct, line, self._component_limits[i], min_start_id, n_test_components)
                    best_start_pos = self._component_limits[i][best_start_id][0]
                    best_end_pos = self._component_limits[i][best_end_id][1]

                self._structure_data[struct_id].append(line[best_start_pos:best_end_pos])
                idx[struct_id] = (best_start_id, best_end_id)
                
                min_start_id = best_end_id + 1
                    

            ## Fill in the rest of the components (ie the ones that are not of interest)
            start_id = 0
            for j in range(len(initial_structure)):
                if j not in struct_of_interest_set:
                    start_pos = self._component_limits[i][start_id][0]

                    # If the current component is not of interest, then the next one has to be
                    #   So we can just look at the start id of the next one to infer the end id of this one
                    if j < len(initial_structure) - 1:
                        next_id = j+1
                        next_start_id,_ = idx[next_id]
                    else:
                        next_start_id = len(self._component_limits[i]) - 1  # If we reached the last component, then the next one is the last one
                    
                    end_id = next_start_id - 1 if next_start_id > start_id else start_id
                    end_pos = self._component_limits[i][end_id][1]

                    self._structure_data[j].append(line[start_pos:end_pos])
                    idx[j] = (start_id, end_id)

                    start_id = end_id + 1 if end_id < len(self._component_limits[i]) - 1 else end_id
                else:
                    current_end_id = idx[j][1]
                    start_id = current_end_id + 1 if current_end_id < len(self._component_limits[i]) - 1 else current_end_id
            
            self._structure_idx.append(idx)

            # print(self._structure_data)
            # print(self._structure_idx)

            # print(f'Finding structure for data {i+1}/{len(self._data_list)}')
            # t = time()
            # possible_configurations, idx = self._get_possible_configurations(line, self._component_limits[i], n_groups,
            #                                                                  initial_structure, distance, n_down_before_cut=1, 
            #                                                                  struct_of_interest=sorted(struct_of_interest_set))

            # total_config_time += time() - t
            # print(f"Calculating distances for data {i+1}/{len(self._data_list)}")

            # print(possible_configurations)
            
            # t = time()
            # distances = [sum(distance(possible_configurations[i][j], initial_structure[j]) for j in range(n_groups) if j in struct_of_interest_set) 
            #              for i in range(len(possible_configurations))]
            # total_dist_time += time() - t
            
            # print(f"Finding best configuration for data {i+1}/{len(self._data_list)}")
            # t = time()

            # # Minimize the distance between the initial structure and the data
            # best_config_id = argmin(distances)
            # best_config = possible_configurations[best_config_id]

            # total_best_time += time() - t
            # t = time()
            
            # for j, comp in enumerate(best_config):
            #     self._structure_data[j].append(comp)

            # self._structure_idx.append(idx[best_config_id])
            # total_assign_time = time() - t

        # total_time = total_config_time + total_dist_time + total_best_time + total_assign_time

        # percent_config_time = total_config_time/total_time*100 if total_time != 0 else 0
        # percent_dist_time = total_dist_time/total_time*100 if total_time != 0 else 0
        # percent_best_time = total_best_time/total_time*100 if total_time != 0 else 0
        # percent_assign_time = total_assign_time/total_time*100 if total_time != 0 else 0
        
        # print(f"Total time: {total_time}")
        # print(f"Total config time: {total_config_time} ({percent_config_time}%)")
        # print(f"Total dist time: {total_dist_time} ({percent_dist_time}%)")
        # print(f"Total best time: {total_best_time} ({percent_best_time}%)")
        # print(f"Total assign time: {total_assign_time} ({percent_assign_time}%)")
        
        # Remove potential duplicates
        possible_structure_values = [set(comp) for comp in self._structure_data]

        # Save the found configurations in decreasing order of length (useful for regex)
        self._sorted_possible_structure_values = [sorted(comp, key=len, reverse=True) for comp in possible_structure_values]

        # for i in zip(*self._structure_data):
        #     print(i)
        
        structure_dicts : list[dict[str,str]] = [{
                    struct_name: self._structure_data[struct_id][i] 
                    if struct_id is not None else self._data_list[i]
                for struct_name, struct_id in zip(struct_names, struct_of_interest, strict=True)} 
            for i in range(len(self._data_list))]
    
        return structure_dicts

    def get_structure_regexp(self, batch_pos:int|None, dataset_pos:int|None, mouse_pos:int|None, run_pos:int|None,
                          batch_delimiter:str='Batch', dataset_delimiter:str='Dataset', mouse_delimiter:str='Mouse', run_delimiter:str='Run'):
        """
            Returns the regex string to capture the structure of the data
        """
        escaped_separators = [re.escape(sep) for sep in self.separators]
        separators_str = '(?:' + '|'.join(escaped_separators) + ')+('

        structure_str = ''
        for i in range(len(self._structure_data)):
            if i == 0:
                structure_str += '('
            else:
                structure_str += separators_str
            
            if i == batch_pos:
                structure_str += batch_delimiter + ':'
            elif i == dataset_pos:
                structure_str += dataset_delimiter + ':'
            elif i == mouse_pos:
                structure_str += mouse_delimiter + ':'
            elif i == run_pos:
                structure_str += run_delimiter + ':'
            else:
                structure_str += '?:' # Non capturing group

            for j, possible_val in enumerate(self._sorted_possible_structure_values[i]):
                structure_str += re.escape(possible_val)
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

    print(sf.get_structure_regexp(0, 1, 2, 3))