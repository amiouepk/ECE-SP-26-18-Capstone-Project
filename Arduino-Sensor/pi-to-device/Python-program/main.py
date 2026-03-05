import sys
import numpy as np
import data 

#

def file_reading(file):
    # indexing through diagnostics
    #print('in function')
    while (1):
        line = file.readline()

        print(line)
        
        if not line:
            break
        if line[0] == '|':
            print("found it")

            sensor_num = 1
            
            for line in file:
                curr_sensor = sensor
                #line = file.readline()
                #print(f"input: {input}")

                if not line:
                    break
                
                curr_str_arr = np.empty(6)
                curr_num_arr = np.empty(6)
                curr_str_num = '' 
                

                i = 0
                j = 0

                while (i < 6):
                    
                    while (line[j] != '/' and line[j] != '|'):
                        curr_str_num += line[j]
                        #print(f"line[{j}]: {line[j]}")
                        j += 1
                    
                    curr_num_arr[i] = float(curr_str_num)
                        


                    i += 1

                line_data = data.mpuData(curr_num_arr[0], curr_num_arr[1], curr_num_arr[2], curr_num_arr[3], curr_num_arr[4], curr_num_arr[5])

                line_data.print_data()

                    
                

                


                



                


            break

        # break
    
    return



def sample_input(path):

    try: 
        with open(path, "r", encoding="utf-8") as file:
            file_reading(file)
            
    except FileNotFoundError: 
        print('Please enter a valid file path')
    except Exception as e:
        print(f"An erro rhas occured: {e}")
    


if __name__ == "__main__":

    if (len(sys.argv) > 1):

        sample_input(sys.argv[1])
        

    
    print("finished")
