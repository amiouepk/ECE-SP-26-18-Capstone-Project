import sys
import numpy as np
import data 

# def open_sensor_data_file(num_sensors):
#     files = [open(f"sensor_{i+1}.txt", "a") for i in range(num_sensors)]
#     return files

# def write_data(f, data):
#     f.write(data)
#     f.flush()


def file_reading(msg):
    print(msg)
    imu_num = 5    
    
    sensor_num = [None] * imu_num
    

    if not msg:
        print("Message was empty")
        return

    curr_num_arr = np.empty(6)
    curr_str_num = '' 
    
    i = 0
    j = 1
    k = 0

    if (msg[0] != '|'):
        return

    while (i < imu_num):
        
        if (msg[j] == '|'):

            curr_num_arr[k] = float(curr_str_num)
            curr_str_num = ''
            line_data = data.mpuData(curr_num_arr[0], curr_num_arr[1], curr_num_arr[2], curr_num_arr[3], curr_num_arr[4], curr_num_arr[5])

            sensor_num[i] = line_data

            i += 1
            j += 1
            k = 0
            
            continue

        if (msg[j] == '/'):
            #print(f"STR: {curr_str_num}")

            curr_num_arr[k] = float(curr_str_num)
            curr_str_num = ''
            j += 1
            k += 1
            continue
        
        #print(f"J VAL: {msg[j]}")

        curr_str_num += msg[j]

        j += 1

        #while (j < 7):



    i = 0
    all_data = ''

    while (i < imu_num):
        all_data += sensor_num[i].print_data(i)
        #sensor_num[i].print_data(i)
        i += 1


    #print(all_data)
    
    #line_data.print_data()   


    return all_data



def sample_input(path):
    
    num_sensors = 6

    out_file = open('sensor_data.txt', 'w+')

    try: 
        with open(path, "r", encoding="utf-8") as file:
            
            for line in file:
                # print("in line loop")
                data = file_reading(line.strip())
                
                if data is not None:
                    out_file.write(data + '\n')
                
            
    except FileNotFoundError: 
        print('Please enter a valid file path')
    except Exception as e:
        print(f"An error has occured: {e}")
    


if __name__ == "__main__":

    if (len(sys.argv) > 1):

        sample_input(sys.argv[1])
        

    
    print("finished")
